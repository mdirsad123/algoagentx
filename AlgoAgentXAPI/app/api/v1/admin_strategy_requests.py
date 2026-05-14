from __future__ import annotations

from typing import Any, Optional
from pathlib import Path

from datetime import date, timedelta, datetime, timezone
from uuid import uuid4
import hashlib

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.dependencies import get_admin_user, get_db
from ...db.compat import as_uuid_or_str, column_text
from ...db.models.strategy_requests import StrategyRequest, StrategyRequestAttachment
from ...db.models.strategies import Strategy, StrategyRuntimePreset, StrategyAsset
from ...db.models.users import User
from ...db.models import Instrument, MarketData
from ...services.backtest_service import BacktestService
from ...services.dynamic_strategy_loader import validate_dynamic_strategy_source, DynamicStrategyLoadError, DynamicStrategySecurityError
from ...services.trading.runtime_config_service import get_system_default_runtime_config, get_default_runtime_config_schema, normalize_runtime_config
from ...utils.api_response import success_response
from .strategies import (
    PRIVATE_VISIBILITY,
    PUBLIC_VISIBILITY,
    VALID_REQUEST_STATUSES,
    _safe_float,
    _safe_int,
    _upsert_strategy_from_request,
    _load_request_attachments,
)

router = APIRouter()
VALID_VISIBILITY = {PRIVATE_VISIBILITY, PUBLIC_VISIBILITY}

PROJECT_ROOT = Path(__file__).resolve().parents[3]
STRATEGY_ASSET_ROOT = PROJECT_ROOT / "uploads" / "strategy_assets"
ALLOWED_STRATEGY_ASSET_TYPES = {"image/png", "image/jpeg", "image/webp"}
MAX_STRATEGY_ASSET_SIZE = 5 * 1024 * 1024
MAX_STRATEGY_ASSETS = 6


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


async def _load_strategy_assets(db: AsyncSession, strategy_ids: list[Any]) -> dict[str, list[dict[str, Any]]]:
    ids = [str(item) for item in strategy_ids if item]
    if not ids:
        return {}
    try:
        rows = (await db.execute(
            select(StrategyAsset)
            .where(StrategyAsset.strategy_id.in_(ids))
            .order_by(StrategyAsset.sort_order.asc(), StrategyAsset.created_at.asc())
        )).scalars().all()
    except Exception:
        return {}
    out: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        out.setdefault(str(row.strategy_id), []).append(_serialize_strategy_asset(row))
    return out


async def _save_strategy_assets(db: AsyncSession, strategy: Strategy, files: list[UploadFile], admin_user: dict) -> list[dict[str, Any]]:
    if len(files) > MAX_STRATEGY_ASSETS:
        raise HTTPException(status_code=400, detail="Maximum 6 concept images are allowed")
    existing_count = (await db.execute(select(func.count()).select_from(StrategyAsset).where(StrategyAsset.strategy_id == str(strategy.id)))).scalar() or 0
    if int(existing_count) + len(files) > MAX_STRATEGY_ASSETS:
        raise HTTPException(status_code=400, detail="Maximum 6 concept images are allowed per strategy")
    target_dir = STRATEGY_ASSET_ROOT / str(strategy.id)
    target_dir.mkdir(parents=True, exist_ok=True)
    created: list[StrategyAsset] = []
    for offset, upload in enumerate(files):
        if upload.content_type not in ALLOWED_STRATEGY_ASSET_TYPES:
            raise HTTPException(status_code=400, detail="Only PNG, JPEG, or WEBP concept images are allowed")
        original = Path(upload.filename or f"strategy-image-{offset + 1}").name
        safe_name = f"{int(existing_count) + offset + 1:02d}_{uuid4().hex}_{original}"[:240]
        path = target_dir / safe_name
        size = 0
        with path.open("wb") as buffer:
            while True:
                chunk = await upload.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_STRATEGY_ASSET_SIZE:
                    path.unlink(missing_ok=True)
                    raise HTTPException(status_code=400, detail="Each concept image must be 5 MB or smaller")
                buffer.write(chunk)
        row = StrategyAsset(
            strategy_id=str(strategy.id),
            file_name=safe_name,
            original_name=original,
            file_path=str(path.relative_to(PROJECT_ROOT) if path.is_absolute() else path),
            public_url=None,
            mime_type=upload.content_type or "application/octet-stream",
            size_bytes=size,
            sort_order=int(existing_count) + offset,
            is_public=True,
            uploaded_by=as_uuid_or_str(admin_user.get("user_id")) if admin_user.get("user_id") else None,
        )
        db.add(row)
        created.append(row)
    await db.flush()
    return [_serialize_strategy_asset(row) for row in created]


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
    source_code: Optional[str] = None
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
    source_code: Optional[str] = None
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


def _build_default_runtime_config(params: dict[str, Any] | None = None, strategy_name: str | None = None) -> dict[str, Any]:
    """Professional default preset for workshop-created strategies.

    Uses the existing common risk/engine contract. If a pasted strategy emits
    strategy_stop_loss / strategy_target, STRATEGY_SUGGESTED will consume them.
    Otherwise the engine safely falls back to fixed/ATR behavior based on config.
    """
    params = params if isinstance(params, dict) else {}
    config = get_system_default_runtime_config()
    config.setdefault("risk", {}).update({
        "initial_capital": 1000,
        "risk_percent": float(params.get("risk_percent") or 0.01),
        "position_size_mode": "RISK_BASED",
    })
    config.setdefault("execution", {}).update({
        "entry_mode": "NEXT_CANDLE_OPEN",
        "exit_on_opposite_signal": True,
        "allow_long": True,
        "allow_short": True,
        "max_open_positions": 1,
        "intraday_square_off": False,
    })
    config.setdefault("sl_tp", {}).update({
        "sl_mode": "STRATEGY_SUGGESTED",
        "use_strategy_suggested_sl": True,
        "rr_ratio": float(params.get("rr_ratio") or 2.0),
        "atr_period": int(params.get("atr_period") or 14),
        "atr_multiplier": float(params.get("atr_multiplier") or 1.5),
        "swing_lookback": int(params.get("swing_lookback") or 5),
        "fixed_price_risk_pct": float(params.get("fixed_price_risk_pct") or 0.002),
    })
    config.setdefault("strategy_params", {})
    for key, value in params.items():
        if str(key).startswith("_") or key in {
            "source_code", "strategy_type", "market", "timeframe", "entry_rules", "exit_rules",
            "confirmation_rules", "risk_rules", "invalidation_rules", "trade_management_rules", "notes",
            "performance_metrics",
        }:
            continue
        if isinstance(value, (str, int, float, bool)):
            config["strategy_params"][str(key)] = value
    return normalize_runtime_config(config)


