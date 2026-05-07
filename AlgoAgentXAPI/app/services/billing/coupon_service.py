from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Optional
import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

ALLOWED_DISCOUNT_TYPES = {"PERCENT", "FIXED_USD"}
ALLOWED_APPLIES_TO = {"ALL", "SUBSCRIPTION", "CREDITS"}
ALLOWED_BILLING_PERIODS = {"NONE", "MONTHLY", "YEARLY", ""}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _as_decimal(value: Any, default: str = "0") -> Decimal:
    try:
        if value is None or value == "":
            return Decimal(default)
        return Decimal(str(value))
    except Exception:
        return Decimal(default)


def _money(value: Any) -> Decimal:
    """Return a 2-decimal Decimal for money values from DB/JSON/UI.

    Checkout metadata is serialized through JSON, so values often come back as
    float/int/str instead of Decimal. Keep this helper tolerant everywhere the
    coupon engine stores or calculates money.
    """
    return _as_decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _upper(value: Any) -> str:
    return str(value or "").strip().upper()


def _normalize_purchase_type(value: Any) -> str:
    raw = _upper(value)
    if raw in {"CREDIT_TOPUP", "CREDITS_TOPUP", "CREDIT", "TOPUP"}:
        return "CREDITS"
    if raw == "SUBSCRIPTION":
        return "SUBSCRIPTION"
    return raw or "CREDITS"


def _parse_dt(value: Any) -> Optional[datetime]:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    raw = str(value).strip()
    if not raw:
        return None
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(raw)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except Exception:
        return None


@dataclass
class CouponPreviewInput:
    code: str
    purchase_type: str
    subtotal_usd: Decimal
    user_id: Optional[str] = None
    plan_code: Optional[str] = None
    billing_period: Optional[str] = None
    credit_amount: Optional[int] = None


async def ensure_coupon_tables(db: AsyncSession) -> None:
    await db.execute(text("""
        CREATE TABLE IF NOT EXISTS billing_coupons (
            id UUID PRIMARY KEY,
            code TEXT NOT NULL UNIQUE,
            description TEXT NULL,
            discount_type TEXT NOT NULL DEFAULT 'PERCENT',
            discount_value NUMERIC(12, 2) NOT NULL DEFAULT 0,
            applies_to TEXT NOT NULL DEFAULT 'ALL',
            plan_code TEXT NULL,
            billing_period TEXT NULL,
            min_order_usd NUMERIC(12, 2) NULL,
            max_discount_usd NUMERIC(12, 2) NULL,
            max_redemptions INTEGER NULL,
            per_user_limit INTEGER NULL DEFAULT 1,
            starts_at TIMESTAMPTZ NULL,
            expires_at TIMESTAMPTZ NULL,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """))
    await db.execute(text("""
        CREATE TABLE IF NOT EXISTS billing_coupon_redemptions (
            id UUID PRIMARY KEY,
            coupon_id UUID NOT NULL REFERENCES billing_coupons(id) ON DELETE CASCADE,
            user_id UUID NULL,
            order_id UUID NULL,
            purchase_type TEXT NULL,
            subtotal_usd NUMERIC(12, 2) NOT NULL DEFAULT 0,
            discount_usd NUMERIC(12, 2) NOT NULL DEFAULT 0,
            final_usd NUMERIC(12, 2) NOT NULL DEFAULT 0,
            redeemed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """))
    # PAY-BILL hotfix: older installs may have the table without coupon_code.
    await db.execute(text("ALTER TABLE billing_coupon_redemptions ADD COLUMN IF NOT EXISTS coupon_code TEXT NULL"))
    await db.execute(text("CREATE INDEX IF NOT EXISTS idx_billing_coupons_code ON billing_coupons (UPPER(code))"))
    await db.execute(text("CREATE INDEX IF NOT EXISTS idx_billing_coupons_active ON billing_coupons (is_active)"))
    await db.execute(text("CREATE INDEX IF NOT EXISTS idx_billing_coupon_redemptions_coupon_user ON billing_coupon_redemptions (coupon_id, user_id)"))


def serialize_coupon(row: Any) -> dict[str, Any]:
    data = dict(row)
    for key in ["discount_value", "min_order_usd", "max_discount_usd", "total_discount_usd"]:
        if data.get(key) is not None:
            data[key] = float(data[key])
    for key in ["starts_at", "expires_at", "created_at", "updated_at", "last_used_at"]:
        if data.get(key) is not None and hasattr(data[key], "isoformat"):
            data[key] = data[key].isoformat()
    data["is_active"] = bool(data.get("is_active"))
    return data


