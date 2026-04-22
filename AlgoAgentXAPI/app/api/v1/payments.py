from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from uuid import uuid4

import razorpay
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import settings
from ...core.dependencies import get_current_user, get_db
from ...db.compat import as_uuid_or_str, column_text, table_has_column
from ...db.models import BillingOrder, CreditTransaction, CreditTransactionType, Payment, UserCredit
from ...schemas.payments import (
    CreateOrderRequest,
    PaymentFailureRequest,
    VerifyPaymentRequest,
)
from ...utils.api_response import success_response

router = APIRouter()
logger = logging.getLogger(__name__)


DEFAULT_TOPUP_PACKS = [
    {"code": "PACK_100", "credits": 100, "amount_inr": 100, "label": "₹100", "popular": False},
    {"code": "PACK_250", "credits": 250, "amount_inr": 250, "label": "₹250", "popular": False},
    {"code": "PACK_500", "credits": 500, "amount_inr": 500, "label": "₹500", "popular": True},
    {"code": "PACK_1000", "credits": 1000, "amount_inr": 1000, "label": "₹1000", "popular": False},
]


def _get_key_id() -> str:
    return settings.razorpay_key_id or ""


def _is_razorpay_configured() -> bool:
    return bool(settings.razorpay_key_id and settings.razorpay_key_secret)


def _get_topup_rules() -> dict:
    packs = DEFAULT_TOPUP_PACKS
    custom_json = getattr(settings, "credits_topup_packs_json", None)
    if custom_json:
        try:
            parsed = json.loads(custom_json)
            if isinstance(parsed, list):
                candidate = []
                for item in parsed:
                    if not isinstance(item, dict):
                        continue
                    credits = int(item.get("credits") or 0)
                    amount_inr = int(item.get("amount_inr") or credits)
                    code = str(item.get("code") or "").strip().upper()
                    if not code or credits <= 0 or amount_inr <= 0:
                        continue
                    candidate.append(
                        {
                            "code": code,
                            "credits": credits,
                            "amount_inr": amount_inr,
                            "label": str(item.get("label") or f"₹{amount_inr}"),
                            "popular": bool(item.get("popular", False)),
                        }
                    )
                if candidate:
                    packs = candidate
        except Exception:
            logger.warning("Invalid CREDITS_TOPUP_PACKS_JSON, using default pack config")

    return {
        "allow_custom_topup": bool(getattr(settings, "credits_allow_custom_topup", True)),
        "min_custom_credits": int(getattr(settings, "credits_min_custom_topup", 1) or 1),
        "max_custom_credits": int(getattr(settings, "credits_max_custom_topup", 100000) or 100000),
        "packs": packs,
    }


def _resolve_topup_request(payload: CreateOrderRequest) -> dict:
    rules = _get_topup_rules()
    packs = rules["packs"]

    if payload.pack_code:
        pack_code = str(payload.pack_code).strip().upper()
        selected = next((p for p in packs if p["code"] == pack_code), None)
        if not selected:
            raise HTTPException(status_code=400, detail="Invalid pack_code")
        return {
            "pack_code": selected["code"],
            "credits": int(selected["credits"]),
            "amount_inr": int(selected["amount_inr"]),
        }

    if not rules["allow_custom_topup"]:
        raise HTTPException(status_code=400, detail="Custom credit top-up is disabled")

    credits = int(payload.credits_to_buy or 0)
    if credits < rules["min_custom_credits"] or credits > rules["max_custom_credits"]:
        raise HTTPException(
            status_code=400,
            detail=f"Custom credits must be between {rules['min_custom_credits']} and {rules['max_custom_credits']}",
        )
    return {
        "pack_code": None,
        "credits": credits,
        "amount_inr": credits,  # 1 credit = ₹1
    }


def _get_razorpay_client() -> razorpay.Client:
    key_id = settings.razorpay_key_id
    key_secret = settings.razorpay_key_secret
    if not key_id or not key_secret:
        raise HTTPException(status_code=503, detail="Razorpay is not configured")
    return razorpay.Client(auth=(key_id, key_secret))


async def _ensure_credit_row(db: AsyncSession, user_id: str) -> UserCredit:
    row = (
        await db.execute(
            select(UserCredit)
            .where(column_text(UserCredit.user_id) == str(user_id))
            .with_for_update()
        )
    ).scalar_one_or_none()
    if row:
        return row
    row = UserCredit(user_id=str(user_id), balance=0)
    db.add(row)
    await db.flush()
    return row


async def _sync_billing_order(db: AsyncSession, payment: Payment, *, metadata: dict | None = None) -> None:
    if not await table_has_column(db, "billing_orders", "id"):
        return

    billing_order_id = str(payment.billing_order_id or payment.razorpay_order_id or f"ord_{uuid4().hex[:24]}")
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
            purpose=str(payment.purpose or ""),
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
    existing.purpose = str(payment.purpose or existing.purpose or "")
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


