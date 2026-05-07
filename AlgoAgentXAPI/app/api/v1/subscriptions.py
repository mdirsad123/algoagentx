from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import razorpay
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import String, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import settings
from ...core.dependencies import get_current_user, get_db
from ...db.compat import as_uuid_or_str, column_text, table_has_column
from ...db.models import (
    BillingDocument,
    BillingOrder,
    BillingWebhookEvent,
    Payment,
    Plan,
    UserSubscription,
)
from ...services.subscriptions import SubscriptionLifecycleService, SubscriptionLifecycleState
from ...utils.api_response import success_response
from ...services.billing.coupon_service import record_coupon_redemption

router = APIRouter()


class SubscriptionCheckoutRequest(BaseModel):
    plan_code: str = Field(..., min_length=2, max_length=50)
    billing_period: str = Field(default="NONE")

    @field_validator("plan_code")
    @classmethod
    def normalize_plan_code(cls, value: str) -> str:
        return str(value or "").strip().upper()

    @field_validator("billing_period")
    @classmethod
    def normalize_billing_period(cls, value: str) -> str:
        normalized = str(value or "").strip().upper()
        if normalized == "ANNUAL":
            return "YEARLY"
        return normalized

class SubscriptionVerifyRequest(BaseModel):
    order_id: str
    razorpay_payment_id: str
    razorpay_signature: str

class SubscriptionFailureRequest(BaseModel):
    order_id: str
    reason: str | None = None
    code: str | None = None


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_billing_period(period: str | None) -> str:
    raw = str(period or "").strip().upper()
    if raw == "ANNUAL":
        return "YEARLY"
    if raw in {"YEARLY", "MONTHLY", "NONE"}:
        return raw
    return raw


def _normalize_plan_code(plan_code: str | None) -> str:
    return str(plan_code or "").strip().upper()


def _period_days(period: str) -> int:
    return 365 if _normalize_billing_period(period) == "YEARLY" else 30


def _get_razorpay_client() -> razorpay.Client:
    if not settings.razorpay_key_id or not settings.razorpay_key_secret:
        raise HTTPException(status_code=503, detail="Razorpay is not configured")
    return razorpay.Client(auth=(settings.razorpay_key_id, settings.razorpay_key_secret))


def _subscription_state(sub: UserSubscription) -> str:
    if not sub:
        return "NONE"
    now = _now_utc()
    normalized = str(sub.status or "").upper()
    if normalized in {"CANCELED", "CANCELLED"}:
        return "CANCELED"
    if sub.end_at and sub.end_at < now:
        return "EXPIRED"
    if normalized in {"TRIAL", "TRIALING"}:
        return "TRIAL"
    if normalized in {"ACTIVE"}:
        return "ACTIVE"
    return normalized or "UNKNOWN"


def _next_refill_at(now: datetime, period: str) -> datetime:
    return now + timedelta(days=_period_days(period))


def _plan_key(plan_code: str | None, billing_period: str | None) -> str:
    return f"{_normalize_plan_code(plan_code)}::{_normalize_billing_period(billing_period)}"


def _is_valid_plan_combo(plan_code: str | None, billing_period: str | None) -> bool:
    code = _normalize_plan_code(plan_code)
    period = _normalize_billing_period(billing_period)
    if not code or not period:
        return False
    if code == "FREE":
        return period == "NONE"
    return period in {"MONTHLY", "YEARLY"}




def _price_usd_from_plan(plan: Plan | None) -> float:
    if not plan:
        return 0.0
    raw = getattr(plan, "price_usd", None)
    try:
        price_usd = float(raw or 0)
    except Exception:
        price_usd = 0.0
    if price_usd > 0 or int(getattr(plan, "price_inr", 0) or 0) <= 0:
        return round(price_usd, 2)
    return round(int(getattr(plan, "price_inr", 0) or 0) / 83, 2)

def _serialize_plan(row: Plan) -> dict:
    code = _normalize_plan_code(getattr(row, "code", None))
    period = _normalize_billing_period(getattr(row, "billing_period", None))
    return {
        "id": str(row.id),
        "code": code,
        "billing_period": period,
        "price_usd": _price_usd_from_plan(row),
        "price_inr": int(row.price_inr or 0),
        "included_credits": int(row.included_credits or 0),
        "features": row.features or {},
        "is_active": bool(row.is_active),
        "plan_key": _plan_key(code, period),
    }


async def _sync_billing_order(db: AsyncSession, payment: Payment, *, metadata: dict | None = None) -> None:
    if not await table_has_column(db, "billing_orders", "id"):
        return

    billing_order_id = str(payment.billing_order_id or payment.razorpay_order_id or f"subord_{uuid4().hex[:24]}")
    existing = (
        await db.execute(
            select(BillingOrder).where(BillingOrder.billing_order_id == billing_order_id).limit(1)
        )
    ).scalar_one_or_none()

    if not existing:
        existing = BillingOrder(
            id=billing_order_id,
            user_id=str(payment.user_id),
            billing_order_id=billing_order_id,
            provider=str(payment.provider or "RAZORPAY"),
            purpose=str(payment.purpose or "SUBSCRIPTION"),
            amount_inr=int(payment.amount_inr or 0),
            currency=str(payment.currency or "INR"),
            status=str(payment.status or "CREATED"),
        )
        db.add(existing)

    existing.payment_id = str(payment.id) if getattr(payment, "id", None) else existing.payment_id
    existing.subscription_id = str(getattr(payment, "subscription_id", None) or "") or existing.subscription_id
    existing.plan_id = str(getattr(payment, "plan_id", None) or "") or existing.plan_id
    existing.plan_code = getattr(payment, "plan_code", None)
    existing.billing_period = getattr(payment, "billing_period", None)
    existing.provider = str(payment.provider or existing.provider or "RAZORPAY")
    existing.purpose = str(payment.purpose or existing.purpose or "SUBSCRIPTION")
    existing.amount_inr = int(payment.amount_inr or existing.amount_inr or 0)
    existing.currency = str(payment.currency or existing.currency or "INR")
    existing.status = str(payment.status or existing.status or "CREATED")
    existing.razorpay_order_id = payment.razorpay_order_id
    existing.razorpay_payment_id = payment.razorpay_payment_id
    existing.failure_reason = payment.failure_reason
    existing.verified_at = payment.verified_at
    if metadata is not None:
        existing.metadata_json = json.dumps(metadata)

    await db.flush()


