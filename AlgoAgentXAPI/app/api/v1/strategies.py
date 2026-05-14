from __future__ import annotations

from typing import Any, Optional
from uuid import UUID, uuid4
from datetime import datetime, timezone
import json
from pathlib import Path
from shutil import copyfileobj

from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.dependencies import get_admin_user, get_current_user, get_db
from ...db.compat import as_uuid_or_str, column_text, table_has_column
from ...db.models import PerformanceMetric, Strategy, StrategyRequest, StrategyRequestAttachment, StrategyRuntimePreset, StrategyAsset, User
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
VALID_REQUEST_STATUSES = {"DRAFT", "PENDING", "SUBMITTED", "UNDER_REVIEW", "UNDER_DEVELOPMENT", "NEEDS_CLARIFICATION", "REJECTED", "DEPLOYED", "PUBLISHED", "CANCELLED", "ARCHIVED"}

PROJECT_ROOT = Path(__file__).resolve().parents[3]
UPLOAD_ROOT = PROJECT_ROOT / "uploads" / "strategy_requests"
STRATEGY_ASSET_ROOT = PROJECT_ROOT / "uploads" / "strategy_assets"
ALLOWED_ATTACHMENT_TYPES = {"image/png", "image/jpeg", "image/webp"}
MAX_ATTACHMENT_SIZE = 5 * 1024 * 1024
MIN_ATTACHMENTS = 2
MAX_ATTACHMENTS = 6


def _jsonb_text_param(value: Any) -> Optional[str]:
    """Return a JSON string suitable for CAST(:param AS jsonb) in raw SQL inserts.

    Some local asyncpg/SQLAlchemy combinations expect JSONB bind values to be
    pre-serialized when SQL is built with sqlalchemy.text(). Passing a dict can
    raise: dict object has no attribute encode.
    """
    if value is None or value == "":
        return None
    if isinstance(value, str):
        try:
            json.loads(value)
            return value
        except Exception:
            return json.dumps(value)
    return json.dumps(value)


def _attachment_url(request_id: Any, attachment_id: Any) -> str:
    return f"/api/v1/strategies/requests/{request_id}/attachments/{attachment_id}"


def _asset_url(strategy_id: Any, asset_id: Any) -> str:
    return f"/api/v1/strategies/{strategy_id}/assets/{asset_id}"


def _serialize_strategy_asset(asset: StrategyAsset) -> dict[str, Any]:
    return {
        "id": str(asset.id),
        "strategy_id": str(asset.strategy_id),
        "strategyId": str(asset.strategy_id),
        "file_name": asset.file_name,
        "fileName": asset.file_name,
        "original_name": asset.original_name,
        "originalName": asset.original_name,
        "public_url": asset.public_url or _asset_url(asset.strategy_id, asset.id),
        "publicUrl": asset.public_url or _asset_url(asset.strategy_id, asset.id),
        "mime_type": asset.mime_type,
        "mimeType": asset.mime_type,
        "size_bytes": asset.size_bytes,
        "sizeBytes": asset.size_bytes,
        "sort_order": asset.sort_order,
        "sortOrder": asset.sort_order,
        "is_public": bool(asset.is_public),
        "isPublic": bool(asset.is_public),
        "created_at": asset.created_at.isoformat() if asset.created_at else None,
        "createdAt": asset.created_at.isoformat() if asset.created_at else None,
    }


async def _load_strategy_assets(db: AsyncSession, strategy_ids: list[Any], public_only: bool = False) -> dict[str, list[dict[str, Any]]]:
    ids = [str(x) for x in strategy_ids if x]
    if not ids:
        return {}
    try:
        stmt = select(StrategyAsset).where(StrategyAsset.strategy_id.in_(ids))
        if public_only:
            stmt = stmt.where(StrategyAsset.is_public == True)
        rows = (await db.execute(stmt.order_by(StrategyAsset.sort_order.asc(), StrategyAsset.created_at.asc()))).scalars().all()
    except Exception:
        return {}
    out: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        out.setdefault(str(row.strategy_id), []).append(_serialize_strategy_asset(row))
    return out


def _resolve_asset_file_path(stored_path: str | None) -> Optional[Path]:
    if not stored_path:
        return None
    raw = Path(stored_path)
    candidates = []
    if raw.is_absolute():
        candidates.append(raw)
    else:
        candidates.append(Path.cwd() / raw)
        candidates.append(PROJECT_ROOT / raw)
        candidates.append(PROJECT_ROOT / "uploads" / "strategy_assets" / raw.name)
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except Exception:
            resolved = candidate
        if resolved.exists() and resolved.is_file():
            return resolved
    return None


