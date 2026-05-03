from __future__ import annotations

from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.dependencies import get_current_user, get_db
from ...db.models import BrokerAccount, StrategyDeployment
from ...services.brokers.factory import get_broker_code
from ...services.live.order_preview_service import build_live_order_preview
from ...utils.api_response import success_response
from .live_common import get_deployment_or_404, is_admin, user_id_from

router = APIRouter()


class LiveOrderPreviewIn(BaseModel):
    deployment_id: Optional[UUID] = None
    mode: str = Field(default="MANUAL")
    strategy_id: Optional[str] = None
    strategy_preset_id: Optional[str] = None
    instrument_id: Optional[int] = None
    symbol: Optional[str] = None
    side: str = Field(default="BUY")
    entry_price: Optional[float] = None
    market_price: Optional[float] = None
    stop_loss: Optional[float] = None
    runtime_config: Optional[dict[str, Any]] = None


@router.post("/order-preview")
async def preview_live_order(payload: LiveOrderPreviewIn, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    deployment = None
    broker_code = None
    if payload.deployment_id:
        deployment = await get_deployment_or_404(db, payload.deployment_id, current_user)
        if deployment.broker_account_id:
            broker = (await db.execute(select(BrokerAccount).where(BrokerAccount.id == deployment.broker_account_id))).scalar_one_or_none()
            broker_code = get_broker_code(broker) if broker is not None else None
    elif not payload.strategy_id:
        raise HTTPException(status_code=400, detail="deployment_id or strategy_id is required")

    result = await build_live_order_preview(
        db,
        deployment=deployment,
        broker_code=broker_code,
        instrument_id=payload.instrument_id,
        symbol=payload.symbol,
        side=payload.side,
        entry_price=payload.entry_price or payload.market_price,
        stop_loss=payload.stop_loss,
        preview_mode=payload.mode,
        runtime_config=payload.runtime_config,
        strategy_id=payload.strategy_id,
        strategy_preset_id=payload.strategy_preset_id,
        strict_instrument=True,
    )
    return success_response(result, "Live order sizing preview generated")
