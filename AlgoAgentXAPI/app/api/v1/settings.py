from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_admin_user, get_db

router = APIRouter()
admin_router = APIRouter()

COUPON_BAR_KEYS = {
    "enabled": "coupon_bar_enabled",
    "message": "coupon_bar_message",
    "code": "coupon_bar_code",
}

DEFAULT_COUPON_BAR = {
    "enabled": False,
    "message": "Haven't purchased yet? Use code HELLO & Get 20% OFF now on your first purchase!",
    "code": "HELLO",
}


class CouponBarConfig(BaseModel):
    enabled: bool = False
    message: str = ""
    code: str = ""


class CouponBarUpdate(BaseModel):
    enabled: bool = False
    message: str = Field(default="", max_length=300)
    code: str = Field(default="", max_length=50)

    @field_validator("message", "code")
    @classmethod
    def trim_text(cls, value: str) -> str:
        return (value or "").strip()


async def _ensure_app_settings_table(db: AsyncSession) -> None:
    await db.execute(text("""
        CREATE TABLE IF NOT EXISTS app_settings (
            key VARCHAR(120) PRIMARY KEY,
            value TEXT NOT NULL DEFAULT '',
            description TEXT NULL,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """))
    await db.execute(text("""
        INSERT INTO app_settings (key, value, description)
        VALUES
            ('coupon_bar_enabled', 'false', 'Enable or disable the logged-in user coupon announcement bar'),
            ('coupon_bar_message', :message, 'Coupon announcement message shown to logged-in users'),
            ('coupon_bar_code', :code, 'Coupon code highlighted in the coupon announcement bar')
        ON CONFLICT (key) DO NOTHING
    """), {"message": DEFAULT_COUPON_BAR["message"], "code": DEFAULT_COUPON_BAR["code"]})


async def _read_coupon_bar(db: AsyncSession) -> CouponBarConfig:
    await _ensure_app_settings_table(db)
    rows = (await db.execute(text("""
        SELECT key, value
        FROM app_settings
        WHERE key IN ('coupon_bar_enabled', 'coupon_bar_message', 'coupon_bar_code')
    """))).mappings().all()
    saved = {row["key"]: row["value"] for row in rows}
    enabled = str(saved.get("coupon_bar_enabled", "false")).strip().lower() in {"1", "true", "yes", "on"}
    return CouponBarConfig(
        enabled=enabled,
        message=str(saved.get("coupon_bar_message") or "").strip(),
        code=str(saved.get("coupon_bar_code") or "").strip(),
    )


@router.get("/coupon-bar", response_model=CouponBarConfig)
async def get_coupon_bar(db: AsyncSession = Depends(get_db)) -> CouponBarConfig:
    """Read the coupon announcement bar configuration for the frontend."""
    try:
        config = await _read_coupon_bar(db)
        await db.commit()
        return config
    except Exception:
        await db.rollback()
        return CouponBarConfig(enabled=False, message="", code="")


@admin_router.get("/coupon-bar", response_model=CouponBarConfig)
async def admin_get_coupon_bar(
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_admin_user),
) -> CouponBarConfig:
    config = await _read_coupon_bar(db)
    await db.commit()
    return config


@admin_router.put("/coupon-bar", response_model=CouponBarConfig)
async def admin_update_coupon_bar(
    payload: CouponBarUpdate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_admin_user),
) -> CouponBarConfig:
    message = payload.message.strip()
    code = payload.code.strip()
    if len(message) > 300:
        raise HTTPException(status_code=422, detail="Announcement message must be 300 characters or less")
    if len(code) > 50:
        raise HTTPException(status_code=422, detail="Coupon code must be 50 characters or less")

    await _ensure_app_settings_table(db)
    values = {
        "coupon_bar_enabled": "true" if payload.enabled else "false",
        "coupon_bar_message": message,
        "coupon_bar_code": code,
    }
    for key, value in values.items():
        await db.execute(text("""
            INSERT INTO app_settings (key, value, updated_at)
            VALUES (:key, :value, NOW())
            ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = NOW()
        """), {"key": key, "value": value})
    await db.commit()
    return CouponBarConfig(enabled=payload.enabled, message=message, code=code)
