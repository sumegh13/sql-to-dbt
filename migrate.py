"""Migrate one proc: triage -> translate -> dbt run -> row-by-row diff on every dataset -> retry with feedback.

Procs that triage flags still get a proposal (model + assumptions + reviewer questions), verified as far as the
blocker allows, but they always end as needs_human."""
import json
import traceback
from pathlib import Path
from harness import legacy, dbt_runner, diff, translate, preflight

MAX_ATTEMPTS = 3
SMALL_TABLE_ROWS = 5  # tables this small are shown to the model when a proc is blocked (e.g. config tables)


def _canon(res):
    cols, rows = res
    return cols, sorted(map(repr, rows))


def _human(base, category, reason, history=(), sql=None):
    r = {**base, "status": "needs_human", "reason_category": category, "reason": reason,
         "attempts": len(history), "history": list(history)}
    if sql:
        r["model_sql"] = sql
    return r


def _shape_compare(legacy_cols, legacy_rows, new_cols, new_rows):
    """For nondeterministic procs: same columns and same row count is all that can be checked."""
    issues = []
    if [c.lower() for c in legacy_cols] != [c.lower() for c in new_cols]:
        issues.append({"column_mismatch": {"legacy": legacy_cols, "new": new_cols}})
    if len(legacy_rows) != len(new_rows):
        issues.append(f"row count differs: legacy={len(legacy_rows)} new={len(new_rows)}")
    return {"equivalent": not issues, "legacy_rows": len(legacy_rows), "new_rows": len(new_rows), "issues": issues}


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
    blocker = flags[0] if flags else None
    if blocker and translate.MODE == "reference":
        return _human(base, *blocker)

    expected = {}
    for v in legacy.VARIANTS:
        schema, sources, out = legacy.run_proc(proc_sql, meta["proc"], meta["output"], v)
        if not (blocker and blocker[0] == "nondeterministic"):
            _, _, again = legacy.run_proc(proc_sql, meta["proc"], meta["output"], v)
            if _canon(out) != _canon(again):  # objective determinism check
                blocker = ("nondeterministic", f"Legacy proc returns different output on identical input (dataset {v}).")
        dbt_runner.load_sources(schema, sources, v)
        expected[v] = out
        if v == "base":
            base_schema, base_sources = schema, sources
    dbt_runner.write_sources_yml(list(base_sources))
    small = {t: (cols, rows) for t, (cols, rows) in base_sources.items() if len(rows) <= SMALL_TABLE_ROWS} if blocker else None
    compare = _shape_compare if blocker and blocker[0] == "nondeterministic" else diff.compare

    ok, sql, history, datasets, extra, last = _attempts(proc_dir, meta, proc_sql, base_schema, expected, compare, blocker, small)

    if blocker:
        r = _human(base, *blocker, history, sql)
        r["proposal"] = {
            "model_sql": sql, "assumptions": last.get("assumptions"), "questions": last.get("questions"),
            "not_migrated": last.get("not_migrated"),
            "verification": (("shape only (columns + row count)" if compare is _shape_compare else "output rows match")
                             + f" on {len(datasets)} datasets") if ok else "not verified: " + (history[-1]["status"] if history else "no model"),
        }
        return {**r, **extra}
    if ok:
        return {**base, "status": "verified", "attempts": len(history), "rows": sum(datasets.values()), "datasets": datasets,
                "model_sql": sql, "history": history, **extra}
    if sql is None and translate.MODE == "reference":
        return {**_human(base, "no_translation", "Translator produced no model.", history), **extra}
    return {**_human(base, "unresolved_diff", f"Outputs still differ after {MAX_ATTEMPTS} attempts.", history, sql), **extra}


def _attempts(proc_dir, meta, proc_sql, schema, expected, compare, blocker, small):
    """Translate -> run -> compare on every dataset, up to MAX_ATTEMPTS.
    Returns (ok, sql, history, datasets, extra, last_translation)."""
    history, sql, explanation, calls, t = [], None, None, [], {}
    extra = {}
    for attempt in range(1, MAX_ATTEMPTS + 1):
        t = translate.translate(proc_dir, proc_sql, schema, expected["base"][0], history, blocker, small)
        if t["usage"]:
            calls.append(t["usage"])
        explanation = explanation or t["explanation"]
        extra = {"explanation": explanation, "llm_calls": calls, "cost_usd": round(sum(c["cost_usd"] for c in calls), 6)}
        if t["sql"] is None:
            if translate.MODE == "reference":
                break
            history.append({"attempt": attempt, "sql": "", "status": "bad_response", "detail": t["error"]})
            continue
        sql = t["sql"]
        got, err = dbt_runner.run_model(meta["slug"], sql)
        if err:
            history.append({"attempt": attempt, "sql": sql, "status": "dbt_error", "detail": err})
            continue
        datasets, failed = {}, None
        for v in legacy.VARIANTS:
            if v != "base":
                got, err = dbt_runner.run_compiled(meta["slug"], v)
                if err:
                    failed = {"attempt": attempt, "sql": sql, "status": "runtime_error", "detail": f"dataset {v}: {err}"}
                    break
            res = compare(*expected[v], *got)
            if not res["equivalent"]:
                failed = {"attempt": attempt, "sql": sql, "status": "diff", "detail": {"dataset": v, **res}}
                break
            datasets[v] = res["legacy_rows"]
        if failed:
            history.append(failed)
            continue
        history.append({"attempt": attempt, "sql": sql, "status": "match", "detail": {"datasets": datasets}})
        return True, sql, history, datasets, extra, t
    return False, sql, history, {}, extra, t