def validate_coupon_payload(payload: dict[str, Any], partial: bool = False) -> dict[str, Any]:
    data: dict[str, Any] = {}
    if not partial or "code" in payload:
        code = _upper(payload.get("code"))
        if not code:
            raise ValueError("Coupon code is required")
        if any(ch.isspace() for ch in code):
            raise ValueError("Coupon code cannot contain spaces")
        data["code"] = code
    if "description" in payload or not partial:
        data["description"] = str(payload.get("description") or "").strip() or None
    if not partial or "discount_type" in payload:
        discount_type = _upper(payload.get("discount_type") or "PERCENT")
        if discount_type not in ALLOWED_DISCOUNT_TYPES:
            raise ValueError("Discount type must be PERCENT or FIXED_USD")
        data["discount_type"] = discount_type
    if not partial or "discount_value" in payload:
        discount_value = _as_decimal(payload.get("discount_value"))
        dtype = data.get("discount_type") or _upper(payload.get("discount_type") or "PERCENT")
        if discount_value <= 0:
            raise ValueError("Discount value must be greater than 0")
        if dtype == "PERCENT" and discount_value > 100:
            raise ValueError("Percent discount cannot exceed 100")
        data["discount_value"] = discount_value
    if not partial or "applies_to" in payload:
        applies_to = _upper(payload.get("applies_to") or "ALL")
        if applies_to not in ALLOWED_APPLIES_TO:
            raise ValueError("Applies to must be ALL, SUBSCRIPTION, or CREDITS")
        data["applies_to"] = applies_to
    if "plan_code" in payload or not partial:
        data["plan_code"] = _upper(payload.get("plan_code")) or None
    if "billing_period" in payload or not partial:
        period = _upper(payload.get("billing_period"))
        if period and period not in ALLOWED_BILLING_PERIODS:
            raise ValueError("Billing period must be NONE, MONTHLY, or YEARLY")
        data["billing_period"] = period or None
    for key in ["min_order_usd", "max_discount_usd"]:
        if key in payload or not partial:
            val = payload.get(key)
            data[key] = _as_decimal(val) if val not in (None, "") else None
            if data[key] is not None and data[key] < 0:
                raise ValueError(f"{key} cannot be negative")
    for key in ["max_redemptions", "per_user_limit"]:
        if key in payload or not partial:
            val = payload.get(key)
            data[key] = int(val) if val not in (None, "") else (1 if key == "per_user_limit" else None)
            if data[key] is not None and data[key] <= 0:
                raise ValueError(f"{key} must be positive")
    if "starts_at" in payload or not partial:
        data["starts_at"] = _parse_dt(payload.get("starts_at"))
    if "expires_at" in payload or not partial:
        data["expires_at"] = _parse_dt(payload.get("expires_at"))
    starts = data.get("starts_at") if "starts_at" in data else _parse_dt(payload.get("starts_at"))
    expires = data.get("expires_at") if "expires_at" in data else _parse_dt(payload.get("expires_at"))
    if starts and expires and expires < starts:
        raise ValueError("Expiry date cannot be before start date")
    if "is_active" in payload or not partial:
        data["is_active"] = bool(payload.get("is_active", True))
    return data


def calculate_discount(discount_type: str, discount_value: Decimal, subtotal_usd: Decimal, max_discount_usd: Decimal | None = None) -> Decimal:
    subtotal_usd = max(Decimal("0"), _money(subtotal_usd))
    if discount_type == "PERCENT":
        discount = subtotal_usd * (discount_value / Decimal("100"))
    else:
        discount = discount_value
    if max_discount_usd is not None and max_discount_usd > 0:
        discount = min(discount, max_discount_usd)
    discount = min(_money(discount), subtotal_usd)
    return max(Decimal("0"), discount)


async def get_coupon_by_code(db: AsyncSession, code: str) -> dict[str, Any] | None:
    await ensure_coupon_tables(db)
    row = (await db.execute(text("""
        SELECT * FROM billing_coupons WHERE UPPER(code) = :code LIMIT 1
    """), {"code": _upper(code)})).mappings().first()
    return dict(row) if row else None


