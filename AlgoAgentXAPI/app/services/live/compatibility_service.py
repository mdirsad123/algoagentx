from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...db.models import BrokerAccount, LiveMarketCandle, Strategy, StrategyDeployment
from ..brokers.factory import get_broker_code
from ..trading.guardrails import validate_instrument_spec
from .broker_candle_service import get_latest_closed_candles
from .capital_service import get_effective_trading_capital
from .order_preview_service import find_live_instrument_spec, resolve_live_runtime_config
from .strategy_runner import _candles_to_dataframe, _run_strategy_generate, extract_latest_signal_payload
from ..strategy_registry import resolve_strategy

PASS = "PASS"
WARNING = "WARNING"
FAIL = "FAIL"


def _check(name: str, status: str, message: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"name": name, "status": status, "message": message}
    if data:
        payload["data"] = data
    return payload


def _overall(checks: list[dict[str, Any]]) -> str:
    if any(c.get("status") == FAIL for c in checks):
        return FAIL
    if any(c.get("status") == WARNING for c in checks):
        return WARNING
    return PASS


def _mode(deployment: StrategyDeployment) -> str:
    return str(getattr(deployment, "mode", "DEMO") or "DEMO").upper()


def _sl_mode(config: dict[str, Any] | None) -> str:
    sl_tp = (config or {}).get("sl_tp") if isinstance(config, dict) else {}
    if not isinstance(sl_tp, dict):
        sl_tp = {}
    return str(sl_tp.get("sl_mode") or "ATR").upper().replace(" ", "_")


def _has_signal_contract_columns(columns: list[str]) -> bool:
    normalized = {str(c).strip().lower() for c in columns}
    return bool(normalized.intersection({"position", "signal"}))


def _positive(value: Any) -> bool:
    try:
        return Decimal(str(value or "0")) > 0
    except Exception:
        return False