def _resolve_attachment_file_path(stored_path: str | None) -> Optional[Path]:
    if not stored_path:
        return None
    raw = Path(stored_path)
    candidates = []
    if raw.is_absolute():
        candidates.append(raw)
    else:
        candidates.append(Path.cwd() / raw)
        candidates.append(PROJECT_ROOT / raw)
        candidates.append(PROJECT_ROOT / "uploads" / "strategy_requests" / raw.name)
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except Exception:
            resolved = candidate
        if resolved.exists() and resolved.is_file():
            return resolved
    return None


def _serialize_attachment(item: StrategyRequestAttachment) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "request_id": str(item.request_id),
        "requestId": str(item.request_id),
        "file_name": item.file_name,
        "fileName": item.file_name,
        "original_name": item.original_name,
        "originalName": item.original_name,
        "public_url": item.public_url or _attachment_url(item.request_id, item.id),
        "publicUrl": item.public_url or _attachment_url(item.request_id, item.id),
        "mime_type": item.mime_type,
        "mimeType": item.mime_type,
        "size_bytes": item.size_bytes,
        "sizeBytes": item.size_bytes,
        "sort_order": item.sort_order,
        "sortOrder": item.sort_order,
        "created_at": item.created_at.isoformat() if item.created_at else None,
        "createdAt": item.created_at.isoformat() if item.created_at else None,
    }


def _request_extra(req: StrategyRequest, field: str) -> Optional[str]:
    return getattr(req, field, None)


async def _load_request_attachments(db: AsyncSession, request_ids: list[Any]) -> dict[str, list[dict[str, Any]]]:
    ids = [str(x) for x in request_ids if x]
    if not ids:
        return {}
    try:
        rows = (await db.execute(
            select(StrategyRequestAttachment)
            .where(column_text(StrategyRequestAttachment.request_id).in_(ids))
            .order_by(StrategyRequestAttachment.sort_order.asc(), StrategyRequestAttachment.created_at.asc())
        )).scalars().all()
    except Exception:
        return {}
    out: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        out.setdefault(str(row.request_id), []).append(_serialize_attachment(row))
    return out


async def _save_strategy_request_attachments(db: AsyncSession, req: StrategyRequest, files: list[UploadFile]) -> None:
    if not files:
        return
    target_dir = UPLOAD_ROOT / str(req.id)
    target_dir.mkdir(parents=True, exist_ok=True)
    for idx, upload in enumerate(files):
        if upload.content_type not in ALLOWED_ATTACHMENT_TYPES:
            raise HTTPException(status_code=400, detail="Only PNG, JPEG, or WEBP screenshots are allowed")
        original = Path(upload.filename or f"screenshot-{idx + 1}").name
        safe_name = f"{idx + 1:02d}_{uuid4().hex}_{original}"[:240]
        path = target_dir / safe_name
        size = 0
        with path.open("wb") as buffer:
            while True:
                chunk = await upload.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_ATTACHMENT_SIZE:
                    path.unlink(missing_ok=True)
                    raise HTTPException(status_code=400, detail="Each screenshot must be 5 MB or smaller")
                buffer.write(chunk)
        db.add(StrategyRequestAttachment(
            request_id=req.id,
            user_id=req.user_id,
            file_name=safe_name,
            original_name=original,
            file_path=str(path.relative_to(PROJECT_ROOT) if path.is_absolute() else path),
            public_url=None,
            mime_type=upload.content_type or "application/octet-stream",
            size_bytes=size,
            sort_order=idx,
        ))
    await db.flush()



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




def _is_user_visible_strategy(row: Strategy, user_id: Any) -> bool:
    visibility = (getattr(row, "visibility", None) or PRIVATE_VISIBILITY).upper()
    if visibility == PUBLIC_VISIBILITY:
        return True
    if str(getattr(row, "created_by", "")) != str(user_id):
        return False
    # Request-linked strategies stay hidden while admin is developing them.
    if getattr(row, "source_request_id", None):
        lifecycle = str(getattr(row, "lifecycle_status", "") or "").upper()
        return lifecycle in {"PRIVATE_DEPLOYED", "PUBLISHED", "LIVE_APPROVED", "PRIVATE"}
    return True



