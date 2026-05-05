from __future__ import annotations

import os
from datetime import datetime, timezone
from decimal import Decimal, ROUND_DOWN
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...db.models import BrokerAccount, LiveOrder, LivePosition, LiveSignal, LiveTradeLog, StrategyDeployment
from ..brokers.base import BrokerOrderRequest
from ..brokers.factory import get_broker_adapter, get_broker_code
from ..live.order_preview_service import build_live_order_preview
from ..live.paper_broker import fill_market_order
from ..live.pnl_service import to_decimal
from ..live.position_service import open_position
from .readiness_service import build_live_deployment_readiness


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _plain(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_plain(v) for v in value]
    return value


def _status_from_checks(checks: list[dict[str, Any]]) -> str:
    if any(c.get("status") == "FAIL" for c in checks):
        return "FAIL"
    if any(c.get("status") == "WARNING" for c in checks):
        return "WARNING"
    return "PASS"


def _check(key: str, label: str, status: str, message: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"key": key, "label": label, "status": status, "message": message, "data": _plain(data or {})}


def _safe_demo_max_lot(deployment: StrategyDeployment) -> Decimal:
    env_value = os.getenv("MT5_DEMO_MAX_LOT") or "0.01"
    env_cap = to_decimal(env_value, "0.01")
    dep_cap = to_decimal(getattr(deployment, "mt5_demo_max_lot", None), str(env_cap)) if getattr(deployment, "mt5_demo_max_lot", None) is not None else env_cap
    cap = min(env_cap, dep_cap)
    if cap <= 0:
        cap = Decimal("0.01")
    return cap


def _floor_to_step(value: Decimal, step: Decimal) -> Decimal:
    if step <= 0:
        return value
    return (value / step).to_integral_value(rounding=ROUND_DOWN) * step


