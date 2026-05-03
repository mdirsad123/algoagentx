from __future__ import annotations

from copy import deepcopy
from decimal import Decimal
from typing import Any, Mapping


NUMBER_TYPES = (int, float, Decimal)


SYSTEM_DEFAULT_RUNTIME_CONFIG: dict[str, Any] = {
    "risk": {
        "initial_capital": 1000,
        "account_currency": None,
        "risk_percent": 0.01,
        "position_size_mode": "RISK_BASED",
        "fixed_lot": None,
        "fixed_quantity": None,
        "max_lot_cap": None,
        "max_quantity_cap": None,
    },
    "execution": {
        "entry_mode": "NEXT_CANDLE_OPEN",
        "exit_on_opposite_signal": True,
        "allow_long": True,
        "allow_short": True,
        "max_trades_per_day": None,
        "max_open_positions": 1,
        "intraday_square_off": False,
        "square_off_time": "15:15",
    },
    "sl_tp": {
        "sl_mode": "ATR",
        "rr_ratio": 2,
        "atr_period": 14,
        "atr_multiplier": 1.5,
        "swing_lookback": 5,
        "fixed_price_risk_pct": 0.002,
        "use_strategy_suggested_sl": False,
    },
    "trade_management": {
        "break_even_enabled": False,
        "break_even_trigger_r": 1,
        "break_even_offset_points": 0,
        "trailing_enabled": False,
        "trailing_mode": "ATR_TRAIL",
        "trail_start_r": 1.5,
        "trail_atr_multiplier": 1,
        "partial_exit_enabled": False,
        "partial_exit_at_r": 1,
        "partial_exit_percent": 0.5,
    },
    "strategy_params": {},
}


EMA_RUNTIME_CONFIG_SCHEMA: dict[str, Any] = {
    "strategy_params": {
        "ema_fast": {
            "type": "number",
            "label": "EMA Fast",
            "default": 9,
            "min": 1,
            "max": 200,
        },
        "ema_slow": {
            "type": "number",
            "label": "EMA Slow",
            "default": 20,
            "min": 1,
            "max": 300,
        },
        "use_ema_200_filter": {
            "type": "boolean",
            "label": "Use EMA 200 Filter",
            "default": True,
        },
        "body_ratio_min": {
            "type": "number",
            "label": "Minimum Body Ratio",
            "default": 0.5,
        },
    }
}


SMC_RUNTIME_CONFIG_SCHEMA: dict[str, Any] = {
    "strategy_params": {
        "swing_lookback": {
            "type": "number",
            "label": "Swing Lookback",
            "default": 5,
        },
        "liquidity_sweep_window": {
            "type": "number",
            "label": "Liquidity Sweep Window",
            "default": 10,
        },
        "require_bos": {
            "type": "boolean",
            "label": "Require BOS",
            "default": True,
        },
    }
}


ALLOWED_POSITION_SIZE_MODES = {"RISK_BASED", "FIXED_LOT", "FIXED_QUANTITY"}
ALLOWED_ENTRY_MODES = {"NEXT_CANDLE_OPEN", "SIGNAL_CANDLE_CLOSE", "MARKET_ON_SIGNAL"}
ALLOWED_SL_MODES = {"ATR", "SWING", "FIXED_PERCENT", "FIXED_PRICE_RISK_PCT", "STRATEGY_SUGGESTED", "NONE"}
ALLOWED_TRAILING_MODES = {"ATR_TRAIL", "EMA20_TRAIL", "SWING_TRAIL", "POINTS", "PERCENT", "NONE"}


def get_system_default_runtime_config() -> dict[str, Any]:
    """Return a safe copy of the universal AlgoAgentX runtime config."""
    return deepcopy(SYSTEM_DEFAULT_RUNTIME_CONFIG)


def get_default_runtime_config_schema(strategy_hint: str | None = None) -> dict[str, Any]:
    """Return a light default schema based on a strategy hint/name/type."""
    hint = (strategy_hint or "").lower()
    if "smc" in hint or "liquidity" in hint or "bos" in hint:
        return deepcopy(SMC_RUNTIME_CONFIG_SCHEMA)
    if "ema" in hint or "moving average" in hint or "stockburner" in hint:
        return deepcopy(EMA_RUNTIME_CONFIG_SCHEMA)
    return {"strategy_params": {}}


