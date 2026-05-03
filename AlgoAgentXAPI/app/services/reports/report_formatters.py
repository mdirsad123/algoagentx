from __future__ import annotations

import math
from datetime import date, datetime
from decimal import Decimal
from typing import Any


def safe_text(value: Any, fallback: str = "-") -> str:
    if value is None:
        return fallback
    if isinstance(value, str):
        stripped = value.strip()
        return stripped if stripped else fallback
    try:
        if isinstance(value, float) and math.isnan(value):
            return fallback
    except Exception:
        pass
    return str(value)


def _to_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        if isinstance(value, Decimal):
            return float(value)
        return float(value)
    except Exception:
        return None


def _format_grouped_us(value: float, decimals: int = 2) -> str:
    return f"{value:,.{decimals}f}"


def _format_grouped_in(value: float, decimals: int = 2) -> str:
    # Indian numbering system: 12,34,567.89
    formatted = f"{value:.{decimals}f}"
    whole, dot, frac = formatted.partition(".")
    if len(whole) <= 3:
        grouped = whole
    else:
        last3 = whole[-3:]
        rest = whole[:-3]
        parts = []
        while len(rest) > 2:
            parts.insert(0, rest[-2:])
            rest = rest[:-2]
        if rest:
            parts.insert(0, rest)
        grouped = ",".join(parts + [last3])
    return grouped + (dot + frac if decimals > 0 else "")


def format_number(value: Any, decimals: int = 2, fallback: str = "-") -> str:
    numeric = _to_float(value)
    if numeric is None:
        return fallback
    return f"{numeric:,.{decimals}f}"


def format_percent(value: Any, decimals: int = 2, fallback: str = "-") -> str:
    numeric = _to_float(value)
    if numeric is None:
        return fallback
    return f"{numeric:.{decimals}f}%"


def format_money(value: Any, currency_symbol: str = "$", account_currency: str = "USD", fallback: str = "-") -> str:
    numeric = _to_float(value)
    if numeric is None:
        return fallback
    symbol = currency_symbol or ("$" if (account_currency or "").upper() == "USD" else "₹" if (account_currency or "").upper() == "INR" else f"{account_currency or ''} ")
    sign = "-" if numeric < 0 else ""
    abs_value = abs(numeric)
    if (account_currency or "").upper() == "INR" or symbol == "₹":
        grouped = _format_grouped_in(abs_value, 2)
    else:
        grouped = _format_grouped_us(abs_value, 2)
    return f"{sign}{symbol}{grouped}"


def format_price(value: Any, price_precision: int | None = 2, fallback: str = "-") -> str:
    decimals = 2 if price_precision is None else max(0, min(int(price_precision), 8))
    return format_number(value, decimals=decimals, fallback=fallback)


def format_trade_size(trade: dict[str, Any], quantity_mode: str | None = None, fallback: str = "-") -> str:
    mode = (quantity_mode or trade.get("quantity_mode") or "").upper()
    if mode == "LOTS":
        lot = _to_float(trade.get("lot_size") or trade.get("final_lot_size"))
        return fallback if lot is None or lot == 0 else f"{lot:.2f}"
    qty = _to_float(trade.get("quantity") or trade.get("final_quantity"))
    if qty is None:
        return fallback
    if mode in {"SHARES", "CONTRACTS", "UNITS"}:
        return f"{qty:,.0f}" if abs(qty - int(qty)) < 1e-9 else f"{qty:,.2f}"
    lot = _to_float(trade.get("lot_size") or trade.get("final_lot_size"))
    if lot:
        return f"{lot:.2f}"
    return f"{qty:,.0f}" if abs(qty - int(qty)) < 1e-9 else f"{qty:,.2f}"


def parse_datetime_label(value: Any, fallback: str = "-") -> str:
    if value is None:
        return fallback
    if isinstance(value, (datetime, date)):
        return value.strftime("%Y-%m-%d %H:%M") if isinstance(value, datetime) else value.isoformat()
    text = str(value)
    if not text:
        return fallback
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return text[:19].replace("T", " ")
