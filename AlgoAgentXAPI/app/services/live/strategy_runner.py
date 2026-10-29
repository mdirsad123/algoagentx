from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Any, Optional
import math
import logging
import hashlib
import time
from uuid import UUID

import pandas as pd
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from ...db.models import BrokerAccount, LiveOrder, LiveSignal, LiveTradeLog, Strategy, StrategyDeployment
from ...core.redis_manager import redis_manager
from ..strategy_registry import resolve_strategy
from .execution_engine import execute_signal
from .order_preview_service import build_live_order_preview, resolve_live_runtime_config
from ..brokers.factory import get_broker_code
from .broker_candle_service import get_deployment_candle_history_status, get_latest_closed_candles, load_live_candles_for_runner, refresh_deployment_candles
from .pnl_service import to_decimal
from .runner_scheduler import calculate_next_runner_after_candle, calculate_next_runner_at, ensure_utc
from ..live_trading.paper_position_manager import process_paper_positions_for_deployment
from .live_latency_trace_service import LiveLatencyTraceService
from .deployment_lock import try_deployment_xact_lock
from .strategy_history_profile import resolve_live_strategy_profile, runtime_contract_violations
from .history_warmup_queue import enqueue_history_warmup
from .runner_diagnostics import StageClock, profile_generate
from .retained_strategy_state import (
    retained_states, is_opted_in, signature as incremental_signature,
    signal_runtime_identity, fingerprint_fields,
)
from .runner_cache import history_ready_cache
from .incremental_adapter_registry import select_registered_adapter, configured_max_advances
from .signal_contract import (
    _normalize_signal_value, _json_safe_value, _safe_float, _first_present,
    _safe_row_dict, extract_latest_signal_payload,
)
from ...core.config import settings
from .runner_scheduler import parse_timeframe_to_seconds

logger = logging.getLogger(__name__)


@dataclass
class StrategyRunnerResult:
    success: bool
    deployment_id: str
    strategy_name: str | None
    latest_candle_time: str | None
    signal: str | None
    executed: bool
    order_id: str | None
    broker_order_id: str | None
    signal_id: str | None
    duplicate: bool
    message: str
    latest_runner_log: str | None = None
    order_status: str | None = None
    error_message: str | None = None
    symbol: str | None = None
    entry_plan: dict[str, Any] | None = None
    risk_preview: dict[str, Any] | None = None
    final_action: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "deployment_id": self.deployment_id,
            "strategy_name": self.strategy_name,
            "latest_candle_time": self.latest_candle_time,
            "signal": self.signal,
            "executed": self.executed,
            "order_id": self.order_id,
            "broker_order_id": self.broker_order_id,
            "signal_id": self.signal_id,
            "duplicate": self.duplicate,
            "message": self.message,
            "latest_runner_log": self.latest_runner_log,
            "order_status": self.order_status,
            "error_message": self.error_message,
            "symbol": self.symbol,
            "entry_plan": self.entry_plan,
            "risk_preview": self.risk_preview,
            "final_action": self.final_action,
        }


