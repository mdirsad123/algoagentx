from __future__ import annotations

from typing import Any

import pandas as pd


def _to_float(value: Any, default: float | None = None) -> float | None:
    try:
        if value is None or pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def _normalize_side(side: str | int | None) -> str:
    if side in (1, "1"):
        return "BUY"
    if side in (-1, "-1"):
        return "SELL"
    value = str(side or "").strip().upper()
    if value in {"LONG", "BUY", "B"}:
        return "BUY"
    if value in {"SHORT", "SELL", "S"}:
        return "SELL"
    return value


def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculate ATR using standard true range rolling mean."""
    high = pd.to_numeric(df["High"], errors="coerce")
    low = pd.to_numeric(df["Low"], errors="coerce")
    close = pd.to_numeric(df["Close"], errors="coerce")
    prev_close = close.shift(1)
    true_range = pd.concat(
        [
            (high - low).abs(),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return true_range.rolling(window=max(1, int(period or 14)), min_periods=1).mean()


def enrich_sl_tp_indicators(df: pd.DataFrame, runtime_config: dict[str, Any] | None = None) -> pd.DataFrame:
    """Add helper columns used by SL/TP and trade-management engines."""
    out = df.copy()
    sl_tp = (runtime_config or {}).get("sl_tp") or {}
    period = int(sl_tp.get("atr_period") or 14)
    out["_aax_atr"] = calculate_atr(out, period=period)
    out["_aax_ema20"] = pd.to_numeric(out["Close"], errors="coerce").ewm(span=20, adjust=False).mean()
    return out


def calculate_sl_tp(
    *,
    df: pd.DataFrame,
    signal_index: int,
    entry_price: float,
    side: str | int,
    runtime_config: dict[str, Any] | None = None,
    suggested_stop_loss: float | None = None,
    suggested_target: float | None = None,
) -> dict[str, Any]:
    """Resolve stop-loss and target from runtime config.

    Supported sl_mode: ATR, SWING, FIXED_PERCENT/FIXED_PRICE_RISK_PCT, STRATEGY_SUGGESTED.
    Returns REJECTED when a valid protective stop cannot be produced.
    """
    config = runtime_config or {}
    sl_tp = config.get("sl_tp") or {}
    mode = str(sl_tp.get("sl_mode") or "ATR").strip().upper()
    if mode == "FIXED_PRICE_RISK_PCT":
        mode = "FIXED_PERCENT"

    normalized_side = _normalize_side(side)
    entry = float(entry_price)
    rr_ratio = float(sl_tp.get("rr_ratio") or 2.0)
    lookback = max(1, int(sl_tp.get("swing_lookback") or 5))
    atr_multiplier = float(sl_tp.get("atr_multiplier") or 1.5)
    fixed_pct = float(sl_tp.get("fixed_price_risk_pct") or 0.002)

    stop_loss: float | None = None
    source = mode

    suggested_sl = _to_float(suggested_stop_loss, None)
    if mode == "STRATEGY_SUGGESTED" and suggested_sl is not None and suggested_sl > 0:
        stop_loss = suggested_sl
    elif mode == "STRATEGY_SUGGESTED":
        mode = "ATR"
        source = "ATR_FALLBACK"

    if stop_loss is None and mode == "ATR":
        atr_value = _to_float(df.iloc[signal_index].get("_aax_atr") if "_aax_atr" in df.columns else None, None)
        if atr_value is None or atr_value <= 0:
            atr_value = abs(float(df.iloc[signal_index].get("High", entry)) - float(df.iloc[signal_index].get("Low", entry)))
        distance = float(atr_value or 0) * atr_multiplier
        if distance > 0:
            stop_loss = entry - distance if normalized_side == "BUY" else entry + distance

    if stop_loss is None and mode == "SWING":
        start = max(0, int(signal_index) - lookback + 1)
        window = df.iloc[start : int(signal_index) + 1]
        if normalized_side == "BUY":
            stop_loss = _to_float(window["Low"].min(), None)
        else:
            stop_loss = _to_float(window["High"].max(), None)

    if stop_loss is None and mode == "FIXED_PERCENT":
        distance = entry * fixed_pct
        if distance > 0:
            stop_loss = entry - distance if normalized_side == "BUY" else entry + distance

    if stop_loss is None:
        return {"status": "REJECTED", "rejected_reason": "Could not calculate stop_loss.", "sl_mode": source}

    if normalized_side == "BUY" and stop_loss >= entry:
        return {"status": "REJECTED", "rejected_reason": "Calculated BUY stop_loss is not below entry.", "stop_loss": stop_loss, "sl_mode": source}
    if normalized_side == "SELL" and stop_loss <= entry:
        return {"status": "REJECTED", "rejected_reason": "Calculated SELL stop_loss is not above entry.", "stop_loss": stop_loss, "sl_mode": source}

    risk_distance = abs(entry - float(stop_loss))
    target: float | None = None
    suggested_tp = _to_float(suggested_target, None)
    if suggested_tp is not None and suggested_tp > 0:
        if (normalized_side == "BUY" and suggested_tp > entry) or (normalized_side == "SELL" and suggested_tp < entry):
            target = suggested_tp
    if target is None:
        reward_distance = risk_distance * rr_ratio
        target = entry + reward_distance if normalized_side == "BUY" else entry - reward_distance

    return {
        "status": "OK",
        "rejected_reason": None,
        "sl_mode": source,
        "stop_loss": float(stop_loss),
        "target": float(target),
        "risk_points": float(risk_distance),
        "reward_points": float(abs(float(target) - entry)),
        "rr_ratio": float(rr_ratio),
    }