async def _get_latest_subscription(db: AsyncSession, user_id: str) -> UserSubscription | None:
    active = await _get_active_subscription(db, user_id)
    if active:
        return active

    return (
        await db.execute(
            select(UserSubscription)
            .where(cast(UserSubscription.user_id, String) == str(user_id))
            .order_by(UserSubscription.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()


async def _get_subscription_by_id(db: AsyncSession, subscription_id: str | None) -> UserSubscription | None:
    if not subscription_id:
        return None
    return (
        await db.execute(
            select(UserSubscription)
            .where(cast(UserSubscription.id, String) == str(subscription_id))
            .limit(1)
        )
    ).scalar_one_or_none()


async def _get_active_subscription(db: AsyncSession, user_id: str) -> UserSubscription | None:
    now = _now_utc()
    return (
        await db.execute(
            select(UserSubscription)
            .where(
                cast(UserSubscription.user_id, String) == str(user_id),
                UserSubscription.status.in_(["ACTIVE", "TRIAL", "TRIALING"]),
                UserSubscription.end_at > now,
            )
            .order_by(UserSubscription.end_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()


async def _billing_order_metadata(db: AsyncSession, billing_order_id: str | None) -> dict:
    if not billing_order_id or not await table_has_column(db, "billing_orders", "id"):
        return {}
    row = (
        await db.execute(select(BillingOrder).where(BillingOrder.billing_order_id == str(billing_order_id)).limit(1))
    ).scalar_one_or_none()
    raw = getattr(row, "metadata_json", None) if row else None
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def _expected_payment_paise(payment: Payment, metadata: dict) -> int:
    try:
        if metadata.get("payment_amount_paise"):
            return int(metadata.get("payment_amount_paise") or 0)
    except Exception:
        pass
    return int(payment.amount_inr or 0) * 100


async def _record_checkout_coupon_if_needed(db: AsyncSession, payment: Payment, metadata: dict) -> None:
    await record_coupon_redemption(
        db,
        coupon_code=metadata.get("coupon_code"),
        user_id=str(payment.user_id),
        order_id=str(payment.billing_order_id or payment.id),
        purchase_type=metadata.get("purchase_type") or "SUBSCRIPTION",
        subtotal_usd=metadata.get("subtotal_usd") or 0,
        discount_usd=metadata.get("discount_usd") or 0,
        final_usd=metadata.get("final_usd") or 0,
    )


def _verify_webhook_signature(raw_body: bytes, signature: str | None) -> bool:
    if not settings.razorpay_webhook_secret:
        return False
    if not signature:
        return False
    expected = hmac.new(
        settings.razorpay_webhook_secret.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


async def _ensure_billing_documents(
    db: AsyncSession,
    *,
    payment: Payment,
    subscription: UserSubscription | None,
    source: str,
) -> None:
    if not await table_has_column(db, "billing_documents", "id"):
        return

    payment_id = getattr(payment, "id", None)
    if not payment_id:
        return

    credits_delta = int(getattr(subscription, "included_credits_total", 0) or 0)
    now = _now_utc()

    for document_type, prefix in (("INVOICE", "INV"), ("RECEIPT", "RCPT")):
        existing = (
            await db.execute(
                select(BillingDocument).where(
                    BillingDocument.payment_id == payment_id,
                    BillingDocument.document_type == document_type,
                )
            )
        ).scalar_one_or_none()
        if existing:
            continue

        doc_number = f"{prefix}-{now.strftime('%Y%m%d')}-{str(payment_id).replace('-', '')[:12].upper()}"
        db.add(
            BillingDocument(
                user_id=as_uuid_or_str(str(payment.user_id)),
                payment_id=payment_id,
                billing_order_id=str(payment.billing_order_id or "") or None,
                document_type=document_type,
                document_number=doc_number,
                provider="RAZORPAY",
                purpose="SUBSCRIPTION",
                amount_inr=int(payment.amount_inr or 0),
                currency=str(payment.currency or "INR"),
                plan_code=str(payment.plan_code or "") or None,
                billing_period=str(payment.billing_period or "") or None,
                credits_delta=credits_delta,
                metadata_json=json.dumps(
                    {
                        "source": source,
                        "subscription_id": str(getattr(subscription, "id", "") or "") or None,
                        "razorpay_order_id": payment.razorpay_order_id,
                        "razorpay_payment_id": payment.razorpay_payment_id,
                    }
                ),
            )
        )


async def _record_webhook_event(
    db: AsyncSession,
    *,
    event_type: str,
    payload_json: str,
    signature: str | None,
    status: str,
    event_key: str | None = None,
    payload_hash: str | None = None,
    payment: Payment | None = None,
    processing_error: str | None = None,
) -> BillingWebhookEvent | None:
    if not await table_has_column(db, "billing_webhook_events", "id"):
        return None

    row = BillingWebhookEvent(
        provider="RAZORPAY",
        event_type=event_type,
        event_key=event_key,
        payload_hash=payload_hash,
        signature=signature,
        payload_json=payload_json,
        status=status,
        processing_error=processing_error,
        payment_id=getattr(payment, "id", None),
        billing_order_id=str(getattr(payment, "billing_order_id", None) or "") or None,
        purpose="SUBSCRIPTION" if payment else None,
        processed_at=_now_utc() if status in {"PROCESSED", "FAILED", "IGNORED"} else None,
    )
    db.add(row)
    await db.flush()
    return row


async def _activate_or_refill_subscription(
    db: AsyncSession,
    *,
    user_id: str,
    payment: Payment,
    plan: Plan,
) -> UserSubscription:
    now = _now_utc()
    cycle_days = _period_days(str(plan.billing_period or "MONTHLY"))
    active = await _get_active_subscription(db, user_id)
    included_total = int(plan.included_credits or 0)

    if active:
        # Renewal or upgrade on active subscription.
        same_plan = str(active.plan_id) == str(plan.id)
        if same_plan:
            base_end = active.end_at if active.end_at and active.end_at > now else now
            active.end_at = base_end + timedelta(days=cycle_days)
            # Renewal resets current cycle included credits to the plan quota.
            active.included_credits_remaining = included_total
            active.last_refill_cycle_key = None
        else:
            active.plan_id = plan.id
            active.start_at = now
            active.end_at = now + timedelta(days=cycle_days)
            active.included_credits_remaining = included_total
            active.last_refill_cycle_key = None

        active.status = "ACTIVE"
        active.renews = True
        active.plan_code_snapshot = str(plan.code)
        active.billing_period_snapshot = _normalize_billing_period(getattr(plan, "billing_period", None))
        active.plan_price_inr = int(plan.price_inr or 0)
        active.included_credits_total = included_total
        active.last_credit_refill_at = now
        active.next_credit_refill_at = _next_refill_at(now, _normalize_billing_period(str(plan.billing_period or "MONTHLY")))
        active.source_payment_id = payment.id
        active.trial_end_at = None
        subscription = active
    else:
        subscription = UserSubscription(
            user_id=as_uuid_or_str(user_id),
            plan_id=plan.id,
            status="ACTIVE",
            start_at=now,
            end_at=now + timedelta(days=cycle_days),
            trial_end_at=None,
            renews=True,
            plan_code_snapshot=str(plan.code),
            billing_period_snapshot=_normalize_billing_period(getattr(plan, "billing_period", None)),
            plan_price_inr=int(plan.price_inr or 0),
            included_credits_total=included_total,
            included_credits_remaining=included_total,
            last_credit_refill_at=now,
            next_credit_refill_at=_next_refill_at(now, _normalize_billing_period(str(plan.billing_period or "MONTHLY"))),
            source_payment_id=payment.id,
        )
        db.add(subscription)
        await db.flush()

    payment.subscription_id = str(subscription.id)
    payment.plan_id = plan.id
    payment.plan_code = str(plan.code)
    payment.billing_period = _normalize_billing_period(getattr(plan, "billing_period", None))
    return subscription


def _serialize_subscription(sub: UserSubscription | None, plan: Plan | None = None) -> dict | None:
    if not sub:
        return None
    return {
        "id": str(sub.id),
        "user_id": str(sub.user_id),
        "plan_id": str(sub.plan_id),
        "plan_code": (sub.plan_code_snapshot or getattr(plan, "code", None) or "FREE"),
        "billing_period": _normalize_billing_period(sub.billing_period_snapshot or getattr(plan, "billing_period", None) or "NONE"),
        "plan_key": _plan_key(sub.plan_code_snapshot or getattr(plan, "code", None), sub.billing_period_snapshot or getattr(plan, "billing_period", None)),
        "price_usd": _price_usd_from_plan(plan),
        "price_inr": int(sub.plan_price_inr or getattr(plan, "price_inr", 0) or 0),
        "status": sub.status,
        "billing_state": _subscription_state(sub),
        "start_at": sub.start_at.isoformat() if sub.start_at else None,
        "end_at": sub.end_at.isoformat() if sub.end_at else None,
        "renews": bool(sub.renews),
        "razorpay_subscription_id": sub.razorpay_subscription_id,
        "included_credits_total": int(sub.included_credits_total or getattr(plan, "included_credits", 0) or 0),
        "included_credits_remaining": int(sub.included_credits_remaining or 0),
        "next_credit_refill_at": sub.next_credit_refill_at.isoformat() if sub.next_credit_refill_at else None,
        "next_refill_reset_at": sub.next_credit_refill_at.isoformat() if sub.next_credit_refill_at else None,
        "last_credit_refill_at": sub.last_credit_refill_at.isoformat() if sub.last_credit_refill_at else None,
        "created_at": sub.created_at.isoformat() if sub.created_at else None,
    }


@router.get("/")
async def list_my_subscriptions(db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    await SubscriptionLifecycleService.ensure_user_subscription_cycle(
        db,
        str(current_user["user_id"]),
        for_update=True,
        auto_commit=True,
    )
    rows = (
        await db.execute(
            select(UserSubscription, Plan)
            .outerjoin(Plan, Plan.id == UserSubscription.plan_id)
            .where(cast(UserSubscription.user_id, String) == str(current_user["user_id"]))
            .order_by(UserSubscription.created_at.desc())
        )
    ).all()
    data = [_serialize_subscription(sub, plan) for sub, plan in rows]
    return success_response(data, "No data found" if not data else None)


@router.get("/me")
async def get_my_subscription(db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    cycle = await SubscriptionLifecycleService.ensure_user_subscription_cycle(
        db,
        str(current_user["user_id"]),
        for_update=True,
        auto_commit=True,
    )
    sub: UserSubscription | None = cycle.get("subscription")
    plan: Plan | None = cycle.get("plan")
    lifecycle_state = str(cycle.get("lifecycle_state") or SubscriptionLifecycleState.NONE.value)

    if not sub:
        # Legacy safety: if latest row is absent but a valid active row exists, return it.
        active = await _get_active_subscription(db, str(current_user["user_id"]))
        if not active:
            return success_response(None, "No data found")
        sub = active
        plan = await db.get(Plan, sub.plan_id) if sub.plan_id else None
        lifecycle_state = SubscriptionLifecycleState.ACTIVE.value

    payload = _serialize_subscription(sub, plan)
    if payload is not None:
        payload["lifecycle_state"] = lifecycle_state
    return success_response(payload)


@router.get("/plans")
async def get_available_plans(db: AsyncSession = Depends(get_db)):
    rows = (
        await db.execute(
            select(Plan)
            .where(Plan.is_active == True)
            .order_by(Plan.created_at.asc(), Plan.id.asc())
        )
    ).scalars().all()

    deduped: dict[str, dict] = {}
    for row in rows:
        normalized = _serialize_plan(row)
        if not _is_valid_plan_combo(normalized.get("code"), normalized.get("billing_period")):
            continue
        # Prefer latest created row for duplicate legacy keys.
        deduped[normalized["plan_key"]] = normalized

    plans = list(deduped.values())

    grouped = {
        "free": [p for p in plans if p["code"] == "FREE"],
        "monthly": [p for p in plans if p["billing_period"] == "MONTHLY"],
        "yearly": [p for p in plans if p["billing_period"] == "YEARLY"],
        "paid": [p for p in plans if p["code"] != "FREE"],
    }
    grouped["free"] = sorted(grouped["free"], key=lambda item: int(item.get("price_inr") or 0))
    grouped["monthly"] = sorted(grouped["monthly"], key=lambda item: int(item.get("price_inr") or 0))
    grouped["yearly"] = sorted(grouped["yearly"], key=lambda item: int(item.get("price_inr") or 0))
    grouped["paid"] = sorted(grouped["paid"], key=lambda item: (item.get("billing_period", ""), int(item.get("price_inr") or 0)))
    return success_response(grouped)


@router.post("/upgrade")
async def upgrade_subscription_compat(
    request: SubscriptionCheckoutRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    # Backward-compatible route kept intentionally.
    # Paid plans must go through Razorpay checkout.
    if request.plan_code != "FREE":
        raise HTTPException(
            status_code=400,
            detail="Direct upgrade is disabled. Use /subscriptions/razorpay/create-order for paid plans.",
        )

    user_id = str(current_user["user_id"])
    request_period = _normalize_billing_period(request.billing_period)
    if request_period and request_period != "NONE":
        raise HTTPException(status_code=400, detail="FREE plan billing_period must be NONE")

    free_plan = (
        await db.execute(
            select(Plan)
            .where(
                func.upper(Plan.code) == "FREE",
                func.upper(Plan.billing_period) == "NONE",
                Plan.is_active == True,
            )
            .order_by(Plan.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if not free_plan:
        free_plan = (
            await db.execute(
                select(Plan)
                .where(func.upper(Plan.code) == "FREE", Plan.is_active == True)
                .order_by(Plan.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
    if not free_plan:
        raise HTTPException(status_code=404, detail="FREE plan not configured")

    cycle = await SubscriptionLifecycleService.ensure_user_subscription_cycle(
        db,
        user_id,
        for_update=True,
        auto_commit=False,
    )
    active_sub: UserSubscription | None = cycle.get("subscription")
    lifecycle_state = str(cycle.get("lifecycle_state") or SubscriptionLifecycleState.NONE.value)

    if active_sub and lifecycle_state in {SubscriptionLifecycleState.ACTIVE.value, SubscriptionLifecycleState.TRIAL.value}:
        active_plan_code = str(getattr(active_sub, "plan_code_snapshot", None) or "").upper()
        if not active_plan_code and getattr(active_sub, "plan_id", None):
            active_plan = await db.get(Plan, active_sub.plan_id)
            active_plan_code = str(getattr(active_plan, "code", None) or "").upper()

        if active_plan_code and active_plan_code != "FREE":
            raise HTTPException(
                status_code=409,
                detail="An active paid subscription already exists. Cancel/expire it before activating FREE.",
            )
        if active_plan_code == "FREE":
            await db.commit()
            return success_response(_serialize_subscription(active_sub, free_plan), "Already on free plan")

    now = _now_utc()
    existing_latest = await _get_latest_subscription(db, user_id)
    if existing_latest and str(getattr(existing_latest, "status", "")).upper() in {
        "CANCELLED",
        "CANCELED",
        "EXPIRED",
        "FAILED",
        "PENDING",
        "NONE",
    }:
        sub = existing_latest
        sub.plan_id = free_plan.id
        sub.status = "ACTIVE"
        sub.start_at = now
        sub.end_at = now + timedelta(days=30)
        sub.renews = False
        sub.plan_code_snapshot = str(free_plan.code)
        sub.billing_period_snapshot = str(free_plan.billing_period)
        sub.plan_price_inr = int(free_plan.price_inr or 0)
        sub.included_credits_total = int(free_plan.included_credits or 0)
        sub.included_credits_remaining = int(free_plan.included_credits or 0)
        sub.last_credit_refill_at = now
        sub.next_credit_refill_at = _next_refill_at(now, str(free_plan.billing_period or "MONTHLY"))
        sub.last_refill_cycle_key = None
        sub.source_payment_id = None
        sub.trial_end_at = None
    else:
        sub = UserSubscription(
            user_id=as_uuid_or_str(user_id),
            plan_id=free_plan.id,
            status="ACTIVE",
            start_at=now,
            end_at=now + timedelta(days=30),
            renews=False,
            plan_code_snapshot=str(free_plan.code),
            billing_period_snapshot=str(free_plan.billing_period),
            plan_price_inr=int(free_plan.price_inr or 0),
            included_credits_total=int(free_plan.included_credits or 0),
            included_credits_remaining=int(free_plan.included_credits or 0),
            last_credit_refill_at=now,
            next_credit_refill_at=_next_refill_at(now, str(free_plan.billing_period or "MONTHLY")),
            source_payment_id=None,
        )
        db.add(sub)

    await db.flush()
    await db.commit()
    await db.refresh(sub)
    return success_response(_serialize_subscription(sub, free_plan), "Free subscription activated")


@router.get("/razorpay/config")
async def get_razorpay_subscription_config():
    return success_response({
        "key_id": settings.razorpay_key_id or "",
        "currency": "INR",
        "configured": bool(settings.razorpay_key_id and settings.razorpay_key_secret),
    })


@router.post("/razorpay/create")
@router.post("/razorpay/create-order")
async def create_subscription_checkout(
    request: SubscriptionCheckoutRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_id = str(current_user["user_id"])
    client = _get_razorpay_client()

    if request.plan_code == "FREE":
        raise HTTPException(status_code=400, detail="FREE plan does not require Razorpay checkout")
    if request.billing_period not in {"MONTHLY", "YEARLY"}:
        raise HTTPException(status_code=400, detail="Paid subscriptions must be MONTHLY or YEARLY")

    stmt = select(Plan).where(
        func.upper(Plan.code) == request.plan_code,
        Plan.is_active == True,
    )
    if request.billing_period == "YEARLY":
        stmt = stmt.where(func.upper(Plan.billing_period).in_(["YEARLY", "ANNUAL"]))
    else:
        stmt = stmt.where(func.upper(Plan.billing_period) == request.billing_period)

    plan = (
        await db.execute(
            stmt.order_by(Plan.created_at.desc())
        )
    ).scalars().first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    if int(plan.price_inr or 0) <= 0:
        raise HTTPException(status_code=400, detail="Selected plan does not require paid checkout")

    billing_order_id = f"subord_{uuid4().hex[:24]}"
    try:
        razorpay_order = client.order.create(
            data={
                "amount": int(plan.price_inr or 0) * 100,
                "currency": "INR",
                "receipt": billing_order_id,
                "payment_capture": 1,
                "notes": {
                    "user_id": user_id,
                    "purpose": "SUBSCRIPTION",
                    "plan_code": str(plan.code),
                    "billing_period": _normalize_billing_period(getattr(plan, "billing_period", None)),
                },
            }
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Unable to create Razorpay order") from exc

    payment = Payment(
        user_id=as_uuid_or_str(user_id),
        provider="RAZORPAY",
        purpose="SUBSCRIPTION",
        amount_inr=int(plan.price_inr or 0),
        currency="INR",
        status="CREATED",
        billing_order_id=billing_order_id,
        razorpay_order_id=str(razorpay_order.get("id") or ""),
        plan_id=plan.id,
        plan_code=str(plan.code),
        billing_period=_normalize_billing_period(getattr(plan, "billing_period", None)),
    )
    db.add(payment)
    await db.flush()
    await _sync_billing_order(
        db,
        payment,
        metadata={
            "flow": "subscription_create_order",
            "plan_code": str(plan.code),
            "billing_period": _normalize_billing_period(getattr(plan, "billing_period", None)),
        },
    )
    await db.commit()
    await db.refresh(payment)

    return success_response(
        {
            "order_id": payment.razorpay_order_id,
            "billing_order_id": payment.billing_order_id,
            "payment_record_id": str(payment.id),
            "amount": int(payment.amount_inr or 0) * 100,
            "amount_inr": int(payment.amount_inr or 0),
            "currency": payment.currency or "INR",
            "key_id": settings.razorpay_key_id or "",
            "razorpay_key_id": settings.razorpay_key_id or "",
            "status": payment.status,
            "plan": {
                "id": str(plan.id),
                "code": str(plan.code),
                "billing_period": _normalize_billing_period(getattr(plan, "billing_period", None)),
                "price_usd": _price_usd_from_plan(plan),
                "price_inr": int(plan.price_inr or 0),
                "included_credits": int(plan.included_credits or 0),
            },
        },
        "Subscription checkout created successfully",
    )


@router.post("/razorpay/verify")
async def verify_subscription_payment(
    payload: SubscriptionVerifyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_id = str(current_user["user_id"])
    client = _get_razorpay_client()

    payment = (
        await db.execute(
            select(Payment)
            .where(
                Payment.razorpay_order_id == payload.order_id,
                column_text(Payment.user_id) == user_id,
                Payment.purpose == "SUBSCRIPTION",
            )
            .with_for_update()
        )
    ).scalar_one_or_none()
    if not payment:
        raise HTTPException(status_code=404, detail="Subscription order not found")

    checkout_metadata = await _billing_order_metadata(db, payment.billing_order_id)

    if payment.status == "PAID":
        existing_sub = await _get_subscription_by_id(db, payment.subscription_id)
        if not existing_sub:
            existing_sub = await _get_latest_subscription(db, user_id)
        existing_plan = await db.get(Plan, existing_sub.plan_id) if existing_sub and existing_sub.plan_id else None
        return success_response(
            {
                "success": True,
                "payment_id": payment.razorpay_payment_id or payload.razorpay_payment_id,
                "order_id": payment.razorpay_order_id,
                "billing_order_id": payment.billing_order_id,
                "status": payment.status,
                "idempotent": True,
                "subscription": _serialize_subscription(existing_sub, existing_plan),
                "message": "Subscription payment already verified",
            },
            "Subscription payment already verified",
        )

    duplicate_paid = (
        await db.execute(
            select(Payment).where(
                Payment.razorpay_payment_id == payload.razorpay_payment_id,
                Payment.status == "PAID",
            )
        )
    ).scalar_one_or_none()
    if duplicate_paid and str(duplicate_paid.id) != str(payment.id):
        raise HTTPException(status_code=409, detail="This Razorpay payment is already linked to another order")

    try:
        client.utility.verify_payment_signature(
            {
                "razorpay_order_id": payload.order_id,
                "razorpay_payment_id": payload.razorpay_payment_id,
                "razorpay_signature": payload.razorpay_signature,
            }
        )
    except Exception as exc:
        payment.status = "FAILED"
        payment.failure_reason = "signature_verification_failed"
        await db.commit()
        raise HTTPException(status_code=400, detail="Invalid payment signature") from exc

    try:
        fetched = client.payment.fetch(payload.razorpay_payment_id)
        fetched_status = str(fetched.get("status") or "").lower()
        fetched_order = str(fetched.get("order_id") or "")
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Unable to verify payment with Razorpay") from exc

    if fetched_order != str(payment.razorpay_order_id):
        payment.status = "FAILED"
        payment.failure_reason = "order_mismatch"
        await db.commit()
        raise HTTPException(status_code=400, detail="Payment order mismatch")

    if fetched_status != "captured":
        payment.status = "FAILED"
        payment.failure_reason = f"payment_status_{fetched_status or 'unknown'}"
        await db.commit()
        raise HTTPException(status_code=400, detail="Payment is not successful")

    fetched_amount = int(fetched.get("amount") or 0)
    expected_amount = _expected_payment_paise(payment, checkout_metadata)
    if fetched_amount != expected_amount:
        payment.status = "FAILED"
        payment.failure_reason = "amount_mismatch"
        await db.commit()
        raise HTTPException(status_code=400, detail="Payment amount mismatch")

    plan = None
    if payment.plan_id:
        plan = await db.get(Plan, payment.plan_id)
    if not plan and payment.plan_code and payment.billing_period:
        stmt = select(Plan).where(func.upper(Plan.code) == _normalize_plan_code(payment.plan_code))
        if _normalize_billing_period(payment.billing_period) == "YEARLY":
            stmt = stmt.where(func.upper(Plan.billing_period).in_(["YEARLY", "ANNUAL"]))
        else:
            stmt = stmt.where(func.upper(Plan.billing_period) == _normalize_billing_period(payment.billing_period))
        plan = (await db.execute(stmt.order_by(Plan.created_at.desc()))).scalars().first()
    if not plan:
        payment.status = "FAILED"
        payment.failure_reason = "plan_metadata_missing"
        await db.commit()
        raise HTTPException(status_code=500, detail="Plan metadata missing for this subscription payment")

    payment.razorpay_payment_id = payload.razorpay_payment_id
    payment.razorpay_signature = payload.razorpay_signature
    payment.status = "PAID"
    payment.failure_reason = None
    payment.verified_at = _now_utc()

    subscription = await _activate_or_refill_subscription(db, user_id=user_id, payment=payment, plan=plan)
    await _sync_billing_order(
        db,
        payment,
        metadata={
            "flow": "subscription_verify",
            "idempotent": False,
            "subscription_id": str(subscription.id),
        },
    )
    await _ensure_billing_documents(
        db,
        payment=payment,
        subscription=subscription,
        source="verify_endpoint",
    )
    await _record_checkout_coupon_if_needed(db, payment, checkout_metadata)
    await db.commit()

    return success_response(
        {
            "success": True,
            "payment_id": payload.razorpay_payment_id,
            "order_id": payment.razorpay_order_id,
            "billing_order_id": payment.billing_order_id,
            "status": payment.status,
            "idempotent": False,
            "subscription": _serialize_subscription(subscription, plan),
            "message": "Subscription activated successfully",
        },
        "Subscription activated successfully",
    )


@router.post("/razorpay/failure")
async def mark_subscription_payment_failure(
    payload: SubscriptionFailureRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_id = str(current_user["user_id"])
    payment = (
        await db.execute(
            select(Payment).where(
                Payment.razorpay_order_id == payload.order_id,
                column_text(Payment.user_id) == user_id,
                Payment.purpose == "SUBSCRIPTION",
            )
            .with_for_update()
        )
    ).scalar_one_or_none()
    if not payment:
        raise HTTPException(status_code=404, detail="Subscription order not found")

    if payment.status == "PAID":
        return success_response(
            {
                "order_id": payment.razorpay_order_id,
                "billing_order_id": payment.billing_order_id,
                "status": payment.status,
            },
            "Subscription payment already paid",
        )

    detail = payload.reason or "subscription_payment_failed_or_cancelled"
    if payload.code:
        detail = f"{detail} ({payload.code})"

    payment.status = "FAILED"
    payment.failure_reason = detail
    await _sync_billing_order(
        db,
        payment,
        metadata={
            "flow": "subscription_failure",
            "reason": detail,
        },
    )
    await db.commit()
    return success_response(
        {
            "order_id": payment.razorpay_order_id,
            "billing_order_id": payment.billing_order_id,
            "status": payment.status,
        },
        "Subscription payment marked as failed",
    )


@router.post("/cancel/{subscription_id}")
async def cancel_subscription(
    subscription_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    sub = (
        await db.execute(
            select(UserSubscription).where(
                cast(UserSubscription.id, String) == str(subscription_id),
                cast(UserSubscription.user_id, String) == str(current_user["user_id"]),
            )
        )
    ).scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")

    sub.status = "CANCELED"
    sub.renews = False
    await db.commit()
    return success_response({"id": str(sub.id), "status": sub.status}, "Subscription canceled successfully")


@router.post("/razorpay/webhook")
async def razorpay_subscription_webhook(
    request: Request,
    x_razorpay_signature: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    raw_body = await request.body()
    payload_hash = hashlib.sha256(raw_body).hexdigest()
    if not _verify_webhook_signature(raw_body, x_razorpay_signature):
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid webhook payload") from exc

    event = str(payload.get("event") or "")
    payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
    webhook_event_key = str(payment_entity.get("id") or payload.get("id") or "") or None

    if event not in {"payment.captured", "payment.failed"}:
        await _record_webhook_event(
            db,
            event_type=event,
            payload_json=raw_body.decode("utf-8", errors="ignore"),
            signature=x_razorpay_signature,
            status="IGNORED",
            event_key=webhook_event_key,
            payload_hash=payload_hash,
            processing_error="unsupported_event",
        )
        await db.commit()
        return success_response({"event": event, "status": "ignored"}, "Event ignored")

    if event == "payment.captured":
        entity = payment_entity
        order_id = str(entity.get("order_id") or "")
        payment_id = str(entity.get("id") or "")
        if not order_id or not payment_id:
            await _record_webhook_event(
                db,
                event_type=event,
                payload_json=raw_body.decode("utf-8", errors="ignore"),
                signature=x_razorpay_signature,
                status="FAILED",
                event_key=webhook_event_key,
                payload_hash=payload_hash,
                processing_error="missing_payment_identifiers",
            )
            await db.commit()
            return success_response({"event": event, "status": "ignored"}, "Missing payment identifiers")

        payment = (
            await db.execute(
                select(Payment)
                .where(Payment.razorpay_order_id == order_id, Payment.purpose == "SUBSCRIPTION")
                .with_for_update()
            )
        ).scalar_one_or_none()
        if not payment:
            await _record_webhook_event(
                db,
                event_type=event,
                payload_json=raw_body.decode("utf-8", errors="ignore"),
                signature=x_razorpay_signature,
                status="IGNORED",
                event_key=webhook_event_key,
                payload_hash=payload_hash,
                processing_error="payment_not_found",
            )
            await db.commit()
            return success_response({"event": event, "status": "ignored"}, "No matching subscription payment")

        if payment.status == "PAID":
            await _record_webhook_event(
                db,
                event_type=event,
                payload_json=raw_body.decode("utf-8", errors="ignore"),
                signature=x_razorpay_signature,
                status="IGNORED",
                event_key=webhook_event_key,
                payload_hash=payload_hash,
                payment=payment,
                processing_error="already_paid",
            )
            await db.commit()
            return success_response({"event": event, "status": "already_processed"}, "Already processed")

        duplicate_paid = (
            await db.execute(
                select(Payment).where(
                    Payment.razorpay_payment_id == payment_id,
                    Payment.status == "PAID",
                )
            )
        ).scalar_one_or_none()
        if duplicate_paid and str(duplicate_paid.id) != str(payment.id):
            payment.status = "FAILED"
            payment.failure_reason = "duplicate_payment_id"
            await _sync_billing_order(
                db,
                payment,
                metadata={"flow": "subscription_webhook_payment_failed", "reason": payment.failure_reason},
            )
            await _record_webhook_event(
                db,
                event_type=event,
                payload_json=raw_body.decode("utf-8", errors="ignore"),
                signature=x_razorpay_signature,
                status="FAILED",
                event_key=webhook_event_key,
                payload_hash=payload_hash,
                payment=payment,
                processing_error="duplicate_payment_id",
            )
            await db.commit()
            return success_response({"event": event, "status": "failed"}, "Payment already linked to another order")

        plan = None
        if payment.plan_id:
            plan = await db.get(Plan, payment.plan_id)
        if not plan and payment.plan_code and payment.billing_period:
            stmt = select(Plan).where(func.upper(Plan.code) == _normalize_plan_code(payment.plan_code))
            if _normalize_billing_period(payment.billing_period) == "YEARLY":
                stmt = stmt.where(func.upper(Plan.billing_period).in_(["YEARLY", "ANNUAL"]))
            else:
                stmt = stmt.where(func.upper(Plan.billing_period) == _normalize_billing_period(payment.billing_period))
            plan = (await db.execute(stmt.order_by(Plan.created_at.desc()))).scalars().first()
        if not plan:
            payment.status = "FAILED"
            payment.failure_reason = "plan_metadata_missing"
            await _sync_billing_order(
                db,
                payment,
                metadata={"flow": "subscription_webhook_payment_failed", "reason": payment.failure_reason},
            )
            await _record_webhook_event(
                db,
                event_type=event,
                payload_json=raw_body.decode("utf-8", errors="ignore"),
                signature=x_razorpay_signature,
                status="FAILED",
                event_key=webhook_event_key,
                payload_hash=payload_hash,
                payment=payment,
                processing_error="plan_metadata_missing",
            )
            await db.commit()
            return success_response({"event": event, "status": "failed"}, "Plan metadata missing")

        fetched_amount = int(entity.get("amount") or 0)
        expected_amount = int(payment.amount_inr or 0) * 100
        if fetched_amount != expected_amount:
            payment.status = "FAILED"
            payment.failure_reason = "amount_mismatch"
            await _sync_billing_order(
                db,
                payment,
                metadata={"flow": "subscription_webhook_payment_failed", "reason": payment.failure_reason},
            )
            await _record_webhook_event(
                db,
                event_type=event,
                payload_json=raw_body.decode("utf-8", errors="ignore"),
                signature=x_razorpay_signature,
                status="FAILED",
                event_key=webhook_event_key,
                payload_hash=payload_hash,
                payment=payment,
                processing_error="amount_mismatch",
            )
            await db.commit()
            return success_response({"event": event, "status": "failed"}, "Payment amount mismatch")

        payment.status = "PAID"
        payment.razorpay_payment_id = payment_id
        payment.failure_reason = None
        payment.verified_at = _now_utc()
        subscription = await _activate_or_refill_subscription(db, user_id=str(payment.user_id), payment=payment, plan=plan)
        await _sync_billing_order(
            db,
            payment,
            metadata={
                "flow": "subscription_webhook_payment_captured",
                "subscription_id": str(subscription.id),
            },
        )
        await _ensure_billing_documents(
            db,
            payment=payment,
            subscription=subscription,
            source="webhook_payment_captured",
        )
        await _record_checkout_coupon_if_needed(db, payment, checkout_metadata)
        await _record_webhook_event(
            db,
            event_type=event,
            payload_json=raw_body.decode("utf-8", errors="ignore"),
            signature=x_razorpay_signature,
            status="PROCESSED",
            event_key=webhook_event_key,
            payload_hash=payload_hash,
            payment=payment,
        )
        await db.commit()
        return success_response({"event": event, "status": "processed"}, "Subscription payment processed")

    if event == "payment.failed":
        entity = payment_entity
        order_id = str(entity.get("order_id") or "")
        if order_id:
            payment = (
                await db.execute(
                    select(Payment)
                    .where(Payment.razorpay_order_id == order_id, Payment.purpose == "SUBSCRIPTION")
                    .with_for_update()
                )
            ).scalar_one_or_none()
            if payment and payment.status != "PAID":
                payment.status = "FAILED"
                payment.failure_reason = str(entity.get("error_description") or "webhook_payment_failed")
                await _sync_billing_order(
                    db,
                    payment,
                    metadata={
                        "flow": "subscription_webhook_payment_failed",
                        "reason": payment.failure_reason,
                    },
                )
                await _record_webhook_event(
                    db,
                    event_type=event,
                    payload_json=raw_body.decode("utf-8", errors="ignore"),
                    signature=x_razorpay_signature,
                    status="PROCESSED",
                    event_key=webhook_event_key,
                    payload_hash=payload_hash,
                    payment=payment,
                )
                await db.commit()
            elif payment:
                await _record_webhook_event(
                    db,
                    event_type=event,
                    payload_json=raw_body.decode("utf-8", errors="ignore"),
                    signature=x_razorpay_signature,
                    status="IGNORED",
                    event_key=webhook_event_key,
                    payload_hash=payload_hash,
                    payment=payment,
                    processing_error="already_paid",
                )
                await db.commit()
            else:
                await _record_webhook_event(
                    db,
                    event_type=event,
                    payload_json=raw_body.decode("utf-8", errors="ignore"),
                    signature=x_razorpay_signature,
                    status="IGNORED",
                    event_key=webhook_event_key,
                    payload_hash=payload_hash,
                    processing_error="payment_not_found",
                )
                await db.commit()
        else:
            await _record_webhook_event(
                db,
                event_type=event,
                payload_json=raw_body.decode("utf-8", errors="ignore"),
                signature=x_razorpay_signature,
                status="FAILED",
                event_key=webhook_event_key,
                payload_hash=payload_hash,
                processing_error="missing_order_id",
            )
            await db.commit()
        return success_response({"event": event, "status": "processed"}, "Failure event processed")
