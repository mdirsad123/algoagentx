from __future__ import annotations

import secrets
from datetime import datetime, time, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.dependencies import get_current_user, get_db
from ...db.models import BrokerAccount, LiveEquityPoint, LiveOrder, LivePosition, LiveSignal, LiveTradeLog, StrategyDeployment
from ...schemas.live_trading import LiveSignalOut, ManualDeploymentSignalIn, StrategyDeploymentCreate, StrategyDeploymentOut, StrategyDeploymentUpdate
from ...services.live.execution_engine import execute_signal
from ...services.live.pnl_service import to_decimal
from ...utils.api_response import success_response
from .live_common import (
    block_live_mode,
    dump_list,
    dump_one,
    get_broker_account_or_404,
    get_deployment_or_404,
    get_published_strategy_or_400,
    is_admin,
    update_from_payload,
    user_id_from,
)

router = APIRouter()


def _ensure_tradingview_secret(row: StrategyDeployment) -> None:
    if not row.tradingview_secret:
        row.tradingview_secret = secrets.token_urlsafe(32)


async def _validate_broker_for_user(db: AsyncSession, broker_account_id: UUID | None, current_user: dict) -> None:
    if broker_account_id is None:
        return
    await get_broker_account_or_404(db, broker_account_id, current_user)


async def _write_log(db: AsyncSession, deployment: StrategyDeployment, event_type: str, message: str, level: str = "INFO", metadata: dict | None = None) -> None:
    db.add(
        LiveTradeLog(
            deployment_id=deployment.id,
            user_id=deployment.user_id,
            event_type=event_type,
            level=level,
            message=message,
            metadata_json=metadata or {"status": deployment.status, "mode": deployment.mode},
        )
    )


async def _deployment_summary(db: AsyncSession, row: StrategyDeployment) -> dict:
    day_start = datetime.combine(datetime.now(timezone.utc).date(), time.min, tzinfo=timezone.utc)
    realized = to_decimal((await db.execute(
        select(func.coalesce(func.sum(LivePosition.realized_pnl), 0)).where(LivePosition.deployment_id == row.id)
    )).scalar())
    unrealized = to_decimal((await db.execute(
        select(func.coalesce(func.sum(LivePosition.unrealized_pnl), 0)).where(
            LivePosition.deployment_id == row.id,
            LivePosition.status == "OPEN",
        )
    )).scalar())
    today_pnl = to_decimal((await db.execute(
        select(func.coalesce(func.sum(LivePosition.realized_pnl), 0)).where(
            LivePosition.deployment_id == row.id,
            LivePosition.closed_at >= day_start,
        )
    )).scalar())
    open_positions_count = int((await db.execute(
        select(func.count(LivePosition.id)).where(LivePosition.deployment_id == row.id, LivePosition.status == "OPEN")
    )).scalar() or 0)
    orders_count_today = int((await db.execute(
        select(func.count(LiveOrder.id)).where(LiveOrder.deployment_id == row.id, LiveOrder.created_at >= day_start)
    )).scalar() or 0)
    signals_count_today = int((await db.execute(
        select(func.count(LiveSignal.id)).where(LiveSignal.deployment_id == row.id, LiveSignal.created_at >= day_start)
    )).scalar() or 0)
    latest_equity = (await db.execute(
        select(LiveEquityPoint.equity).where(LiveEquityPoint.deployment_id == row.id).order_by(LiveEquityPoint.timestamp.desc()).limit(1)
    )).scalar_one_or_none()
    equity = to_decimal(latest_equity, str(to_decimal(row.capital, "100000") + realized + unrealized))
    return {
        "status": row.status,
        "mode": row.mode,
        "today_pnl": today_pnl,
        "realized_pnl": realized,
        "unrealized_pnl": unrealized,
        "open_positions_count": open_positions_count,
        "orders_count_today": orders_count_today,
        "signals_count_today": signals_count_today,
        "equity": equity,
    }


