"""Export a project's migration results as a standalone dbt project.

    uv run python export.py [--project NAME] [--out DIR]

Writes <out>/ (default out/<project>/):
  dbt_project.yml, models/sources.yml
  models/migrated/<model>.sql + schema.yml      verified models, documented with the agent's explanation
  models/needs_review/<model>.sql (disabled)    agent proposals for procs a human must decide on
  REVIEW.md, MIGRATION_REPORT.md
Then runs `dbt build` on the exported project against the base dataset to prove it works as a whole.
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

import yaml

from harness import dbt_runner
from harness import project as projects


def _model_name(r):
    return re.sub(r"\W+", "_", r["slug"]).lower()


def _header(r, proc_name):
    lines = [f"-- Migrated from {proc_name}"]
    if r["status"] == "verified":
        ds = ", ".join(f"{k}: {v} rows" for k, v in r.get("datasets", {}).items())
        lines.append(f"-- Verified equivalent: output matched the legacy procedure row by row on {ds}"
                     + (f" across {r['param_sets']} parameter sets" if r.get("param_sets", 1) > 1 else "") + ".")
    if r.get("param_mode") == "vars":
        example = json.dumps(r.get("dbt_vars", {}))
        lines.append("-- Parameterized via dbt vars (the parameters change what is aggregated, so a row filter can't express it):")
        lines.append(f"--   dbt run --select {_model_name(r)} --vars '{example}'")
    if r.get("param_filter"):
        lines.append("-- Parameterized: the procedure's rows for given parameters are this model filtered by")
        lines.append("--   " + r["param_filter"].replace("\n", " "))
    return "\n".join(lines) + "\n"


def export(proj, out: Path):
    results = [json.loads(f.read_text()) for f in sorted(proj.results.glob("*.json"))]
    if not results:
        raise SystemExit(f"no results in {proj.results}: run run_all.py --project {proj.name} first")
    if out.exists():
        shutil.rmtree(out)
    (out / "models" / "migrated").mkdir(parents=True)
    (out / "models" / "needs_review").mkdir(parents=True)

    pname = re.sub(r"\W+", "_", proj.name).lower()
    dbt_vars = {}  # defaults so `dbt build` works; override per run with --vars
    for r in results:
        if r["status"] == "verified":
            for k, v in r.get("dbt_vars", {}).items():
                dbt_vars.setdefault(k, v)
    (out / "dbt_project.yml").write_text(yaml.safe_dump({
        "name": pname, "version": "1.0", "config-version": 2, "profile": pname, "model-paths": ["models"],
        **({"vars": dbt_vars} if dbt_vars else {}),
        "models": {pname: {"migrated": {"+materialized": "table"}, "needs_review": {"+enabled": False}}},
    }, sort_keys=False))
    (out / "models" / "sources.yml").write_text(
        "# Point schema/database at wherever the legacy tables land in the new platform.\n" + yaml.safe_dump({
            "version": 2,
            "sources": [{"name": "legacy", "schema": "{{ var('legacy_schema', 'legacy') }}",
                         "tables": [{"name": proj.source_name(t), "identifier": proj.source_name(t),
                                     "description": f"Legacy table {t}"} for t in proj.tables]}],
        }, sort_keys=False))

    docs, review, report_rows = [], [], []
    for r in results:
        meta = json.loads((proj.procs / f"{r['id']:03d}_{r['slug']}" / "meta.json").read_text()) \
            if (proj.procs / f"{r['id']:03d}_{r['slug']}").exists() else {}
        proc_name = meta.get("proc", r["slug"])
        name = _model_name(r)
        if r["status"] == "verified":
            (out / "models" / "migrated" / f"{name}.sql").write_text(_header(r, proc_name) + r["model_sql"].rstrip() + "\n")
            docs.append({"name": name, "description": r.get("explanation") or f"Migrated from {proc_name}.",
                         "meta": {"legacy_procedure": proc_name, "verified_rows": r.get("rows"), "attempts": r["attempts"],
                                  **({"param_filter": r["param_filter"]} if r.get("param_filter") else {})}})
            report_rows.append((proc_name, "verified", f"{r.get('rows')} rows, {r['attempts']} attempt(s)"))
            continue
        prop = r.get("proposal") or {}
        sql = prop.get("model_sql") or r.get("model_sql")
        if sql:
            (out / "models" / "needs_review" / f"{name}.sql").write_text(
                f"-- NEEDS REVIEW ({r.get('reason_category')}): {r.get('reason')}\n"
                f"-- Agent proposal, {prop.get('verification', 'not verified')}. Disabled until a reviewer signs off.\n"
                + sql.rstrip() + "\n")
        review.append((proc_name, name, r, prop))
        report_rows.append((proc_name, "needs human", r.get("reason_category", "")))
    (out / "models" / "migrated" / "schema.yml").write_text(yaml.safe_dump({"version": 2, "models": docs}, sort_keys=False, width=110))

    lines = [f"# Review queue: {proj.name}", "",
             f"{len(review)} procedure(s) need a human decision. Proposed models are in `models/needs_review/` (disabled).", ""]
    for proc_name, name, r, prop in review:
        lines += [f"## {proc_name}", "", f"**Why:** {r.get('reason')}", ""]
        if r.get("explanation"):
            lines += [f"**What it does:** {r['explanation']}", ""]
        if prop:
            lines += [f"**Proposal:** `models/needs_review/{name}.sql`, {prop.get('verification')}.", ""]
            for key, title in (("questions", "Questions for the reviewer"), ("assumptions", "Assumptions"), ("not_migrated", "Not migrated")):
                if prop.get(key):
                    lines += [f"**{title}:**", "", prop[key].strip(), ""]
    (out / "REVIEW.md").write_text("\n".join(lines))

    verified = sum(1 for _, s, _ in report_rows if s == "verified")
    cost = sum(r.get("cost_usd") or 0 for r in results)
    rep = [f"# Migration report: {proj.name}", "", f"Generated {date.today().isoformat()}.", "",
           f"**{verified} of {len(results)} procedures migrated and verified equivalent; {len(results) - verified} need a human.**", "",
           "Each verified model was run on the same datasets as the legacy procedure (base, two random seeds, and an edge-case set), "
           "for every parameter set, and its output matched row by row.", "", f"LLM cost for the run: ${cost:.3f}.", "",
           "| Procedure | Status | Detail |", "|---|---|---|"]
    rep += [f"| `{p}` | {s} | {d} |" for p, s, d in report_rows]
    (out / "MIGRATION_REPORT.md").write_text("\n".join(rep) + "\n")
    return verified, len(results)


def smoke_build(proj, out: Path):
    """dbt build the exported project against a copy of the base dataset, using a throwaway profile."""
    from harness.legacy import Legacy
    out = out.resolve()
    work = out / ".smoke"
    work.mkdir(exist_ok=True)
    db = work / "warehouse.duckdb"
    with Legacy(proj) as L:  # fresh copy of this project's base dataset
        L.load(proj.variants[0])
        schema, sources = L.schema(), L.sources()
    dbt_runner.load_sources(schema, sources, "_export_smoke", proj.source_name)
    shutil.move(str(dbt_runner.db_path("_export_smoke")), db)
    pname = re.sub(r"\W+", "_", proj.name).lower()
    (work / "profiles.yml").write_text(yaml.safe_dump({pname: {"target": "smoke", "outputs": {"smoke": {
        "type": "duckdb", "path": str(db), "threads": 4, "settings": {"enable_external_access": False}}}}}))
    dbt = Path(sys.executable).with_name("dbt")
    p = subprocess.run([str(dbt), "build", "--profiles-dir", str(work), "--project-dir", str(out),
                        "--target-path", str(work / "target"), "--log-path", str(work / "logs")],
                       capture_output=True, text=True, timeout=600)
    log = re.sub(r"\x1b\[[0-9;]*m", "", p.stdout)
    summary = next((l for l in log.splitlines()[::-1] if "PASS=" in l), log[-500:]).strip()
    if p.returncode != 0:
        summary += "\n" + "\n".join(l for l in log.splitlines() if "Error" in l or "error" in l)[:1500]
    shutil.rmtree(work)
    return p.returncode == 0, summary


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default="corpus")
    ap.add_argument("--out")
    a = ap.parse_args()
    proj = projects.load(a.project)
    out = Path(a.out) if a.out else Path("out") / proj.name
    verified, total = export(proj, out)
    print(f"exported {verified}/{total} verified models to {out}")
    ok, summary = smoke_build(proj, out)
    print("dbt build", "OK" if ok else "FAILED", "|", summary)