READY_BACKTEST_LIFECYCLES = {"PUBLISHED", "DEPLOYED", "BACKTEST_READY", "LIVE_APPROVED", "PRIVATE_DEPLOYED", "PRIVATE"}
BLOCKED_BACKTEST_LIFECYCLES = {"UNDER_DEVELOPMENT", "DRAFT", "WORKSPACE_CREATED", "NEEDS_CLARIFICATION", "SUBMITTED", "UNDER_REVIEW", "REJECTED", "ARCHIVED", "CANCELLED"}
READY_REQUEST_STATUSES = {"DEPLOYED", "PUBLISHED"}
BLOCKED_REQUEST_STATUSES = {"UNDER_DEVELOPMENT", "DRAFT", "WORKSPACE_CREATED", "NEEDS_CLARIFICATION", "SUBMITTED", "UNDER_REVIEW", "REJECTED", "ARCHIVED", "CANCELLED", "PENDING"}


def _strategy_has_backtest_code(row: Strategy) -> bool:
    params = row.parameters if isinstance(row.parameters, dict) else {}
    # Dynamic strategies use source_code. Older/static strategies may not store code,
    # but are still resolvable by the backtest engine when they are deployed/published.
    return bool(str(params.get("source_code") or "").strip() or params.get("code_attached") or params.get("codeAttached") or params.get("engine_mode") != "DYNAMIC_DB")


def _is_backtest_eligible_strategy(row: Strategy, user_id: Any, request_status_by_id: dict[str, str] | None = None) -> bool:
    visibility = (getattr(row, "visibility", None) or PRIVATE_VISIBILITY).upper()
    lifecycle = str(getattr(row, "lifecycle_status", "") or "").upper()
    source_request_id = getattr(row, "source_request_id", None)
    request_status = str((request_status_by_id or {}).get(str(source_request_id), "") or "").upper()

    if not _strategy_has_backtest_code(row):
        return False
    if lifecycle in BLOCKED_BACKTEST_LIFECYCLES or request_status in BLOCKED_REQUEST_STATUSES:
        return False

    if visibility == PUBLIC_VISIBILITY:
        return lifecycle in READY_BACKTEST_LIFECYCLES or not lifecycle

    if visibility == PRIVATE_VISIBILITY and str(getattr(row, "created_by", "")) == str(user_id):
        return lifecycle in READY_BACKTEST_LIFECYCLES or request_status in READY_REQUEST_STATUSES

    return False


async def _request_status_map_for_strategies(db: AsyncSession, rows: list[Strategy]) -> dict[str, str]:
    request_ids = [getattr(row, "source_request_id", None) for row in rows if getattr(row, "source_request_id", None)]
    if not request_ids:
        return {}
    try:
        req_rows = (await db.execute(select(StrategyRequest.id, StrategyRequest.status).where(StrategyRequest.id.in_(request_ids)))).all()
        return {str(req_id): str(status or "").upper() for req_id, status in req_rows}
    except Exception:
        return {}

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


