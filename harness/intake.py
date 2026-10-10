"""Build a user project into something the harness can run.

    uv run python -m harness.intake projects/<name>

Input  projects/<name>/schema.sql              CREATE TABLE (and view) DDL, any schemas, FKs/identity allowed
       projects/<name>/data.sql                optional INSERTs for the base dataset
       projects/<name>/procs/*.sql             one CREATE PROCEDURE per file
       projects/<name>/procs/<file>.params.json  optional list of parameter sets, e.g. [{"@CustomerID": 3}]
Output projects/<name>/build/{project.json, fixtures/<variant>.sql, procs/NNN_slug/{proc.sql, meta.json}}

Datasets: base (data.sql, or synthesized), seed_101 and seed_202 (synthesized), edge (synthesized edge cases).
Every synthesized row is test-inserted into SQL Server and dropped if the database rejects it, so fixtures always load.
"""
import json
import random
import re
import shutil
import string
import sys
import uuid
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path

import pymssql

from harness import preflight
from harness.legacy import CONN, batches, literal
from harness.project import database_name

VARIANTS = {"seed_101": (101, False), "seed_202": (202, False), "edge": (303, True)}
ROWS = {False: 30, True: 15}
NAMES = ["Acme", "Globex", "Initech", "Hooli", "Umbrella", "Stark", "Wayne", "Wonka", "Cyberdyne", "Tyrell"]
STATUSES = ["active", "inactive", "pending", "shipped", "cancelled", "closed"]


# ---------------------------------------------------------------- database introspection
def _recreate(cur, db, schema_sql):
    cur.execute("USE master")
    cur.execute(f"IF DB_ID('{db}') IS NOT NULL BEGIN ALTER DATABASE [{db}] SET SINGLE_USER WITH ROLLBACK IMMEDIATE; DROP DATABASE [{db}] END")
    cur.execute(f"CREATE DATABASE [{db}]")
    cur.execute(f"USE [{db}]")
    for b in batches(schema_sql):
        cur.execute(b)


def _introspect(cur):
    """Returns (tables, views): tables = {"sch.tbl": {"cols": [...], "fks": {col: (parent, pcol)}}}."""
    cur.execute("SELECT TABLE_SCHEMA, TABLE_NAME, TABLE_TYPE FROM INFORMATION_SCHEMA.TABLES ORDER BY TABLE_SCHEMA, TABLE_NAME")
    objs = cur.fetchall()
    tables = {f"{s}.{t}": {"cols": [], "fks": {}} for s, t, ty in objs if ty == "BASE TABLE"}
    views = [f"{s}.{t}" for s, t, ty in objs if ty == "VIEW"]
    cur.execute("""
        SELECT s.name, t.name, c.name, ty.name, c.max_length, c.precision, c.scale, c.is_nullable, c.is_identity, c.is_computed,
               CASE WHEN EXISTS (SELECT 1 FROM sys.index_columns ic JOIN sys.indexes i ON i.object_id = ic.object_id AND i.index_id = ic.index_id
                                 WHERE ic.object_id = c.object_id AND ic.column_id = c.column_id AND i.is_unique = 1) THEN 1 ELSE 0 END
        FROM sys.columns c JOIN sys.tables t ON t.object_id = c.object_id JOIN sys.schemas s ON s.schema_id = t.schema_id
        JOIN sys.types ty ON ty.user_type_id = c.user_type_id ORDER BY s.name, t.name, c.column_id""")
    for s, t, c, ty, mlen, prec, scale, nullable, ident, computed, unique in cur.fetchall():
        if ty in ("nvarchar", "nchar") and mlen > 0:
            mlen //= 2
        tables[f"{s}.{t}"]["cols"].append(dict(name=c, type=ty, len=mlen, prec=prec, scale=scale, nullable=bool(nullable),
                                               identity=bool(ident), skip=bool(computed) or ty in ("timestamp", "rowversion"),
                                               unique=bool(unique)))
    cur.execute("""
        SELECT ps.name, pt.name, pc.name, rs.name, rt.name, rc.name FROM sys.foreign_key_columns f
        JOIN sys.tables pt ON pt.object_id = f.parent_object_id JOIN sys.schemas ps ON ps.schema_id = pt.schema_id
        JOIN sys.columns pc ON pc.object_id = f.parent_object_id AND pc.column_id = f.parent_column_id
        JOIN sys.tables rt ON rt.object_id = f.referenced_object_id JOIN sys.schemas rs ON rs.schema_id = rt.schema_id
        JOIN sys.columns rc ON rc.object_id = f.referenced_object_id AND rc.column_id = f.referenced_column_id""")
    for ps, pt, pc, rs, rt, rc in cur.fetchall():
        tables[f"{ps}.{pt}"]["fks"][pc] = (f"{rs}.{rt}", rc)
    return tables, views


