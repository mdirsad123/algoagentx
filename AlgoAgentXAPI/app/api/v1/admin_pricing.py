from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.dependencies import get_admin_user, get_db
from ...db.models import Plan, User
from ...utils.api_response import success_response

router = APIRouter()

DEFAULT_FEATURES: dict[str, Any] = {
    "summary": "",
    "daily_backtests": 0,
    "daily_ai_screener_runs": 0,
    "max_date_range_days": 0,
    "export_results": False,
    "advanced_strategies": False,
    "ai_screener_access": False,
    "priority_support": False,
    "dedicated_account_manager": False,
}

STRUCTURED_FEATURE_KEYS = {
    "summary",
    "daily_backtests",
    "daily_ai_screener_runs",
    "max_date_range_days",
    "export_results",
    "advanced_strategies",
    "ai_screener_access",
    "priority_support",
    "dedicated_account_manager",
}


def _normalize_billing_period(value: str) -> str:
    normalized = str(value or "").strip().upper()
    if normalized == "ANNUAL":
        return "YEARLY"
    return normalized


def _to_int(value: Any, default: int = 0) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        try:
            return int(float(value.strip()))
        except Exception:
            return default
    return default


def _to_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value > 0
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "included", "enabled"}:
            return True
        if normalized in {"0", "false", "no", "disabled", "not_included"}:
            return False
    return default


def _extract_structured_features(features: dict[str, Any] | None) -> dict[str, Any]:
    source = features or {}
    return {
        "summary": str(source.get("summary") or "").strip(),
        "daily_backtests": max(0, _to_int(source.get("daily_backtests"), default=0)),
        "daily_ai_screener_runs": max(0, _to_int(source.get("daily_ai_screener_runs"), default=0)),
        "max_date_range_days": max(0, _to_int(source.get("max_date_range_days"), default=0)),
        "export_results": _to_bool(source.get("export_results"), default=False),
        "advanced_strategies": _to_bool(source.get("advanced_strategies"), default=False),
        "ai_screener_access": _to_bool(source.get("ai_screener_access"), default=False),
        "priority_support": _to_bool(source.get("priority_support"), default=False),
        "dedicated_account_manager": _to_bool(source.get("dedicated_account_manager"), default=False),
    }


class PlanCreateRequest(BaseModel):
    code: str = Field(..., min_length=2, max_length=50)
    billing_period: str = Field(..., min_length=2, max_length=20)
    price_inr: int = Field(..., ge=0)
    included_credits: int = Field(..., ge=0)

    summary: str = Field(default="", max_length=500)
    daily_backtests: int = Field(default=0, ge=0)
    daily_ai_screener_runs: int = Field(default=0, ge=0)
    max_date_range_days: int = Field(default=0, ge=0)
    export_results: bool = False
    advanced_strategies: bool = False
    ai_screener_access: bool = False
    priority_support: bool = False
    dedicated_account_manager: bool = False

    features: Optional[dict[str, Any]] = None
    is_active: bool = True

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return str(value or "").strip().upper()

    @field_validator("billing_period")
    @classmethod
    def normalize_period(cls, value: str) -> str:
        return _normalize_billing_period(value)


