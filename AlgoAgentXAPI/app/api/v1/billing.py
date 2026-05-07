"""
Billing API endpoints
Handles plan information and cost preview functionality
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4
import json
import logging

import razorpay
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select, func
from pydantic import BaseModel, Field, field_validator

from app.schemas.billing import PlanResponse, CostPreviewRequest, CostPreviewResponse
from app.billing.plan_catalog import PlanCatalog
from app.billing.cost_rules import CostRules, CostType
from app.core.dependencies import get_admin_user, get_current_user, get_user_entitlements, get_db
from app.core.config import settings as app_settings
from app.db.compat import as_uuid_or_str, column_text, table_has_column
from app.services.billing.coupon_service import CouponPreviewInput, preview_coupon
from app.db.models import BillingOrder, Payment, Plan

router = APIRouter()
admin_router = APIRouter()
logger = logging.getLogger(__name__)

BILLING_SETTING_DEFAULTS = {
    "billing_base_currency": "USD",
    "billing_inr_conversion_rate": "83",
    "billing_gst_percent": "18",
    "billing_enable_razorpay_upi": "true",
    "billing_enable_card_payment": "true",
    "billing_enable_crypto_payment": "true",
    "billing_live_trading_requires_subscription": "true",
}


def _to_bool(value: Any, default: bool = False) -> bool:
    normalized = str(value if value is not None else "").strip().lower()
    if normalized in {"1", "true", "yes", "on", "enabled"}:
        return True
    if normalized in {"0", "false", "no", "off", "disabled"}:
        return False
    return default


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(str(value).strip())
    except Exception:
        return default


async def _ensure_app_settings_table(db: AsyncSession) -> None:
    await db.execute(text("""
        CREATE TABLE IF NOT EXISTS app_settings (
            key VARCHAR(120) PRIMARY KEY,
            value TEXT NOT NULL DEFAULT '',
            description TEXT NULL,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """))
    descriptions = {
        "billing_base_currency": "Base billing currency for AlgoAgentX pricing",
        "billing_inr_conversion_rate": "INR conversion rate for one USD",
        "billing_gst_percent": "GST percent used for future invoices and payment summaries",
        "billing_enable_razorpay_upi": "Enable Razorpay UPI payment option",
        "billing_enable_card_payment": "Enable card payment option",
        "billing_enable_crypto_payment": "Enable crypto payment option",
        "billing_live_trading_requires_subscription": "Require active paid subscription for live trading deployment and start actions",
    }
    for key, value in BILLING_SETTING_DEFAULTS.items():
        await db.execute(text("""
            INSERT INTO app_settings (key, value, description)
            VALUES (:key, :value, :description)
            ON CONFLICT (key) DO NOTHING
        """), {"key": key, "value": value, "description": descriptions.get(key, "")})


async def _read_billing_settings(db: AsyncSession) -> dict[str, Any]:
    await _ensure_app_settings_table(db)
    rows = (await db.execute(text("""
        SELECT key, value
        FROM app_settings
        WHERE key IN (
            'billing_base_currency',
            'billing_inr_conversion_rate',
            'billing_gst_percent',
            'billing_enable_razorpay_upi',
            'billing_enable_card_payment',
            'billing_enable_crypto_payment',
            'billing_live_trading_requires_subscription'
        )
    """))).mappings().all()
    saved = dict(BILLING_SETTING_DEFAULTS)
    saved.update({row["key"]: row["value"] for row in rows})
    return {
        "base_currency": "USD",
        "inr_conversion_rate": _to_float(saved.get("billing_inr_conversion_rate"), 83.0),
        "gst_percent": _to_float(saved.get("billing_gst_percent"), 18.0),
        "payment_methods": {
            "razorpay_upi": _to_bool(saved.get("billing_enable_razorpay_upi"), True),
            "card": _to_bool(saved.get("billing_enable_card_payment"), True),
            "crypto": _to_bool(saved.get("billing_enable_crypto_payment"), True),
        },
        "live_trading_requires_subscription": _to_bool(saved.get("billing_live_trading_requires_subscription"), True),
    }


@router.get("/settings/public")
async def get_public_billing_settings(db: AsyncSession = Depends(get_db)):
    try:
        payload = await _read_billing_settings(db)
        await db.commit()
        return payload
    except Exception:
        await db.rollback()
        return {
            "base_currency": "USD",
            "inr_conversion_rate": 83,
            "gst_percent": 18,
            "payment_methods": {"razorpay_upi": True, "card": True, "crypto": True},
            "live_trading_requires_subscription": True,
        }


@router.get("/credit-packs")
async def get_billing_credit_packs(db: AsyncSession = Depends(get_db)):
    await _ensure_credit_topup_packs_table(db)
    rows = (await db.execute(text("""
        SELECT * FROM billing_credit_topup_packs
        WHERE is_active = TRUE
        ORDER BY sort_order ASC, credits ASC, code ASC
    """))).mappings().all()
    await db.commit()
    return [_pack_payload(row) for row in rows]


@admin_router.get("/settings")
async def admin_get_billing_settings(
    db: AsyncSession = Depends(get_db),
    _current_admin: dict = Depends(get_admin_user),
):
    payload = await _read_billing_settings(db)
    await db.commit()
    return payload


@admin_router.put("/settings")
async def admin_update_billing_settings(
    payload: dict[str, Any],
    db: AsyncSession = Depends(get_db),
    _current_admin: dict = Depends(get_admin_user),
):
    inr_rate = _to_float(payload.get("inr_conversion_rate"), 0)
    gst_percent = _to_float(payload.get("gst_percent"), 0)
    methods = payload.get("payment_methods") or {}
    live_requires_subscription = bool(payload.get("live_trading_requires_subscription", True))
    razorpay_upi = bool(methods.get("razorpay_upi"))
    card = bool(methods.get("card"))
    crypto = bool(methods.get("crypto"))

    if inr_rate <= 0:
        raise HTTPException(status_code=422, detail="INR conversion rate must be greater than 0")
    if gst_percent < 0 or gst_percent > 50:
        raise HTTPException(status_code=422, detail="GST percent must be between 0 and 50")
    if not any([razorpay_upi, card, crypto]):
        raise HTTPException(status_code=422, detail="At least one payment method must remain enabled")

    await _ensure_app_settings_table(db)
    values = {
        "billing_base_currency": "USD",
        "billing_inr_conversion_rate": str(inr_rate),
        "billing_gst_percent": str(gst_percent),
        "billing_enable_razorpay_upi": "true" if razorpay_upi else "false",
        "billing_enable_card_payment": "true" if card else "false",
        "billing_enable_crypto_payment": "true" if crypto else "false",
        "billing_live_trading_requires_subscription": "true" if live_requires_subscription else "false",
    }
    for key, value in values.items():
        await db.execute(text("""
            INSERT INTO app_settings (key, value, updated_at)
            VALUES (:key, :value, NOW())
            ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = NOW()
        """), {"key": key, "value": value})
    await db.commit()
    return await _read_billing_settings(db)



class CheckoutPreviewRequest(BaseModel):
    purchase_type: str = Field(..., min_length=3, max_length=30)
    plan_code: Optional[str] = Field(default=None, max_length=50)
    billing_period: Optional[str] = Field(default=None, max_length=20)
    credit_amount: Optional[int] = Field(default=None, ge=0)
    pack_code: Optional[str] = Field(default=None, max_length=80)
    coupon_code: Optional[str] = Field(default=None, max_length=80)
    payment_method: str = Field(default="RAZORPAY_UPI", max_length=30)

    @field_validator("purchase_type", "plan_code", "billing_period", "pack_code", "coupon_code", "payment_method")
    @classmethod
    def normalize_upper(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        return str(value or "").strip().upper()


def _money(value: Any) -> Decimal:
    try:
        return Decimal(str(value or "0")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except Exception:
        return Decimal("0.00")


def _plan_price_usd(plan: Plan) -> Decimal:
    price_usd = _money(getattr(plan, "price_usd", None))
    price_inr = int(getattr(plan, "price_inr", 0) or 0)
    if price_usd > 0 or price_inr <= 0:
        return price_usd
    return _money(Decimal(price_inr) / Decimal("83"))


def _credit_pack_price_usd(credits: int) -> Decimal:
    mapping = {10: Decimal("1"), 100: Decimal("1"), 250: Decimal("25"), 500: Decimal("45"), 1000: Decimal("90")}
    if credits in mapping:
        return _money(mapping[credits])
    return _money(Decimal(max(credits, 0)) / Decimal("10"))


def _pack_payload(row: Any) -> dict[str, Any]:
    total_credits = int(row.get("credits") or 0) + int(row.get("bonus_credits") or 0)
    return {
        "id": str(row.get("id")) if row.get("id") else None,
        "code": str(row.get("code") or "").upper(),
        "title": row.get("title") or f"{total_credits} Credits",
        "credits": int(row.get("credits") or 0),
        "bonus_credits": int(row.get("bonus_credits") or 0),
        "total_credits": total_credits,
        "price_usd": float(_money(row.get("price_usd") or 0)),
        "amount_usd": float(_money(row.get("price_usd") or 0)),
        "description": row.get("description"),
        "is_popular": bool(row.get("is_popular")),
        "popular": bool(row.get("is_popular")),
        "is_active": bool(row.get("is_active", True)),
        "sort_order": int(row.get("sort_order") or 100),
        "label": f"${float(_money(row.get('price_usd') or 0)):g}",
    }


async def _ensure_credit_topup_packs_table(db: AsyncSession) -> None:
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


async def _load_credit_pack(db: AsyncSession, pack_code: str, *, active_only: bool = True) -> dict[str, Any] | None:
    await _ensure_credit_topup_packs_table(db)
    where_active = "AND is_active = TRUE" if active_only else ""
    row = (await db.execute(text(f"""
        SELECT * FROM billing_credit_topup_packs
        WHERE UPPER(code) = :code {where_active}
        LIMIT 1
    """), {"code": str(pack_code or "").strip().upper()})).mappings().one_or_none()
    return _pack_payload(row) if row else None

def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _get_razorpay_client() -> razorpay.Client:
    key_id = app_settings.razorpay_key_id
    key_secret = app_settings.razorpay_key_secret
    if not key_id or not key_secret:
        raise HTTPException(status_code=503, detail="Razorpay is not configured")
    return razorpay.Client(auth=(key_id, key_secret))


def _amount_to_paise(amount: Any) -> int:
    return int((_money(amount) * Decimal("100")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _checkout_description(preview: dict[str, Any]) -> str:
    if preview.get("purchase_type") == "SUBSCRIPTION":
        return f"{preview.get('plan_code') or ''} {preview.get('billing_period') or ''} subscription".strip()
    pack_code = preview.get("pack_code")
    pack_title = preview.get("pack_title")
    if pack_code or pack_title:
        return f"{pack_title or pack_code} credit top-up"
    return f"{preview.get('credit_amount') or 0} credits top-up"


async def _ensure_payment_routing_columns(db: AsyncSession) -> None:
    # SQL migration is still provided for production. This lightweight guard keeps local dev safe.
    await db.execute(text("""
        CREATE TABLE IF NOT EXISTS billing_orders (
            id VARCHAR(64) PRIMARY KEY,
            user_id VARCHAR(36) NOT NULL,
            billing_order_id VARCHAR(64) NOT NULL,
            provider VARCHAR(50) NOT NULL DEFAULT 'RAZORPAY',
            purpose VARCHAR(50) NOT NULL DEFAULT 'SUBSCRIPTION',
            amount_inr INTEGER NOT NULL DEFAULT 0,
            currency VARCHAR(3) NOT NULL DEFAULT 'INR',
            status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NULL
        )
    """))


async def _create_or_update_billing_order(
    db: AsyncSession,
    *,
    payment: Payment | None,
    internal_order_id: str,
    user_id: str,
    preview: dict[str, Any],
    provider: str,
    provider_order_id: str | None,
    status: str,
    metadata: dict[str, Any],
) -> BillingOrder | None:
    if not await table_has_column(db, "billing_orders", "id"):
        return None
    existing = (
        await db.execute(select(BillingOrder).where(BillingOrder.billing_order_id == internal_order_id).limit(1))
    ).scalar_one_or_none()
    if not existing:
        existing = BillingOrder(
            id=internal_order_id,
            user_id=str(user_id),
            billing_order_id=internal_order_id,
            provider=provider,
            purpose=str(preview.get("purchase_type") or ""),
            amount_inr=int(round(float(preview.get("final_inr") or preview.get("payment_amount") or 0))) if preview.get("payment_currency") == "INR" else 0,
            currency=str(preview.get("payment_currency") or "USD"),
            status=status,
        )
        db.add(existing)
    existing.payment_id = str(getattr(payment, "id", "") or "") or existing.payment_id
    existing.provider = provider
    existing.purpose = str(preview.get("purchase_type") or existing.purpose or "")
    existing.currency = str(preview.get("payment_currency") or existing.currency or "USD")[:3]
    existing.amount_inr = int(round(float(preview.get("final_inr") or 0))) if existing.currency == "INR" else int(existing.amount_inr or 0)
    existing.status = status
    existing.plan_code = preview.get("plan_code")
    existing.billing_period = preview.get("billing_period")
    existing.razorpay_order_id = provider_order_id if provider == "RAZORPAY" else existing.razorpay_order_id
    existing.metadata_json = json.dumps(metadata, default=str)
    # PAY-BILL-4 columns are added by migration; assign only when model has them.
    for attr, value in {
        "purchase_type": preview.get("purchase_type"),
        "credit_amount": preview.get("credit_amount"),
        "subtotal_usd": preview.get("subtotal_usd"),
        "coupon_code": preview.get("coupon_code"),
        "discount_usd": preview.get("discount_usd"),
        "final_usd": preview.get("final_usd"),
        "payment_method": preview.get("payment_method"),
        "payment_currency": preview.get("payment_currency"),
        "payment_amount": preview.get("payment_amount"),
        "inr_conversion_rate": preview.get("inr_conversion_rate"),
        "gst_percent": preview.get("gst_percent"),
        "gst_amount_inr": preview.get("gst_inr"),
        "final_amount_inr": preview.get("final_inr"),
        "provider_order_id": provider_order_id,
    }.items():
        if hasattr(existing, attr):
            setattr(existing, attr, value)
    await db.flush()
    return existing


@router.post("/checkout/preview")
async def preview_billing_checkout(
    payload: CheckoutPreviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    purchase_type = str(payload.purchase_type or "").upper()
    payment_method = str(payload.payment_method or "RAZORPAY_UPI").upper()
    if purchase_type not in {"SUBSCRIPTION", "CREDITS"}:
        raise HTTPException(status_code=422, detail="purchase_type must be SUBSCRIPTION or CREDITS")
    if payment_method not in {"RAZORPAY_UPI", "CARD", "CRYPTO"}:
        raise HTTPException(status_code=422, detail="Unsupported payment method")

    settings = await _read_billing_settings(db)
    methods = settings.get("payment_methods") or {}
    method_key = {"RAZORPAY_UPI": "razorpay_upi", "CARD": "card", "CRYPTO": "crypto"}[payment_method]
    if not bool(methods.get(method_key)):
        raise HTTPException(status_code=422, detail="Selected payment method is disabled")

    plan_payload: dict[str, Any] | None = None
    credit_amount: int | None = None
    if purchase_type == "SUBSCRIPTION":
        plan_code = str(payload.plan_code or "").upper()
        billing_period = str(payload.billing_period or "").upper()
        if not plan_code or not billing_period:
            raise HTTPException(status_code=422, detail="plan_code and billing_period are required")
        plan = (await db.execute(
            select(Plan).where(func.upper(Plan.code) == plan_code, func.upper(Plan.billing_period) == billing_period).limit(1)
        )).scalar_one_or_none()
        if not plan or not bool(getattr(plan, "is_active", False)):
            raise HTTPException(status_code=404, detail="Plan not found or inactive")
        subtotal_usd = _plan_price_usd(plan)
        plan_payload = {
            "id": str(plan.id),
            "code": str(plan.code or "").upper(),
            "billing_period": str(plan.billing_period or "").upper(),
            "included_credits": int(plan.included_credits or 0),
            "price_usd": float(subtotal_usd),
            "features": plan.features or {},
        }
    else:
        pack_code = str(payload.pack_code or "").strip().upper()
        pack_payload: dict[str, Any] | None = None
        if pack_code:
            pack_payload = await _load_credit_pack(db, pack_code, active_only=True)
            if not pack_payload:
                raise HTTPException(status_code=404, detail="Credit top-up pack not found or inactive")
            credit_amount = int(pack_payload.get("total_credits") or 0)
            subtotal_usd = _money(pack_payload.get("price_usd") or 0)
        else:
            # Legacy/custom compatibility: keep old preview/create-order working for old URLs.
            credit_amount = int(payload.credit_amount or 0)
            if credit_amount <= 0:
                raise HTTPException(status_code=422, detail="pack_code is required for credit top-up")
            subtotal_usd = _credit_pack_price_usd(credit_amount)
            pack_payload = None

    coupon_code = str(payload.coupon_code or "").strip().upper() or None
    coupon_result: dict[str, Any] | None = None
    discount_usd = Decimal("0.00")
    coupon_message = None
    if coupon_code:
        coupon_result = await preview_coupon(
            db,
            CouponPreviewInput(
                code=coupon_code,
                purchase_type=purchase_type,
                plan_code=(plan_payload or {}).get("code") if plan_payload else None,
                billing_period=(plan_payload or {}).get("billing_period") if plan_payload else None,
                credit_amount=credit_amount,
                subtotal_usd=subtotal_usd,
                user_id=str(current_user.get("user_id") or current_user.get("id") or ""),
            ),
        )
        if not bool(coupon_result.get("valid")):
            inr_rate = _money(settings.get("inr_conversion_rate", 83))
            gst_percent = _money(settings.get("gst_percent", 18))
            invalid_gst_inr = Decimal("0.00")
            invalid_final_inr = None
            invalid_payment_currency = "USD"
            invalid_payment_amount = subtotal_usd
            if payment_method == "RAZORPAY_UPI":
                invalid_base_inr = _money(subtotal_usd * inr_rate)
                invalid_gst_inr = _money(invalid_base_inr * (gst_percent / Decimal("100")))
                invalid_final_inr = _money(invalid_base_inr + invalid_gst_inr)
                invalid_payment_currency = "INR"
                invalid_payment_amount = invalid_final_inr
            await db.commit()
            return {
                "valid": False,
                "message": coupon_result.get("message") or "Coupon is not valid",
                "purchase_type": purchase_type,
                "plan_code": (plan_payload or {}).get("code") if plan_payload else None,
                "billing_period": (plan_payload or {}).get("billing_period") if plan_payload else None,
                "credit_amount": credit_amount,
                "pack_code": (pack_payload or {}).get("code") if purchase_type == "CREDITS" else None,
                "pack_title": (pack_payload or {}).get("title") if purchase_type == "CREDITS" else None,
                "pack": pack_payload if purchase_type == "CREDITS" else None,
                "bonus_credits": (pack_payload or {}).get("bonus_credits", 0) if purchase_type == "CREDITS" else 0,
                "base_credits": (pack_payload or {}).get("credits", credit_amount) if purchase_type == "CREDITS" else None,
                "base_currency": "USD",
                "subtotal_usd": float(subtotal_usd),
                "coupon_code": coupon_code,
                "discount_usd": 0,
                "tax_usd": 0,
                "final_usd": float(subtotal_usd),
                "payment_method": payment_method,
                "inr_conversion_rate": float(inr_rate),
                "gst_percent": float(gst_percent),
                "gst_inr": float(invalid_gst_inr),
                "final_inr": float(invalid_final_inr) if invalid_final_inr is not None else None,
                "payment_currency": invalid_payment_currency,
                "payment_amount": float(invalid_payment_amount),
                "payment_methods": methods,
            }
        discount_usd = _money(coupon_result.get("discount_usd", 0))
        coupon_message = coupon_result.get("message")

    final_usd_before_tax = _money(subtotal_usd - discount_usd)
    tax_usd = Decimal("0.00")
    final_usd = final_usd_before_tax
    inr_rate = _money(settings.get("inr_conversion_rate", 83))
    gst_percent = _money(settings.get("gst_percent", 18))
    gst_inr: Decimal | None = Decimal("0.00")
    final_inr: Decimal | None = None
    payment_currency = "USD"
    payment_amount = final_usd

    if payment_method == "RAZORPAY_UPI":
        base_inr = _money(final_usd_before_tax * inr_rate)
        gst_inr = _money(base_inr * (gst_percent / Decimal("100")))
        final_inr = _money(base_inr + gst_inr)
        payment_currency = "INR"
        payment_amount = final_inr
    else:
        gst_inr = Decimal("0.00")
        final_inr = None

    await db.commit()
    return {
        "valid": True,
        "message": coupon_message or ("Coupon applied successfully" if coupon_code else "Checkout preview ready"),
        "purchase_type": purchase_type,
        "plan_code": (plan_payload or {}).get("code") if plan_payload else None,
        "billing_period": (plan_payload or {}).get("billing_period") if plan_payload else None,
        "credit_amount": credit_amount,
        "pack_code": (pack_payload or {}).get("code") if purchase_type == "CREDITS" else None,
        "pack_title": (pack_payload or {}).get("title") if purchase_type == "CREDITS" else None,
        "pack": pack_payload if purchase_type == "CREDITS" else None,
        "bonus_credits": (pack_payload or {}).get("bonus_credits", 0) if purchase_type == "CREDITS" else 0,
        "base_credits": (pack_payload or {}).get("credits", credit_amount) if purchase_type == "CREDITS" else None,
        "plan": plan_payload,
        "base_currency": "USD",
        "subtotal_usd": float(subtotal_usd),
        "coupon_code": coupon_code,
        "discount_usd": float(discount_usd),
        "tax_usd": float(tax_usd),
        "final_usd": float(final_usd_before_tax),
        "payment_method": payment_method,
        "inr_conversion_rate": float(inr_rate),
        "gst_percent": float(gst_percent),
        "gst_inr": float(gst_inr or 0),
        "final_inr": float(final_inr) if final_inr is not None else None,
        "payment_currency": payment_currency,
        "payment_amount": float(payment_amount),
        "payment_methods": methods,
    }


class CheckoutCreateOrderRequest(BaseModel):
    purchase_type: str = Field(..., min_length=3, max_length=30)
    plan_code: Optional[str] = Field(default=None, max_length=50)
    billing_period: Optional[str] = Field(default=None, max_length=20)
    credit_amount: Optional[int] = Field(default=None, ge=0)
    pack_code: Optional[str] = Field(default=None, max_length=80)
    coupon_code: Optional[str] = Field(default=None, max_length=80)
    payment_method: str = Field(default="RAZORPAY_UPI", max_length=30)

    @field_validator("purchase_type", "plan_code", "billing_period", "pack_code", "coupon_code", "payment_method")
    @classmethod
    def normalize_upper(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        return str(value or "").strip().upper()


@router.post("/checkout/create-order")
async def create_billing_checkout_order(
    payload: CheckoutCreateOrderRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_id = str(current_user.get("user_id") or current_user.get("id") or "")
    if not user_id:
        raise HTTPException(status_code=401, detail="User is required")

    preview_payload = CheckoutPreviewRequest(
        purchase_type=payload.purchase_type,
        plan_code=payload.plan_code,
        billing_period=payload.billing_period,
        credit_amount=payload.credit_amount,
        pack_code=payload.pack_code,
        coupon_code=payload.coupon_code,
        payment_method=payload.payment_method,
    )
    preview = await preview_billing_checkout(preview_payload, db, current_user)
    if not bool(preview.get("valid", True)):
        raise HTTPException(status_code=422, detail=preview.get("message") or "Checkout preview is not valid")

    purchase_type = str(preview.get("purchase_type") or "").upper()
    payment_method = str(preview.get("payment_method") or "").upper()
    if purchase_type not in {"SUBSCRIPTION", "CREDITS"}:
        raise HTTPException(status_code=422, detail="Invalid purchase type")
    if payment_method not in {"RAZORPAY_UPI", "CARD", "CRYPTO"}:
        raise HTTPException(status_code=422, detail="Unsupported payment method")

    internal_order_id = f"bill_{uuid4().hex[:24]}"
    metadata = {
        "flow": "billing_checkout_create_order",
        "purchase_type": purchase_type,
        "plan_code": preview.get("plan_code"),
        "billing_period": preview.get("billing_period"),
        "credit_amount": preview.get("credit_amount"),
        "pack_code": preview.get("pack_code"),
        "pack_title": preview.get("pack_title"),
        "base_credits": preview.get("base_credits"),
        "bonus_credits": preview.get("bonus_credits"),
        "price_usd": preview.get("subtotal_usd"),
        "coupon_code": preview.get("coupon_code"),
        "discount_usd": preview.get("discount_usd"),
        "subtotal_usd": preview.get("subtotal_usd"),
        "final_usd": preview.get("final_usd"),
        "payment_method": payment_method,
        "payment_currency": preview.get("payment_currency"),
        "payment_amount": preview.get("payment_amount"),
        "payment_amount_paise": _amount_to_paise(preview.get("payment_amount")) if preview.get("payment_currency") == "INR" else None,
        "inr_conversion_rate": preview.get("inr_conversion_rate"),
        "gst_percent": preview.get("gst_percent"),
        "gst_inr": preview.get("gst_inr"),
        "final_inr": preview.get("final_inr"),
    }

    if payment_method == "RAZORPAY_UPI":
        if str(preview.get("payment_currency") or "") != "INR":
            raise HTTPException(status_code=422, detail="Razorpay UPI orders must be payable in INR")
        amount_paise = _amount_to_paise(preview.get("payment_amount"))
        if amount_paise <= 0:
            raise HTTPException(status_code=422, detail="Payment amount must be greater than zero")
        client = _get_razorpay_client()
        try:
            razorpay_order = client.order.create(
                data={
                    "amount": amount_paise,
                    "currency": "INR",
                    "receipt": internal_order_id,
                    "payment_capture": 1,
                    "notes": {
                        "user_id": user_id,
                        "purpose": purchase_type,
                        "plan_code": str(preview.get("plan_code") or ""),
                        "billing_period": str(preview.get("billing_period") or ""),
                        "credit_amount": str(preview.get("credit_amount") or ""),
                        "pack_code": str(preview.get("pack_code") or ""),
                        "coupon_code": str(preview.get("coupon_code") or ""),
                    },
                }
            )
        except Exception as exc:
            logger.exception("Failed to create Razorpay billing checkout order")
            raise HTTPException(status_code=502, detail="Unable to create Razorpay order") from exc

        provider_order_id = str(razorpay_order.get("id") or "")
        plan_id = None
        if purchase_type == "SUBSCRIPTION" and preview.get("plan"):
            plan_id = (preview.get("plan") or {}).get("id")
        payment = Payment(
            user_id=as_uuid_or_str(user_id),
            provider="RAZORPAY",
            purpose="SUBSCRIPTION" if purchase_type == "SUBSCRIPTION" else "CREDIT_TOPUP",
            amount_inr=int(round(float(preview.get("payment_amount") or 0))),
            currency="INR",
            status="CREATED",
            billing_order_id=internal_order_id,
            razorpay_order_id=provider_order_id,
            plan_id=as_uuid_or_str(plan_id) if plan_id else None,
            plan_code=preview.get("plan_code"),
            billing_period=preview.get("billing_period"),
        )
        db.add(payment)
        await db.flush()
        await _create_or_update_billing_order(
            db,
            payment=payment,
            internal_order_id=internal_order_id,
            user_id=user_id,
            preview=preview,
            provider="RAZORPAY",
            provider_order_id=provider_order_id,
            status="PENDING",
            metadata=metadata,
        )
        await db.commit()
        return {
            "order_id": internal_order_id,
            "payment_record_id": str(payment.id),
            "purchase_type": purchase_type,
            "payment_method": "RAZORPAY_UPI",
            "provider": "RAZORPAY",
            "razorpay_order_id": provider_order_id,
            "currency": "INR",
            "amount": float(preview.get("payment_amount") or 0),
            "amount_paise": amount_paise,
            "key_id": app_settings.razorpay_key_id or "",
            "razorpay_key_id": app_settings.razorpay_key_id or "",
            "checkout": {
                "key_id": app_settings.razorpay_key_id or "",
                "name": "AlgoAgentX",
                "description": _checkout_description(preview),
            },
            "preview": preview,
        }

    provider = "CARD_PROVIDER" if payment_method == "CARD" else "CRYPTO"
    await _create_or_update_billing_order(
        db,
        payment=None,
        internal_order_id=internal_order_id,
        user_id=user_id,
        preview=preview,
        provider=provider,
        provider_order_id=None,
        status="PENDING",
        metadata=metadata,
    )
    await db.commit()
    return {
        "order_id": internal_order_id,
        "purchase_type": purchase_type,
        "payment_method": payment_method,
        "provider": provider,
        "currency": "USD",
        "amount": float(preview.get("payment_amount") or 0),
        "status": "PENDING",
        "message": "Card payment provider will be connected soon." if payment_method == "CARD" else "Crypto invoice created. Payment confirmation is pending.",
        "preview": preview,
    }




class CouponPreviewRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=80)
    purchase_type: str = Field(..., min_length=3, max_length=30)
    plan_code: Optional[str] = Field(default=None, max_length=50)
    billing_period: Optional[str] = Field(default=None, max_length=20)
    credit_amount: Optional[int] = Field(default=None, ge=0)
    subtotal_usd: Decimal = Field(..., ge=0)

    @field_validator("code", "purchase_type", "plan_code", "billing_period")
    @classmethod
    def normalize_upper(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        return str(value or "").strip().upper()


@router.post("/coupons/preview")
async def preview_billing_coupon(
    payload: CouponPreviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    result = await preview_coupon(
        db,
        CouponPreviewInput(
            code=payload.code,
            purchase_type=payload.purchase_type,
            plan_code=payload.plan_code,
            billing_period=payload.billing_period,
            credit_amount=payload.credit_amount,
            subtotal_usd=payload.subtotal_usd,
            user_id=str(current_user.get("user_id") or ""),
        ),
    )
    await db.commit()
    return result

@router.get("/plans", response_model=List[PlanResponse])
async def get_plans():
    """
    Get all available plans with their features and pricing
    
    Returns:
        List of all available plans
    """
    try:
        plans_data = PlanCatalog.get_all_plans()
        plans = []
        
        for plan_key, plan_info in plans_data.items():
            plans.append(PlanResponse(
                code=plan_info["code"],
                billing_period=plan_info["billing_period"],
                price_inr=plan_info["price_inr"],
                included_credits=plan_info["included_credits"],
                features=plan_info["features"],
                is_active=plan_info["is_active"]
            ))
        
        return plans
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving plans: {str(e)}")


@router.post("/preview-cost", response_model=CostPreviewResponse)
async def preview_cost(request: CostPreviewRequest):
    """
    Preview cost for backtest or AI screener operations
    
    Args:
        request: Cost preview request with operation details
    
    Returns:
        Cost preview with detailed breakdown
    """
    try:
        # Validate request parameters
        if request.type == "backtest":
            if not request.start_date or not request.end_date:
                raise HTTPException(
                    status_code=400, 
                    detail="start_date and end_date are required for backtest cost calculation"
                )
            
            if not request.timeframe:
                request.timeframe = "1h"  # Default timeframe
            
            # Validate parameters
            if not CostRules.validate_cost_parameters(
                CostType.BACKTEST,
                start_date=request.start_date,
                end_date=request.end_date,
                timeframe=request.timeframe
            ):
                raise HTTPException(
                    status_code=400,
                    detail="Invalid backtest parameters"
                )
            
            # Calculate cost
            cost = CostRules.calculate_backtest_cost(
                request.start_date,
                request.end_date,
                request.timeframe
            )
            
            # Get detailed breakdown
            breakdown = CostRules.get_cost_breakdown(
                CostType.BACKTEST,
                start_date=request.start_date,
                end_date=request.end_date,
                timeframe=request.timeframe
            )
        
        elif request.type == "ai_screener":
            if not request.mode:
                request.mode = "basic"  # Default mode
            
            # Validate parameters
            if not CostRules.validate_cost_parameters(
                CostType.AI_SCREENER,
                mode=request.mode,
                depth=request.depth
            ):
                raise HTTPException(
                    status_code=400,
                    detail="Invalid AI screener parameters"
                )
            
            # Calculate cost
            cost = CostRules.calculate_ai_screener_cost(
                request.mode,
                request.depth
            )
            
            # Get detailed breakdown
            breakdown = CostRules.get_cost_breakdown(
                CostType.AI_SCREENER,
                mode=request.mode,
                depth=request.depth
            )
        
        else:
            raise HTTPException(
                status_code=400,
                detail="Invalid cost type. Must be 'backtest' or 'ai_screener'"
            )
        
        return CostPreviewResponse(
            type=request.type,
            total_cost=cost,
            breakdown=breakdown
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error calculating cost: {str(e)}"
        )


@router.get("/cost-rules")
async def get_cost_rules():
    """
    Get cost calculation rules and multipliers
    
    Returns:
        Cost calculation rules and multipliers
    """
    try:
        rules = {
            "backtest_cost_rules": CostRules.BACKTEST_COST_RULES,
            "timeframe_multipliers": CostRules.TIMEFRAME_MULTIPLIERS,
            "ai_screener_cost_rules": CostRules.AI_SCREENER_COST_RULES,
            "valid_timeframes": list(CostRules.TIMEFRAME_MULTIPLIERS.keys()),
            "valid_modes": list(CostRules.AI_SCREENER_COST_RULES.keys()),
            "valid_depths": ["light", "medium", "deep"]
        }
        
        return rules
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving cost rules: {str(e)}"
        )


@router.get("/me")
async def get_user_billing_info(
    current_user: dict = Depends(get_current_user),
    entitlements: dict = Depends(get_user_entitlements),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current user's billing information
    
    Returns:
        Current plan, trial status, credits balance, and limits summary
    """
    try:
        # Get user's credit balance
        credits_query = text("""
            SELECT balance FROM user_credits WHERE user_id = :user_id
        """)
        
        credits_result = await db.execute(credits_query, {"user_id": current_user["user_id"]})
        credits_row = credits_result.fetchone()
        credits_balance = credits_row.balance if credits_row else 0
        
        # Get daily usage counts
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        
        # Backtest count
        backtest_count_query = text("""
            SELECT COUNT(*) as count FROM backtests 
            WHERE user_id = :user_id AND created_at >= :start_date AND created_at < :end_date
        """)
        
        backtest_result = await db.execute(backtest_count_query, {
            "user_id": current_user["user_id"],
            "start_date": today_start,
            "end_date": today_end
        })
        daily_backtest_count = backtest_result.scalar() or 0
        
        # AI runs count (placeholder - would need actual tracking)
        ai_runs_count_query = text("""
            SELECT COUNT(*) as count FROM credit_transactions 
            WHERE user_id = :user_id AND type = 'DEBIT' AND reason LIKE '%AI%' 
            AND created_at >= :start_date AND created_at < :end_date
        """)
        
        ai_result = await db.execute(ai_runs_count_query, {
            "user_id": current_user["user_id"],
            "start_date": today_start,
            "end_date": today_end
        })
        daily_ai_runs_count = ai_result.scalar() or 0
        
        return {
            "user_id": current_user["user_id"],
            "plan": {
                "code": entitlements["plan_code"],
                "billing_period": entitlements["billing_period"],
                "price_inr": entitlements["price_inr"],
                "subscription_status": entitlements["subscription_status"],
                "is_trial": entitlements["is_trial"],
                "is_premium": entitlements["is_premium"]
            },
            "trial": {
                "remaining_days": entitlements["trial_remaining_days"],
                "end_date": (datetime.utcnow() + timedelta(days=entitlements["trial_remaining_days"])).isoformat() if entitlements["trial_remaining_days"] > 0 else None
            },
            "credits": {
                "balance": credits_balance,
                "included_in_plan": entitlements["included_credits"],
                "total_available": credits_balance + entitlements["included_credits"]
            },
            "limits": {
                "max_backtests_per_day": entitlements["features"]["backtests_per_day"],
                "daily_backtests_used": daily_backtest_count,
                "backtests_remaining_today": max(0, entitlements["features"]["backtests_per_day"] - daily_backtest_count),
                
                "max_ai_runs_per_day": entitlements["features"]["ai_runs_per_day"],
                "daily_ai_runs_used": daily_ai_runs_count,
                "ai_runs_remaining_today": max(0, entitlements["features"]["ai_runs_per_day"] - daily_ai_runs_count),
                
                "max_parallel_jobs": entitlements["features"]["max_parallel_jobs"],
                "max_date_range_days": entitlements["features"]["max_date_range_days"],
                "export_enabled": entitlements["features"]["export_enabled"],
                "support_priority": entitlements["features"]["support_priority"]
            },
            "usage": {
                "daily_backtest_count": daily_backtest_count,
                "daily_ai_runs_count": daily_ai_runs_count
            }
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving billing information: {str(e)}"
        )