async def _ensure_default_runtime_preset(db: AsyncSession, strategy: Strategy, admin_user: dict | None = None) -> None:
    params = strategy.parameters if isinstance(strategy.parameters, dict) else {}
    default_config = _build_default_runtime_config(params, strategy.name)
    strategy.default_runtime_config = strategy.default_runtime_config or default_config
    strategy.runtime_config_schema = strategy.runtime_config_schema or get_default_runtime_config_schema(
        " ".join([str(strategy.name or ""), str(params.get("strategy_type") or "")])
    )
    strategy.supports_runtime_config = True
    strategy.config_version = int(getattr(strategy, "config_version", 1) or 1)

    existing_default = (
        await db.execute(
            select(StrategyRuntimePreset).where(
                StrategyRuntimePreset.strategy_id == str(strategy.id),
                StrategyRuntimePreset.is_default == True,
                StrategyRuntimePreset.is_active == True,
            )
        )
    ).scalar_one_or_none()

    if existing_default:
        if not existing_default.config_json:
            existing_default.config_json = default_config
        return

    row = StrategyRuntimePreset(
        id=str(uuid4()),
        strategy_id=str(strategy.id),
        name="Default Risk-Based Runtime",
        description="Auto-created by Strategy Workshop. Uses common engine, risk-based sizing, next-candle entry, and strategy-suggested SL/TP when provided by code.",
        config_json=default_config,
        risk_label="Risk 1% | Strategy SL/TP | RR 1:2",
        is_default=True,
        is_active=True,
        created_by=as_uuid_or_str(admin_user.get("user_id")) if admin_user and admin_user.get("user_id") else None,
    )
    db.add(row)


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


def _serialize_request(req: StrategyRequest, email: Optional[str] = None, fullname: Optional[str] = None, attachments: Optional[list[dict[str, Any]]] = None) -> dict[str, Any]:
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
        "confirmation_rules": getattr(req, "confirmation_rules", None),
        "invalidation_rules": getattr(req, "invalidation_rules", None),
        "trade_management_rules": getattr(req, "trade_management_rules", None),
        "notes": req.notes,
        "user_update_notes": getattr(req, "user_update_notes", None),
        "userUpdateNotes": getattr(req, "user_update_notes", None),
        "clarification_reply": getattr(req, "user_update_notes", None),
        "clarificationReply": getattr(req, "user_update_notes", None),
        "clarification_submitted_at": _serialize_dt(getattr(req, "clarification_submitted_at", None)),
        "clarificationSubmittedAt": _serialize_dt(getattr(req, "clarification_submitted_at", None)),
        "last_user_update_at": _serialize_dt(getattr(req, "last_user_update_at", None)),
        "lastUserUpdateAt": _serialize_dt(getattr(req, "last_user_update_at", None)),
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
        "description": req.notes or req.entry_rules,
        "status": req.status,
        "user_id": str(req.user_id),
        "user_email": email,
        "user_name": fullname or email,
        "admin_notes": req.admin_notes,
        "assigned_to": str(req.assigned_to) if getattr(req, "assigned_to", None) else None,
        "deployed_strategy_id": str(req.deployed_strategy_id) if getattr(req, "deployed_strategy_id", None) else None,
        "deployedStrategyId": str(req.deployed_strategy_id) if getattr(req, "deployed_strategy_id", None) else None,
        "linked_strategy_id": str(req.deployed_strategy_id) if getattr(req, "deployed_strategy_id", None) else None,
        "linkedStrategyId": str(req.deployed_strategy_id) if getattr(req, "deployed_strategy_id", None) else None,
        "workspace_status": "Workspace Created" if getattr(req, "deployed_strategy_id", None) else "Not Started",
        "workspaceStatus": "Workspace Created" if getattr(req, "deployed_strategy_id", None) else "Not Started",
        "created_at": _serialize_dt(req.created_at),
        "createdAt": _serialize_dt(req.created_at),
        "updated_at": _serialize_dt(req.updated_at),
        "updatedAt": _serialize_dt(req.updated_at),
    }




def _snapshot_strategy(strategy: Strategy) -> dict[str, Any]:
    params = dict(strategy.parameters or {})
    return {
        "version_id": str(uuid4()),
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "name": strategy.name,
        "description": strategy.description,
        "visibility": getattr(strategy, "visibility", PRIVATE_VISIBILITY),
        "source_request_id": str(strategy.source_request_id) if getattr(strategy, "source_request_id", None) else None,
        "payload": {
            "strategy_type": params.get("strategy_type"),
            "market": params.get("market"),
            "timeframe": params.get("timeframe"),
            "entry_rules": params.get("entry_rules"),
            "exit_rules": params.get("exit_rules"),
            "confirmation_rules": params.get("confirmation_rules"),
            "risk_rules": params.get("risk_rules"),
            "invalidation_rules": params.get("invalidation_rules"),
            "trade_management_rules": params.get("trade_management_rules"),
            "notes": params.get("notes"),
            "source_code": params.get("source_code"),
            "parameters": {
                k: v for k, v in params.items() if not str(k).startswith("_") and k not in {
                    "strategy_type", "market", "timeframe", "entry_rules", "exit_rules", "confirmation_rules",
                    "risk_rules", "invalidation_rules", "trade_management_rules", "notes", "source_code", "performance_metrics"
                }
            },
            "performance_metrics": params.get("performance_metrics"),
        },
    }


