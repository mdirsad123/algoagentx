from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.dependencies import get_admin_user, get_db
from ...db.models import AdminLiveAction, LiveTradeLog, StrategyDeployment
from ...utils.api_response import success_response

router = APIRouter()


def _admin_id(current_user: dict) -> UUID:
    return UUID(str(current_user["user_id"]))


async def _audit(db: AsyncSession, admin_id: UUID, row: StrategyDeployment, action: str, message: str):
    db.add(AdminLiveAction(admin_user_id=admin_id, deployment_id=row.id, action=action, reason=message, metadata_json={"global_action": True}))
    db.add(LiveTradeLog(deployment_id=row.id, user_id=row.user_id, event_type=f"ADMIN_{action}", level="WARNING", message=message, metadata_json={"admin_user_id": str(admin_id), "global_action": True}))


@router.post("/force-stop-all")
async def force_stop_all(db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_admin_user)):
    admin_id = _admin_id(current_user)
    rows = (await db.execute(select(StrategyDeployment).where(StrategyDeployment.status.in_(["RUNNING", "PAUSED"])))).scalars().all()
    now = datetime.now(timezone.utc)
    for row in rows:
        row.status = "STOPPED"
        row.stopped_at = now
        await _audit(db, admin_id, row, "FORCE_STOP_ALL", "Admin emergency force-stopped all active deployments")
    await db.commit()
    return success_response({"affected": len(rows)}, "All active deployments force stopped")


@router.post("/pause-all-demo")
async def pause_all_demo(db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_admin_user)):
    admin_id = _admin_id(current_user)
    rows = (await db.execute(select(StrategyDeployment).where(StrategyDeployment.status == "RUNNING", StrategyDeployment.mode == "DEMO"))).scalars().all()
    for row in rows:
        row.status = "PAUSED"
        await _audit(db, admin_id, row, "PAUSE_ALL_DEMO", "Admin emergency paused all running MT5 DEMO deployments")
    await db.commit()
    return success_response({"affected": len(rows)}, "All running demo deployments paused")
