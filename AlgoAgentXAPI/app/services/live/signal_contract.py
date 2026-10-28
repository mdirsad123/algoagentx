"""Pure source-of-truth signal extraction shared by the live runner and parity tests."""
from __future__ import annotations
from typing import Any
from datetime import datetime
import math
import pandas as pd

def _normalize_signal_value(raw_value: Any) -> str:
    if raw_value is None:
        return "HOLD"
    try:
        numeric = int(float(raw_value))
        if numeric > 0:
            return "BUY"
        if numeric < 0:
            return "SELL"
        return "HOLD"
    except Exception:
        text = str(raw_value or "").strip().upper()
        if text in {"BUY", "LONG", "BULL", "1", "+1"}:
            return "BUY"
        if text in {"SELL", "SHORT", "BEAR", "-1"}:
            return "SELL"
        if text in {"EXIT", "CLOSE", "CLOSE_LONG", "CLOSE_SHORT", "FLAT"}:
            return "EXIT"
        return "HOLD"




def _json_safe_value(value: Any) -> Any:
    """Convert pandas/numpy/scalar values into JSON-safe Python values."""
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    if isinstance(value, (datetime,)):
        return value.isoformat()
    if hasattr(value, "item"):
        try:
            value = value.item()
        except Exception:
            pass
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return value
    if isinstance(value, (int, bool, str)):
        text = value.strip() if isinstance(value, str) else value
        if text == "":
            return None
        return text
    if isinstance(value, dict):
        return {str(k): _json_safe_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe_value(v) for v in value]
    return str(value)


def _safe_float(value: Any) -> float | None:
    value = _json_safe_value(value)
    if value is None:
        return None
    try:
        number = float(value)
    except Exception:
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def _first_present(row: Any, columns: tuple[str, ...]) -> Any:
    for column in columns:
        try:
            if column in row.index:
                value = row[column]
                if _json_safe_value(value) is not None:
                    return value
        except Exception:
            continue
    return None


def _safe_row_dict(row: Any) -> dict[str, Any]:
    try:
        raw = row.to_dict()
    except Exception:
        raw = {}
    return {str(k): _json_safe_value(v) for k, v in raw.items()}


def extract_latest_signal_payload(generated_df: pd.DataFrame) -> dict[str, Any]:
    """Extract the live runner contract from the latest generated strategy row.

    Live-compatible strategies may return signal/Position plus strategy_stop_loss,
    strategy_target, helper risk/reward columns and signal_reason.  This helper
    intentionally reads only the latest closed-candle row, mirroring the live
    runner decision point.
    """
    if generated_df is None or generated_df.empty:
        return {
            "signal_type": "HOLD",
            "strategy_stop_loss": None,
            "strategy_target": None,
            "strategy_risk_points": None,
            "strategy_reward_points": None,
            "signal_reason": None,
            "source_row": {},
        }

    latest = generated_df.iloc[-1]
    signal_raw = _first_present(latest, ("signal", "Signal", "SIGNAL", "position", "Position", "POSITION"))
    signal_type = _normalize_signal_value(signal_raw)
    stop_loss = _safe_float(_first_present(latest, ("strategy_stop_loss", "stop_loss", "sl", "SL")))
    target = _safe_float(_first_present(latest, ("strategy_target", "target", "take_profit", "tp", "TP")))
    risk_points = _safe_float(_first_present(latest, ("strategy_risk_points", "risk_points", "risk", "risk_distance")))
    reward_points = _safe_float(_first_present(latest, ("strategy_reward_points", "reward_points", "reward", "reward_distance")))
    reason_value = _json_safe_value(_first_present(latest, ("signal_reason", "reason", "Reason", "SIGNAL_REASON")))
    signal_reason = str(reason_value) if reason_value is not None else None

    return {
        "signal_type": signal_type,
        "strategy_stop_loss": stop_loss,
        "strategy_target": target,
        "strategy_risk_points": risk_points,
        "strategy_reward_points": reward_points,
        "signal_reason": signal_reason,
        "source_row": _safe_row_dict(latest),
    }


