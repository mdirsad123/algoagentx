from __future__ import annotations

import math
from decimal import Decimal, ROUND_FLOOR, InvalidOperation
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


def _floor_to_step(value: Decimal, step: Decimal | None) -> Decimal:
    if step is None or step <= 0:
        return value
    return (value / step).to_integral_value(rounding=ROUND_FLOOR) * step


def _is_step_aligned(value: Decimal, step: Decimal | None, tolerance: Decimal = Decimal("0.00000001")) -> bool:
    if step is None or step <= 0:
        return True
    remainder = abs(value % step)
    return remainder <= tolerance or abs(remainder - step) <= tolerance


def _reject(base: dict[str, Any], reason: str) -> dict[str, Any]:
    base["status"] = "REJECTED"
    base["rejected_reason"] = reason
    return base


def _normalize_side(side: str | None) -> str | None:
    if not side:
        return None
    value = str(side).strip().upper()
    if value in {"LONG", "BUY", "B"}:
        return "BUY"
    if value in {"SHORT", "SELL", "S"}:
        return "SELL"
    return value


def _validate_stop_loss(entry: Decimal, stop_loss: Decimal, side: str | None) -> str | None:
    normalized = _normalize_side(side)
    if normalized == "BUY" and stop_loss >= entry:
        return "For BUY side, stop_loss must be below entry_price."
    if normalized == "SELL" and stop_loss <= entry:
        return "For SELL side, stop_loss must be above entry_price."
    return None


def _base_result(
    *,
    entry_price: Decimal,
    stop_loss: Decimal,
    capital: Decimal,
    risk_percent: Decimal,
    instrument_spec: dict[str, Any],
) -> dict[str, Any]:
    quantity_mode = str(instrument_spec.get("quantity_mode") or "SHARES").upper()
    tick_size = _to_decimal(instrument_spec.get("tick_size"), Decimal("0")) or Decimal("0")
    tick_value_per_lot = _to_decimal(instrument_spec.get("tick_value_per_lot"), Decimal("0")) or Decimal("0")
    pip_size = _to_decimal(instrument_spec.get("pip_size"), tick_size) or tick_size
    contract_size = _to_decimal(instrument_spec.get("contract_size"), Decimal("0")) or Decimal("0")
    min_lot = _to_decimal(instrument_spec.get("min_lot"), Decimal("0")) or Decimal("0")
    max_lot = _to_decimal(instrument_spec.get("max_lot"), None)
    lot_step = _to_decimal(instrument_spec.get("lot_step"), Decimal("0.01")) or Decimal("0.01")
    min_quantity = _to_decimal(instrument_spec.get("min_quantity"), Decimal("1")) or Decimal("1")
    max_quantity = _to_decimal(instrument_spec.get("max_quantity"), None)
    quantity_step = _to_decimal(instrument_spec.get("quantity_step"), Decimal("1")) or Decimal("1")
    risk_amount = capital * risk_percent
    risk_points = abs(entry_price - stop_loss)
    risk_ticks = risk_points / tick_size if tick_size > 0 else None
    risk_pips = risk_points / pip_size if pip_size and pip_size > 0 else None

    return {
        "status": "OK",
        "rejected_reason": None,
        "quantity_mode": quantity_mode,
        "account_currency": instrument_spec.get("account_currency"),
        "currency_symbol": instrument_spec.get("currency_symbol"),
        "risk_amount": _to_float(risk_amount),
        "actual_risk_amount": None,
        "entry_price": _to_float(entry_price),
        "stop_loss": _to_float(stop_loss),
        "risk_points": _to_float(risk_points),
        "risk_ticks": _to_float(risk_ticks),
        "risk_pips": _to_float(risk_pips),
        "loss_per_1_lot": None,
        "raw_lot_size": None,
        "final_lot_size": None,
        "raw_quantity": None,
        "final_quantity": None,
        "tick_size": _to_float(tick_size),
        "tick_value_per_lot": _to_float(tick_value_per_lot),
        "pip_size": _to_float(pip_size),
        "contract_size": _to_float(contract_size),
        "min_lot": _to_float(min_lot),
        "max_lot": _to_float(max_lot),
        "lot_step": _to_float(lot_step),
        "min_quantity": _to_float(min_quantity),
        "max_quantity": _to_float(max_quantity),
        "quantity_step": _to_float(quantity_step),
        "_decimal": {
            "risk_amount": risk_amount,
            "risk_points": risk_points,
            "risk_ticks": risk_ticks,
            "risk_pips": risk_pips,
            "tick_size": tick_size,
            "tick_value_per_lot": tick_value_per_lot,
            "min_lot": min_lot,
            "max_lot": max_lot,
            "lot_step": lot_step,
            "min_quantity": min_quantity,
            "max_quantity": max_quantity,
            "quantity_step": quantity_step,
        },
    }


