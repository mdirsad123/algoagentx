from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.dependencies import get_current_user, get_db
from ...db.models import LiveSignal, LiveTradeLog, StrategyDeployment
from ...schemas.live_trading import LiveSignalCreate, LiveSignalOut
from ...utils.api_response import success_response
from .live_common import dump_list, dump_one, get_deployment_or_404, is_admin, user_id_from

router = APIRouter()


@router.get("")
async def list_signals(
    deployment_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    stmt = select(LiveSignal).order_by(LiveSignal.created_at.desc())
    if deployment_id:
        stmt = stmt.where(LiveSignal.deployment_id == deployment_id)
    if not is_admin(current_user):
        stmt = stmt.where(LiveSignal.user_id == user_id_from(current_user))
    rows = (await db.execute(stmt)).scalars().all()
    return success_response(dump_list(LiveSignalOut, rows))


@router.post("/manual")
async def create_manual_signal(
    payload: LiveSignalCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    deployment: StrategyDeployment = await get_deployment_or_404(db, payload.deployment_id, current_user)
    symbol = payload.symbol or deployment.instrument
    timeframe = payload.timeframe or deployment.timeframe
    raw_payload = payload.raw_payload or {}

    row = LiveSignal(
        deployment_id=deployment.id,
        user_id=deployment.user_id,
        strategy_id=deployment.strategy_id,
        source="MANUAL",
        symbol=symbol,
        timeframe=timeframe,
        signal_type=payload.signal_type,
        side=payload.side,
        price=payload.price,
        candle_time=payload.candle_time,
        confidence=payload.confidence,
        reason=payload.reason,
        raw_payload=raw_payload,
        status="ACCEPTED" if deployment.status in {"RUNNING", "PAUSED", "DRAFT", "STOPPED"} else "RECEIVED",
    )
    deployment.last_signal_at = datetime.now(timezone.utc)
    db.add(row)
    db.add(
        LiveTradeLog(
            deployment_id=deployment.id,
            user_id=deployment.user_id,
            event_type="SIGNAL_RECEIVED",
            level="INFO",
            message=f"Manual {payload.signal_type} signal received for {symbol}",
            metadata_json={"source": "MANUAL", "signal_type": payload.signal_type},
        )
    )
    await db.commit()
    await db.refresh(row)
    return success_response(dump_one(LiveSignalOut, row), "Manual signal saved")
