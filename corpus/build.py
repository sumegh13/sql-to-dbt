"""Materialize procs/<nnn>_<slug>/{proc.sql,model.sql,meta.json} from the specs."""
import json, re, shutil
from pathlib import Path
from specs_a import SPECS_A
from specs_b import SPECS_B

ROOT = Path(__file__).resolve().parent.parent
out = ROOT / "procs"
if out.exists():
    shutil.rmtree(out)
for n, (slug, diff, tags, body, model) in enumerate(SPECS_A + SPECS_B, 1):
    d = out / f"{n:03d}_{slug}"
    d.mkdir(parents=True)
    proc = (f"CREATE OR ALTER PROCEDURE dbo.usp_{slug}\nAS\nBEGIN\n    SET NOCOUNT ON;\n"
            f"    IF OBJECT_ID('dbo.{slug}') IS NOT NULL DROP TABLE dbo.{slug};\n{body.strip()}\nEND\n")
    (d / "proc.sql").write_text(proc)
    if model:
        (d / "reference_model.sql").write_text(re.sub(r"<<(\w+)>>", r"{{ source('legacy', '\1') }}", model.strip()) + "\n")
    (d / "meta.json").write_text(json.dumps({"id": n, "slug": slug, "proc": f"dbo.usp_{slug}", "output": f"dbo.{slug}",
                                              "difficulty": diff, "tags": tags}, indent=1))
print(len(SPECS_A + SPECS_B), "procs")
