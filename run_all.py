import json, sys
from pathlib import Path
from migrate import migrate

dirs = sorted(Path("procs").iterdir())
if len(sys.argv) > 1:
    dirs = [d for d in dirs if any(a in d.name for a in sys.argv[1:])]
Path("results").mkdir(exist_ok=True)
for d in dirs:
    r = migrate(d)
    (Path("results") / f"{d.name}.json").write_text(json.dumps(r, indent=1, default=str))
    extra = r.get("reason_category", "")
    print(f"{r['status']:12} {d.name} {extra}", flush=True)
    if r["status"] == "needs_human" and r["history"]:
        print("   ", json.dumps(r["history"][-1]["detail"], default=str)[:400])
