"""Turn whatever the user supplied into a project folder (schema.sql, data.sql, procs/*.sql) for harness.intake.

Sources:
  from_files(dir)          any tree of .sql files: SSMS "Generate Scripts" output, one-proc-per-file repos, mixed dumps
  from_github(url, token)  a repo (or sub-folder) downloaded as a zip, then from_files
  from_sql_server(...)     a live database: proc/view/function definitions, generated table DDL, optional sample rows

Statements are sorted by what they are, not where they sit: a file may hold several GO-separated batches of
different kinds. Schema statements are replayed against a scratch database until no more succeed, which fixes
ordering across files (e.g. a foreign key to a table defined later) and reports what could not be created.
"""
import io
import json
import re
import shutil
import urllib.request
import zipfile
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pymssql

from harness.legacy import CONN, batches, literal

SQL_SUFFIXES = {".sql", ".prc", ".proc", ".tab", ".vw", ".udf", ".trg"}
MAX_ZIP_BYTES = 50 * 1024 * 1024
MAX_FILES = 5000

PROC = re.compile(r"^\s*CREATE\s+(?:OR\s+ALTER\s+)?PROC(?:EDURE)?\b", re.I)
SCHEMA = re.compile(r"^\s*(?:CREATE\s+(?:OR\s+ALTER\s+)?(?:TABLE|VIEW|SCHEMA|FUNCTION|TYPE|SEQUENCE|SYNONYM|"
                    r"(?:UNIQUE\s+)?(?:(?:NON)?CLUSTERED\s+)?INDEX)\b|ALTER\s+TABLE\b)", re.I)
DATA = re.compile(r"^\s*(?:SET\s+IDENTITY_INSERT\b|INSERT\b)", re.I)
SKIP = re.compile(r"^\s*(?:USE\b|SET\s+(?:ANSI_\w+|QUOTED_IDENTIFIER|NOCOUNT|ARITHABORT|CONCAT_NULL_YIELDS_NULL|NUMERIC_ROUNDABORT|XACT_ABORT)\b|"
                  r"PRINT\b|GRANT\b|DENY\b|REVOKE\b|DROP\b|IF\s+(?:NOT\s+)?EXISTS\b|IF\s+OBJECT_ID\b|EXEC(?:UTE)?\s+(?:sys\.)?sp_addextendedproperty\b|"
                  r"CREATE\s+(?:USER|LOGIN|ROLE|DATABASE|TRIGGER)\b|ALTER\s+(?:DATABASE|AUTHORIZATION|ROLE)\b)", re.I)


def _strip_leading_comments(sql: str) -> str:
    prev = None
    while prev != sql:
        prev = sql
        sql = re.sub(r"^\s*(?:--[^\n]*\n|/\*.*?\*/)", "", sql, count=1, flags=re.S)
    return sql


def _decode(raw: bytes) -> str:
    """SSMS often saves scripts as UTF-16 with a BOM."""
    for bom, enc in ((b"\xef\xbb\xbf", "utf-8-sig"), (b"\xff\xfe", "utf-16"), (b"\xfe\xff", "utf-16")):
        if raw.startswith(bom):
            return raw.decode(enc)
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("latin-1")


def classify(sql_text: str):
    """Split a script into batches and sort them. Returns {"schema": [...], "data": [...], "procs": [...], "skipped": [...]}."""
    out = {"schema": [], "data": [], "procs": [], "skipped": []}
    for b in batches(sql_text):
        head = _strip_leading_comments(b)
        if not head.strip():
            continue
        if PROC.match(head):
            out["procs"].append(b.strip())
        elif DATA.match(head):
            out["data"].append(b.strip())
        elif SCHEMA.match(head):
            out["schema"].append(b.strip())
        else:
            # a batch may start with SET options and still contain DDL/DML further down
            body = "\n".join(l for l in head.splitlines() if not SKIP.match(l))
            if PROC.search(body):
                out["procs"].append(body.strip())
            elif SCHEMA.search(body) and not PROC.search(body):
                out["schema"].append(body.strip())
            elif DATA.search(body):
                out["data"].append(body.strip())
            else:
                out["skipped"].append(head.strip().splitlines()[0][:120])
    return out


def _proc_name(sql: str) -> str:
    part = r"(?:\[[^\]]+\]|\w+)"  # bracketed names may contain spaces, bare names may not
    m = re.search(rf"CREATE\s+(?:OR\s+ALTER\s+)?PROC(?:EDURE)?\s+({part}(?:\.{part})?)", sql, re.I)
    return m.group(1).replace("[", "").replace("]", "") if m else "unnamed"