async def _rollback_safely(db: AsyncSession) -> None:
    try:
        await db.rollback()
    except Exception:
        pass


@router.get('/config')
@router.get('/razorpay/config')
async def get_payment_config():
    rules = _get_topup_rules()
    configured = _is_razorpay_configured()
    return success_response(
        {
            "key_id": _get_key_id(),
            "currency": "INR",
            "configured": configured,
            "allow_custom_topup": rules["allow_custom_topup"],
            "min_custom_credits": rules["min_custom_credits"],
            "max_custom_credits": rules["max_custom_credits"],
            "packs": rules["packs"],
        }
    )


@router.post('/create-order')
@router.post('/razorpay/create-order')
async def create_order(payload: CreateOrderRequest, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    resolved = _resolve_topup_request(payload)
    client = _get_razorpay_client()
    user_id = str(current_user['user_id'])
    billing_order_id = f"ord_{uuid4().hex[:24]}"

    try:
        razorpay_order = client.order.create(
            data={
                "amount": int(resolved["amount_inr"]) * 100,
                "currency": "INR",
                "receipt": billing_order_id,
                "payment_capture": 1,
                "notes": {
                    "user_id": user_id,
                    "purpose": "CREDITS_TOPUP",
                    "credits": str(int(resolved["credits"])),
                    "pack_code": str(resolved["pack_code"] or "CUSTOM"),
                },
            }
        )
    except Exception as exc:
        logger.exception("Failed to create Razorpay order")
        raise HTTPException(status_code=502, detail="Unable to create Razorpay order") from exc

    try:
        payment = Payment(
            user_id=user_id,
            provider='RAZORPAY',
            purpose='CREDITS_TOPUP',
            amount_inr=int(resolved["amount_inr"]),
            currency='INR',
            status='CREATED',
            billing_order_id=billing_order_id,
            razorpay_order_id=str(razorpay_order.get("id") or ""),
        )
        db.add(payment)
        await db.flush()
        await _sync_billing_order(
            db,
            payment,
            metadata={
                "pack_code": resolved.get("pack_code"),
                "credits": int(resolved.get("credits") or 0),
                "flow": "credits_topup_create_order",
            },
        )
        await db.commit()
        await db.refresh(payment)
    except SQLAlchemyError as exc:
        await _rollback_safely(db)
        logger.exception("Failed to persist created payment order")
        raise HTTPException(status_code=500, detail="Unable to save payment order. Please try again.") from exc

    return success_response({
        'order_id': payment.razorpay_order_id,
        'billing_order_id': payment.billing_order_id,
        'payment_record_id': str(payment.id),
        'credits': int(resolved["credits"]),
        'amount': int(resolved["amount_inr"]) * 100,
        'amount_inr': int(resolved["amount_inr"]),
        'currency': payment.currency,
        'razorpay_key_id': _get_key_id(),
        'key_id': _get_key_id(),
        'status': payment.status,
    }, 'Order created successfully')


@router.post('/verify')
@router.post('/razorpay/verify')
async def verify_payment(payload: VerifyPaymentRequest, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    user_id = str(current_user['user_id'])
    client = _get_razorpay_client()

    payment = (
        await db.execute(
            select(Payment)
            .where(
                Payment.razorpay_order_id == payload.order_id,
                column_text(Payment.user_id) == user_id,
            )
            .with_for_update()
        )
    ).scalar_one_or_none()
    if not payment:
        raise HTTPException(status_code=404, detail='Order not found')

    if payment.status == 'PAID':
        if payment.razorpay_payment_id and payment.razorpay_payment_id != payload.razorpay_payment_id:
            raise HTTPException(status_code=409, detail='Order already paid with a different payment id')
        credit_row = await _ensure_credit_row(db, user_id)
        return success_response(
            {
                'success': True,
                'payment_id': payment.razorpay_payment_id or payload.razorpay_payment_id,
                'order_id': payment.razorpay_order_id,
                'billing_order_id': payment.billing_order_id,
                'credits_granted': 0,
                'balance': int(credit_row.balance or 0),
                'status': payment.status,
                'idempotent': True,
                'message': 'Payment already verified',
            },
            'Payment already verified',
        )

    duplicate_paid_payment = (
        await db.execute(
            select(Payment).where(
                Payment.razorpay_payment_id == payload.razorpay_payment_id,
                Payment.status == 'PAID',
            )
        )
    ).scalar_one_or_none()
    if duplicate_paid_payment and str(duplicate_paid_payment.id) != str(payment.id):
        raise HTTPException(status_code=409, detail='This Razorpay payment is already linked to another order')

    try:
        client.utility.verify_payment_signature(
            {
                'razorpay_order_id': payload.order_id,
                'razorpay_payment_id': payload.razorpay_payment_id,
                'razorpay_signature': payload.razorpay_signature,
            }
        )
    except Exception as exc:
        payment.status = 'FAILED'
        payment.failure_reason = 'signature_verification_failed'
        await _sync_billing_order(
            db,
            payment,
            metadata={
                "flow": "credits_topup_verify_failed",
                "reason": "signature_verification_failed",
            },
        )
        try:
            await db.commit()
        except SQLAlchemyError:
            await _rollback_safely(db)
        raise HTTPException(status_code=400, detail='Invalid payment signature') from exc

    try:
        razorpay_payment = client.payment.fetch(payload.razorpay_payment_id)
        fetched_order_id = str(razorpay_payment.get('order_id') or '')
        fetched_status = str(razorpay_payment.get('status') or '').lower()
    except Exception as exc:
        logger.exception('Failed to fetch Razorpay payment details')
        raise HTTPException(status_code=502, detail='Unable to verify payment with Razorpay') from exc

    if fetched_order_id != str(payment.razorpay_order_id):
        payment.status = 'FAILED'
        payment.failure_reason = 'order_mismatch'
        await _sync_billing_order(
            db,
            payment,
            metadata={
                "flow": "credits_topup_verify_failed",
                "reason": "order_mismatch",
            },
        )
        try:
            await db.commit()
        except SQLAlchemyError:
            await _rollback_safely(db)
        raise HTTPException(status_code=400, detail='Payment order mismatch')

    if fetched_status not in {'captured', 'authorized'}:
        payment.status = 'FAILED'
        payment.failure_reason = f'payment_status_{fetched_status or "unknown"}'
        await _sync_billing_order(
            db,
            payment,
            metadata={
                "flow": "credits_topup_verify_failed",
                "reason": payment.failure_reason,
            },
        )
        try:
            await db.commit()
        except SQLAlchemyError:
            await _rollback_safely(db)
        raise HTTPException(status_code=400, detail='Payment is not successful')

    granted_credits = int(payment.amount_inr or 0)
    try:
        payment.razorpay_payment_id = payload.razorpay_payment_id
        payment.razorpay_signature = payload.razorpay_signature
        payment.status = 'PAID'
        payment.verified_at = datetime.now(timezone.utc)
        payment.failure_reason = None

        credit_row = await _ensure_credit_row(db, user_id)
        old_balance = int(credit_row.balance or 0)
        new_balance = old_balance + granted_credits
        credit_row.balance = new_balance

        description = (
            f"Credits top-up via Razorpay | billing_order_id={payment.billing_order_id} | "
            f"razorpay_order_id={payment.razorpay_order_id} | razorpay_payment_id={payload.razorpay_payment_id}"
        )

        db.add(CreditTransaction(
            id=str(uuid4()),
            user_id=as_uuid_or_str(user_id),
            transaction_type=CreditTransactionType.CREDIT,
            amount=granted_credits,
            balance_after=new_balance,
            description=description,
        ))

        await _sync_billing_order(
            db,
            payment,
            metadata={
                "flow": "credits_topup_verify",
                "credits_granted": granted_credits,
                "idempotent": False,
            },
        )

        await db.commit()
    except SQLAlchemyError as exc:
        await _rollback_safely(db)
        logger.exception("Failed to persist verified payment and wallet credit grant")
        raise HTTPException(status_code=500, detail='Payment captured but wallet update failed. Please retry verification.') from exc

    return success_response(
        {
            'success': True,
            'payment_id': payload.razorpay_payment_id,
            'order_id': payment.razorpay_order_id,
            'billing_order_id': payment.billing_order_id,
            'credits_granted': granted_credits,
            'balance': new_balance,
            'status': payment.status,
            'idempotent': False,
            'message': 'Payment verified successfully',
        },
        'Payment verified successfully',
    )


@router.post('/failure')
@router.post('/razorpay/failure')
async def mark_payment_failure(payload: PaymentFailureRequest, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    user_id = str(current_user['user_id'])
    payment = (
        await db.execute(
            select(Payment).where(
                Payment.razorpay_order_id == payload.order_id,
                column_text(Payment.user_id) == user_id,
            )
        )
    ).scalar_one_or_none()
    if not payment:
        raise HTTPException(status_code=404, detail='Order not found')

    if payment.status == 'PAID':
        return success_response(
            {
                'order_id': payment.razorpay_order_id,
                'billing_order_id': payment.billing_order_id,
                'status': payment.status,
            },
            'Order is already paid',
        )

    detail = payload.reason or 'payment_failed_or_cancelled'
    if payload.code:
        detail = f"{detail} ({payload.code})"

    payment.status = 'FAILED'
    payment.failure_reason = detail
    try:
        await _sync_billing_order(
            db,
            payment,
            metadata={
                "flow": "credits_topup_failure",
                "reason": detail,
            },
        )
        await db.commit()
    except SQLAlchemyError as exc:
        await _rollback_safely(db)
        logger.exception("Failed to persist payment failure state")
        raise HTTPException(status_code=500, detail='Unable to save failed payment status') from exc

    return success_response(
        {
            'order_id': payment.razorpay_order_id,
            'billing_order_id': payment.billing_order_id,
            'status': payment.status,
        },
        'Payment marked as failed',
    )