async def run_live_compatibility_check(db: AsyncSession, deployment_id: UUID | str) -> dict[str, Any]:
    deployment = (await db.execute(select(StrategyDeployment).where(StrategyDeployment.id == deployment_id))).scalar_one_or_none()
    if deployment is None:
        return {"status": FAIL, "summary": "Deployment not found", "checks": [_check("Deployment", FAIL, "Deployment was not found.")]}

    checks: list[dict[str, Any]] = []
    mode = _mode(deployment)

    strategy = (await db.execute(select(Strategy).where(Strategy.id == deployment.strategy_id))).scalar_one_or_none()
    if strategy is None:
        checks.append(_check("Strategy code", FAIL, "Strategy was not found."))
        return {"status": FAIL, "summary": "Live compatibility failed", "checks": checks}

    strategy_params = strategy.parameters if isinstance(strategy.parameters, dict) else {}
    try:
        strategy_class, params, canonical_name = resolve_strategy(strategy.id, strategy.name, strategy_params)
        checks.append(_check("Strategy code", PASS, f"Strategy code resolved as {canonical_name}.", {"canonical_strategy": canonical_name}))
    except Exception as exc:
        checks.append(_check("Strategy code", FAIL, f"Strategy code could not be resolved: {exc}"))
        return {"status": FAIL, "summary": "Live compatibility failed", "checks": checks}

    _, instrument_spec = await find_live_instrument_spec(db, symbol=getattr(deployment, "instrument", None))
    if instrument_spec is None:
        checks.append(_check("Instrument spec", FAIL, "Instrument Master spec is missing for this deployment instrument."))
    else:
        validation = validate_instrument_spec(instrument_spec, live=True)
        valid = bool(validation.get("valid"))
        errors = validation.get("errors") or []
        required_labels = ["quantity_mode", "tick_size", "tick_value_per_lot/contract_size", "min_lot/lot_step", "account_currency"]
        checks.append(_check("Instrument spec", PASS if valid else FAIL, "Instrument spec is complete for live risk sizing." if valid else " ".join(errors) or "Instrument spec is incomplete.", {"required": required_labels, "spec": instrument_spec}))

    try:
        runtime_config = await resolve_live_runtime_config(db, deployment=deployment)
        sl_mode = _sl_mode(runtime_config)
        checks.append(_check("Runtime config", PASS, f"Runtime config resolved. SL mode = {sl_mode}.", {"sl_mode": sl_mode, "runtime_config": runtime_config}))
    except Exception as exc:
        runtime_config = {}
        sl_mode = "ATR"
        checks.append(_check("Runtime config", FAIL, f"Runtime config is invalid: {exc}"))

    broker = None
    if mode in {"DEMO", "LIVE"}:
        if deployment.broker_account_id:
            broker = (await db.execute(select(BrokerAccount).where(BrokerAccount.id == deployment.broker_account_id))).scalar_one_or_none()
        if broker is None:
            checks.append(_check("Broker capital", FAIL, "Broker account is required for DEMO/LIVE compatibility."))
        elif str(getattr(broker, "status", "") or "").upper() != "CONNECTED":
            checks.append(_check("Broker capital", FAIL, "Broker account must be CONNECTED before live order sizing."))
        else:
            capital = get_effective_trading_capital(deployment, broker)
            source = capital.effective_capital_source
            is_broker_source = source in {"BROKER_EQUITY", "BROKER_BALANCE", "BROKER_FREE_MARGIN"}
            checks.append(_check("Broker capital", PASS if is_broker_source and capital.effective_capital > 0 else FAIL, f"Capital source: {source}." if is_broker_source else "Broker capital is unavailable. Sync broker account before live order sizing.", {"effective_capital": str(capital.effective_capital), "effective_capital_source": source, "broker_code": get_broker_code(broker)}))
    else:
        checks.append(_check("Broker capital", WARNING, "PAPER deployments are deprecated. Create a DEMO or LIVE broker deployment."))

    candles = await get_latest_closed_candles(db, deployment.id, limit=300)
    if len(candles) < 2:
        checks.append(_check("Strategy generates DataFrame", FAIL, f"Only {len(candles)} closed candles found. Refresh broker candles before compatibility check."))
        checks.append(_check("Signal contract", FAIL, "Cannot validate signal contract without generated strategy output."))
        checks.append(_check("Strategy SL output", FAIL if sl_mode == "STRATEGY_SUGGESTED" else WARNING, "Cannot validate strategy SL output without generated strategy output."))
        status = _overall(checks)
        return {"status": status, "summary": "Live compatibility failed" if status == FAIL else "Live compatibility has warnings", "checks": checks}

    try:
        df = _candles_to_dataframe(candles)
        generated = _run_strategy_generate(strategy_class(df, **params))
        columns = [str(c) for c in getattr(generated, "columns", [])]
        if generated is None or generated.empty:
            checks.append(_check("Strategy generates DataFrame", FAIL, "Strategy returned an empty DataFrame."))
        else:
            checks.append(_check("Strategy generates DataFrame", PASS, f"Strategy generated {len(generated)} rows.", {"columns": columns[-30:]}))
        has_contract = _has_signal_contract_columns(columns)
        checks.append(_check("Signal contract", PASS if has_contract else FAIL, "Signal contract found: Position or signal column exists." if has_contract else "Strategy output must include Position or signal column for live runner."))
        signal_payload = extract_latest_signal_payload(generated)
        signal_type = str(signal_payload.get("signal_type") or "HOLD")
        strategy_sl = signal_payload.get("strategy_stop_loss")
        strategy_tp = signal_payload.get("strategy_target")
        if sl_mode == "STRATEGY_SUGGESTED" and signal_type in {"BUY", "SELL"}:
            if strategy_sl is None:
                checks.append(_check("Strategy SL output", FAIL, "STRATEGY_SUGGESTED is selected but latest BUY/SELL row did not produce strategy_stop_loss.", signal_payload))
            elif not _positive(strategy_sl):
                checks.append(_check("Strategy SL output", FAIL, "strategy_stop_loss is present but invalid.", signal_payload))
            elif strategy_tp is None:
                checks.append(_check("Strategy SL output", WARNING, "strategy_stop_loss is valid. strategy_target is missing, so TP will be calculated from RR.", signal_payload))
            else:
                checks.append(_check("Strategy SL output", PASS, "Strategy provided valid SL/TP for latest BUY/SELL signal.", signal_payload))
        elif sl_mode == "STRATEGY_SUGGESTED":
            checks.append(_check("Strategy SL output", PASS, f"Latest signal is {signal_type}; strategy_stop_loss is required only for BUY/SELL auto execution.", signal_payload))
        else:
            checks.append(_check("Strategy SL output", PASS, f"SL mode is {sl_mode}; strategy_stop_loss is not required for compatibility.", signal_payload))
    except Exception as exc:
        checks.append(_check("Strategy generates DataFrame", FAIL, f"Strategy execution failed during compatibility check: {exc}"))
        checks.append(_check("Signal contract", FAIL, "Cannot validate signal contract because strategy execution failed."))
        checks.append(_check("Strategy SL output", FAIL if sl_mode == "STRATEGY_SUGGESTED" else WARNING, "Cannot validate strategy SL output because strategy execution failed."))

    status = _overall(checks)
    if status == PASS:
        summary = "Live compatible"
    elif status == WARNING:
        summary = "Live compatible with warnings"
    else:
        summary = "Live compatibility failed"
    return {"status": status, "summary": summary, "checks": checks}


def compatibility_failed(result: dict[str, Any]) -> bool:
    return str(result.get("status") or "FAIL").upper() == FAIL
