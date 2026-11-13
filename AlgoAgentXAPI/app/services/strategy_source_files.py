"""Immutable, versioned .py mirrors of DB-backed admin strategies.

Database source_code remains authoritative. Files are audit/export artifacts,
not imported by live workers and never an execution-time dependency.
"""
from __future__ import annotations

from hashlib import sha256
import os
from pathlib import Path
from uuid import UUID, uuid4


def export_strategy_source(strategy_id: str, source: str) -> str | None:
    source = str(source or "").strip()
    if not source:
        return None
    uid = str(UUID(str(strategy_id)))  # reject path traversal
    digest = sha256(source.encode("utf-8")).hexdigest()
    root = Path(os.environ.get("STRATEGY_SOURCE_EXPORT_DIR", "/app/runtime_data/strategy_sources"))
    directory = root / uid
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / (digest + ".py")
    if target.exists():
        if target.read_text(encoding="utf-8") != source + "\n":
            raise RuntimeError("Existing strategy source artifact does not match SHA")
    else:
        temp = directory / ("." + digest + "." + uuid4().hex + ".tmp")
        try:
            temp.write_text(source + "\n", encoding="utf-8", newline="\n")
            os.replace(temp, target)
        finally:
            temp.unlink(missing_ok=True)
    return str(target)
