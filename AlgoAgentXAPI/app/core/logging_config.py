"""Central logging configuration for AlgoAgentX.

Normal production traffic is intentionally quiet. Set LOG_LEVEL=DEBUG
when detailed diagnostics are temporarily needed.
"""
from __future__ import annotations

import logging
import os
import sys

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - python-dotenv is an app dependency
    load_dotenv = None


_ALLOWED_LEVELS = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}
_NOISY_LOGGERS = (
    "uvicorn.access",
    "uvicorn.error",
    "gunicorn.access",
    "gunicorn.error",
    "sqlalchemy.engine",
    "sqlalchemy.pool",
    "redis",
)


def _load_env_files() -> None:
    """Load local env files without overriding real process env vars."""
    if load_dotenv is None:
        return
    load_dotenv(".env", override=False)
    load_dotenv(".env.local", override=False)


def _resolve_level() -> int:
    _load_env_files()
    requested = str(os.getenv("LOG_LEVEL", "ERROR") or "ERROR").strip().upper()
    if requested not in _ALLOWED_LEVELS:
        requested = "ERROR"
    return getattr(logging, requested, logging.ERROR)


def configure_logging() -> int:
    """Configure app logging once and silence routine framework access logs."""
    level = _resolve_level()

    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )

    # Successful HTTP access logs and verbose library diagnostics are not useful
    # in normal production operation. Genuine application failures still use the
    # root ERROR/CRITICAL level and remain visible.
    for logger_name in _NOISY_LOGGERS:
        logging.getLogger(logger_name).setLevel(logging.ERROR)

    return level
