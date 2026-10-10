"""Translation step: legacy T-SQL proc -> single dbt SELECT model on DuckDB.

TRANSLATOR=claude (default when ANTHROPIC_API_KEY is set) calls Claude; TRANSLATOR=reference serves
each proc's checked-in reference_model.sql. Each call is stateless: prior attempts and their dbt
error / row diff are passed back in the prompt so the model can debug its own output.
"""
import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODEL = os.environ.get("CLAUDE_MODEL", "claude-haiku-5-5")
# USD per 1M tokens (input, output) for cost tracking
PRICES = {"claude-haiku-5-5": (0.10, 0.50), "claude-sonnet-5-5": (2.00, 10.00), "claude-opus-5-5": (4.00, 20.00)}


def _load_dotenv():
    env = ROOT / ".env"
    if env.exists() and not os.environ.get("SQLTODBT_NO_DOTENV"):
        for line in env.read_text().splitlines():
            k, sep, v = line.strip().partition("=")
            if sep and not k.startswith("#") and v and k not in os.environ:
                os.environ[k] = v


_load_dotenv()


def mode() -> str:
    """Checked per call, so a key supplied after startup (e.g. per web job) takes effect."""
    return os.environ.get("TRANSLATOR") or ("claude" if os.environ.get("ANTHROPIC_API_KEY") else "reference")

SYSTEM = """You migrate legacy SQL Server stored procedures to dbt models that run on DuckDB.

Each procedure produces one output: a table it builds, or the result set it returns. Write ONE dbt model: a single SELECT statement (CTEs allowed) whose result has exactly the same rows as that output, run against the same source data.

Rules for the model:
- Read sources only via {{ source('legacy', '<name>') }}, using the source name given for each legacy table.
- No trailing semicolon, no DDL/DML, no file or network access, no Jinja beyond source().
- Output columns: include every output column, with exactly the names given.
- Row order does not matter. Duplicate row counts do.
- Convert cursors, WHILE loops, temp tables, table variables, UPDATE/DELETE on temp tables and MERGE into set-based SQL (window functions, CTEs, joins).

Preserve T-SQL semantics exactly. Common traps:
- The default collation is case-insensitive: 'abc' = 'ABC' is true in comparisons, IN lists, PIVOT, GROUP BY and joins. DuckDB is case-sensitive.
- ISNULL(a, b) returns a's type, so b is truncated to a's length; COALESCE does not truncate.
- int / int is integer division in T-SQL (DuckDB: use //). Decimal arithmetic keeps fixed scale; storing into DECIMAL(p,s) rounds.
- String + NULL is NULL. LEN ignores trailing spaces. Trailing spaces are ignored in comparisons.
- DATEDIFF counts boundaries crossed. DATENAME(weekday) returns full English names. EOMONTH is last_day.
- TOP n without ORDER BY is arbitrary. TOP n WITH TIES includes ties.
- PIVOT with ISNULL gives 0 for missing combinations. CROSS APPLY drops outer rows with no match; OUTER APPLY keeps them.
- Aggregates over DECIMAL columns may keep the input scale in DuckDB; cast to DOUBLE where T-SQL returns float or a higher-scale value.

Parameterized procedures: a dbt model has no parameters. Write the model for ALL parameter values at once, and add a
<param_filter> block: a DuckDB boolean expression over your model's columns, using @ParamName placeholders, that selects
the rows the procedure returns for given parameter values (e.g. customer_id = @CustomerID AND order_date >= @StartDate).
Keep any columns the filter needs in the model output, even if they are not output columns; the harness projects to the
output columns after filtering. Mirror the procedure's handling of NULL parameters (e.g. "@X IS NULL OR col = @X").
If the procedure's rows cannot be expressed as a row filter over one parameter-free model (e.g. parameters restrict
which rows feed an aggregate, so the totals themselves depend on the parameter values), do not guess: output
<param_filter>NOT_FILTERABLE: one sentence on why</param_filter>; the harness then asks you for a dbt-vars version.
Parameters with defaults may be omitted by callers; the filter sees the default value then.

Respond in exactly this format:
<explanation>2-4 plain-English sentences on what the procedure does, for a business reader.</explanation>
<sql>
the dbt model
</sql>"""


def _schema_text(schema, source_name):
    return "\n".join(f"{t} -> source('legacy', '{source_name(t)}'): ({', '.join(f'{c} {ty}' for c, ty in cols)})"
                     for t, cols in schema.items())


def _feedback(history):
    parts = []
    for h in history[-2:]:  # last two attempts keep the prompt small
        detail = h["detail"] if isinstance(h["detail"], str) else json.dumps(h["detail"], default=str)
        pf = f"\n<param_filter>{h['param_filter']}</param_filter>" if h.get("param_filter") else ""
        parts.append(f"Attempt {h['attempt']} ({h['status']}):\n<sql>\n{h['sql']}\n</sql>{pf}\nResult: {detail[:3000]}")
    return ("\n\nYour previous attempts did not match the legacy output. The model is checked against several "
            "source datasets (base, random seeds, and an 'edge' set with NULLs, trailing spaces, ties, boundary values, "
            "orphan rows) and, for parameterized procedures, several parameter sets; 'dataset' and 'params' name the run that failed. 'in_legacy_not_new' rows are what the "
            "procedure produced that your model did not; 'in_new_not_legacy' rows are what your model produced instead. "
            "Find the semantic difference and fix it.\n\n" + "\n\n".join(parts))


