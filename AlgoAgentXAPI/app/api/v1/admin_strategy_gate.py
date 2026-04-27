from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.dependencies import get_admin_user, get_db
from ...db.compat import as_uuid_or_str, column_text
from ...db.models.strategies import Strategy
from ...utils.api_response import success_response

router = APIRouter()


class StrategyDeploymentGateIn(BaseModel):
    is_deployable_paper: Optional[bool] = None
    is_deployable_demo: Optional[bool] = None
    is_live_approved: Optional[bool] = None
    reason: Optional[str] = None


def _serialize_dt(value: Any) -> Optional[str]:
    return value.isoformat() if value else None


def _serialize_strategy(strategy: Strategy) -> dict[str, Any]:
    params = strategy.parameters if isinstance(strategy.parameters, dict) else {}
    return {
        "id": str(strategy.id),
        "name": strategy.name,
        "description": strategy.description,
        "visibility": getattr(strategy, "visibility", None),
        "status": "PUBLISHED" if str(getattr(strategy, "visibility", "")).upper() == "PUBLIC" else "PRIVATE",
        "parameters": params,
        "lifecycle_status": getattr(strategy, "lifecycle_status", None) or "DRAFT",
        "lifecycleStatus": getattr(strategy, "lifecycle_status", None) or "DRAFT",
        "is_deployable_paper": bool(getattr(strategy, "is_deployable_paper", False)),
        "isDeployablePaper": bool(getattr(strategy, "is_deployable_paper", False)),
        "is_deployable_demo": bool(getattr(strategy, "is_deployable_demo", False)),
        "isDeployableDemo": bool(getattr(strategy, "is_deployable_demo", False)),
        "is_live_approved": bool(getattr(strategy, "is_live_approved", False)),
        "isLiveApproved": bool(getattr(strategy, "is_live_approved", False)),
        "verified_at": _serialize_dt(getattr(strategy, "verified_at", None)),
        "verifiedAt": _serialize_dt(getattr(strategy, "verified_at", None)),
        "sandbox_passed_at": _serialize_dt(getattr(strategy, "sandbox_passed_at", None)),
        "sandboxPassedAt": _serialize_dt(getattr(strategy, "sandbox_passed_at", None)),
        "paper_enabled_at": _serialize_dt(getattr(strategy, "paper_enabled_at", None)),
        "paperEnabledAt": _serialize_dt(getattr(strategy, "paper_enabled_at", None)),
        "demo_enabled_at": _serialize_dt(getattr(strategy, "demo_enabled_at", None)),
        "demoEnabledAt": _serialize_dt(getattr(strategy, "demo_enabled_at", None)),
        "live_approved_at": _serialize_dt(getattr(strategy, "live_approved_at", None)),
        "liveApprovedAt": _serialize_dt(getattr(strategy, "live_approved_at", None)),
        "approved_by": str(getattr(strategy, "approved_by", None)) if getattr(strategy, "approved_by", None) else None,
        "approvedBy": str(getattr(strategy, "approved_by", None)) if getattr(strategy, "approved_by", None) else None,
        "created_at": _serialize_dt(getattr(strategy, "created_at", None)),
        "updated_at": _serialize_dt(getattr(strategy, "updated_at", None)),
    }


async def _get_strategy_or_404(db: AsyncSession, strategy_id: str) -> Strategy:
    strategy = (await db.execute(select(Strategy).where(column_text(Strategy.id) == str(strategy_id)))).scalar_one_or_none()
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return strategy


@router.post("/{strategy_id}/deployment-gate")
async def update_strategy_deployment_gate(
    strategy_id: str,
    payload: StrategyDeploymentGateIn,
    admin_user: dict = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    strategy = await _get_strategy_or_404(db, strategy_id)
    now = datetime.now(timezone.utc)
    params = dict(strategy.parameters or {})
    history = list(params.get("_deployment_gate_history") or [])
    previous = {
        "is_deployable_paper": bool(getattr(strategy, "is_deployable_paper", False)),
        "is_deployable_demo": bool(getattr(strategy, "is_deployable_demo", False)),
        "is_live_approved": bool(getattr(strategy, "is_live_approved", False)),
    }

    if payload.is_deployable_paper is not None:
        strategy.is_deployable_paper = bool(payload.is_deployable_paper)
        strategy.paper_enabled_at = now if payload.is_deployable_paper else None
    if payload.is_deployable_demo is not None:
        strategy.is_deployable_demo = bool(payload.is_deployable_demo)
        strategy.demo_enabled_at = now if payload.is_deployable_demo else None
    if payload.is_live_approved is not None:
        strategy.is_live_approved = bool(payload.is_live_approved)
        strategy.live_approved_at = now if payload.is_live_approved else None

    if any(value is not None for value in [payload.is_deployable_paper, payload.is_deployable_demo, payload.is_live_approved]):
        strategy.approved_by = as_uuid_or_str(admin_user["user_id"])

    if strategy.is_live_approved:
        strategy.lifecycle_status = "LIVE_APPROVED"
    elif strategy.is_deployable_demo:
        strategy.lifecycle_status = "DEMO_READY"
    elif strategy.is_deployable_paper:
        strategy.lifecycle_status = "PAPER_READY"
    elif getattr(strategy, "sandbox_passed_at", None):
        strategy.lifecycle_status = "SANDBOX_PASSED"
    elif getattr(strategy, "verified_at", None):
        strategy.lifecycle_status = "VERIFIED"
    else:
        strategy.lifecycle_status = "DRAFT"

    history.insert(0, {
        "changed_at": now.isoformat(),
        "admin_user_id": str(admin_user.get("user_id")),
        "reason": payload.reason or "Deployment gate updated",
        "previous": previous,
        "current": {
            "is_deployable_paper": bool(strategy.is_deployable_paper),
            "is_deployable_demo": bool(strategy.is_deployable_demo),
            "is_live_approved": bool(strategy.is_live_approved),
            "lifecycle_status": strategy.lifecycle_status,
        },
    })
    params["_deployment_gate_history"] = history[:50]
    strategy.parameters = params

    await db.commit()
    await db.refresh(strategy)
    return success_response(_serialize_strategy(strategy), "Deployment gate updated")
