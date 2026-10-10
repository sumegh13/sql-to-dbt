"""Run legacy T-SQL procs in SQL Server against a project's dataset variants.

A dataset is loaded once per variant; each proc execution then runs inside a transaction that is rolled back,
so procs that write tables can't leak state into the next run.
"""
import os
import re
from datetime import date, datetime
from decimal import Decimal
import pymssql

from harness.project import Project

CONN = dict(server=os.environ.get("MSSQL_HOST", "localhost"), user=os.environ.get("MSSQL_USER", "sa"),
            password=os.environ.get("MSSQL_SA_PASSWORD", "Legacy_Pass123"), autocommit=True)


def batches(sql: str):
    return [b for b in re.split(r"^\s*GO\s*$", sql, flags=re.M | re.I) if b.strip()]


def literal(v) -> str:
    """Python value -> T-SQL literal."""
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "1" if v else "0"
    if isinstance(v, (int, float, Decimal)):
        return str(v)
    if isinstance(v, (date, datetime)):
        return f"'{v.isoformat(sep=' ') if isinstance(v, datetime) else v.isoformat()}'"
    return "N'" + str(v).replace("'", "''") + "'"


class Legacy:
    def __init__(self, project: Project):
        self.p = project
        self.conn = pymssql.connect(**CONN)
        self.cur = self.conn.cursor()
        self.loaded = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.conn.close()

    def load(self, variant: str):
        cur = self.cur
        if self.p.database:
            db = self.p.database
            cur.execute("USE master")
            cur.execute(f"IF DB_ID('{db}') IS NOT NULL BEGIN ALTER DATABASE [{db}] SET SINGLE_USER WITH ROLLBACK IMMEDIATE; DROP DATABASE [{db}] END")
            cur.execute(f"CREATE DATABASE [{db}]")
            cur.execute(f"USE [{db}]")
        for b in batches((self.p.fixtures / f"{variant}.sql").read_text()):
            cur.execute(b)
        self.loaded = variant

    def schema(self):
        """{legacy_table: [(col, 'decimal(18,2)'), ...]} in column order, for the project's tables."""
        self.cur.execute("""SELECT TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, NUMERIC_PRECISION, NUMERIC_SCALE
                            FROM INFORMATION_SCHEMA.COLUMNS ORDER BY TABLE_SCHEMA, TABLE_NAME, ORDINAL_POSITION""")
        out = {}
        for sch, tbl, col, dt, clen, prec, scale in self.cur.fetchall():
            if dt in ("decimal", "numeric"):
                dt = f"{dt}({prec},{scale})"
            elif dt in ("varchar", "nvarchar", "char", "nchar"):
                dt = f"{dt}({'max' if clen == -1 else clen})"
            out.setdefault(f"{sch}.{tbl}".lower(), []).append((col, dt))
        return {t: out[t.lower()] for t in self.p.tables}

    def dump(self, table: str):
        self.cur.execute(f"SELECT * FROM {table}")
        return [d[0] for d in self.cur.description], self.cur.fetchall()

    def sources(self):
        return {t: self.dump(t) for t in self.p.tables}

    def create_proc(self, proc_sql: str):
        for b in batches(proc_sql):
            self.cur.execute(b)

    def run(self, proc_name: str, params: dict, output_table: str | None):
        """EXEC the proc in a rolled-back transaction. Returns {"result_sets": [(cols, rows)], "table": (cols, rows)|None}."""
        cur = self.cur
        args = ", ".join(f"{k} = {literal(v)}" for k, v in params.items())
        cur.execute("BEGIN TRANSACTION")
        try:
            cur.execute(f"EXEC {proc_name} {args}")
            sets = []
            while True:
                if cur.description:
                    sets.append(([d[0] for d in cur.description], cur.fetchall()))
                if not cur.nextset():
                    break
            table = self.dump(output_table) if output_table else None
            return {"result_sets": sets, "table": table}
        finally:
            cur.execute("SELECT @@TRANCOUNT")
            if cur.fetchone()[0] > 0:
                cur.execute("ROLLBACK")
            else:  # the proc committed or rolled back our transaction itself: data may be dirty
                self.loaded = None
