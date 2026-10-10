"""Static triage: constructs that can't be verified/migrated automatically."""
import re

RULES = [
    ("dynamic_sql", r"\bsp_executesql\b|\bEXEC(?:UTE)?\s*\(\s*@", "Builds SQL at runtime; the real query shape is only known by executing it. Needs a human to pin down the intended static SQL."),
    ("nondeterministic", r"\bNEWID\s*\(|\bRAND\s*\(|\bGETDATE\s*\(|\bSYSDATETIME\s*\(|\bCURRENT_TIMESTAMP\b", "Output depends on time/randomness, so old-vs-new equivalence can't be proven row by row."),
    ("external_side_effect", r"\bxp_cmdshell\b|\bsp_send_dbmail\b|\bsp_OACreate\b|\bOPENROWSET\b", "Touches systems outside the warehouse."),
]
MUTATION = re.compile(r"^\s*(?:DELETE\s+(?:FROM\s+)?|UPDATE\s+|INSERT\s+INTO\s+|TRUNCATE\s+TABLE\s+)(dbo\.\w+)", re.I | re.M)


def triage(proc_sql: str, output_table: str):
    """Returns list of (category, reason). Empty list = automatable."""
    sql = re.sub(r"--[^\n]*", "", proc_sql)
    found = [(c, why) for c, pat, why in RULES if re.search(pat, sql, re.I)]
    out = output_table.lower()
    mutated = sorted({m.lower() for m in MUTATION.findall(sql)} - {out})
    # tables the proc itself creates via CREATE TABLE / SELECT INTO are not "source" mutations
    mutated = [m for m in mutated if not re.search(rf"INTO\s+{re.escape(m)}\b|CREATE\s+TABLE\s+{re.escape(m)}\b", sql, re.I)]
    if mutated:
        found.append(("mutates_source", f"Modifies existing tables in place ({', '.join(mutated)}); a dbt model can only build new relations, so this needs a design decision (incremental/snapshot/ops job)."))
    return found
