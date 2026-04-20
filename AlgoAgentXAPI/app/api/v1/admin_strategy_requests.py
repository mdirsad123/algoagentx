from __future__ import annotations

from typing import Any, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.dependencies import get_admin_user, get_db
from ...db.compat import as_uuid_or_str, column_text
from ...db.models.strategy_requests import StrategyRequest
from ...db.models.strategies import Strategy
from ...db.models.users import User
from ...utils.api_response import success_response
from .strategies import (
    PRIVATE_VISIBILITY,
    PUBLIC_VISIBILITY,
    VALID_REQUEST_STATUSES,
    _safe_float,
    _safe_int,
    _upsert_strategy_from_request,
)

router = APIRouter()
VALID_VISIBILITY = {PRIVATE_VISIBILITY, PUBLIC_VISIBILITY}


class StrategyRequestPatchIn(BaseModel):
    status: Optional[str] = None
    admin_notes: Optional[str] = None
    assigned_to: Optional[str] = None


class DeployRequestIn(BaseModel):
    strategy_id: Optional[str] = None
    strategy_name: Optional[str] = Field(default=None, max_length=255)
    strategy_description: Optional[str] = None
    publish: bool = False
    visibility: Optional[str] = None
    admin_notes: Optional[str] = None


class StrategyCreateIn(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = None
    strategy_type: Optional[str] = None
    market: Optional[str] = None
    timeframe: Optional[str] = None
    entry_rules: Optional[str] = None
    exit_rules: Optional[str] = None
    confirmation_rules: Optional[str] = None
    risk_rules: Optional[str] = None
    invalidation_rules: Optional[str] = None
    trade_management_rules: Optional[str] = None
    notes: Optional[str] = None
    parameters: Optional[dict[str, Any]] = None
    performance_metrics: Optional[dict[str, Any]] = None
    visibility: Optional[str] = PRIVATE_VISIBILITY
    source_request_id: Optional[str] = None
    created_by: Optional[str] = None


class StrategyUpdateIn(BaseModel):
    name: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = None
    strategy_type: Optional[str] = None
    market: Optional[str] = None
    timeframe: Optional[str] = None
    entry_rules: Optional[str] = None
    exit_rules: Optional[str] = None
    confirmation_rules: Optional[str] = None
    risk_rules: Optional[str] = None
    invalidation_rules: Optional[str] = None
    trade_management_rules: Optional[str] = None
    notes: Optional[str] = None
    parameters: Optional[dict[str, Any]] = None
    performance_metrics: Optional[dict[str, Any]] = None
    visibility: Optional[str] = None
    source_request_id: Optional[str] = None


def _clean(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _serialize_dt(value: Any) -> Optional[str]:
    return value.isoformat() if value else None


def _set_or_remove(params: dict[str, Any], key: str, value: Any, *, remove_if_none: bool = True) -> None:
    if value is None and remove_if_none:
        params.pop(key, None)
        return
    params[key] = value


def _normalize_visibility(value: Optional[str], *, default: str = PRIVATE_VISIBILITY) -> str:
    normalized = (value or default).upper()
    if normalized not in VALID_VISIBILITY:
        raise HTTPException(status_code=400, detail="Invalid visibility. Use PUBLIC or PRIVATE")
    return normalized


def _extract_metrics_from_parameters(parameters: Any) -> dict[str, Any]:
    if not isinstance(parameters, dict):
        return {}

    candidates = [
        parameters.get("performance_metrics"),
        parameters.get("metrics"),
        parameters.get("performance"),
        parameters.get("stats"),
        parameters.get("metricSummary"),
        parameters.get("metric_summary"),
    ]
    summary = next((item for item in candidates if isinstance(item, dict)), {})

    return {
        "win_rate": summary.get("winRate") if summary.get("winRate") is not None else summary.get("win_rate"),
        "sharpe_ratio": summary.get("sharpeRatio") if summary.get("sharpeRatio") is not None else summary.get("sharpe_ratio"),
        "max_drawdown": summary.get("maxDrawdown") if summary.get("maxDrawdown") is not None else summary.get("max_drawdown"),
        "total_trades": summary.get("totalTrades") if summary.get("totalTrades") is not None else summary.get("total_trades"),
        "profit_factor": summary.get("profitFactor") if summary.get("profitFactor") is not None else summary.get("profit_factor"),
    }


def _serialize_request(req: StrategyRequest, email: Optional[str] = None, fullname: Optional[str] = None) -> dict[str, Any]:
    return {
        "id": str(req.id),
        "title": req.title,
        "name": req.title,
        "strategy_type": req.strategy_type,
        "strategyType": req.strategy_type,
        "market": req.market,
        "timeframe": req.timeframe,
        "indicators": req.indicators,
        "entry_rules": req.entry_rules,
        "exit_rules": req.exit_rules,
        "risk_rules": req.risk_rules,
        "notes": req.notes,
        "description": req.notes or req.entry_rules,
        "status": req.status,
        "user_id": str(req.user_id),
        "user_email": email,
        "user_name": fullname or email,
        "admin_notes": req.admin_notes,
        "assigned_to": str(req.assigned_to) if getattr(req, "assigned_to", None) else None,
        "deployed_strategy_id": str(req.deployed_strategy_id) if getattr(req, "deployed_strategy_id", None) else None,
        "deployedStrategyId": str(req.deployed_strategy_id) if getattr(req, "deployed_strategy_id", None) else None,
        "created_at": _serialize_dt(req.created_at),
        "createdAt": _serialize_dt(req.created_at),
        "updated_at": _serialize_dt(req.updated_at),
        "updatedAt": _serialize_dt(req.updated_at),
    }


def _serialize_strategy(item: Strategy) -> dict[str, Any]:
    params = item.parameters if isinstance(item.parameters, dict) else {}
    metrics = _extract_metrics_from_parameters(params)
    visibility = getattr(item, "visibility", None) or PRIVATE_VISIBILITY

    return {
        "id": str(item.id),
        "name": item.name,
        "description": item.description,
        "visibility": visibility,
        "status": "PUBLISHED" if visibility == PUBLIC_VISIBILITY else "PRIVATE",
        "strategy_type": params.get("strategy_type"),
        "strategyType": params.get("strategy_type"),
        "market": params.get("market"),
        "timeframe": params.get("timeframe"),
        "entry_rules": params.get("entry_rules"),
        "exit_rules": params.get("exit_rules"),
        "confirmation_rules": params.get("confirmation_rules"),
        "risk_rules": params.get("risk_rules"),
        "invalidation_rules": params.get("invalidation_rules"),
        "trade_management_rules": params.get("trade_management_rules"),
        "notes": params.get("notes"),
        "winRate": _safe_float(metrics.get("win_rate")),
        "sharpeRatio": _safe_float(metrics.get("sharpe_ratio")),
        "maxDrawdown": _safe_float(metrics.get("max_drawdown")),
        "totalTrades": _safe_int(metrics.get("total_trades")),
        "profitFactor": _safe_float(metrics.get("profit_factor")),
        "parameters": params,
        "source_request_id": str(item.source_request_id) if getattr(item, "source_request_id", None) else None,
        "sourceRequestId": str(item.source_request_id) if getattr(item, "source_request_id", None) else None,
        "created_by": str(item.created_by) if getattr(item, "created_by", None) else None,
        "published_by": str(item.published_by) if getattr(item, "published_by", None) else None,
        "created_at": _serialize_dt(item.created_at),
        "createdAt": _serialize_dt(item.created_at),
        "updated_at": _serialize_dt(item.updated_at),
        "updatedAt": _serialize_dt(item.updated_at),
    }


def _apply_payload_to_parameters(params: dict[str, Any], payload: StrategyCreateIn | StrategyUpdateIn) -> dict[str, Any]:
    if payload.parameters is not None:
        params.update(payload.parameters)

    if payload.strategy_type is not None:
        _set_or_remove(params, "strategy_type", _clean(payload.strategy_type))
    if payload.market is not None:
        _set_or_remove(params, "market", _clean(payload.market))
    if payload.timeframe is not None:
        _set_or_remove(params, "timeframe", _clean(payload.timeframe))
    if payload.entry_rules is not None:
        _set_or_remove(params, "entry_rules", _clean(payload.entry_rules))
    if payload.exit_rules is not None:
        _set_or_remove(params, "exit_rules", _clean(payload.exit_rules))
    if payload.confirmation_rules is not None:
        _set_or_remove(params, "confirmation_rules", _clean(payload.confirmation_rules))
    if payload.risk_rules is not None:
        _set_or_remove(params, "risk_rules", _clean(payload.risk_rules))
    if payload.invalidation_rules is not None:
        _set_or_remove(params, "invalidation_rules", _clean(payload.invalidation_rules))
    if payload.trade_management_rules is not None:
        _set_or_remove(params, "trade_management_rules", _clean(payload.trade_management_rules))
    if payload.notes is not None:
        _set_or_remove(params, "notes", _clean(payload.notes))

    if payload.performance_metrics is not None:
        _set_or_remove(params, "performance_metrics", payload.performance_metrics)

    return params


async def _get_request_or_404(db: AsyncSession, request_id: str) -> StrategyRequest:
    req = (
        await db.execute(
            select(StrategyRequest).where(column_text(StrategyRequest.id) == str(request_id))
        )
    ).scalar_one_or_none()

    if not req:
        raise HTTPException(status_code=404, detail="Strategy request not found")
    return req


async def _get_strategy_or_404(db: AsyncSession, strategy_id: str) -> Strategy:
    strategy = (
        await db.execute(
            select(Strategy).where(column_text(Strategy.id) == str(strategy_id))
        )
    ).scalar_one_or_none()

    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return strategy


async def _link_source_request_if_exists(db: AsyncSession, source_request_id: Optional[str], strategy_id: str) -> None:
    if not source_request_id:
        return

    req = (
        await db.execute(
            select(StrategyRequest).where(column_text(StrategyRequest.id) == str(source_request_id))
        )
    ).scalar_one_or_none()

    if req:
        req.deployed_strategy_id = str(strategy_id)
        req.status = "DEPLOYED"


@router.get("")
@router.get("/")
async def list_strategy_requests(
    skip: int = 0,
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    search: Optional[str] = None,
    strategy_search: Optional[str] = None,
    strategy_visibility: Optional[str] = None,
    strategy_source: Optional[str] = Query(default=None, pattern="^(MANUAL|REQUESTED)$"),
    strategy_skip: int = 0,
    strategy_limit: int = Query(100, ge=1, le=200),
    admin_user: dict = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(StrategyRequest, User.email, User.fullname).join(User, User.id == StrategyRequest.user_id)
    count_stmt = select(func.count()).select_from(StrategyRequest).join(User, User.id == StrategyRequest.user_id)

    request_filters = []
    if status:
        request_filters.append(StrategyRequest.status == status)
    if search:
        like = f"%{search.strip()}%"
        request_filters.append(
            or_(
                StrategyRequest.title.ilike(like),
                StrategyRequest.strategy_type.ilike(like),
                StrategyRequest.market.ilike(like),
                User.email.ilike(like),
                User.fullname.ilike(like),
            )
        )

    if request_filters:
        stmt = stmt.where(*request_filters)
        count_stmt = count_stmt.where(*request_filters)

    rows = (
        await db.execute(
            stmt.order_by(StrategyRequest.created_at.desc()).offset(skip).limit(limit)
        )
    ).all()

    total = (await db.execute(count_stmt)).scalar() or 0
    items = [_serialize_request(req, email, fullname) for req, email, fullname in rows]

    strategy_stmt = select(Strategy)
    strategy_count_stmt = select(func.count()).select_from(Strategy)
    strategy_filters = []

    if strategy_search:
        like = f"%{strategy_search.strip()}%"
        strategy_filters.append(
            or_(
                Strategy.name.ilike(like),
                Strategy.description.ilike(like),
                column_text(Strategy.id).ilike(like),
            )
        )

    if strategy_visibility:
        normalized_visibility = _normalize_visibility(strategy_visibility)
        strategy_filters.append(Strategy.visibility == normalized_visibility)

    if strategy_source == "MANUAL":
        strategy_filters.append(Strategy.source_request_id.is_(None))
    elif strategy_source == "REQUESTED":
        strategy_filters.append(Strategy.source_request_id.is_not(None))

    if strategy_filters:
        strategy_stmt = strategy_stmt.where(*strategy_filters)
        strategy_count_stmt = strategy_count_stmt.where(*strategy_filters)

    implemented_rows = (
        await db.execute(
            strategy_stmt.order_by(Strategy.updated_at.desc(), Strategy.created_at.desc()).offset(strategy_skip).limit(strategy_limit)
        )
    ).scalars().all()

    strategy_total = (await db.execute(strategy_count_stmt)).scalar() or 0

    return success_response(
        {
            "items": items,
            "implemented": [_serialize_strategy(item) for item in implemented_rows],
            "total": total,
            "skip": skip,
            "limit": limit,
            "strategy_total": strategy_total,
            "strategy_skip": strategy_skip,
            "strategy_limit": strategy_limit,
        },
        "No data found" if not items and not implemented_rows else None,
    )


@router.get("/strategies")
async def list_strategies(
    skip: int = 0,
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    visibility: Optional[str] = None,
    source: Optional[str] = Query(default=None, pattern="^(MANUAL|REQUESTED)$"),
    admin_user: dict = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Strategy)
    count_stmt = select(func.count()).select_from(Strategy)
    filters = []

    if search:
        like = f"%{search.strip()}%"
        filters.append(
            or_(
                Strategy.name.ilike(like),
                Strategy.description.ilike(like),
                column_text(Strategy.id).ilike(like),
            )
        )

    if visibility:
        filters.append(Strategy.visibility == _normalize_visibility(visibility))

    if source == "MANUAL":
        filters.append(Strategy.source_request_id.is_(None))
    elif source == "REQUESTED":
        filters.append(Strategy.source_request_id.is_not(None))

    if filters:
        stmt = stmt.where(*filters)
        count_stmt = count_stmt.where(*filters)

    rows = (
        await db.execute(
            stmt.order_by(Strategy.updated_at.desc(), Strategy.created_at.desc()).offset(skip).limit(limit)
        )
    ).scalars().all()

    total = (await db.execute(count_stmt)).scalar() or 0

    return success_response(
        {
            "items": [_serialize_strategy(item) for item in rows],
            "total": total,
            "skip": skip,
            "limit": limit,
        },
        "No data found" if not rows else None,
    )


@router.post("/strategies")
async def create_strategy(
    payload: StrategyCreateIn,
    admin_user: dict = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    name = _clean(payload.name)
    if not name:
        raise HTTPException(status_code=400, detail="Strategy name is required")

    visibility = _normalize_visibility(payload.visibility)
    params = _apply_payload_to_parameters(dict(payload.parameters or {}), payload)

    strategy = Strategy(
        id=str(uuid4()),
        name=name,
        description=_clean(payload.description),
        parameters=params,
        visibility=visibility,
        source_request_id=as_uuid_or_str(payload.source_request_id) if payload.source_request_id else None,
        created_by=as_uuid_or_str(payload.created_by) if payload.created_by else as_uuid_or_str(admin_user["user_id"]),
        published_by=as_uuid_or_str(admin_user["user_id"]) if visibility == PUBLIC_VISIBILITY else None,
    )
    db.add(strategy)

    await _link_source_request_if_exists(db, payload.source_request_id, strategy.id)

    await db.commit()
    await db.refresh(strategy)

    return success_response(_serialize_strategy(strategy), "Strategy created successfully")


@router.patch("/strategies/{strategy_id}")
async def update_strategy(
    strategy_id: str,
    payload: StrategyUpdateIn,
    admin_user: dict = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    strategy = await _get_strategy_or_404(db, strategy_id)

    if payload.name is not None:
        name = _clean(payload.name)
        if not name:
            raise HTTPException(status_code=400, detail="Strategy name cannot be empty")
        strategy.name = name

    if payload.description is not None:
        strategy.description = _clean(payload.description)

    params = dict(strategy.parameters or {})
    params = _apply_payload_to_parameters(params, payload)
    strategy.parameters = params

    if payload.visibility is not None:
        strategy.visibility = _normalize_visibility(payload.visibility)

    if strategy.visibility == PUBLIC_VISIBILITY:
        strategy.published_by = as_uuid_or_str(admin_user["user_id"])
    elif payload.visibility is not None:
        strategy.published_by = None

    if payload.source_request_id is not None:
        strategy.source_request_id = as_uuid_or_str(payload.source_request_id) if _clean(payload.source_request_id) else None
        await _link_source_request_if_exists(db, payload.source_request_id, strategy.id)

    await db.commit()
    await db.refresh(strategy)

    return success_response(_serialize_strategy(strategy), "Strategy updated successfully")


@router.delete("/strategies/{strategy_id}")
async def delete_strategy(
    strategy_id: str,
    admin_user: dict = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    strategy = await _get_strategy_or_404(db, strategy_id)

    dependent_requests = (
        await db.execute(
            select(StrategyRequest).where(column_text(StrategyRequest.deployed_strategy_id) == str(strategy.id))
        )
    ).scalars().all()

    for req in dependent_requests:
        req.deployed_strategy_id = None
        if req.status == "DEPLOYED":
            req.status = "UNDER_DEVELOPMENT"

    await db.delete(strategy)
    await db.commit()

    return success_response(
        {
            "id": str(strategy_id),
            "released_request_count": len(dependent_requests),
        },
        "Strategy deleted successfully",
    )


@router.post("/strategies/{strategy_id}/publish")
async def publish_strategy(
    strategy_id: str,
    admin_user: dict = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    strategy = await _get_strategy_or_404(db, strategy_id)
    strategy.visibility = PUBLIC_VISIBILITY
    strategy.published_by = as_uuid_or_str(admin_user["user_id"])

    await db.commit()
    await db.refresh(strategy)

    return success_response(_serialize_strategy(strategy), "Strategy published successfully")


@router.post("/strategies/{strategy_id}/unpublish")
async def unpublish_strategy(
    strategy_id: str,
    admin_user: dict = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    strategy = await _get_strategy_or_404(db, strategy_id)
    strategy.visibility = PRIVATE_VISIBILITY
    strategy.published_by = None

    await db.commit()
    await db.refresh(strategy)

    return success_response(_serialize_strategy(strategy), "Strategy moved to private successfully")


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
            .where(column_text(StrategyRequest.id) == str(request_id))
        )
    ).first()

    if not row:
        raise HTTPException(status_code=404, detail="Strategy request not found")

    req, email, fullname = row
    return success_response(_serialize_request(req, email, fullname))


@router.patch("/{request_id}")
async def update_strategy_request(
    request_id: str,
    payload: StrategyRequestPatchIn,
    admin_user: dict = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    req = await _get_request_or_404(db, request_id)

    status_value = payload.status
    if status_value is not None:
        if status_value not in VALID_REQUEST_STATUSES:
            raise HTTPException(status_code=400, detail="Invalid strategy request status")
        req.status = status_value

    if payload.admin_notes is not None:
        req.admin_notes = _clean(payload.admin_notes)

    if payload.assigned_to is not None:
        req.assigned_to = as_uuid_or_str(payload.assigned_to) if _clean(payload.assigned_to) else None

    if status_value == "DEPLOYED":
        strategy = await _upsert_strategy_from_request(db, req, visibility=PRIVATE_VISIBILITY)
        req.deployed_strategy_id = str(strategy.id)

    await db.commit()
    await db.refresh(req)

    row = (
        await db.execute(
            select(StrategyRequest, User.email, User.fullname)
            .join(User, User.id == StrategyRequest.user_id)
            .where(column_text(StrategyRequest.id) == str(request_id))
        )
    ).first()

    if row:
        req2, email, fullname = row
        return success_response(_serialize_request(req2, email, fullname), "Strategy request updated successfully")

    return success_response(_serialize_request(req), "Strategy request updated successfully")


@router.post("/{request_id}/deploy")
async def deploy_strategy_request(
    request_id: str,
    payload: DeployRequestIn | None = None,
    admin_user: dict = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    req = await _get_request_or_404(db, request_id)
    payload = payload or DeployRequestIn()

    visibility = _normalize_visibility(payload.visibility, default=PRIVATE_VISIBILITY)
    if payload.publish:
        visibility = PUBLIC_VISIBILITY

    if payload.strategy_id:
        strategy = await _get_strategy_or_404(db, payload.strategy_id)
        params = dict(strategy.parameters or {})
        params.update(
            {
                "strategy_type": req.strategy_type,
                "market": req.market,
                "timeframe": req.timeframe,
                "indicators": req.indicators,
                "entry_rules": req.entry_rules,
                "exit_rules": req.exit_rules,
                "risk_rules": req.risk_rules,
                "notes": req.notes,
            }
        )
        strategy.parameters = params
        strategy.source_request_id = as_uuid_or_str(req.id)
        strategy.created_by = as_uuid_or_str(req.user_id)

        if _clean(payload.strategy_name):
            strategy.name = _clean(payload.strategy_name)
        elif not strategy.name:
            strategy.name = req.title

        if payload.strategy_description is not None:
            strategy.description = _clean(payload.strategy_description)
        elif not strategy.description:
            strategy.description = req.notes or req.entry_rules

        strategy.visibility = visibility
        strategy.published_by = as_uuid_or_str(admin_user["user_id"]) if visibility == PUBLIC_VISIBILITY else None
    else:
        strategy = await _upsert_strategy_from_request(
            db,
            req,
            visibility=visibility,
            published_by=admin_user["user_id"] if visibility == PUBLIC_VISIBILITY else None,
        )

        if _clean(payload.strategy_name):
            strategy.name = _clean(payload.strategy_name)
        if payload.strategy_description is not None:
            strategy.description = _clean(payload.strategy_description)

    req.status = "DEPLOYED"
    req.deployed_strategy_id = str(strategy.id)
    if payload.admin_notes is not None:
        req.admin_notes = _clean(payload.admin_notes)

    await db.commit()
    await db.refresh(req)
    await db.refresh(strategy)

    return success_response(
        {"request": _serialize_request(req), "strategy": _serialize_strategy(strategy)},
        "Strategy deployed successfully",
    )


@router.post("/{request_id}/publish")
async def publish_strategy_request(
    request_id: str,
    payload: DeployRequestIn | None = None,
    admin_user: dict = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    merged_payload = payload or DeployRequestIn()
    merged_payload.publish = True
    merged_payload.visibility = PUBLIC_VISIBILITY

    return await deploy_strategy_request(
        request_id=request_id,
        payload=merged_payload,
        admin_user=admin_user,
        db=db,
    )