def _order_schema(statements, scratch_db="mig_ingest_scratch"):
    """Replay statements until a pass makes no progress. Returns (ordered_ok, [(statement_head, error)])."""
    conn = pymssql.connect(**CONN)
    cur = conn.cursor()
    try:
        cur.execute("USE master")
        cur.execute(f"IF DB_ID('{scratch_db}') IS NOT NULL BEGIN ALTER DATABASE [{scratch_db}] SET SINGLE_USER WITH ROLLBACK IMMEDIATE; DROP DATABASE [{scratch_db}] END")
        cur.execute(f"CREATE DATABASE [{scratch_db}]")
        cur.execute(f"USE [{scratch_db}]")
        pending, ok, errors = list(statements), [], {}
        while pending:
            progressed, still = False, []
            for s in pending:
                try:
                    cur.execute(s)
                    ok.append(s)
                    progressed = True
                except pymssql.Error as e:
                    errors[s] = str(e.args[1] if len(e.args) > 1 else e)[:300]
                    still.append(s)
            pending = still
            if not progressed:
                break
        failed = [(_strip_leading_comments(s).strip().splitlines()[0][:120], errors[s]) for s in pending]
        cur.execute("USE master")
        cur.execute(f"ALTER DATABASE [{scratch_db}] SET SINGLE_USER WITH ROLLBACK IMMEDIATE; DROP DATABASE [{scratch_db}]")
        return ok, failed
    finally:
        conn.close()


def _referenced_tables(proc_sql):
    body = re.sub(r"--[^\n]*|/\*.*?\*/", "", proc_sql, flags=re.S)
    names = re.findall(r"\b(?:FROM|JOIN|INTO|UPDATE|MERGE(?:\s+INTO)?|TRUNCATE\s+TABLE|DELETE\s+(?:FROM\s+)?)\s+((?:\[?\w+\]?\.)?\[?\w+\]?)", body, re.I)
    aliases = {a.lower() for a in re.findall(r"\b(?:FROM|JOIN)\s+[\w.\[\]#]+\s+(?:AS\s+)?(\w+)", body, re.I)}
    return {n.replace("[", "").replace("]", "").lower() for n in names
            if not n.startswith(("#", "@", "(")) and not ("." not in n and n.strip("[]").lower() in aliases)}


def write_project(root: Path, schema, data, procs, params_files=None, report=None):
    """Write the harness project layout plus ingest_report.json."""
    report = report or {}
    if root.exists():
        shutil.rmtree(root)
    (root / "procs").mkdir(parents=True)
    ok, failed = _order_schema(schema) if schema else ([], [])
    (root / "schema.sql").write_text("\nGO\n".join(ok) + ("\nGO\n" if ok else ""))
    if data:
        (root / "data.sql").write_text("\nGO\n".join(data) + "\nGO\n")
    known = {m.lower().replace("[", "").replace("]", "")
             for s in ok for m in re.findall(r"CREATE\s+(?:TABLE|VIEW)\s+((?:\[?\w+\]?\.)?\[?\w+\]?)", s, re.I)}
    known |= {k.split(".", 1)[1] for k in known if "." in k}
    seen, missing = {}, {}
    for p in procs:
        name = _proc_name(p)
        fname = re.sub(r"[^\w.]+", "_", name)
        if fname in seen:  # same proc defined twice: keep the last definition
            report.setdefault("duplicates", []).append(name)
        seen[fname] = p
        unknown = sorted(t for t in _referenced_tables(p) if t not in known and t.split(".")[-1] not in known)
        if unknown:
            missing[name] = unknown
    for fname, p in seen.items():
        (root / "procs" / f"{fname}.sql").write_text(p.rstrip() + "\n")
        # params files may be named after the file or the bare proc name (uspX.params.json for Sales.uspX)
        pkey = next((k for k in (fname.lower(), fname.split(".")[-1].lower()) if params_files and k in params_files), None)
        if pkey:
            (root / "procs" / f"{fname}.params.json").write_text(params_files[pkey])
    n_objects = sum(len(re.findall(r"CREATE\s+(?:TABLE|VIEW)\b", s, re.I)) for s in ok)
    report.update({"tables_and_views": n_objects, "schema_statements": len(ok),
                   "schema_failed": failed, "data_statements": len(data), "procedures": len(seen),
                   "procs_referencing_unknown_tables": missing})
    (root / "ingest_report.json").write_text(json.dumps(report, indent=1, default=str))
    if not ok:
        raise ValueError("No table definitions found. Include CREATE TABLE scripts for the tables your procedures use.")
    if not seen:
        raise ValueError("No CREATE PROCEDURE statements found.")
    return report


