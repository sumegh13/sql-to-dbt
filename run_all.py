"""Migrate every proc in a project. Usage: run_all.py [--project NAME] [name-filter ...]"""
import argparse
import json
import shutil

from harness import project as projects
from migrate import migrate

ap = argparse.ArgumentParser()
ap.add_argument("--project", default="corpus", help="'corpus' (default) or a projects/<name> folder")
ap.add_argument("--results", help="write results here instead of the project's results folder (e.g. for test runs)")
ap.add_argument("filters", nargs="*")
args = ap.parse_args()

proj = projects.load(args.project)
if args.results:
    from pathlib import Path
    proj.results = Path(args.results)
dirs = sorted(d for d in proj.procs.iterdir() if d.is_dir())
if args.filters:
    dirs = [d for d in dirs if any(a in d.name for a in args.filters)]
elif proj.results.exists():
    shutil.rmtree(proj.results)  # full run: drop stale results from renamed/removed procs
proj.results.mkdir(parents=True, exist_ok=True)
for d in dirs:
    r = migrate(proj, d)
    (proj.results / f"{d.name}.json").write_text(json.dumps(r, indent=1, default=str))
    print(f"{r['status']:12} {d.name} {r.get('reason_category', '')}", flush=True)
    if r["status"] == "error":
        print("   ", r["reason"])
    elif r["status"] != "verified" and r["history"]:
        print("   ", json.dumps(r["history"][-1]["detail"], default=str)[:400])
