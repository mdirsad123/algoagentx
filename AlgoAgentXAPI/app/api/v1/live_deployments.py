from __future__ import annotations

import secrets
from datetime import datetime, time, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.dependencies import get_current_user, get_db
from ...db.models import BrokerAccount, LiveEquityPoint, LiveOrder, LivePosition, LiveSignal, LiveTradeLog, StrategyDeployment
from ...schemas.live_trading import LiveOrderOut, LivePositionOut, LiveSignalOut, LiveTradeLogOut, ManualDeploymentSignalIn, RunStrategyOnceIn, StrategyDeploymentCreate, StrategyDeploymentOut, StrategyDeploymentUpdate
from ...services.brokers.factory import get_broker_adapter
from ...services.live.execution_engine import execute_signal
from ...services.live.pnl_service import to_decimal
from ...services.live.mt5_candle_service import get_candle_snapshot, refresh_deployment_candles
from ...services.live.strategy_runner import run_strategy_for_deployment
from ...services.live.trading_safety import LIVE_DISABLED_MESSAGE, check_platform_mode_allowed, mark_heartbeat
from ...utils.api_response import success_response
from .live_common import (
    block_live_mode,
    dump_list,
    dump_one,
    get_broker_account_or_404,
    get_deployment_or_404,
    get_deployable_strategy_or_400,
    get_published_strategy_or_400,
    is_admin,
    update_from_payload,
    user_id_from,
)

router = APIRouter()


def _ensure_tradingview_secret(row: StrategyDeployment) -> None:
    if not row.tradingview_secret:
        row.tradingview_secret = secrets.token_urlsafe(32)


def _dec(value: object, default: str = "0") -> Decimal:
    return to_decimal(value, default)


def _as_money(value: object | None) -> Decimal | None:
    if value is None:
        return None
    return _dec(value)


def _broker_safe(row: BrokerAccount | None) -> dict | None:
    if row is None:
        return None
    meta = row.metadata_json or {}
    last_test = meta.get("last_test") if isinstance(meta, dict) else {}
    if not isinstance(last_test, dict):
        last_test = {}
    return {
        "id": str(row.id),
        "broker_account_id": str(row.id),
        "broker_name": row.broker_name,
        "account_label": row.account_label,
        "mode": row.mode,
        "status": row.status,
        "login_id": row.login_id,
        "server_name": row.server_name or last_test.get("server"),
        "balance": _as_money(last_test.get("balance")),
        "equity": _as_money(last_test.get("equity")),
        "currency": last_test.get("currency"),
        "last_connected_at": row.last_connected_at,
    }


def _strategy_name(row: StrategyDeployment) -> str:
    strategy = getattr(row, "strategy", None)
    return getattr(strategy, "name", None) or row.strategy_id


async def _validate_broker_for_user(db: AsyncSession, broker_account_id: UUID | None, current_user: dict) -> None:
    if broker_account_id is None:
        return
    await get_broker_account_or_404(db, broker_account_id, current_user)


async def _write_log(db: AsyncSession, deployment: StrategyDeployment, event_type: str, message: str, level: str = "INFO", metadata: dict | None = None) -> None:
    db.add(LiveTradeLog(
        deployment_id=deployment.id,
        user_id=deployment.user_id,
        event_type=event_type,
        level=level,
        message=message,
        metadata_json=metadata or {"status": deployment.status, "mode": deployment.mode},
    ))


async def _recent(db: AsyncSession, model, deployment_id: UUID, limit: int = 20):
    result = await db.execute(select(model).where(model.deployment_id == deployment_id).order_by(model.created_at.desc()).limit(limit))
    return list(result.scalars().all())


