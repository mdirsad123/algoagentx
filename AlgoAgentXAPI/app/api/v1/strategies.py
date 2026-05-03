from __future__ import annotations

from typing import Any, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.dependencies import get_admin_user, get_current_user, get_db
from ...db.compat import as_uuid_or_str, column_text, table_has_column
from ...db.models import PerformanceMetric, Strategy, StrategyRequest, StrategyRuntimePreset, User
from ...services.trading.runtime_config_service import (
    get_default_runtime_config_schema,
    get_system_default_runtime_config,
    resolve_runtime_config,
    validate_runtime_config,
)
from ...utils.api_response import success_response

router = APIRouter()

PUBLIC_VISIBILITY = "PUBLIC"
PRIVATE_VISIBILITY = "PRIVATE"
TEMPLATE_USER_EMAIL = "templates@algoagentx.local"
VALID_REQUEST_STATUSES = {"UNDER_DEVELOPMENT", "NEEDS_CLARIFICATION", "REJECTED", "DEPLOYED"}


class StrategyRequestIn(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    strategy_type: Optional[str] = Field(default=None, max_length=255)
    market: Optional[str] = Field(default=None, max_length=255)
    timeframe: Optional[str] = Field(default=None, max_length=255)
    indicators: Optional[dict[str, Any]] = None

    entry_rules: str = Field(..., min_length=3)
    exit_rules: str = Field(..., min_length=3)
    confirmation_rules: Optional[str] = None
    risk_rules: str = Field(..., min_length=3)
    invalidation_rules: Optional[str] = None
    trade_management_rules: Optional[str] = None
    notes: Optional[str] = None


class StrategyAdminUpdateIn(BaseModel):
    status: Optional[str] = None
    admin_notes: Optional[str] = None
    assigned_to: Optional[str] = None


def _safe_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return round(float(value), 2)
    except Exception:
        return None


def _safe_int(value: Any) -> Optional[int]:
    try:
        if value is None:
            return None
        return int(value)
    except Exception:
        return None


def _clean(value: Optional[str]) -> Optional[str]:
    value = (value or "").strip()
    return value or None


def _user_uuid(value: Any) -> Optional[UUID]:
    if value is None:
        return None
    return UUID(str(value))


async def _columns(db: AsyncSession, table_name: str, names: list[str]) -> set[str]:
    found: set[str] = set()
    for name in names:
        if await table_has_column(db, table_name, name):
            found.add(name)
    return found


async def _get_template_user_id(db: AsyncSession):
    result = await db.execute(select(User.id).where(User.email == TEMPLATE_USER_EMAIL).limit(1))
    return result.scalar_one_or_none()


def _extract_metric_from_parameters(parameters: Any) -> dict[str, Any]:
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


async def _strategy_metrics_map(db: AsyncSession, rows: list[Strategy]) -> dict[str, dict[str, Any]]:
    strategy_ids = [str(row.id) for row in rows if row.id]
    if not strategy_ids:
        return {}

    available = await _columns(
        db,
        "performance_metrics",
        [
            "strategy_id",
            "win_rate",
            "sharpe_ratio",
            "max_drawdown",
            "total_trades",
            "profit_factor",
            "initial_capital",
            "final_capital",
            "net_profit",
        ],
    )

    db_metrics: dict[str, dict[str, Any]] = {}

    if "strategy_id" in available:
        select_parts = ["CAST(strategy_id AS TEXT) AS strategy_id"]

        if "win_rate" in available:
            select_parts.append("AVG(win_rate) AS win_rate")
        if "sharpe_ratio" in available:
            select_parts.append("AVG(sharpe_ratio) AS sharpe_ratio")
        if "max_drawdown" in available:
            select_parts.append("AVG(max_drawdown) AS max_drawdown")
        if "total_trades" in available:
            select_parts.append("SUM(total_trades) AS total_trades")
        if "profit_factor" in available:
            select_parts.append("AVG(profit_factor) AS profit_factor")
        elif {"final_capital", "initial_capital"}.issubset(available):
            select_parts.append("AVG(final_capital / NULLIF(initial_capital, 0)) AS profit_factor")
        elif {"net_profit", "initial_capital"}.issubset(available):
            select_parts.append("AVG((initial_capital + net_profit) / NULLIF(initial_capital, 0)) AS profit_factor")

        sql = text(
            f"""
            SELECT {", ".join(select_parts)}
            FROM performance_metrics
            WHERE CAST(strategy_id AS TEXT) = ANY(:strategy_ids)
            GROUP BY CAST(strategy_id AS TEXT)
            """
        )

        try:
            result = await db.execute(sql, {"strategy_ids": strategy_ids})
            for row in result.mappings().all():
                db_metrics[str(row["strategy_id"])] = {
                    "win_rate": _safe_float(row.get("win_rate")),
                    "sharpe_ratio": _safe_float(row.get("sharpe_ratio")),
                    "max_drawdown": _safe_float(row.get("max_drawdown")),
                    "total_trades": _safe_int(row.get("total_trades")),
                    "profit_factor": _safe_float(row.get("profit_factor")),
                }
        except Exception:
            db_metrics = {}

    merged: dict[str, dict[str, Any]] = {}
    for row in rows:
        parameter_metrics = _extract_metric_from_parameters(row.parameters)
        database_metrics = db_metrics.get(str(row.id), {})
        merged[str(row.id)] = {
            "win_rate": database_metrics.get("win_rate") if database_metrics.get("win_rate") is not None else _safe_float(parameter_metrics.get("win_rate")),
            "sharpe_ratio": database_metrics.get("sharpe_ratio") if database_metrics.get("sharpe_ratio") is not None else _safe_float(parameter_metrics.get("sharpe_ratio")),
            "max_drawdown": database_metrics.get("max_drawdown") if database_metrics.get("max_drawdown") is not None else _safe_float(parameter_metrics.get("max_drawdown")),
            "total_trades": database_metrics.get("total_trades") if database_metrics.get("total_trades") is not None else _safe_int(parameter_metrics.get("total_trades")),
            "profit_factor": database_metrics.get("profit_factor") if database_metrics.get("profit_factor") is not None else _safe_float(parameter_metrics.get("profit_factor")),
        }
    return merged


def _visibility_for(row: Strategy, template_user_id: Any = None) -> str:
    visibility = getattr(row, "visibility", None)
    if visibility:
        return visibility
    if row.created_by is None:
        return PUBLIC_VISIBILITY
    if template_user_id is not None and str(row.created_by) == str(template_user_id):
        return PUBLIC_VISIBILITY
    return PRIVATE_VISIBILITY


def _serialize_strategy(
    row: Strategy,
    metrics: Optional[dict[str, Any]] = None,
    template_user_id: Any = None,
    include_visibility: bool = True,
) -> dict[str, Any]:
    metrics = metrics or {}
    params = row.parameters if isinstance(row.parameters, dict) else {}
    creator_name = None

    if getattr(row, "creator", None) is not None:
        creator_name = row.creator.fullname or row.creator.email

    data = {
        "id": str(row.id),
        "name": row.name,
        "description": row.description or "",
        "createdBy": str(row.created_by) if row.created_by else None,
        "creatorName": creator_name,
        "sourceRequestId": str(row.source_request_id) if getattr(row, "source_request_id", None) else None,
        "publishedBy": str(row.published_by) if getattr(row, "published_by", None) else None,
        "strategyType": params.get("strategy_type"),
        "market": params.get("market"),
        "timeframe": params.get("timeframe"),
        "parameters": params,
        "winRate": metrics.get("win_rate"),
        "sharpeRatio": metrics.get("sharpe_ratio"),
        "totalTrades": metrics.get("total_trades"),
        "maxDrawdown": metrics.get("max_drawdown"),
        "profitFactor": metrics.get("profit_factor"),
        "createdAt": row.created_at.isoformat() if row.created_at else None,
        "updatedAt": row.updated_at.isoformat() if getattr(row, "updated_at", None) else None,
        "lastUpdated": row.updated_at.isoformat() if getattr(row, "updated_at", None) else (row.created_at.isoformat() if row.created_at else None),
        "lifecycle_status": getattr(row, "lifecycle_status", None) or "DRAFT",
        "lifecycleStatus": getattr(row, "lifecycle_status", None) or "DRAFT",
        "is_deployable_paper": bool(getattr(row, "is_deployable_paper", False)),
        "isDeployablePaper": bool(getattr(row, "is_deployable_paper", False)),
        "is_deployable_demo": bool(getattr(row, "is_deployable_demo", False)),
        "isDeployableDemo": bool(getattr(row, "is_deployable_demo", False)),
        "is_live_approved": bool(getattr(row, "is_live_approved", False)),
        "isLiveApproved": bool(getattr(row, "is_live_approved", False)),
        "verified_at": row.verified_at.isoformat() if getattr(row, "verified_at", None) else None,
        "verifiedAt": row.verified_at.isoformat() if getattr(row, "verified_at", None) else None,
        "sandbox_passed_at": row.sandbox_passed_at.isoformat() if getattr(row, "sandbox_passed_at", None) else None,
        "sandboxPassedAt": row.sandbox_passed_at.isoformat() if getattr(row, "sandbox_passed_at", None) else None,
    }

    if include_visibility:
        visibility = _visibility_for(row, template_user_id)
        data["visibility"] = visibility
        data["status"] = "PUBLISHED" if visibility == PUBLIC_VISIBILITY else "PRIVATE"

    return data


def _serialize_request(req: StrategyRequest) -> dict[str, Any]:
    return {
        "id": str(req.id),
        "title": req.title,
        "name": req.title,
        "description": req.notes or req.entry_rules,
        "strategy_type": req.strategy_type,
        "strategyType": req.strategy_type,
        "market": req.market,
        "timeframe": req.timeframe,
        "indicators": req.indicators,
        "entry_rules": req.entry_rules,
        "exit_rules": req.exit_rules,
        "risk_rules": req.risk_rules,
        "notes": req.notes,
        "status": req.status,
        "admin_notes": req.admin_notes,
        "assigned_to": str(req.assigned_to) if getattr(req, "assigned_to", None) else None,
        "deployed_strategy_id": str(req.deployed_strategy_id) if getattr(req, "deployed_strategy_id", None) else None,
        "deployedStrategyId": str(req.deployed_strategy_id) if getattr(req, "deployed_strategy_id", None) else None,
        "created_at": req.created_at.isoformat() if req.created_at else None,
        "createdAt": req.created_at.isoformat() if req.created_at else None,
        "updated_at": req.updated_at.isoformat() if req.updated_at else None,
        "updatedAt": req.updated_at.isoformat() if req.updated_at else None,
        "lastUpdated": req.updated_at.isoformat() if req.updated_at else (req.created_at.isoformat() if req.created_at else None),
    }


async def _upsert_strategy_from_request(
    db: AsyncSession,
    req: StrategyRequest,
    *,
    visibility: str = PRIVATE_VISIBILITY,
    published_by: Any = None,
) -> Strategy:
    strategy = (
        await db.execute(
            select(Strategy).where(
                or_(
                    Strategy.source_request_id == req.id,
                    column_text(Strategy.id) == str(req.id),
                )
            )
        )
    ).scalar_one_or_none()

    payload = {
        "name": req.title,
        "description": req.notes or req.entry_rules,
        "parameters": {
            "strategy_type": req.strategy_type,
            "market": req.market,
            "timeframe": req.timeframe,
            "indicators": req.indicators,
            "entry_rules": req.entry_rules,
            "exit_rules": req.exit_rules,
            "risk_rules": req.risk_rules,
            "notes": req.notes,
        },
        "created_by": as_uuid_or_str(req.user_id),
        "visibility": visibility,
        "source_request_id": as_uuid_or_str(req.id),
        "published_by": as_uuid_or_str(published_by) if published_by else None,
    }

    if strategy is None:
        strategy = Strategy(id=str(req.id), **payload)
        db.add(strategy)
    else:
        for key, value in payload.items():
            setattr(strategy, key, value)

    await db.flush()
    return strategy


async def _create_strategy_request_record(
    db: AsyncSession,
    *,
    user_id: UUID,
    title: str,
    strategy_type: Optional[str],
    market: Optional[str],
    timeframe: Optional[str],
    indicators: Optional[dict[str, Any]],
    entry_rules: str,
    exit_rules: str,
    risk_rules: str,
    notes: Optional[str],
) -> StrategyRequest:
    request_id = uuid4()

    has_legacy_strategy_name = await table_has_column(db, "strategy_requests", "strategy_name")
    has_legacy_strategy_description = await table_has_column(db, "strategy_requests", "strategy_description")

    if has_legacy_strategy_name or has_legacy_strategy_description:
        columns = [
            "id",
            "user_id",
            "title",
            "strategy_type",
            "market",
            "timeframe",
            "indicators",
            "entry_rules",
            "exit_rules",
            "risk_rules",
            "notes",
            "status",
        ]

        values: dict[str, Any] = {
            "id": request_id,
            "user_id": user_id,
            "title": title,
            "strategy_type": strategy_type,
            "market": market,
            "timeframe": timeframe,
            "indicators": indicators,
            "entry_rules": entry_rules,
            "exit_rules": exit_rules,
            "risk_rules": risk_rules,
            "notes": notes,
            "status": "UNDER_DEVELOPMENT",
        }

        if has_legacy_strategy_name:
            columns.append("strategy_name")
            values["strategy_name"] = title

        if has_legacy_strategy_description:
            columns.append("strategy_description")
            values["strategy_description"] = notes or entry_rules

        columns_sql = ", ".join(columns)
        values_sql = ", ".join(f":{column}" for column in columns)

        await db.execute(
            text(f"INSERT INTO strategy_requests ({columns_sql}) VALUES ({values_sql})"),
            values,
        )
        await db.commit()

        row = (
            await db.execute(
                select(StrategyRequest).where(column_text(StrategyRequest.id) == str(request_id))
            )
        ).scalar_one()
        return row

    row = StrategyRequest(
        id=request_id,
        user_id=user_id,
        title=title,
        strategy_type=strategy_type,
        market=market,
        timeframe=timeframe,
        indicators=indicators,
        entry_rules=entry_rules,
        exit_rules=exit_rules,
        risk_rules=risk_rules,
        notes=notes,
        status="UNDER_DEVELOPMENT",
    )

    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


@router.get("/")
async def get_strategies(
    approved_only: bool = Query(True),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    stmt = select(Strategy).order_by(Strategy.created_at.desc())

    if approved_only:
        user_id = _user_uuid(current_user["user_id"])
        stmt = stmt.where(or_(Strategy.visibility == PUBLIC_VISIBILITY, Strategy.created_by == user_id))

    rows = (await db.execute(stmt)).scalars().all()
    metrics_map = await _strategy_metrics_map(db, rows)
    template_user_id = await _get_template_user_id(db)

    data = [_serialize_strategy(row, metrics_map.get(str(row.id)), template_user_id) for row in rows]
    return success_response(data, "No data found" if not data else None)


@router.get("/templates")
async def get_strategy_templates(db: AsyncSession = Depends(get_db)):
    template_user_id = await _get_template_user_id(db)

    filters = [Strategy.visibility == PUBLIC_VISIBILITY, Strategy.created_by.is_(None)]
    if template_user_id is not None:
        filters.append(Strategy.created_by == template_user_id)

    rows = (
        await db.execute(
            select(Strategy)
            .where(or_(*filters))
            .order_by(Strategy.created_at.desc())
        )
    ).scalars().all()

    metrics_map = await _strategy_metrics_map(db, rows)
    data = [
        _serialize_strategy(row, metrics_map.get(str(row.id)), template_user_id, include_visibility=False)
        for row in rows
    ]
    return success_response(data, "No data found" if not data else None)


@router.get("/my")
async def get_my_strategies(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_id = _user_uuid(current_user["user_id"])

    strategies = (
        await db.execute(
            select(Strategy)
            .where(Strategy.created_by == user_id)
            .order_by(Strategy.created_at.desc())
        )
    ).scalars().all()

    metrics_map = await _strategy_metrics_map(db, strategies)
    template_user_id = await _get_template_user_id(db)

    strategy_items = [
        _serialize_strategy(row, metrics_map.get(str(row.id)), template_user_id)
        for row in strategies
    ]

    requests = (
        await db.execute(
            select(StrategyRequest)
            .where(StrategyRequest.user_id == user_id)
            .order_by(StrategyRequest.created_at.desc())
        )
    ).scalars().all()

    request_items = [_serialize_request(req) for req in requests]

    return success_response(
        {"strategies": strategy_items, "requests": request_items},
        "No data found" if not strategy_items and not request_items else None,
    )


@router.get("/my/requests")
async def get_my_strategy_requests(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_id = _user_uuid(current_user["user_id"])
    rows = (
        await db.execute(
            select(StrategyRequest)
            .where(StrategyRequest.user_id == user_id)
            .order_by(StrategyRequest.created_at.desc())
        )
    ).scalars().all()

    data = [_serialize_request(req) for req in rows]
    return success_response(data, "No requests found" if not data else None)


@router.post("/request", status_code=status.HTTP_201_CREATED)
async def request_strategy(
    payload: StrategyRequestIn,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    notes_parts: list[str] = []

    if _clean(payload.confirmation_rules):
        notes_parts.append(f"Confirmation Rules:\n{payload.confirmation_rules.strip()}")
    if _clean(payload.invalidation_rules):
        notes_parts.append(f"Invalidation Rules:\n{payload.invalidation_rules.strip()}")
    if _clean(payload.trade_management_rules):
        notes_parts.append(f"Trade Management Rules:\n{payload.trade_management_rules.strip()}")
    if _clean(payload.notes):
        notes_parts.append(f"Additional Notes:\n{payload.notes.strip()}")

    combined_notes = "\n\n".join(notes_parts) if notes_parts else None

    row = await _create_strategy_request_record(
        db,
        user_id=_user_uuid(current_user["user_id"]),
        title=payload.title.strip(),
        strategy_type=_clean(payload.strategy_type),
        market=_clean(payload.market),
        timeframe=_clean(payload.timeframe),
        indicators=payload.indicators or None,
        entry_rules=payload.entry_rules.strip(),
        exit_rules=payload.exit_rules.strip(),
        risk_rules=payload.risk_rules.strip(),
        notes=combined_notes,
    )

    return success_response(_serialize_request(row), "Strategy request submitted successfully")


@router.get("/admin")
async def get_admin_strategies(
    skip: int = 0,
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_admin_user),
):
    stmt = select(StrategyRequest, User.email, User.fullname).join(User, User.id == StrategyRequest.user_id)
    count_stmt = select(func.count()).select_from(StrategyRequest).join(User, User.id == StrategyRequest.user_id)

    filters = []
    if search:
        like = f"%{search}%"
        filters.append(
            or_(
                StrategyRequest.title.ilike(like),
                StrategyRequest.strategy_type.ilike(like),
                StrategyRequest.market.ilike(like),
                User.email.ilike(like),
                User.fullname.ilike(like),
            )
        )
    if status_filter:
        filters.append(StrategyRequest.status == status_filter)

    if filters:
        stmt = stmt.where(*filters)
        count_stmt = count_stmt.where(*filters)

    rows = (
        await db.execute(
            stmt.order_by(StrategyRequest.created_at.desc()).offset(skip).limit(limit)
        )
    ).all()

    total = (await db.execute(count_stmt)).scalar() or 0

    data = [
        {
            **_serialize_request(req),
            "user_id": str(req.user_id),
            "user_email": email,
            "user_name": fullname or email,
            "description": req.notes or req.entry_rules,
        }
        for req, email, fullname in rows
    ]

    return success_response(
        {"items": data, "total": total, "skip": skip, "limit": limit},
        "No data found" if not data else None,
    )


@router.patch("/admin/{request_id}")
async def update_admin_strategy(
    request_id: str,
    payload: StrategyAdminUpdateIn,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_admin_user),
):
    req = (
        await db.execute(
            select(StrategyRequest).where(column_text(StrategyRequest.id) == str(request_id))
        )
    ).scalar_one_or_none()

    if not req:
        raise HTTPException(status_code=404, detail="Strategy request not found")

    if payload.status:
        if payload.status not in VALID_REQUEST_STATUSES:
            raise HTTPException(status_code=400, detail="Invalid strategy request status")
        req.status = payload.status

    if payload.admin_notes is not None:
        req.admin_notes = payload.admin_notes

    if payload.assigned_to is not None:
        req.assigned_to = as_uuid_or_str(payload.assigned_to) if payload.assigned_to else None

    if payload.status == "DEPLOYED":
        strategy = await _upsert_strategy_from_request(db, req, visibility=PRIVATE_VISIBILITY)
        req.deployed_strategy_id = str(strategy.id)

    await db.commit()
    await db.refresh(req)

    return success_response(_serialize_request(req), "Strategy updated successfully")


@router.post("/admin/{request_id}/publish")
async def publish_strategy(
    request_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_admin_user),
):
    req = (
        await db.execute(
            select(StrategyRequest).where(column_text(StrategyRequest.id) == str(request_id))
        )
    ).scalar_one_or_none()

    if not req:
        raise HTTPException(status_code=404, detail="Strategy request not found")

    strategy = await _upsert_strategy_from_request(
        db,
        req,
        visibility=PUBLIC_VISIBILITY,
        published_by=current_user["user_id"],
    )

    req.status = "DEPLOYED"
    req.deployed_strategy_id = str(strategy.id)

    await db.commit()
    await db.refresh(req)

    return success_response(
        {
            "request": _serialize_request(req),
            "strategy": _serialize_strategy(strategy, include_visibility=True),
        },
        "Strategy published successfully",
    )

def _serialize_runtime_preset(row: StrategyRuntimePreset) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "strategy_id": str(row.strategy_id),
        "strategyId": str(row.strategy_id),
        "name": row.name,
        "description": row.description,
        "config_json": row.config_json or {},
        "configJson": row.config_json or {},
        "risk_label": getattr(row, "risk_label", None),
        "riskLabel": getattr(row, "risk_label", None),
        "is_default": bool(row.is_default),
        "isDefault": bool(row.is_default),
        "is_active": bool(row.is_active),
        "isActive": bool(row.is_active),
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "createdAt": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        "updatedAt": row.updated_at.isoformat() if row.updated_at else None,
    }


@router.get("/{strategy_id}/runtime-config")
async def get_strategy_runtime_config(
    strategy_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    strategy = (
        await db.execute(select(Strategy).where(column_text(Strategy.id) == str(strategy_id)))
    ).scalar_one_or_none()

    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    presets = (
        await db.execute(
            select(StrategyRuntimePreset)
            .where(
                StrategyRuntimePreset.strategy_id == str(strategy_id),
                StrategyRuntimePreset.is_active == True,
            )
            .order_by(StrategyRuntimePreset.is_default.desc(), StrategyRuntimePreset.created_at.asc())
        )
    ).scalars().all()

    strategy_hint = " ".join(
        str(part or "")
        for part in [
            strategy.name,
            (strategy.parameters or {}).get("strategy_type") if isinstance(strategy.parameters, dict) else None,
        ]
    )

    default_runtime_config = strategy.default_runtime_config or get_system_default_runtime_config()
    runtime_config_schema = strategy.runtime_config_schema or get_default_runtime_config_schema(strategy_hint)
    default_preset = next((row for row in presets if bool(row.is_default)), None)
    resolved_defaults = resolve_runtime_config(strategy=strategy, strategy_preset=default_preset)
    validation = validate_runtime_config(resolved_defaults)

    return success_response(
        {
            "strategy_id": str(strategy.id),
            "strategyId": str(strategy.id),
            "strategy_name": strategy.name,
            "strategyName": strategy.name,
            "supports_runtime_config": bool(getattr(strategy, "supports_runtime_config", True)),
            "supportsRuntimeConfig": bool(getattr(strategy, "supports_runtime_config", True)),
            "config_version": int(getattr(strategy, "config_version", 1) or 1),
            "configVersion": int(getattr(strategy, "config_version", 1) or 1),
            "system_default_runtime_config": get_system_default_runtime_config(),
            "systemDefaultRuntimeConfig": get_system_default_runtime_config(),
            "default_runtime_config": default_runtime_config,
            "defaultRuntimeConfig": default_runtime_config,
            "runtime_config_schema": runtime_config_schema,
            "runtimeConfigSchema": runtime_config_schema,
            "presets": [_serialize_runtime_preset(row) for row in presets],
            "resolved_defaults": resolved_defaults,
            "resolvedDefaults": resolved_defaults,
            "validation": validation,
        },
        "Strategy runtime config loaded",
    )

@router.get("/{strategy_id}/runtime-presets")
async def get_strategy_runtime_presets(
    strategy_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    strategy = (await db.execute(select(Strategy).where(column_text(Strategy.id) == str(strategy_id)))).scalar_one_or_none()
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    rows = (
        await db.execute(
            select(StrategyRuntimePreset)
            .where(StrategyRuntimePreset.strategy_id == str(strategy_id), StrategyRuntimePreset.is_active == True)
            .order_by(StrategyRuntimePreset.is_default.desc(), StrategyRuntimePreset.created_at.asc())
        )
    ).scalars().all()
    return success_response({"items": [_serialize_runtime_preset(row) for row in rows]}, "Runtime presets loaded")