class PlanUpdateRequest(BaseModel):
    code: Optional[str] = Field(default=None, min_length=2, max_length=50)
    billing_period: Optional[str] = Field(default=None, min_length=2, max_length=20)
    price_inr: Optional[int] = Field(default=None, ge=0)
    included_credits: Optional[int] = Field(default=None, ge=0)

    summary: Optional[str] = Field(default=None, max_length=500)
    daily_backtests: Optional[int] = Field(default=None, ge=0)
    daily_ai_screener_runs: Optional[int] = Field(default=None, ge=0)
    max_date_range_days: Optional[int] = Field(default=None, ge=0)
    export_results: Optional[bool] = None
    advanced_strategies: Optional[bool] = None
    ai_screener_access: Optional[bool] = None
    priority_support: Optional[bool] = None
    dedicated_account_manager: Optional[bool] = None

    features: Optional[dict[str, Any]] = None
    is_active: Optional[bool] = None

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        return str(value or "").strip().upper()

    @field_validator("billing_period")
    @classmethod
    def normalize_period(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        return _normalize_billing_period(value)


def _build_features_payload(
    *,
    request_payload: PlanCreateRequest | PlanUpdateRequest,
    fields_set: set[str],
    existing_features: dict[str, Any] | None,
    force_all_structured_fields: bool,
) -> dict[str, Any]:
    features: dict[str, Any] = dict(existing_features or {})

    if request_payload.features is not None:
        features.update(request_payload.features)

    structured_fields: dict[str, Any] = {
        "summary": request_payload.summary,
        "daily_backtests": request_payload.daily_backtests,
        "daily_ai_screener_runs": request_payload.daily_ai_screener_runs,
        "max_date_range_days": request_payload.max_date_range_days,
        "export_results": request_payload.export_results,
        "advanced_strategies": request_payload.advanced_strategies,
        "ai_screener_access": request_payload.ai_screener_access,
        "priority_support": request_payload.priority_support,
        "dedicated_account_manager": request_payload.dedicated_account_manager,
    }

    for key, value in structured_fields.items():
        if force_all_structured_fields or key in fields_set:
            if value is None:
                continue
            features[key] = value

    if not features:
        features.update(DEFAULT_FEATURES)

    normalized_structured = _extract_structured_features(features)
    for key, value in normalized_structured.items():
        features[key] = value

    return features


def _serialize_plan(plan: Plan) -> dict[str, Any]:
    features = plan.features or {}
    structured = _extract_structured_features(features)
    return {
        "id": str(plan.id),
        "code": str(plan.code or "").upper(),
        "billing_period": _normalize_billing_period(str(plan.billing_period or "")),
        "price_inr": int(plan.price_inr or 0),
        "included_credits": int(plan.included_credits or 0),
        "summary": structured["summary"],
        "daily_backtests": structured["daily_backtests"],
        "daily_ai_screener_runs": structured["daily_ai_screener_runs"],
        "max_date_range_days": structured["max_date_range_days"],
        "export_results": structured["export_results"],
        "advanced_strategies": structured["advanced_strategies"],
        "ai_screener_access": structured["ai_screener_access"],
        "priority_support": structured["priority_support"],
        "dedicated_account_manager": structured["dedicated_account_manager"],
        "features": features,
        "is_active": bool(plan.is_active),
        "created_at": plan.created_at.isoformat() if getattr(plan, "created_at", None) else None,
    }


def _validate_plan_combo(code: str, billing_period: str) -> None:
    if code == "FREE" and billing_period != "NONE":
        raise HTTPException(status_code=400, detail="FREE plan must use billing_period NONE")
    if code != "FREE" and billing_period not in {"MONTHLY", "YEARLY"}:
        raise HTTPException(status_code=400, detail="Paid plans must use MONTHLY or YEARLY billing period")


@router.get("/plans")
@router.get("/pricing/plans")
async def list_pricing_plans(
    _current_admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Plan).order_by(func.upper(Plan.code).asc(), func.upper(Plan.billing_period).asc()))
    items = [_serialize_plan(plan) for plan in result.scalars().all()]
    return success_response(items)


@router.post("/plans")
@router.post("/pricing/plans")
async def create_pricing_plan(
    payload: PlanCreateRequest,
    _current_admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    _validate_plan_combo(payload.code, payload.billing_period)

    existing = (
        await db.execute(
            select(Plan)
            .where(
                func.upper(Plan.code) == payload.code,
                func.upper(Plan.billing_period) == payload.billing_period,
            )
            .limit(1)
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Plan with this code and billing period already exists")

    features = _build_features_payload(
        request_payload=payload,
        fields_set=set(payload.model_fields_set),
        existing_features=None,
        force_all_structured_fields=False,
    )

    plan = Plan(
        code=payload.code,
        billing_period=payload.billing_period,
        price_inr=int(payload.price_inr),
        included_credits=int(payload.included_credits),
        features=features,
        is_active=bool(payload.is_active),
    )
    db.add(plan)
    await db.commit()
    await db.refresh(plan)
    return success_response(_serialize_plan(plan), message="Plan created successfully")


@router.patch("/plans/{plan_id}")
@router.patch("/pricing/plans/{plan_id}")
async def update_pricing_plan(
    plan_id: str,
    payload: PlanUpdateRequest,
    _current_admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    plan = (await db.execute(select(Plan).where(Plan.id == plan_id).limit(1))).scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    next_code = payload.code if payload.code is not None else str(plan.code or "").upper()
    next_period = payload.billing_period if payload.billing_period is not None else _normalize_billing_period(str(plan.billing_period or ""))
    _validate_plan_combo(next_code, next_period)

    duplicate = (
        await db.execute(
            select(Plan)
            .where(
                Plan.id != plan.id,
                func.upper(Plan.code) == next_code,
                func.upper(Plan.billing_period) == next_period,
            )
            .limit(1)
        )
    ).scalar_one_or_none()
    if duplicate:
        raise HTTPException(status_code=409, detail="Another plan already exists with this code and billing period")

    if payload.code is not None:
        plan.code = next_code
    if payload.billing_period is not None:
        plan.billing_period = next_period
    if payload.price_inr is not None:
        plan.price_inr = int(payload.price_inr)
    if payload.included_credits is not None:
        plan.included_credits = int(payload.included_credits)

    fields_set = set(payload.model_fields_set)
    has_structured_update = any(field in fields_set for field in STRUCTURED_FEATURE_KEYS)
    if payload.features is not None or has_structured_update:
        plan.features = _build_features_payload(
            request_payload=payload,
            fields_set=fields_set,
            existing_features=plan.features,
            force_all_structured_fields=False,
        )

    if payload.is_active is not None:
        plan.is_active = bool(payload.is_active)

    await db.commit()
    await db.refresh(plan)
    return success_response(_serialize_plan(plan), message="Plan updated successfully")
