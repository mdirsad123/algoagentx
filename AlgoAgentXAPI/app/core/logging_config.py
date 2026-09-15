"""Central logging configuration for AlgoAgentX.

Normal production traffic is intentionally quiet. ``LOG_LEVEL=ERROR`` keeps
routine framework/application logs hidden, while the dedicated activity logger
emits a small number of human-readable lifecycle events (backtest start/stage/
finish, first API hit for a route, and real alert triggers).
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
_ACTIVITY_LOGGER_NAME = "algoagentx.activity"
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


def _env_bool(name: str, default: bool = True) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return str(value).strip().lower() not in {"0", "false", "no", "off", "disabled"}


def configure_logging() -> int:
    """Configure quiet root logging plus concise operational activity logs."""
    level = _resolve_level()

    root_handler = logging.StreamHandler(sys.stdout)
    root_handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s"))
    logging.basicConfig(level=level, handlers=[root_handler], force=True)

    # Successful HTTP access logs and verbose library diagnostics are not useful
    # in normal production operation. Genuine application failures still use the
    # root ERROR/CRITICAL level and remain visible.
    for logger_name in _NOISY_LOGGERS:
        logging.getLogger(logger_name).setLevel(logging.ERROR)

    # Activity logs are intentionally independent from LOG_LEVEL. They are a
    # tiny, curated stream so production can stay ERROR-only without looking
    # completely dead during a long-running job.
    activity = logging.getLogger(_ACTIVITY_LOGGER_NAME)
    activity.handlers.clear()
    activity.propagate = False
    if _env_bool("ACTIVITY_LOGS", True):
        activity.setLevel(logging.INFO)
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.INFO)
        handler.setFormatter(logging.Formatter("%(asctime)s | ACTIVITY | %(message)s"))
        activity.addHandler(handler)
    else:
        activity.setLevel(logging.CRITICAL + 1)

    return level


def get_activity_logger() -> logging.Logger:
    """Return the dedicated low-volume operational logger."""
    return logging.getLogger(_ACTIVITY_LOGGER_NAME)