def _serialize_request(req: StrategyRequest, attachments: Optional[list[dict[str, Any]]] = None) -> dict[str, Any]:
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
        "confirmation_rules": _request_extra(req, "confirmation_rules"),
        "invalidation_rules": _request_extra(req, "invalidation_rules"),
        "trade_management_rules": _request_extra(req, "trade_management_rules"),
        "notes": req.notes,
        "user_update_notes": getattr(req, "user_update_notes", None),
        "userUpdateNotes": getattr(req, "user_update_notes", None),
        "clarification_reply": getattr(req, "user_update_notes", None),
        "clarificationReply": getattr(req, "user_update_notes", None),
        "clarification_submitted_at": getattr(req, "clarification_submitted_at", None).isoformat() if getattr(req, "clarification_submitted_at", None) else None,
        "clarificationSubmittedAt": getattr(req, "clarification_submitted_at", None).isoformat() if getattr(req, "clarification_submitted_at", None) else None,
        "last_user_update_at": getattr(req, "last_user_update_at", None).isoformat() if getattr(req, "last_user_update_at", None) else None,
        "lastUserUpdateAt": getattr(req, "last_user_update_at", None).isoformat() if getattr(req, "last_user_update_at", None) else None,
        "parent_strategy_id": str(getattr(req, "parent_strategy_id", None)) if getattr(req, "parent_strategy_id", None) else None,
        "parentStrategyId": str(getattr(req, "parent_strategy_id", None)) if getattr(req, "parent_strategy_id", None) else None,
        "parent_request_id": str(getattr(req, "parent_request_id", None)) if getattr(req, "parent_request_id", None) else None,
        "parentRequestId": str(getattr(req, "parent_request_id", None)) if getattr(req, "parent_request_id", None) else None,
        "request_kind": getattr(req, "request_kind", None) or "NEW",
        "requestKind": getattr(req, "request_kind", None) or "NEW",
        "refinement_notes": getattr(req, "refinement_notes", None),
        "refinementNotes": getattr(req, "refinement_notes", None),
        "attachments": attachments or [],
        "attachment_count": len(attachments or []),
        "attachmentCount": len(attachments or []),
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
            "confirmation_rules": _request_extra(req, "confirmation_rules"),
            "invalidation_rules": _request_extra(req, "invalidation_rules"),
            "trade_management_rules": _request_extra(req, "trade_management_rules"),
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
    confirmation_rules: Optional[str] = None,
    invalidation_rules: Optional[str] = None,
    trade_management_rules: Optional[str] = None,
    notes: Optional[str] = None,
    parent_strategy_id: Optional[Any] = None,
    parent_request_id: Optional[Any] = None,
    request_kind: str = "NEW",
    refinement_notes: Optional[str] = None,
    user_update_notes: Optional[str] = None,
) -> StrategyRequest:
    request_id = uuid4()

    has_legacy_strategy_name = await table_has_column(db, "strategy_requests", "strategy_name")
    has_legacy_strategy_description = await table_has_column(db, "strategy_requests", "strategy_description")
    has_refinement_notes = await table_has_column(db, "strategy_requests", "refinement_notes")

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
            "confirmation_rules",
            "invalidation_rules",
            "trade_management_rules",
            "notes",
            "user_update_notes",
            "parent_strategy_id",
            "parent_request_id",
            "request_kind",
            "status",
        ]

        values: dict[str, Any] = {
            "id": request_id,
            "user_id": user_id,
            "title": title,
            "strategy_type": strategy_type,
            "market": market,
            "timeframe": timeframe,
            "indicators": _jsonb_text_param(indicators),
            "entry_rules": entry_rules,
            "exit_rules": exit_rules,
            "risk_rules": risk_rules,
            "confirmation_rules": confirmation_rules,
            "invalidation_rules": invalidation_rules,
            "trade_management_rules": trade_management_rules,
            "notes": notes,
            "user_update_notes": user_update_notes,
            "parent_strategy_id": parent_strategy_id,
            "parent_request_id": parent_request_id,
            "request_kind": request_kind,
            "status": "SUBMITTED",
        }

        if has_refinement_notes:
            columns.append("refinement_notes")
            values["refinement_notes"] = refinement_notes

        if has_legacy_strategy_name:
            columns.append("strategy_name")
            values["strategy_name"] = title

        if has_legacy_strategy_description:
            columns.append("strategy_description")
            values["strategy_description"] = notes or entry_rules

        columns_sql = ", ".join(columns)
        values_sql = ", ".join("CAST(:indicators AS jsonb)" if column == "indicators" else f":{column}" for column in columns)

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
        confirmation_rules=confirmation_rules,
        invalidation_rules=invalidation_rules,
        trade_management_rules=trade_management_rules,
        notes=notes,
        user_update_notes=user_update_notes,
        parent_strategy_id=str(parent_strategy_id) if parent_strategy_id else None,
        parent_request_id=as_uuid_or_str(parent_request_id) if parent_request_id else None,
        request_kind=request_kind,
        refinement_notes=refinement_notes,
        status="SUBMITTED",
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
    if approved_only:
        rows = [row for row in rows if _is_user_visible_strategy(row, user_id)]
    metrics_map = await _strategy_metrics_map(db, rows)
    template_user_id = await _get_template_user_id(db)

    data = [_serialize_strategy(row, metrics_map.get(str(row.id)), template_user_id) for row in rows]
    return success_response(data, "No data found" if not data else None)