def _to_plain_json(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, Mapping):
        return {str(k): _to_plain_json(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_to_plain_json(v) for v in value]
    return value


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return {str(k): _to_plain_json(v) for k, v in value.items()}
    return {}


def deep_merge_runtime_config(base: Any, override: Any) -> dict[str, Any]:
    """Deep merge runtime configs without mutating either input."""
    merged = deepcopy(_as_dict(base))
    override_dict = _as_dict(override)

    for key, value in override_dict.items():
        if isinstance(value, Mapping) and isinstance(merged.get(key), Mapping):
            merged[key] = deep_merge_runtime_config(merged[key], value)
        else:
            merged[key] = deepcopy(_to_plain_json(value))
    return merged


def _num(value: Any, default: float | None = None) -> float | None:
    if value is None or value == "":
        return default
    try:
        return float(value)
    except Exception:
        return default


def _int(value: Any, default: int | None = None) -> int | None:
    number = _num(value, None)
    if number is None:
        return default
    return int(number)


def _bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return bool(value)


def normalize_runtime_config(config: Any) -> dict[str, Any]:
    """Merge with system defaults and normalize known values/types."""
    normalized = deep_merge_runtime_config(get_system_default_runtime_config(), config)

    risk = normalized.setdefault("risk", {})
    risk["initial_capital"] = _num(risk.get("initial_capital"), 1000) or 1000
    risk["risk_percent"] = _num(risk.get("risk_percent"), 0.01) or 0.0
    risk["position_size_mode"] = str(risk.get("position_size_mode") or "RISK_BASED").upper()
    risk["fixed_lot"] = _num(risk.get("fixed_lot"), None)
    risk["fixed_quantity"] = _num(risk.get("fixed_quantity"), None)
    risk["max_lot_cap"] = _num(risk.get("max_lot_cap"), None)
    risk["max_quantity_cap"] = _num(risk.get("max_quantity_cap"), None)

    execution = normalized.setdefault("execution", {})
    execution["entry_mode"] = str(execution.get("entry_mode") or "NEXT_CANDLE_OPEN").upper()
    execution["exit_on_opposite_signal"] = _bool(execution.get("exit_on_opposite_signal"), True)
    execution["allow_long"] = _bool(execution.get("allow_long"), True)
    execution["allow_short"] = _bool(execution.get("allow_short"), True)
    execution["max_trades_per_day"] = _int(execution.get("max_trades_per_day"), None)
    execution["max_open_positions"] = max(1, _int(execution.get("max_open_positions"), 1) or 1)
    execution["intraday_square_off"] = _bool(execution.get("intraday_square_off"), False)
    execution["square_off_time"] = str(execution.get("square_off_time") or "15:15")

    sl_tp = normalized.setdefault("sl_tp", {})
    sl_tp["sl_mode"] = str(sl_tp.get("sl_mode") or "ATR").upper()
    if sl_tp["sl_mode"] == "FIXED_PRICE_RISK_PCT":
        sl_tp["sl_mode"] = "FIXED_PERCENT"
    sl_tp["rr_ratio"] = _num(sl_tp.get("rr_ratio"), 2) or 0
    sl_tp["atr_period"] = max(1, _int(sl_tp.get("atr_period"), 14) or 14)
    sl_tp["atr_multiplier"] = _num(sl_tp.get("atr_multiplier"), 1.5) or 0
    sl_tp["swing_lookback"] = max(1, _int(sl_tp.get("swing_lookback"), 5) or 5)
    sl_tp["fixed_price_risk_pct"] = _num(sl_tp.get("fixed_price_risk_pct"), 0.002) or 0
    sl_tp["use_strategy_suggested_sl"] = _bool(sl_tp.get("use_strategy_suggested_sl"), False)

    trade_management = normalized.setdefault("trade_management", {})
    trade_management["break_even_enabled"] = _bool(trade_management.get("break_even_enabled"), False)
    trade_management["break_even_trigger_r"] = _num(trade_management.get("break_even_trigger_r"), 1) or 0
    trade_management["break_even_offset_points"] = _num(trade_management.get("break_even_offset_points"), 0) or 0
    trade_management["trailing_enabled"] = _bool(trade_management.get("trailing_enabled"), False)
    trade_management["trailing_mode"] = str(trade_management.get("trailing_mode") or "ATR_TRAIL").upper()
    trade_management["trail_start_r"] = _num(trade_management.get("trail_start_r"), 1.5) or 0
    trade_management["trail_atr_multiplier"] = _num(trade_management.get("trail_atr_multiplier"), 1) or 0
    trade_management["partial_exit_enabled"] = _bool(trade_management.get("partial_exit_enabled"), False)
    trade_management["partial_exit_at_r"] = _num(trade_management.get("partial_exit_at_r"), 1) or 0
    trade_management["partial_exit_percent"] = _num(trade_management.get("partial_exit_percent"), 0.5) or 0

    if not isinstance(normalized.get("strategy_params"), Mapping):
        normalized["strategy_params"] = {}

    return normalized


def validate_runtime_config(config: Any) -> dict[str, Any]:
    """Return validation result. Does not raise, so API/backtest callers remain safe."""
    normalized = normalize_runtime_config(config)
    errors: list[str] = []

    risk = normalized["risk"]
    if risk["initial_capital"] <= 0:
        errors.append("risk.initial_capital must be greater than 0")
    if risk["risk_percent"] <= 0:
        errors.append("Risk percent must be greater than 0.")
    if risk["risk_percent"] > 0.10:
        errors.append("Risk percent is too high. Maximum allowed risk per trade is 10%.")
    if risk["position_size_mode"] not in ALLOWED_POSITION_SIZE_MODES:
        errors.append("Position size mode must be RISK_BASED, FIXED_LOT, or FIXED_QUANTITY.")
    if risk["position_size_mode"] == "FIXED_LOT" and not risk.get("fixed_lot"):
        errors.append("Fixed lot is required when position size mode is FIXED_LOT.")
    if risk["position_size_mode"] == "FIXED_QUANTITY" and not risk.get("fixed_quantity"):
        errors.append("Fixed quantity is required when position size mode is FIXED_QUANTITY.")

    execution = normalized["execution"]
    if execution["entry_mode"] not in ALLOWED_ENTRY_MODES:
        errors.append("Entry mode is invalid.")
    if not execution["allow_long"] and not execution["allow_short"]:
        errors.append("At least one of execution.allow_long or execution.allow_short must be true")
    if execution.get("max_trades_per_day") is not None and execution["max_trades_per_day"] <= 0:
        errors.append("execution.max_trades_per_day must be positive when provided")

    sl_tp = normalized["sl_tp"]
    if sl_tp["sl_mode"] not in ALLOWED_SL_MODES:
        errors.append("SL mode is invalid. Use ATR, SWING, FIXED_PERCENT, or STRATEGY_SUGGESTED.")
    if sl_tp["rr_ratio"] <= 0:
        errors.append("RR ratio must be greater than 0.")
    if sl_tp["rr_ratio"] > 10:
        errors.append("RR ratio is too high. Keep RR ratio at 10 or lower for stable backtests.")
    if sl_tp["atr_period"] < 2:
        errors.append("ATR period must be greater than zero.")
    if sl_tp["atr_multiplier"] <= 0:
        errors.append("ATR multiplier must be greater than zero.")

    trade_management = normalized["trade_management"]
    if trade_management["trailing_mode"] not in ALLOWED_TRAILING_MODES:
        errors.append("Trailing mode is invalid.")
    if trade_management["partial_exit_enabled"] and not (0 < trade_management["partial_exit_percent"] <= 1):
        errors.append("Partial exit percent must be between 1% and 100%.")
    if trade_management["break_even_trigger_r"] <= 0:
        errors.append("Breakeven trigger R must be greater than zero.")
    if trade_management["trail_start_r"] <= 0:
        errors.append("Trail start R must be greater than zero.")

    return {"valid": not errors, "errors": errors, "config": normalized}


def _instrument_runtime_defaults(instrument: Any) -> dict[str, Any]:
    if instrument is None:
        return {}

    account_currency = getattr(instrument, "account_currency", None)
    quantity_mode = getattr(instrument, "quantity_mode", None)
    data: dict[str, Any] = {}

    if account_currency:
        data.setdefault("risk", {})["account_currency"] = account_currency

    # Keep this light in Phase 2C: instrument master informs currency now;
    # actual sizing remains in Phase 2B risk engine/backtest integration later.
    if quantity_mode:
        data.setdefault("instrument", {})["quantity_mode"] = quantity_mode

    return data


def resolve_runtime_config(
    strategy: Any = None,
    instrument: Any = None,
    user_override: Any = None,
    strategy_preset: Any = None,
) -> dict[str, Any]:
    """
    Resolve runtime config using the required merge order:
    system defaults + instrument defaults + strategy defaults + preset + user override.
    """
    merged = get_system_default_runtime_config()
    merged = deep_merge_runtime_config(merged, _instrument_runtime_defaults(instrument))

    if strategy is not None:
        merged = deep_merge_runtime_config(merged, getattr(strategy, "default_runtime_config", None))

    preset_config = None
    if isinstance(strategy_preset, Mapping):
        preset_config = strategy_preset.get("config_json") or strategy_preset.get("config")
    elif strategy_preset is not None:
        preset_config = getattr(strategy_preset, "config_json", None)
    merged = deep_merge_runtime_config(merged, preset_config)

    merged = deep_merge_runtime_config(merged, user_override)
    return normalize_runtime_config(merged)
