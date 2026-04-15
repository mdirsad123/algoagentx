from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import settings
from ...core.dependencies import get_current_user, get_db
from ...db.compat import as_uuid_or_str, column_text
from ...db.models import CreditTransaction, CreditTransactionType, Payment, UserCredit
from ...schemas.payments import CreateOrderRequest, VerifyPaymentRequest
from ...utils.api_response import success_response

router = APIRouter()


def _get_key_id() -> str:
    return settings.razorpay_key_id or 'rzp_test_placeholder'


async def _ensure_credit_row(db: AsyncSession, user_id: str) -> UserCredit:
    row = (await db.execute(select(UserCredit).where(column_text(UserCredit.user_id) == str(user_id)))).scalar_one_or_none()
    if row:
        return row
    row = UserCredit(user_id=as_uuid_or_str(user_id), balance=0)
    db.add(row)
    await db.flush()
    return row


@router.post('/create-order')
@router.post('/razorpay/create-order')
async def create_order(payload: CreateOrderRequest, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    amount_inr = int(payload.credits_to_buy)
    payment = Payment(
        user_id=as_uuid_or_str(current_user['user_id']),
        provider='RAZORPAY',
        purpose='CREDITS_TOPUP',
        amount_inr=amount_inr,
        currency='INR',
        status='CREATED',
        razorpay_order_id=f'order_{uuid4().hex[:14]}',
    )
    db.add(payment)
    await db.commit()
    await db.refresh(payment)
    return success_response({
        'order_id': payment.razorpay_order_id,
        'payment_record_id': str(payment.id),
        'amount': amount_inr * 100,
        'currency': payment.currency,
        'razorpay_key_id': _get_key_id(),
        'key_id': _get_key_id(),
    }, 'Order created successfully')


@router.post('/verify')
@router.post('/razorpay/verify')
async def verify_payment(payload: VerifyPaymentRequest, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    payment = (await db.execute(select(Payment).where(Payment.razorpay_order_id == payload.order_id, column_text(Payment.user_id) == str(current_user['user_id'])))).scalar_one_or_none()
    if not payment:
        raise HTTPException(status_code=404, detail='Order not found')
    payment.razorpay_payment_id = payload.razorpay_payment_id
    payment.razorpay_signature = payload.razorpay_signature
    payment.status = 'PAID'

    credit_row = await _ensure_credit_row(db, str(current_user['user_id']))
    old_balance = int(credit_row.balance or 0)
    new_balance = old_balance + int(payment.amount_inr or 0)
    credit_row.balance = new_balance
    db.add(CreditTransaction(
        id=str(uuid4()),
        user_id=as_uuid_or_str(current_user['user_id']),
        transaction_type=CreditTransactionType.CREDIT,
        amount=int(payment.amount_inr or 0),
        balance_after=new_balance,
        description='Credits top-up via Razorpay',
    ))
    await db.commit()
    return success_response({'success': True, 'payment_id': payload.razorpay_payment_id, 'credits_granted': int(payment.amount_inr or 0), 'balance': new_balance}, 'Payment verified successfully')
