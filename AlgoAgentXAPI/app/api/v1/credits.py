from __future__ import annotations

from datetime import datetime, time
from decimal import Decimal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.dependencies import get_admin_user, get_current_user, get_db
from ...db.compat import as_uuid_or_str, column_text
from ...db.models import CreditTransaction, CreditTransactionType, MarketData, Plan, Strategy, User, UserCredit, UserSubscription
from ...billing.cost_rules import CostRules
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


@router.get('/summary')
async def get_credit_summary(current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    user_id = str(current_user['user_id'])
    balance_row = await _ensure_credit_row(db, user_id)

    # Latest active subscription with snapshot fields fallback
    latest_sub_row = (
        await db.execute(
            select(UserSubscription, Plan)
            .outerjoin(Plan, Plan.id == UserSubscription.plan_id)
            .where(column_text(UserSubscription.user_id) == user_id)
            .order_by(UserSubscription.created_at.desc())
            .limit(1)
        )
    ).first()
    plan_name = "FREE"
    included_remaining = 0
    next_reset_date = None
    if latest_sub_row:
        sub, plan = latest_sub_row
        plan_name = str(getattr(sub, "plan_code_snapshot", None) or getattr(plan, "code", None) or "FREE")
        included_remaining = int(getattr(sub, "included_credits_remaining", 0) or 0)
        if getattr(sub, "next_credit_refill_at", None):
            next_reset_date = sub.next_credit_refill_at.isoformat()

    txn_count = (
        await db.execute(
            select(func.count()).select_from(CreditTransaction).where(column_text(CreditTransaction.user_id) == user_id)
        )
    ).scalar() or 0

    debit_count = (
        await db.execute(
            select(func.count()).select_from(CreditTransaction).where(
                column_text(CreditTransaction.user_id) == user_id,
                column_text(CreditTransaction.transaction_type) == CreditTransactionType.DEBIT.name,
            )
        )
    ).scalar() or 0

    credit_count = (
        await db.execute(
            select(func.count()).select_from(CreditTransaction).where(
                column_text(CreditTransaction.user_id) == user_id,
                column_text(CreditTransaction.transaction_type) == CreditTransactionType.CREDIT.name,
            )
        )
    ).scalar() or 0

    refund_count = (
        await db.execute(
            select(func.count()).select_from(CreditTransaction).where(
                column_text(CreditTransaction.user_id) == user_id,
                column_text(CreditTransaction.transaction_type) == CreditTransactionType.REFUND.name,
            )
        )
    ).scalar() or 0

    return success_response(
        {
            "user_id": user_id,
            "credit_balance": _as_int(balance_row.balance),
            "included_remaining": included_remaining,
            "plan_name": plan_name,
            "next_reset_date": next_reset_date,
            "total_transactions": int(txn_count),
            "transaction_counts": {
                "debit": int(debit_count),
                "credit": int(credit_count),
                "refund": int(refund_count),
            },
            "last_updated": balance_row.updated_at.isoformat() if getattr(balance_row, "updated_at", None) else None,
        }
    )


@router.get('/ledger')
@router.get('/transactions')
async def get_credit_ledger(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_id = str(current_user['user_id'])
    rows = (
        await db.execute(
            text(
                """
                SELECT
                    id,
                    CAST(transaction_type AS TEXT) AS transaction_type,
                    amount,
                    balance_after,
                    description,
                    backtest_id,
                    job_id,
                    created_at
                FROM credit_transactions
                WHERE CAST(user_id AS TEXT) = :user_id
                ORDER BY created_at DESC
                OFFSET :offset
                LIMIT :limit
                """
            ),
            {
                "user_id": user_id,
                "offset": int(offset),
                "limit": int(limit),
            },
        )
    ).mappings().all()

    data = [
        {
            'id': str(row.get('id')),
            'type': str(row.get('transaction_type') or '').lower(),
            'transaction_type': str(row.get('transaction_type') or '').lower(),
            'amount': _as_int(row.get('amount')),
            'balance_after': _as_int(row.get('balance_after')),
            'description': row.get('description'),
            'reason': row.get('description'),
            'backtest_id': str(row.get('backtest_id')) if row.get('backtest_id') else None,
            'job_id': str(row.get('job_id')) if row.get('job_id') else None,
            'created_at': row.get('created_at').isoformat() if row.get('created_at') else None,
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


@router.post('/preview-cost')
async def preview_backtest_cost(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    try:
        start_date = payload.get("start_date")
        end_date = payload.get("end_date")
        timeframe = payload.get("timeframe")
        instrument_id = payload.get("instrument_id")
        strategy_id = payload.get("strategy_id")

        if not start_date or not end_date or not timeframe:
            raise HTTPException(status_code=400, detail="start_date, end_date, timeframe are required")

        s_date = datetime.fromisoformat(str(start_date)).date()
        e_date = datetime.fromisoformat(str(end_date)).date()
        if s_date >= e_date:
            raise HTTPException(status_code=400, detail="start_date must be before end_date")

        base_cost = CostRules.calculate_backtest_cost(
            datetime.combine(s_date, time.min),
            datetime.combine(e_date, time.max),
            str(timeframe),
        )

        candle_count = 0
        if instrument_id is not None:
            candle_count = (
                await db.execute(
                    select(func.count()).select_from(MarketData).where(
                        MarketData.instrument_id == int(instrument_id),
                        MarketData.timeframe == str(timeframe),
                        MarketData.timestamp >= datetime.combine(s_date, time.min),
                        MarketData.timestamp <= datetime.combine(e_date, time.max),
                    )
                )
            ).scalar() or 0

        volume_multiplier = 1.0
        if candle_count > 100000:
            volume_multiplier = 2.0
        elif candle_count > 25000:
            volume_multiplier = 1.5
        elif candle_count > 5000:
            volume_multiplier = 1.2

        complexity_multiplier = 1.0
        if strategy_id:
            strategy = await db.get(Strategy, str(strategy_id))
            if strategy and isinstance(strategy.parameters, dict):
                complexity_multiplier += min(0.2, len(strategy.parameters.keys()) * 0.01)

        total_cost = max(1, int(round(base_cost * volume_multiplier * complexity_multiplier)))
        balance_row = await _ensure_credit_row(db, str(current_user['user_id']))
        current_balance = _as_int(balance_row.balance)

        return success_response(
            {
                "total_cost": total_cost,
                "current_balance": current_balance,
                "can_run": current_balance >= total_cost,
                "breakdown": {
                    "base_cost": base_cost,
                    "candle_count": int(candle_count),
                    "multipliers": {
                        "volume": volume_multiplier,
                        "complexity": complexity_multiplier,
                    },
                    "timeframe": timeframe,
                    "date_range_days": (e_date - s_date).days,
                },
            }
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid preview payload: {exc}")