def from_files(src: Path, root: Path):
    schema, data, procs, skipped, params, n = [], [], [], [], {}, 0
    for f in sorted(src.rglob("*")):
        if not f.is_file() or any(part.startswith(".") for part in f.relative_to(src).parts):
            continue
        n += 1
        if n > MAX_FILES:
            raise ValueError(f"More than {MAX_FILES} files; upload just the SQL scripts.")
        if f.name.lower().endswith(".params.json"):
            params[f.name[:-len(".params.json")].lower()] = f.read_text()
            continue
        if f.suffix.lower() not in SQL_SUFFIXES:
            continue
        c = classify(_decode(f.read_bytes()))
        schema += c["schema"]
        data += c["data"]
        procs += c["procs"]
        skipped += [f"{f.relative_to(src)}: {s}" for s in c["skipped"]]
    return write_project(root, schema, data, procs, params, {"source": "files", "skipped_statements": skipped[:200]})


def safe_extract(zip_bytes: bytes, dest: Path):
    if len(zip_bytes) > MAX_ZIP_BYTES:
        raise ValueError("Archive is larger than 50 MB.")
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
        total = sum(i.file_size for i in z.infolist())
        if total > 4 * MAX_ZIP_BYTES:
            raise ValueError("Archive expands to more than 200 MB.")
        for info in z.infolist():
            target = (dest / info.filename).resolve()
            if not target.is_relative_to(dest.resolve()):  # zip-slip
                raise ValueError(f"Unsafe path in archive: {info.filename}")
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(z.read(info))


def from_github(url: str, root: Path, token: str | None = None, workdir: Path | None = None):
    """https://github.com/owner/repo[/tree/<ref>[/sub/path]]"""
    m = re.match(r"https?://github\.com/([\w.-]+)/([\w.-]+?)(?:\.git)?(?:/tree/([^/]+)(?:/(.+))?)?/?$", url.strip())
    if not m:
        raise ValueError("Expected a URL like https://github.com/owner/repo or .../tree/main/sql")
    owner, repo, ref, sub = m.groups()
    api = f"https://api.github.com/repos/{owner}/{repo}/zipball" + (f"/{ref}" if ref else "")
    req = urllib.request.Request(api, headers={"Accept": "application/vnd.github+json", "User-Agent": "sql-to-dbt",
                                               **({"Authorization": f"Bearer {token}"} if token else {})})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read(MAX_ZIP_BYTES + 1)
    except urllib.error.HTTPError as e:
        raise ValueError(f"GitHub returned {e.code}" + (" (private repo? add a token)" if e.code in (401, 403, 404) else "")) from None
    workdir = workdir or root.parent / "github_src"
    if workdir.exists():
        shutil.rmtree(workdir)
    workdir.mkdir(parents=True)
    safe_extract(raw, workdir)
    top = next(workdir.iterdir())  # zipball wraps everything in owner-repo-sha/
    src = (top / sub).resolve() if sub else top
    if not src.is_relative_to(top.resolve()):
        raise ValueError(f"Path {sub!r} is outside the repository")
    if not src.exists():
        raise ValueError(f"Path {sub!r} not found in the repository")
    return from_files(src, root)


# ---------------------------------------------------------------- live SQL Server
def _type_sql(ty, max_len, prec, scale):
    if ty in ("varchar", "char", "varbinary", "binary"):
        return f"{ty}({'max' if max_len == -1 else max_len})"
    if ty in ("nvarchar", "nchar"):
        return f"{ty}({'max' if max_len == -1 else max_len // 2})"
    if ty in ("decimal", "numeric"):
        return f"{ty}({prec},{scale})"
    if ty in ("datetime2", "time", "datetimeoffset"):
        return f"{ty}({scale})"
    return ty


