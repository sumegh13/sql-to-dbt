"""Load legacy source data into DuckDB, write dbt model, run dbt, fetch output."""
import subprocess
from pathlib import Path
import duckdb

ROOT = Path(__file__).resolve().parent.parent / "dbt_project"
DB = ROOT / "target" / "warehouse.duckdb"


def _ddl_type(vals):
    from datetime import date, datetime
    from decimal import Decimal
    v = next((x for x in vals if x is not None), None)
    if isinstance(v, Decimal):
        scale = max(-x.as_tuple().exponent for x in vals if x is not None)
        return f"DECIMAL(38,{max(scale, 0)})"
    if isinstance(v, float):
        return "DOUBLE"
    if isinstance(v, datetime):
        return "TIMESTAMP"
    if isinstance(v, date):
        return "DATE"
    if isinstance(v, int):  # includes bool (BIT)
        return "BIGINT"
    return "VARCHAR"


def load_sources(sources):
    DB.parent.mkdir(exist_ok=True)
    if DB.exists():
        DB.unlink()
    con = duckdb.connect(str(DB))
    con.execute("create schema if not exists legacy")
    for t, (cols, rows) in sources.items():
        name = t.split(".")[-1]
        types = [_ddl_type([r[i] for r in rows]) for i in range(len(cols))]
        con.execute(f"create table legacy.{name} ({', '.join(f'{c} {ty}' for c, ty in zip(cols, types))})")
        if rows:
            con.executemany(f"insert into legacy.{name} values ({','.join('?'*len(cols))})",
                            [[int(v) if isinstance(v, bool) else v for v in r] for r in rows])
    con.close()


def write_sources_yml(tables):
    body = "version: 2\nsources:\n  - name: legacy\n    schema: legacy\n    tables:\n" + "".join(f"      - name: {t.split('.')[-1]}\n" for t in tables)
    (ROOT / "models" / "sources.yml").write_text(body)


def run_model(model_name, model_sql):
    for f in (ROOT / "models").glob("*.sql"):
        f.unlink()
    (ROOT / "models" / f"{model_name}.sql").write_text(model_sql)
    p = subprocess.run(["uv", "run", "dbt", "run", "--select", model_name, "--profiles-dir", ".", "--project-dir", "."],
                       cwd=ROOT, capture_output=True, text=True)
    if p.returncode != 0:
        return None, (p.stdout + p.stderr)[-2000:]
    con = duckdb.connect(str(DB), read_only=True)
    cur = con.execute(f"select * from main.{model_name}")
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()
    con.close()
    return (cols, rows), None
