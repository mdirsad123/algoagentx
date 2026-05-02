from __future__ import annotations

import logging
from dataclasses import dataclass, asdict
from datetime import time
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd

logger = logging.getLogger(__name__)

ALLOWED_DAYS = {
    "MONDAY",
    "TUESDAY",
    "WEDNESDAY",
    "THURSDAY",
    "FRIDAY",
    "SATURDAY",
    "SUNDAY",
}

DAY_NAME_BY_INDEX = {
    0: "MONDAY",
    1: "TUESDAY",
    2: "WEDNESDAY",
    3: "THURSDAY",
    4: "FRIDAY",
    5: "SATURDAY",
    6: "SUNDAY",
}

ALLOWED_SESSIONS = {"ALL", "ASIAN", "LONDON", "NEW_YORK", "CUSTOM"}

# Preset session windows in Asia/Kolkata time, per AF-1 requirement.
SESSION_WINDOWS_IST = {
    "ASIAN": ("05:30", "13:30"),
    "LONDON": ("12:30", "21:30"),
    "NEW_YORK": ("18:30", "02:30"),
}

FOREX_MARKET_TOKENS = {"FOREX", "FX", "COMMODITY", "CFD"}
FOREX_SYMBOL_TOKENS = {"XAU", "XAG", "EUR", "GBP", "JPY", "USD", "AUD", "NZD", "CAD", "CHF"}
INDIAN_MARKET_TOKENS = {"INDIA", "NSE", "BSE", "MCX"}


@dataclass(slots=True)
class NormalizedAdvancedFilters:
    enabled: bool = False
    days_of_week: list[str] | None = None
    session: str = "ALL"
    custom_start_time: str | None = None
    custom_end_time: str | None = None
    timezone: str = "Asia/Kolkata"
    warnings: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["days_of_week"] = data.get("days_of_week") or []
        data["warnings"] = data.get("warnings") or []
        return data


def _parse_time(value: str | None) -> time | None:
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    parts = raw.split(":")
    if len(parts) < 2:
        return None
    try:
        hour = int(parts[0])
        minute = int(parts[1])
        second = int(parts[2]) if len(parts) > 2 else 0
        if hour < 0 or hour > 23 or minute < 0 or minute > 59 or second < 0 or second > 59:
            return None
        return time(hour=hour, minute=minute, second=second)
    except Exception:
        return None


def _safe_timezone(value: str | None) -> str:
    candidate = str(value or "Asia/Kolkata").strip() or "Asia/Kolkata"
    try:
        ZoneInfo(candidate)
        return candidate
    except Exception:
        return "Asia/Kolkata"


def normalize_advanced_filters(raw_filters: Any) -> NormalizedAdvancedFilters:
    """Normalize user supplied advanced filter payload without breaking legacy requests."""
    if raw_filters is None:
        return NormalizedAdvancedFilters(enabled=False, days_of_week=[], warnings=[])

    if hasattr(raw_filters, "model_dump"):
        raw = raw_filters.model_dump()
    elif isinstance(raw_filters, dict):
        raw = dict(raw_filters)
    else:
        return NormalizedAdvancedFilters(
            enabled=False,
            days_of_week=[],
            warnings=["Advanced filters ignored because payload format is invalid."],
        )

    enabled = bool(raw.get("enabled", False))
    warnings: list[str] = []

    raw_days = raw.get("days_of_week") or []
    if isinstance(raw_days, str):
        raw_days = [raw_days]
    days: list[str] = []
    if isinstance(raw_days, list):
        for day in raw_days:
            normalized_day = str(day or "").strip().upper()
            if normalized_day in ALLOWED_DAYS and normalized_day not in days:
                days.append(normalized_day)
            elif normalized_day:
                warnings.append(f"Ignored invalid day filter: {normalized_day}")

    session = str(raw.get("session") or "ALL").strip().upper()
    if session not in ALLOWED_SESSIONS:
        warnings.append(f"Ignored invalid session filter: {session}")
        session = "ALL"

    timezone = _safe_timezone(raw.get("timezone"))
    custom_start_time = raw.get("custom_start_time")
    custom_end_time = raw.get("custom_end_time")

    if session == "CUSTOM":
        if _parse_time(custom_start_time) is None or _parse_time(custom_end_time) is None:
            warnings.append("Custom time filter ignored because start/end time is invalid.")
            session = "ALL"

    return NormalizedAdvancedFilters(
        enabled=enabled,
        days_of_week=days,
        session=session,
        custom_start_time=str(custom_start_time).strip() if custom_start_time else None,
        custom_end_time=str(custom_end_time).strip() if custom_end_time else None,
        timezone=timezone,
        warnings=warnings,
    )