def _topo(tables):
    order, seen = [], set()

    def visit(t, stack=()):
        if t in seen or t in stack:
            return
        for parent, _ in tables[t]["fks"].values():
            if parent != t and parent in tables:
                visit(parent, stack + (t,))
        seen.add(t)
        order.append(t)
    for t in tables:
        visit(t)
    return order


# ---------------------------------------------------------------- data synthesis
def _value(col, i, rng, edge, parent_values, pool):
    name, ty = col["name"].lower(), col["type"]
    if col["nullable"] and not col["unique"] and rng.random() < (0.25 if edge else 0.08):
        return None
    if parent_values is not None:
        if edge and rng.random() < 0.1 and all(isinstance(v, int) for v in parent_values[:3]):
            return max(parent_values) + 500 + i  # orphan row: FK constraints are disabled in fixtures
        return rng.choice(parent_values) if parent_values else None
    if col["unique"] and ty in ("int", "bigint", "smallint", "tinyint"):
        return i + 1
    if pool and not col["unique"]:
        v = rng.choice(pool)
        if edge and isinstance(v, str) and rng.random() < 0.3:
            v = rng.choice([v.upper(), v + "  ", v.capitalize()])
        return v
    if ty == "bit":
        return rng.randint(0, 1)
    if ty in ("int", "bigint", "smallint", "tinyint"):
        hi = 255 if ty == "tinyint" else 1000
        return rng.choice([0, -1, 1, hi]) if edge and rng.random() < 0.3 else rng.randint(0, hi)
    if ty in ("decimal", "numeric", "money", "smallmoney"):
        scale = 4 if "money" in ty else col["scale"]
        top = 10 ** min((col["prec"] or 19) - scale, 6) - 1
        if edge and rng.random() < 0.3:
            return Decimal(rng.choice([0, -1, 100, 500, 1000, top])).quantize(Decimal(1).scaleb(-scale))
        return Decimal(str(round(rng.uniform(0, min(top, 5000)), scale)))
    if ty in ("float", "real"):
        return round(rng.uniform(-10 if edge else 0, 1000), 4)
    if ty == "date":
        if edge and rng.random() < 0.3:
            return rng.choice([date(2024, 2, 29), date(2024, 12, 31), date(2025, 1, 1), date(2025, 12, 31)])
        return date(2024, 1, 1) + timedelta(days=rng.randint(0, 730))
    if ty in ("datetime", "datetime2", "smalldatetime", "datetimeoffset"):
        d = date(2024, 1, 1) + timedelta(days=rng.randint(0, 730))
        t = time(23, 59, 59) if edge and rng.random() < 0.3 else time(rng.randint(0, 23), rng.randint(0, 59), rng.randint(0, 59))
        return datetime.combine(d, t)
    if ty == "time":
        return time(rng.randint(0, 23), rng.randint(0, 59))
    if ty == "uniqueidentifier":
        return str(uuid.UUID(int=rng.getrandbits(128)))
    if ty in ("varchar", "nvarchar", "char", "nchar", "text", "ntext"):
        n = col["len"] if col["len"] and col["len"] > 0 else 50
        if "email" in name:
            v = f"user{i}@{rng.choice(['acme.com', 'example.org', 'globex.io'])}"
        elif "status" in name:
            v = rng.choice(STATUSES)
        elif "name" in name:
            v = rng.choice(NAMES) + ("" if not col["unique"] else f" {i}")
        elif "code" in name or "sku" in name:
            v = "".join(rng.choices(string.ascii_uppercase + string.digits, k=min(n, 6)))
        else:
            v = rng.choice(["alpha", "beta", "gamma", "delta", "omega"]) + (f"_{i}" if col["unique"] else "")
        if edge and not col["unique"] and rng.random() < 0.3:
            v = rng.choice(["", " " + v, v + "   ", v.upper()])
        if col["unique"] and not v.endswith(str(i)):
            v = f"{v}_{i}"
        return v[:n]
    return None if col["nullable"] else 0


