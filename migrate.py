"""Migrate one proc: triage -> translate -> dbt run -> row-by-row diff on every dataset and parameter set -> retry.

The proc's output is the table named in meta.json ("output"), or else the result set it returns. Parameterized procs
are translated to one parameter-free model plus a row filter; each parameter set is checked separately.
Procs that triage flags still get a proposal (model + assumptions + reviewer questions), verified as far as the
blocker allows, but they always end as needs_human."""
import json
import traceback
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from harness import dbt_runner, diff, preflight, translate
from harness.legacy import Legacy
from harness.project import Project

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


def _coerce(value, tsql_type):
    """JSON param value -> Python value matching the parameter's declared type."""
    if value is None or not isinstance(value, str):
        return value
    t = tsql_type.lower()
    if t in ("int", "bigint", "smallint", "tinyint", "bit"):
        return int(value)
    if t.startswith(("decimal", "numeric", "money", "float", "real")):
        return Decimal(value)
    if t == "date":
        return date.fromisoformat(value)
    if t.startswith(("datetime", "smalldatetime")):
        return datetime.fromisoformat(value)
    return value


def migrate(project: Project, proc_dir: Path):
    meta = json.loads((proc_dir / "meta.json").read_text())
    base = {"id": meta["id"], "slug": meta["slug"], "difficulty": meta.get("difficulty", "unknown"), "tags": meta.get("tags", [])}
    try:
        return _migrate(project, proc_dir, meta, base)
    except Exception as e:  # one broken proc must not kill the batch
        return {**base, "status": "error", "reason_category": "harness_error", "reason": f"{type(e).__name__}: {e}",
                "trace": traceback.format_exc()[-2000:], "attempts": 0, "history": []}


def _run_legacy(project, meta, proc_sql, param_sets, check_determinism):
    """Returns (schema, base_sources, expected, problem). expected[(variant, i)] = (cols, rows)."""
    expected, problem, schema, base_sources = {}, None, None, None
    with Legacy(project) as L:
        for v in project.variants:
            L.load(v)
            L.create_proc(proc_sql)
            sources = L.sources()
            if schema is None:
                schema, base_sources = L.schema(), sources
            dbt_runner.load_sources(schema, sources, v, project.source_name)
            for i, ps in enumerate(param_sets):
                outs = []
                for _ in range(2 if check_determinism else 1):
                    if L.loaded is None:  # proc broke out of our transaction; reload clean data
                        L.load(v)
                        L.create_proc(proc_sql)
                    r = L.run(meta["proc"], ps, meta.get("output"))
                    if r["table"] is not None:
                        outs.append(r["table"])
                    elif len(r["result_sets"]) == 1:
                        outs.append(r["result_sets"][0])
                    elif not r["result_sets"]:
                        return schema, base_sources, expected, ("no_output", "Procedure neither returns a result set nor builds a known output table; it only changes data.")
                    else:
                        outs.append(r["result_sets"][-1])
                        problem = problem or ("multiple_result_sets", f"Procedure returns {len(r['result_sets'])} result sets; a dbt model produces one. The proposal covers the last one.")
                if len(outs) == 2 and _canon(outs[0]) != _canon(outs[1]):
                    problem = ("nondeterministic", f"Legacy proc returns different output on identical input (dataset {v}).")
                expected[(v, i)] = outs[0]
    return schema, base_sources, expected, problem


def _migrate(project, proc_dir, meta, base):
    proc_sql = (proc_dir / "proc.sql").read_text()
    params = meta.get("params", [])
    raw_sets = meta.get("param_sets") or [{}]
    param_sets = [{k: _coerce(v, next((p["type"] for p in params if p["name"].lower() == k.lower()), "")) for k, v in ps.items()}
                  for ps in raw_sets]

    flags = preflight.triage(proc_sql, meta.get("output") or "", project.tables)
    if meta.get("blocker"):  # set by intake, e.g. no parameter values could be derived
        flags.insert(0, tuple(meta["blocker"]))
    if any(p.get("output") for p in params):
        flags.append(("output_parameters", "Returns values through OUTPUT parameters; a dbt model can only return rows."))
    blocker = flags[0] if flags else None
    if blocker and (blocker[0] == "no_param_values" or translate.mode() == "reference"):
        return _human(base, *blocker)

    nondet = bool(blocker and blocker[0] == "nondeterministic")
    schema, base_sources, expected, problem = _run_legacy(project, meta, proc_sql, param_sets, not nondet)
    if problem and problem[0] == "no_output":
        return _human(base, *problem)
    blocker = blocker or problem
    if blocker and translate.mode() == "reference":
        return _human(base, *blocker)

    dbt_runner.write_sources_yml([project.source_name(t) for t in base_sources])
    dbt_runner.use_for_dbt(project.variants[0])
    small = {t: (c, r) for t, (c, r) in base_sources.items() if len(r) <= SMALL_TABLE_ROWS} if blocker else None
    compare = _shape_compare if blocker and blocker[0] == "nondeterministic" else diff.compare
    ok, sql, pfilter, history, runs, extra, last = _attempts(
        project, proc_dir, meta, proc_sql, schema, expected, param_sets, params, compare, blocker, small)

    if blocker:
        r = _human(base, *blocker, history, sql)
        r["proposal"] = {
            "model_sql": sql, "param_filter": pfilter, "assumptions": last.get("assumptions"), "questions": last.get("questions"),
            "not_migrated": last.get("not_migrated"),
            "verification": (("shape only (columns + row count)" if compare is _shape_compare else "output rows match")
                             + f" on {len(runs)} dataset/parameter runs") if ok else "not verified: " + (history[-1]["status"] if history else "no model"),
        }
        return {**r, **extra}
    if ok:
        datasets = {}
        for (v, _), n in runs.items():
            datasets[v] = datasets.get(v, 0) + n
        mode = history[-1].get("param_mode", "filter")
        return {**base, "status": "verified", "attempts": len(history), "rows": sum(runs.values()), "datasets": datasets,
                "param_sets": len(param_sets), "model_sql": sql, "param_filter": pfilter, "param_mode": mode,
                **({"dbt_vars": {p["name"][1:]: dbt_runner.var_text(v) for p in params if not p["output"]
                                 for v in [_with_defaults(param_sets[0], params).get(p["name"])]}} if mode == "vars" else {}),
                "history": history, **extra}
    if sql is None and translate.mode() == "reference":
        return {**_human(base, "no_translation", "Translator produced no model.", history), **extra}
    if history and history[-1]["status"] == "not_filterable":
        why = history[-1]["detail"].split(":", 1)[-1].strip()
        return {**_human(base, "parameter_changes_grain",
                         f"Parameters change which rows are aggregated, so no single parameter-free model plus row filter can reproduce it. {why}",
                         history, sql), **extra}
    return {**_human(base, "unresolved_diff", f"Outputs still differ after {MAX_ATTEMPTS} attempts.", history, sql), **extra}