def _datetime_series_in_timezone(df: pd.DataFrame, timezone: str) -> pd.Series:
    values = pd.to_datetime(df["Date"], errors="coerce")
    # Backtest market data is usually stored as naive timestamps already in the
    # project display timezone. For timezone-aware data, convert safely.
    try:
        if getattr(values.dt, "tz", None) is not None:
            return values.dt.tz_convert(timezone)
    except Exception:
        pass
    return values


def _time_mask(series: pd.Series, start_time: time, end_time: time) -> pd.Series:
    local_times = series.dt.time
    if start_time <= end_time:
        return (local_times >= start_time) & (local_times <= end_time)
    # Overnight window, e.g. 18:30 to 02:30.
    return (local_times >= start_time) | (local_times <= end_time)


def is_indian_equity_like(instrument_symbol: str | None = None, instrument_market: str | None = None) -> bool:
    market = str(instrument_market or "").upper()
    symbol = str(instrument_symbol or "").upper()
    return market in INDIAN_MARKET_TOKENS or symbol.endswith(".NS") or symbol.endswith(".BO")


def is_forex_or_crypto_like(instrument_symbol: str | None = None, instrument_market: str | None = None) -> bool:
    market = str(instrument_market or "").upper()
    symbol = str(instrument_symbol or "").upper()
    if market in FOREX_MARKET_TOKENS or market == "CRYPTO":
        return True
    return any(token in symbol for token in FOREX_SYMBOL_TOKENS) or any(token in symbol for token in {"BTC", "ETH", "USDT"})


def apply_day_filter(df: pd.DataFrame, days_of_week: list[str] | None, *, timezone: str = "Asia/Kolkata") -> pd.DataFrame:
    if df.empty or not days_of_week:
        return df
    selected_days = {str(day).upper() for day in days_of_week if str(day).upper() in ALLOWED_DAYS}
    if not selected_days:
        return df
    local_dt = _datetime_series_in_timezone(df, timezone)
    day_names = local_dt.dt.weekday.map(DAY_NAME_BY_INDEX)
    return df.loc[day_names.isin(selected_days)].copy().reset_index(drop=True)


def apply_custom_time_filter(
    df: pd.DataFrame,
    custom_start_time: str | None,
    custom_end_time: str | None,
    *,
    timezone: str = "Asia/Kolkata",
) -> pd.DataFrame:
    if df.empty:
        return df
    start = _parse_time(custom_start_time)
    end = _parse_time(custom_end_time)
    if start is None or end is None:
        return df
    local_dt = _datetime_series_in_timezone(df, timezone)
    mask = _time_mask(local_dt, start, end)
    return df.loc[mask].copy().reset_index(drop=True)


def apply_session_filter(
    df: pd.DataFrame,
    session: str | None,
    *,
    timezone: str = "Asia/Kolkata",
    instrument_symbol: str | None = None,
    instrument_market: str | None = None,
) -> tuple[pd.DataFrame, list[str]]:
    warnings: list[str] = []
    selected_session = str(session or "ALL").upper()
    if df.empty or selected_session == "ALL":
        return df, warnings

    if selected_session == "CUSTOM":
        return df, warnings

    if selected_session not in SESSION_WINDOWS_IST:
        return df, warnings

    if is_indian_equity_like(instrument_symbol, instrument_market):
        warnings.append("Session presets are mainly for Forex/Crypto and were ignored for Indian equity/NSE instrument.")
        return df, warnings

    start_str, end_str = SESSION_WINDOWS_IST[selected_session]
    return apply_custom_time_filter(df, start_str, end_str, timezone=timezone), warnings


