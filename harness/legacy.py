"""Run a legacy T-SQL proc in SQL Server against the shared fixture and dump tables."""
import json
import os
import re
from contextlib import closing
from pathlib import Path
import pymssql

CORPUS = Path(__file__).resolve().parent.parent / "corpus"
CONN = dict(server=os.environ.get("MSSQL_HOST", "localhost"), user=os.environ.get("MSSQL_USER", "sa"),
            password=os.environ.get("MSSQL_SA_PASSWORD", "Legacy_Pass123"), autocommit=True)
SOURCE_TABLES = json.loads((CORPUS / "tables.json").read_text())


def _batches(sql: str):
    return [b for b in re.split(r"^\s*GO\s*$", sql, flags=re.M | re.I) if b.strip()]


def _dump(cur, t):
    cur.execute(f"SELECT * FROM {t}")
    return [d[0] for d in cur.description], cur.fetchall()


def _schema(cur):
    """{ 'dbo.t': [(col, 'decimal(18,2)'), ...] } from INFORMATION_SCHEMA, in column order."""
    cur.execute("""SELECT TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, NUMERIC_PRECISION, NUMERIC_SCALE
                   FROM INFORMATION_SCHEMA.COLUMNS ORDER BY TABLE_SCHEMA, TABLE_NAME, ORDINAL_POSITION""")
    out = {}
    for sch, tbl, col, dt, clen, prec, scale in cur.fetchall():
        t = f"{sch}.{tbl}".lower()
        if dt in ("decimal", "numeric"):
            dt = f"{dt}({prec},{scale})"
        elif dt in ("varchar", "nvarchar", "char", "nchar"):
            dt = f"{dt}({'max' if clen == -1 else clen})"
        out.setdefault(t, []).append((col, dt))
    return out


def run_proc(proc_sql: str, proc_name: str, output_table: str):
    """Reset fixture, create + run proc. Returns (schema, sources_before, output).
    Sources are dumped BEFORE the proc runs so procs that mutate them can't skew the baseline."""
    with closing(pymssql.connect(**CONN)) as conn:
        cur = conn.cursor()
        for b in _batches((CORPUS / "fixture.sql").read_text()):
            cur.execute(b)
        schema = _schema(cur)
        schema = {t: schema[t.lower()] for t in SOURCE_TABLES}
        sources = {t: _dump(cur, t) for t in SOURCE_TABLES}
        for b in _batches(proc_sql):
            cur.execute(b)
        cur.execute(f"EXEC {proc_name}")
        return schema, sources, _dump(cur, output_table)