def _strip_private(result: dict[str, Any]) -> dict[str, Any]:
    result.pop("_decimal", None)
    return result


def calculate_position_size(
    entry_price: float,
    stop_loss: float,
    capital: float,
    risk_percent: float,
    instrument_spec: dict,
    position_size_mode: str = "RISK_BASED",
    fixed_lot: float | None = None,
    fixed_quantity: float | None = None,
    max_lot_cap: float | None = None,
    max_quantity_cap: float | None = None,
    side: str | None = None,
) -> dict[str, Any]:
    """Calculate professional position sizing from instrument master specifications.

    risk_percent is treated as a decimal fraction: 0.01 means 1% risk.
    """
    entry = _to_decimal(entry_price)
    sl = _to_decimal(stop_loss)
    cap = _to_decimal(capital)
    risk_pct = _to_decimal(risk_percent)
    if entry is None or sl is None or cap is None or risk_pct is None:
        return {"status": "REJECTED", "rejected_reason": "Invalid numeric input."}

    result = _base_result(entry_price=entry, stop_loss=sl, capital=cap, risk_percent=risk_pct, instrument_spec=instrument_spec or {})
    decimals = result["_decimal"]

    if cap <= 0:
        return _strip_private(_reject(result, "Initial capital must be greater than 0."))
    if risk_pct <= 0:
        return _strip_private(_reject(result, "Risk percent must be greater than 0."))

    stop_error = _validate_stop_loss(entry, sl, side)
    if stop_error:
        return _strip_private(_reject(result, stop_error))

    quantity_mode = result["quantity_mode"]
    mode = str(position_size_mode or "RISK_BASED").upper()
    risk_points = decimals["risk_points"]
    if risk_points <= 0:
        return _strip_private(_reject(result, "Stop loss distance must be greater than 0."))

    if mode == "FIXED_LOT":
        lot = _to_decimal(fixed_lot)
        if lot is None or lot <= 0:
            return _strip_private(_reject(result, "fixed_lot must be greater than 0 for FIXED_LOT mode."))
        return _strip_private(_calculate_lot_result(result, lot, fixed=True, max_lot_cap=max_lot_cap))

    if mode == "FIXED_QUANTITY":
        qty = _to_decimal(fixed_quantity)
        if qty is None or qty <= 0:
            return _strip_private(_reject(result, "fixed_quantity must be greater than 0 for FIXED_QUANTITY mode."))
        return _strip_private(_calculate_quantity_result(result, qty, fixed=True, max_quantity_cap=max_quantity_cap))

    if quantity_mode in LOT_STYLE_MODES:
        return _strip_private(_calculate_risk_based_lot_result(result, max_lot_cap=max_lot_cap))

    if quantity_mode in QUANTITY_STYLE_MODES:
        return _strip_private(_calculate_risk_based_quantity_result(result, max_quantity_cap=max_quantity_cap))

    return _strip_private(_reject(result, f"Unsupported quantity_mode: {quantity_mode}."))


def _calculate_risk_based_lot_result(result: dict[str, Any], max_lot_cap: float | None = None) -> dict[str, Any]:
    d = result["_decimal"]
    tick_size = d["tick_size"]
    tick_value = d["tick_value_per_lot"]
    if tick_size <= 0:
        return _reject(result, "Instrument spec is missing tick_size for LOTS mode. Please ask admin to configure Market Master.")
    if tick_value <= 0:
        return _reject(result, "Instrument spec is missing tick_value_per_lot. Please ask admin to configure Market Master.")

    loss_per_1_lot = (d["risk_points"] / tick_size) * tick_value
    if loss_per_1_lot <= 0:
        return _reject(result, "loss_per_1_lot must be greater than 0.")
    raw_lot = d["risk_amount"] / loss_per_1_lot
    final_lot = _floor_to_step(raw_lot, d["lot_step"])
    result["loss_per_1_lot"] = _to_float(loss_per_1_lot)
    result["raw_lot_size"] = _to_float(raw_lot)
    return _calculate_lot_result(result, final_lot, fixed=False, max_lot_cap=max_lot_cap, loss_per_1_lot=loss_per_1_lot)


