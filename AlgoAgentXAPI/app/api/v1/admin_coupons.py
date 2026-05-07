from __future__ import annotations

from typing import Any, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_admin_user, get_db
from app.services.billing.coupon_service import ensure_coupon_tables, serialize_coupon, validate_coupon_payload

router = APIRouter()


class CouponPayload(BaseModel):
    code: str = Field(..., min_length=1, max_length=80)
    description: Optional[str] = Field(default=None, max_length=500)
    discount_type: str = Field(default="PERCENT")
    discount_value: float = Field(..., gt=0)
    applies_to: str = Field(default="ALL")
    plan_code: Optional[str] = Field(default=None, max_length=50)
    billing_period: Optional[str] = Field(default=None, max_length=20)
    min_order_usd: Optional[float] = Field(default=None, ge=0)
    max_discount_usd: Optional[float] = Field(default=None, ge=0)
    max_redemptions: Optional[int] = Field(default=None, gt=0)
    per_user_limit: Optional[int] = Field(default=1, gt=0)
    starts_at: Optional[str] = None
    expires_at: Optional[str] = None
    is_active: bool = True

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        code = str(value or "").strip().upper()
        if not code:
            raise ValueError("Coupon code is required")
        if any(ch.isspace() for ch in code):
            raise ValueError("Coupon code cannot contain spaces")
        return code

    @field_validator("discount_type", "applies_to", "plan_code", "billing_period")
    @classmethod
    def upper_optional(cls, value: Optional[str]) -> Optional[str]:
        return str(value or "").strip().upper() or None


class CouponUpdatePayload(BaseModel):
    code: Optional[str] = Field(default=None, max_length=80)
    description: Optional[str] = Field(default=None, max_length=500)
    discount_type: Optional[str] = None
    discount_value: Optional[float] = Field(default=None, gt=0)
    applies_to: Optional[str] = None
    plan_code: Optional[str] = Field(default=None, max_length=50)
    billing_period: Optional[str] = Field(default=None, max_length=20)
    min_order_usd: Optional[float] = Field(default=None, ge=0)
    max_discount_usd: Optional[float] = Field(default=None, ge=0)
    max_redemptions: Optional[int] = Field(default=None, gt=0)
    per_user_limit: Optional[int] = Field(default=None, gt=0)
    starts_at: Optional[str] = None
    expires_at: Optional[str] = None
    is_active: Optional[bool] = None

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        code = str(value or "").strip().upper()
        if not code:
            raise ValueError("Coupon code is required")
        if any(ch.isspace() for ch in code):
            raise ValueError("Coupon code cannot contain spaces")
        return code

    @field_validator("discount_type", "applies_to", "plan_code", "billing_period")
    @classmethod
    def upper_optional(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        return str(value or "").strip().upper() or None


class CouponStatusPayload(BaseModel):
    is_active: bool


@router.get("")
async def list_coupons(
    search: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _admin: dict = Depends(get_admin_user),
):
    await ensure_coupon_tables(db)
    where = ""
    params: dict[str, Any] = {}
    if search:
        where = "WHERE UPPER(code) LIKE :search OR COALESCE(description, '') ILIKE :search_like"
        params = {"search": f"%{search.strip().upper()}%", "search_like": f"%{search.strip()}%"}
    rows = (await db.execute(text(f"""
        SELECT c.*,
               COALESCE(r.redemption_count, 0) AS redemption_count,
               COALESCE(r.total_discount_usd, 0) AS total_discount_usd,
               r.last_used_at AS last_used_at
        FROM billing_coupons c
        LEFT JOIN (
            SELECT coupon_id, COUNT(*) AS redemption_count, COALESCE(SUM(discount_usd), 0) AS total_discount_usd, MAX(redeemed_at) AS last_used_at
            FROM billing_coupon_redemptions
            GROUP BY coupon_id
        ) r ON r.coupon_id = c.id
        {where}
        ORDER BY c.created_at DESC
    """), params)).mappings().all()
    await db.commit()
    return {"items": [serialize_coupon(row) for row in rows], "total": len(rows)}


@router.post("")
async def create_coupon(
    payload: CouponPayload,
    db: AsyncSession = Depends(get_db),
    _admin: dict = Depends(get_admin_user),
):
    try:
        await ensure_coupon_tables(db)
        data = validate_coupon_payload(payload.model_dump(), partial=False)
        row = (await db.execute(text("""
            INSERT INTO billing_coupons (
                id, code, description, discount_type, discount_value, applies_to, plan_code,
                billing_period, min_order_usd, max_discount_usd, max_redemptions,
                per_user_limit, starts_at, expires_at, is_active, created_at, updated_at
            ) VALUES (
                :id, :code, :description, :discount_type, :discount_value, :applies_to, :plan_code,
                :billing_period, :min_order_usd, :max_discount_usd, :max_redemptions,
                :per_user_limit, :starts_at, :expires_at, :is_active, NOW(), NOW()
            ) RETURNING *
        """), {"id": str(uuid4()), **data})).mappings().first()
        await db.commit()
        return serialize_coupon(row)
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        await db.rollback()
        if "unique" in str(exc).lower():
            raise HTTPException(status_code=409, detail="Coupon code already exists")
        raise HTTPException(status_code=500, detail=f"Failed to create coupon: {exc}")


@router.get("/{coupon_id}")
async def get_coupon(
    coupon_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: dict = Depends(get_admin_user),
):
    await ensure_coupon_tables(db)
    row = (await db.execute(text("SELECT * FROM billing_coupons WHERE id::text = :id LIMIT 1"), {"id": coupon_id})).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Coupon not found")
    return serialize_coupon(row)


@router.put("/{coupon_id}")
async def update_coupon(
    coupon_id: str,
    payload: CouponUpdatePayload,
    db: AsyncSession = Depends(get_db),
    _admin: dict = Depends(get_admin_user),
):
    try:
        await ensure_coupon_tables(db)
        existing = (await db.execute(text("SELECT * FROM billing_coupons WHERE id::text = :id LIMIT 1"), {"id": coupon_id})).mappings().first()
        if not existing:
            raise HTTPException(status_code=404, detail="Coupon not found")
        raw = payload.model_dump(exclude_unset=True)
        if not raw:
            return serialize_coupon(existing)
        data = validate_coupon_payload(raw, partial=True)
        assignments = ", ".join([f"{key} = :{key}" for key in data.keys()])
        row = (await db.execute(text(f"""
            UPDATE billing_coupons
            SET {assignments}, updated_at = NOW()
            WHERE id::text = :id
            RETURNING *
        """), {"id": coupon_id, **data})).mappings().first()
        await db.commit()
        return serialize_coupon(row)
    except HTTPException:
        raise
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        await db.rollback()
        if "unique" in str(exc).lower():
            raise HTTPException(status_code=409, detail="Coupon code already exists")
        raise HTTPException(status_code=500, detail=f"Failed to update coupon: {exc}")


@router.patch("/{coupon_id}/status")
async def update_coupon_status(
    coupon_id: str,
    payload: CouponStatusPayload,
    db: AsyncSession = Depends(get_db),
    _admin: dict = Depends(get_admin_user),
):
    await ensure_coupon_tables(db)
    row = (await db.execute(text("""
        UPDATE billing_coupons
        SET is_active = :is_active, updated_at = NOW()
        WHERE id::text = :id
        RETURNING *
    """), {"id": coupon_id, "is_active": payload.is_active})).mappings().first()
    if not row:
        await db.rollback()
        raise HTTPException(status_code=404, detail="Coupon not found")
    await db.commit()
    return serialize_coupon(row)