async def _summary(db: AsyncSession, row: StrategyDeployment) -> dict:
    day_start = datetime.combine(datetime.now(timezone.utc).date(), time.min, tzinfo=timezone.utc)

    realized = _dec((await db.execute(select(func.coalesce(func.sum(LivePosition.realized_pnl), 0)).where(LivePosition.deployment_id == row.id))).scalar())
    unrealized = _dec((await db.execute(select(func.coalesce(func.sum(LivePosition.unrealized_pnl), 0)).where(LivePosition.deployment_id == row.id, LivePosition.status == "OPEN"))).scalar())
    today_pnl = _dec((await db.execute(select(func.coalesce(func.sum(LivePosition.realized_pnl), 0)).where(LivePosition.deployment_id == row.id, LivePosition.closed_at >= day_start))).scalar())
    open_positions_count = int((await db.execute(select(func.count(LivePosition.id)).where(LivePosition.deployment_id == row.id, LivePosition.status == "OPEN"))).scalar() or 0)
    orders_count_today = int((await db.execute(select(func.count(LiveOrder.id)).where(LiveOrder.deployment_id == row.id, LiveOrder.created_at >= day_start))).scalar() or 0)
    signals_count_today = int((await db.execute(select(func.count(LiveSignal.id)).where(LiveSignal.deployment_id == row.id, LiveSignal.created_at >= day_start))).scalar() or 0)
    total_orders = int((await db.execute(select(func.count(LiveOrder.id)).where(LiveOrder.deployment_id == row.id))).scalar() or 0)
    total_signals = int((await db.execute(select(func.count(LiveSignal.id)).where(LiveSignal.deployment_id == row.id))).scalar() or 0)

    latest_equity = (await db.execute(select(LiveEquityPoint.equity).where(LiveEquityPoint.deployment_id == row.id).order_by(LiveEquityPoint.timestamp.desc()).limit(1))).scalar_one_or_none()
    equity = _dec(latest_equity, str(_dec(row.capital, "100000") + realized + unrealized))

    latest_signal = (await db.execute(select(LiveSignal).where(LiveSignal.deployment_id == row.id).order_by(LiveSignal.created_at.desc()).limit(1))).scalar_one_or_none()
    latest_order = (await db.execute(select(LiveOrder).where(LiveOrder.deployment_id == row.id).order_by(LiveOrder.created_at.desc()).limit(1))).scalar_one_or_none()
    open_positions = (await db.execute(select(LivePosition).where(LivePosition.deployment_id == row.id, LivePosition.status == "OPEN").order_by(LivePosition.opened_at.desc()).limit(20))).scalars().all()
    recent_orders = await _recent(db, LiveOrder, row.id)
    recent_signals = await _recent(db, LiveSignal, row.id)
    recent_logs = await _recent(db, LiveTradeLog, row.id)
    latest_engine_signal = (await db.execute(select(LiveSignal).where(LiveSignal.deployment_id == row.id, LiveSignal.source == "ENGINE").order_by(LiveSignal.created_at.desc()).limit(1))).scalar_one_or_none()
    latest_runner_log = (await db.execute(select(LiveTradeLog).where(LiveTradeLog.deployment_id == row.id, LiveTradeLog.event_type.ilike("RUNNER_%")).order_by(LiveTradeLog.created_at.desc()).limit(1))).scalar_one_or_none()

    broker = None
    if row.broker_account_id:
        broker_row = (await db.execute(select(BrokerAccount).where(BrokerAccount.id == row.broker_account_id))).scalar_one_or_none()
        broker = _broker_safe(broker_row)

    currency = broker.get("currency") if isinstance(broker, dict) else None
    # DEMO deployments should display MT5 account balance/equity/currency when a broker is linked.
    if row.mode == "DEMO" and isinstance(broker, dict):
        broker_balance = broker.get("balance")
        broker_equity = broker.get("equity")
        capital_value = _dec(broker_balance, str(row.capital or "100000")) if broker_balance is not None else _dec(row.capital, "100000")
        if broker_equity is not None:
            equity = _dec(broker_equity, str(equity))
    else:
        capital_value = _dec(row.capital, "100000")

    return {
        "deployment": {
            "id": str(row.id),
            "name": row.name,
            "strategy_id": row.strategy_id,
            "strategy_name": _strategy_name(row),
            "instrument": row.instrument,
            "timeframe": row.timeframe,
            "mode": row.mode,
            "status": row.status,
            "auto_trade_enabled": row.auto_trade_enabled,
            "last_signal_at": row.last_signal_at,
            "last_heartbeat_at": row.last_heartbeat_at,
            "heartbeat_stale": bool(row.last_heartbeat_at and (datetime.now(timezone.utc) - row.last_heartbeat_at).total_seconds() > 180),
            "webhook_url": row.webhook_url,
            "tradingview_secret": row.tradingview_secret,
            "example_payload": row.example_payload,
        },
        "broker": broker,
        "metrics": {
            "capital": capital_value,
            "currency": currency,
            "equity": equity,
            "realized_pnl": realized,
            "unrealized_pnl": unrealized,
            "today_pnl": today_pnl,
            "open_positions": open_positions_count,
            "open_positions_count": open_positions_count,
            "orders_today": orders_count_today,
            "orders_count_today": orders_count_today,
            "signals_today": signals_count_today,
            "signals_count_today": signals_count_today,
            "total_orders": total_orders,
            "total_signals": total_signals,
        },
        "runner": {
            "last_run_at": latest_runner_log.created_at if latest_runner_log else None,
            "last_candle_time": latest_engine_signal.candle_time if latest_engine_signal else None,
            "last_signal": latest_engine_signal.signal_type if latest_engine_signal else None,
            "latest_runner_log": latest_runner_log.message if latest_runner_log else None,
            "latest_runner_status": latest_runner_log.level if latest_runner_log else None,
        },
        "latest_signal": dump_one(LiveSignalOut, latest_signal) if latest_signal else None,
        "latest_order": dump_one(LiveOrderOut, latest_order) if latest_order else None,
        "open_positions": dump_list(LivePositionOut, open_positions),
        "recent_orders": dump_list(LiveOrderOut, recent_orders),
        "recent_signals": dump_list(LiveSignalOut, recent_signals),
        "recent_logs": dump_list(LiveTradeLogOut, recent_logs),
    }


