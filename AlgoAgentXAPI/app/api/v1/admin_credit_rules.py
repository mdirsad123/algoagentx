from __future__ import annotations

from typing import Any, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_admin_user, get_db
from app.services.billing.credit_cost_service import CreditCostService

router = APIRouter()


def _upper(value: Optional[str]) -> Optional[str]:
    text_value = str(value or "").strip().upper()
    return text_value or None


def serialize_rule(row: Any) -> dict[str, Any]:
    data = dict(row)
    for key in ["id"]:
        if data.get(key) is not None:
            data[key] = str(data[key])
    for key in ["per_1000_candles_credits", "advanced_filter_multiplier"]:
        if data.get(key) is not None:
            data[key] = float(data[key])
    for key in ["created_at", "updated_at"]:
        if data.get(key) is not None:
            data[key] = data[key].isoformat()
    return data


class CreditRulePayload(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    operation_type: str = Field(default="BACKTEST")
    market: Optional[str] = None
    instrument_symbol: Optional[str] = Field(default=None, max_length=80)
    timeframe: Optional[str] = Field(default=None, max_length=40)
    base_credits: int = Field(default=1, ge=0)
    per_1000_candles_credits: float = Field(default=1, ge=0)
    min_credits: int = Field(default=1, ge=0)
    max_credits: Optional[int] = Field(default=None, ge=0)
    advanced_filter_multiplier: float = Field(default=1, gt=0)
    is_active: bool = True
    priority: int = Field(default=100, ge=1)

    @field_validator("operation_type", "market", "instrument_symbol", "timeframe")
    @classmethod
    def normalize_upper(cls, value: Optional[str]) -> Optional[str]:
        return _upper(value)

    @model_validator(mode="after")
    def validate_rule(self):
        if self.operation_type not in {"BACKTEST", "AI_SCREENER", "LIVE_DEPLOYMENT", "OTHER"}:
            raise ValueError("Invalid operation type")
        if self.market and self.market not in {"FOREX", "INDIAN", "CRYPTO", "ALL"}:
            raise ValueError("Invalid market")
        if self.max_credits is not None and self.max_credits < self.min_credits:
            raise ValueError("Max credits must be greater than or equal to min credits")
        return self


class CreditRuleStatusPayload(BaseModel):
    is_active: bool


@router.get("")
async def list_credit_rules(
    search: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _admin: dict = Depends(get_admin_user),
):
    await CreditCostService.ensure_table(db)
    params: dict[str, Any] = {}
    where = ""
    if search:
        params["search"] = f"%{search.strip()}%"
        where = "WHERE name ILIKE :search OR COALESCE(instrument_symbol, '') ILIKE :search OR COALESCE(timeframe, '') ILIKE :search"
    rows = (await db.execute(text(f"""
        SELECT *
        FROM billing_credit_expense_rules
        {where}
        ORDER BY is_active DESC, priority ASC, updated_at DESC
    """), params)).mappings().all()
    await db.commit()
    return {"items": [serialize_rule(row) for row in rows], "total": len(rows)}


@router.post("")
async def create_credit_rule(
    payload: CreditRulePayload,
    db: AsyncSession = Depends(get_db),
    _admin: dict = Depends(get_admin_user),
):
    await CreditCostService.ensure_table(db)
    data = payload.model_dump()
    data["name"] = data["name"].strip()
    row = (await db.execute(text("""
        INSERT INTO billing_credit_expense_rules (
            id, name, operation_type, market, instrument_symbol, timeframe,
            base_credits, per_1000_candles_credits, min_credits, max_credits,
            advanced_filter_multiplier, is_active, priority, created_at, updated_at
        ) VALUES (
            :id, :name, :operation_type, :market, :instrument_symbol, :timeframe,
            :base_credits, :per_1000_candles_credits, :min_credits, :max_credits,
            :advanced_filter_multiplier, :is_active, :priority, NOW(), NOW()
        ) RETURNING *
    """), {"id": str(uuid4()), **data})).mappings().first()
    await db.commit()
    return serialize_rule(row)


@router.put("/{rule_id}")
async def update_credit_rule(
    rule_id: str,
    payload: CreditRulePayload,
    db: AsyncSession = Depends(get_db),
    _admin: dict = Depends(get_admin_user),
):
    await CreditCostService.ensure_table(db)
    data = payload.model_dump()
    data["id"] = rule_id
    data["name"] = data["name"].strip()
    row = (await db.execute(text("""
        UPDATE billing_credit_expense_rules
        SET name = :name,
            operation_type = :operation_type,
            market = :market,
            instrument_symbol = :instrument_symbol,
            timeframe = :timeframe,
            base_credits = :base_credits,
            per_1000_candles_credits = :per_1000_candles_credits,
            min_credits = :min_credits,
            max_credits = :max_credits,
            advanced_filter_multiplier = :advanced_filter_multiplier,
            is_active = :is_active,
            priority = :priority,
            updated_at = NOW()
        WHERE id::text = :id
        RETURNING *
    """), data)).mappings().first()
    if not row:
        await db.rollback()
        raise HTTPException(status_code=404, detail="Credit rule not found")
    await db.commit()
    return serialize_rule(row)


@router.patch("/{rule_id}/status")
async def update_credit_rule_status(
    rule_id: str,
    payload: CreditRuleStatusPayload,
    db: AsyncSession = Depends(get_db),
    _admin: dict = Depends(get_admin_user),
):
    await CreditCostService.ensure_table(db)
    row = (await db.execute(text("""
        UPDATE billing_credit_expense_rules
        SET is_active = :is_active, updated_at = NOW()
        WHERE id::text = :id
        RETURNING *
    """), {"id": rule_id, "is_active": payload.is_active})).mappings().first()
    if not row:
        await db.rollback()
        raise HTTPException(status_code=404, detail="Credit rule not found")
    await db.commit()
    return serialize_rule(row)