def _pools(base_rows):
    """Categorical value pools from the user's base data: columns with few distinct non-null values."""
    pools = {}
    for t, (cols, rows) in base_rows.items():
        for j, c in enumerate(cols):
            vals = sorted({r[j] for r in rows if r[j] is not None}, key=repr)
            if 0 < len(vals) <= 12 and len(rows) >= 2 * len(vals):
                pools[(t, c)] = vals
    return pools


def _synthesize(cur, tables, seed, edge, pools):
    """Insert synthesized rows (dropping rejected ones). Returns {table: [(col_names, row), ...]} of accepted inserts."""
    rng = random.Random(seed)
    accepted, key_values = {}, {}
    for t in _topo(tables):
        cur.execute(f"ALTER TABLE {t} NOCHECK CONSTRAINT ALL")
    for t in _topo(tables):
        cols = [c for c in tables[t]["cols"] if not c["skip"]]
        names = [c["name"] for c in cols]
        has_identity = any(c["identity"] for c in cols)
        # child tables get more rows than their parents so joins produce one-to-many fan-out
        n = (ROWS[edge] + (rng.randint(-5, 10) if not edge else 0)) * (1 + len(tables[t]["fks"]))
        rows = []
        for i in range(n):
            row = []
            for c in cols:
                fk = tables[t]["fks"].get(c["name"])
                parents = key_values.get(fk) if fk else None
                row.append(i + 1 if c["identity"] else _value(c, i, rng, edge, parents if fk else None, pools.get((t, c["name"]))))
            sql = (f"INSERT INTO {t} ({', '.join('[' + x + ']' for x in names)}) VALUES ({', '.join(literal(v) for v in row)})")
            try:
                cur.execute((f"SET IDENTITY_INSERT {t} ON; " if has_identity else "") + sql
                            + (f"; SET IDENTITY_INSERT {t} OFF" if has_identity else ""))
                rows.append(row)
            except pymssql.Error:
                if has_identity:
                    cur.execute(f"SET IDENTITY_INSERT {t} OFF")
        accepted[t] = (names, rows, has_identity)
        for j, c in enumerate(cols):
            key_values[(t, c["name"])] = [r[j] for r in rows if r[j] is not None]
    return accepted


def _fixture_sql(schema_sql, tables, accepted):
    lines = [schema_sql.rstrip(), "GO"]
    lines += [f"ALTER TABLE {t} NOCHECK CONSTRAINT ALL;" for t in _topo(tables)]
    lines.append("GO")
    for t, (names, rows, ident) in accepted.items():
        if not rows:
            continue
        cols = ", ".join("[" + x + "]" for x in names)
        if ident:
            lines.append(f"SET IDENTITY_INSERT {t} ON;")
        for k in range(0, len(rows), 50):
            lines.append(f"INSERT INTO {t} ({cols}) VALUES " + ",".join("(" + ", ".join(literal(v) for v in r) + ")" for r in rows[k:k + 50]) + ";")
        if ident:
            lines.append(f"SET IDENTITY_INSERT {t} OFF;")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------- procs
HEADER = re.compile(r"CREATE\s+(?:OR\s+ALTER\s+)?PROC(?:EDURE)?\s+((?:\[?\w+\]?\.)?\[?\w+\]?)(.*?)\bAS\b", re.I | re.S)
PARAM = re.compile(r"(@\w+)\s+(\w+(?:\s*\(\s*(?:\d+|max)\s*(?:,\s*\d+\s*)?\))?)(?:\s*=\s*('(?:[^']|'')*'|[-\w.]+))?(\s+OUT(?:PUT)?\b)?", re.I)


