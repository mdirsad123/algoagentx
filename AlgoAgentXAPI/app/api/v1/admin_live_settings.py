from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.dependencies import get_admin_user, get_db
from ...db.models import PlatformTradingSettings
from ...services.live.trading_safety import get_platform_trading_settings
from ...utils.api_response import success_response

router = APIRouter()


class PlatformTradingSettingsIn(BaseModel):
    paper_trading_enabled: Optional[bool] = None
    demo_trading_enabled: Optional[bool] = None
    live_trading_enabled: Optional[bool] = None
    global_kill_switch: Optional[bool] = None
    max_global_demo_orders_per_day: Optional[int] = Field(default=None, ge=0)
    max_user_demo_orders_per_day: Optional[int] = Field(default=None, ge=0)


def _admin_id(current_user: dict) -> UUID:
    return UUID(str(current_user["user_id"]))


def _out(row: PlatformTradingSettings) -> dict:
    return {
        "id": str(row.id),
        "paper_trading_enabled": bool(row.paper_trading_enabled),
        "demo_trading_enabled": bool(row.demo_trading_enabled),
        "live_trading_enabled": bool(row.live_trading_enabled),
        "global_kill_switch": bool(row.global_kill_switch),
        "max_global_demo_orders_per_day": row.max_global_demo_orders_per_day,
        "max_user_demo_orders_per_day": row.max_user_demo_orders_per_day,
        "updated_by": str(row.updated_by) if row.updated_by else None,
        "updated_at": row.updated_at,
    }


@router.get("")
async def get_live_settings(db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_admin_user)):
    row = await get_platform_trading_settings(db)
    await db.commit()
    return success_response(_out(row))


@router.patch("")
async def update_live_settings(payload: PlatformTradingSettingsIn, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_admin_user)):
    row = await get_platform_trading_settings(db)
    values = payload.model_dump(exclude_unset=True)
    if values.get("live_trading_enabled"):
        values["live_trading_enabled"] = False
    for key, value in values.items():
        setattr(row, key, value)
    row.updated_by = _admin_id(current_user)
    row.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(row)
    return success_response(_out(row), "Live trading safety settings updated")


@router.post("/kill-switch/on")
async def kill_switch_on(db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_admin_user)):
    row = await get_platform_trading_settings(db)
    row.global_kill_switch = True
    row.updated_by = _admin_id(current_user)
    row.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(row)
    return success_response(_out(row), "Global kill switch enabled")


@router.post("/kill-switch/off")
async def kill_switch_off(db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_admin_user)):
    row = await get_platform_trading_settings(db)
    row.global_kill_switch = False
    row.updated_by = _admin_id(current_user)
    row.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(row)
    return success_response(_out(row), "Global kill switch disabled")