def from_sql_server(host, port, database, user, password, root: Path, sample_rows: int = 0):
    """Read-only: reads catalog views and (optionally) SELECT TOP n from each table. Nothing is written to the source."""
    conn = pymssql.connect(server=host, port=str(port or 1433), user=user, password=password, database=database,
                           login_timeout=15, timeout=120)
    cur = conn.cursor()
    try:
        cur.execute("""SELECT s.name, o.name, o.type, m.definition FROM sys.sql_modules m
                       JOIN sys.objects o ON o.object_id = m.object_id JOIN sys.schemas s ON s.schema_id = o.schema_id
                       WHERE o.is_ms_shipped = 0 AND o.type IN ('P','V','FN','IF','TF') ORDER BY o.type, s.name, o.name""")
        modules = cur.fetchall()
        cur.execute("SELECT name FROM sys.schemas WHERE schema_id BETWEEN 5 AND 16383")
        schemas = [f"CREATE SCHEMA [{r[0]}]" for r in cur.fetchall()]
        cur.execute("""SELECT s.name, t.name, c.name, ty.name, c.max_length, c.precision, c.scale, c.is_nullable,
                              c.is_identity, cc.definition
                       FROM sys.tables t JOIN sys.schemas s ON s.schema_id = t.schema_id
                       JOIN sys.columns c ON c.object_id = t.object_id JOIN sys.types ty ON ty.user_type_id = c.user_type_id
                       LEFT JOIN sys.computed_columns cc ON cc.object_id = c.object_id AND cc.column_id = c.column_id
                       WHERE t.is_ms_shipped = 0 ORDER BY s.name, t.name, c.column_id""")
        tables = {}
        for s, t, c, ty, ml, pr, sc, nul, ident, comp in cur.fetchall():
            col = f"[{c}] AS {comp}" if comp else \
                f"[{c}] {_type_sql(ty, ml, pr, sc)}{' IDENTITY(1,1)' if ident else ''}{' NULL' if nul else ' NOT NULL'}"
            tables.setdefault((s, t), []).append(col)
        cur.execute("""SELECT s.name, t.name, k.name, STRING_AGG('[' + c.name + ']', ', ') WITHIN GROUP (ORDER BY ic.key_ordinal)
                       FROM sys.key_constraints k JOIN sys.tables t ON t.object_id = k.parent_object_id
                       JOIN sys.schemas s ON s.schema_id = t.schema_id
                       JOIN sys.index_columns ic ON ic.object_id = k.parent_object_id AND ic.index_id = k.unique_index_id
                       JOIN sys.columns c ON c.object_id = ic.object_id AND c.column_id = ic.column_id
                       WHERE k.type = 'PK' GROUP BY s.name, t.name, k.name""")
        pks = {(s, t): f"CONSTRAINT [{k}] PRIMARY KEY ({cols})" for s, t, k, cols in cur.fetchall()}
        cur.execute("""SELECT ps.name, pt.name, f.name, STRING_AGG('[' + pc.name + ']', ', '), rs.name, rt.name, STRING_AGG('[' + rc.name + ']', ', ')
                       FROM sys.foreign_keys f JOIN sys.foreign_key_columns fc ON fc.constraint_object_id = f.object_id
                       JOIN sys.tables pt ON pt.object_id = f.parent_object_id JOIN sys.schemas ps ON ps.schema_id = pt.schema_id
                       JOIN sys.columns pc ON pc.object_id = fc.parent_object_id AND pc.column_id = fc.parent_column_id
                       JOIN sys.tables rt ON rt.object_id = f.referenced_object_id JOIN sys.schemas rs ON rs.schema_id = rt.schema_id
                       JOIN sys.columns rc ON rc.object_id = fc.referenced_object_id AND rc.column_id = fc.referenced_column_id
                       GROUP BY ps.name, pt.name, f.name, rs.name, rt.name""")
        fks = [f"ALTER TABLE [{ps}].[{pt}] ADD CONSTRAINT [{f}] FOREIGN KEY ({pc}) REFERENCES [{rs}].[{rt}] ({rc})"
               for ps, pt, f, pc, rs, rt, rc in cur.fetchall()]
        ddl = [f"CREATE TABLE [{s}].[{t}] (\n    " + ",\n    ".join(cols + ([pks[(s, t)]] if (s, t) in pks else [])) + "\n)"
               for (s, t), cols in tables.items()]
        views_funcs = [d for _, _, ty, d in modules if ty.strip() != "P" and d]
        procs = [d for _, _, ty, d in modules if ty.strip() == "P" and d]

        data = []
        if sample_rows > 0:
            for (s, t), cols in tables.items():
                cur.execute(f"SELECT TOP ({int(sample_rows)}) * FROM [{s}].[{t}]")
                names = [d[0] for d in cur.description]
                rows = cur.fetchall()
                if not rows:
                    continue
                cur.execute(f"SELECT COLUMNPROPERTY(OBJECT_ID('[{s}].[{t}]'), name, 'IsComputed') FROM sys.columns "
                            f"WHERE object_id = OBJECT_ID('[{s}].[{t}]') ORDER BY column_id")
                computed = [bool(r[0]) for r in cur.fetchall()]
                keep = [i for i, c in enumerate(computed) if not c and not isinstance(rows[0][i], (bytes, bytearray))]
                ident = any("IDENTITY" in c for c in cols)
                col_list = ", ".join(f"[{names[i]}]" for i in keep)
                stmts = [f"SET IDENTITY_INSERT [{s}].[{t}] ON"] if ident else []
                for k in range(0, len(rows), 100):
                    stmts.append(f"INSERT INTO [{s}].[{t}] ({col_list}) VALUES " + ",".join(
                        "(" + ", ".join(literal(r[i]) for i in keep) + ")" for r in rows[k:k + 100]))
                if ident:
                    stmts.append(f"SET IDENTITY_INSERT [{s}].[{t}] OFF")
                data.append(";\n".join(stmts))
    finally:
        conn.close()
    return write_project(root, schemas + ddl + fks + views_funcs, data, procs, None,
                         {"source": f"sql server {host}/{database}", "sample_rows_per_table": sample_rows})