def _append_version_history(params: dict[str, Any], strategy: Strategy, admin_user: dict, reason: str = "save") -> dict[str, Any]:
    history = list(params.get("_ide_versions") or [])
    snapshot = _snapshot_strategy(strategy)
    snapshot["editor_user_id"] = str(admin_user.get("user_id")) if admin_user.get("user_id") else None
    snapshot["reason"] = reason
    history.insert(0, snapshot)
    params["_ide_versions"] = history[:20]
    return params


def _strategy_hash_from_params(params: dict[str, Any]) -> str:
    relevant = {
        "source_code": params.get("source_code"),
        "execution": {
            "rr_ratio": params.get("rr_ratio"),
            "capital_risk_pct": params.get("capital_risk_pct"),
            "price_risk_pct": params.get("price_risk_pct"),
            "max_bars_in_trade": params.get("max_bars_in_trade"),
        },
        "rules": {
            "entry_rules": params.get("entry_rules"),
            "exit_rules": params.get("exit_rules"),
            "confirmation_rules": params.get("confirmation_rules"),
            "risk_rules": params.get("risk_rules"),
            "invalidation_rules": params.get("invalidation_rules"),
            "trade_management_rules": params.get("trade_management_rules"),
        },
    }
    return hashlib.sha256(repr(relevant).encode("utf-8")).hexdigest()


def _get_workflow_state(params: dict[str, Any]) -> dict[str, Any]:
    return dict(params.get("_workflow") or {})


def _set_workflow_state(params: dict[str, Any], *, validation: dict[str, Any] | None = None, sandbox: dict[str, Any] | None = None) -> dict[str, Any]:
    workflow = _get_workflow_state(params)
    if validation is not None:
        workflow["validation"] = validation
    if sandbox is not None:
        workflow["sandbox"] = sandbox
    params["_workflow"] = workflow
    return params


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
        "source_code": params.get("source_code"),
        "sourceCode": params.get("source_code"),
        "winRate": _safe_float(metrics.get("win_rate")),
        "sharpeRatio": _safe_float(metrics.get("sharpe_ratio")),
        "maxDrawdown": _safe_float(metrics.get("max_drawdown")),
        "totalTrades": _safe_int(metrics.get("total_trades")),
        "profitFactor": _safe_float(metrics.get("profit_factor")),
        "parameters": params,
        "workflow": _get_workflow_state(params),
        "workspace_status": _workspace_status_for_strategy(item),
        "workspaceStatus": _workspace_status_for_strategy(item),
        "version_count": len(params.get("_ide_versions") or []),
        "assets": [],
        "strategy_assets": [],
        "strategyAssets": [],
        "source_request_id": str(item.source_request_id) if getattr(item, "source_request_id", None) else None,
        "sourceRequestId": str(item.source_request_id) if getattr(item, "source_request_id", None) else None,
        "created_by": str(item.created_by) if getattr(item, "created_by", None) else None,
        "published_by": str(item.published_by) if getattr(item, "published_by", None) else None,
        "created_at": _serialize_dt(item.created_at),
        "createdAt": _serialize_dt(item.created_at),
        "updated_at": _serialize_dt(item.updated_at),
        "updatedAt": _serialize_dt(item.updated_at),
        "lifecycle_status": getattr(item, "lifecycle_status", None) or "DRAFT",
        "lifecycleStatus": getattr(item, "lifecycle_status", None) or "DRAFT",
        "is_deployable_paper": bool(getattr(item, "is_deployable_paper", False)),
        "isDeployablePaper": bool(getattr(item, "is_deployable_paper", False)),
        "is_deployable_demo": bool(getattr(item, "is_deployable_demo", False)),
        "isDeployableDemo": bool(getattr(item, "is_deployable_demo", False)),
        "is_live_approved": bool(getattr(item, "is_live_approved", False)),
        "isLiveApproved": bool(getattr(item, "is_live_approved", False)),
        "verified_at": _serialize_dt(getattr(item, "verified_at", None)),
        "verifiedAt": _serialize_dt(getattr(item, "verified_at", None)),
        "sandbox_passed_at": _serialize_dt(getattr(item, "sandbox_passed_at", None)),
        "sandboxPassedAt": _serialize_dt(getattr(item, "sandbox_passed_at", None)),
        "paper_enabled_at": _serialize_dt(getattr(item, "paper_enabled_at", None)),
        "paperEnabledAt": _serialize_dt(getattr(item, "paper_enabled_at", None)),
        "demo_enabled_at": _serialize_dt(getattr(item, "demo_enabled_at", None)),
        "demoEnabledAt": _serialize_dt(getattr(item, "demo_enabled_at", None)),
        "live_approved_at": _serialize_dt(getattr(item, "live_approved_at", None)),
        "liveApprovedAt": _serialize_dt(getattr(item, "live_approved_at", None)),
        "approved_by": str(getattr(item, "approved_by", None)) if getattr(item, "approved_by", None) else None,
        "approvedBy": str(getattr(item, "approved_by", None)) if getattr(item, "approved_by", None) else None,
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
    if getattr(payload, "source_code", None) is not None:
        _set_or_remove(params, "source_code", _clean(payload.source_code), remove_if_none=False)
        if _clean(payload.source_code):
            params["engine_mode"] = "DYNAMIC_DB"
        else:
            params.pop("engine_mode", None)

    if payload.performance_metrics is not None:
        _set_or_remove(params, "performance_metrics", payload.performance_metrics)

    if any(getattr(payload, field, None) is not None for field in ["source_code", "entry_rules", "exit_rules", "confirmation_rules", "risk_rules", "invalidation_rules", "trade_management_rules", "market", "timeframe"]):
        params["_workflow"] = {}

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