def _calculate_lot_result(
    result: dict[str, Any],
    lot: Decimal,
    *,
    fixed: bool,
    max_lot_cap: float | None = None,
    loss_per_1_lot: Decimal | None = None,
) -> dict[str, Any]:
    d = result["_decimal"]
    if loss_per_1_lot is None:
        if d["tick_size"] <= 0:
            return _reject(result, "Instrument spec is missing tick_size for LOTS mode. Please ask admin to configure Market Master.")
        if d["tick_value_per_lot"] <= 0:
            return _reject(result, "Instrument spec is missing tick_value_per_lot. Please ask admin to configure Market Master.")
        loss_per_1_lot = (d["risk_points"] / d["tick_size"]) * d["tick_value_per_lot"]
        result["loss_per_1_lot"] = _to_float(loss_per_1_lot)
        result["raw_lot_size"] = _to_float(lot)

    if fixed and not _is_step_aligned(lot, d["lot_step"]):
        return _reject(result, "fixed_lot is not aligned to lot_step.")

    cap = d["max_lot"]
    supplied_cap = _to_decimal(max_lot_cap)
    if supplied_cap is not None and supplied_cap > 0:
        cap = supplied_cap if cap is None else min(cap, supplied_cap)
    if cap is not None and lot > cap:
        lot = _floor_to_step(cap, d["lot_step"])
    if lot < d["min_lot"]:
        return _reject(result, f"Calculated lot size {_to_float(lot)} is below broker minimum {_to_float(d['min_lot'])}. Increase capital, reduce SL distance, or reduce min lot.")

    result["final_lot_size"] = _to_float(lot)
    result["actual_risk_amount"] = _to_float(lot * loss_per_1_lot)
    return result


def _calculate_risk_based_quantity_result(result: dict[str, Any], max_quantity_cap: float | None = None) -> dict[str, Any]:
    d = result["_decimal"]
    risk_per_unit = d["risk_points"]
    if risk_per_unit <= 0:
        return _reject(result, "risk_per_share must be greater than 0.")
    raw_qty = d["risk_amount"] / risk_per_unit
    final_qty = _floor_to_step(raw_qty, d["quantity_step"])
    result["raw_quantity"] = _to_float(raw_qty)
    return _calculate_quantity_result(result, final_qty, fixed=False, max_quantity_cap=max_quantity_cap, risk_per_unit=risk_per_unit)


def _calculate_quantity_result(
    result: dict[str, Any],
    qty: Decimal,
    *,
    fixed: bool,
    max_quantity_cap: float | None = None,
    risk_per_unit: Decimal | None = None,
) -> dict[str, Any]:
    d = result["_decimal"]
    risk_per_unit = risk_per_unit or d["risk_points"]
    if fixed and not _is_step_aligned(qty, d["quantity_step"]):
        return _reject(result, "fixed_quantity is not aligned to quantity_step.")

    cap = d["max_quantity"]
    supplied_cap = _to_decimal(max_quantity_cap)
    if supplied_cap is not None and supplied_cap > 0:
        cap = supplied_cap if cap is None else min(cap, supplied_cap)
    if cap is not None and qty > cap:
        qty = _floor_to_step(cap, d["quantity_step"])
    if qty < d["min_quantity"]:
        return _reject(result, f"Calculated quantity {_to_float(qty)} is below minimum {_to_float(d['min_quantity'])}. Increase capital, reduce SL distance, or reduce minimum quantity.")

    result["raw_quantity"] = result.get("raw_quantity") or _to_float(qty)
    result["final_quantity"] = _to_float(qty)
    result["actual_risk_amount"] = _to_float(qty * risk_per_unit)
    return result
