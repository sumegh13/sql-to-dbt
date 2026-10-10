"""Migrate one proc: triage -> translate -> dbt run -> row-by-row diff -> retry with feedback."""
import json
from pathlib import Path
from harness import legacy, dbt_runner, diff, translate, preflight

MAX_ATTEMPTS = 3


def _canon(res):
    cols, rows = res
    return cols, sorted(map(repr, rows))


def migrate(proc_dir: Path):
    meta = json.loads((proc_dir / "meta.json").read_text())
    base = {"id": meta["id"], "slug": meta["slug"], "difficulty": meta["difficulty"], "tags": meta["tags"]}
    proc_sql = (proc_dir / "proc.sql").read_text()

    flags = preflight.triage(proc_sql, meta["output"])
    sources, expected = legacy.run_proc(proc_sql, meta["proc"], meta["output"])
    if not flags:  # objective determinism check: run legacy twice, outputs must be identical
        _, again = legacy.run_proc(proc_sql, meta["proc"], meta["output"])
        if _canon(expected) != _canon(again):
            flags = [("nondeterministic", "Legacy proc returns different output on identical input.")]
    if flags:
        return {**base, "status": "needs_human", "reason_category": flags[0][0], "reason": flags[0][1], "attempts": 0, "history": []}

    dbt_runner.load_sources(sources)
    dbt_runner.write_sources_yml(list(sources))
    model = meta["slug"]
    feedback, history = None, []
    for attempt in range(1, MAX_ATTEMPTS + 1):
        sql = translate.translate(proc_dir, proc_sql, feedback)
        if sql is None:
            return {**base, "status": "needs_human", "reason_category": "no_translation", "reason": "Translator produced no model.", "attempts": attempt - 1, "history": history}
        got, err = dbt_runner.run_model(model, sql)
        if err:
            feedback = f"dbt error:\n{err}"
            history.append({"attempt": attempt, "status": "dbt_error", "detail": err})
            continue
        res = diff.compare(*expected, *got)
        history.append({"attempt": attempt, "status": "match" if res["equivalent"] else "diff", "detail": res})
        if res["equivalent"]:
            return {**base, "status": "verified", "attempts": attempt, "rows": res["legacy_rows"], "model_sql": sql, "history": history}
        feedback = json.dumps(res, default=str)
    return {**base, "status": "needs_human", "reason_category": "unresolved_diff",
            "reason": f"Outputs still differ after {MAX_ATTEMPTS} attempts.", "attempts": MAX_ATTEMPTS, "model_sql": sql, "history": history}