def _workspace_status_for_strategy(strategy: Strategy | None, req: StrategyRequest | None = None) -> str:
    if req is not None and getattr(req, "status", None) == "DEPLOYED":
        visibility = (getattr(strategy, "visibility", None) if strategy else None) or PRIVATE_VISIBILITY
        return "Public Published" if visibility == PUBLIC_VISIBILITY else "Private Deployed"
    if not strategy:
        return "Not Started"
    params = strategy.parameters if isinstance(strategy.parameters, dict) else {}
    workflow = _get_workflow_state(params)
    if workflow.get("sandbox", {}).get("ok"):
        return "Sandbox Passed"
    if workflow.get("validation", {}).get("ok") or getattr(strategy, "verified_at", None):
        return "Verify Passed"
    if params.get("source_code"):
        return "Code Attached"
    return "Workspace Created"


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
    request_ids = [req.id for req, _, _ in rows]
    attachment_map = await _load_request_attachments(db, request_ids)
    linked_strategy_map: dict[str, Strategy] = {}
    parent_strategy_map: dict[str, Strategy] = {}
    if request_ids:
        linked_rows = (
            await db.execute(
                select(Strategy).where(Strategy.source_request_id.in_(request_ids))
            )
        ).scalars().all()
        linked_strategy_map = {str(item.source_request_id): item for item in linked_rows if getattr(item, "source_request_id", None)}
        parent_ids = [str(req.parent_strategy_id) for req, _, _ in rows if getattr(req, "parent_strategy_id", None)]
        if parent_ids:
            parent_rows = (await db.execute(select(Strategy).where(column_text(Strategy.id).in_(parent_ids)))).scalars().all()
            parent_strategy_map = {str(item.id): item for item in parent_rows}

    items = []
    for req, email, fullname in rows:
        row_data = _serialize_request(req, email, fullname, attachment_map.get(str(req.id), []))
        linked_strategy = linked_strategy_map.get(str(req.id))
        if linked_strategy:
            row_data["deployed_strategy_id"] = str(linked_strategy.id)
            row_data["deployedStrategyId"] = str(linked_strategy.id)
            row_data["linked_strategy_id"] = str(linked_strategy.id)
            row_data["linkedStrategyId"] = str(linked_strategy.id)
        parent_strategy = parent_strategy_map.get(str(getattr(req, "parent_strategy_id", "")))
        if parent_strategy:
            row_data["original_strategy_name"] = parent_strategy.name
            row_data["originalStrategyName"] = parent_strategy.name
        row_data["workspace_status"] = _workspace_status_for_strategy(linked_strategy, req)
        row_data["workspaceStatus"] = row_data["workspace_status"]
        items.append(row_data)

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




class StrategyValidationIn(BaseModel):
    instrument_id: Optional[int] = None
    timeframe: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    capital: float = 100000


async def _resolve_validation_window(db: AsyncSession, instrument_id: int, timeframe: str, requested_start: Optional[date], requested_end: Optional[date]) -> tuple[date, date]:
    if requested_start and requested_end:
        return requested_start, requested_end

    row = (
        await db.execute(
            select(func.min(MarketData.timestamp), func.max(MarketData.timestamp))
            .where(MarketData.instrument_id == instrument_id, MarketData.timeframe == timeframe)
        )
    ).one_or_none()

    min_ts = row[0] if row else None
    max_ts = row[1] if row else None
    if max_ts is None:
        end_date = requested_end or date.today()
        start_date = requested_start or (end_date - timedelta(days=14))
        return start_date, end_date

    resolved_end = requested_end or max_ts.date()
    resolved_start = requested_start or max(min_ts.date() if min_ts else resolved_end - timedelta(days=14), resolved_end - timedelta(days=14))
    if resolved_start > resolved_end:
        resolved_start = resolved_end - timedelta(days=14)
    return resolved_start, resolved_end