@router.get("/backtest-eligible")
async def get_backtest_eligible_strategies(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_id = _user_uuid(current_user["user_id"])
    rows = (
        await db.execute(
            select(Strategy)
            .where(or_(Strategy.visibility == PUBLIC_VISIBILITY, Strategy.created_by == user_id))
            .order_by(Strategy.created_at.desc())
        )
    ).scalars().all()
    request_status_by_id = await _request_status_map_for_strategies(db, rows)
    rows = [row for row in rows if _is_backtest_eligible_strategy(row, user_id, request_status_by_id)]
    metrics_map = await _strategy_metrics_map(db, rows)
    template_user_id = await _get_template_user_id(db)
    data = [_serialize_strategy(row, metrics_map.get(str(row.id)), template_user_id) for row in rows]
    return success_response(data, "No backtest-ready strategies found" if not data else None)


@router.get("/templates")
async def get_strategy_templates(db: AsyncSession = Depends(get_db)):
    template_user_id = await _get_template_user_id(db)

    rows = (
        await db.execute(
            select(Strategy)
            .where(Strategy.visibility == PUBLIC_VISIBILITY)
            .order_by(Strategy.created_at.desc())
        )
    ).scalars().all()

    metrics_map = await _strategy_metrics_map(db, rows)
    data = [
        _serialize_strategy(row, metrics_map.get(str(row.id)), template_user_id, include_visibility=True)
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
    strategies = [row for row in strategies if _is_user_visible_strategy(row, user_id)]

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

    attachment_map = await _load_request_attachments(db, [req.id for req in requests])
    request_items = [_serialize_request(req, attachment_map.get(str(req.id), [])) for req in requests]

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

    attachment_map = await _load_request_attachments(db, [req.id for req in rows])
    data = [_serialize_request(req, attachment_map.get(str(req.id), [])) for req in rows]
    return success_response(data, "No requests found" if not data else None)


@router.post("/request", status_code=status.HTTP_201_CREATED)
async def request_strategy(
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    content_type = request.headers.get("content-type", "")
    files: list[UploadFile] = []
    if "multipart/form-data" in content_type:
        form = await request.form()
        def text_value(name: str) -> Optional[str]:
            value = form.get(name)
            return str(value).strip() if value is not None and str(value).strip() else None
        raw_indicators = text_value("indicators")
        try:
            indicators = json.loads(raw_indicators) if raw_indicators else None
        except Exception:
            indicators = None
        files = [v for k, v in form.multi_items() if k in {"attachments", "attachments[]", "files"} and hasattr(v, "filename") and hasattr(v, "read")]
        if len(files) < MIN_ATTACHMENTS:
            raise HTTPException(status_code=400, detail="Upload at least 2 chart screenshots")
        if len(files) > MAX_ATTACHMENTS:
            raise HTTPException(status_code=400, detail="Upload maximum 6 chart screenshots")
        payload = StrategyRequestIn(
            title=text_value("title") or "",
            strategy_type=text_value("strategy_type"),
            market=text_value("market"),
            timeframe=text_value("timeframe"),
            indicators=indicators,
            entry_rules=text_value("entry_rules") or "",
            exit_rules=text_value("exit_rules") or "",
            confirmation_rules=text_value("confirmation_rules"),
            risk_rules=text_value("risk_rules") or "",
            invalidation_rules=text_value("invalidation_rules"),
            trade_management_rules=text_value("trade_management_rules"),
            notes=text_value("notes"),
        )
    else:
        payload = StrategyRequestIn.model_validate(await request.json())

    notes_parts: list[str] = []
    if _clean(payload.notes):
        notes_parts.append(payload.notes.strip())
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
        confirmation_rules=_clean(payload.confirmation_rules),
        risk_rules=payload.risk_rules.strip(),
        invalidation_rules=_clean(payload.invalidation_rules),
        trade_management_rules=_clean(payload.trade_management_rules),
        notes=combined_notes,
    )
    await _save_strategy_request_attachments(db, row, files)
    await db.commit()
    await db.refresh(row)
    attachment_map = await _load_request_attachments(db, [row.id])
    return success_response(_serialize_request(row, attachment_map.get(str(row.id), [])), "Strategy request submitted successfully")


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




EDITABLE_REQUEST_STATUSES = {"DRAFT", "PENDING", "SUBMITTED", "UNDER_REVIEW", "NEEDS_CLARIFICATION"}
LOCKED_REQUEST_STATUSES = {"DEPLOYED", "PUBLISHED", "REJECTED", "CANCELLED", "ARCHIVED"}


def _normalize_request_status(value: Any) -> str:
    raw = str(value or "").strip().upper().replace(" ", "_").replace("-", "_")
    aliases = {
        "PENDING_REVIEW": "PENDING",
        "UNDER_REVIEW": "UNDER_REVIEW",
        "NEEDS_CLARIFICATION": "NEEDS_CLARIFICATION",
        "UNDER_DEVELOPMENT": "UNDER_DEVELOPMENT",
        "DEPLOYED": "DEPLOYED",
        "PUBLISHED": "PUBLISHED",
        "REJECTED": "REJECTED",
        "CANCELLED": "CANCELLED",
        "ARCHIVED": "ARCHIVED",
        "DRAFT": "DRAFT",
        "SUBMITTED": "SUBMITTED",
    }
    return aliases.get(raw, raw or "SUBMITTED")


def _form_text(form: Any, name: str) -> Optional[str]:
    value = form.get(name)
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


async def _get_user_request_or_404(db: AsyncSession, request_id: str, current_user: dict) -> StrategyRequest:
    req = (await db.execute(select(StrategyRequest).where(column_text(StrategyRequest.id) == str(request_id)))).scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Strategy request not found")
    is_admin = str(current_user.get("role", "")).upper() == "ADMIN"
    if not is_admin and str(req.user_id) != str(current_user.get("user_id")):
        raise HTTPException(status_code=404, detail="Strategy request not found")
    return req


@router.get("/requests/{request_id}")
async def get_user_strategy_request_detail(
    request_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    req = await _get_user_request_or_404(db, request_id, current_user)
    attachment_map = await _load_request_attachments(db, [req.id])
    return success_response(_serialize_request(req, attachment_map.get(str(req.id), [])), "Strategy request loaded")


@router.patch("/requests/{request_id}")
async def update_user_strategy_request(
    request_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    req = await _get_user_request_or_404(db, request_id, current_user)
    status_value = _normalize_request_status(req.status)
    if status_value in LOCKED_REQUEST_STATUSES or status_value not in EDITABLE_REQUEST_STATUSES:
        raise HTTPException(status_code=400, detail="This request can no longer be edited. Please create a refinement request.")

    form = await request.form()
    files = [v for k, v in form.multi_items() if k in {"attachments", "attachments[]", "files"} and hasattr(v, "filename") and hasattr(v, "read")]
    existing_count = (await db.execute(select(func.count()).select_from(StrategyRequestAttachment).where(StrategyRequestAttachment.request_id == req.id))).scalar() or 0
    if int(existing_count) + len(files) > MAX_ATTACHMENTS:
        raise HTTPException(status_code=400, detail="Maximum 6 screenshots are allowed per request")

    for field in ["title", "strategy_type", "market", "timeframe", "entry_rules", "exit_rules", "confirmation_rules", "risk_rules", "invalidation_rules", "trade_management_rules", "notes"]:
        value = _form_text(form, field)
        if value is not None:
            setattr(req, field, value)

    raw_indicators = _form_text(form, "indicators")
    if raw_indicators:
        try:
            req.indicators = json.loads(raw_indicators)
        except Exception:
            pass

    reply = _form_text(form, "clarification_reply") or _form_text(form, "user_update_notes")
    if reply:
        req.user_update_notes = reply

    now = datetime.now(timezone.utc)
    req.last_user_update_at = now
    if status_value == "NEEDS_CLARIFICATION":
        req.clarification_submitted_at = now
        req.status = "UNDER_REVIEW"
    elif status_value in {"PENDING", "SUBMITTED", "DRAFT"}:
        req.status = "UNDER_REVIEW"

    await _save_strategy_request_attachments(db, req, files)
    await db.commit()
    await db.refresh(req)
    attachment_map = await _load_request_attachments(db, [req.id])
    return success_response(_serialize_request(req, attachment_map.get(str(req.id), [])), "Clarification submitted. Admin can review your updated request.")


@router.post("/{strategy_id}/refinement-request", status_code=status.HTTP_201_CREATED)
async def create_strategy_refinement_request(
    strategy_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    strategy = (await db.execute(select(Strategy).where(column_text(Strategy.id) == str(strategy_id)))).scalar_one_or_none()
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    user_id = _user_uuid(current_user["user_id"])
    visibility = (getattr(strategy, "visibility", None) or PRIVATE_VISIBILITY).upper()
    lifecycle = (getattr(strategy, "lifecycle_status", None) or "").upper()
    if lifecycle in {"ARCHIVED", "DELETED"}:
        raise HTTPException(status_code=404, detail="Strategy not found")

    source_req = None
    if getattr(strategy, "source_request_id", None):
        source_req = (await db.execute(select(StrategyRequest).where(StrategyRequest.id == strategy.source_request_id))).scalar_one_or_none()

    owns_strategy = str(strategy.created_by) == str(user_id)
    owns_source_request = bool(source_req and str(source_req.user_id) == str(user_id))
    if visibility != PUBLIC_VISIBILITY and not owns_strategy and not owns_source_request:
        raise HTTPException(status_code=404, detail="Strategy not found")

    form = await request.form()
    requested_changes = _form_text(form, "requested_changes") or _form_text(form, "refinement_notes")
    if not requested_changes:
        raise HTTPException(status_code=400, detail="Please describe what should be improved")
    files = [v for k, v in form.multi_items() if k in {"attachments", "attachments[]", "files"} and hasattr(v, "filename") and hasattr(v, "read")]
    if len(files) > MAX_ATTACHMENTS:
        raise HTTPException(status_code=400, detail="Upload maximum 6 chart screenshots")

    params = strategy.parameters if isinstance(strategy.parameters, dict) else {}
    source_params = {
        "strategy_type": getattr(source_req, "strategy_type", None),
        "market": getattr(source_req, "market", None),
        "timeframe": getattr(source_req, "timeframe", None),
        "indicators": getattr(source_req, "indicators", None),
        "entry_rules": getattr(source_req, "entry_rules", None),
        "exit_rules": getattr(source_req, "exit_rules", None),
        "confirmation_rules": getattr(source_req, "confirmation_rules", None),
        "risk_rules": getattr(source_req, "risk_rules", None),
        "invalidation_rules": getattr(source_req, "invalidation_rules", None),
        "trade_management_rules": getattr(source_req, "trade_management_rules", None),
    } if source_req else {}
    title = _form_text(form, "title") or f"Refinement: {strategy.name}"
    notes = _form_text(form, "notes") or requested_changes
    row = await _create_strategy_request_record(
        db,
        user_id=user_id,
        title=title,
        strategy_type=_form_text(form, "strategy_type") or params.get("strategy_type") or source_params.get("strategy_type"),
        market=_form_text(form, "market") or params.get("market") or source_params.get("market"),
        timeframe=_form_text(form, "timeframe") or params.get("timeframe") or source_params.get("timeframe"),
        indicators=params.get("indicators") if isinstance(params.get("indicators"), dict) else source_params.get("indicators"),
        entry_rules=_form_text(form, "entry_rules") or params.get("entry_rules") or source_params.get("entry_rules") or "Refinement requested",
        exit_rules=_form_text(form, "exit_rules") or params.get("exit_rules") or source_params.get("exit_rules") or "Refinement requested",
        confirmation_rules=_form_text(form, "confirmation_rules") or params.get("confirmation_rules") or source_params.get("confirmation_rules"),
        risk_rules=_form_text(form, "risk_rules") or params.get("risk_rules") or source_params.get("risk_rules") or "Refinement requested",
        invalidation_rules=_form_text(form, "invalidation_rules") or params.get("invalidation_rules") or source_params.get("invalidation_rules"),
        trade_management_rules=_form_text(form, "trade_management_rules") or params.get("trade_management_rules") or source_params.get("trade_management_rules"),
        notes=notes,
        parent_strategy_id=strategy.id,
        parent_request_id=getattr(strategy, "source_request_id", None),
        request_kind="REFINEMENT",
        refinement_notes=requested_changes,
        user_update_notes=requested_changes,
    )
    await _save_strategy_request_attachments(db, row, files)
    await db.commit()
    await db.refresh(row)
    attachment_map = await _load_request_attachments(db, [row.id])
    return success_response(_serialize_request(row, attachment_map.get(str(row.id), [])), "Refinement request submitted successfully")

@router.get("/{strategy_id}")
async def get_strategy_detail(
    strategy_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    strategy = (await db.execute(select(Strategy).where(column_text(Strategy.id) == str(strategy_id)))).scalar_one_or_none()
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    user_id = _user_uuid(current_user["user_id"])
    visibility = (getattr(strategy, "visibility", None) or PRIVATE_VISIBILITY).upper()
    is_admin = str(current_user.get("role", "")).upper() == "ADMIN"
    if visibility != PUBLIC_VISIBILITY and not is_admin:
        if str(strategy.created_by) != str(user_id) or not _is_user_visible_strategy(strategy, user_id):
            raise HTTPException(status_code=404, detail="Strategy not found")
    metrics_map = await _strategy_metrics_map(db, [strategy])
    template_user_id = await _get_template_user_id(db)
    data = _serialize_strategy(strategy, metrics_map.get(str(strategy.id)), template_user_id)
    params = strategy.parameters if isinstance(strategy.parameters, dict) else {}
    for key in ["entry_rules", "exit_rules", "confirmation_rules", "risk_rules", "invalidation_rules", "trade_management_rules", "notes", "source_code"]:
        if key != "source_code" or is_admin:
            data[key] = params.get(key)
    data["default_runtime_config"] = strategy.default_runtime_config
    data["defaultRuntimeConfig"] = strategy.default_runtime_config
    asset_public_only = visibility == PUBLIC_VISIBILITY and not is_admin and str(strategy.created_by) != str(user_id)
    assets = (await _load_strategy_assets(db, [strategy.id], public_only=asset_public_only)).get(str(strategy.id), [])
    data["assets"] = assets
    data["strategy_assets"] = assets
    data["strategyAssets"] = assets
    attachments: list[dict[str, Any]] = list(assets)
    if strategy.source_request_id:
        req = (await db.execute(select(StrategyRequest).where(StrategyRequest.id == strategy.source_request_id))).scalar_one_or_none()
        if req and (is_admin or str(req.user_id) == str(user_id) or (visibility != PUBLIC_VISIBILITY and str(strategy.created_by) == str(user_id))):
            request_attachments = (await _load_request_attachments(db, [req.id])).get(str(req.id), [])
            attachments.extend(request_attachments)
    data["attachments"] = attachments
    return success_response(data)


@router.get("/{strategy_id}/assets/{asset_id}")
async def get_strategy_asset(
    strategy_id: str,
    asset_id: str,
    download: bool = Query(False),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from fastapi.responses import FileResponse
    row = (await db.execute(
        select(StrategyAsset, Strategy)
        .join(Strategy, Strategy.id == StrategyAsset.strategy_id)
        .where(text("CAST(strategy_assets.id AS TEXT) = :aid AND CAST(strategy_assets.strategy_id AS TEXT) = :sid"))
        .params(aid=str(asset_id), sid=str(strategy_id))
    )).first()
    if not row:
        raise HTTPException(status_code=404, detail="Strategy image not found")
    asset, strategy = row
    is_admin = str(current_user.get("role", "")).upper() == "ADMIN"
    visibility = (getattr(strategy, "visibility", None) or PRIVATE_VISIBILITY).upper()
    is_owner = str(strategy.created_by) == str(current_user.get("user_id"))
    if not is_admin and not (visibility == PUBLIC_VISIBILITY and asset.is_public) and not is_owner:
        raise HTTPException(status_code=404, detail="Strategy image not found")
    path = _resolve_asset_file_path(asset.file_path)
    if not path:
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(
        path,
        media_type=asset.mime_type,
        filename=asset.original_name or asset.file_name,
        content_disposition_type="attachment" if download else "inline",
    )


@router.get("/requests/{request_id}/attachments/{attachment_id}")
async def get_strategy_request_attachment(
    request_id: str,
    attachment_id: str,
    download: bool = Query(False),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from fastapi.responses import FileResponse
    row = (await db.execute(
        select(StrategyRequestAttachment, StrategyRequest)
        .join(StrategyRequest, StrategyRequest.id == StrategyRequestAttachment.request_id)
        .where(text("CAST(strategy_request_attachments.id AS TEXT) = :aid AND CAST(strategy_request_attachments.request_id AS TEXT) = :rid"))
        .params(aid=str(attachment_id), rid=str(request_id))
    )).first()
    if not row:
        raise HTTPException(status_code=404, detail="Attachment not found")
    attachment, req = row
    is_admin = str(current_user.get("role", "")).upper() == "ADMIN"
    if not is_admin and str(req.user_id) != str(current_user["user_id"]):
        raise HTTPException(status_code=404, detail="Attachment not found")
    path = _resolve_attachment_file_path(attachment.file_path)
    if not path:
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(
        path,
        media_type=attachment.mime_type,
        filename=attachment.original_name or attachment.file_name,
        content_disposition_type="attachment" if download else "inline",
    )


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