def calculate_filter_impact(before_count: int, after_count: int) -> dict[str, Any]:
    before = max(int(before_count or 0), 0)
    after = max(int(after_count or 0), 0)
    removed = max(before - after, 0)
    reduction = round((removed / before) * 100, 2) if before > 0 else 0.0
    return {
        "total_candles_before_filter": before,
        "total_candles_after_filter": after,
        "candles_removed": removed,
        "filter_reduction_pct": reduction,
    }


def _minimum_candles_for_timeframe(timeframe: str) -> int:
    tf = str(timeframe or "").strip().lower()
    return 20 if tf in {"1d", "d", "day", "daily"} or tf.endswith("d") else 50


def apply_advanced_filters(
    df: pd.DataFrame,
    raw_filters: Any,
    *,
    timeframe: str,
    instrument_symbol: str | None = None,
    instrument_market: str | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    normalized = normalize_advanced_filters(raw_filters)
    before_count = int(len(df.index)) if df is not None else 0
    warnings = list(normalized.warnings or [])

    if df is None:
        df = pd.DataFrame()

    if not normalized.enabled:
        impact = calculate_filter_impact(before_count, before_count)
        return df, {
            "enabled": False,
            "filters": normalized.to_dict(),
            **impact,
            "minimum_candles_required": _minimum_candles_for_timeframe(timeframe),
            "warning": None,
            "warnings": warnings,
            "status": "disabled",
        }

    logger.info(
        "Advanced backtest filters enabled: days=%s session=%s custom=%s-%s timezone=%s",
        normalized.days_of_week or [],
        normalized.session,
        normalized.custom_start_time,
        normalized.custom_end_time,
        normalized.timezone,
    )

    filtered = df.copy()
    filtered = apply_day_filter(filtered, normalized.days_of_week, timezone=normalized.timezone)

    if normalized.session == "CUSTOM":
        filtered = apply_custom_time_filter(
            filtered,
            normalized.custom_start_time,
            normalized.custom_end_time,
            timezone=normalized.timezone,
        )
    else:
        filtered, session_warnings = apply_session_filter(
            filtered,
            normalized.session,
            timezone=normalized.timezone,
            instrument_symbol=instrument_symbol,
            instrument_market=instrument_market,
        )
        warnings.extend(session_warnings)

    after_count = int(len(filtered.index))
    impact = calculate_filter_impact(before_count, after_count)
    min_required = _minimum_candles_for_timeframe(timeframe)
    low_candle_warning = None
    status = "ok"
    if after_count == 0:
        low_candle_warning = "Advanced filters removed all candles. Please widen the day/session/time filters."
        status = "error"
    elif after_count < min_required:
        low_candle_warning = (
            f"Advanced filters left only {after_count} candles. Minimum recommended for {timeframe} is {min_required}."
        )
        status = "warning"
    if low_candle_warning:
        warnings.append(low_candle_warning)

    logger.info(
        "Advanced backtest filter impact: before=%s after=%s removed=%s reduction=%s%%",
        impact["total_candles_before_filter"],
        impact["total_candles_after_filter"],
        impact["candles_removed"],
        impact["filter_reduction_pct"],
    )

    return filtered.sort_values("Date").reset_index(drop=True), {
        "enabled": True,
        "filters": normalized.to_dict(),
        **impact,
        "minimum_candles_required": min_required,
        "warning": low_candle_warning,
        "warnings": warnings,
        "status": status,
    }

def build_filter_summary(raw_filters: Any) -> str:
    """Return a concise human-readable summary for preview UI cards."""
    normalized = normalize_advanced_filters(raw_filters)
    if not normalized.enabled:
        return "Advanced filters disabled"

    parts: list[str] = []
    if normalized.days_of_week:
        pretty_days = [day.replace("_", " ").title() for day in normalized.days_of_week]
        parts.append(", ".join(pretty_days))

    session = str(normalized.session or "ALL").upper()
    if session == "CUSTOM":
        if normalized.custom_start_time and normalized.custom_end_time:
            parts.append(f"Custom {normalized.custom_start_time}-{normalized.custom_end_time}")
        else:
            parts.append("Custom Time")
    elif session != "ALL":
        session_name = session.replace("_", " ").title()
        parts.append(f"{session_name} Session")

    if not parts:
        parts.append("All candles")

    return " · ".join(parts)

