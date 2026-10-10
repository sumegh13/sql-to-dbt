"""Row-by-row comparison of legacy output vs dbt output (both loaded in DuckDB)."""
from decimal import Decimal
import duckdb


def _norm(v, tol_digits=6):
    if v is None:
        return None
    if isinstance(v, (Decimal, float)):
        return round(float(v), tol_digits)
    if isinstance(v, str):
        return v.rstrip()  # T-SQL CHAR padding / trailing spaces
    return v


def compare(legacy_cols, legacy_rows, new_cols, new_rows, key_sample=5):
    result = {"equivalent": False, "legacy_rows": len(legacy_rows), "new_rows": len(new_rows), "issues": []}
    lc, nc = [c.lower() for c in legacy_cols], [c.lower() for c in new_cols]
    if lc != nc:
        result["issues"].append(f"column mismatch: legacy={lc} new={nc}")
        return result
    L = sorted((tuple(_norm(v) for v in r) for r in legacy_rows), key=repr)
    N = sorted((tuple(_norm(v) for v in r) for r in new_rows), key=repr)
    missing = [r for r in L if r not in N]
    extra = [r for r in N if r not in L]
    if missing:
        result["issues"].append({"in_legacy_not_new": missing[:key_sample], "count": len(missing)})
    if extra:
        result["issues"].append({"in_new_not_legacy": extra[:key_sample], "count": len(extra)})
    if len(L) != len(N) and not missing and not extra:
        result["issues"].append("duplicate-row count differs")
    result["equivalent"] = not result["issues"]
    return result
