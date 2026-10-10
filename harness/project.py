"""A project = legacy source schema + dataset variants + procs to migrate.

The built-in corpus lives in corpus/ + procs/ and runs in SQL Server's default database. User projects live in
projects/<name>/ and are built by harness/intake.py into projects/<name>/build/, each in its own database.
"""
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


@dataclass
class Project:
    name: str
    fixtures: Path              # <variant>.sql: full schema + data for one dataset
    procs: Path                 # NNN_slug/{proc.sql, meta.json}
    results: Path
    database: str | None        # None = default database (corpus); else dropped/recreated per load
    tables: list[str] = field(default_factory=list)    # legacy names, e.g. "dbo.orders", "Sales.Order"
    variants: list[str] = field(default_factory=list)  # first one is the base dataset

    def source_name(self, table: str) -> str:
        """DuckDB/dbt source table name for a legacy table: dbo.x -> x, Sales.Order -> Sales_Order."""
        schema, _, name = table.rpartition(".")
        return name if schema.lower() in ("", "dbo") else f"{schema}_{name}"


def corpus() -> Project:
    c = ROOT / "corpus"
    return Project("corpus", c / "fixtures", ROOT / "procs", ROOT / "results", None,
                   json.loads((c / "tables.json").read_text()), json.loads((c / "variants.json").read_text()))


def load(name_or_path: str) -> Project:
    if name_or_path in ("", "corpus"):
        return corpus()
    root = Path(name_or_path) if "/" in name_or_path else ROOT / "projects" / name_or_path
    build = root / "build"
    if not (build / "project.json").exists():
        raise SystemExit(f"{root} is not built yet: run `uv run python -m harness.intake {root}`")
    meta = json.loads((build / "project.json").read_text())
    return Project(meta["name"], build / "fixtures", build / "procs", root / "results", meta["database"],
                   meta["tables"], meta["variants"])


def database_name(project_name: str) -> str:
    return "mig_" + re.sub(r"\W", "_", project_name).lower()
