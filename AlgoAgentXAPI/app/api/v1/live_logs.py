from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.dependencies import get_current_user, get_db
from ...db.models import LiveTradeLog
from ...schemas.live_trading import LiveTradeLogOut
from ...utils.api_response import success_response
from .live_common import dump_list, is_admin, user_id_from

router = APIRouter()


@router.get("")
async def list_logs(
    deployment_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    stmt = select(LiveTradeLog).order_by(LiveTradeLog.created_at.desc())
    if deployment_id:
        stmt = stmt.where(LiveTradeLog.deployment_id == deployment_id)
    if not is_admin(current_user):
        stmt = stmt.where(LiveTradeLog.user_id == user_id_from(current_user))
    rows = (await db.execute(stmt)).scalars().all()
    return success_response(dump_list(LiveTradeLogOut, rows))
