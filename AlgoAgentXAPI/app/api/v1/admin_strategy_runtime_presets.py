from __future__ import annotations

from typing import Any, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.dependencies import get_admin_user, get_db
from ...db.compat import as_uuid_or_str, column_text
from ...db.models.strategies import Strategy, StrategyRuntimePreset
from ...services.trading.runtime_config_service import validate_runtime_config
from ...utils.api_response import success_response

router = APIRouter()


class PresetIn(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = None
    config_json: Optional[dict[str, Any]] = None
    configJson: Optional[dict[str, Any]] = None
    risk_label: Optional[str] = Field(default=None, max_length=100)
    riskLabel: Optional[str] = Field(default=None, max_length=100)
    is_default: Optional[bool] = False
    isDefault: Optional[bool] = False
    is_active: Optional[bool] = True
    isActive: Optional[bool] = True


class PresetPatchIn(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    description: Optional[str] = None
    config_json: Optional[dict[str, Any]] = None
    configJson: Optional[dict[str, Any]] = None
    risk_label: Optional[str] = Field(default=None, max_length=100)
    riskLabel: Optional[str] = Field(default=None, max_length=100)
    is_default: Optional[bool] = None
    isDefault: Optional[bool] = None
    is_active: Optional[bool] = None
    isActive: Optional[bool] = None


def _dt(v: Any) -> Optional[str]:
    return v.isoformat() if v else None


def _config(payload: Any) -> dict[str, Any]:
    raw = getattr(payload, "config_json", None)
    if raw is None:
        raw = getattr(payload, "configJson", None)
    validation = validate_runtime_config(raw or {})
    if not validation["valid"]:
        raise HTTPException(status_code=400, detail={"message": "Invalid runtime preset config", "errors": validation["errors"]})
    return validation["config"]


def _risk_label(payload: Any) -> Optional[str]:
    value = getattr(payload, "risk_label", None)
    if value is None:
        value = getattr(payload, "riskLabel", None)
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def _serialize(row: StrategyRuntimePreset) -> dict[str, Any]:
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
        "created_at": _dt(row.created_at),
        "createdAt": _dt(row.created_at),
        "updated_at": _dt(row.updated_at),
        "updatedAt": _dt(row.updated_at),
    }


async def _strategy_or_404(db: AsyncSession, strategy_id: str) -> Strategy:
    row = (await db.execute(select(Strategy).where(column_text(Strategy.id) == str(strategy_id)))).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return row


@router.get("/strategies/{strategy_id}/runtime-presets")
async def list_presets(strategy_id: str, admin_user: dict = Depends(get_admin_user), db: AsyncSession = Depends(get_db)):
    await _strategy_or_404(db, strategy_id)
    rows = (await db.execute(select(StrategyRuntimePreset).where(StrategyRuntimePreset.strategy_id == str(strategy_id)).order_by(StrategyRuntimePreset.is_default.desc(), StrategyRuntimePreset.is_active.desc(), StrategyRuntimePreset.created_at.asc()))).scalars().all()
    return success_response({"items": [_serialize(r) for r in rows]}, "Runtime presets loaded")


@router.post("/strategies/{strategy_id}/runtime-presets")
async def create_preset(strategy_id: str, payload: PresetIn, admin_user: dict = Depends(get_admin_user), db: AsyncSession = Depends(get_db)):
    await _strategy_or_404(db, strategy_id)
    make_default = bool(payload.is_default if payload.is_default is not None else payload.isDefault)
    if make_default:
        await db.execute(update(StrategyRuntimePreset).where(StrategyRuntimePreset.strategy_id == str(strategy_id)).values(is_default=False))
    row = StrategyRuntimePreset(
        id=str(uuid4()), strategy_id=str(strategy_id), name=payload.name.strip(), description=payload.description,
        config_json=_config(payload), risk_label=_risk_label(payload), is_default=make_default,
        is_active=bool(payload.is_active if payload.is_active is not None else payload.isActive), created_by=as_uuid_or_str(admin_user.get("user_id")),
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return success_response(_serialize(row), "Runtime preset created")


@router.patch("/strategy-runtime-presets/{preset_id}")
async def patch_preset(preset_id: str, payload: PresetPatchIn, admin_user: dict = Depends(get_admin_user), db: AsyncSession = Depends(get_db)):
    row = (await db.execute(select(StrategyRuntimePreset).where(column_text(StrategyRuntimePreset.id) == str(preset_id)))).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Runtime preset not found")
    if payload.name is not None:
        row.name = payload.name.strip()
    if payload.description is not None:
        row.description = payload.description
    if payload.config_json is not None or payload.configJson is not None:
        row.config_json = _config(payload)
    if payload.risk_label is not None or payload.riskLabel is not None:
        row.risk_label = _risk_label(payload)
    active = payload.is_active if payload.is_active is not None else payload.isActive
    if active is not None:
        row.is_active = bool(active)
    default = payload.is_default if payload.is_default is not None else payload.isDefault
    if default is not None:
        if bool(default):
            await db.execute(update(StrategyRuntimePreset).where(StrategyRuntimePreset.strategy_id == row.strategy_id).values(is_default=False))
            row.is_default = True
            row.is_active = True
        else:
            row.is_default = False
    await db.commit()
    await db.refresh(row)
    return success_response(_serialize(row), "Runtime preset updated")


@router.delete("/strategy-runtime-presets/{preset_id}")
async def deactivate_preset(preset_id: str, admin_user: dict = Depends(get_admin_user), db: AsyncSession = Depends(get_db)):
    row = (await db.execute(select(StrategyRuntimePreset).where(column_text(StrategyRuntimePreset.id) == str(preset_id)))).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Runtime preset not found")
    row.is_active = False
    row.is_default = False
    await db.commit()
    await db.refresh(row)
    return success_response(_serialize(row), "Runtime preset deactivated")


@router.post("/strategy-runtime-presets/{preset_id}/make-default")
async def make_default(preset_id: str, admin_user: dict = Depends(get_admin_user), db: AsyncSession = Depends(get_db)):
    row = (await db.execute(select(StrategyRuntimePreset).where(column_text(StrategyRuntimePreset.id) == str(preset_id)))).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Runtime preset not found")
    await db.execute(update(StrategyRuntimePreset).where(StrategyRuntimePreset.strategy_id == row.strategy_id).values(is_default=False))
    row.is_default = True
    row.is_active = True
    await db.commit()
    await db.refresh(row)
    return success_response(_serialize(row), "Runtime preset marked as default")