@router.get("")
async def list_deployments(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    stmt = select(StrategyDeployment).order_by(StrategyDeployment.created_at.desc())
    if not is_admin(current_user):
        stmt = stmt.where(StrategyDeployment.user_id == user_id_from(current_user))
    rows = (await db.execute(stmt)).scalars().all()
    return success_response(dump_list(StrategyDeploymentOut, rows))


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_deployment(
    payload: StrategyDeploymentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    block_live_mode(payload.mode)
    await get_published_strategy_or_400(db, payload.strategy_id)
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
async def get_deployment_summary(
    deployment_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    row = await get_deployment_or_404(db, deployment_id, current_user)
    return success_response(await _deployment_summary(db, row))


@router.post("/{deployment_id}/manual-signal")
async def create_deployment_manual_signal(
    deployment_id: UUID,
    payload: ManualDeploymentSignalIn,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    row = await get_deployment_or_404(db, deployment_id, current_user)
    side = "LONG" if payload.signal_type == "BUY" else "SHORT" if payload.signal_type == "SELL" else None
    signal = LiveSignal(
        deployment_id=row.id,
        user_id=row.user_id,
        strategy_id=row.strategy_id,
        source="MANUAL",
        symbol=row.instrument,
        timeframe=row.timeframe,
        signal_type=payload.signal_type,
        side=side,
        price=payload.price,
        candle_time=payload.candle_time or datetime.now(timezone.utc),
        confidence=None,
        reason=payload.reason or "Manual paper test",
        raw_payload={"source": "manual-signal-panel", "price": str(payload.price), "signal_type": payload.signal_type},
        status="ACCEPTED",
    )
    row.last_signal_at = datetime.now(timezone.utc)
    db.add(signal)
    await db.flush()
    await _write_log(db, row, "SIGNAL_RECEIVED", f"Manual {payload.signal_type} signal received for paper execution", metadata={"signal_id": str(signal.id), "price": str(payload.price)})
    if row.status == "RUNNING" and row.auto_trade_enabled:
        await execute_signal(db, row, signal)
    elif row.status != "RUNNING":
        signal.status = "REJECTED"
        signal.rejection_reason = f"Deployment is {row.status}"
        await _write_log(db, row, "RISK_REJECTED", signal.rejection_reason, "WARNING", {"signal_id": str(signal.id)})
    else:
        await _write_log(db, row, "EXECUTION_SKIPPED", "Auto trade is disabled; manual signal saved only", metadata={"signal_id": str(signal.id)})
    await db.commit()
    await db.refresh(signal)
    return success_response(dump_one(LiveSignalOut, signal), "Manual signal processed")


@router.get("/{deployment_id}")
async def get_deployment(
    deployment_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    row = await get_deployment_or_404(db, deployment_id, current_user)
    if not row.tradingview_secret:
        _ensure_tradingview_secret(row)
        await db.commit()
        await db.refresh(row)
    return success_response(dump_one(StrategyDeploymentOut, row))


@router.patch("/{deployment_id}")
async def update_deployment(
    deployment_id: UUID,
    payload: StrategyDeploymentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    row = await get_deployment_or_404(db, deployment_id, current_user)
    values = payload.model_dump(exclude_unset=True)
    if "mode" in values:
        block_live_mode(values["mode"])
    if "broker_account_id" in values:
        await _validate_broker_for_user(db, values["broker_account_id"], current_user)
    update_from_payload(row, payload, exclude={"status"})
    await _write_log(db, row, "DEPLOYMENT_UPDATED", "Deployment updated")
    await db.commit()
    await db.refresh(row)
    return success_response(dump_one(StrategyDeploymentOut, row), "Deployment updated")


@router.post("/{deployment_id}/start")
async def start_deployment(
    deployment_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    row = await get_deployment_or_404(db, deployment_id, current_user)
    block_live_mode(row.mode)
    await get_published_strategy_or_400(db, row.strategy_id)

    if row.mode == "DEMO":
        if row.broker_account_id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="DEMO mode requires a broker account")
        broker = (await db.execute(select(BrokerAccount).where(BrokerAccount.id == row.broker_account_id))).scalar_one_or_none()
        if broker is None or broker.status != "CONNECTED":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="DEMO mode requires a CONNECTED MT5 broker account. Go to Brokers and click Test Connection first.")

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
async def pause_deployment(
    deployment_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    row = await get_deployment_or_404(db, deployment_id, current_user)
    row.status = "PAUSED"
    await _write_log(db, row, "DEPLOYMENT_PAUSED", "Deployment paused")
    await db.commit()
    await db.refresh(row)
    return success_response(dump_one(StrategyDeploymentOut, row), "Deployment paused")


@router.post("/{deployment_id}/stop")
async def stop_deployment(
    deployment_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    row = await get_deployment_or_404(db, deployment_id, current_user)
    row.status = "STOPPED"
    row.stopped_at = datetime.now(timezone.utc)
    await _write_log(db, row, "DEPLOYMENT_STOPPED", "Deployment stopped")
    await db.commit()
    await db.refresh(row)
    return success_response(dump_one(StrategyDeploymentOut, row), "Deployment stopped")