def parse_proc(sql):
    m = HEADER.search(re.sub(r"--[^\n]*", "", sql))
    if not m:
        raise ValueError("no CREATE PROCEDURE header found")
    name = m.group(1).replace("[", "").replace("]", "")
    params = []
    for p in PARAM.finditer(m.group(2)):
        default = p.group(3)
        if default is not None:
            default = None if default.upper() == "NULL" else default.strip("'")
        params.append({"name": p.group(1), "type": re.sub(r"\s+", "", p.group(2)).lower(),
                       "has_default": p.group(3) is not None, "default": default, "output": bool(p.group(4))})
    return (name if "." in name else f"dbo.{name}"), params


def _output_table(sql, source_tables):
    """A table the proc builds: SELECT INTO / CREATE TABLE of a non-temp table, or a source table it fully refreshes
    (TRUNCATE or unfiltered DELETE, then INSERT). None = the proc's output is the result set it returns."""
    body = preflight._strip_comments(sql)
    canon = preflight._canon
    created = {canon(t) for t in re.findall(r"\b(?:INTO|CREATE\s+TABLE)\s+((?:\[?\w+\]?\.)?\[?\w+\]?)", body, re.I)
               if not t.startswith("#") and not re.search(rf"INSERT\s+INTO\s+{re.escape(t)}\b", body, re.I)}
    if created:
        return sorted(created)[0]
    sources = {canon(t): t for t in source_tables}
    refreshed = {canon(t) for t in re.findall(r"\b(?:TRUNCATE\s+TABLE\s+|DELETE\s+(?:FROM\s+)?)((?:\[?\w+\]?\.)?\[?\w+\]?)\s*(?:;|$|\bINSERT\b)", body, re.I | re.M)}
    inserted = {canon(t) for t in re.findall(r"\bINSERT\s+(?:INTO\s+)?((?:\[?\w+\]?\.)?\[?\w+\]?)", body, re.I)}
    other_writes = {canon(t) for t in preflight.write_targets(body) if not t.startswith(("#", "@"))} - refreshed - inserted
    targets = (refreshed & inserted) - other_writes
    if len(targets) == 1 and next(iter(targets)) in sources:
        return sources[next(iter(targets))]
    return None


