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
    if env.exists():
        for line in env.read_text().splitlines():
            k, sep, v = line.strip().partition("=")
            if sep and not k.startswith("#") and v and k not in os.environ:
                os.environ[k] = v


_load_dotenv()
MODE = os.environ.get("TRANSLATOR") or ("claude" if os.environ.get("ANTHROPIC_API_KEY") else "reference")

SYSTEM = """You migrate legacy SQL Server stored procedures to dbt models that run on DuckDB.

Each procedure builds exactly one output table. Write ONE dbt model: a single SELECT statement (CTEs allowed) whose result has exactly the same rows as that output table, run against the same source data.

Rules for the model:
- Read sources only via {{ source('legacy', '<table>') }}. The legacy table dbo.orders is {{ source('legacy', 'orders') }}.
- No trailing semicolon, no DDL/DML, no file or network access, no Jinja beyond source().
- Output columns: exactly the names and order given, nothing extra.
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

Respond in exactly this format:
<explanation>2-4 plain-English sentences on what the procedure does, for a business reader.</explanation>
<sql>
the dbt model
</sql>"""


def _schema_text(schema):
    return "\n".join(f"{t}({', '.join(f'{c} {ty}' for c, ty in cols)})" for t, cols in schema.items())


def _feedback(history):
    parts = []
    for h in history[-2:]:  # last two attempts keep the prompt small
        detail = h["detail"] if isinstance(h["detail"], str) else json.dumps(h["detail"], default=str)
        parts.append(f"Attempt {h['attempt']} ({h['status']}):\n<sql>\n{h['sql']}\n</sql>\nResult: {detail[:3000]}")
    return ("\n\nYour previous attempts did not match the legacy output. The model is checked against several "
            "source datasets (base, random seeds, and an 'edge' set with NULLs, trailing spaces, ties, boundary values, "
            "orphan rows); 'dataset' names the one that failed. 'in_legacy_not_new' rows are what the "
            "procedure produced that your model did not; 'in_new_not_legacy' rows are what your model produced instead. "
            "Find the semantic difference and fix it.\n\n" + "\n\n".join(parts))


def _claude(proc_sql, schema, output_columns, history):
    import anthropic
    client = anthropic.Anthropic()
    prompt = (f"Source tables (SQL Server types):\n{_schema_text(schema)}\n\n"
              f"Output columns, in order: {', '.join(output_columns)}\n\n"
              f"Procedure:\n<tsql>\n{proc_sql}\n</tsql>")
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
    return {"sql": sql, "explanation": expl.group(1) if expl else None, "usage": usage,
            "error": None if sql else f"no <sql> block in response (stop_reason={resp.stop_reason})"}


def translate(proc_dir: Path, proc_sql: str, schema: dict, output_columns: list[str], history: list[dict]) -> dict:
    """Returns {"sql": str|None, "explanation": str|None, "usage": dict|None, "error": str|None}."""
    if MODE == "reference":
        f = proc_dir / "reference_model.sql"
        return {"sql": f.read_text() if f.exists() else None, "explanation": None, "usage": None, "error": None}
    return _claude(proc_sql, schema, output_columns, history)
