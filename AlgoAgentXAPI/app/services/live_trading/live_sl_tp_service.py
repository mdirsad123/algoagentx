from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from ..live.pnl_service import to_decimal


def _dec(value: Any, default: str = "0") -> Decimal:
    return to_decimal(value, default)


def _float(value: Any, default: float | None = None) -> float | None:
    if value in (None, ""):
        return default
    try:
        return float(value)
    except Exception:
        return default


def _field(candle: Any, name: str) -> Any:
    if isinstance(candle, dict):
        return candle.get(name)
    return getattr(candle, name, None)


def _atr(candles: list[Any], period: int) -> Decimal | None:
    if len(candles) < period + 1:
        return None
    trs: list[Decimal] = []
    recent = candles[-(period + 1):]
    for prev, cur in zip(recent, recent[1:]):
        high = _dec(_field(cur, "high"), "0")
        low = _dec(_field(cur, "low"), "0")
        prev_close = _dec(_field(prev, "close"), "0")
        if high <= 0 or low <= 0 or prev_close <= 0:
            continue
        trs.append(max(high - low, abs(high - prev_close), abs(low - prev_close)))
    if not trs:
        return None
    return sum(trs, Decimal("0")) / Decimal(len(trs))


def calculate_live_entry_plan(
    *,
    candles: list[Any] | None,
    side: str,
    entry_price: Any,
    runtime_config: dict[str, Any] | None,
    instrument_spec: dict[str, Any] | None = None,
    strategy_stop_loss: Any = None,
) -> dict[str, Any]:
    """Calculate a live entry plan before risk sizing/execution.

    This mirrors the backtest-grade flow: entry -> SL/TP -> risk points -> reward points.
    It intentionally returns a rejected payload instead of raising so live runner logs stay readable.
    """
    side = str(side or "BUY").upper()
    entry = _dec(entry_price, "0")
    if side not in {"BUY", "SELL"}:
        return {"status": "REJECTED", "rejected_reason": "Entry plan side must be BUY or SELL."}
    if entry <= 0:
        return {"status": "REJECTED", "rejected_reason": "Entry plan needs a positive latest price."}

    config = runtime_config or {}
    sl_tp = config.get("sl_tp") or {}
    rr = _dec(sl_tp.get("rr_ratio"), "2")
    if rr <= 0:
        return {"status": "REJECTED", "rejected_reason": "RR ratio must be greater than zero."}

    sl_mode = str(sl_tp.get("sl_mode") or "FIXED_PERCENT").upper().replace(" ", "_")
    if sl_mode in {"FIXED", "FIXED_PRICE_RISK", "FIXED_PERCENT_SL"}:
        sl_mode = "FIXED_PERCENT"
    if sl_mode == "STRATEGY_SUGGESTED" and strategy_stop_loss in (None, "", 0):
        # Beginner safe fallback. If an explicit strategy SL engine is added later, pass it in.
        sl_mode = "ATR" if len(candles or []) >= int(_float(sl_tp.get("atr_period"), 14) or 14) + 1 else "FIXED_PERCENT"

    stop_loss: Decimal | None = None
    if strategy_stop_loss not in (None, "", 0):
        stop_loss = _dec(strategy_stop_loss, "0")
    elif sl_mode == "ATR":
        period = int(_float(sl_tp.get("atr_period"), 14) or 14)
        multiplier = _dec(sl_tp.get("atr_multiplier"), "2")
        atr_value = _atr(candles or [], period)
        if atr_value is None or atr_value <= 0:
            return {"status": "REJECTED", "rejected_reason": "Stop loss could not be calculated because ATR needs more candles. Try Fixed Percent SL or refresh candles.", "sl_mode": sl_mode}
        distance = atr_value * multiplier
        stop_loss = entry - distance if side == "BUY" else entry + distance
    elif sl_mode == "SWING":
        lookback = int(_float(sl_tp.get("swing_lookback"), 10) or 10)
        if len(candles or []) < lookback:
            return {"status": "REJECTED", "rejected_reason": "Stop loss could not be calculated because Swing SL needs more candles. Try Fixed Percent SL or refresh candles.", "sl_mode": sl_mode}
        recent = (candles or [])[-lookback:]
        stop_loss = min(_dec(_field(c, "low"), "0") for c in recent) if side == "BUY" else max(_dec(_field(c, "high"), "0") for c in recent)
    else:
        pct = _dec(sl_tp.get("fixed_price_risk_pct"), "0.002")
        if pct <= 0:
            return {"status": "REJECTED", "rejected_reason": "Stop loss could not be calculated. Fixed Percent SL must be greater than zero.", "sl_mode": sl_mode}
        stop_loss = entry * (Decimal("1") - pct) if side == "BUY" else entry * (Decimal("1") + pct)
        sl_mode = "FIXED_PERCENT"

    if stop_loss is None or stop_loss <= 0:
        return {"status": "REJECTED", "rejected_reason": "Stop loss could not be calculated.", "sl_mode": sl_mode}
    if side == "BUY" and stop_loss >= entry:
        return {"status": "REJECTED", "rejected_reason": "BUY stop loss must be below entry price.", "entry_price": float(entry), "stop_loss": float(stop_loss), "sl_mode": sl_mode}
    if side == "SELL" and stop_loss <= entry:
        return {"status": "REJECTED", "rejected_reason": "SELL stop loss must be above entry price.", "entry_price": float(entry), "stop_loss": float(stop_loss), "sl_mode": sl_mode}

    risk_points = abs(entry - stop_loss)
    if risk_points <= 0:
        return {"status": "REJECTED", "rejected_reason": "Risk distance must be greater than zero.", "sl_mode": sl_mode}
    target = entry + (risk_points * rr) if side == "BUY" else entry - (risk_points * rr)
    if side == "BUY" and target <= entry:
        return {"status": "REJECTED", "rejected_reason": "BUY target must be above entry price.", "sl_mode": sl_mode}
    if side == "SELL" and target >= entry:
        return {"status": "REJECTED", "rejected_reason": "SELL target must be below entry price.", "sl_mode": sl_mode}

    return {
        "status": "OK",
        "entry_price": float(entry),
        "stop_loss": float(stop_loss),
        "target": float(target),
        "take_profit": float(target),
        "sl_mode": sl_mode,
        "rr_ratio": float(rr),
        "risk_points": float(risk_points),
        "reward_points": float(abs(target - entry)),
        "instrument_spec_snapshot": instrument_spec or {},
        "calculated_at": datetime.now(timezone.utc).isoformat(),
    }
