"""Run a legacy T-SQL proc in SQL Server against the shared fixture and dump tables."""
import json
import re
from pathlib import Path
import pymssql

CORPUS = Path(__file__).resolve().parent.parent / "corpus"
CONN = dict(server="localhost", user="sa", password="Legacy_Pass123", autocommit=True)
SOURCE_TABLES = json.loads((CORPUS / "tables.json").read_text())


def _batches(sql: str):
    return [b for b in re.split(r"^\s*GO\s*$", sql, flags=re.M | re.I) if b.strip()]


def _dump(cur, t):
    cur.execute(f"SELECT * FROM {t}")
    return [d[0] for d in cur.description], cur.fetchall()


def run_proc(proc_sql: str, proc_name: str, output_table: str):
    """Reset fixture, create + run proc. Returns (sources_before, output).
    Sources are dumped BEFORE the proc runs so procs that mutate them can't skew the baseline."""
    conn = pymssql.connect(**CONN)
    cur = conn.cursor()
    for b in _batches((CORPUS / "fixture.sql").read_text()):
        cur.execute(b)
    sources = {t: _dump(cur, t) for t in SOURCE_TABLES}
    for b in _batches(proc_sql):
        cur.execute(b)
    cur.execute(f"EXEC {proc_name}")
    out = _dump(cur, output_table)
    conn.close()
    return sources, out