def _normalize_dt(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    text = str(value or "").strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except Exception:
        return datetime.now(timezone.utc)


def _mark_candle_processed(deployment: StrategyDeployment, candle_time: datetime) -> None:
    """Advance the durable cursor only after a candle completed successfully."""
    current = getattr(deployment, "last_processed_candle_time", None)
    if current is not None and current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    if current is None or candle_time > current:
        deployment.last_processed_candle_time = candle_time


async def _log(
    db: AsyncSession,
    deployment: StrategyDeployment,
    event_type: str,
    message: str,
    level: str = "INFO",
    metadata: Optional[dict[str, Any]] = None,
) -> None:
    db.add(
        LiveTradeLog(
            deployment_id=deployment.id,
            user_id=deployment.user_id,
            event_type=event_type,
            level=level,
            message=message,
            metadata_json=metadata or {},
        )
    )


def _preview_cap_applied(preview: dict[str, Any] | None) -> bool:
    preview = preview or {}
    risk_metadata = preview.get("risk_metadata") if isinstance(preview.get("risk_metadata"), dict) else {}
    risk_engine = preview.get("risk_engine") if isinstance(preview.get("risk_engine"), dict) else {}
    raw_lot = _safe_float(risk_metadata.get("raw_lot") or risk_metadata.get("requested_lot") or risk_engine.get("raw_lot_size"))
    final_lot = _safe_float(risk_metadata.get("final_lot") or preview.get("final_lot_size") or risk_engine.get("final_lot_size"))
    max_lot = _safe_float(risk_metadata.get("max_lot_cap") or risk_engine.get("max_lot_cap"))
    raw_qty = _safe_float(risk_metadata.get("raw_quantity") or risk_metadata.get("requested_quantity") or risk_engine.get("raw_quantity"))
    final_qty = _safe_float(risk_metadata.get("final_quantity") or preview.get("final_quantity") or risk_engine.get("final_quantity"))
    max_qty = _safe_float(risk_metadata.get("max_quantity_cap") or risk_engine.get("max_quantity_cap"))
    if raw_lot is not None and final_lot is not None and max_lot is not None and raw_lot > final_lot and final_lot <= max_lot:
        return True
    if raw_qty is not None and final_qty is not None and max_qty is not None and raw_qty > final_qty and final_qty <= max_qty:
        return True
    return False


def _broker_payload_ok(preview: dict[str, Any] | None) -> bool:
    preview = preview or {}
    payload = preview.get("broker_payload_preview") or preview.get("broker_order_payload_preview")
    if not isinstance(payload, dict) or not payload.get("side") or not payload.get("symbol"):
        return False
    has_size = payload.get("volume") not in (None, "", 0) or payload.get("quantity") not in (None, "", 0)
    return bool(has_size and payload.get("sl") is not None and payload.get("tp") is not None)


async def _log_live_engine_qa_preview(
    db: AsyncSession,
    deployment: StrategyDeployment,
    *,
    signal_id: str | None = None,
    signal_type: str | None = None,
    signal_payload: dict[str, Any] | None = None,
    preview: dict[str, Any] | None = None,
    context: str = "runner",
) -> None:
    """Write final end-to-end QA pass logs for strategy output, SL/TP, risk and broker payload.

    These logs make the demo strategy and real Support/Resistance strategy easy to
    verify without changing the execution architecture. FAIL/WARNING states are
    already represented by the normal preview/readiness logs; these PASS events are
    emitted only when each contract stage is satisfied.
    """
    signal_payload = signal_payload or {}
    preview = preview or {}
    base = {
        "context": context,
        "signal_id": signal_id,
        "signal_type": signal_type or signal_payload.get("signal_type"),
        "strategy_stop_loss": signal_payload.get("strategy_stop_loss") or preview.get("strategy_stop_loss"),
        "strategy_target": signal_payload.get("strategy_target") or preview.get("strategy_target"),
    }
    await _log(db, deployment, "LIVE_ENGINE_QA_SIGNAL_CONTRACT_PASS", "Live engine signal contract validated", metadata={**base, "signal_reason": signal_payload.get("signal_reason")})

    entry_plan = preview.get("entry_plan") if isinstance(preview.get("entry_plan"), dict) else {}
    if entry_plan.get("status") == "OK" and preview.get("stop_loss") is not None and preview.get("target") is not None:
        await _log(
            db,
            deployment,
            "LIVE_ENGINE_QA_SLTP_PASS",
            "Live engine SL/TP contract validated",
            metadata={
                **base,
                "entry_price": preview.get("entry_price"),
                "final_stop_loss": preview.get("stop_loss"),
                "final_target": preview.get("target"),
                "sl_mode": entry_plan.get("sl_mode"),
                "stop_loss_source": entry_plan.get("stop_loss_source"),
                "target_source": entry_plan.get("target_source"),
                "risk_points": entry_plan.get("risk_points"),
                "reward_points": entry_plan.get("reward_points"),
                "rr_ratio": entry_plan.get("rr_ratio"),
            },
        )

    if str(preview.get("validation_status") or preview.get("status") or "").upper() == "OK":
        risk_metadata = preview.get("risk_metadata") if isinstance(preview.get("risk_metadata"), dict) else {}
        await _log(
            db,
            deployment,
            "LIVE_ENGINE_QA_RISK_PASS",
            "Live engine risk sizing validated",
            metadata={
                **base,
                "effective_capital": risk_metadata.get("effective_capital") or preview.get("effective_capital"),
                "effective_capital_source": risk_metadata.get("effective_capital_source") or preview.get("effective_capital_source"),
                "risk_percent": risk_metadata.get("risk_percent"),
                "risk_amount": risk_metadata.get("risk_amount") or preview.get("risk_amount"),
                "position_size_mode": risk_metadata.get("position_size_mode"),
                "raw_lot": risk_metadata.get("raw_lot"),
                "final_lot": risk_metadata.get("final_lot") or preview.get("final_lot_size"),
                "raw_quantity": risk_metadata.get("raw_quantity"),
                "final_quantity": risk_metadata.get("final_quantity") or preview.get("final_quantity"),
                "max_lot_cap": risk_metadata.get("max_lot_cap"),
                "cap_applied": _preview_cap_applied(preview),
            },
        )
        if _broker_payload_ok(preview):
            await _log(
                db,
                deployment,
                "LIVE_ENGINE_QA_BROKER_PAYLOAD_PASS",
                "Live engine broker payload validated",
                metadata={
                    **base,
                    "broker_payload_preview": preview.get("broker_payload_preview") or preview.get("broker_order_payload_preview"),
                    "cap_applied": _preview_cap_applied(preview),
                },
            )


def _validate_strategy_gate(strategy: Strategy, mode: str) -> None:
    visibility = str(getattr(strategy, "visibility", "") or "").upper()
    if visibility != "PUBLIC":
        raise HTTPException(status_code=400, detail="Only published strategies can run live")
    mode = (mode or "PAPER").upper()
    if mode == "LIVE" and not bool(getattr(strategy, "is_live_approved", False)):
        raise HTTPException(status_code=400, detail="Strategy is not enabled for LIVE deployment")
    if mode == "PAPER" and not bool(getattr(strategy, "is_deployable_paper", False)):
        raise HTTPException(status_code=400, detail="Strategy is not enabled for PAPER deployment")
    if mode == "DEMO" and not bool(getattr(strategy, "is_deployable_demo", False)):
        raise HTTPException(status_code=400, detail="Strategy is not enabled for DEMO broker deployment")


def _candles_to_dataframe(candles: list[dict[str, Any]]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    # get_latest_closed_candles returns newest first. Strategies expect ascending time.
    for candle in reversed(candles):
        rows.append(
            {
                "Date": _normalize_dt(candle.get("candle_time")),
                "Open": float(to_decimal(candle.get("open"))),
                "High": float(to_decimal(candle.get("high"))),
                "Low": float(to_decimal(candle.get("low"))),
                "Close": float(to_decimal(candle.get("close"))),
                "Volume": float(to_decimal(candle.get("volume"), "0")),
            }
        )
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values("Date").reset_index(drop=True)
    return df


def _extract_latest_signal(result_df: pd.DataFrame) -> str:
    return str(extract_latest_signal_payload(result_df).get("signal_type") or "HOLD")


def _run_strategy_generate(strategy_instance: Any) -> pd.DataFrame:
    for method_name in ("generate", "generate_signals", "run"):
        method = getattr(strategy_instance, method_name, None)
        if callable(method):
            generated = method()
            if isinstance(generated, pd.DataFrame):
                return generated
    df = getattr(strategy_instance, "df", None)
    if isinstance(df, pd.DataFrame):
        return df
    raise ValueError("Strategy did not return a valid DataFrame")


async def _find_duplicate_engine_signal(
    db: AsyncSession,
    deployment_id: UUID,
    candle_time: datetime,
    signal_type: str,
    *,
    strategy_id: str | None = None,
    symbol: str | None = None,
    timeframe: str | None = None,
) -> LiveSignal | None:
    stmt = select(LiveSignal).where(
        LiveSignal.deployment_id == deployment_id,
        LiveSignal.source == "ENGINE",
        LiveSignal.candle_time == candle_time,
        LiveSignal.signal_type == signal_type,
    )
    if strategy_id:
        stmt = stmt.where(LiveSignal.strategy_id == strategy_id)
    if symbol:
        stmt = stmt.where(LiveSignal.symbol == symbol)
    if timeframe:
        stmt = stmt.where(LiveSignal.timeframe == timeframe)
    return (await db.execute(stmt.order_by(LiveSignal.created_at.desc()).limit(1))).scalar_one_or_none()


def _message_for_result(signal_type: str, execute: bool, auto_trade: bool, order: Optional[LiveOrder], duplicate: bool = False) -> str:
    if duplicate:
        return "Duplicate signal ignored"
    if signal_type == "HOLD":
        return "Strategy generated HOLD, no order placed"
    if not execute:
        return f"Dry run completed; strategy generated {signal_type}, no order placed"
    if not auto_trade:
        return "Auto trade disabled; signal saved without order"
    if order is None:
        return f"Strategy generated {signal_type}, but no order was placed"
    if order.status in {"FILLED", "PLACED"}:
        return f"Strategy generated {signal_type} and broker demo order placed" if order.broker_order_id else f"Strategy generated {signal_type}; local order recorded"
    if order.status == "ERROR":
        return f"Broker order failed: {order.error_message or 'Check execution logs'}"
    return f"Strategy generated {signal_type}; order status {order.status}"


async def run_full_dry_test_for_deployment(db: AsyncSession, deployment_id: UUID) -> dict[str, Any]:
    """Run one complete live runner cycle without placing an order or saving a signal."""
    deployment = (await db.execute(select(StrategyDeployment).where(StrategyDeployment.id == deployment_id))).scalar_one_or_none()
    if deployment is None:
        raise HTTPException(status_code=404, detail="Deployment not found")

    steps: list[dict[str, Any]] = []

    def step(name: str, status: str, message: str, data: dict[str, Any] | None = None) -> None:
        steps.append({"name": name, "status": status, "message": message, "data": data or {}})

    mode = str(deployment.mode or "PAPER").upper()
    status = str(deployment.status or "").upper()
    step("Loaded deployment", "PASS" if status == "RUNNING" else "FAIL", f"Deployment is {deployment.status} in {mode} mode.")
    await _log(db, deployment, "LIVE_ENGINE_QA_STARTED", "Live engine final QA dry test started", metadata={"context": "full_dry_test", "mode": mode, "status": status})
    if status != "RUNNING":
        final = "REJECTED"
        return {"success": False, "deployment_id": str(deployment.id), "steps": steps, "final_action": final, "message": "Deployment must be RUNNING for full dry test."}
    if mode not in {"DEMO", "LIVE"}:
        step("Broker mode", "FAIL", "Full dry test is available for broker DEMO/LIVE deployments only.")
        return {"success": False, "deployment_id": str(deployment.id), "steps": steps, "final_action": "REJECTED", "message": "Create a DEMO or LIVE broker deployment for full dry test."}

    strategy = (await db.execute(select(Strategy).where(Strategy.id == deployment.strategy_id))).scalar_one_or_none()
    if strategy is None:
        step("Loaded strategy", "FAIL", "Strategy not found.")
        return {"success": False, "deployment_id": str(deployment.id), "steps": steps, "final_action": "REJECTED", "message": "Strategy not found."}
    _validate_strategy_gate(strategy, mode)
    strategy_params = strategy.parameters if isinstance(strategy.parameters, dict) else {}
    strategy_class, params, canonical_name = resolve_strategy(strategy.id, strategy.name, strategy_params)
    profile = resolve_live_strategy_profile(strategy_class, strategy_params)
    runtime_config = await resolve_live_runtime_config(db, deployment=deployment)
    contract_issues = runtime_contract_violations(strategy_class, runtime_config, strategy_params)
    if contract_issues:
        step("Runtime contract", "FAIL", "Deployment runtime settings do not match this strategy's validated research/live contract.", {"violations": contract_issues})
        return {"success": False, "deployment_id": str(deployment.id), "steps": steps, "final_action": "REJECTED", "message": "Fix runtime-contract mismatches before live execution.", "runtime_contract_violations": contract_issues}
    step("Loaded strategy", "PASS", f"Strategy {strategy.name} is deployable for {mode}.", {"resolved_strategy_class": strategy_class.__name__, "required_history_bars": profile.required_history_bars})

    refresh_warning = None
    if mode in {"DEMO", "LIVE"}:
        try:
            history = await get_deployment_candle_history_status(db, deployment, profile.required_history_bars)
            if not history.get("ready"):
                queued = enqueue_history_warmup(deployment.id, profile.required_history_bars)
                history["warmup_queue"] = queued
                step("Strategy history", "FAIL", f"Only {history.get('stored_count', 0)}/{profile.required_history_bars} required closed candles are available. Background warm-up queued; retry after it completes.", history)
                return {"success": False, "deployment_id": str(deployment.id), "steps": steps, "final_action": "REJECTED", "message": "Strategy warm-up history is still running in background.", "history": history}
            await refresh_deployment_candles(db, deployment.id, count=300)
            step("Refreshed broker candles", "PASS", f"Latest broker candles refreshed for {mode} dry test.", history)
        except Exception as exc:
            refresh_warning = str(exc)
            step("Refreshed broker candles", "WARNING", f"Could not refresh broker candles: {str(exc)[:180]}. Existing stored candles will be used if available.")

    candles = await load_live_candles_for_runner(db, deployment, limit=profile.required_history_bars)
    if len(candles) < profile.required_history_bars:
        step("Loaded candles", "FAIL", f"Only {len(candles)} closed broker candles found by deployment_id. Required {profile.required_history_bars}.")
        return {"success": False, "ok": False, "error_code": "NOT_ENOUGH_LIVE_CANDLES", "deployment_id": str(deployment.id), "instrument": deployment.instrument, "instrument_key": getattr(deployment, "instrument_key", None), "timeframe": deployment.timeframe, "loaded_candles": len(candles), "steps": steps, "final_action": "REJECTED", "message": f"HOLD - Not enough live candles. Loaded {len(candles)} candles, required {profile.required_history_bars}.", "refresh_warning": refresh_warning}
    latest_candle = candles[0]
    latest_candle_time = _normalize_dt(latest_candle.get("candle_time"))
    latest_close = to_decimal(latest_candle.get("close"))
    latest_symbol = str(latest_candle.get("symbol") or deployment.instrument)
    step("Loaded candles", "PASS", f"Loaded {len(candles)} candles. Latest close {latest_close} at {latest_candle_time}.", {"latest_candle_time": latest_candle_time.isoformat(), "latest_price": float(latest_close), "symbol": latest_symbol})

    df = _candles_to_dataframe(candles)
    generated = _run_strategy_generate(strategy_class(df, **params))
    signal_payload = extract_latest_signal_payload(generated)
    signal_type = str(signal_payload.get("signal_type") or "HOLD")
    step("Strategy generated signal", "PASS", f"{canonical_name} generated {signal_type}.", {"signal": signal_type, "signal_reason": signal_payload.get("signal_reason")})
    has_strategy_sltp = signal_payload.get("strategy_stop_loss") is not None and signal_payload.get("strategy_target") is not None
    if signal_type in {"BUY", "SELL"}:
        step(
            "Extracted strategy SL/TP",
            "PASS" if has_strategy_sltp else "WARNING",
            "Strategy provided SL/TP on the latest signal row." if has_strategy_sltp else "Strategy generated BUY/SELL but did not provide strategy SL/TP. Runtime fallback may be used in later execution phases.",
            {
                "strategy_stop_loss": signal_payload.get("strategy_stop_loss"),
                "strategy_target": signal_payload.get("strategy_target"),
                "strategy_risk_points": signal_payload.get("strategy_risk_points"),
                "strategy_reward_points": signal_payload.get("strategy_reward_points"),
                "signal_reason": signal_payload.get("signal_reason"),
            },
        )
    else:
        step("Extracted strategy SL/TP", "PASS", "HOLD/EXIT does not require strategy SL/TP for this dry test.", {"signal": signal_type})
    await _log(
        db,
        deployment,
        "RUNNER_STRATEGY_OUTPUT_EXTRACTED",
        "Strategy output extracted from latest closed candle",
        metadata={
            "signal_type": signal_type,
            "v64_hybrid_monitor_only": force_monitor_no_orders,
            "strategy_stop_loss": signal_payload.get("strategy_stop_loss"),
            "strategy_target": signal_payload.get("strategy_target"),
            "signal_reason": signal_payload.get("signal_reason"),
        },
    )
    from .compatibility_service import run_live_compatibility_check
    compatibility = await run_live_compatibility_check(db, deployment.id)
    compatibility_status = str(compatibility.get("status") or "FAIL").upper()
    step(
        "Live Compatibility",
        "PASS" if compatibility_status == "PASS" else "WARNING" if compatibility_status == "WARNING" else "FAIL",
        compatibility.get("summary") or "Live compatibility checked.",
        {"checks": compatibility.get("checks", [])},
    )
    if compatibility_status == "FAIL":
        step("Final simulated action", "FAIL", "Compatibility failed. Fix failed checks before live auto execution.")
        await db.commit()
        return {"success": False, "deployment_id": str(deployment.id), "strategy_name": canonical_name, "latest_candle_time": latest_candle_time.isoformat(), "signal": signal_type, "steps": steps, "final_action": "REJECTED", "message": "Full dry test rejected: live compatibility failed.", "compatibility": compatibility}

    if signal_type == "HOLD":
        step("Final simulated action", "PASS", "HOLD - no order would be placed.")
        await db.commit()
        return {"success": True, "deployment_id": str(deployment.id), "strategy_name": canonical_name, "latest_candle_time": latest_candle_time.isoformat(), "signal": signal_type, "steps": steps, "final_action": "HOLD", "message": "Full dry test completed: HOLD.", "compatibility": compatibility}

    duplicate = await _find_duplicate_engine_signal(db, deployment.id, latest_candle_time, signal_type, strategy_id=deployment.strategy_id, symbol=latest_symbol, timeframe=deployment.timeframe)
    step("Duplicate signal check", "WARNING" if duplicate else "PASS", "Duplicate signal ignored." if duplicate else "No duplicate signal found.", {"duplicate_signal_id": str(duplicate.id) if duplicate else None})
    if duplicate:
        step("Final simulated action", "WARNING", "Duplicate signal would be ignored.")
        await db.commit()
        return {"success": True, "deployment_id": str(deployment.id), "strategy_name": canonical_name, "latest_candle_time": latest_candle_time.isoformat(), "signal": signal_type, "steps": steps, "duplicate": True, "final_action": "REJECTED", "message": "Duplicate signal would be ignored."}

    broker = (await db.execute(select(BrokerAccount).where(BrokerAccount.id == deployment.broker_account_id))).scalar_one_or_none() if deployment.broker_account_id else None
    broker_code = get_broker_code(broker) if broker is not None else ("PAPER" if mode == "PAPER" else "MT5")
    preview = await build_live_order_preview(
        db,
        deployment=deployment,
        broker_code=broker_code,
        symbol=latest_symbol,
        side=signal_type,
        stop_loss=signal_payload.get("strategy_stop_loss"),
        strategy_target=signal_payload.get("strategy_target"),
        preview_mode="AUTO_LATEST_PRICE",
        strict_instrument=mode in {"DEMO", "LIVE"},
    )
    entry_plan = preview.get("entry_plan") or {}
    await _log_live_engine_qa_preview(db, deployment, signal_type=signal_type, signal_payload=signal_payload, preview=preview, context="full_dry_test")
    preview_ok = str(preview.get("validation_status") or preview.get("status") or "").upper() == "OK"
    step("Calculated SL/TP", "PASS" if entry_plan.get("status") == "OK" else "FAIL", "SL/TP calculated." if entry_plan.get("status") == "OK" else str(preview.get("rejected_reason") or "SL/TP calculation failed."), entry_plan)
    step("Calculated lot/qty", "PASS" if preview_ok else "FAIL", "Risk preview passed." if preview_ok else str(preview.get("rejected_reason") or "Risk preview rejected."), {"quantity_mode": preview.get("quantity_mode"), "lot": preview.get("final_lot_size"), "quantity": preview.get("final_quantity"), "risk": preview.get("actual_risk_amount"), "payload": preview.get("broker_payload_preview")})
    if preview.get("latest_price_warnings"):
        step("Latest price sanity", "WARNING", "; ".join(preview.get("latest_price_warnings") or []))
    else:
        step("Latest price sanity", "PASS", "Latest candle price passed sanity checks.")

    if not preview_ok:
        step("Final simulated action", "FAIL", "Signal would be rejected before order placement.")
        return {"success": False, "deployment_id": str(deployment.id), "strategy_name": canonical_name, "latest_candle_time": latest_candle_time.isoformat(), "signal": signal_type, "steps": steps, "entry_plan": entry_plan, "risk_preview": preview, "final_action": "REJECTED", "message": preview.get("rejected_reason") or "Full dry test rejected."}

    final_action = "WOULD_PLACE_LIVE_ORDER" if mode == "LIVE" else "WOULD_PLACE_DEMO_ORDER"
    step("Safety checks", "PASS", "No real order placed. Safety/risk preview passed for this simulated cycle.")
    step("Final simulated action", "PASS", final_action.replace("_", " "))
    await _log(db, deployment, "RUNNER_FULL_DRY_TEST", f"Full dry test completed: {final_action}", metadata={"signal": signal_type, "entry_plan": entry_plan, "risk_preview": {k: preview.get(k) for k in ["quantity_mode", "final_lot_size", "final_quantity", "actual_risk_amount", "broker_payload_preview"]}})
    await db.commit()
    return {"success": True, "deployment_id": str(deployment.id), "strategy_name": canonical_name, "latest_candle_time": latest_candle_time.isoformat(), "signal": signal_type, "steps": steps, "entry_plan": entry_plan, "risk_preview": preview, "final_action": final_action, "message": f"Full dry test completed: {final_action.replace('_', ' ').title()}"}


async def run_strategy_for_deployment(
    db: AsyncSession,
    deployment_id: UUID,
    execute: bool = True,
    *,
    refresh_broker_candles: bool = True,
    candle_time: datetime | None = None,
    trace_id: str | None = None,
    event_context: dict[str, Any] | None = None,
    suppress_broker_order_for_catchup: bool = False,
) -> dict[str, Any]:
    deployment = (await db.execute(select(StrategyDeployment).where(StrategyDeployment.id == deployment_id))).scalar_one_or_none()
    if deployment is None:
        raise HTTPException(status_code=404, detail="Deployment not found")

    latest_log_message: str | None = None
    canonical_name: str | None = None
    latest_candle_time: datetime | None = None
    latest_symbol: str | None = None
    latency_trace = LiveLatencyTraceService(redis_manager.client if redis_manager.is_available else None)
    stage_clock = StageClock(str(deployment_id), logger)
    runner_total_started = time.perf_counter()

    try:
        locked = await try_deployment_xact_lock(db, deployment.id)
        if not locked:
            latest_log_message = "Another runner is already processing this deployment."
            await _log(db, deployment, "RUNNER_LOCK_SKIPPED", latest_log_message, "WARNING", {"deployment_id": str(deployment.id)})
            await db.commit()
            return StrategyRunnerResult(
                success=True,
                deployment_id=str(deployment.id),
                strategy_name=None,
                latest_candle_time=None,
                signal=None,
                executed=False,
                order_id=None,
                broker_order_id=None,
                signal_id=None,
                duplicate=True,
                message=latest_log_message,
                latest_runner_log=latest_log_message,
                final_action="LOCK_SKIPPED",
            ).to_dict()

        await _log(db, deployment, "RUNNER_STARTED", "Strategy runner started", metadata={"execute": execute, "trace_id": trace_id, "event_context": event_context or {}})
        await _log(db, deployment, "LIVE_ENGINE_QA_STARTED", "Live engine final QA runner cycle started", metadata={"context": "runner", "execute": execute})
        mode = str(deployment.mode or "PAPER").upper()
        status = str(deployment.status or "").upper()
        if status != "RUNNING":
            raise HTTPException(status_code=400, detail=f"Deployment not RUNNING. Current status is {deployment.status}.")
        if mode not in {"PAPER", "DEMO", "LIVE"}:
            raise HTTPException(status_code=400, detail="Strategy runner supports PAPER, DEMO, and LIVE modes")

        if mode == "PAPER":
            try:
                await process_paper_positions_for_deployment(db, deployment.id)
                await _log(db, deployment, "PAPER_POSITION_MANAGER_UPDATED", "Paper positions checked before strategy runner cycle")
            except Exception as exc:
                await _log(db, deployment, "PAPER_POSITION_MANAGER_ERROR", f"Paper position manager failed: {exc}", "WARNING")

        timer = stage_clock.start("resolve_strategy_and_runtime")
        strategy = (await db.execute(select(Strategy).where(Strategy.id == deployment.strategy_id))).scalar_one_or_none()
        if strategy is None:
            raise HTTPException(status_code=404, detail="Strategy not found")
        _validate_strategy_gate(strategy, mode)
        strategy_params = strategy.parameters if isinstance(strategy.parameters, dict) else {}
        strategy_class, params, canonical_name = resolve_strategy(strategy.id, strategy.name, strategy_params)
        profile = resolve_live_strategy_profile(strategy_class, strategy_params)
        runtime_config = await resolve_live_runtime_config(db, deployment=deployment)
        contract_issues = runtime_contract_violations(strategy_class, runtime_config, strategy_params)
        if contract_issues:
            detail = {
                "ok": False,
                "error_code": "RUNTIME_CONTRACT_MISMATCH",
                "message": "HOLD - Deployment runtime settings do not match the strategy research/live contract.",
                "violations": contract_issues,
                "resolved_strategy_class": strategy_class.__name__,
            }
            await _log(db, deployment, "RUNNER_RUNTIME_CONTRACT_MISMATCH", detail["message"], "ERROR", detail)
            await db.commit()
            return {"success": False, **detail, "final_action": "HOLD_RUNTIME_CONTRACT_MISMATCH"}

        # Strictly opt-in runtime adapter. The authoritative DB Strategy source
        # remains FROZEN and used in backtests; only the DEMO runner can select
        # this audited hybrid when all independent approval switches match.
        # Profile/runtime contract intentionally resolved from ORIGINAL class.
        adapter = select_registered_adapter(
            settings=settings, source_code=str(strategy_params.get("source_code") or ""),
            mode=mode, instrument=str(deployment.instrument),
            timeframe_seconds=parse_timeframe_to_seconds(str(deployment.timeframe or "M5")),
            required_history_bars=profile.required_history_bars,
        ) if execute and not refresh_broker_candles else None
        hybrid_class = adapter.strategy_class if adapter else None
        hybrid_reason = adapter.reason if adapter else "disabled"
        hybrid_selected = hybrid_class is not None
        hybrid_monitor_only = bool(adapter and adapter.monitor_only)
        # Operator can keep DEMO Auto Trade ON. Research monitor mode (if
        # requested) never submits broker orders, even on full-history fallback.
        generic_monitor_requested = (
            bool(getattr(settings, "live_incremental_adapter_enabled", False))
            and bool(getattr(settings, "live_incremental_monitor_only", True))
        )
        legacy_monitor_requested = (
            not bool(getattr(settings, "live_incremental_adapter_enabled", False))
            and bool(getattr(settings, "live_v64_hybrid_enabled", False))
            and bool(getattr(settings, "live_v64_hybrid_monitor_only", False))
        )
        force_monitor_no_orders = mode == "DEMO" and (
            generic_monitor_requested or legacy_monitor_requested or suppress_broker_order_for_catchup
        )
        if suppress_broker_order_for_catchup:
            logger.warning("RUNNER_HISTORICAL_CATCHUP_ORDER_SUPPRESSED deployment=%s candle=%s "
                           "reason=state_replay_not_a_current_trade", deployment_id, candle_time)
        if hybrid_selected:
            strategy_class = hybrid_class
            logger.warning(
                "RUNNER_INCREMENTAL_ADAPTER_SELECTED deployment=%s adapter=%s source_sha256=%s "
                "bars=%s mode=%s monitor_only=%s",
                deployment_id, adapter.adapter_id, adapter.source_sha256,
                profile.required_history_bars, mode, hybrid_monitor_only,
            )
            # Preserve the existing WATCH_V64_HYBRID.ps1 log markers.
            logger.warning(
                "RUNNER_V64_HYBRID_SELECTED deployment=%s source_sha256=%s bars=%s "
                "mode=%s monitor_only=%s", deployment_id, adapter.source_sha256,
                profile.required_history_bars, mode, hybrid_monitor_only,
            )
        elif hybrid_reason != "disabled":
            logger.warning("RUNNER_INCREMENTAL_ADAPTER_FALLBACK deployment=%s reason=%s "
                           "mode=FULL_HISTORY", deployment_id, hybrid_reason)
        stage_clock.stop("resolve_strategy_and_runtime", timer)
        timer = stage_clock.start("history_readiness_check")
        authoritative_candle_time = _normalize_dt(candle_time) if candle_time is not None else None
        history_status = None
        if mode in {"DEMO", "LIVE"}:
            history_signature = (
                f"{deployment.strategy_id}|{deployment.broker_account_id}|"
                f"{deployment.timeframe}|{deployment.instrument}|{getattr(deployment, 'instrument_key', None)}"
            )
            history_cached = history_ready_cache.can_reuse(
                deployment.id, required=profile.required_history_bars,
                signature=history_signature, through=authoritative_candle_time,
            )
            if history_cached:
                # Positive result is only a short-lived hint; every FULL_HISTORY
                # load still verifies count and exact requested candle. No
                # strategy BUY/SELL decision is ever read from this cache.
                history_status = {'ready': True, 'required_count': profile.required_history_bars,
                                  'source': 'positive_short_ttl_cache'}
            else:
                history_status = await get_deployment_candle_history_status(
                    db,
                    deployment,
                    profile.required_history_bars,
                    through_candle_time=authoritative_candle_time,
                )
                if history_status.get('ready'):
                    history_ready_cache.remember(
                        deployment.id, required=profile.required_history_bars,
                        signature=history_signature, through=authoritative_candle_time,
                    )
            if not history_status.get("ready"):
                history_ready_cache.invalidate(deployment.id)
                history_status["warmup_queue"] = enqueue_history_warmup(deployment.id, profile.required_history_bars)
                detail = {
                    "ok": False,
                    "error_code": "STRATEGY_HISTORY_INSUFFICIENT",
                    "message": f"HOLD - Strategy requires {profile.required_history_bars} closed candles; only {history_status.get('stored_count', 0)} are available. Background warm-up is queued/running.",
                    "required_history_bars": profile.required_history_bars,
                    "stored_history_bars": history_status.get("stored_count", 0),
                    "history": history_status,
                }
                await _log(db, deployment, "RUNNER_STRATEGY_HISTORY_INSUFFICIENT", detail["message"], "WARNING", detail)
                await db.commit()
                return {"success": False, **detail, "final_action": "HOLD_STRATEGY_HISTORY"}

        stage_clock.stop("history_readiness_check", timer)
        refresh_warning = None
        if mode in {"DEMO", "LIVE"} and refresh_broker_candles:
            await _log(db, deployment, "RUNNER_CANDLE_REFRESH_STARTED", "Refreshing latest broker closed candles before strategy run")
            try:
                await refresh_deployment_candles(db, deployment.id, count=300)
            except Exception as exc:
                refresh_warning = str(getattr(exc, "detail", None) or exc)
                await _log(db, deployment, "RUNNER_CANDLE_REFRESH_WARNING", f"Broker candle refresh failed; using stored candles if available: {refresh_warning}", "WARNING", {"deployment_id": str(deployment.id), "instrument": deployment.instrument, "instrument_key": getattr(deployment, "instrument_key", None)})

        # The shared runner is universal; incremental calculation is NOT. A
        # strategy must implement the explicit v1 protocol and have an
        # independently recorded parity approval. All other strategies run the
        # original full-history generate() path without semantic changes.
        source_code = str(strategy_params.get("source_code") or "").strip()
        source_code_sha256 = str(strategy_params.get("source_code_sha256") or "").strip()
        if source_code and not source_code_sha256:
            source_code_sha256 = hashlib.sha256(source_code.encode("utf-8")).hexdigest()
        incremental_allowed = (
            hybrid_selected or is_opted_in(
                strategy_class, strategy_params,
                global_enabled=bool(getattr(settings, "live_incremental_enabled", False)),
            )
        ) and mode in {"DEMO", "LIVE", "PAPER"} and execute and not refresh_broker_candles
        identity_runtime = signal_runtime_identity(
            runtime_config, capital_independent=bool(hybrid_selected and adapter.adapter_id == 'v64_hybrid_v1'),
            configured_capital=deployment.capital,
        )
        identity_runtime['_v64_hybrid_runtime'] = bool(hybrid_selected)
        identity_runtime['_routing'] = {
            'broker_account_id': str(deployment.broker_account_id),
            'mode': mode, 'broker_symbol': getattr(deployment, 'broker_symbol', None),
        }
        identity_fields = fingerprint_fields(params=strategy_params, runtime=identity_runtime) if incremental_allowed else {}
        observed_capital = str((runtime_config.get('risk') or {}).get('initial_capital'))
        fingerprint = incremental_signature(
            strategy_id=str(deployment.strategy_id), params=strategy_params,
            runtime=identity_runtime,
            history_bars=profile.required_history_bars,
            timeframe=str(deployment.timeframe),
            instrument=str(getattr(deployment, 'instrument_key', None) or deployment.instrument),
        ) if incremental_allowed else ""
        state_id = str(deployment.id)
        if not incremental_allowed:
            retained_states.invalidate(state_id, 'incremental_not_enabled_or_unsupported')

        latest_probe = None
        warmed = None
        if incremental_allowed:
            # Exact candle lookup is cheap. If a worker restarted, deployment
            # changed, or a candle gap occurred, retained state cannot be used.
            probe = await load_live_candles_for_runner(
                db, deployment, limit=2, through_candle_time=authoritative_candle_time,
            )
            latest_probe = probe[0] if probe else None
            if latest_probe:
                probe_time = _normalize_dt(latest_probe.get('candle_time'))
                if authoritative_candle_time is not None and probe_time != authoritative_candle_time:
                    raise HTTPException(status_code=409, detail='Requested closed candle not available')
                warmed = retained_states.get_for_next_candle(
                    state_id, fingerprint=fingerprint,
                    last_processed=getattr(deployment, 'last_processed_candle_time', None),
                    next_candle_time=probe_time,
                    timeframe_seconds=parse_timeframe_to_seconds(str(deployment.timeframe or 'M5')),
                    previous_candle=probe[1] if len(probe) > 1 else None,
                    fields=identity_fields, observed_capital=observed_capital,
                )
                # Experimental adapter appends to history. Rebase from the
                # authoritative *rolling 80K* window periodically so memory
                # and source-history dependence cannot grow without a bound.
                # This is a cold full evaluation, not a shortened warmup.
                if hybrid_selected and warmed is not None:
                    max_advances = configured_max_advances(settings)
                    if retained_states.rebase_due(state_id, history_bars=profile.required_history_bars,
                                                 max_advances=max_advances):
                        logger.warning('RUNNER_V64_HYBRID_REBASE deployment=%s incremental_steps=%s history=%s',
                                       deployment_id, warmed.candle_count-profile.required_history_bars,
                                       profile.required_history_bars)
                        retained_states.invalidate(state_id, 'hybrid_periodic_rolling_80k_rebase')
                        warmed = None

        if warmed is None:
            timer = stage_clock.start("load_closed_candles")
            candles = await load_live_candles_for_runner(
                db, deployment, limit=profile.required_history_bars,
                through_candle_time=authoritative_candle_time,
            )
            stage_clock.stop("load_closed_candles", timer, bars=len(candles))
            if len(candles) < profile.required_history_bars:
                history_ready_cache.invalidate(deployment.id)
                detail = {
                    "ok": False,
                    "error_code": "NOT_ENOUGH_LIVE_CANDLES",
                    "message": f"HOLD - Not enough live candles. Loaded {len(candles)} candles, required {profile.required_history_bars}.",
                    "loaded_candles": len(candles),
                    "deployment_id": str(deployment.id),
                    "instrument": deployment.instrument,
                    "instrument_key": getattr(deployment, "instrument_key", None),
                    "timeframe": deployment.timeframe,
                    "refresh_warning": refresh_warning,
                }
                deployment.last_runner_at = datetime.now(timezone.utc)
                try:
                    deployment.next_run_at = calculate_next_runner_at(datetime.now(timezone.utc), deployment.timeframe, 1)
                except Exception:
                    pass
                await _log(db, deployment, "RUNNER_NOT_ENOUGH_CANDLES", detail["message"], "WARNING", detail)
                await db.commit()
                return {"success": False, **detail, "latest_runner_log": detail["message"], "final_action": "HOLD_NOT_ENOUGH_CANDLES"}
            latest_candle = candles[0]
            latest_candle_time = _normalize_dt(latest_candle.get("candle_time"))
            if authoritative_candle_time is not None and latest_candle_time != authoritative_candle_time:
                raise HTTPException(status_code=409, detail=(
                    "Authoritative closed candle is not available in PostgreSQL "
                    f"(expected {authoritative_candle_time.isoformat()}, got {latest_candle_time.isoformat()})."
                ))
            timer = stage_clock.start("build_dataframe")
            df = _candles_to_dataframe(candles)
            stage_clock.stop("build_dataframe", timer, bars=len(df))
            history_bars_used = len(df)
            timer = stage_clock.start("strategy_class_init")
            strategy_instance = strategy_class(df, **params)
            stage_clock.stop("strategy_class_init", timer, bars=len(df))
            timer = stage_clock.start("strategy_generate")
            if bool(getattr(settings, "live_strategy_cprofile_enabled", False)):
                generated = profile_generate(_run_strategy_generate, strategy_instance, logger, state_id)
            else:
                generated = _run_strategy_generate(strategy_instance)
            stage_clock.stop("strategy_generate", timer, bars=len(df))
            if incremental_allowed and isinstance(generated, pd.DataFrame) and not generated.empty:
                retained_states.prime(
                    state_id, fingerprint=fingerprint, candle_time=latest_candle_time,
                    strategy=strategy_instance, generated=generated,
                    candle_count=len(df), latest_candle=latest_candle,
                    fields=identity_fields, observed_capital=observed_capital,
                )
            runner_mode = 'FULL_HISTORY'
        else:
            latest_candle = latest_probe
            latest_candle_time = _normalize_dt(latest_candle.get('candle_time'))
            # Incremental strategy code receives the same canonical OHLCV names
            # as its initial DataFrame. No implicit indicator approximations.
            df = _candles_to_dataframe([latest_candle])
            timer = stage_clock.start('strategy_incremental_update')
            incremental = retained_states.advance(
                state_id, fingerprint=fingerprint,
                last_processed=getattr(deployment, 'last_processed_candle_time', None),
                next_candle_time=latest_candle_time,
                timeframe_seconds=parse_timeframe_to_seconds(str(deployment.timeframe or 'M5')),
                candle=df.iloc[-1].to_dict(), previous_candle=probe[1] if len(probe) > 1 else None,
            )
            stage_clock.stop('strategy_incremental_update', timer, bars=1)
            if incremental is None:
                # Cannot safely use a possibly mutated state. Never guess a
                # HOLD/signal; request an isolated cold evaluation next cycle.
                await db.rollback()
                logger.error('RUNNER_INCREMENTAL_RETRY_COLD deployment=%s candle=%s', state_id, latest_candle_time)
                return {'success': False, 'final_action': 'HOLD_INCREMENTAL_RECOVERY',
                        'message': 'Incremental state invalidated; retrying full calculation next scheduler cycle.'}
            generated, history_bars_used = incremental
            runner_mode = 'RETAINED_INCREMENTAL'
            logger.info('RUNNER_INCREMENTAL_DONE deployment=%s candle=%s bars_seen=%s',
                        state_id, latest_candle_time.isoformat(), history_bars_used)

        latest_close = to_decimal(latest_candle.get("close"))
        latest_symbol = str(latest_candle.get("symbol") or deployment.instrument)
        deployment.last_runner_at = datetime.now(timezone.utc)
        deployment.next_run_at = calculate_next_runner_after_candle(
            latest_candle_time, deployment.timeframe, 1, now_utc=datetime.now(timezone.utc)
        )
        await _log(db, deployment, "RUNNER_CANDLES_LOADED",
                   f"Strategy evaluated from {runner_mode} data",
                   metadata={"latest_candle_time": latest_candle_time.isoformat(),
                             "symbol": latest_symbol, "runner_mode": runner_mode,
                             "required_history_bars": profile.required_history_bars,
                             "loaded_history_bars": history_bars_used})
        await latency_trace.mark(trace_id, "t6", status="STRATEGY_STARTED")
        stage_clock.summary()
        logger.warning('RUNNER_GENERATE_COMPLETE deployment=%s candle_open=%s mode=%s total_wall_s=%.3f',
                       deployment_id, latest_candle_time.isoformat(), runner_mode,
                       time.perf_counter() - runner_total_started)
        if generated is None or not isinstance(generated, pd.DataFrame) or generated.empty:
            raise HTTPException(status_code=400, detail="Strategy did not return a valid DataFrame")
        await latency_trace.mark(trace_id, "t7", status="STRATEGY_FINISHED")

        timer = stage_clock.start("extract_latest_signal")
        signal_payload = extract_latest_signal_payload(generated)
        stage_clock.stop("extract_latest_signal", timer)
        signal_type = str(signal_payload.get("signal_type") or "HOLD")
        side = "LONG" if signal_type == "BUY" else "SHORT" if signal_type == "SELL" else None
        output_metadata = {
            "signal_type": signal_type,
            "v64_hybrid_monitor_only": force_monitor_no_orders,
            "strategy_stop_loss": signal_payload.get("strategy_stop_loss"),
            "strategy_target": signal_payload.get("strategy_target"),
            "strategy_risk_points": signal_payload.get("strategy_risk_points"),
            "strategy_reward_points": signal_payload.get("strategy_reward_points"),
            "signal_reason": signal_payload.get("signal_reason"),
            "latest_candle_time": latest_candle_time.isoformat(),
            "price": str(latest_close),
            "symbol": latest_symbol,
            "display_symbol": deployment.instrument,
            "execution_symbol": getattr(deployment, "instrument_key", None) or getattr(deployment, "broker_symbol", None) or latest_symbol,
            "instrument_key": getattr(deployment, "instrument_key", None),
            "broker": "UPSTOX" if "|" in str(getattr(deployment, "instrument_key", "") or latest_symbol) else None,
        }
        await _log(
            db,
            deployment,
            "RUNNER_STRATEGY_OUTPUT_EXTRACTED",
            "Strategy output extracted from latest closed candle",
            metadata={k: output_metadata.get(k) for k in ["signal_type", "strategy_stop_loss", "strategy_target", "signal_reason"]},
        )
        await _log(
            db,
            deployment,
            "RUNNER_SIGNAL_GENERATED",
            f"{canonical_name} generated {signal_type} on latest closed candle",
            metadata=output_metadata,
        )
        await _log(db, deployment, "LIVE_ENGINE_QA_SIGNAL_CONTRACT_PASS", "Live engine signal contract validated", metadata=output_metadata)

        if execute and bool(getattr(settings, "live_runner_stale_order_guard_enabled", False)):
            candle_closes_at = latest_candle_time + timedelta(
                seconds=parse_timeframe_to_seconds(str(deployment.timeframe or "M5"))
            )
            max_stale_age = max(0, int(getattr(settings, "live_runner_max_order_age_after_close_seconds", 60)))
            age = (datetime.now(timezone.utc) - candle_closes_at).total_seconds()
            if age > max_stale_age:
                deployment.last_heartbeat_at = datetime.now(timezone.utc)
                _mark_candle_processed(deployment, latest_candle_time)
                await _log(db, deployment, "RUNNER_STALE_SIGNAL_BLOCKED",
                           "Stale candle evaluated; skipped live order to avoid executing a delayed signal",
                           "WARNING", {"signal_type": signal_type, "candle_time": latest_candle_time.isoformat(),
                                       "age_after_close_seconds": round(age, 3), "max_age_seconds": max_stale_age,
                                       "generate_seconds": stage_clock.stages.get("strategy_generate")})
                await db.commit()
                return StrategyRunnerResult(
                    success=True, deployment_id=str(deployment.id), strategy_name=canonical_name,
                    latest_candle_time=latest_candle_time.isoformat(), signal=signal_type,
                    executed=False, order_id=None, broker_order_id=None, signal_id=None,
                    duplicate=False, message="HOLD - stale candle; order blocked by configured guard",
                    latest_runner_log="Stale candle order blocked", symbol=latest_symbol,
                    final_action="HOLD_STALE_CANDLE",
                ).to_dict()

        # Do not persist HOLD noise into live_signals. HOLD is a heartbeat/result,
        # not a tradeable signal. Persist only BUY/SELL/EXIT so Recent Signals and
        # signal counts stay useful for trading decisions.
        if signal_type == "HOLD":
            deployment.last_heartbeat_at = datetime.now(timezone.utc)
            _mark_candle_processed(deployment, latest_candle_time)
            latest_log_message = "HOLD - no tradeable signal, not saved"
            await _log(
                db,
                deployment,
                "RUNNER_HOLD_IGNORED",
                latest_log_message,
                metadata={"latest_candle_time": latest_candle_time.isoformat(), "price": str(latest_close), "symbol": latest_symbol, "strategy_output": output_metadata},
            )
            await db.commit()
            return StrategyRunnerResult(
                success=True,
                deployment_id=str(deployment.id),
                strategy_name=canonical_name or getattr(strategy, "name", None),
                latest_candle_time=latest_candle_time.isoformat(),
                signal=signal_type,
                executed=False,
                order_id=None,
                broker_order_id=None,
                signal_id=None,
                duplicate=False,
                message=latest_log_message,
                latest_runner_log=latest_log_message,
                symbol=latest_symbol,
                final_action="HOLD_IGNORED",
            ).to_dict()

        duplicate = await _find_duplicate_engine_signal(db, deployment.id, latest_candle_time, signal_type, strategy_id=deployment.strategy_id, symbol=latest_symbol, timeframe=deployment.timeframe)
        if duplicate is not None:
            deployment.last_heartbeat_at = datetime.now(timezone.utc)
            _mark_candle_processed(deployment, latest_candle_time)
            latest_log_message = "Duplicate tradeable signal ignored"
            await _log(
                db,
                deployment,
                "RUNNER_DUPLICATE_IGNORED",
                latest_log_message,
                "WARNING",
                {"existing_signal_id": str(duplicate.id), "signal_type": signal_type, "latest_candle_time": latest_candle_time.isoformat()},
            )
            await db.commit()
            return StrategyRunnerResult(
                success=True,
                deployment_id=str(deployment.id),
                strategy_name=canonical_name or getattr(strategy, "name", None),
                latest_candle_time=latest_candle_time.isoformat(),
                signal=signal_type,
                executed=False,
                order_id=None,
                broker_order_id=None,
                signal_id=str(duplicate.id),
                duplicate=True,
                message=latest_log_message,
                latest_runner_log=latest_log_message,
                symbol=latest_symbol,
            ).to_dict()

        signal = LiveSignal(
            trace_id=trace_id,
            deployment_id=deployment.id,
            user_id=deployment.user_id,
            strategy_id=deployment.strategy_id,
            source="ENGINE",
            symbol=latest_symbol,
            timeframe=deployment.timeframe,
            signal_type=signal_type,
            side=side,
            price=latest_close,
            candle_time=latest_candle_time,
            confidence=None,
            reason=signal_payload.get("signal_reason") or f"Strategy runner: {canonical_name}",
            raw_payload={
                "runner": "live_market_candles",
                "strategy_id": strategy.id,
                "strategy_name": strategy.name,
                "canonical_strategy": canonical_name,
                "resolved_strategy_class": getattr(strategy_class, "__name__", str(strategy_class)),
                "engine_mode": str(strategy_params.get("engine_mode") or ("DYNAMIC_DB" if source_code else "STATIC_REGISTRY")),
                "source_code_sha256": source_code_sha256 or None,
                "required_history_bars": profile.required_history_bars,
                "loaded_history_bars": history_bars_used,
                "history_ready": history_bars_used >= profile.required_history_bars,
                "execute_requested": execute,
                "latest_candle_time": latest_candle_time.isoformat(),
                "resolved_symbol": latest_symbol,
                "display_symbol": deployment.instrument,
                "execution_symbol": getattr(deployment, "instrument_key", None) or getattr(deployment, "broker_symbol", None) or latest_symbol,
                "instrument_key": getattr(deployment, "instrument_key", None),
                "broker": "UPSTOX" if "|" in str(getattr(deployment, "instrument_key", "") or latest_symbol) else None,
                "strategy_stop_loss": signal_payload.get("strategy_stop_loss"),
                "strategy_target": signal_payload.get("strategy_target"),
                "strategy_risk_points": signal_payload.get("strategy_risk_points"),
                "strategy_reward_points": signal_payload.get("strategy_reward_points"),
                "signal_reason": signal_payload.get("signal_reason"),
                "source_row": signal_payload.get("source_row") or {},
                "trace_id": trace_id,
                "event_context": event_context or {},
            },
            status="RECEIVED",
        )
        try:
            async with db.begin_nested():
                db.add(signal)
                await db.flush()
                await latency_trace.mark(
                    trace_id,
                    "t8",
                    status="SIGNAL_PERSISTED",
                    signal_id=str(signal.id),
                    signal_type=signal_type,
                )
        except IntegrityError:
            duplicate = await _find_duplicate_engine_signal(db, deployment.id, latest_candle_time, signal_type, strategy_id=deployment.strategy_id, symbol=latest_symbol, timeframe=deployment.timeframe)
            deployment.last_heartbeat_at = datetime.now(timezone.utc)
            _mark_candle_processed(deployment, latest_candle_time)
            latest_log_message = "Duplicate tradeable signal blocked by DB idempotency guard"
            await _log(
                db,
                deployment,
                "DUPLICATE_SIGNAL_BLOCKED",
                latest_log_message,
                "WARNING",
                {"existing_signal_id": str(duplicate.id) if duplicate else None, "signal_type": signal_type, "latest_candle_time": latest_candle_time.isoformat()},
            )
            await db.commit()
            return StrategyRunnerResult(
                success=True,
                deployment_id=str(deployment.id),
                strategy_name=canonical_name or getattr(strategy, "name", None),
                latest_candle_time=latest_candle_time.isoformat(),
                signal=signal_type,
                executed=False,
                order_id=None,
                broker_order_id=None,
                signal_id=str(duplicate.id) if duplicate else None,
                duplicate=True,
                message=latest_log_message,
                latest_runner_log=latest_log_message,
                symbol=latest_symbol,
                final_action="DUPLICATE_SIGNAL_BLOCKED",
            ).to_dict()

        deployment.last_signal_at = datetime.now(timezone.utc)
        deployment.last_heartbeat_at = datetime.now(timezone.utc)
        await _log(db, deployment, "RUNNER_SIGNAL_SAVED", f"ENGINE {signal_type} signal saved", metadata={"signal_id": str(signal.id)})

        order: Optional[LiveOrder] = None
        executed = False
        if not execute or force_monitor_no_orders:
            # Fail-closed even when the dashboard Auto Trade flag is ON.
            # Research monitor mode is never allowed to submit broker orders.
            if force_monitor_no_orders:
                logger.warning('RUNNER_INCREMENTAL_ORDER_SUPPRESSED deployment=%s candle=%s signal=%s '
                               'historical_catchup=%s monitor_only=%s',
                               deployment_id, latest_candle_time.isoformat(), signal_type,
                               suppress_broker_order_for_catchup,
                               generic_monitor_requested or legacy_monitor_requested)
            signal.status = "ACCEPTED"
            latest_log_message = _message_for_result(signal_type, execute, bool(deployment.auto_trade_enabled), None)
            await _log(db, deployment, "RUNNER_DRY_RUN_COMPLETED", latest_log_message, metadata={"signal_id": str(signal.id)})
        elif not deployment.auto_trade_enabled:
            signal.status = "ACCEPTED"
            latest_log_message = _message_for_result(signal_type, execute, False, None)
            await _log(db, deployment, "RUNNER_EXECUTION_SKIPPED", latest_log_message, "WARNING", {"signal_id": str(signal.id)})
        else:
            order = await execute_signal(db, deployment, signal)
            executed = bool(order and signal.status == "EXECUTED" and order.status in {"FILLED", "PLACED"})
            latest_log_message = signal.rejection_reason or _message_for_result(signal_type, execute, True, order)
            await _log(
                db,
                deployment,
                "RUNNER_COMPLETED",
                latest_log_message,
                "ERROR" if order is not None and order.status == "ERROR" else "INFO",
                {"signal_id": str(signal.id), "order_id": str(order.id) if order else None, "executed": executed},
            )

        _mark_candle_processed(deployment, latest_candle_time)
        await db.commit()
        await db.refresh(signal)
        if order is not None:
            await db.refresh(order)

        return StrategyRunnerResult(
            success=True,
            deployment_id=str(deployment.id),
            strategy_name=canonical_name or getattr(strategy, "name", None),
            latest_candle_time=latest_candle_time.isoformat(),
            signal=signal_type,
            executed=executed,
            order_id=str(order.id) if order else None,
            broker_order_id=order.broker_order_id if order else None,
            signal_id=str(signal.id),
            duplicate=False,
            message=latest_log_message or "Strategy runner completed",
            latest_runner_log=latest_log_message,
            order_status=order.status if order else None,
            error_message=order.error_message if order else signal.rejection_reason,
            symbol=latest_symbol,
        ).to_dict()

    except HTTPException as exc:
        latest_log_message = str(exc.detail)
        # A failed flush/commit leaves AsyncSession in a failed transaction.
        # Always rollback before any new ORM query/log write, for BOTH the
        # event-worker route and the MT5/legacy auto-runner route.
        await db.rollback()
        failed_deployment = (
            await db.execute(select(StrategyDeployment).where(StrategyDeployment.id == deployment_id))
        ).scalar_one_or_none()
        if failed_deployment is not None:
            await _log(db, failed_deployment, "RUNNER_ERROR", latest_log_message, "ERROR", {"deployment_id": str(deployment_id)})
            await db.commit()
        raise
    except Exception as exc:
        logger.exception("Strategy runner failed for deployment %s", deployment_id)
        latest_log_message = f"Strategy runner failed: {exc.__class__.__name__}: {str(exc)[:240]}"
        # Never attempt to reuse a poisoned transaction after DBAPI/flush errors.
        # This prevents PendingRollbackError from masking the real root cause and
        # lets the 1-second auto-runner retry start with a clean session.
        await db.rollback()
        failed_deployment = (
            await db.execute(select(StrategyDeployment).where(StrategyDeployment.id == deployment_id))
        ).scalar_one_or_none()
        if failed_deployment is not None:
            await _log(db, failed_deployment, "RUNNER_ERROR", latest_log_message, "ERROR", {"deployment_id": str(deployment_id)})
            await db.commit()
        status_code = 500 if candle_time is not None else 400
        detail = latest_log_message if candle_time is not None else "Strategy runner failed. Check execution logs for details."
        raise HTTPException(status_code=status_code, detail=detail) from exc


async def run_strategy_for_candle(
    db: AsyncSession,
    deployment_id: UUID,
    candle_time: datetime,
    trace_id: str,
    *,
    execute: bool = True,
    event_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run the existing strategy engine for one authoritative closed candle.

    This is the Redis worker entry point.  Broker candle refresh is disabled so
    no polling or second cTrader connection can enter the critical path.
    """
    return await run_strategy_for_deployment(
        db,
        deployment_id,
        execute=execute,
        refresh_broker_candles=False,
        candle_time=candle_time,
        trace_id=trace_id,
        event_context=event_context,
    )
