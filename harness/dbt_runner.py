"""Load legacy source data into DuckDB, write dbt model, run dbt, fetch output."""
import re
import subprocess
import sys
from pathlib import Path
import duckdb

ROOT = Path(__file__).resolve().parent.parent / "dbt_project"
DB = ROOT / "target" / "warehouse.duckdb"
DBT = Path(sys.executable).with_name("dbt")
TIMEOUT_S = 120

_TYPE_MAP = [(r"^(n?varchar|n?char|text|ntext)\b", "VARCHAR"), (r"^(decimal|numeric)\((\d+),(\d+)\)$", None),
             (r"^bigint$", "BIGINT"), (r"^(int|smallint|tinyint|bit)$", "INTEGER"), (r"^(float|real)$", "DOUBLE"),
             (r"^date$", "DATE"), (r"^(datetime|datetime2|smalldatetime)$", "TIMESTAMP"), (r"^money$", "DECIMAL(19,4)")]

# Statement-level keywords that have no business in a single SELECT model.
_FORBIDDEN = re.compile(r"\b(copy|attach|detach|install|load|pragma|export|import|call|insert|update|delete|drop|alter|truncate|create)\b"
                        r"|read_(csv|parquet|json|text|blob|ndjson)\w*|\bglob\s*\(|\{%|env_var|run_query|\blog\s*\(", re.I)


def duck_type(tsql_type: str) -> str:
    for pat, duck in _TYPE_MAP:
        m = re.match(pat, tsql_type, re.I)
        if m:
            return duck or f"DECIMAL({min(int(m.group(2)), 38)},{m.group(3)})"
    return "VARCHAR"


def check_model_sql(sql: str) -> str | None:
    """Returns a rejection reason, or None if the SQL looks like a single read-only SELECT."""
    body = re.sub(r"'(?:[^']|'')*'", "''", re.sub(r"--[^\n]*|/\*.*?\*/", "", sql, flags=re.S))
    if ";" in body.strip().rstrip(";"):
        return "model must be a single SELECT statement (found ';')"
    m = _FORBIDDEN.search(body)
    return f"forbidden construct in model: {m.group(0)!r}" if m else None


SANDBOX = {"enable_external_access": False, "autoload_known_extensions": False, "autoinstall_known_extensions": False}


def db_path(variant: str) -> Path:
    """dbt runs against the base DB; other variants live in same-named files so compiled SQL resolves."""
    return DB if variant == "base" else ROOT / "target" / "variants" / variant / "warehouse.duckdb"


def load_sources(schema, sources, variant="base"):
    path = db_path(variant)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.unlink(missing_ok=True)
    con = duckdb.connect(str(path))
    try:
        con.execute("create schema legacy")
        for t, (cols, rows) in sources.items():
            name = t.split(".")[-1]
            ddl = ", ".join(f'"{c}" {duck_type(ty)}' for c, ty in schema[t])
            con.execute(f"create table legacy.{name} ({ddl})")
            if rows:
                con.executemany(f"insert into legacy.{name} values ({','.join('?' * len(cols))})",
                                [[int(v) if isinstance(v, bool) else v for v in r] for r in rows])
    finally:
        con.close()


def write_sources_yml(tables):
    body = "version: 2\nsources:\n  - name: legacy\n    schema: legacy\n    tables:\n" + "".join(f"      - name: {t.split('.')[-1]}\n" for t in tables)
    (ROOT / "models" / "sources.yml").write_text(body)


def _dbt_error(log: str) -> str:
    """Keep only the error part of dbt's log, minus ANSI codes and timestamps."""
    lines = [re.sub(r"^\d\d:\d\d:\d\d\s*", "", re.sub(r"\x1b\[[0-9;]*m", "", l)).rstrip() for l in log.splitlines()]
    start = next((i for i, l in enumerate(lines) if re.search(r"error", l, re.I) and "PASS=" not in l), max(len(lines) - 30, 0))
    return "\n".join(l for l in lines[start:] if l.strip() and not l.startswith(("Done.", "Finished running", "Completed with")))[:2000]


def run_model(model_name, model_sql):
    """Returns ((cols, rows), None) on success or (None, error_text)."""
    if not re.fullmatch(r"\w+", model_name):
        raise ValueError(f"bad model name {model_name!r}")
    reason = check_model_sql(model_sql)
    if reason:
        return None, f"rejected before execution: {reason}"
    for f in (ROOT / "models").glob("*.sql"):
        f.unlink()
    (ROOT / "models" / f"{model_name}.sql").write_text(model_sql)
    try:
        p = subprocess.run([str(DBT), "run", "--select", model_name, "--profiles-dir", ".", "--project-dir", "."],
                           cwd=ROOT, capture_output=True, text=True, timeout=TIMEOUT_S)
    except subprocess.TimeoutExpired:
        return None, f"dbt run timed out after {TIMEOUT_S}s"
    if p.returncode != 0:
        return None, _dbt_error(p.stdout + p.stderr)
    con = duckdb.connect(str(DB), read_only=True)
    try:
        cur = con.execute(f"select * from main.{model_name}")
        return ([d[0] for d in cur.description], cur.fetchall()), None
    finally:
        con.close()


def run_compiled(model_name, variant):
    """Execute the model dbt compiled in the last run_model() against another dataset, sandboxed."""
    sql = (ROOT / "target" / "compiled" / "migrated" / "models" / f"{model_name}.sql").read_text()
    con = duckdb.connect(str(db_path(variant)), read_only=True, config=SANDBOX)
    try:
        cur = con.execute(sql)
        return ([d[0] for d in cur.description], cur.fetchall()), None
    except duckdb.Error as e:
        return None, f"{type(e).__name__}: {e}"[:2000]
    finally:
        con.close()
