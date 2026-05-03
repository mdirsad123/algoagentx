from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any


QUANTITY_STYLE_MODES = {"SHARES", "UNITS", "CONTRACTS"}
LOT_STYLE_MODES = {"LOTS"}


def _to_decimal(value: Any, default: Decimal | None = None) -> Decimal | None:
    if value is None or value == "":
        return default
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return default


def _to_float(value: Decimal | None) -> float | None:
    if value is None:
        return None
    return float(value)


def _normalize_side(side: str) -> str:
    value = str(side or "").strip().upper()
    if value in {"LONG", "BUY", "B"}:
        return "BUY"
    if value in {"SHORT", "SELL", "S"}:
        return "SELL"
    return value


def calculate_trade_pnl(
    entry_price: float,
    exit_price: float,
    side: str,
    quantity_mode: str,
    quantity: float | None,
    lot_size: float | None,
    instrument_spec: dict,
) -> dict[str, Any]:
    """Calculate PnL using professional instrument master specs."""
    entry = _to_decimal(entry_price)
    exit_ = _to_decimal(exit_price)
    if entry is None or exit_ is None:
        return {"status": "REJECTED", "rejected_reason": "Invalid entry_price or exit_price."}

    normalized_side = _normalize_side(side)
    if normalized_side == "BUY":
        price_move = exit_ - entry
    elif normalized_side == "SELL":
        price_move = entry - exit_
    else:
        return {"status": "REJECTED", "rejected_reason": "side must be BUY/SELL."}

    mode = str(quantity_mode or instrument_spec.get("quantity_mode") or "SHARES").upper()
    tick_size = _to_decimal(instrument_spec.get("tick_size"), Decimal("0")) or Decimal("0")
    pip_size = _to_decimal(instrument_spec.get("pip_size"), tick_size) or tick_size
    tick_value = _to_decimal(instrument_spec.get("tick_value_per_lot"), Decimal("0")) or Decimal("0")
    points = price_move
    ticks = price_move / tick_size if tick_size > 0 else None
    pips = price_move / pip_size if pip_size and pip_size > 0 else None

    if mode in QUANTITY_STYLE_MODES:
        qty = _to_decimal(quantity)
        if qty is None or qty <= 0:
            return {"status": "REJECTED", "rejected_reason": "quantity must be greater than 0 for quantity mode."}
        pnl = price_move * qty
    elif mode in LOT_STYLE_MODES:
        lot = _to_decimal(lot_size)
        if lot is None or lot <= 0:
            return {"status": "REJECTED", "rejected_reason": "lot_size must be greater than 0 for LOTS mode."}
        if tick_size <= 0:
            return {"status": "REJECTED", "rejected_reason": "tick_size must be greater than 0 for LOTS mode."}
        if tick_value <= 0:
            return {"status": "REJECTED", "rejected_reason": "tick_value_per_lot must be greater than 0 for LOTS mode."}
        pnl = (price_move / tick_size) * tick_value * lot
    else:
        return {"status": "REJECTED", "rejected_reason": f"Unsupported quantity_mode: {mode}."}

    return {
        "status": "OK",
        "rejected_reason": None,
        "pnl": _to_float(pnl),
        "price_move": _to_float(price_move),
        "points": _to_float(points),
        "ticks": _to_float(ticks),
        "pips": _to_float(pips),
        "account_currency": instrument_spec.get("account_currency"),
        "currency_symbol": instrument_spec.get("currency_symbol"),
    }
