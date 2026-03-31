from __future__ import annotations

from typing import Optional
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.dependencies import get_admin_user, get_db
from ...db.models.strategy_requests import StrategyRequest
from ...db.models.strategies import Strategy
from ...db.models.users import User

logger = logging.getLogger(__name__)
router = APIRouter()


def _serialize_dt(value):
    return value.isoformat() if value else None


@router.get("")
@router.get("/")
async def list_strategy_requests(
    skip: int = 0,
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    search: Optional[str] = None,
    admin_user: dict = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(StrategyRequest, User.email, User.fullname)
        .join(User, User.id == StrategyRequest.user_id)
        .order_by(StrategyRequest.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    count_stmt = select(func.count()).select_from(StrategyRequest).join(User, User.id == StrategyRequest.user_id)
    filters = []
    if status:
        filters.append(StrategyRequest.status == status)
    if search:
        like = f"%{search}%"
        filters.append(or_(StrategyRequest.title.ilike(like), StrategyRequest.strategy_type.ilike(like), User.email.ilike(like), User.fullname.ilike(like)))
    if filters:
        stmt = stmt.where(*filters)
        count_stmt = count_stmt.where(*filters)

    rows = (await db.execute(stmt)).all()
    total = (await db.execute(count_stmt)).scalar() or 0
    items = []
    for req, email, fullname in rows:
        items.append(
            {
                "id": str(req.id),
                "title": req.title,
                "strategy_type": req.strategy_type,
                "market": req.market,
                "timeframe": req.timeframe,
                "description": req.notes or req.entry_rules,
                "status": req.status,
                "user_id": str(req.user_id),
                "user_email": email,
                "user_name": fullname,
                "admin_notes": req.admin_notes,
                "created_at": _serialize_dt(req.created_at),
                "updated_at": _serialize_dt(req.updated_at),
            }
        )

    implemented = (await db.execute(select(Strategy).order_by(Strategy.created_at.desc()).limit(50))).scalars().all()
    implemented_items = [
        {
            "id": str(item.id),
            "name": item.name,
            "description": item.description,
            "code": item.parameters,
            "status": "ACTIVE",
            "created_at": _serialize_dt(item.created_at),
        }
        for item in implemented
    ]
    return {"items": items, "implemented": implemented_items, "total": total, "skip": skip, "limit": limit}


@router.get("/{request_id}")
async def get_strategy_request_detail(
    request_id: str,
    admin_user: dict = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    row = (
        await db.execute(
            select(StrategyRequest, User.email, User.fullname)
            .join(User, User.id == StrategyRequest.user_id)
            .where(StrategyRequest.id == request_id)
        )
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Strategy request not found")
    req, email, fullname = row
    return {
        "id": str(req.id),
        "title": req.title,
        "strategy_type": req.strategy_type,
        "market": req.market,
        "timeframe": req.timeframe,
        "indicators": req.indicators,
        "entry_rules": req.entry_rules,
        "exit_rules": req.exit_rules,
        "risk_rules": req.risk_rules,
        "notes": req.notes,
        "status": req.status,
        "admin_notes": req.admin_notes,
        "assigned_to": req.assigned_to,
        "deployed_strategy_id": str(req.deployed_strategy_id) if req.deployed_strategy_id else None,
        "user_id": str(req.user_id),
        "user_email": email,
        "user_name": fullname,
        "created_at": _serialize_dt(req.created_at),
        "updated_at": _serialize_dt(req.updated_at),
    }


@router.patch("/{request_id}")
async def update_strategy_request(
    request_id: str,
    payload: dict,
    admin_user: dict = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    req = await db.get(StrategyRequest, request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Strategy request not found")
    status_value = payload.get("status")
    if status_value:
        req.status = status_value
    if "admin_notes" in payload:
        req.admin_notes = payload.get("admin_notes")
    if "assigned_to" in payload:
        req.assigned_to = payload.get("assigned_to")
    await db.commit()
    return {"message": "Strategy request updated successfully"}
