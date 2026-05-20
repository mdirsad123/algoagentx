from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.dependencies import get_admin_user, get_current_user, get_db
from ...db.models import LiveTradeLog, StrategyDeployment
from ...services.live.auto_runner_service import run_due_deployments
from ...services.live.runner_scheduler import calculate_next_runner_at
from datetime import datetime, timezone
from ...utils.api_response import success_response
from .live_common import get_deployment_or_404
from ...services.billing.live_subscription_gate import require_active_subscription_for_live_trading

router = APIRouter()


async def _set_auto_runner(db: AsyncSession, deployment: StrategyDeployment, enabled: bool) -> StrategyDeployment:
    deployment.auto_runner_enabled = enabled
    if enabled:
        deployment.runner_error_count = 0
        deployment.runner_last_error = None
        now = datetime.now(timezone.utc)
        deployment.next_run_at = calculate_next_runner_at(now, deployment.timeframe, int(getattr(deployment, "broker_delay_seconds", None) or 3))
    db.add(LiveTradeLog(
        deployment_id=deployment.id,
        user_id=deployment.user_id,
        event_type="AUTO_RUNNER_ENABLED" if enabled else "AUTO_RUNNER_DISABLED",
        level="INFO",
        message="Auto runner enabled" if enabled else "Auto runner disabled",
        metadata_json={"auto_runner_enabled": enabled, "next_run_at": deployment.next_run_at.isoformat() if enabled and getattr(deployment, "next_run_at", None) else None},
    ))
    await db.commit()
    await db.refresh(deployment)
    return deployment


@router.post("/tick")
async def manual_auto_runner_tick(db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_admin_user)):
    result = await run_due_deployments(db)
    return success_response(result, "Auto runner tick completed")


@router.post("/deployments/{deployment_id}/auto-runner/enable")
async def enable_auto_runner(deployment_id: UUID, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    deployment = await get_deployment_or_404(db, deployment_id, current_user)
    await require_active_subscription_for_live_trading(db, str(deployment.user_id))
    row = await _set_auto_runner(db, deployment, True)
    return success_response({"deployment_id": str(row.id), "auto_runner_enabled": row.auto_runner_enabled, "last_runner_at": row.last_runner_at, "next_run_at": getattr(row, "next_run_at", None), "last_processed_candle_time": row.last_processed_candle_time, "runner_error_count": row.runner_error_count, "runner_last_error": row.runner_last_error}, "Auto runner enabled")


@router.post("/deployments/{deployment_id}/auto-runner/disable")
async def disable_auto_runner(deployment_id: UUID, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    deployment = await get_deployment_or_404(db, deployment_id, current_user)
    row = await _set_auto_runner(db, deployment, False)
    return success_response({"deployment_id": str(row.id), "auto_runner_enabled": row.auto_runner_enabled, "last_runner_at": row.last_runner_at, "next_run_at": getattr(row, "next_run_at", None), "last_processed_candle_time": row.last_processed_candle_time, "runner_error_count": row.runner_error_count, "runner_last_error": row.runner_last_error}, "Auto runner disabled")
