import json
import shutil
import sys
from pathlib import Path
from migrate import migrate

dirs = sorted(d for d in Path("procs").iterdir() if d.is_dir())
filters = sys.argv[1:]
if filters:
    dirs = [d for d in dirs if any(a in d.name for a in filters)]
elif Path("results").exists():
    shutil.rmtree("results")  # full run: drop stale results from renamed/removed procs
Path("results").mkdir(exist_ok=True)
for d in dirs:
    r = migrate(d)
    (Path("results") / f"{d.name}.json").write_text(json.dumps(r, indent=1, default=str))
    print(f"{r['status']:12} {d.name} {r.get('reason_category', '')}", flush=True)
    if r["status"] != "verified" and r["history"]:
        print("   ", json.dumps(r["history"][-1]["detail"], default=str)[:400])
    elif r["status"] == "error":
        print("   ", r["reason"])
