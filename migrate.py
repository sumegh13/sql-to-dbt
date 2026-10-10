"""Migrate one proc: triage -> translate -> dbt run -> row-by-row diff -> retry with feedback."""
import json
import traceback
from pathlib import Path
from harness import legacy, dbt_runner, diff, translate, preflight

MAX_ATTEMPTS = 3


def _canon(res):
    cols, rows = res
    return cols, sorted(map(repr, rows))


def _human(base, category, reason, history=(), sql=None):
    r = {**base, "status": "needs_human", "reason_category": category, "reason": reason,
         "attempts": len(history), "history": list(history)}
    if sql:
        r["model_sql"] = sql
    return r


def migrate(proc_dir: Path):
    meta = json.loads((proc_dir / "meta.json").read_text())
    base = {"id": meta["id"], "slug": meta["slug"], "difficulty": meta["difficulty"], "tags": meta["tags"]}
    try:
        return _migrate(proc_dir, meta, base)
    except Exception as e:  # one broken proc must not kill the batch
        return {**base, "status": "error", "reason_category": "harness_error", "reason": f"{type(e).__name__}: {e}",
                "trace": traceback.format_exc()[-2000:], "attempts": 0, "history": []}


def _migrate(proc_dir, meta, base):
    proc_sql = (proc_dir / "proc.sql").read_text()

    flags = preflight.triage(proc_sql, meta["output"], legacy.SOURCE_TABLES)
    if flags:
        return _human(base, *flags[0])
    schema, sources, expected = legacy.run_proc(proc_sql, meta["proc"], meta["output"])
    _, _, again = legacy.run_proc(proc_sql, meta["proc"], meta["output"])
    if _canon(expected) != _canon(again):  # objective determinism check
        return _human(base, "nondeterministic", "Legacy proc returns different output on identical input.")

    dbt_runner.load_sources(schema, sources)
    dbt_runner.write_sources_yml(list(sources))
    history, sql, explanation, calls = [], None, None, []
    for attempt in range(1, MAX_ATTEMPTS + 1):
        t = translate.translate(proc_dir, proc_sql, schema, expected[0], history)
        if t["usage"]:
            calls.append(t["usage"])
        explanation = explanation or t["explanation"]
        extra = {"explanation": explanation, "llm_calls": calls, "cost_usd": round(sum(c["cost_usd"] for c in calls), 6)}
        if t["sql"] is None:
            if translate.MODE == "reference":
                return {**_human(base, "no_translation", "Translator produced no model.", history), **extra}
            history.append({"attempt": attempt, "sql": "", "status": "bad_response", "detail": t["error"]})
            continue
        sql = t["sql"]
        got, err = dbt_runner.run_model(meta["slug"], sql)
        if err:
            history.append({"attempt": attempt, "sql": sql, "status": "dbt_error", "detail": err})
            continue
        res = diff.compare(*expected, *got)
        history.append({"attempt": attempt, "sql": sql, "status": "match" if res["equivalent"] else "diff", "detail": res})
        if res["equivalent"]:
            return {**base, "status": "verified", "attempts": attempt, "rows": res["legacy_rows"], "model_sql": sql,
                    "history": history, **extra}
    return {**_human(base, "unresolved_diff", f"Outputs still differ after {MAX_ATTEMPTS} attempts.", history, sql), **extra}
