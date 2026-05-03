from __future__ import annotations

from typing import Any

RISK_ENGINE_VERSION = "2J-risk-engine-guardrails-v1"
PNL_ENGINE_VERSION = "2J-pnl-engine-guardrails-v1"
MAX_BACKTEST_RISK_PERCENT = 0.10
WARN_BACKTEST_RISK_PERCENT = 0.03
MAX_CANDLES_SYNC_BACKTEST = 250_000


def _as_float(value: Any, default: float | None = None) -> float | None:
    if value is None or value == "":
        return default
    try:
        return float(value)
    except Exception:
        return default


def _as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on", "y"}
    return bool(value)


def validate_instrument_spec(spec: dict[str, Any] | None, *, live: bool = False) -> dict[str, Any]:
    """Beginner-friendly instrument spec validation for backtest/live guardrails."""
    errors: list[str] = []
    warnings: list[str] = []
    spec = spec or {}
    symbol = str(spec.get("symbol") or "Selected instrument")
    quantity_mode = str(spec.get("quantity_mode") or "").upper()

    if not spec:
        errors.append("Instrument spec is missing. Please ask admin to configure Market Master before running.")
        return {"valid": False, "errors": errors, "warnings": warnings}

    if quantity_mode not in {"LOTS", "SHARES", "UNITS", "CONTRACTS"}:
        errors.append(f"{symbol} quantity mode is invalid. Please ask admin to configure Market Master quantity_mode.")

    tick_size = _as_float(spec.get("tick_size"), None)
    if tick_size is None or tick_size <= 0:
        errors.append(f"{symbol} instrument spec is missing tick_size. Please ask admin to configure Market Master.")

    if not spec.get("account_currency"):
        errors.append(f"{symbol} instrument spec is missing account_currency. Please ask admin to configure Market Master.")

    if quantity_mode == "LOTS":
        tick_value = _as_float(spec.get("tick_value_per_lot"), None)
        lot_step = _as_float(spec.get("lot_step"), None)
        min_lot = _as_float(spec.get("min_lot"), None)
        if tick_value is None or tick_value <= 0:
            errors.append(f"{symbol} instrument spec is missing tick_value_per_lot. Please ask admin to configure Market Master.")
        if lot_step is None or lot_step <= 0:
            errors.append(f"{symbol} instrument spec is missing lot_step. Please ask admin to configure Market Master.")
        if min_lot is None or min_lot <= 0:
            errors.append(f"{symbol} instrument spec is missing min_lot. Please ask admin to configure Market Master.")
    elif quantity_mode in {"SHARES", "UNITS", "CONTRACTS"}:
        qty_step = _as_float(spec.get("quantity_step"), None)
        min_qty = _as_float(spec.get("min_quantity"), None)
        if qty_step is None or qty_step <= 0:
            errors.append(f"{symbol} instrument spec is missing quantity_step. Please ask admin to configure Market Master.")
        if min_qty is None or min_qty <= 0:
            errors.append(f"{symbol} instrument spec is missing min_quantity. Please ask admin to configure Market Master.")

    if live and not _as_bool(spec.get("is_tradeable_live"), True):
        errors.append(f"{symbol} is not enabled for live trading in Market Master.")

    return {"valid": not errors, "errors": errors, "warnings": warnings}


def validate_backtest_guardrails(runtime_config: dict[str, Any] | None, instrument_spec: dict[str, Any] | None, *, capital: float, candle_count: int | None = None) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    runtime_config = runtime_config or {}
    risk = runtime_config.get("risk") or {}
    risk_percent = _as_float(risk.get("risk_percent"), 0.01) or 0.0

    if capital <= 0:
        errors.append("Initial capital must be greater than 0.")
    if risk_percent <= 0:
        errors.append("Risk percent must be greater than 0.")
    if risk_percent > MAX_BACKTEST_RISK_PERCENT:
        errors.append("Risk percent is too high. Maximum allowed risk per trade is 10%.")
    elif risk_percent > WARN_BACKTEST_RISK_PERCENT:
        warnings.append("Risk percent is above 3%. This is high risk for most trading systems.")

    spec_result = validate_instrument_spec(instrument_spec, live=False)
    errors.extend(spec_result.get("errors") or [])
    warnings.extend(spec_result.get("warnings") or [])

    if candle_count is not None and candle_count > MAX_CANDLES_SYNC_BACKTEST:
        errors.append(
            f"Selected dataset has {candle_count:,} candles, which may timeout in sync mode. Use a smaller range/timeframe or queue mode."
        )

    return {"valid": not errors, "errors": errors, "warnings": warnings}


def build_rejection_summary(reasons: list[str] | dict[str, int] | None) -> dict[str, int]:
    if not reasons:
        return {}
    if isinstance(reasons, dict):
        return {str(k): int(v) for k, v in reasons.items()}
    summary: dict[str, int] = {}
    for reason in reasons:
        key = str(reason or "Unknown rejection")
        summary[key] = summary.get(key, 0) + 1
    return summary
