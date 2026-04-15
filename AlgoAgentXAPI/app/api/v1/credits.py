from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.dependencies import get_admin_user, get_current_user, get_db
from ...db.compat import as_uuid_or_str, column_text
from ...db.models import CreditTransaction, CreditTransactionType, User, UserCredit
from ...utils.api_response import success_response

router = APIRouter()


class CreditAdjustRequest(BaseModel):
    user_id: str
    amount: int = Field(..., gt=0)
    reason: str


def _as_int(value) -> int:
    if value is None:
        return 0
    if isinstance(value, Decimal):
        return int(value)
    return int(value)


async def _ensure_credit_row(db: AsyncSession, user_id: str) -> UserCredit:
    row = (await db.execute(select(UserCredit).where(column_text(UserCredit.user_id) == str(user_id)))).scalar_one_or_none()
    if row:
        return row
    row = UserCredit(user_id=as_uuid_or_str(user_id), balance=0)
    db.add(row)
    await db.flush()
    return row


@router.get('/balance')
async def get_credit_balance(current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    row = await _ensure_credit_row(db, str(current_user['user_id']))
    return success_response({'balance': _as_int(row.balance), 'current_balance': _as_int(row.balance), 'user_id': str(current_user['user_id']), 'last_updated': row.updated_at.isoformat() if getattr(row, 'updated_at', None) else None})


@router.get('/ledger')
@router.get('/transactions')
async def get_credit_ledger(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(CreditTransaction)
        .where(column_text(CreditTransaction.user_id) == str(current_user['user_id']))
        .order_by(CreditTransaction.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    rows = (await db.execute(stmt)).scalars().all()
    data = [
        {
            'id': str(row.id),
            'type': row.transaction_type.value if hasattr(row.transaction_type, 'value') else str(row.transaction_type),
            'transaction_type': row.transaction_type.value if hasattr(row.transaction_type, 'value') else str(row.transaction_type),
            'amount': _as_int(row.amount),
            'balance_after': _as_int(row.balance_after),
            'description': row.description,
            'reason': row.description,
            'backtest_id': str(row.backtest_id) if getattr(row, 'backtest_id', None) else None,
            'job_id': str(row.job_id) if getattr(row, 'job_id', None) else None,
            'created_at': row.created_at.isoformat() if row.created_at else None,
        }
        for row in rows
    ]
    return success_response(data, 'No data found' if not data else None)


async def _adjust(db: AsyncSession, payload: CreditAdjustRequest, tx_type: CreditTransactionType):
    user = (await db.execute(select(User).where(column_text(User.id) == str(payload.user_id)))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail='User not found')
    row = await _ensure_credit_row(db, payload.user_id)
    current = _as_int(row.balance)
    signed = payload.amount if tx_type != CreditTransactionType.DEBIT else -payload.amount
    new_balance = current + signed
    if new_balance < 0:
        raise HTTPException(status_code=400, detail='Insufficient credit balance')
    row.balance = new_balance
    tx = CreditTransaction(
        id=str(uuid4()),
        user_id=as_uuid_or_str(payload.user_id),
        transaction_type=tx_type,
        amount=payload.amount,
        balance_after=new_balance,
        description=payload.reason,
    )
    db.add(tx)
    await db.commit()
    return success_response({'balance': new_balance, 'transaction_id': str(tx.id)}, 'Credits updated successfully')


@router.post('/admin/add')
async def add_credits_admin(payload: CreditAdjustRequest, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_admin_user)):
    return await _adjust(db, payload, CreditTransactionType.CREDIT)


@router.post('/admin/deduct')
async def deduct_credits_admin(payload: CreditAdjustRequest, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_admin_user)):
    return await _adjust(db, payload, CreditTransactionType.DEBIT)