async def build_final_live_qa(db: AsyncSession, deployment_id: UUID, user: dict) -> dict[str, Any]:
    deployment = (await db.execute(select(StrategyDeployment).where(StrategyDeployment.id == deployment_id))).scalar_one_or_none()
    if deployment is None:
        return {
            "overall_status": "FAIL",
            "summary": "Deployment not found.",
            "checks": [_check("deployment", "Deployment", "FAIL", "Deployment was not found.")],
        }

    readiness = await build_live_deployment_readiness(db, deployment_id, user)
    readiness_checks = readiness.get("checks") or []
    readiness_by_key = {c.get("key"): c for c in readiness_checks if isinstance(c, dict)}
    broker = None
    if deployment.broker_account_id:
        broker = (await db.execute(select(BrokerAccount).where(BrokerAccount.id == deployment.broker_account_id))).scalar_one_or_none()

    open_positions = int((await db.execute(select(func.count(LivePosition.id)).where(LivePosition.deployment_id == deployment.id, LivePosition.status == "OPEN"))).scalar() or 0)
    last_dry = (await db.execute(select(LiveTradeLog).where(LiveTradeLog.deployment_id == deployment.id, LiveTradeLog.event_type.in_(["FULL_DRY_TEST", "RUN_FULL_DRY_TEST"])).order_by(LiveTradeLog.created_at.desc()).limit(1))).scalar_one_or_none()
    recent_orders = list((await db.execute(select(LiveOrder).where(LiveOrder.deployment_id == deployment.id).order_by(LiveOrder.created_at.desc()).limit(50))).scalars().all())
    last_paper = next((o for o in recent_orders if isinstance(o.raw_response, dict) and o.raw_response.get("is_test_order") is True and o.raw_response.get("qa_test_type") == "PAPER_ORDER_TEST"), None)
    last_demo = next((o for o in recent_orders if isinstance(o.raw_response, dict) and o.raw_response.get("qa_test_type") == "DEMO_MICRO_ORDER"), None)
    last_log = (await db.execute(select(LiveTradeLog).where(LiveTradeLog.deployment_id == deployment.id, LiveTradeLog.level.in_(["ERROR", "WARNING"])).order_by(LiveTradeLog.created_at.desc()).limit(1))).scalar_one_or_none()

    checks: list[dict[str, Any]] = []
    checks.append(_check("deployment_ready", "Deployment readiness", "PASS" if readiness.get("ready_to_auto_trade") else ("WARNING" if readiness.get("overall_status") == "WARNING" else "FAIL"), readiness.get("summary") or "Readiness checked."))
    for source_key, label in [
        ("instrument_spec_valid", "Instrument spec ready"),
        ("broker_connected", "Broker connected if DEMO"),
        ("broker_symbol_configured", "Broker symbol verified"),
        ("latest_candles_available", "Latest candles available"),
        ("latest_entry_plan_ok", "Entry plan can calculate SL/TP"),
        ("risk_preview_ok", "Risk preview OK"),
        ("duplicate_protection_enabled", "Duplicate protection ready"),
    ]:
        src = readiness_by_key.get(source_key)
        if src:
            checks.append(_check(source_key, label, str(src.get("status") or "FAIL"), str(src.get("message") or label)))
        else:
            checks.append(_check(source_key, label, "WARNING", "Readiness detail is not available yet."))

    checks.append(_check("strategy_dry_run", "Strategy can dry-run", "PASS" if readiness_by_key.get("enough_candles_for_strategy", {}).get("status") == "PASS" else "WARNING", "Run Full Dry Test to confirm the latest strategy signal."))
    checks.append(_check("paper_position_manager", "Paper position manager ready", "PASS", "PAPER positions can be managed by AlgoAgentX candle checks."))
    checks.append(_check("broker_sync_ready", "Broker sync ready", "PASS" if deployment.mode == "PAPER" or (broker is not None and broker.status == "CONNECTED") else "FAIL", "Broker sync is not required for PAPER." if deployment.mode == "PAPER" else "Connected broker is required for DEMO sync."))
    demo_cap = _safe_demo_max_lot(deployment)
    checks.append(_check("max_lot_cap_safe", "Max lot cap safe", "PASS" if demo_cap <= Decimal("0.01") else "WARNING", f"Demo micro-order cap is {demo_cap}. Keep it at or below 0.01 for final QA.", {"safe_cap": str(demo_cap)}))
    checks.append(_check("daily_loss_guard", "Daily loss guard active", "PASS" if to_decimal(getattr(deployment, "max_daily_loss", None), "0") > 0 else "WARNING", "Max daily loss is configured." if to_decimal(getattr(deployment, "max_daily_loss", None), "0") > 0 else "Max daily loss is not configured."))
    checks.append(_check("auto_trade_status", "Auto Trade status", "PASS" if deployment.auto_trade_enabled else "WARNING", "Auto Trade is ON." if deployment.auto_trade_enabled else "Auto Trade is OFF. This is safe for QA; enable only when ready."))
    checks.append(_check("auto_runner_status", "Auto Runner status", "PASS" if deployment.auto_runner_enabled else "WARNING", "Auto Runner is ON." if deployment.auto_runner_enabled else "Auto Runner is OFF. This is safe for QA; enable only when ready."))
    if deployment.mode == "LIVE":
        checks.append(_check("live_mode_locked", "LIVE mode lock", "FAIL", "Real live trading is locked for safety. Use PAPER or DEMO until final QA passes."))

    overall = _status_from_checks(checks)
    return {
        "overall_status": overall,
        "summary": "Final QA passed." if overall == "PASS" else "Final QA has warnings." if overall == "WARNING" else "Final QA has blocking issues.",
        "checks": checks,
        "deployment_id": str(deployment.id),
        "mode": deployment.mode,
        "last_results": {
            "last_dry_test": _plain(last_dry.metadata_json if last_dry else None),
            "last_paper_test": _plain({"order_id": str(last_paper.id), "status": last_paper.status, "created_at": last_paper.created_at} if last_paper else None),
            "last_demo_micro_test": _plain({"order_id": str(last_demo.id), "broker_order_id": last_demo.broker_order_id, "status": last_demo.status, "created_at": last_demo.created_at} if last_demo else None),
            "last_broker_sync": _plain(getattr(deployment, "last_broker_sync_at", None)),
            "last_auto_runner_cycle": _plain(getattr(deployment, "last_runner_at", None)),
            "last_blocking_error": _plain({"event_type": last_log.event_type, "message": last_log.message, "created_at": last_log.created_at} if last_log else None),
            "open_positions": open_positions,
        },
        "debug_summary": {
            "deployment_id": str(deployment.id),
            "strategy": deployment.strategy_id,
            "instrument": deployment.instrument,
            "mode": deployment.mode,
            "readiness_status": readiness.get("overall_status"),
            "last_error": last_log.message if last_log else None,
            "broker_status": getattr(broker, "status", None) if broker else None,
        },
    }


