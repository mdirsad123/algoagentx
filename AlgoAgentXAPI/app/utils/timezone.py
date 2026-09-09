from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

UTC = timezone.utc
KOLKATA_TZ = ZoneInfo("Asia/Kolkata")
DISPLAY_TIMEZONE_NAME = "Asia/Kolkata"
DISPLAY_TIMEZONE_LABEL = "IST (UTC+05:30)"


def ensure_utc(value: Any) -> datetime | None:
    """Normalize an API/DB timestamp to an aware UTC datetime.

    AlgoAgentX market/backtest timestamps are canonical UTC instants. Legacy
    rows may be returned as timezone-naive values by older PostgreSQL schemas;
    those naive values must therefore be interpreted as UTC, not local time.
    """
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value).strip()
        if not text:
            return None
        try:
            dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except Exception:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def iso_utc(value: Any) -> str | None:
    dt = ensure_utc(value)
    if dt is None:
        return None
    return dt.isoformat().replace("+00:00", "Z")


def to_kolkata(value: Any) -> datetime | None:
    dt = ensure_utc(value)
    if dt is None:
        return None
    return dt.astimezone(KOLKATA_TZ)


def format_kolkata_datetime(
    value: Any,
    fallback: str = "-",
    *,
    include_seconds: bool = False,
    include_timezone: bool = True,
) -> str:
    if value is None:
        return fallback
    if isinstance(value, date) and not isinstance(value, datetime):
        return value.isoformat()
    dt = to_kolkata(value)
    if dt is None:
        text = str(value).strip()
        return text if text else fallback
    fmt = "%Y-%m-%d %H:%M:%S" if include_seconds else "%Y-%m-%d %H:%M"
    result = dt.strftime(fmt)
    if include_timezone:
        result += " IST"
    return result


def kolkata_date_key(value: Any, fallback: str = "") -> str:
    dt = to_kolkata(value)
    return dt.date().isoformat() if dt is not None else fallback
