from __future__ import annotations

from typing import Any, Optional
from uuid import UUID, uuid4
import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.dependencies import get_admin_user, get_db

router = APIRouter()

_CODE_RE = re.compile(r"^[A-Z0-9_\-]+$")


class CreditPackPayload(BaseModel):
    code: str = Field(..., min_length=2, max_length=80)
    title: str = Field(..., min_length=1, max_length=160)
    credits: int = Field(..., gt=0)
    price_usd: float = Field(..., gt=0)
    bonus_credits: int = Field(default=0, ge=0)
    description: Optional[str] = Field(default=None, max_length=500)
    is_popular: bool = False
    is_active: bool = True
    sort_order: int = Field(default=100)

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        code = str(value or "").strip().upper().replace(" ", "_")
        if not _CODE_RE.match(code):
            raise ValueError("Code can contain only uppercase letters, numbers, underscore, or dash")
        return code

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str) -> str:
        title = str(value or "").strip()
        if not title:
            raise ValueError("Title is required")
        return title


class CreditPackUpdatePayload(BaseModel):
    code: Optional[str] = Field(default=None, min_length=2, max_length=80)
    title: Optional[str] = Field(default=None, min_length=1, max_length=160)
    credits: Optional[int] = Field(default=None, gt=0)
    price_usd: Optional[float] = Field(default=None, gt=0)
    bonus_credits: Optional[int] = Field(default=None, ge=0)
    description: Optional[str] = Field(default=None, max_length=500)
    is_popular: Optional[bool] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        code = str(value or "").strip().upper().replace(" ", "_")
        if not _CODE_RE.match(code):
            raise ValueError("Code can contain only uppercase letters, numbers, underscore, or dash")
        return code

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        title = str(value or "").strip()
        if not title:
            raise ValueError("Title is required")
        return title


class CreditPackStatusPayload(BaseModel):
    is_active: Optional[bool] = None
    is_popular: Optional[bool] = None


async def _ensure_table(db: AsyncSession) -> None:
    await db.execute(text("""
        CREATE TABLE IF NOT EXISTS billing_credit_topup_packs (
            id UUID PRIMARY KEY,
            code TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            credits INTEGER NOT NULL,
            price_usd NUMERIC(12, 2) NOT NULL,
            bonus_credits INTEGER NOT NULL DEFAULT 0,
            description TEXT NULL,
            is_popular BOOLEAN NOT NULL DEFAULT FALSE,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            sort_order INTEGER NOT NULL DEFAULT 100,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """))
    await db.execute(text("""
        INSERT INTO billing_credit_topup_packs (id, code, title, credits, price_usd, bonus_credits, description, is_popular, is_active, sort_order)
        VALUES
            ('11111111-1111-4111-8111-111111111111', 'STARTER_10', '10 Credits', 10, 1.00, 0, 'Starter pack for quick checks', FALSE, TRUE, 10),
            ('22222222-2222-4222-8222-222222222222', 'BASIC_250', '250 Credits', 250, 25.00, 0, 'Basic top-up pack', FALSE, TRUE, 20),
            ('33333333-3333-4333-8333-333333333333', 'POPULAR_500', '500 Credits', 500, 45.00, 0, 'Best value for active traders', TRUE, TRUE, 30),
            ('44444444-4444-4444-8444-444444444444', 'PRO_1000', '1000 Credits', 1000, 90.00, 0, 'Pro pack for frequent backtesting', FALSE, TRUE, 40)
        ON CONFLICT (code) DO NOTHING
    """))


def _row_payload(row: Any) -> dict[str, Any]:
    total = int(row.get("credits") or 0) + int(row.get("bonus_credits") or 0)
    return {
        "id": str(row.get("id")),
        "code": row.get("code"),
        "title": row.get("title"),
        "credits": int(row.get("credits") or 0),
        "price_usd": float(row.get("price_usd") or 0),
        "bonus_credits": int(row.get("bonus_credits") or 0),
        "total_credits": total,
        "description": row.get("description"),
        "is_popular": bool(row.get("is_popular")),
        "popular": bool(row.get("is_popular")),
        "is_active": bool(row.get("is_active")),
        "sort_order": int(row.get("sort_order") or 100),
        "created_at": row.get("created_at").isoformat() if row.get("created_at") else None,
        "updated_at": row.get("updated_at").isoformat() if row.get("updated_at") else None,
    }


@router.get("")
async def list_credit_packs(
    db: AsyncSession = Depends(get_db),
    _current_admin: dict = Depends(get_admin_user),
):
    await _ensure_table(db)
    rows = (await db.execute(text("""
        SELECT * FROM billing_credit_topup_packs
        ORDER BY sort_order ASC, credits ASC, code ASC
    """))).mappings().all()
    await db.commit()
    return [_row_payload(row) for row in rows]


@router.post("")
async def create_credit_pack(
    payload: CreditPackPayload,
    db: AsyncSession = Depends(get_db),
    _current_admin: dict = Depends(get_admin_user),
):
    await _ensure_table(db)
    try:
        values = payload.model_dump()
        values["id"] = str(uuid4())
        row = (await db.execute(text("""
            INSERT INTO billing_credit_topup_packs
                (id, code, title, credits, price_usd, bonus_credits, description, is_popular, is_active, sort_order)
            VALUES
                (:id, :code, :title, :credits, :price_usd, :bonus_credits, :description, :is_popular, :is_active, :sort_order)
            RETURNING *
        """), values)).mappings().one()
        await db.commit()
        return _row_payload(row)
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Credit pack code already exists or data is invalid") from exc


@router.put("/{pack_id}")
async def update_credit_pack(
    pack_id: UUID,
    payload: CreditPackUpdatePayload,
    db: AsyncSession = Depends(get_db),
    _current_admin: dict = Depends(get_admin_user),
):
    await _ensure_table(db)
    current = (await db.execute(text("SELECT * FROM billing_credit_topup_packs WHERE id = :id"), {"id": str(pack_id)})).mappings().one_or_none()
    if not current:
        raise HTTPException(status_code=404, detail="Credit pack not found")
    values = dict(current)
    for key, value in payload.model_dump(exclude_unset=True).items():
        values[key] = value
    values["id"] = str(pack_id)
    try:
        row = (await db.execute(text("""
            UPDATE billing_credit_topup_packs
            SET code = :code,
                title = :title,
                credits = :credits,
                price_usd = :price_usd,
                bonus_credits = :bonus_credits,
                description = :description,
                is_popular = :is_popular,
                is_active = :is_active,
                sort_order = :sort_order,
                updated_at = NOW()
            WHERE id = :id
            RETURNING *
        """), values)).mappings().one()
        await db.commit()
        return _row_payload(row)
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Credit pack update failed. Check duplicate code or invalid values.") from exc


@router.patch("/{pack_id}/status")
async def update_credit_pack_status(
    pack_id: UUID,
    payload: CreditPackStatusPayload,
    db: AsyncSession = Depends(get_db),
    _current_admin: dict = Depends(get_admin_user),
):
    await _ensure_table(db)
    row = (await db.execute(text("""
        UPDATE billing_credit_topup_packs
        SET is_active = COALESCE(:is_active, is_active),
            is_popular = COALESCE(:is_popular, is_popular),
            updated_at = NOW()
        WHERE id = :id
        RETURNING *
    """), {"id": str(pack_id), "is_active": payload.is_active, "is_popular": payload.is_popular})).mappings().one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Credit pack not found")
    await db.commit()
    return _row_payload(row)