def _with_defaults(ps, params):
    """Parameter values the proc actually sees: the set, plus declared defaults for omitted parameters."""
    full = {p["name"]: _coerce(p["default"], p["type"]) for p in params if not p["output"] and p.get("has_default")}
    full.update({next((p["name"] for p in params if p["name"].lower() == k.lower()), k): v for k, v in ps.items()})
    return full


def _attempts(project, proc_dir, meta, proc_sql, schema, expected, param_sets, params, compare, blocker, small):
    """Translate -> run -> compare on every dataset x parameter set, up to MAX_ATTEMPTS.
    Returns (ok, sql, param_filter, history, runs, extra, last_translation)."""
    history, sql, pfilter, explanation, calls, t, extra = [], None, None, None, [], {}, {}
    out_cols = expected[(project.variants[0], 0)][0]
    mode = "filter"
    for attempt in range(1, MAX_ATTEMPTS + 2):  # +1: a switch to vars mode doesn't use up a debugging attempt
        if sum(h["status"] != "not_filterable" for h in history) >= MAX_ATTEMPTS:
            break
        t = translate.translate(proc_dir, proc_sql, schema, out_cols, history, blocker, small, params, project.source_name,
                                param_mode=mode)
        if t["usage"]:
            calls.append(t["usage"])
        explanation = explanation or t["explanation"]
        extra = {"explanation": explanation, "llm_calls": calls, "cost_usd": round(sum(c["cost_usd"] for c in calls), 6)}
        if t["sql"] is None:
            if translate.mode() == "reference":
                break
            history.append({"attempt": attempt, "sql": "", "status": "bad_response", "detail": t["error"]})
            continue
        sql, pfilter = t["sql"], (t.get("param_filter") if mode == "filter" else None)
        entry = {"attempt": attempt, "sql": sql, "param_filter": pfilter, "param_mode": mode}
        if mode == "filter" and pfilter and pfilter.upper().startswith("NOT_FILTERABLE"):
            history.append({**entry, "status": "not_filterable", "detail": pfilter})
            mode = "vars"
            continue
        if params and mode == "filter" and not pfilter:
            history.append({**entry, "status": "bad_response", "detail": "parameterized procedure but no <param_filter> block"})
            continue
        var_names = [p["name"][1:] for p in params if not p["output"]] if mode == "vars" else []
        base_vars = {n: _with_defaults(param_sets[0], params).get("@" + n) for n in var_names} if mode == "vars" else None
        _, err = dbt_runner.run_model(meta["slug"], sql, base_vars)
        if err:
            history.append({**entry, "status": "dbt_error", "detail": err})
            continue
        runs, failed = {}, None
        for (v, i), exp in expected.items():
            ps = param_sets[i]
            full = _with_defaults(ps, params)
            where = dbt_runner.render_filter(pfilter, full) if pfilter else None
            var_values = {n: full.get("@" + n) for n in var_names} if mode == "vars" else None
            got, err = dbt_runner.run_compiled(meta["slug"], v, exp[0], where, var_values)
            where_run = {"dataset": v, **({"params": {k: str(x) for k, x in ps.items()}} if ps else {})}
            if err:
                failed = {**entry, "status": "runtime_error", "detail": f"{json.dumps(where_run)}: {err}"}
                break
            res = compare(*exp, *got)
            if not res["equivalent"]:
                failed = {**entry, "status": "diff", "detail": {**where_run, **res}}
                break
            runs[(v, i)] = res["legacy_rows"]
        if failed:
            history.append(failed)
            continue
        history.append({**entry, "status": "match", "detail": {"runs": len(runs), "rows": sum(runs.values())}})
        return True, sql, pfilter, history, runs, extra, t
    return False, sql, pfilter, history, {}, extra, t