def _blocker_text(blocker, small_tables):
    category, reason = blocker
    shape = (" Its output cannot be compared row by row, so it will only be checked for identical column names and row count."
             " Make your model deterministic and state how in your assumptions." if category == "nondeterministic" else
             " Its output table will still be compared row by row against the procedure, so reproduce the output table exactly.")
    data = "".join(f"\nCurrent contents of {t} (columns: {', '.join(c)}): {rows}" for t, (c, rows) in small_tables.items())
    return (f"\n\nThis procedure was flagged for human review ({category}): {reason}{shape}{data}\n\n"
            "Still write the best dbt model you can. After the <sql> block, also output:\n"
            "<assumptions>bullet list of assumptions your model relies on</assumptions>\n"
            "<questions>bullet list of questions a reviewer must answer before this ships</questions>\n"
            "<not_migrated>procedure behaviour your model does not reproduce (side effects, writes to other tables), or 'none'</not_migrated>")


VARS_MODE = """Parameter mode: dbt vars. A row filter cannot express this procedure, so pass the parameters as dbt vars instead.
Reference parameter @X as {{ var('X') }} (name without @). A var renders the parameter's plain text, e.g. 2024-01-02 or 5,
and a NULL parameter renders as the empty string. Write it like a literal: cast('{{ var("StartDate") }}' as date),
cast(nullif('{{ var("Category") }}', '') as varchar); numbers may be cast the same way. Do not output a <param_filter> block."""


def _claude(proc_sql, schema, output_columns, history, blocker=None, small_tables=None, params=None, source_name=None,
            param_mode="filter"):
    import anthropic
    client = anthropic.Anthropic()
    source_name = source_name or (lambda t: t.rpartition(".")[2])
    prompt = (f"Source tables (legacy name -> dbt source, SQL Server types):\n{_schema_text(schema, source_name)}\n\n"
              f"Output columns, in order: {', '.join(output_columns)}\n\n")
    if params:
        prompt += ("Parameters: " + ", ".join(f"{p['name']} {p['type']}" + (f" = {p['default']}" if p.get("default") is not None else "")
                                              for p in params)
                   + (". Include a <param_filter> block.\n\n" if param_mode == "filter" else f".\n{VARS_MODE}\n\n"))
    prompt += f"Procedure:\n<tsql>\n{proc_sql}\n</tsql>"
    if blocker:
        prompt += _blocker_text(blocker, small_tables or {})
    if history:
        prompt += _feedback(history)
    resp = client.messages.create(
        model=MODEL,
        max_tokens=16000,
        system=SYSTEM,
        output_config={"effort": "medium"},
        messages=[{"role": "user", "content": prompt}],
    )
    u = resp.usage
    usage = {"model": MODEL, "input_tokens": u.input_tokens, "output_tokens": u.output_tokens,
             "cache_write_tokens": u.cache_creation_input_tokens or 0, "cache_read_tokens": u.cache_read_input_tokens or 0}
    pin, pout = PRICES.get(MODEL, (0, 0))
    billed_in = usage["input_tokens"] + 1.25 * usage["cache_write_tokens"] + 0.1 * usage["cache_read_tokens"]
    usage["cost_usd"] = round((billed_in * pin + usage["output_tokens"] * pout) / 1e6, 6)
    if resp.stop_reason == "refusal":
        return {"sql": None, "explanation": None, "usage": usage, "error": "model refused"}
    text = "".join(b.text for b in resp.content if b.type == "text")
    sql = re.search(r"<sql>\s*(.*?)\s*</sql>", text, re.S)
    expl = re.search(r"<explanation>\s*(.*?)\s*</explanation>", text, re.S)
    sql = sql.group(1) if sql else None
    if sql:
        sql = re.sub(r"^```\w*\s*|\s*```$", "", sql).strip().rstrip(";")
    tag = lambda name: (m.group(1).strip() if (m := re.search(rf"<{name}>\s*(.*?)\s*</{name}>", text, re.S)) else None)
    return {"sql": sql, "explanation": expl.group(1) if expl else None, "usage": usage,
            "param_filter": tag("param_filter"), "assumptions": tag("assumptions"), "questions": tag("questions"), "not_migrated": tag("not_migrated"),
            "error": None if sql else f"no <sql> block in response (stop_reason={resp.stop_reason})"}


def translate(proc_dir: Path, proc_sql: str, schema: dict, output_columns: list[str], history: list[dict],
              blocker: tuple[str, str] | None = None, small_tables: dict | None = None,
              params: list[dict] | None = None, source_name=None, param_mode: str = "filter") -> dict:
    """Returns {"sql", "explanation", "usage", "error"} (+ "assumptions", "questions", "not_migrated" when blocker is set).
    blocker = (category, reason) from triage: ask for a proposal for human review instead of a plain translation."""
    if mode() == "reference":
        f = proc_dir / "reference_model.sql"
        pf = proc_dir / "reference_filter.txt"
        return {"sql": f.read_text() if f.exists() else None, "param_filter": pf.read_text().strip() if pf.exists() else None,
                "explanation": None, "usage": None, "error": None}
    return _claude(proc_sql, schema, output_columns, history, blocker, small_tables, params, source_name, param_mode)