def _param_sets(params, base_rows, tables, proc_sql):
    """Derive up to 3 parameter sets from the base data: two existing values and one that matches nothing.
    Returns (sets, missing_param_names)."""
    inputs = [p for p in params if not p["output"]]
    if not inputs:
        return [{}], []
    referenced = [t for t in base_rows if re.search(rf"\b{re.escape(t.split('.')[-1])}\b", proc_sql, re.I)] or list(base_rows)
    candidates, missing = {}, []
    for p in inputs:
        key = p["name"][1:].lower()
        vals = None
        for t in referenced:  # exact column-name match first
            cols, rows = base_rows[t]
            for j, c in enumerate(cols):
                if c.lower() == key:
                    vals = sorted({r[j] for r in rows if r[j] is not None}, key=repr)
                    break
            if vals:
                break
        if not vals and p["type"] in ("date", "datetime", "datetime2", "smalldatetime"):
            as_date = p["type"] == "date"
            norm = lambda v: (v.date() if isinstance(v, datetime) else v) if as_date else (v if isinstance(v, datetime) else datetime.combine(v, time()))
            dates = sorted(norm(r[j]) for t in referenced for j, c in enumerate(base_rows[t][0])
                           for r in base_rows[t][1] if isinstance(r[j], (date, datetime)))
            if dates:
                lo, hi = dates[len(dates) // 4], dates[3 * len(dates) // 4]
                start = any(w in key for w in ("start", "from", "begin", "min"))
                vals = [lo if start else hi, dates[0] if start else dates[-1]]
        if not vals:
            if p["has_default"]:
                candidates[p["name"]] = [None]
                continue
            missing.append(p["name"])
            continue
        picks = [vals[len(vals) // 2], vals[0]]
        sample = vals[0]
        if isinstance(sample, int) and not isinstance(sample, bool):
            picks.append(max(vals) + 1000)
        elif isinstance(sample, str):
            picks.append("zz_no_match")
        candidates[p["name"]] = picks
    if missing:
        return [], missing
    sets = []
    for k in range(max(len(v) for v in candidates.values())):
        ps = {}
        for name, picks in candidates.items():
            v = picks[min(k, len(picks) - 1)]
            if v is not None:
                ps[name] = v.isoformat() if isinstance(v, (date, datetime)) else (str(v) if isinstance(v, Decimal) else v)
        if ps not in sets:
            sets.append(ps)
    return sets, []


# ---------------------------------------------------------------- build
def build(root: Path):
    name = root.name
    db = database_name(name)
    schema_sql = (root / "schema.sql").read_text()
    build_dir = root / "build"
    if build_dir.exists():
        shutil.rmtree(build_dir)
    (build_dir / "fixtures").mkdir(parents=True)

    conn = pymssql.connect(**CONN)
    cur = conn.cursor()
    try:
        _recreate(cur, db, schema_sql)
        tables, views = _introspect(cur)
        if not tables:
            raise SystemExit("schema.sql created no tables")

        variants = ["base"]
        data_file = root / "data.sql"
        if data_file.exists():
            for b in batches(data_file.read_text()):
                cur.execute(b)
            base_sql = schema_sql.rstrip() + "\nGO\n" + data_file.read_text()
            print("base: data.sql")
        else:
            accepted = _synthesize(cur, tables, 1, False, {})
            base_sql = _fixture_sql(schema_sql, tables, accepted)
            print("base: synthesized", {t: len(r[1]) for t, r in accepted.items()})
        (build_dir / "fixtures" / "base.sql").write_text(base_sql)
        base_rows = {}
        for t in list(tables) + views:
            cur.execute(f"SELECT * FROM {t}")
            base_rows[t] = ([d[0] for d in cur.description], cur.fetchall())
        pools = _pools({t: base_rows[t] for t in tables}) if data_file.exists() else {}

        for v, (seed, edge) in VARIANTS.items():
            _recreate(cur, db, schema_sql)
            accepted = _synthesize(cur, tables, seed, edge, pools)
            (build_dir / "fixtures" / f"{v}.sql").write_text(_fixture_sql(schema_sql, tables, accepted))
            variants.append(v)
            print(f"{v}: synthesized", {t: len(r[1]) for t, r in accepted.items()})
    finally:
        conn.close()

    source_tables = list(tables) + views
    procs_out = build_dir / "procs"
    for n, f in enumerate(sorted((root / "procs").glob("*.sql")), 1):
        proc_sql = f.read_text()
        try:
            proc_name, params = parse_proc(proc_sql)
        except ValueError as e:
            print(f"skip {f.name}: {e}")
            continue
        slug = re.sub(r"\W+", "_", proc_name.split(".")[-1]).lower()
        meta = {"id": n, "slug": slug, "proc": proc_name, "file": f.name, "difficulty": "unknown", "tags": [],
                "output": _output_table(proc_sql, source_tables), "params": params}
        pfile = f.with_suffix(".params.json")
        if pfile.exists():
            meta["param_sets"] = json.loads(pfile.read_text())
            meta["param_source"] = pfile.name
        else:
            sets, missing = _param_sets(params, base_rows, tables, proc_sql)
            meta["param_sets"], meta["param_source"] = sets, "derived from base data"
            if missing:
                meta["blocker"] = ["no_param_values", f"Could not derive test values for {', '.join(missing)}; add procs/{f.stem}.params.json."]
        d = procs_out / f"{n:03d}_{slug}"
        d.mkdir(parents=True)
        (d / "proc.sql").write_text(proc_sql)
        (d / "meta.json").write_text(json.dumps(meta, indent=1, default=str))
        print(f"proc {proc_name}: output={meta['output'] or 'result set'} params={[p['name'] for p in params]} sets={meta['param_sets']}")

    (build_dir / "project.json").write_text(json.dumps({"name": name, "database": db, "tables": source_tables, "variants": variants}, indent=1))
    print(f"built {build_dir}: {len(source_tables)} source tables, {len(variants)} datasets")


if __name__ == "__main__":
    build(Path(sys.argv[1]).resolve())