async def preview_coupon(db: AsyncSession, data: CouponPreviewInput) -> dict[str, Any]:
    code = _upper(data.code)
    purchase_type = _upper(data.purchase_type)
    billing_period = _upper(data.billing_period)
    plan_code = _upper(data.plan_code)
    subtotal_usd = _money(data.subtotal_usd)

    if not code:
        return {"valid": False, "message": "Coupon code is required"}
    if subtotal_usd < 0:
        return {"valid": False, "message": "Subtotal must be greater than or equal to 0"}

    coupon = await get_coupon_by_code(db, code)
    if not coupon:
        return {"valid": False, "message": "Coupon not found"}
    if not bool(coupon.get("is_active")):
        return {"valid": False, "message": "Coupon is inactive"}

    now = _utc_now()
    starts_at = coupon.get("starts_at")
    expires_at = coupon.get("expires_at")
    if starts_at and starts_at > now:
        return {"valid": False, "message": "Coupon is not active yet"}
    if expires_at and expires_at < now:
        return {"valid": False, "message": "Coupon expired"}

    applies_to = _upper(coupon.get("applies_to") or "ALL")
    if applies_to != "ALL" and applies_to != purchase_type:
        return {"valid": False, "message": "Coupon is not valid for this purchase type"}

    coupon_plan = _upper(coupon.get("plan_code"))
    if coupon_plan and coupon_plan != plan_code:
        return {"valid": False, "message": "Coupon is not valid for this plan"}

    coupon_period = _upper(coupon.get("billing_period"))
    if coupon_period and coupon_period != billing_period:
        return {"valid": False, "message": "Coupon is not valid for this billing period"}

    min_order = _as_decimal(coupon.get("min_order_usd"), "0") if coupon.get("min_order_usd") is not None else None
    if min_order is not None and subtotal_usd < min_order:
        return {"valid": False, "message": f"Minimum order amount is ${_money(min_order)}"}

    coupon_id = str(coupon["id"])
    max_redemptions = coupon.get("max_redemptions")
    if max_redemptions:
        total_count = int((await db.execute(text("""
            SELECT COUNT(*) FROM billing_coupon_redemptions WHERE coupon_id::text = :coupon_id
        """), {"coupon_id": coupon_id})).scalar() or 0)
        if total_count >= int(max_redemptions):
            return {"valid": False, "message": "Coupon redemption limit reached"}

    per_user_limit = coupon.get("per_user_limit")
    if per_user_limit and data.user_id:
        user_count = int((await db.execute(text("""
            SELECT COUNT(*) FROM billing_coupon_redemptions WHERE coupon_id::text = :coupon_id AND user_id::text = :user_id
        """), {"coupon_id": coupon_id, "user_id": str(data.user_id)})).scalar() or 0)
        if user_count >= int(per_user_limit):
            return {"valid": False, "message": "Coupon already used for this user"}

    discount = calculate_discount(
        _upper(coupon.get("discount_type")),
        _as_decimal(coupon.get("discount_value")),
        subtotal_usd,
        _as_decimal(coupon.get("max_discount_usd")) if coupon.get("max_discount_usd") is not None else None,
    )
    final_usd = _money(subtotal_usd - discount)
    return {
        "valid": True,
        "code": code,
        "discount_type": _upper(coupon.get("discount_type")),
        "discount_value": float(_as_decimal(coupon.get("discount_value"))),
        "subtotal_usd": float(subtotal_usd),
        "discount_usd": float(discount),
        "final_usd": float(final_usd),
        "message": "Coupon applied successfully",
    }


async def record_coupon_redemption(
    db: AsyncSession,
    *,
    coupon_code: str | None,
    user_id: str | None,
    order_id: str | None,
    purchase_type: str | None,
    subtotal_usd: Any = 0,
    discount_usd: Any = 0,
    final_usd: Any = 0,
) -> bool:
    """Record coupon usage after a successful payment only. Idempotent per coupon/user/order."""
    code = _upper(coupon_code)
    if not code or not user_id or not order_id:
        return False
    await ensure_coupon_tables(db)
    coupon = await get_coupon_by_code(db, code)
    if not coupon:
        return False
    coupon_id = str(coupon["id"])
    existing = (await db.execute(text("""
        SELECT id FROM billing_coupon_redemptions
        WHERE coupon_id::text = :coupon_id AND user_id::text = :user_id AND order_id::text = :order_id
        LIMIT 1
    """), {"coupon_id": coupon_id, "user_id": str(user_id), "order_id": str(order_id)})).scalar()
    if existing:
        return False
    await db.execute(text("""
        INSERT INTO billing_coupon_redemptions (
            id, coupon_id, coupon_code, user_id, order_id, purchase_type,
            subtotal_usd, discount_usd, final_usd, redeemed_at
        ) VALUES (
            :id, :coupon_id, :coupon_code, :user_id, :order_id, :purchase_type,
            :subtotal_usd, :discount_usd, :final_usd, NOW()
        )
    """), {
        "id": str(uuid.uuid4()),
        "coupon_id": coupon_id,
        "coupon_code": code,
        "user_id": str(user_id),
        "order_id": str(order_id),
        "purchase_type": _normalize_purchase_type(purchase_type),
        "subtotal_usd": str(_money(subtotal_usd)),
        "discount_usd": str(_money(discount_usd)),
        "final_usd": str(_money(final_usd)),
    })
    return True