async def run_paper_order_test(db: AsyncSession, deployment: StrategyDeployment, *, side: str = "BUY") -> dict[str, Any]:
    if deployment.mode != "PAPER":
        raise ValueError("Paper order test is allowed only for PAPER deployments.")
    side = "SELL" if str(side or "BUY").upper() == "SELL" else "BUY"
    preview = await build_live_order_preview(db, deployment=deployment, broker_code="PAPER", symbol=deployment.instrument, side=side, preview_mode="AUTO_LATEST_PRICE", strict_instrument=True)
    if preview.get("validation_status") != "OK":
        raise ValueError(preview.get("rejected_reason") or "Paper order test preview failed.")
    qty = to_decimal(preview.get("final_lot_size") if str(preview.get("quantity_mode") or "").upper() == "LOTS" else preview.get("final_quantity"), "0")
    if qty <= 0:
        raise ValueError("Calculated lot/quantity is zero.")
    entry = to_decimal(preview.get("entry_price"), "0")
    sl = to_decimal(preview.get("stop_loss"), "0")
    tp = to_decimal(preview.get("target"), "0")
    signal = LiveSignal(
        deployment_id=deployment.id,
        user_id=deployment.user_id,
        strategy_id=deployment.strategy_id,
        source="QA_PAPER_TEST",
        symbol=deployment.instrument,
        timeframe=deployment.timeframe,
        signal_type=side,
        side="LONG" if side == "BUY" else "SHORT",
        price=entry,
        candle_time=_now(),
        reason="Phase 3E paper order test",
        raw_payload={"is_test_signal": True, "qa_test_type": "PAPER_ORDER_TEST"},
        status="EXECUTED",
    )
    db.add(signal)
    await db.flush()
    order = await fill_market_order(db, deployment, signal, side, qty, entry, sl, tp, action="QA_PAPER_TEST")
    order.raw_response = {**(order.raw_response or {}), "is_test_order": True, "qa_test_type": "PAPER_ORDER_TEST", "preview": _plain(preview)}
    metadata = preview.get("risk_metadata") or {}
    for field, key in {
        "quantity_mode": "quantity_mode",
        "requested_lot": "requested_lot",
        "final_lot": "final_lot",
        "requested_quantity": "requested_quantity",
        "final_quantity": "final_quantity",
        "risk_amount": "risk_amount",
        "actual_risk": "actual_risk",
        "instrument_spec_snapshot": "instrument_spec_snapshot",
        "runtime_config_snapshot": "runtime_config_snapshot",
    }.items():
        if hasattr(order, field):
            setattr(order, field, metadata.get(key))
    position = await open_position(db, deployment, deployment.instrument, "LONG" if side == "BUY" else "SHORT", qty, entry, sl, tp)
    db.add(LiveTradeLog(deployment_id=deployment.id, user_id=deployment.user_id, event_type="QA_PAPER_ORDER_TEST", level="INFO", message="QA paper order test created a paper position only. No broker order was placed.", metadata_json={"order_id": str(order.id), "position_id": str(position.id), "is_test_order": True}))
    await db.commit()
    return {
        "status": "OK",
        "message": "Paper order test created a paper position only. No broker order was placed.",
        "order_id": str(order.id),
        "position_id": str(position.id),
        "side": side,
        "lot_or_quantity": float(qty),
        "entry": float(entry),
        "SL": float(sl),
        "TP": float(tp),
        "risk": preview.get("actual_risk_amount") or preview.get("risk_amount"),
        "expected_reward": preview.get("expected_reward_amount"),
        "preview": _plain(preview),
    }


