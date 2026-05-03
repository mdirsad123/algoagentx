from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.dependencies import get_admin_user, get_db
from ...db.compat import as_uuid_or_str, column_text
from ...db.models.strategies import Strategy, StrategyRuntimePreset
from ...services.trading.runtime_config_service import (
    get_default_runtime_config_schema,
    get_system_default_runtime_config,
    normalize_runtime_config,
    validate_runtime_config,
)
from ...utils.api_response import success_response

router = APIRouter()


class StrategyRuntimeConfigUpdateIn(BaseModel):
    default_runtime_config: Optional[dict[str, Any]] = Field(default=None)
    defaultRuntimeConfig: Optional[dict[str, Any]] = Field(default=None)
    runtime_config_schema: Optional[dict[str, Any]] = Field(default=None)
    runtimeConfigSchema: Optional[dict[str, Any]] = Field(default=None)
    supports_runtime_config: Optional[bool] = None
    supportsRuntimeConfig: Optional[bool] = None
    config_version: Optional[int] = None
    configVersion: Optional[int] = None




class StrategyRuntimePresetIn(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = None
    config_json: Optional[dict[str, Any]] = Field(default=None)
    configJson: Optional[dict[str, Any]] = Field(default=None)
    risk_label: Optional[str] = Field(default=None, max_length=100)
    riskLabel: Optional[str] = Field(default=None, max_length=100)
    is_default: Optional[bool] = False
    isDefault: Optional[bool] = False
    is_active: Optional[bool] = True
    isActive: Optional[bool] = True


class StrategyRuntimePresetPatchIn(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    description: Optional[str] = None
    config_json: Optional[dict[str, Any]] = Field(default=None)
    configJson: Optional[dict[str, Any]] = Field(default=None)
    risk_label: Optional[str] = Field(default=None, max_length=100)
    riskLabel: Optional[str] = Field(default=None, max_length=100)
    is_default: Optional[bool] = None
    isDefault: Optional[bool] = None
    is_active: Optional[bool] = None
    isActive: Optional[bool] = None

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
        "default_runtime_config": getattr(strategy, "default_runtime_config", None) or {},
        "defaultRuntimeConfig": getattr(strategy, "default_runtime_config", None) or {},
        "runtime_config_schema": getattr(strategy, "runtime_config_schema", None) or {},
        "runtimeConfigSchema": getattr(strategy, "runtime_config_schema", None) or {},
        "supports_runtime_config": bool(getattr(strategy, "supports_runtime_config", True)),
        "supportsRuntimeConfig": bool(getattr(strategy, "supports_runtime_config", True)),
        "config_version": int(getattr(strategy, "config_version", 1) or 1),
        "configVersion": int(getattr(strategy, "config_version", 1) or 1),
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




def _preset_config_from_payload(payload: Any) -> dict[str, Any]:
    config = getattr(payload, "config_json", None)
    if config is None:
        config = getattr(payload, "configJson", None)
    validation = validate_runtime_config(config or {})
    if not validation["valid"]:
        raise HTTPException(status_code=400, detail={"message": "Invalid runtime preset config", "errors": validation["errors"]})
    return validation["config"]


def _preset_risk_label_from_payload(payload: Any) -> Optional[str]:
    value = getattr(payload, "risk_label", None)
    if value is None:
        value = getattr(payload, "riskLabel", None)
    if value is None:
        return None
    value = str(value).strip()
    return value or None


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
        "created_by": str(row.created_by) if row.created_by else None,
        "createdBy": str(row.created_by) if row.created_by else None,
        "created_at": _serialize_dt(row.created_at),
        "createdAt": _serialize_dt(row.created_at),
        "updated_at": _serialize_dt(row.updated_at),
        "updatedAt": _serialize_dt(row.updated_at),
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


@router.patch("/{strategy_id}/runtime-config")
async def update_strategy_runtime_config(
    strategy_id: str,
    payload: StrategyRuntimeConfigUpdateIn,
    admin_user: dict = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    strategy = await _get_strategy_or_404(db, strategy_id)

    incoming_default = payload.default_runtime_config if payload.default_runtime_config is not None else payload.defaultRuntimeConfig
    incoming_schema = payload.runtime_config_schema if payload.runtime_config_schema is not None else payload.runtimeConfigSchema
    supports = payload.supports_runtime_config if payload.supports_runtime_config is not None else payload.supportsRuntimeConfig
    version = payload.config_version if payload.config_version is not None else payload.configVersion

    if incoming_default is not None:
        validation = validate_runtime_config(incoming_default)
        if not validation["valid"]:
            raise HTTPException(status_code=400, detail={"message": "Invalid runtime config", "errors": validation["errors"]})
        strategy.default_runtime_config = validation["config"]
    elif strategy.default_runtime_config is None:
        strategy.default_runtime_config = normalize_runtime_config(get_system_default_runtime_config())

    if incoming_schema is not None:
        strategy.runtime_config_schema = incoming_schema
    elif strategy.runtime_config_schema is None:
        hint = " ".join([str(strategy.name or ""), str((strategy.parameters or {}).get("strategy_type") if isinstance(strategy.parameters, dict) else "")])
        strategy.runtime_config_schema = get_default_runtime_config_schema(hint)

    if supports is not None:
        strategy.supports_runtime_config = bool(supports)
    if version is not None:
        strategy.config_version = max(1, int(version))

    params = dict(strategy.parameters or {})
    history = list(params.get("_runtime_config_history") or [])
    history.insert(0, {
        "changed_at": datetime.now(timezone.utc).isoformat(),
        "admin_user_id": str(admin_user.get("user_id")),
        "config_version": int(strategy.config_version or 1),
        "supports_runtime_config": bool(strategy.supports_runtime_config),
    })
    params["_runtime_config_history"] = history[:50]
    strategy.parameters = params

    await db.commit()
    await db.refresh(strategy)

    return success_response(
        {
            "strategy_id": str(strategy.id),
            "strategyId": str(strategy.id),
            "default_runtime_config": strategy.default_runtime_config or {},
            "defaultRuntimeConfig": strategy.default_runtime_config or {},
            "runtime_config_schema": strategy.runtime_config_schema or {},
            "runtimeConfigSchema": strategy.runtime_config_schema or {},
            "supports_runtime_config": bool(strategy.supports_runtime_config),
            "supportsRuntimeConfig": bool(strategy.supports_runtime_config),
            "config_version": int(strategy.config_version or 1),
            "configVersion": int(strategy.config_version or 1),
        },
        "Strategy runtime config updated",
    )

@router.get("/{strategy_id}/runtime-presets")
async def list_strategy_runtime_presets(
    strategy_id: str,
    admin_user: dict = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_strategy_or_404(db, strategy_id)
    rows = (
        await db.execute(
            select(StrategyRuntimePreset)
            .where(StrategyRuntimePreset.strategy_id == str(strategy_id))
            .order_by(StrategyRuntimePreset.is_default.desc(), StrategyRuntimePreset.is_active.desc(), StrategyRuntimePreset.created_at.asc())
        )
    ).scalars().all()
    return success_response({"items": [_serialize_runtime_preset(row) for row in rows]}, "Runtime presets loaded")


@router.post("/{strategy_id}/runtime-presets")
async def create_strategy_runtime_preset(
    strategy_id: str,
    payload: StrategyRuntimePresetIn,
    admin_user: dict = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_strategy_or_404(db, strategy_id)
    config = _preset_config_from_payload(payload)
    make_default = bool(payload.is_default if payload.is_default is not None else payload.isDefault)
    if make_default:
        await db.execute(update(StrategyRuntimePreset).where(StrategyRuntimePreset.strategy_id == str(strategy_id)).values(is_default=False))
    row = StrategyRuntimePreset(
        id=str(uuid4()),
        strategy_id=str(strategy_id),
        name=payload.name.strip(),
        description=payload.description,
        config_json=config,
        risk_label=_preset_risk_label_from_payload(payload),
        is_default=make_default,
        is_active=bool(payload.is_active if payload.is_active is not None else payload.isActive),
        created_by=as_uuid_or_str(admin_user.get("user_id")),
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return success_response(_serialize_runtime_preset(row), "Runtime preset created")


@router.patch("/runtime-presets/{preset_id}")
async def update_strategy_runtime_preset(
    preset_id: str,
    payload: StrategyRuntimePresetPatchIn,
    admin_user: dict = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    row = (await db.execute(select(StrategyRuntimePreset).where(column_text(StrategyRuntimePreset.id) == str(preset_id)))).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Runtime preset not found")
    if payload.name is not None:
        row.name = payload.name.strip()
    if payload.description is not None:
        row.description = payload.description
    if payload.config_json is not None or payload.configJson is not None:
        row.config_json = _preset_config_from_payload(payload)
    if payload.risk_label is not None or payload.riskLabel is not None:
        row.risk_label = _preset_risk_label_from_payload(payload)
    active_value = payload.is_active if payload.is_active is not None else payload.isActive
    if active_value is not None:
        row.is_active = bool(active_value)
    default_value = payload.is_default if payload.is_default is not None else payload.isDefault
    if default_value is not None:
        if bool(default_value):
            await db.execute(update(StrategyRuntimePreset).where(StrategyRuntimePreset.strategy_id == row.strategy_id).values(is_default=False))
            row.is_default = True
            row.is_active = True
        else:
            row.is_default = False
    await db.commit()
    await db.refresh(row)
    return success_response(_serialize_runtime_preset(row), "Runtime preset updated")


@router.delete("/runtime-presets/{preset_id}")
async def deactivate_strategy_runtime_preset(
    preset_id: str,
    admin_user: dict = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    row = (await db.execute(select(StrategyRuntimePreset).where(column_text(StrategyRuntimePreset.id) == str(preset_id)))).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Runtime preset not found")
    row.is_active = False
    row.is_default = False
    await db.commit()
    await db.refresh(row)
    return success_response(_serialize_runtime_preset(row), "Runtime preset deactivated")


@router.post("/runtime-presets/{preset_id}/make-default")
async def make_strategy_runtime_preset_default(
    preset_id: str,
    admin_user: dict = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    row = (await db.execute(select(StrategyRuntimePreset).where(column_text(StrategyRuntimePreset.id) == str(preset_id)))).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Runtime preset not found")
    await db.execute(update(StrategyRuntimePreset).where(StrategyRuntimePreset.strategy_id == row.strategy_id).values(is_default=False))
    row.is_default = True
    row.is_active = True
    await db.commit()
    await db.refresh(row)
    return success_response(_serialize_runtime_preset(row), "Runtime preset marked as default")

