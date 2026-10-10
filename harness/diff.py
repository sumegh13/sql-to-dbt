"""Row-by-row comparison of legacy output vs dbt output, as multisets (duplicate counts matter)."""
from collections import Counter
from decimal import Decimal

FLOAT_DIGITS = 6


def _norm(v):
    if v is None:
        return None
    if isinstance(v, bool):
        return int(v)
    if isinstance(v, (Decimal, float)):
        f = round(float(v), FLOAT_DIGITS)
        return 0.0 if f == 0 else f  # fold -0.0
    if isinstance(v, str):
        return v.rstrip()  # SQL Server ignores trailing spaces in comparisons
    return v


def compare(legacy_cols, legacy_rows, new_cols, new_rows, sample=5):
    result = {"equivalent": False, "legacy_rows": len(legacy_rows), "new_rows": len(new_rows), "issues": []}
    lc, nc = [c.lower() for c in legacy_cols], [c.lower() for c in new_cols]
    if lc != nc:
        result["issues"].append({"column_mismatch": {"legacy": lc, "new": nc}})
        return result
    L = Counter(tuple(_norm(v) for v in r) for r in legacy_rows)
    N = Counter(tuple(_norm(v) for v in r) for r in new_rows)
    missing, extra = L - N, N - L
    if missing:
        result["issues"].append({"in_legacy_not_new": [list(r) for r in list(missing.elements())[:sample]], "count": sum(missing.values())})
    if extra:
        result["issues"].append({"in_new_not_legacy": [list(r) for r in list(extra.elements())[:sample]], "count": sum(extra.values())})
    result["equivalent"] = not result["issues"]
    return result
