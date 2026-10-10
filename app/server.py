"""Web app: start a migration from an upload, a GitHub repo or a live SQL Server, watch it run, get the results.

    uv run python -m app            # http://localhost:8000
"""
import re
from pathlib import Path, PurePosixPath

from fastapi import FastAPI, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

from app import jobs
from harness import ingest

STATIC = Path(__file__).parent / "static"
MAX_UPLOAD_BYTES = 50 * 1024 * 1024

app = FastAPI(title="sql-to-dbt", docs_url=None, redoc_url=None)


@app.on_event("startup")
def _startup():
    jobs.start_worker()


@app.get("/", response_class=HTMLResponse)
def index():
    return (STATIC / "index.html").read_text()


@app.get("/jobs/{job_id}", response_class=HTMLResponse)
def job_page(job_id: str):
    _status_or_404(job_id)
    return (STATIC / "job.html").read_text()


@app.get("/api/jobs")
def api_list():
    return jobs.list_jobs()


@app.get("/api/jobs/{job_id}")
def api_status(job_id: str):
    st = _status_or_404(job_id)
    st.pop("trace", None)
    return st


@app.get("/jobs/{job_id}/dashboard", response_class=HTMLResponse)
def job_dashboard(job_id: str):
    f = jobs.JOBS / _check_id(job_id) / "dashboard.html"
    if not f.exists():
        raise HTTPException(404, "Dashboard is ready when the job finishes.")
    return f.read_text()


@app.get("/jobs/{job_id}/download")
def job_download(job_id: str):
    f = jobs.JOBS / _check_id(job_id) / "dbt_project.zip"
    if not f.exists():
        raise HTTPException(404, "The dbt project is ready when the job finishes.")
    return FileResponse(f, filename=f"dbt_project_{job_id}.zip", media_type="application/zip")


@app.post("/api/jobs")
async def api_create(
    source: str = Form(...),
    files: list[UploadFile] | None = None,
    github_url: str = Form(""), github_token: str = Form(""),
    host: str = Form(""), port: str = Form("1433"), database: str = Form(""), user: str = Form(""), password: str = Form(""),
    sample_rows: str = Form("0"),
    anthropic_key: str = Form(""),
):
    secrets = {k: v for k, v in (("anthropic_key", anthropic_key.strip()), ("github_token", github_token.strip()),
                                 ("password", password)) if v}
    if source == "upload":
        if not files:
            raise HTTPException(400, "Choose a folder or a .zip file.")
        job = jobs.new_job("upload", {"files": len(files)}, secrets)
        await _save_upload(files, job.dir / "input")
    elif source == "github":
        if not re.match(r"https?://github\.com/[\w.-]+/[\w.-]+", github_url.strip()):
            raise HTTPException(400, "Enter a GitHub URL like https://github.com/owner/repo")
        job = jobs.new_job("github", {"github_url": github_url.strip()}, secrets)
    elif source == "sqlserver":
        if not (host.strip() and database.strip() and user.strip()):
            raise HTTPException(400, "Host, database and user are required.")
        try:
            rows = max(0, min(int(sample_rows or 0), 1000))
            port_n = int(port or 1433)
        except ValueError:
            raise HTTPException(400, "Port and sample rows must be numbers.")
        job = jobs.new_job("sqlserver", {"host": host.strip(), "port": port_n, "database": database.strip(),
                                         "user": user.strip(), "sample_rows": rows}, secrets)
    else:
        raise HTTPException(400, "Unknown source.")
    jobs.submit(job)
    return JSONResponse({"id": job.id})


async def _save_upload(files: list[UploadFile], dest: Path):
    total = 0
    for i, f in enumerate(files):
        data = await f.read()
        total += len(data)
        if total > MAX_UPLOAD_BYTES:
            raise HTTPException(413, "Upload is larger than 50 MB.")
        name = f.filename or f"file_{i}"
        if name.lower().endswith(".zip") and len(files) == 1:
            try:
                ingest.safe_extract(data, dest)
            except Exception as e:
                raise HTTPException(400, f"Could not read the zip: {e}")
            return
        # keep the folder structure the browser sends, but never let a path escape dest
        parts = [p for p in PurePosixPath(name.replace("\\", "/")).parts if p not in ("", ".", "..", "/")]
        target = dest.joinpath(*parts) if parts else dest / f"file_{i}"
        if target.exists():
            target = target.with_name(f"{target.stem}_{i}{target.suffix}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)


def _check_id(job_id: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{10}", job_id):
        raise HTTPException(404, "No such job.")
    return job_id


def _status_or_404(job_id: str) -> dict:
    st = jobs.read_status(_check_id(job_id))
    if st is None:
        raise HTTPException(404, "No such job.")
    return st
