"""Static triage: constructs that can't be verified/migrated automatically."""
import re

RULES = [
    ("dynamic_sql", r"\bsp_executesql\b|\bEXEC(?:UTE)?\s*\(\s*@|\bEXEC(?:UTE)?\s+@\w+\b(?!\s*=)",
     "Builds SQL at runtime; the real query shape is only known by executing it. Needs a human to pin down the intended static SQL."),
    ("nondeterministic", r"\bNEWID\s*\(|\bRAND\s*\(|\bGETDATE\s*\(|\bGETUTCDATE\s*\(|\bSYSDATETIME\s*\(|\bCURRENT_TIMESTAMP\b",
     "Output depends on time/randomness, so old-vs-new equivalence can't be proven row by row."),
    ("external_side_effect", r"\bxp_cmdshell\b|\bsp_send_dbmail\b|\bsp_OA\w+|\bOPENROWSET\b|\bOPENQUERY\b|\bBULK\s+INSERT\b",
     "Touches systems outside the warehouse."),
    ("calls_other_proc", r"\bEXEC(?:UTE)?\s+(?!sp_executesql\b)(?:\[?\w+\]?\.)?\[?usp_\w+",
     "Calls another stored procedure; migrate the dependency first or inline it."),
]
# Statements that write to an existing table. Anchored on word boundaries, not line starts.
WRITE = re.compile(r"\b(?:INSERT\s+(?:INTO\s+)?|UPDATE\s+|DELETE\s+(?:FROM\s+)?|MERGE\s+(?:INTO\s+)?|TRUNCATE\s+TABLE\s+|DROP\s+TABLE\s+(?:IF\s+EXISTS\s+)?)"
                   r"((?:\[?\w+\]?\.)?\[?\w+\]?)", re.I)


def _strip_comments(sql):
    return re.sub(r"--[^\n]*", "", re.sub(r"/\*.*?\*/", "", sql, flags=re.S))


def _canon(name):
    name = name.replace("[", "").replace("]", "").lower()
    return name if "." in name else f"dbo.{name}"


def triage(proc_sql: str, output_table: str, source_tables: list[str]):
    """Returns list of (category, reason). Empty list = automatable."""
    sql = _strip_comments(proc_sql)
    found = [(c, why) for c, pat, why in RULES if re.search(pat, sql, re.I)]
    sources = {_canon(t) for t in source_tables}
    mutated = sorted({_canon(m) for m in WRITE.findall(sql) if not m.startswith(("#", "@"))} & sources - {_canon(output_table)})
    if mutated:
        found.append(("mutates_source", f"Modifies existing tables in place ({', '.join(mutated)}); a dbt model can only build new relations, so this needs a design decision (incremental/snapshot/ops job)."))
    return found
