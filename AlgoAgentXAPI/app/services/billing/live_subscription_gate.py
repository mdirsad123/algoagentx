from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy import String, cast, text, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Plan, UserSubscription


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _as_bool(value: Any, default: bool = True) -> bool:
    raw = str(value if value is not None else "").strip().lower()
    if raw in {"1", "true", "yes", "on", "enabled"}:
        return True
    if raw in {"0", "false", "no", "off", "disabled"}:
        return False
    return default


async def ensure_live_subscription_gate_settings(db: AsyncSession) -> None:
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
        VALUES ('billing_live_trading_requires_subscription', 'true', 'Require active paid subscription for live trading deployment and start actions')
        ON CONFLICT (key) DO NOTHING
    """))


async def live_trading_requires_subscription(db: AsyncSession) -> bool:
    await ensure_live_subscription_gate_settings(db)
    value = (await db.execute(text("""
        SELECT value FROM app_settings WHERE key = 'billing_live_trading_requires_subscription' LIMIT 1
    """))).scalar()
    return _as_bool(value, True)


async def get_recommended_coupon_code(db: AsyncSession) -> str | None:
    await ensure_live_subscription_gate_settings(db)
    rows = (await db.execute(text("""
        SELECT key, value FROM app_settings
        WHERE key IN ('coupon_bar_enabled', 'coupon_bar_code')
    """))).mappings().all()
    saved = {row["key"]: row["value"] for row in rows}
    if _as_bool(saved.get("coupon_bar_enabled"), False):
        code = str(saved.get("coupon_bar_code") or "").strip().upper()
        if code:
            return code

    try:
        row = (await db.execute(text("""
            SELECT code FROM billing_coupons
            WHERE is_active = TRUE
              AND applies_to IN ('ALL', 'SUBSCRIPTION')
              AND (starts_at IS NULL OR starts_at <= NOW())
              AND (expires_at IS NULL OR expires_at >= NOW())
            ORDER BY created_at DESC
            LIMIT 1
        """))).scalar()
        code = str(row or "").strip().upper()
        return code or None
    except Exception:
        return None


async def get_active_paid_subscription(db: AsyncSession, user_id: str) -> tuple[UserSubscription | None, Plan | None]:
    now = _now_utc()
    row = (await db.execute(
        select(UserSubscription, Plan)
        .join(Plan, Plan.id == UserSubscription.plan_id)
        .where(cast(UserSubscription.user_id, String) == str(user_id))
        .where(func.upper(UserSubscription.status) == "ACTIVE")
        .where(UserSubscription.end_at > now)
        .where(func.upper(Plan.code) != "FREE")
        .order_by(UserSubscription.end_at.desc(), UserSubscription.created_at.desc())
        .limit(1)
    )).first()
    if not row:
        return None, None
    return row[0], row[1]


async def build_live_trading_access_status(db: AsyncSession, user_id: str) -> dict[str, Any]:
    requires_subscription = await live_trading_requires_subscription(db)
    recommended_coupon = await get_recommended_coupon_code(db)
    sub, plan = (None, None)
    if requires_subscription:
        sub, plan = await get_active_paid_subscription(db, user_id)
    allowed = (not requires_subscription) or bool(sub)
    return {
        "allowed": allowed,
        "requires_subscription": requires_subscription,
        "code": None if allowed else "SUBSCRIPTION_REQUIRED",
        "message": "Live trading access enabled" if allowed else "Active subscription required to deploy live strategies.",
        "recommended_coupon": recommended_coupon,
        "subscription": None if not sub else {
            "id": str(sub.id),
            "status": sub.status,
            "plan_code": getattr(plan, "code", None),
            "billing_period": getattr(plan, "billing_period", None),
            "end_at": sub.end_at.isoformat() if sub.end_at else None,
        },
    }


async def require_active_subscription_for_live_trading(db: AsyncSession, user_id: str) -> None:
    status = await build_live_trading_access_status(db, user_id)
    if status.get("allowed"):
        return
    raise HTTPException(status_code=402, detail={
        "code": "SUBSCRIPTION_REQUIRED",
        "message": "Active subscription required to deploy live strategies.",
        "recommended_coupon": status.get("recommended_coupon"),
    })
