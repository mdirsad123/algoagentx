from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from datetime import date, datetime, time, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

from .types import NormalizedCandle, ValidationErrorSample

_TIMESTAMP_ALIASES = ("timestamp", "candle_time", "datetime", "date", "time")
_OPEN_ALIASES = ("open", "Open", "OPEN", "o")
_HIGH_ALIASES = ("high", "High", "HIGH", "h")
_LOW_ALIASES = ("low", "Low", "LOW", "l")
_CLOSE_ALIASES = ("close", "Close", "CLOSE", "c")
_VOLUME_ALIASES = ("volume", "Volume", "VOLUME", "tick_volume", "Tick Volume", "tickVolume", "v")


def _row_as_mapping(row: Any) -> Mapping[str, Any]:
    if isinstance(row, Mapping):
        return row
    # Pandas Series supports to_dict without requiring pandas as a dependency.
    if hasattr(row, "to_dict"):
        converted = row.to_dict()
        if isinstance(converted, Mapping):
            return converted
    raise TypeError("row must be a mapping-like object")


def _get_first(row: Mapping[str, Any], aliases: tuple[str, ...]) -> Any:
    lowered = {str(key).strip().lower(): value for key, value in row.items()}
    for alias in aliases:
        key = alias.strip().lower()
        if key in lowered:
            return lowered[key]
    return None


def _parse_timestamp(value: Any) -> datetime:
    if value is None or value == "":
        raise ValueError("timestamp is required")

    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, date):
        parsed = datetime.combine(value, time.min)
    else:
        text = str(value).strip()
        if not text:
            raise ValueError("timestamp is required")
        if text.endswith("Z"):
            text = f"{text[:-1]}+00:00"
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            # Common CSV/vendor date formats. Kept small and deterministic.
            formats = (
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d %H:%M",
                "%Y-%m-%d",
                "%d-%m-%Y %H:%M:%S",
                "%d-%m-%Y %H:%M",
                "%d-%m-%Y",
                "%d/%m/%Y %H:%M:%S",
                "%d/%m/%Y %H:%M",
                "%d/%m/%Y",
            )
            for fmt in formats:
                try:
                    parsed = datetime.strptime(text, fmt)
                    break
                except ValueError:
                    continue
            else:
                raise ValueError(f"invalid timestamp: {value!r}") from None

    # Existing market_data timestamp column is timezone-aware. Treat naive vendor
    # candles as UTC for consistent DB storage; aware values are converted to UTC.
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _parse_decimal(value: Any, field_name: str, *, default: Decimal | None = None) -> Decimal:
    if value is None or value == "":
        if default is not None:
            return default
        raise ValueError(f"{field_name} is required")
    try:
        dec = Decimal(str(value).replace(",", "").strip())
    except (InvalidOperation, AttributeError):
        raise ValueError(f"{field_name} must be numeric") from None
    if not dec.is_finite():
        raise ValueError(f"{field_name} must be finite")
    return dec


def normalize_candle(row: Any, row_index: int | None = None) -> NormalizedCandle:
    raw = _row_as_mapping(row)
    timestamp = _parse_timestamp(_get_first(raw, _TIMESTAMP_ALIASES))
    open_ = _parse_decimal(_get_first(raw, _OPEN_ALIASES), "open")
    high = _parse_decimal(_get_first(raw, _HIGH_ALIASES), "high")
    low = _parse_decimal(_get_first(raw, _LOW_ALIASES), "low")
    close = _parse_decimal(_get_first(raw, _CLOSE_ALIASES), "close")
    volume = _parse_decimal(_get_first(raw, _VOLUME_ALIASES), "volume", default=Decimal("0"))
    return NormalizedCandle(timestamp=timestamp, open=open_, high=high, low=low, close=close, volume=volume)


def normalize_candles(rows: Iterable[Any], *, max_error_samples: int = 25) -> tuple[list[NormalizedCandle], list[ValidationErrorSample], int]:
    """Normalize mapping-like rows into canonical candles.

    Returns: (normalized_candles, errors_sample, total_input_rows)
    Invalid rows are captured instead of raising so one bad vendor row does not
    fail a whole import.
    """
    normalized: list[NormalizedCandle] = []
    errors: list[ValidationErrorSample] = []
    total = 0

    for idx, row in enumerate(rows):
        total += 1
        try:
            normalized.append(normalize_candle(row, row_index=idx))
        except Exception as exc:
            raw: dict[str, Any] | None = None
            try:
                raw = dict(_row_as_mapping(row))
            except Exception:
                raw = {"value": repr(row)}
            if len(errors) < max_error_samples:
                errors.append(ValidationErrorSample(row_index=idx, reason=str(exc), row=raw))

    return normalized, errors, total