async def run_demo_micro_order_test(db: AsyncSession, deployment: StrategyDeployment, *, confirm_demo_micro_order: bool, side: str = "BUY") -> dict[str, Any]:
    if not confirm_demo_micro_order:
        raise ValueError("Type DEMO and send confirm_demo_micro_order=true before placing a demo micro order.")
    if deployment.mode == "LIVE":
        raise ValueError("Real LIVE mode is locked. Demo micro order test cannot run in LIVE mode.")
    if deployment.mode != "DEMO":
        raise ValueError("Demo micro order test is allowed only for DEMO deployments.")
    if not deployment.broker_account_id:
        raise ValueError("DEMO micro order requires a connected demo broker account.")
    broker = (await db.execute(select(BrokerAccount).where(BrokerAccount.id == deployment.broker_account_id))).scalar_one_or_none()
    if broker is None or broker.status != "CONNECTED":
        raise ValueError("DEMO micro order requires broker status CONNECTED.")
    side = "SELL" if str(side or "BUY").upper() == "SELL" else "BUY"
    safe_cap = _safe_demo_max_lot(deployment)
    preview_override = {"risk": {"max_lot_cap": float(safe_cap)}}
    preview = await build_live_order_preview(db, deployment=deployment, broker_code=get_broker_code(broker), symbol=deployment.instrument, side=side, runtime_config=preview_override, preview_mode="AUTO_LATEST_PRICE", strict_instrument=True)
    if preview.get("validation_status") != "OK":
        raise ValueError(preview.get("rejected_reason") or "Demo micro order preview failed.")
    quantity_mode = str(preview.get("quantity_mode") or "LOTS").upper()
    spec = preview.get("instrument_spec_snapshot") or {}
    if quantity_mode == "LOTS":
        step = to_decimal(spec.get("lot_step"), "0.01")
        min_lot = to_decimal(spec.get("min_lot"), "0.01")
        qty = min(to_decimal(preview.get("final_lot_size"), str(safe_cap)), safe_cap)
        if min_lot > safe_cap:
            raise ValueError(f"Broker minimum lot {min_lot} is above safe demo cap {safe_cap}.")
        qty = max(qty, min_lot)
        qty = _floor_to_step(qty, step)
    else:
        step = to_decimal(spec.get("quantity_step"), "1")
        min_qty = to_decimal(spec.get("min_quantity"), "1")
        qty = max(min_qty, to_decimal(preview.get("final_quantity"), "1"))
        qty = _floor_to_step(qty, step)
    if quantity_mode == "LOTS" and qty > safe_cap:
        raise ValueError(f"Demo micro order lot {qty} exceeds safe cap {safe_cap}.")
    entry = to_decimal(preview.get("entry_price"), "0")
    sl = to_decimal(preview.get("stop_loss"), "0")
    tp = to_decimal(preview.get("target"), "0")
    if sl <= 0 or tp <= 0:
        raise ValueError("Demo micro order requires valid SL and TP.")
    broker_symbol = str(preview.get("broker_symbol") or deployment.broker_symbol or deployment.instrument)

    # Save the test signal before sending the broker order, and use an allowed
    # source value. The DB check constraint commonly allows ENGINE/MANUAL/WEBHOOK
    # sources; putting QA_DEMO_MICRO_TEST in source caused a 500 after MT5 had
    # already accepted the order. Keep the QA marker in raw_payload instead.
    signal = LiveSignal(
        deployment_id=deployment.id,
        user_id=deployment.user_id,
        strategy_id=deployment.strategy_id,
        source="ENGINE",
        symbol=broker_symbol,
        timeframe=deployment.timeframe,
        signal_type=side,
        side="LONG" if side == "BUY" else "SHORT",
        price=entry,
        candle_time=_now(),
        reason="Phase 3E demo micro order test",
        raw_payload={"is_test_signal": True, "qa_test_type": "DEMO_MICRO_ORDER", "source_label": "QA_DEMO_MICRO_TEST"},
        status="RECEIVED",
    )
    db.add(signal)
    await db.flush()

    adapter = get_broker_adapter(broker)
    result = await adapter.place_market_order(BrokerOrderRequest(symbol=broker_symbol, side=side, qty=qty, price=entry, stop_loss=sl, target=tp, comment="AlgoAgentX QA Demo Micro", max_lot=safe_cap))
    signal.status = "EXECUTED" if result.success else "ERROR"
    signal.rejection_reason = None if result.success else result.message

    order = LiveOrder(
        deployment_id=deployment.id,
        signal_id=signal.id,
        user_id=deployment.user_id,
        broker_account_id=deployment.broker_account_id,
        broker_order_id=result.broker_order_id,
        symbol=broker_symbol,
        side=side,
        order_type="MARKET",
        qty=qty,
        entry_price=entry,
        executed_price=result.executed_price if result.success else None,
        stop_loss=sl,
        target=tp,
        status="FILLED" if result.success else "ERROR",
        error_message=None if result.success else result.message,
        raw_response={**(result.raw_response or {}), "is_test_order": True, "qa_test_type": "DEMO_MICRO_ORDER", "safe_cap": str(safe_cap), "preview": _plain(preview)},
    )
    db.add(order)
    if result.success:
        await db.flush()
        await open_position(db, deployment, broker_symbol, "LONG" if side == "BUY" else "SHORT", qty, result.executed_price or entry, sl, tp)
    db.add(LiveTradeLog(deployment_id=deployment.id, user_id=deployment.user_id, event_type="QA_DEMO_MICRO_ORDER_TEST", level="INFO" if result.success else "ERROR", message="Demo micro order was sent to the connected DEMO broker." if result.success else (result.message or "Demo micro order failed."), metadata_json={"broker_order_id": result.broker_order_id, "lot_or_quantity": str(qty), "safe_cap": str(safe_cap), "status": "FILLED" if result.success else "ERROR"}))
    await db.commit()
    return {
        "status": "OK" if result.success else "ERROR",
        "message": "Demo broker micro order was placed. This uses DEMO money only." if result.success else (result.message or "Demo micro order failed."),
        "broker_order_id": result.broker_order_id,
        "broker_response": _plain(result.raw_response or {}),
        "lot_or_quantity_sent": float(qty),
        "SL": float(sl),
        "TP": float(tp),
        "risk_estimate": preview.get("actual_risk_amount") or preview.get("risk_amount"),
        "warning": "A real order was placed on your DEMO broker account only.",
        "order_id": str(order.id),
    }