@router.post("/strategies/{strategy_id}/validate")
async def validate_strategy_code(
    strategy_id: str,
    payload: StrategyValidationIn,
    admin_user: dict = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    strategy = await _get_strategy_or_404(db, strategy_id)
    params = strategy.parameters if isinstance(strategy.parameters, dict) else {}
    source_code = str(params.get("source_code") or "")

    syntax_ok = True
    syntax_message = "No custom source code attached. Static registry strategy will be used if available."
    if source_code.strip():
        try:
            safety = validate_dynamic_strategy_source(source_code)
            classes = ", ".join(safety.get("classes") or [])
            syntax_message = f"Dynamic source check passed. Strategy class found: {classes or 'Strategy'}."
        except (DynamicStrategyLoadError, DynamicStrategySecurityError, Exception) as exc:
            syntax_ok = False
            syntax_message = f"Dynamic source check failed: {exc}"

    instrument_id = payload.instrument_id
    timeframe = payload.timeframe or params.get("timeframe") or "5m"
    if instrument_id is None:
        instrument_id = (await db.execute(select(Instrument.id).order_by(Instrument.id.asc()).limit(1))).scalar()
    if instrument_id is None:
        raise HTTPException(status_code=400, detail="No instrument available for validation")

    start_date, end_date = await _resolve_validation_window(db, int(instrument_id), str(timeframe), payload.start_date, payload.end_date)

    sample_result = None
    validation_ok = False
    validation_message = syntax_message
    try:
        service_response = await BacktestService.run_backtest(
            db=db,
            strategy_id=strategy_id,
            instrument_id=int(instrument_id),
            timeframe=str(timeframe),
            start_date=start_date,
            end_date=end_date,
            initial_capital=payload.capital,
        )
        trades = service_response.result.trades or []
        buy_count = sum(1 for t in trades if str(getattr(t, "direction", "")).upper() == "LONG")
        sell_count = sum(1 for t in trades if str(getattr(t, "direction", "")).upper() == "SHORT")
        sample_result = {
            "instrument_id": int(instrument_id),
            "timeframe": str(timeframe),
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "total_trades": len(trades),
            "buy_signals": buy_count,
            "sell_signals": sell_count,
            "final_capital": float(service_response.final_capital),
        }
        validation_ok = syntax_ok
        validation_message = "Validation run completed successfully." if syntax_ok else syntax_message
    except Exception as exc:
        validation_ok = False
        validation_message = f"Validation backtest failed: {exc}"

    params = dict(strategy.parameters or {})
    params = _set_workflow_state(params, validation={
        "ok": bool(validation_ok),
        "message": validation_message,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "source_hash": _strategy_hash_from_params(params),
        "sample_result": sample_result,
    })
    strategy.parameters = params
    strategy.verified_at = datetime.now(timezone.utc) if validation_ok else None
    if validation_ok:
        strategy.lifecycle_status = "VERIFIED"
    await db.commit()

    return success_response({
        "strategy_id": strategy_id,
        "strategy_name": strategy.name,
        "syntax_ok": syntax_ok,
        "validation_ok": validation_ok,
        "message": validation_message,
        "sample_result": sample_result,
    })



@router.get("/strategies/{strategy_id}")
async def get_strategy_by_id(
    strategy_id: str,
    admin_user: dict = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    strategy = await _get_strategy_or_404(db, strategy_id)
    data = _serialize_strategy(strategy)
    assets = (await _load_strategy_assets(db, [strategy.id])).get(str(strategy.id), [])
    data["assets"] = assets
    data["strategy_assets"] = assets
    data["strategyAssets"] = assets
    if getattr(strategy, "source_request_id", None):
        data["attachments"] = (await _load_request_attachments(db, [strategy.source_request_id])).get(str(strategy.source_request_id), [])
        row = (
            await db.execute(
                select(StrategyRequest, User.email, User.fullname)
                .join(User, User.id == StrategyRequest.user_id)
                .where(column_text(StrategyRequest.id) == str(strategy.source_request_id))
            )
        ).first()
        if row:
            req, email, fullname = row
            data["source_request"] = _serialize_request(req, email, fullname, data["attachments"])
            data["sourceRequest"] = data["source_request"]
    return success_response(data)


class StrategySandboxBacktestIn(BaseModel):
    instrument_id: int
    timeframe: str
    start_date: date
    end_date: date
    capital: float = 100000


@router.post("/strategies/{strategy_id}/sandbox-backtest")
async def sandbox_backtest_strategy(
    strategy_id: str,
    payload: StrategySandboxBacktestIn,
    admin_user: dict = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    strategy = await _get_strategy_or_404(db, strategy_id)
    resolved_start_date, resolved_end_date = await _resolve_validation_window(db, int(payload.instrument_id), str(payload.timeframe), payload.start_date, payload.end_date)
    service_response = await BacktestService.run_backtest(
        db=db,
        strategy_id=strategy_id,
        instrument_id=int(payload.instrument_id),
        timeframe=str(payload.timeframe),
        start_date=resolved_start_date,
        end_date=resolved_end_date,
        initial_capital=payload.capital,
    )

    result = service_response.result
    trades = getattr(result, "trades", None) or []
    raw_pnl_calendar = getattr(result, "daily_pnl", None) or []
    equity = getattr(result, "equity_curve", None) or []
    summary = getattr(result, "summary", None) or {}

    # Normalize engine summary keys for sandbox UI.
    initial_capital_value = float(getattr(service_response, "initial_capital", payload.capital) or payload.capital)
    final_capital_value = float(getattr(service_response, "final_capital", initial_capital_value) or initial_capital_value)

    if "net_profit" not in summary:
        summary["net_profit"] = float(
            summary.get("net_pnl", final_capital_value - initial_capital_value) or 0
        )

    if "return_pct" not in summary:
        total_return = getattr(result, "total_return", None)
        if total_return is not None:
            value = float(total_return or 0)
            summary["return_pct"] = value * 100.0 if abs(value) <= 1 else value
        else:
            summary["return_pct"] = (
                ((final_capital_value - initial_capital_value) / initial_capital_value) * 100.0
                if initial_capital_value
                else 0.0
            )

    if "win_rate" not in summary:
        value = float(getattr(result, "win_rate", 0) or 0)
        summary["win_rate"] = value * 100.0 if abs(value) <= 1 else value

    if "sharpe_ratio" not in summary:
        summary["sharpe_ratio"] = float(getattr(result, "sharpe_ratio", 0) or 0)

    if "total_trades" not in summary:
        summary["total_trades"] = len(trades)

    def _dt(v):
        return v.isoformat() if hasattr(v, 'isoformat') else v

    if not raw_pnl_calendar and trades:
        daily_totals: dict[str, float] = {}
        for t in trades:
            dt_value = getattr(t, 'exit_time', None) or getattr(t, 'exit_datetime', None) or getattr(t, 'entry_time', None) or getattr(t, 'entry_datetime', None)
            key = dt_value.date().isoformat() if hasattr(dt_value, 'date') else str(dt_value)[:10]
            daily_totals[key] = daily_totals.get(key, 0.0) + float(getattr(t, 'pnl', 0) or 0)
        pnl_calendar = [{"date": key, "pnl": value} for key, value in sorted(daily_totals.items())]
    else:
        pnl_calendar = raw_pnl_calendar

    if not summary:
        total_trades = len(trades)
        win_rate = float(getattr(service_response, 'win_rate', 0) or 0) * 100.0
        net_profit = float(getattr(service_response, 'net_profit', 0) or 0)
        return_pct = ((float(getattr(service_response, 'final_capital', 0) or 0) - float(getattr(service_response, 'initial_capital', payload.capital) or payload.capital)) / float(getattr(service_response, 'initial_capital', payload.capital) or payload.capital) * 100.0) if float(getattr(service_response, 'initial_capital', payload.capital) or payload.capital) else 0.0
        wins = [float(getattr(t, 'pnl', 0) or 0) for t in trades if float(getattr(t, 'pnl', 0) or 0) > 0]
        losses = [abs(float(getattr(t, 'pnl', 0) or 0)) for t in trades if float(getattr(t, 'pnl', 0) or 0) < 0]
        gross_profit = sum(wins)
        gross_loss = sum(losses)
        avg_win = gross_profit / len(wins) if wins else 0.0
        avg_loss = gross_loss / len(losses) if losses else 0.0
        profit_factor = gross_profit / gross_loss if gross_loss else (gross_profit if gross_profit else 0.0)
        expectancy = (sum(float(getattr(t, 'pnl', 0) or 0) for t in trades) / total_trades) if total_trades else 0.0
        summary = {
            'net_profit': net_profit,
            'return_pct': return_pct,
            'win_rate': win_rate,
            'max_drawdown': float(getattr(service_response, 'max_drawdown', 0) or 0) * 100.0 if abs(float(getattr(service_response, 'max_drawdown', 0) or 0)) <= 1 else float(getattr(service_response, 'max_drawdown', 0) or 0),
            'sharpe_ratio': float(getattr(service_response, 'sharpe_ratio', 0) or 0),
            'profit_factor': profit_factor,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'expectancy': expectancy,
            'total_trades': total_trades,
        }

    def _equity_point(point, index):
        if isinstance(point, dict):
            ts = point.get('timestamp')
            eq = point.get('equity', 0)
        else:
            ts = None
            eq = point
        return {"timestamp": _dt(ts) if ts is not None else str(index + 1), "equity": float(eq or 0)}

    params = dict(strategy.parameters or {})
    params = _set_workflow_state(params, sandbox={
        "ok": True,
        "message": "Sandbox backtest completed successfully",
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "source_hash": _strategy_hash_from_params(params),
        "summary": {
            "net_profit": float(summary.get('net_profit', 0) or 0),
            "return_pct": float(summary.get('return_pct', 0) or 0),
            "total_trades": int(summary.get('total_trades', len(trades)) or 0),
            "win_rate": float(summary.get('win_rate', 0) or 0),
            "profit_factor": float(summary.get('profit_factor', 0) or 0),
        },
    })
    strategy.parameters = params
    strategy.sandbox_passed_at = datetime.now(timezone.utc)
    strategy.lifecycle_status = "SANDBOX_PASSED"
    await db.commit()

    return success_response({
        "strategy_id": strategy_id,
        "strategy_name": strategy.name,
        "summary": {
            "initial_capital": float(getattr(service_response, 'initial_capital', payload.capital) or payload.capital),
            "final_capital": float(getattr(service_response, 'final_capital', payload.capital) or payload.capital),
            "net_profit": float(summary.get('net_profit', 0) or 0),
            "return_pct": float(summary.get('return_pct', 0) or 0),
            "win_rate": float(summary.get('win_rate', 0) or 0),
            "max_drawdown": float(summary.get('max_drawdown', 0) or 0),
            "sharpe_ratio": float(summary.get('sharpe_ratio', 0) or 0),
            "profit_factor": float(summary.get('profit_factor', 0) or 0),
            "avg_win": float(summary.get('avg_win', 0) or 0),
            "avg_loss": float(summary.get('avg_loss', 0) or 0),
            "expectancy": float(summary.get('expectancy', 0) or 0),
            "total_trades": int(summary.get('total_trades', len(trades)) or 0),
        },
        "trades": [
            {
                "entry_time": _dt(getattr(t, 'entry_time', None)),
                "exit_time": _dt(getattr(t, 'exit_time', None)),
                "side": getattr(t, 'direction', None) or getattr(t, 'side', None),
                "quantity": getattr(t, 'quantity', None),
                "entry_price": getattr(t, 'entry_price', None),
                "exit_price": getattr(t, 'exit_price', None),
                "pnl": getattr(t, 'pnl', None),
                "exit_type": getattr(t, 'exit_reason', None) or getattr(t, 'exit_type', None),
            }
            for t in trades[:50]
        ],
        "equity_curve": [_equity_point(point, index) for index, point in enumerate(equity[-300:])],
        "pnl_calendar": [
            {"date": item.get('date'), "pnl": float(item.get('pnl', 0) or 0)}
            for item in pnl_calendar
        ],
    })

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
    asset_map = await _load_strategy_assets(db, [item.id for item in rows])

    return success_response(
        {
            "items": [{**_serialize_strategy(item), **({"assets": asset_map.get(str(item.id), []), "strategy_assets": asset_map.get(str(item.id), []), "strategyAssets": asset_map.get(str(item.id), [])})} for item in rows],
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

    default_runtime_config = _build_default_runtime_config(params, name)
    strategy = Strategy(
        id=str(uuid4()),
        name=name,
        description=_clean(payload.description),
        parameters=params,
        default_runtime_config=default_runtime_config,
        runtime_config_schema=get_default_runtime_config_schema(" ".join([name, str(params.get("strategy_type") or "")])),
        supports_runtime_config=True,
        config_version=1,
        visibility=visibility,
        source_request_id=as_uuid_or_str(payload.source_request_id) if payload.source_request_id else None,
        created_by=as_uuid_or_str(payload.created_by) if payload.created_by else as_uuid_or_str(admin_user["user_id"]),
        published_by=as_uuid_or_str(admin_user["user_id"]) if visibility == PUBLIC_VISIBILITY else None,
    )
    db.add(strategy)
    await _ensure_default_runtime_preset(db, strategy, admin_user)

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
    params = _append_version_history(params, strategy, admin_user, reason="save")
    params = _apply_payload_to_parameters(params, payload)
    strategy.parameters = params
    await _ensure_default_runtime_preset(db, strategy, admin_user)

    if payload.visibility is not None:
        strategy.visibility = _normalize_visibility(payload.visibility)

    if strategy.visibility == PUBLIC_VISIBILITY:
        _ensure_publish_gate(params)
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


@router.post("/strategies/{strategy_id}/assets")
async def upload_strategy_assets(
    strategy_id: str,
    files: list[UploadFile] = File(default=[]),
    admin_user: dict = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    strategy = await _get_strategy_or_404(db, strategy_id)
    if not files:
        return success_response({"items": []}, "No files uploaded")
    items = await _save_strategy_assets(db, strategy, files, admin_user)
    await db.commit()
    return success_response({"items": items}, "Strategy images uploaded successfully")


@router.get("/strategies/{strategy_id}/versions")
async def list_strategy_versions(
    strategy_id: str,
    admin_user: dict = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    strategy = await _get_strategy_or_404(db, strategy_id)
    params = dict(strategy.parameters or {})
    return success_response({
        "items": list(params.get("_ide_versions") or []),
        "current_hash": _strategy_hash_from_params(params),
        "workflow": _get_workflow_state(params),
    })


@router.post("/strategies/{strategy_id}/rollback/{version_id}")
async def rollback_strategy_version(
    strategy_id: str,
    version_id: str,
    admin_user: dict = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    strategy = await _get_strategy_or_404(db, strategy_id)
    params = dict(strategy.parameters or {})
    history = list(params.get("_ide_versions") or [])
    match = next((v for v in history if str(v.get("version_id")) == str(version_id)), None)
    if not match:
        raise HTTPException(status_code=404, detail="Version not found")
    params = _append_version_history(params, strategy, admin_user, reason="rollback")
    payload = match.get("payload") or {}
    strategy.name = match.get("name") or strategy.name
    strategy.description = match.get("description")
    strategy.visibility = match.get("visibility") or strategy.visibility
    strategy.source_request_id = as_uuid_or_str(match.get("source_request_id")) if match.get("source_request_id") else strategy.source_request_id
    params.update(payload.get("parameters") or {})
    for key in ["strategy_type","market","timeframe","entry_rules","exit_rules","confirmation_rules","risk_rules","invalidation_rules","trade_management_rules","notes","source_code","performance_metrics"]:
        if key in payload:
            if payload.get(key) is None:
                params.pop(key, None)
            else:
                params[key] = payload.get(key)
    params["_workflow"] = {}
    strategy.parameters = params
    await db.commit()
    await db.refresh(strategy)
    return success_response(_serialize_strategy(strategy), "Strategy rolled back successfully")


@router.get("/strategy-presets")
async def list_strategy_presets(
    admin_user: dict = Depends(get_admin_user),
):
    presets = [
        {"key": "intraday_momentum", "name": "Intraday Momentum", "config": {"rr_ratio": 2, "capital_risk_pct": 0.01, "price_risk_pct": 0.002, "max_bars_in_trade": 6}},
        {"key": "swing_rr4", "name": "Swing RR 1:4", "config": {"rr_ratio": 4, "capital_risk_pct": 0.02, "price_risk_pct": 0.01, "max_bars_in_trade": 20}},
        {"key": "scalp_tight_risk", "name": "Scalp Tight Risk", "config": {"rr_ratio": 1.5, "capital_risk_pct": 0.005, "price_risk_pct": 0.001, "max_bars_in_trade": 3}},
    ]
    return success_response({"items": presets})


def _ensure_publish_gate(params: dict[str, Any]) -> None:
    workflow = _get_workflow_state(params)
    current_hash = _strategy_hash_from_params(params)
    validation = workflow.get("validation") or {}
    sandbox = workflow.get("sandbox") or {}
    if not (validation.get("ok") and validation.get("source_hash") == current_hash):
        raise HTTPException(status_code=400, detail="Publish blocked: run Verify Code successfully for the latest source/config.")
    if not (sandbox.get("ok") and sandbox.get("source_hash") == current_hash):
        raise HTTPException(status_code=400, detail="Publish blocked: run Sandbox Backtest successfully for the latest source/config.")


@router.post("/strategies/{strategy_id}/deploy-private")
async def deploy_private_strategy(
    strategy_id: str,
    admin_user: dict = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    strategy = await _get_strategy_or_404(db, strategy_id)
    params = dict(strategy.parameters or {})
    _ensure_publish_gate(params)
    await _ensure_default_runtime_preset(db, strategy, admin_user)
    strategy.visibility = PRIVATE_VISIBILITY
    strategy.published_by = None
    strategy.lifecycle_status = "PRIVATE_DEPLOYED"

    if getattr(strategy, "source_request_id", None):
        req = await _get_request_or_404(db, str(strategy.source_request_id))
        strategy.created_by = as_uuid_or_str(req.user_id)
        req.status = "DEPLOYED"
        req.deployed_strategy_id = str(strategy.id)

    await db.commit()
    await db.refresh(strategy)
    return success_response(_serialize_strategy(strategy), "Strategy deployed privately to requesting user")


@router.post("/strategies/{strategy_id}/publish")
async def publish_strategy(
    strategy_id: str,
    admin_user: dict = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    strategy = await _get_strategy_or_404(db, strategy_id)
    params = dict(strategy.parameters or {})
    _ensure_publish_gate(params)
    await _ensure_default_runtime_preset(db, strategy, admin_user)
    strategy.visibility = PUBLIC_VISIBILITY
    strategy.published_by = as_uuid_or_str(admin_user["user_id"])
    if not getattr(strategy, "lifecycle_status", None) or strategy.lifecycle_status in {"DRAFT", "UNDER_DEVELOPMENT", "VERIFIED", "SANDBOX_PASSED", "PRIVATE", "PRIVATE_DEPLOYED"}:
        strategy.lifecycle_status = "PUBLISHED"

    if getattr(strategy, "source_request_id", None):
        req = await _get_request_or_404(db, str(strategy.source_request_id))
        req.status = "DEPLOYED"
        req.deployed_strategy_id = str(strategy.id)
        if not getattr(strategy, "created_by", None):
            strategy.created_by = as_uuid_or_str(req.user_id)

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
    strategy.is_deployable_paper = False
    strategy.is_deployable_demo = False
    strategy.is_live_approved = False
    strategy.paper_enabled_at = None
    strategy.demo_enabled_at = None
    strategy.live_approved_at = None
    strategy.lifecycle_status = "PRIVATE"

    await db.commit()
    await db.refresh(strategy)

    return success_response(_serialize_strategy(strategy), "Strategy moved to private successfully")


@router.post("/{request_id}/workspace")
async def create_strategy_workspace_from_request(
    request_id: str,
    admin_user: dict = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    req = await _get_request_or_404(db, request_id)

    existing = (
        await db.execute(
            select(Strategy).where(Strategy.source_request_id == req.id)
        )
    ).scalar_one_or_none()

    if existing is None and getattr(req, "deployed_strategy_id", None):
        existing = (
            await db.execute(
                select(Strategy).where(column_text(Strategy.id) == str(req.deployed_strategy_id))
            )
        ).scalar_one_or_none()

    if existing is None:
        strategy = await _upsert_strategy_from_request(db, req, visibility=PRIVATE_VISIBILITY)
        strategy.lifecycle_status = "UNDER_DEVELOPMENT"
        if (getattr(req, "request_kind", None) or "").upper() == "REFINEMENT" and getattr(req, "parent_strategy_id", None):
            parent_strategy = (await db.execute(select(Strategy).where(column_text(Strategy.id) == str(req.parent_strategy_id)))).scalar_one_or_none()
            if parent_strategy and not str(strategy.name).endswith(" V2"):
                strategy.name = f"{parent_strategy.name} V2"
        strategy.created_by = as_uuid_or_str(req.user_id)
        strategy.published_by = None
        req.deployed_strategy_id = str(strategy.id)
        req.status = "UNDER_DEVELOPMENT"
        await _ensure_default_runtime_preset(db, strategy, admin_user)
    else:
        strategy = existing
        if not getattr(strategy, "source_request_id", None):
            strategy.source_request_id = as_uuid_or_str(req.id)
        if not getattr(strategy, "created_by", None):
            strategy.created_by = as_uuid_or_str(req.user_id)
        if not getattr(strategy, "visibility", None):
            strategy.visibility = PRIVATE_VISIBILITY
        if not getattr(strategy, "lifecycle_status", None) or strategy.lifecycle_status == "PRIVATE":
            strategy.lifecycle_status = "UNDER_DEVELOPMENT"
        req.deployed_strategy_id = str(strategy.id)
        if req.status != "DEPLOYED":
            req.status = "UNDER_DEVELOPMENT"
        await _ensure_default_runtime_preset(db, strategy, admin_user)

    await db.commit()
    await db.refresh(req)
    await db.refresh(strategy)

    attachments = (await _load_request_attachments(db, [req.id])).get(str(req.id), [])
    user_row = (await db.execute(select(User.email, User.fullname).where(User.id == req.user_id))).first()
    email = user_row[0] if user_row else None
    fullname = user_row[1] if user_row else None
    data = _serialize_strategy(strategy)
    data["attachments"] = attachments
    data["source_request"] = _serialize_request(req, email, fullname, attachments)
    data["sourceRequest"] = data["source_request"]
    return success_response({"request": data["source_request"], "strategy": data}, "Strategy workspace is ready")


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
    attachment_map = await _load_request_attachments(db, [req.id])
    data = _serialize_request(req, email, fullname, attachment_map.get(str(req.id), []))
    linked_strategy = (
        await db.execute(
            select(Strategy).where(Strategy.source_request_id == req.id)
        )
    ).scalar_one_or_none()
    if linked_strategy:
        data["deployed_strategy_id"] = str(linked_strategy.id)
        data["deployedStrategyId"] = str(linked_strategy.id)
        data["linked_strategy_id"] = str(linked_strategy.id)
        data["linkedStrategyId"] = str(linked_strategy.id)
    if getattr(req, "parent_strategy_id", None):
        parent_strategy = (await db.execute(select(Strategy).where(column_text(Strategy.id) == str(req.parent_strategy_id)))).scalar_one_or_none()
        if parent_strategy:
            data["original_strategy"] = {"id": str(parent_strategy.id), "name": parent_strategy.name, "visibility": parent_strategy.visibility}
            data["originalStrategy"] = data["original_strategy"]
            data["original_strategy_name"] = parent_strategy.name
            data["originalStrategyName"] = parent_strategy.name
    if getattr(req, "parent_request_id", None):
        parent_request = (await db.execute(select(StrategyRequest).where(column_text(StrategyRequest.id) == str(req.parent_request_id)))).scalar_one_or_none()
        if parent_request:
            data["original_request"] = {"id": str(parent_request.id), "title": parent_request.title, "status": parent_request.status}
            data["originalRequest"] = data["original_request"]
    data["workspace_status"] = _workspace_status_for_strategy(linked_strategy, req)
    data["workspaceStatus"] = data["workspace_status"]
    return success_response(data)


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
        attachment_map = await _load_request_attachments(db, [req2.id])
        return success_response(_serialize_request(req2, email, fullname, attachment_map.get(str(req2.id), [])), "Strategy request updated successfully")

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
        elif (getattr(req, "request_kind", None) or "").upper() == "REFINEMENT" and getattr(req, "parent_strategy_id", None):
            parent_strategy = (await db.execute(select(Strategy).where(column_text(Strategy.id) == str(req.parent_strategy_id)))).scalar_one_or_none()
            if parent_strategy and str(strategy.name).startswith("Refinement:"):
                strategy.name = f"{parent_strategy.name} V2"
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
        {"request": _serialize_request(req, attachments=(await _load_request_attachments(db, [req.id])).get(str(req.id), [])), "strategy": _serialize_strategy(strategy)},
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


class StrategyDeploymentGateIn(BaseModel):
    is_deployable_paper: Optional[bool] = None
    is_deployable_demo: Optional[bool] = None
    is_live_approved: Optional[bool] = None
    reason: Optional[str] = None


@router.post("/strategies/{strategy_id}/deployment-gate")
async def update_strategy_deployment_gate(
    strategy_id: str,
    payload: StrategyDeploymentGateIn,
    admin_user: dict = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    strategy = await _get_strategy_or_404(db, strategy_id)
    now = datetime.now(timezone.utc)
    params = dict(strategy.parameters or {})

    previous = {
        "is_deployable_paper": bool(getattr(strategy, "is_deployable_paper", False)),
        "is_deployable_demo": bool(getattr(strategy, "is_deployable_demo", False)),
        "is_live_approved": bool(getattr(strategy, "is_live_approved", False)),
    }

    params = _append_version_history(params, strategy, admin_user, reason="deployment_gate")
    gate_history = list(params.get("_deployment_gate_history") or [])

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

    gate_history.insert(0, {
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
    params["_deployment_gate_history"] = gate_history[:50]
    strategy.parameters = params

    await db.commit()
    await db.refresh(strategy)
    return success_response(_serialize_strategy(strategy), "Deployment gate updated")
