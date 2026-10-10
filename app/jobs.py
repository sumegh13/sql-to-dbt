"""Background migration jobs for the web app.

One worker thread runs jobs in order (the dbt workspace and SQL Server are shared). Secrets (Claude key, GitHub
token, database password) live only in the in-memory job and are never written to disk.
"""
import json
import os
import queue
import shutil
import threading
import time
import traceback
import uuid
from dataclasses import dataclass, field
from pathlib import Path

import pymssql

from harness import ingest, intake
from harness import project as projects
from harness.legacy import CONN

ROOT = Path(__file__).resolve().parent.parent
JOBS = ROOT / "jobs"
TERMINAL = ("done", "failed")


@dataclass
class Job:
    id: str
    source: str                                   # upload | github | sqlserver
    options: dict = field(default_factory=dict)   # non-secret inputs, shown in status
    secrets: dict = field(default_factory=dict)   # never persisted

    @property
    def dir(self) -> Path:
        return JOBS / self.id

    @property
    def project_root(self) -> Path:
        return self.dir / f"job_{self.id}"


def new_job(source: str, options: dict, secrets: dict) -> Job:
    job = Job(uuid.uuid4().hex[:10], source, options, secrets)
    (job.dir / "input").mkdir(parents=True)
    write_status(job.id, state="queued", source=source, options=options, created=time.time(), procs=[], log=[])
    return job


def read_status(job_id: str) -> dict | None:
    f = JOBS / job_id / "status.json"
    return json.loads(f.read_text()) if f.exists() else None


_lock = threading.Lock()


def write_status(job_id: str, **changes):
    with _lock:
        f = JOBS / job_id / "status.json"
        st = json.loads(f.read_text()) if f.exists() else {"id": job_id}
        st.update(changes)
        tmp = f.with_suffix(".tmp")
        tmp.write_text(json.dumps(st, default=str))
        tmp.replace(f)
        return st


def log(job_id: str, msg: str):
    st = read_status(job_id) or {}
    write_status(job_id, log=(st.get("log", []) + [f"{time.strftime('%H:%M:%S')} {msg}"])[-200:])


def list_jobs() -> list[dict]:
    out = []
    for d in sorted(JOBS.glob("*/status.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        st = json.loads(d.read_text())
        out.append({k: st.get(k) for k in ("id", "state", "source", "options", "created", "summary", "error")})
    return out


# ---------------------------------------------------------------- worker
_queue: "queue.Queue[Job]" = queue.Queue()


def submit(job: Job):
    _queue.put(job)


def _drop_database(name: str):
    try:
        conn = pymssql.connect(**CONN)
        conn.cursor().execute(f"IF DB_ID('{name}') IS NOT NULL BEGIN ALTER DATABASE [{name}] SET SINGLE_USER WITH ROLLBACK IMMEDIATE; DROP DATABASE [{name}] END")
        conn.close()
    except pymssql.Error:
        pass


def _run(job: Job):
    from dashboard import render
    from export import export, smoke_build
    from migrate import migrate

    jid = job.id
    key = job.secrets.get("anthropic_key")
    try:
        if not key:
            raise ValueError("No Anthropic API key was given for this job.")
        _check_key(key)
        os.environ["ANTHROPIC_API_KEY"] = key  # only for the duration of this job
        write_status(jid, state="ingesting", started=time.time())
        root = job.project_root
        if job.source == "upload":
            report = ingest.from_files(job.dir / "input", root)
        elif job.source == "github":
            report = ingest.from_github(job.options["github_url"], root, job.secrets.get("github_token"), job.dir / "github_src")
        else:
            o = job.options
            report = ingest.from_sql_server(o["host"], o.get("port") or 1433, o["database"], o["user"],
                                            job.secrets.get("password", ""), root, int(o.get("sample_rows") or 0))
        write_status(jid, ingest=report)
        log(jid, f"found {report['procedures']} procedures and {report['tables_and_views']} tables/views")

        write_status(jid, state="building")
        intake.build(root)
        proj = projects.load(str(root))
        dirs = sorted(d for d in proj.procs.iterdir() if d.is_dir())
        names = [json.loads((d / "meta.json").read_text())["proc"] for d in dirs]
        write_status(jid, state="migrating", procs=[{"name": n, "status": "pending"} for n in names])
        log(jid, "built 4 test datasets; migrating")

        proj.results.mkdir(parents=True, exist_ok=True)
        statuses = [{"name": n, "status": "pending"} for n in names]
        for i, d in enumerate(dirs):
            statuses[i]["status"] = "running"
            write_status(jid, procs=statuses)
            r = migrate(proj, d)
            (proj.results / f"{d.name}.json").write_text(json.dumps(r, indent=1, default=str))
            statuses[i].update(status=r["status"], reason_category=r.get("reason_category"), cost_usd=r.get("cost_usd"))
            write_status(jid, procs=statuses)

        write_status(jid, state="exporting")
        out = job.dir / "dbt_project"
        verified, total = export(proj, out)
        ok, summary = smoke_build(proj, out)
        log(jid, f"dbt build {'OK' if ok else 'FAILED'}: {summary.splitlines()[0] if summary else ''}")
        shutil.make_archive(str(job.dir / "dbt_project"), "zip", out)
        html, _ = render(proj)
        (job.dir / "dashboard.html").write_text(html)
        cost = sum(s.get("cost_usd") or 0 for s in statuses)
        write_status(jid, state="done", finished=time.time(), dbt_build_ok=ok,
                     summary={"verified": verified, "total": total, "cost_usd": round(cost, 4)})
    except Exception as e:
        write_status(jid, state="failed", error=f"{type(e).__name__}: {e}", trace=traceback.format_exc()[-3000:])
    finally:
        os.environ.pop("ANTHROPIC_API_KEY", None)
        job.secrets.clear()
        _drop_database(projects.database_name(job.project_root.name))


def _check_key(key: str):
    """Fail fast with a clear message instead of failing every procedure later. Costs no tokens."""
    import anthropic
    from harness.translate import MODEL
    try:
        anthropic.Anthropic(api_key=key, max_retries=1).models.retrieve(MODEL)
    except anthropic.AuthenticationError:
        raise ValueError("Anthropic rejected this API key. Check it at console.anthropic.com.") from None
    except anthropic.PermissionDeniedError:
        raise ValueError(f"This API key can't use {MODEL}.") from None
    except anthropic.APIConnectionError:
        raise ValueError("Could not reach the Anthropic API from here.") from None


def _worker():
    while True:
        job = _queue.get()
        _run(job)


def start_worker():
    JOBS.mkdir(exist_ok=True)
    for st_file in JOBS.glob("*/status.json"):  # jobs interrupted by a restart can't resume: their secrets are gone
        st = json.loads(st_file.read_text())
        if st.get("state") not in TERMINAL:
            write_status(st["id"], state="failed", error="Server restarted before this job finished. Start it again.")
    threading.Thread(target=_worker, daemon=True, name="migration-worker").start()