@router.get("")
async def list_deployments(db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    stmt = select(StrategyDeployment).order_by(StrategyDeployment.created_at.desc())
    if not is_admin(current_user):
        stmt = stmt.where(StrategyDeployment.user_id == user_id_from(current_user))
    rows = (await db.execute(stmt)).scalars().all()
    return success_response(dump_list(StrategyDeploymentOut, rows))


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_deployment(payload: StrategyDeploymentCreate, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    block_live_mode(payload.mode)
    await get_deployable_strategy_or_400(db, payload.strategy_id, payload.mode)
    if payload.mode == "DEMO" and not payload.broker_account_id:
        raise HTTPException(status_code=400, detail="DEMO mode requires an MT5 demo broker account")
    await _validate_broker_for_user(db, payload.broker_account_id, current_user)
    row = StrategyDeployment(user_id=user_id_from(current_user), status="DRAFT", **payload.model_dump())
    _ensure_tradingview_secret(row)
    db.add(row)
    await db.flush()
    await _write_log(db, row, "DEPLOYMENT_CREATED", "Deployment created")
    await db.commit()
    await db.refresh(row)
    return success_response(dump_one(StrategyDeploymentOut, row), "Deployment created")


@router.get("/{deployment_id}/summary")
async def get_deployment_summary(deployment_id: UUID, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    row = await get_deployment_or_404(db, deployment_id, current_user)
    return success_response(await _summary(db, row))


@router.get("/{deployment_id}/broker-status")
async def get_deployment_broker_status(deployment_id: UUID, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    row = await get_deployment_or_404(db, deployment_id, current_user)
    if not row.broker_account_id:
        return success_response({"connected": False, "message": "No broker account connected to this deployment", "broker": None})
    broker = (await db.execute(select(BrokerAccount).where(BrokerAccount.id == row.broker_account_id))).scalar_one_or_none()
    if broker is None:
        return success_response({"connected": False, "message": "Broker account not found", "broker": None})
    adapter = get_broker_adapter(broker)
    info = await adapter.get_account_info()
    connected = bool(info.get("connected"))
    broker.status = "CONNECTED" if connected else "ERROR"
    if connected:
        broker.last_connected_at = datetime.now(timezone.utc)
    broker.metadata_json = {
        **(broker.metadata_json or {}),
        "last_test": {
            "connected": connected,
            "message": info.get("message"),
            "account_login": info.get("account_login"),
            "server": info.get("server"),
            "balance": info.get("balance"),
            "equity": info.get("equity"),
            "currency": info.get("currency"),
        },
        "safe_message": info.get("message"),
        "provider": broker.broker_name,
    }
    await _write_log(db, row, "BROKER_STATUS_REFRESHED", info.get("message") or "Broker status refreshed", "INFO" if connected else "WARNING")
    await db.commit()
    await db.refresh(broker)
    return success_response({"connected": connected, "message": info.get("message"), "broker": _broker_safe(broker), "account_info": {k: v for k, v in info.items() if k != "raw"}})


@router.post("/{deployment_id}/manual-signal")
async def create_deployment_manual_signal(deployment_id: UUID, payload: ManualDeploymentSignalIn, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    row = await get_deployment_or_404(db, deployment_id, current_user)
    signal_type = payload.signal_type
    side = "LONG" if signal_type == "BUY" else "SHORT" if signal_type == "SELL" else None
    now = datetime.now(timezone.utc)
    signal = LiveSignal(
        deployment_id=row.id,
        user_id=row.user_id,
        strategy_id=row.strategy_id,
        source="MANUAL",
        symbol=row.instrument,
        timeframe=row.timeframe,
        signal_type=signal_type,
        side=side,
        price=payload.price,
        candle_time=payload.candle_time or now,
        confidence=None,
        reason=payload.reason or "Manual signal test",
        raw_payload={"source": "manual-signal-panel", "price": str(payload.price), "signal_type": signal_type},
        status="RECEIVED",
    )
    row.last_signal_at = now
    db.add(signal)
    await db.flush()
    await _write_log(db, row, "SIGNAL_RECEIVED", f"Manual {signal_type} signal received", metadata={"signal_id": str(signal.id), "price": str(payload.price)})

    latest_order = None
    message = "Signal saved"
    if row.status != "RUNNING":
        signal.status = "REJECTED"
        signal.rejection_reason = f"Deployment is {row.status}"
        message = signal.rejection_reason
        await _write_log(db, row, "RISK_REJECTED", message, "WARNING", {"signal_id": str(signal.id)})
    elif not row.auto_trade_enabled:
        signal.status = "ACCEPTED"
        message = "Auto trade is disabled; signal saved without execution"
        await _write_log(db, row, "EXECUTION_SKIPPED", message, metadata={"signal_id": str(signal.id)})
    else:
        latest_order = await execute_signal(db, row, signal)
        message = signal.rejection_reason or ("Signal executed" if signal.status == "EXECUTED" else f"Signal {signal.status.lower()}")

    await db.commit()
    await db.refresh(signal)
    if latest_order is not None:
        await db.refresh(latest_order)
    return success_response({
        "signal": dump_one(LiveSignalOut, signal),
        "order": dump_one(LiveOrderOut, latest_order) if latest_order else None,
        "message": message,
        "status": signal.status,
    }, message)


@router.post("/{deployment_id}/run-strategy-once")
async def run_live_strategy_once(deployment_id: UUID, payload: RunStrategyOnceIn | None = None, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    await get_deployment_or_404(db, deployment_id, current_user)
    result = await run_strategy_for_deployment(db, deployment_id, execute=(payload.execute if payload else True))
    return success_response(result, result.get("message") or "Strategy runner completed")

@router.post("/{deployment_id}/refresh-candles")
async def refresh_deployment_mt5_candles(deployment_id: UUID, count: int = 300, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    # Access check first; candle service then validates linked MT5 DEMO broker and stores real MT5 rates only.
    await get_deployment_or_404(db, deployment_id, current_user)
    result = await refresh_deployment_candles(db, deployment_id, count=count)
    return success_response(result, f"Stored {result.get('upserted_count', 0)} MT5 candles")


@router.get("/{deployment_id}/candles")
async def get_deployment_mt5_candles(deployment_id: UUID, limit: int = 300, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    await get_deployment_or_404(db, deployment_id, current_user)
    result = await get_candle_snapshot(db, deployment_id, limit=limit)
    return success_response(result)


@router.get("/{deployment_id}")
async def get_deployment(deployment_id: UUID, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    row = await get_deployment_or_404(db, deployment_id, current_user)
    if not row.tradingview_secret:
        _ensure_tradingview_secret(row)
        await db.commit()
        await db.refresh(row)
    return success_response(dump_one(StrategyDeploymentOut, row))


@router.patch("/{deployment_id}")
async def update_deployment(deployment_id: UUID, payload: StrategyDeploymentUpdate, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    row = await get_deployment_or_404(db, deployment_id, current_user)
    values = payload.model_dump(exclude_unset=True)
    if "mode" in values:
        block_live_mode(values["mode"])
        await get_deployable_strategy_or_400(db, row.strategy_id, values["mode"])
        if values["mode"] == "DEMO" and not values.get("broker_account_id", row.broker_account_id):
            raise HTTPException(status_code=400, detail="DEMO mode requires an MT5 demo broker account")
    if "broker_account_id" in values:
        await _validate_broker_for_user(db, values["broker_account_id"], current_user)
    update_from_payload(row, payload, exclude={"status"})
    await _write_log(db, row, "DEPLOYMENT_UPDATED", "Deployment updated")
    await db.commit()
    await db.refresh(row)
    return success_response(dump_one(StrategyDeploymentOut, row), "Deployment updated")


@router.post("/{deployment_id}/start")
async def start_deployment(deployment_id: UUID, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    row = await get_deployment_or_404(db, deployment_id, current_user)
    block_live_mode(row.mode)
    platform_check = await check_platform_mode_allowed(db, row.mode)
    if not platform_check.allowed:
        raise HTTPException(status_code=400, detail=platform_check.reason)
    await get_deployable_strategy_or_400(db, row.strategy_id, row.mode)
    if row.mode == "DEMO":
        if row.broker_account_id is None:
            raise HTTPException(status_code=400, detail="DEMO mode requires a connected MT5 demo broker account")
        broker = (await db.execute(select(BrokerAccount).where(BrokerAccount.id == row.broker_account_id))).scalar_one_or_none()
        if broker is None or broker.status != "CONNECTED":
            raise HTTPException(status_code=400, detail="DEMO mode requires a CONNECTED MT5 broker account. Go to Brokers and click Test Connection first.")
    now = datetime.now(timezone.utc)
    row.status = "RUNNING"
    row.started_at = now
    row.stopped_at = None
    row.last_heartbeat_at = now
    await _write_log(db, row, "DEPLOYMENT_STARTED", "Deployment started")
    await db.commit()
    await db.refresh(row)
    return success_response(dump_one(StrategyDeploymentOut, row), "Deployment started")


@router.post("/{deployment_id}/pause")
async def pause_deployment(deployment_id: UUID, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    row = await get_deployment_or_404(db, deployment_id, current_user)
    row.status = "PAUSED"
    await _write_log(db, row, "DEPLOYMENT_PAUSED", "Deployment paused")
    await db.commit()
    await db.refresh(row)
    return success_response(dump_one(StrategyDeploymentOut, row), "Deployment paused")


@router.post("/{deployment_id}/stop")
async def stop_deployment(deployment_id: UUID, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    row = await get_deployment_or_404(db, deployment_id, current_user)
    row.status = "STOPPED"
    row.stopped_at = datetime.now(timezone.utc)
    await _write_log(db, row, "DEPLOYMENT_STOPPED", "Deployment stopped")
    await db.commit()
    await db.refresh(row)
    return success_response(dump_one(StrategyDeploymentOut, row), "Deployment stopped")
