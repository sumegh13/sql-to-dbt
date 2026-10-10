"""Translation step. Currently serves each proc's checked-in reference model (stand-in for the
Claude-backed agent); returns None when no translation exists."""
from pathlib import Path


def translate(proc_dir: Path, proc_sql: str, feedback: str | None = None) -> str | None:
    f = proc_dir / "reference_model.sql"
    return f.read_text() if f.exists() else None
