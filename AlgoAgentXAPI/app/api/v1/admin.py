from __future__ import annotations

import json
from datetime import datetime, timedelta
from decimal import Decimal
from math import ceil
from typing import Any, Optional
from uuid import uuid4
import logging

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import String, and_, cast, delete, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.dependencies import get_admin_user, get_current_user, get_db
from ...utils.api_response import success_response
from ...db.models import (
    BillingOrder,
    CreditTransaction,
    CreditTransactionType,
    Instrument,
    JobStatus,
    MarketData,
    Payment,
    PerformanceMetric,
    Plan,
    Strategy,
    StrategyRequest,
    User,
    UserCredit,
    UserSubscription,
    SupportTicket,
    SupportTicketReply,
)
from ...db.compat import as_uuid_or_str, column_text, table_has_column
from ...services.credits.management import CreditManagementService
from ...services.pricing.backtest_pricing_service import BacktestPricingService

logger = logging.getLogger(__name__)
router = APIRouter()


class UserCreateRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    fullname: Optional[str] = None
    mobile: Optional[str] = None
    role: str = "user"

class UserUpdateRequest(BaseModel):
    email: Optional[EmailStr] = None
    fullname: Optional[str] = None
    mobile: Optional[str] = None
    role: Optional[str] = None


class UserStatusRequest(BaseModel):
    is_active: bool


class UserRoleRequest(BaseModel):
    role: str


class CreditAdjustRequest(BaseModel):
    user_id: str
    amount: int = Field(..., gt=0)
    reason: str = Field(..., min_length=2)


class StrategyDecisionRequest(BaseModel):
    status: str = Field(..., pattern="^(UNDER_DEVELOPMENT|NEEDS_CLARIFICATION|REJECTED|DEPLOYED)$")
    admin_notes: Optional[str] = None


class SubscriptionUpdateRequest(BaseModel):
    status: Optional[str] = None
    renews: Optional[bool] = None
    end_at: Optional[datetime] = None


class OrderStatusRequest(BaseModel):
    status: str


class PaymentRefundRequest(BaseModel):
    note: Optional[str] = None


class BacktestPricingRuleSetUpdateRequest(BaseModel):
    name: Optional[str] = None
    version: Optional[str] = None
    description: Optional[str] = None

    base_cost: Optional[float] = Field(default=None, gt=0)
    range_days_step: Optional[int] = Field(default=None, ge=1)
    min_credit_charge: Optional[int] = Field(default=None, ge=1)
    max_credit_charge: Optional[int] = Field(default=None, ge=1)

    date_range_buckets: Optional[list[dict[str, Any]]] = None
    timeframe_multipliers: Optional[list[dict[str, Any]]] = None

    strategy_complexity_enabled: Optional[bool] = None
    strategy_complexity_step: Optional[float] = Field(default=None, ge=0)
    strategy_complexity_cap: Optional[float] = Field(default=None, ge=0)

    plan_discounts: Optional[dict[str, float]] = None


class BacktestPricingRuleSetActivateRequest(BaseModel):
    rule_set_id: str


class MarketDataHookRequest(BaseModel):
    instrument_id: Optional[int] = None
    timeframe: Optional[str] = None
    source: Optional[str] = None
    note: Optional[str] = None


def _serialize(value: Any) -> Any:
    if isinstance(value, Decimal):
        try:
            return int(value) if value == int(value) else float(value)
        except Exception:
            return float(value)
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _parse_iso_datetime(value: Optional[str], *, field_name: str) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        raise HTTPException(status_code=400, detail=f"Invalid {field_name} datetime format")


async def _user_is_active_value(db: AsyncSession, user: User) -> bool:
    if await table_has_column(db, "users", "is_active"):
        result = await db.execute(text("SELECT is_active FROM users WHERE id = :user_id"), {"user_id": str(user.id)})
        value = result.scalar()
        return True if value is None else bool(value)
    return True


async def _ensure_user_credit_row(db: AsyncSession, user_id: str) -> UserCredit:
    row = (await db.execute(select(UserCredit).where(column_text(UserCredit.user_id) == str(user_id)))).scalar_one_or_none()
    if row:
        return row
    row = UserCredit(user_id=as_uuid_or_str(user_id), balance=0)
    db.add(row)
    await db.flush()
    return row


async def _get_credit_balance_map(db: AsyncSession, user_ids: list[str]) -> dict[str, int]:
    if not user_ids:
        return {}
    result = await db.execute(select(UserCredit).where(column_text(UserCredit.user_id).in_([str(uid) for uid in user_ids])))
    return {str(row.user_id): int(row.balance or 0) for row in result.scalars().all()}


async def _get_subscription_map(db: AsyncSession, user_ids: list[str]) -> dict[str, dict[str, Any]]:
    if not user_ids:
        return {}
    stmt = (
        select(UserSubscription, Plan)
        .outerjoin(Plan, Plan.id == UserSubscription.plan_id)
        .where(cast(UserSubscription.user_id, String).in_([str(uid) for uid in user_ids]))
        .order_by(UserSubscription.created_at.desc())
    )
    result = await db.execute(stmt)
    subscription_map: dict[str, dict[str, Any]] = {}
    for sub, plan in result.all():
        key = str(sub.user_id)
        if key in subscription_map:
            continue
        plan_code = str(getattr(sub, "plan_code_snapshot", None) or getattr(plan, "code", None) or "FREE").upper()
        billing_period = str(getattr(sub, "billing_period_snapshot", None) or getattr(plan, "billing_period", None) or "NONE").upper()
        subscription_map[key] = {
            "plan": plan_code,
            "plan_code": plan_code,
            "billing_period": billing_period,
            "status": sub.status,
            "subscription_id": str(sub.id),
            "included_credits_total": int(getattr(sub, "included_credits_total", None) or getattr(plan, "included_credits", 0) or 0),
            "included_credits_remaining": int(getattr(sub, "included_credits_remaining", None) or 0),
        }
    return subscription_map


async def _adjust_credits(
    db: AsyncSession,
    user_id: str,
    amount: int,
    reason: str,
    transaction_type: CreditTransactionType,
    actor_user_id: Optional[str] = None,
    source: str = "admin_manual",
) -> dict[str, Any]:
    user_id_or_email = str(user_id or "").strip()
    user = None
    if "@" in user_id_or_email:
        user = (await db.execute(select(User).where(User.email == user_id_or_email))).scalar_one_or_none()
    else:
        user = (await db.execute(select(User).where(column_text(User.id) == user_id_or_email))).scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    credit_row = await _ensure_user_credit_row(db, str(user.id))
    balance_before = int(credit_row.balance or 0)
    signed_amount = amount if transaction_type != CreditTransactionType.DEBIT else -amount
    new_balance = balance_before + signed_amount
    if new_balance < 0:
        raise HTTPException(status_code=400, detail="Insufficient credit balance")

    credit_row.balance = new_balance

    txn_id = str(uuid4())
    has_actor_user_id = await table_has_column(db, "credit_transactions", "actor_user_id")
    has_source = await table_has_column(db, "credit_transactions", "source")
    normalized_reason = str(reason or "").strip()

    description_value = normalized_reason
    if not has_source or not has_actor_user_id:
        fallback_audit = [normalized_reason or "admin_manual_credit_adjustment", f"source={source}"]
        if actor_user_id:
            fallback_audit.append(f"actor={actor_user_id}")
        description_value = " | ".join(fallback_audit)

    insert_columns = [
        "id",
        "user_id",
        "transaction_type",
        "amount",
        "balance_after",
        "description",
    ]
    insert_params: dict[str, Any] = {
        "id": txn_id,
        "user_id": as_uuid_or_str(str(user.id)),
        "transaction_type": transaction_type.name,
        "amount": amount,
        "balance_after": new_balance,
        "description": description_value,
    }

    if has_actor_user_id:
        insert_columns.append("actor_user_id")
        insert_params["actor_user_id"] = actor_user_id
    if has_source:
        insert_columns.append("source")
        insert_params["source"] = source

    await db.execute(
        text(
            f"""
            INSERT INTO credit_transactions ({', '.join(insert_columns)})
            VALUES ({', '.join(':' + col for col in insert_columns)})
            """
        ),
        insert_params,
    )

    created_at = (
        await db.execute(
            text("SELECT created_at FROM credit_transactions WHERE id = :txn_id"),
            {"txn_id": txn_id},
        )
    ).scalar_one_or_none()

    await db.commit()
    return {
        "message": "Credits updated successfully",
        "transaction": {
            "id": txn_id,
            "user_id": str(user.id),
            "user_email": user.email,
            "credits": signed_amount,
            "type": transaction_type.value,
            "reason": normalized_reason,
            "source_type": source if has_source else None,
            "actor_user_id": actor_user_id if has_actor_user_id else None,
            "balance_after": new_balance,
            "created_at": _serialize(created_at),
        },
    }


async def _get_backtest_billing_snapshot(db: AsyncSession, backtest_ids: list[str]) -> dict[str, dict[str, Any]]:
    if not backtest_ids:
        return {}

    rows = (
        await db.execute(
            select(
                CreditTransaction.backtest_id,
                CreditTransaction.id,
                CreditTransaction.amount,
                CreditTransaction.transaction_type,
                CreditTransaction.source,
            )
            .where(CreditTransaction.backtest_id.in_(backtest_ids))
            .order_by(CreditTransaction.created_at.desc())
        )
    ).all()

    out: dict[str, dict[str, Any]] = {}
    for backtest_id, txn_id, amount, transaction_type, source in rows:
        key = str(backtest_id)
        if key not in out:
            out[key] = {
                "debit_transaction_id": None,
                "debit_transaction_ids": [],
                "refund_transaction_ids": [],
                "credit_cost": 0.0,
                "effective_credit_cost": 0.0,
                "included_debited": 0.0,
                "wallet_debited": 0.0,
                "included_refunded": 0.0,
                "wallet_refunded": 0.0,
                "refund_total": 0.0,
                "charge_status": "not_charged",
            }

        tx_type = transaction_type.name if hasattr(transaction_type, "name") else str(transaction_type).upper()
        tx_source = str(source or "").lower()
        tx_amount = float(amount or 0)

        if tx_type == CreditTransactionType.DEBIT.name:
            if out[key]["debit_transaction_id"] is None:
                out[key]["debit_transaction_id"] = str(txn_id)
            out[key]["debit_transaction_ids"].append(str(txn_id))
            out[key]["credit_cost"] += tx_amount
            if tx_source == CreditManagementService.SOURCE_BACKTEST_INCLUDED_DEBIT:
                out[key]["included_debited"] += tx_amount
            else:
                out[key]["wallet_debited"] += tx_amount
            continue

        if tx_type == CreditTransactionType.REFUND.name:
            out[key]["refund_transaction_ids"].append(str(txn_id))
            if tx_source == CreditManagementService.SOURCE_BACKTEST_INCLUDED_REFUND:
                out[key]["included_refunded"] += tx_amount
            else:
                out[key]["wallet_refunded"] += tx_amount

    for key in out.keys():
        debit_total = float(out[key]["credit_cost"])
        refund_total = float(out[key]["included_refunded"] + out[key]["wallet_refunded"])
        out[key]["refund_total"] = refund_total
        out[key]["effective_credit_cost"] = max(debit_total - refund_total, 0.0)

        if debit_total <= 0:
            out[key]["charge_status"] = "not_charged"
        elif out[key]["effective_credit_cost"] <= 0 and refund_total > 0:
            out[key]["charge_status"] = "refunded"
        elif refund_total > 0:
            out[key]["charge_status"] = "partially_refunded"
        else:
            out[key]["charge_status"] = "charged"

    return out


@router.get("/metrics")
async def get_admin_metrics(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_admin_user),
):
    total_users = (await db.execute(select(func.count()).select_from(User))).scalar() or 0
    has_is_active = await table_has_column(db, "users", "is_active")
    if has_is_active:
        active_users = (await db.execute(text("SELECT COUNT(*) FROM users WHERE is_active = true"))).scalar() or 0
    else:
        active_users = total_users

    paid_statuses = ["PAID", "captured", "success", "SUCCESS"]
    total_revenue = (
        await db.execute(select(func.coalesce(func.sum(Payment.amount_inr), 0)).where(Payment.status.in_(paid_statuses)))
    ).scalar() or 0
    total_credits_issued = (
        await db.execute(
            select(func.coalesce(func.sum(CreditTransaction.amount), 0)).where(
                func.lower(cast(CreditTransaction.transaction_type, String)).in_([
                    CreditTransactionType.CREDIT.value,
                    CreditTransactionType.CREDIT.name.lower(),
                    CreditTransactionType.REFUND.value,
                    CreditTransactionType.REFUND.name.lower(),
                ])
            )
        )
    ).scalar() or 0
    total_subscriptions = (await db.execute(select(func.count()).select_from(UserSubscription))).scalar() or 0
    pending_strategy_requests = (
        await db.execute(
            select(func.count()).select_from(StrategyRequest).where(
                StrategyRequest.status.in_(["PENDING", "UNDER_DEVELOPMENT", "NEEDS_CLARIFICATION"])
            )
        )
    ).scalar() or 0
    total_backtests = (await db.execute(select(func.count()).select_from(PerformanceMetric))).scalar() or 0
    has_billing_orders = await table_has_column(db, "billing_orders", "id")
    if has_billing_orders:
        total_orders = (await db.execute(select(func.count()).select_from(BillingOrder))).scalar() or 0
    else:
        total_orders = (await db.execute(select(func.count()).select_from(Payment))).scalar() or 0

    recent_user_rows = (await db.execute(select(User).order_by(User.created_at.desc()).limit(5))).scalars().all()
    user_ids = [str(user.id) for user in recent_user_rows]
    balances = await _get_credit_balance_map(db, user_ids)
    subs = await _get_subscription_map(db, user_ids)
    recent_users = []
    for user in recent_user_rows:
        uid = str(user.id)
        recent_users.append(
            {
                "id": uid,
                "email": user.email,
                "fullname": user.fullname,
                "role": user.role,
                "is_active": await _user_is_active_value(db, user),
                "mobile": user.mobile,
                "plan": subs.get(uid, {}).get("plan", "FREE"),
                "billing_period": subs.get(uid, {}).get("billing_period", "NONE"),
                "subscription_status": subs.get(uid, {}).get("status"),
                "credits": balances.get(uid, 0),
                "created_at": _serialize(user.created_at),
            }
        )

    payment_stmt = (
        select(Payment, User.email, User.fullname)
        .outerjoin(User, cast(User.id, String) == cast(Payment.user_id, String))
        .order_by(Payment.created_at.desc())
        .limit(5)
    )
    payment_rows = (await db.execute(payment_stmt)).all()
    recent_payments = []
    recent_orders = []
    for payment, email, fullname in payment_rows:
        payload = {
            "id": str(payment.id),
            "user_id": str(payment.user_id),
            "user_email": email or "—",
            "user_name": fullname or email or "—",
            "amount": int(payment.amount_inr or 0),
            "currency": payment.currency or "INR",
            "status": payment.status,
            "payment_method": payment.provider,
            "purpose": payment.purpose,
            "transaction_id": payment.razorpay_payment_id,
            "razorpay_order_id": payment.razorpay_order_id,
            "created_at": _serialize(payment.created_at),
        }
        recent_payments.append(payload)

    if has_billing_orders:
        order_rows = (
            await db.execute(
                select(BillingOrder, User.email, User.fullname)
                .outerjoin(User, cast(User.id, String) == cast(BillingOrder.user_id, String))
                .order_by(BillingOrder.created_at.desc())
                .limit(5)
            )
        ).all()
        for order, email, fullname in order_rows:
            recent_orders.append(
                {
                    "id": str(order.id),
                    "user_id": str(order.user_id),
                    "user_email": email or "—",
                    "user_name": fullname or email or "—",
                    "order_number": order.billing_order_id or order.razorpay_order_id or str(order.id),
                    "status": order.status,
                    "total_amount": int(order.amount_inr or 0),
                    "currency": order.currency or "INR",
                    "payment_method": order.provider,
                    "purpose": order.purpose,
                    "created_at": _serialize(order.created_at),
                }
            )
    else:
        for payment, email, fullname in payment_rows:
            recent_orders.append(
                {
                    "id": str(payment.id),
                    "user_id": str(payment.user_id),
                    "user_email": email or "—",
                    "user_name": fullname or email or "—",
                    "order_number": payment.razorpay_order_id or str(payment.id),
                    "status": payment.status,
                    "total_amount": int(payment.amount_inr or 0),
                    "currency": payment.currency or "INR",
                    "payment_method": payment.provider,
                    "purpose": payment.purpose,
                    "created_at": _serialize(payment.created_at),
                }
            )

    # Calculate additional metrics for test compatibility
    paid_count = (await db.execute(select(func.count()).select_from(Payment).where(Payment.status.in_(paid_statuses)))).scalar() or 0
    failed_count = total_orders - paid_count
    
    total_credits_used = (
        await db.execute(
            select(func.coalesce(func.sum(CreditTransaction.amount), 0)).where(
                func.lower(cast(CreditTransaction.transaction_type, String)).in_([
                    CreditTransactionType.DEBIT.value,
                    CreditTransactionType.DEBIT.name.lower(),
                ])
            )
        )
    ).scalar() or 0
    
    active_subscriptions = (await db.execute(select(func.count()).select_from(UserSubscription).where(UserSubscription.status == "ACTIVE"))).scalar() or 0
    
    # AI Screener Jobs
    try:
        ai_jobs_total = (await db.execute(text("SELECT COUNT(*) FROM job_status WHERE job_type = 'ai_screener'"))).scalar() or 0
        ai_jobs_completed = (await db.execute(text("SELECT COUNT(*) FROM job_status WHERE job_type = 'ai_screener' AND status = 'completed'"))).scalar() or 0
        ai_jobs_failed = ai_jobs_total - ai_jobs_completed
    except Exception:
        await db.rollback()
        ai_jobs_total = 0
        ai_jobs_completed = 0
        ai_jobs_failed = 0
    
    # Support Tickets / Notifications
    try:
        tickets_total = (await db.execute(text("SELECT COUNT(*) FROM notifications"))).scalar() or 0
        tickets_unread = (await db.execute(text("SELECT COUNT(*) FROM notifications WHERE status = 'unread'"))).scalar() or 0
    except Exception:
        await db.rollback()
        tickets_total = 0
        tickets_unread = 0
    
    try:
        total_strategies = (await db.execute(select(func.count()).select_from(Strategy))).scalar() or 0
    except Exception:
        await db.rollback()
        total_strategies = 0

    return success_response({
        "users": {"total": total_users, "active": active_users, "recent": recent_users},
        "payments": {
            "total": total_orders,
            "paid": paid_count,
            "failed": failed_count,
            "revenue": float(total_revenue),
            "revenue_total": float(total_revenue),
            "recent": recent_payments
        },
        "subscriptions": {
            "total": total_subscriptions,
            "active": active_subscriptions
        },
        "credits": {
            "total": int(total_credits_issued),
            "total_issued": int(total_credits_issued),
            "used": int(total_credits_used),
            "available": int(total_credits_issued - total_credits_used),
            "active_subscriptions": active_subscriptions,
        },
        "strategies": {
            "pending": pending_strategy_requests,
            "total": total_strategies
        },
        "backtests": {"total": total_backtests},
        "orders": {"total": total_orders, "recent": recent_orders},
        "ai_screener_jobs": {
            "total": ai_jobs_total,
            "completed": ai_jobs_completed,
            "failed": ai_jobs_failed,
            "recent": []
        },
        "support_tickets": {
            "total": tickets_total,
            "unread": tickets_unread
        },
        "recent_activity": {
            "recent_users": recent_users[:5],
            "recent_payments": recent_payments[:5],
            "recent_jobs": []
        },
        "generated_at": datetime.utcnow().isoformat()
    })


@router.get("/users")
async def get_admin_users(
    skip: int = 0,
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_admin_user),
):
    query = select(User)
    count_query = select(func.count()).select_from(User)
    if search:
        search_filter = or_(
            User.email.ilike(f"%{search}%"),
            User.fullname.ilike(f"%{search}%"),
            User.mobile.ilike(f"%{search}%"),
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

    rows = (await db.execute(query.order_by(User.created_at.desc()).offset(skip).limit(limit))).scalars().all()
    total = (await db.execute(count_query)).scalar() or 0
    user_ids = [str(row.id) for row in rows]
    balances = await _get_credit_balance_map(db, user_ids)
    subs = await _get_subscription_map(db, user_ids)

    items = []
    for user in rows:
        uid = str(user.id)
        items.append(
            {
                "id": uid,
                "email": user.email,
                "role": user.role,
                "is_active": await _user_is_active_value(db, user),
                "fullname": user.fullname,
                "mobile": user.mobile,
                "plan": subs.get(uid, {}).get("plan", "FREE"),
                "billing_period": subs.get(uid, {}).get("billing_period", "NONE"),
                "subscription_status": subs.get(uid, {}).get("status"),
                "credits": balances.get(uid, 0),
                "created_at": _serialize(user.created_at),
            }
        )
    return success_response({"items": items, "total": total, "skip": skip, "limit": limit}, "No data found" if not items else None)


@router.post("/users", status_code=201)
async def create_admin_user(
    payload: UserCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_admin_user),
):
    exists = (await db.execute(select(User).where(User.email == payload.email))).scalar_one_or_none()
    if exists:
        raise HTTPException(status_code=400, detail="User with this email already exists")

    password_hash = bcrypt.hashpw(payload.password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    user = User(
        email=payload.email,
        password_hash=password_hash,
        role=payload.role,
        fullname=payload.fullname,
        mobile=payload.mobile,
    )
    db.add(user)
    await db.flush()
    await _ensure_user_credit_row(db, str(user.id))
    await db.commit()
    await db.refresh(user)
    return success_response({"user": {"id": str(user.id), "email": user.email}}, "User created successfully")


@router.put("/users/{user_id}")
async def update_admin_user(
    user_id: str,
    payload: UserUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_admin_user),
):
    user = (await db.execute(select(User).where(column_text(User.id) == str(user_id)))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(user, key, value)
    await db.commit()
    await db.refresh(user)
    return success_response({}, "User updated successfully")


@router.delete("/users/{user_id}")
async def delete_admin_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    admin_user: dict = Depends(get_admin_user),
):
    user = (await db.execute(select(User).where(column_text(User.id) == str(user_id)))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if str(user.id) == str(current_user.get("user_id")):
        raise HTTPException(status_code=400, detail="You cannot delete your own admin account")

    await db.execute(delete(UserCredit).where(column_text(UserCredit.user_id) == str(user.id)))
    await db.execute(delete(UserSubscription).where(column_text(UserSubscription.user_id) == str(user.id)))
    await db.execute(delete(Payment).where(cast(Payment.user_id, String) == str(user.id)))
    await db.execute(delete(CreditTransaction).where(CreditTransaction.user_id == user.id))
    await db.execute(delete(StrategyRequest).where(StrategyRequest.user_id == user.id))
    await db.execute(delete(User).where(User.id == user.id))
    await db.commit()
    return success_response({}, "User deleted successfully")


@router.patch("/users/{user_id}/status")
async def patch_admin_user_status(
    user_id: str,
    payload: UserStatusRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_admin_user),
):
    user = (await db.execute(select(User).where(column_text(User.id) == str(user_id)))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not await table_has_column(db, "users", "is_active"):
        raise HTTPException(status_code=400, detail="users.is_active column is missing in database")
    await db.execute(text("UPDATE users SET is_active = :is_active WHERE id = :user_id"), {"user_id": user_id, "is_active": payload.is_active})
    await db.commit()
    return success_response({}, f"User {'activated' if payload.is_active else 'deactivated'} successfully")


@router.patch("/users/{user_id}/role")
async def patch_admin_user_role(
    user_id: str,
    payload: UserRoleRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_admin_user),
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.role = payload.role
    await db.commit()
    return success_response({}, "User role updated successfully")


@router.post("/credits/add")
async def add_credits(payload: CreditAdjustRequest, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_admin_user)):
    return await _adjust_credits(
        db,
        payload.user_id,
        payload.amount,
        payload.reason,
        CreditTransactionType.CREDIT,
        actor_user_id=str(current_user.get("user_id")) if current_user else None,
        source="admin_manual_add",
    )


@router.post("/credits/deduct")
async def deduct_credits(payload: CreditAdjustRequest, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_admin_user)):
    return await _adjust_credits(
        db,
        payload.user_id,
        payload.amount,
        payload.reason,
        CreditTransactionType.DEBIT,
        actor_user_id=str(current_user.get("user_id")) if current_user else None,
        source="admin_manual_deduct",
    )


@router.get("/credits/balances")
async def get_credit_balances(
    skip: int = 0,
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_admin_user),
):
    stmt = (
        select(UserCredit, User.email, User.fullname)
        .outerjoin(User, cast(User.id, String) == cast(UserCredit.user_id, String))
        .order_by(UserCredit.updated_at.desc())
        .offset(skip)
        .limit(limit)
    )
    count_stmt = select(func.count()).select_from(UserCredit)

    if search:
        like = f"%{search}%"
        filters = or_(
            cast(UserCredit.user_id, String).ilike(like),
            User.email.ilike(like),
            User.fullname.ilike(like),
        )
        stmt = stmt.where(filters)
        count_stmt = count_stmt.outerjoin(User, cast(User.id, String) == cast(UserCredit.user_id, String)).where(filters)

    rows = (await db.execute(stmt)).all()
    total = (await db.execute(count_stmt)).scalar() or 0
    items = [
        {
            "user_id": str(credit.user_id),
            "user_email": email or "—",
            "user_name": fullname or email or "—",
            "balance": int(credit.balance or 0),
            "updated_at": _serialize(getattr(credit, "updated_at", None)),
        }
        for credit, email, fullname in rows
    ]
    return success_response({"items": items, "total": total, "skip": skip, "limit": limit}, "No data found" if not items else None)


@router.get("/credits/ledger")
async def get_credit_ledger(
    skip: int = 0,
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    transaction_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_admin_user),
):
    has_actor_user_id = await table_has_column(db, "credit_transactions", "actor_user_id")
    has_source = await table_has_column(db, "credit_transactions", "source")

    source_expr = "CAST(tx.source AS TEXT)" if has_source else "NULL"
    actor_expr = "CAST(tx.actor_user_id AS TEXT)" if has_actor_user_id else "NULL"

    where_clauses: list[str] = []
    bind_params: dict[str, Any] = {"skip": skip, "limit": limit}

    if search:
        bind_params["search"] = f"%{search}%"
        where_clauses.append(
            "(u.email ILIKE :search OR u.fullname ILIKE :search OR tx.description ILIKE :search)"
        )

    if transaction_type:
        bind_params["txn_type"] = transaction_type.strip().lower()
        where_clauses.append("LOWER(CAST(tx.transaction_type AS TEXT)) = :txn_type")

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    rows = (
        await db.execute(
            text(
                f"""
                SELECT
                    tx.id,
                    CAST(tx.user_id AS TEXT) AS user_id,
                    CAST(tx.transaction_type AS TEXT) AS transaction_type,
                    tx.amount,
                    tx.balance_after,
                    tx.description,
                    tx.created_at,
                    {source_expr} AS source,
                    {actor_expr} AS actor_user_id,
                    u.email AS user_email,
                    u.fullname AS user_name
                FROM credit_transactions tx
                LEFT JOIN users u ON CAST(u.id AS TEXT) = CAST(tx.user_id AS TEXT)
                {where_sql}
                ORDER BY tx.created_at DESC
                OFFSET :skip
                LIMIT :limit
                """
            ),
            bind_params,
        )
    ).mappings().all()

    total = (
        await db.execute(
            text(
                f"""
                SELECT COUNT(*)
                FROM credit_transactions tx
                LEFT JOIN users u ON CAST(u.id AS TEXT) = CAST(tx.user_id AS TEXT)
                {where_sql}
                """
            ),
            {k: v for k, v in bind_params.items() if k not in {"skip", "limit"}},
        )
    ).scalar() or 0

    items = []
    for txn in rows:
        txn_type = str(txn.get("transaction_type") or "").strip().lower()
        balance_after = int(txn.get("balance_after") or 0)
        credit = int(txn.get("amount") or 0)
        is_debit = txn_type == CreditTransactionType.DEBIT.value
        debit_used = credit if is_debit else 0
        credit_added = credit if not is_debit else 0
        items.append(
            {
                "id": str(txn.get("id")),
                "user_id": str(txn.get("user_id")),
                "user_email": txn.get("user_email") or "—",
                "user_name": txn.get("user_name") or txn.get("user_email") or "—",
                "credits": credit_added if not is_debit else -credit,
                "credits_added": credit_added,
                "credits_used": debit_used,
                "remaining_credits": balance_after,
                "type": txn_type,
                "source": txn.get("source") or txn_type,
                "source_type": txn.get("source"),
                "actor_user_id": str(txn.get("actor_user_id")) if txn.get("actor_user_id") else None,
                "reason": txn.get("description"),
                "balance_after": balance_after,
                "created_at": _serialize(txn.get("created_at")),
            }
        )
    return success_response({"items": items, "total": total, "skip": skip, "limit": limit}, "No data found" if not items else None)


@router.get("/payments")
async def get_payments(
    skip: int = 0,
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    search: Optional[str] = None,
    method: Optional[str] = None,
    purpose: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_admin_user),
):
    stmt = (
        select(Payment, User.email, User.fullname)
        .outerjoin(User, cast(User.id, String) == cast(Payment.user_id, String))
        .order_by(Payment.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    count_stmt = select(func.count()).select_from(Payment)
    filters = []
    if status:
        filters.append(Payment.status == status)
    if search:
        like = f"%{search}%"
        filters.append(
            or_(
                Payment.razorpay_order_id.ilike(like),
                Payment.razorpay_payment_id.ilike(like),
                Payment.provider.ilike(like),
                Payment.purpose.ilike(like),
                User.email.ilike(like),
                User.fullname.ilike(like),
            )
        )
    if method:
        filters.append(func.lower(Payment.provider) == method.strip().lower())
    if purpose:
        filters.append(func.lower(Payment.purpose) == purpose.strip().lower())

    from_dt = _parse_iso_datetime(from_date, field_name="from_date")
    to_dt = _parse_iso_datetime(to_date, field_name="to_date")
    if from_dt:
        filters.append(Payment.created_at >= from_dt)
    if to_dt:
        filters.append(Payment.created_at <= to_dt)
    if filters:
        for flt in filters:
            stmt = stmt.where(flt)
        count_stmt = count_stmt.outerjoin(User, cast(User.id, String) == cast(Payment.user_id, String)).where(*filters)
    rows = (await db.execute(stmt)).all()
    total = (await db.execute(count_stmt)).scalar() or 0
    items = []
    for payment, email, fullname in rows:
        items.append(
            {
                "id": str(payment.id),
                "user_id": str(payment.user_id),
                "user_email": email or "—",
                "user_name": fullname or email or "—",
                "amount": int(payment.amount_inr or 0),
                "currency": payment.currency or "INR",
                "status": payment.status,
                "payment_method": payment.provider,
                "purpose": payment.purpose,
                "transaction_id": payment.razorpay_payment_id,
                "razorpay_order_id": payment.razorpay_order_id,
                "razorpay_payment_id": payment.razorpay_payment_id,
                "billing_order_id": payment.billing_order_id,
                "verified_at": _serialize(getattr(payment, "verified_at", None)),
                "failure_reason": payment.failure_reason,
                "is_reconciled": bool((payment.status or "").upper() == "PAID" and getattr(payment, "verified_at", None)),
                "created_at": _serialize(payment.created_at),
                "updated_at": _serialize(getattr(payment, "updated_at", None)),
            }
        )
    return success_response({"items": items, "total": total, "skip": skip, "limit": limit}, "No data found" if not items else None)


@router.get("/payments/{payment_id}")
async def get_payment_detail(payment_id: str, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_admin_user)):
    row = (
        await db.execute(
            select(Payment, User.email, User.fullname).outerjoin(User, cast(User.id, String) == cast(Payment.user_id, String)).where(cast(Payment.id, String) == str(payment_id))
        )
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Payment not found")
    payment, email, fullname = row
    return success_response({
        "id": str(payment.id),
        "user_id": str(payment.user_id),
        "user_email": email or "—",
        "user_name": fullname or email or "—",
        "amount": int(payment.amount_inr or 0),
        "currency": payment.currency or "INR",
        "status": payment.status,
        "payment_method": payment.provider,
        "purpose": payment.purpose,
        "transaction_id": payment.razorpay_payment_id,
        "razorpay_order_id": payment.razorpay_order_id,
        "razorpay_payment_id": payment.razorpay_payment_id,
        "billing_order_id": payment.billing_order_id,
        "verified_at": _serialize(getattr(payment, "verified_at", None)),
        "failure_reason": payment.failure_reason,
        "reconciliation": {
            "is_reconciled": bool((payment.status or "").upper() == "PAID" and getattr(payment, "verified_at", None)),
            "status": "reconciled" if ((payment.status or "").upper() == "PAID" and getattr(payment, "verified_at", None)) else "pending",
            "provider": payment.provider,
            "purpose": payment.purpose,
        },
        "created_at": _serialize(payment.created_at),
        "updated_at": _serialize(getattr(payment, "updated_at", None)),
    })


@router.post("/payments/{payment_id}/refund")
async def refund_payment(payment_id: str, payload: PaymentRefundRequest | None = None, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_admin_user)):
    payment = (await db.execute(select(Payment).where(cast(Payment.id, String) == str(payment_id)))).scalar_one_or_none()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    if (payment.status or "").upper() == "REFUNDED":
        return success_response({}, "Payment already refunded")

    payment.status = "REFUNDED"
    if payload and payload.note:
        existing_reason = payment.failure_reason or ""
        note = f"Admin refund note: {payload.note.strip()}"
        payment.failure_reason = f"{existing_reason}\n{note}".strip()
    await db.commit()
    return success_response({}, "Payment marked as refunded")


@router.get("/subscriptions")
async def get_subscriptions(
    skip: int = 0,
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_admin_user),
):
    stmt = (
        select(UserSubscription, Plan, User.email, User.fullname)
        .outerjoin(Plan, Plan.id == UserSubscription.plan_id)
        .outerjoin(User, cast(User.id, String) == cast(UserSubscription.user_id, String))
        .order_by(UserSubscription.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    count_stmt = select(func.count()).select_from(UserSubscription)
    filters = []
    if status:
        filters.append(UserSubscription.status == status)
    if search:
        like = f"%{search}%"
        filters.append(or_(User.email.ilike(like), User.fullname.ilike(like), Plan.code.ilike(like)))
    if filters:
        stmt = stmt.where(*filters)
        count_stmt = count_stmt.outerjoin(User, cast(User.id, String) == cast(UserSubscription.user_id, String)).outerjoin(Plan, Plan.id == UserSubscription.plan_id).where(*filters)
    rows = (await db.execute(stmt)).all()
    total = (await db.execute(count_stmt)).scalar() or 0
    items = []
    for sub, plan, email, fullname in rows:
        items.append(
            {
                "id": str(sub.id),
                "user_id": str(sub.user_id),
                "user_email": email or "—",
                "user_name": fullname or email or "—",
                "plan_id": str(sub.plan_id),
                "plan": str(getattr(sub, "plan_code_snapshot", None) or getattr(plan, "code", None) or "FREE").upper(),
                "plan_code": str(getattr(sub, "plan_code_snapshot", None) or getattr(plan, "code", None) or "FREE").upper(),
                "billing_period": str(getattr(sub, "billing_period_snapshot", None) or getattr(plan, "billing_period", None) or "NONE").upper(),
                "amount": int(getattr(sub, "plan_price_inr", None) or getattr(plan, "price_inr", 0) or 0),
                "price_inr": int(getattr(sub, "plan_price_inr", None) or getattr(plan, "price_inr", 0) or 0),
                "included_credits": int(getattr(sub, "included_credits_total", None) or getattr(plan, "included_credits", 0) or 0),
                "included_credits_total": int(getattr(sub, "included_credits_total", None) or getattr(plan, "included_credits", 0) or 0),
                "included_credits_remaining": int(getattr(sub, "included_credits_remaining", None) or 0),
                "status": sub.status,
                "start_date": _serialize(sub.start_at),
                "end_date": _serialize(sub.end_at),
                "start_at": _serialize(sub.start_at),
                "end_at": _serialize(sub.end_at),
                "renews": sub.renews,
                "next_credit_refill_at": _serialize(getattr(sub, "next_credit_refill_at", None)),
                "last_credit_refill_at": _serialize(getattr(sub, "last_credit_refill_at", None)),
                "created_at": _serialize(sub.created_at),
            }
        )
    return success_response({"items": items, "total": total, "skip": skip, "limit": limit}, "No data found" if not items else None)


@router.patch("/subscriptions/{subscription_id}")
async def update_subscription(subscription_id: str, payload: SubscriptionUpdateRequest, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_admin_user)):
    subscription = (await db.execute(select(UserSubscription).where(cast(UserSubscription.id, String) == str(subscription_id)))).scalar_one_or_none()
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(subscription, key, value)
    await db.commit()
    return success_response({}, "Subscription updated successfully")


@router.get("/orders")
async def get_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    search: Optional[str] = None,
    source_type: Optional[str] = None,
    method: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_admin_user),
):
    has_billing_orders = await table_has_column(db, "billing_orders", "id")
    skip = (page - 1) * page_size
    if has_billing_orders:
        stmt = (
            select(BillingOrder, User.email, User.fullname)
            .outerjoin(User, cast(User.id, String) == cast(BillingOrder.user_id, String))
            .order_by(BillingOrder.created_at.desc())
            .offset(skip)
            .limit(page_size)
        )
        count_stmt = select(func.count()).select_from(BillingOrder)
    else:
        stmt = (
            select(Payment, User.email, User.fullname)
            .outerjoin(User, cast(User.id, String) == cast(Payment.user_id, String))
            .order_by(Payment.created_at.desc())
            .offset(skip)
            .limit(page_size)
        )
        count_stmt = select(func.count()).select_from(Payment)

    filters = []
    if status:
        filters.append((BillingOrder.status if has_billing_orders else Payment.status) == status)
    if search:
        like = f"%{search}%"
        if has_billing_orders:
            filters.append(
                or_(
                    BillingOrder.billing_order_id.ilike(like),
                    BillingOrder.razorpay_order_id.ilike(like),
                    BillingOrder.razorpay_payment_id.ilike(like),
                    BillingOrder.purpose.ilike(like),
                    User.email.ilike(like),
                    User.fullname.ilike(like),
                )
            )
        else:
            filters.append(or_(Payment.razorpay_order_id.ilike(like), Payment.razorpay_payment_id.ilike(like), Payment.purpose.ilike(like), User.email.ilike(like), User.fullname.ilike(like)))
    if source_type:
        filters.append(func.lower(BillingOrder.purpose if has_billing_orders else Payment.purpose) == source_type.strip().lower())
    if method:
        filters.append(func.lower(BillingOrder.provider if has_billing_orders else Payment.provider) == method.strip().lower())

    from_dt = _parse_iso_datetime(from_date, field_name="from_date")
    to_dt = _parse_iso_datetime(to_date, field_name="to_date")
    if from_dt:
        filters.append((BillingOrder.created_at if has_billing_orders else Payment.created_at) >= from_dt)
    if to_dt:
        filters.append((BillingOrder.created_at if has_billing_orders else Payment.created_at) <= to_dt)

    if filters:
        stmt = stmt.where(*filters)
        if has_billing_orders:
            count_stmt = count_stmt.outerjoin(User, cast(User.id, String) == cast(BillingOrder.user_id, String)).where(*filters)
        else:
            count_stmt = count_stmt.outerjoin(User, cast(User.id, String) == cast(Payment.user_id, String)).where(*filters)

    rows = (await db.execute(stmt)).all()
    total = (await db.execute(count_stmt)).scalar() or 0
    items = []
    if has_billing_orders:
        for order, email, fullname in rows:
            items.append(
                {
                    "id": str(order.id),
                    "user_id": str(order.user_id),
                    "user_email": email or "—",
                    "user_name": fullname or email or "—",
                    "order_number": order.billing_order_id or order.razorpay_order_id or str(order.id),
                    "order_type": order.purpose,
                    "source_type": order.purpose,
                    "status": order.status,
                    "total_amount": int(order.amount_inr or 0),
                    "currency": order.currency or "INR",
                    "payment_method": order.provider,
                    "transaction_id": order.razorpay_payment_id,
                    "linked_payment_id": order.payment_id,
                    "linked_payment_status": order.status,
                    "reconciliation_status": "reconciled" if ((order.status or "").upper() == "PAID" and getattr(order, "verified_at", None)) else "pending",
                    "created_at": _serialize(order.created_at),
                    "updated_at": _serialize(getattr(order, "updated_at", None)),
                }
            )
    else:
        for payment, email, fullname in rows:
            items.append(
                {
                    "id": str(payment.id),
                    "user_id": str(payment.user_id),
                    "user_email": email or "—",
                    "user_name": fullname or email or "—",
                    "order_number": payment.razorpay_order_id or str(payment.id),
                    "order_type": payment.purpose,
                    "source_type": payment.purpose,
                    "status": payment.status,
                    "total_amount": int(payment.amount_inr or 0),
                    "currency": payment.currency or "INR",
                    "payment_method": payment.provider,
                    "transaction_id": payment.razorpay_payment_id,
                    "linked_payment_id": str(payment.id),
                    "linked_payment_status": payment.status,
                    "reconciliation_status": "reconciled" if ((payment.status or "").upper() == "PAID" and getattr(payment, "verified_at", None)) else "pending",
                    "created_at": _serialize(payment.created_at),
                    "updated_at": _serialize(getattr(payment, "updated_at", None)),
                }
            )

    return success_response({"items": items, "total": total, "page": page, "page_size": page_size, "total_pages": (total + page_size - 1) // page_size}, "No data found" if not items else None)


@router.get("/orders/{order_id}")
async def get_order_detail(order_id: str, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_admin_user)):
    has_billing_orders = await table_has_column(db, "billing_orders", "id")
    if has_billing_orders:
        row = (
            await db.execute(
                select(BillingOrder, User.email, User.fullname)
                .outerjoin(User, cast(User.id, String) == cast(BillingOrder.user_id, String))
                .where(or_(cast(BillingOrder.id, String) == str(order_id), BillingOrder.billing_order_id == str(order_id)))
            )
        ).first()
        if row:
            order, email, fullname = row
            return success_response({
                "id": str(order.id),
                "user_id": str(order.user_id),
                "user_email": email or "—",
                "user_name": fullname or email or "—",
                "order_number": order.billing_order_id or order.razorpay_order_id or str(order.id),
                "order_type": order.purpose,
                "source_type": order.purpose,
                "status": order.status,
                "total_amount": int(order.amount_inr or 0),
                "currency": order.currency or "INR",
                "payment_method": order.provider,
                "transaction_id": order.razorpay_payment_id,
                "linked_payment_id": order.payment_id,
                "linked_payment_status": order.status,
                "billing_order_id": order.billing_order_id,
                "reconciliation": {
                    "status": "reconciled" if ((order.status or "").upper() == "PAID" and getattr(order, "verified_at", None)) else "pending",
                    "verified_at": _serialize(getattr(order, "verified_at", None)),
                    "failure_reason": order.failure_reason,
                },
                "created_at": _serialize(order.created_at),
                "updated_at": _serialize(getattr(order, "updated_at", None)),
                "items": [],
            })

    row = (
        await db.execute(
            select(Payment, User.email, User.fullname).outerjoin(User, cast(User.id, String) == cast(Payment.user_id, String)).where(cast(Payment.id, String) == str(order_id))
        )
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Order not found")
    payment, email, fullname = row
    return success_response({
        "id": str(payment.id),
        "user_id": str(payment.user_id),
        "user_email": email or "—",
        "user_name": fullname or email or "—",
        "order_number": payment.razorpay_order_id or str(payment.id),
        "order_type": payment.purpose,
        "source_type": payment.purpose,
        "status": payment.status,
        "total_amount": int(payment.amount_inr or 0),
        "currency": payment.currency or "INR",
        "payment_method": payment.provider,
        "transaction_id": payment.razorpay_payment_id,
        "linked_payment_id": str(payment.id),
        "linked_payment_status": payment.status,
        "billing_order_id": payment.billing_order_id,
        "reconciliation": {
            "status": "reconciled" if ((payment.status or "").upper() == "PAID" and getattr(payment, "verified_at", None)) else "pending",
            "verified_at": _serialize(getattr(payment, "verified_at", None)),
            "failure_reason": payment.failure_reason,
        },
        "created_at": _serialize(payment.created_at),
        "updated_at": _serialize(getattr(payment, "updated_at", None)),
        "items": [],
    })


@router.patch("/orders/{order_id}/status")
async def update_order_status(order_id: str, payload: OrderStatusRequest, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_admin_user)):
    has_billing_orders = await table_has_column(db, "billing_orders", "id")
    if has_billing_orders:
        order = (
            await db.execute(
                select(BillingOrder).where(or_(cast(BillingOrder.id, String) == str(order_id), BillingOrder.billing_order_id == str(order_id)))
            )
        ).scalar_one_or_none()
        if order:
            order.status = payload.status
            if order.payment_id:
                payment = (
                    await db.execute(select(Payment).where(cast(Payment.id, String) == str(order.payment_id)))
                ).scalar_one_or_none()
                if payment:
                    payment.status = payload.status
            await db.commit()
            return success_response({}, "Order status updated successfully")

    payment = (await db.execute(select(Payment).where(cast(Payment.id, String) == str(order_id)))).scalar_one_or_none()
    if not payment:
        raise HTTPException(status_code=404, detail="Order not found")
    payment.status = payload.status
    await db.commit()
    return success_response({}, "Order status updated successfully")


@router.get("/strategies")
async def get_admin_strategies(
    skip: int = 0,
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_admin_user),
):
    stmt = (
        select(StrategyRequest, User.email, User.fullname)
        .join(User, User.id == StrategyRequest.user_id)
        .order_by(StrategyRequest.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    count_stmt = select(func.count()).select_from(StrategyRequest)
    filters = []
    if status:
        filters.append(StrategyRequest.status == status)
    if search:
        like = f"%{search}%"
        filters.append(or_(StrategyRequest.title.ilike(like), User.email.ilike(like), User.fullname.ilike(like), StrategyRequest.strategy_type.ilike(like)))
    if filters:
        stmt = stmt.where(*filters)
        count_stmt = count_stmt.join(User, User.id == StrategyRequest.user_id).where(*filters)
    rows = (await db.execute(stmt)).all()
    total = (await db.execute(count_stmt)).scalar() or 0
    items = []
    for req, email, fullname in rows:
        items.append(
            {
                "id": str(req.id),
                "title": req.title,
                "description": req.notes or req.entry_rules,
                "strategy_type": req.strategy_type,
                "market": req.market,
                "timeframe": req.timeframe,
                "status": req.status,
                "user_id": str(req.user_id),
                "user_email": email or "—",
                "user_name": fullname or email or "—",
                "admin_notes": req.admin_notes,
                "created_at": _serialize(req.created_at),
                "updated_at": _serialize(req.updated_at),
            }
        )
    implemented = (
        await db.execute(select(Strategy).order_by(Strategy.created_at.desc()).limit(50))
    ).scalars().all()
    implemented_items = [
        {
            "id": str(item.id),
            "name": item.name,
            "description": item.description,
            "code": item.parameters,
            "status": "ACTIVE",
            "created_at": _serialize(item.created_at),
        }
        for item in implemented
    ]
    return success_response({"items": items, "implemented": implemented_items, "total": total, "skip": skip, "limit": limit}, "No data found" if not items and not implemented_items else None)


@router.patch("/strategies/{request_id}")
async def update_admin_strategy(request_id: str, payload: StrategyDecisionRequest, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_admin_user)):
    req = await db.get(StrategyRequest, request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Strategy request not found")
    req.status = payload.status
    if payload.admin_notes is not None:
        req.admin_notes = payload.admin_notes
    await db.commit()
    return success_response({}, "Strategy request updated successfully")


class TicketStatusUpdateRequest(BaseModel):
    status: str


class TicketReplyRequest(BaseModel):
    message: str


@router.get("/backtests")
async def get_admin_backtests(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    status: Optional[str] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    strategy_id: Optional[str] = None,
    instrument_id: Optional[int] = None,
    timeframe: Optional[str] = None,
    user_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_admin_user),
):
    filters = []

    if status:
        filters.append(func.lower(PerformanceMetric.status) == status.lower())
    if strategy_id:
        filters.append(PerformanceMetric.strategy_id == strategy_id)
    if instrument_id is not None:
        filters.append(PerformanceMetric.instrument_id == instrument_id)
    if timeframe:
        filters.append(PerformanceMetric.timeframe == timeframe)
    if user_id:
        filters.append(cast(PerformanceMetric.user_id, String) == str(user_id))
    if from_date:
        filters.append(PerformanceMetric.created_at >= from_date)
    if to_date:
        filters.append(PerformanceMetric.created_at <= to_date)

    stmt = (
        select(
            PerformanceMetric,
            Strategy.name.label("strategy_name"),
            Instrument.symbol.label("instrument_symbol"),
            User.email.label("user_email"),
            User.fullname.label("user_name"),
        )
        .outerjoin(Strategy, Strategy.id == PerformanceMetric.strategy_id)
        .outerjoin(Instrument, Instrument.id == PerformanceMetric.instrument_id)
        .outerjoin(User, cast(User.id, String) == cast(PerformanceMetric.user_id, String))
    )

    if search:
        like = f"%{search}%"
        filters.append(
            or_(
                cast(PerformanceMetric.id, String).ilike(like),
                Strategy.name.ilike(like),
                Instrument.symbol.ilike(like),
                User.email.ilike(like),
                User.fullname.ilike(like),
            )
        )

    if filters:
        stmt = stmt.where(*filters)

    count_stmt = select(func.count()).select_from(PerformanceMetric)
    if filters:
        count_stmt = (
            count_stmt
            .outerjoin(Strategy, Strategy.id == PerformanceMetric.strategy_id)
            .outerjoin(Instrument, Instrument.id == PerformanceMetric.instrument_id)
            .outerjoin(User, cast(User.id, String) == cast(PerformanceMetric.user_id, String))
            .where(*filters)
        )

    total = (await db.execute(count_stmt)).scalar() or 0
    offset = (page - 1) * page_size
    rows = (await db.execute(stmt.order_by(PerformanceMetric.created_at.desc()).offset(offset).limit(page_size))).all()

    backtest_ids = [str(metric.id) for metric, _, _, _, _ in rows]
    debit_map = await _get_backtest_billing_snapshot(db, backtest_ids)

    items = []
    for metric, strategy_name, instrument_symbol, user_email, user_name in rows:
        debit = debit_map.get(str(metric.id), {})
        initial_capital = float(metric.initial_capital or 0)
        final_capital = float(metric.final_capital or 0)
        net_profit = float(metric.net_profit or (final_capital - initial_capital))
        total_return = ((net_profit / initial_capital) * 100.0) if initial_capital > 0 else 0.0

        items.append(
            {
                "id": str(metric.id),
                "strategy_id": metric.strategy_id,
                "strategy_name": strategy_name or metric.strategy_id,
                "instrument_id": metric.instrument_id,
                "instrument_symbol": instrument_symbol,
                "timeframe": metric.timeframe,
                "user_id": str(metric.user_id),
                "user_email": user_email or "—",
                "user_name": user_name or user_email or "—",
                "initial_capital": initial_capital,
                "final_capital": final_capital,
                "net_profit": net_profit,
                "total_return": total_return,
                "sharpe_ratio": float(metric.sharpe_ratio or 0),
                "max_drawdown": float(metric.max_drawdown or 0),
                "win_rate": float(metric.win_rate or 0),
                "total_trades": int(metric.total_trades or 0),
                "credit_cost": debit.get("effective_credit_cost", debit.get("credit_cost")),
                "effective_credit_cost": debit.get("effective_credit_cost", debit.get("credit_cost")),
                "included_debited": debit.get("included_debited", 0.0),
                "wallet_debited": debit.get("wallet_debited", 0.0),
                "included_refunded": debit.get("included_refunded", 0.0),
                "wallet_refunded": debit.get("wallet_refunded", 0.0),
                "refund_total": debit.get("refund_total", 0.0),
                "charge_status": debit.get("charge_status", "not_charged"),
                "debit_transaction_id": debit.get("debit_transaction_id"),
                "refund_transaction_ids": debit.get("refund_transaction_ids", []),
                "status": metric.status,
                "created_at": _serialize(metric.created_at),
                "updated_at": _serialize(metric.updated_at),
            }
        )

    total_pages = ceil(total / page_size) if total > 0 else 1
    return {
        "items": items,
        "total": int(total),
        "page": page,
        "page_size": page_size,
        "total_pages": int(total_pages),
    }


@router.get("/backtests/{backtest_id}")
async def get_admin_backtest_detail(
    backtest_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_admin_user),
):
    metric = await db.get(PerformanceMetric, backtest_id)
    if not metric:
        raise HTTPException(status_code=404, detail="Backtest not found")

    strategy_name = (await db.execute(select(Strategy.name).where(Strategy.id == metric.strategy_id))).scalar_one_or_none()
    instrument_symbol = (await db.execute(select(Instrument.symbol).where(Instrument.id == metric.instrument_id))).scalar_one_or_none()

    billing = (await _get_backtest_billing_snapshot(db, [str(metric.id)])).get(str(metric.id), {})

    return success_response(
        {
            "id": str(metric.id),
            "strategy_id": metric.strategy_id,
            "strategy_name": strategy_name,
            "instrument_id": metric.instrument_id,
            "instrument_symbol": instrument_symbol,
            "user_id": str(metric.user_id),
            "timeframe": metric.timeframe,
            "start_date": metric.start_date.isoformat() if metric.start_date else None,
            "end_date": metric.end_date.isoformat() if metric.end_date else None,
            "initial_capital": float(metric.initial_capital or 0),
            "final_capital": float(metric.final_capital or 0),
            "net_profit": float(metric.net_profit or 0),
            "max_drawdown": float(metric.max_drawdown or 0),
            "sharpe_ratio": float(metric.sharpe_ratio or 0),
            "win_rate": float(metric.win_rate or 0),
            "total_trades": int(metric.total_trades or 0),
            "winning_trades": int(metric.winning_trades or 0),
            "losing_trades": int(metric.losing_trades or 0),
            "profit_factor": float(metric.profit_factor or 0),
            "credit_cost": billing.get("effective_credit_cost", billing.get("credit_cost")),
            "effective_credit_cost": billing.get("effective_credit_cost", billing.get("credit_cost")),
            "included_debited": billing.get("included_debited", 0.0),
            "wallet_debited": billing.get("wallet_debited", 0.0),
            "included_refunded": billing.get("included_refunded", 0.0),
            "wallet_refunded": billing.get("wallet_refunded", 0.0),
            "refund_total": billing.get("refund_total", 0.0),
            "charge_status": billing.get("charge_status", "not_charged"),
            "debit_transaction_id": billing.get("debit_transaction_id"),
            "refund_transaction_ids": billing.get("refund_transaction_ids", []),
            "status": metric.status,
            "created_at": _serialize(metric.created_at),
            "updated_at": _serialize(metric.updated_at),
        }
    )


@router.get("/backtests/pricing-config")
async def get_backtest_pricing_config(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_admin_user),
):
    active = await BacktestPricingService.get_active_pricing_config(db)
    items = await BacktestPricingService.list_rule_sets(db)

    return success_response(
        {
            "active": {
                "id": active.get("id"),
                "name": active.get("name"),
                "version": active.get("version"),
                "description": active.get("description"),
                "is_active": active.get("is_active", True),
                "is_locked": active.get("is_locked", False),
                "base_cost": float(active.get("base_cost", 0)),
                "range_days_step": int(active.get("range_days_step", 1)),
                "min_credit_charge": int(active.get("min_credit_charge", 1)),
                "max_credit_charge": active.get("max_credit_charge"),
                "date_range_buckets": active.get("date_range_buckets") or [],
                "timeframe_multipliers": active.get("timeframe_multipliers") or [],
                "strategy_complexity_enabled": bool(active.get("strategy_complexity_enabled", False)),
                "strategy_complexity_step": float(active.get("strategy_complexity_step", 0) or 0),
                "strategy_complexity_cap": float(active.get("strategy_complexity_cap", 0) or 0),
                "plan_discounts": active.get("plan_discounts") or {},
                "is_db_configured": bool(active.get("is_db_configured", False)),
                "updated_at": _serialize(active.get("updated_at")),
            },
            "items": [
                {
                    **item,
                    "updated_at": _serialize(item.get("updated_at")),
                    "created_at": _serialize(item.get("created_at")),
                }
                for item in items
            ],
            "notes": "Backtest pricing is DB-driven. Edit active set or activate another set safely.",
        }
    )


@router.put("/backtests/pricing-config")
async def update_backtest_pricing_config(
    payload: BacktestPricingRuleSetUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_admin_user),
):
    body = payload.model_dump(exclude_unset=True)
    if not body:
        raise HTTPException(status_code=400, detail="No pricing fields provided")

    if body.get("plan_discounts") is not None:
        normalized_plan_discounts: dict[str, float] = {}
        for key, value in dict(body["plan_discounts"]).items():
            try:
                pct = float(value)
            except Exception:
                continue
            if pct < 0:
                pct = 0.0
            if pct > 0.95:
                pct = 0.95
            normalized_plan_discounts[str(key).upper()] = pct
        body["plan_discounts"] = normalized_plan_discounts

    if body.get("strategy_complexity_step") is not None:
        body["strategy_complexity_step"] = float(body["strategy_complexity_step"])
    if body.get("strategy_complexity_cap") is not None:
        body["strategy_complexity_cap"] = float(body["strategy_complexity_cap"])

    actor_id = str(current_user.get("user_id")) if current_user and current_user.get("user_id") else None
    await BacktestPricingService.update_or_create_active_rule_set(
        db,
        body,
        actor_user_id=actor_id,
    )
    await db.commit()

    active = await BacktestPricingService.get_active_pricing_config(db)
    return success_response(
        {
            "id": active.get("id"),
            "name": active.get("name"),
            "version": active.get("version"),
            "base_cost": float(active.get("base_cost", 0)),
            "range_days_step": int(active.get("range_days_step", 1)),
            "min_credit_charge": int(active.get("min_credit_charge", 1)),
            "max_credit_charge": active.get("max_credit_charge"),
            "date_range_buckets": active.get("date_range_buckets") or [],
            "timeframe_multipliers": active.get("timeframe_multipliers") or [],
            "strategy_complexity_enabled": bool(active.get("strategy_complexity_enabled", False)),
            "strategy_complexity_step": float(active.get("strategy_complexity_step", 0) or 0),
            "strategy_complexity_cap": float(active.get("strategy_complexity_cap", 0) or 0),
            "plan_discounts": active.get("plan_discounts") or {},
        },
        "Backtest pricing config updated",
    )


@router.post("/backtests/pricing-config/activate")
async def activate_backtest_pricing_rule_set(
    payload: BacktestPricingRuleSetActivateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_admin_user),
):
    target = await BacktestPricingService.activate_rule_set(db, payload.rule_set_id)
    if not target:
        raise HTTPException(status_code=404, detail="Pricing rule set not found")
    await db.commit()

    active = await BacktestPricingService.get_active_pricing_config(db)
    return success_response(
        {
            "id": active.get("id"),
            "name": active.get("name"),
            "version": active.get("version"),
            "is_active": bool(active.get("is_active", True)),
        },
        "Pricing rule set activated",
    )


@router.get("/market-data/supported")
async def get_admin_market_data_supported(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_admin_user),
):
    instruments = (await db.execute(select(Instrument).order_by(Instrument.symbol.asc()))).scalars().all()
    timeframes = (
        await db.execute(select(MarketData.timeframe).distinct().order_by(MarketData.timeframe.asc()))
    ).scalars().all()

    return success_response(
        {
            "instruments": [
                {
                    "id": instrument.id,
                    "symbol": instrument.symbol,
                    "exchange": instrument.exchange,
                    "market": instrument.market,
                    "instrument_type": instrument.instrument_type,
                }
                for instrument in instruments
            ],
            "timeframes": [tf for tf in timeframes if tf],
        }
    )


@router.get("/market-data/coverage")
async def get_admin_market_data_coverage(
    instrument_id: Optional[int] = None,
    timeframe: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_admin_user),
):
    stmt = (
        select(
            MarketData.instrument_id,
            Instrument.symbol.label("instrument_symbol"),
            MarketData.timeframe,
            func.min(MarketData.timestamp).label("min_timestamp"),
            func.max(MarketData.timestamp).label("max_timestamp"),
            func.count().label("candle_count"),
        )
        .join(Instrument, Instrument.id == MarketData.instrument_id)
        .group_by(MarketData.instrument_id, Instrument.symbol, MarketData.timeframe)
        .order_by(Instrument.symbol.asc(), MarketData.timeframe.asc())
    )

    if instrument_id is not None:
        stmt = stmt.where(MarketData.instrument_id == instrument_id)
    if timeframe:
        stmt = stmt.where(MarketData.timeframe == timeframe)

    rows = (await db.execute(stmt)).all()
    coverage = [
        {
            "instrument_id": row.instrument_id,
            "instrument_symbol": row.instrument_symbol,
            "timeframe": row.timeframe,
            "min_timestamp": row.min_timestamp.isoformat() if row.min_timestamp else None,
            "max_timestamp": row.max_timestamp.isoformat() if row.max_timestamp else None,
            "candle_count": int(row.candle_count or 0),
        }
        for row in rows
    ]

    return success_response({"items": coverage, "total": len(coverage)})


@router.get("/market-data/freshness")
async def get_admin_market_data_freshness(
    stale_after_hours: int = Query(24, ge=1, le=720),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_admin_user),
):
    coverage_resp = await get_admin_market_data_coverage(db=db, current_user=current_user)
    items = coverage_resp["data"]["items"] if coverage_resp.get("success") else []

    now = datetime.utcnow()
    stale_threshold = now - timedelta(hours=stale_after_hours)
    stale_items = []
    fresh_items = []

    for item in items:
        max_ts_str = item.get("max_timestamp")
        max_ts = datetime.fromisoformat(max_ts_str) if max_ts_str else None
        freshness = {
            **item,
            "is_stale": True,
            "age_hours": None,
        }
        if max_ts:
            age_hours = max((now - max_ts.replace(tzinfo=None)).total_seconds() / 3600.0, 0.0)
            freshness["age_hours"] = round(age_hours, 2)
            freshness["is_stale"] = max_ts < stale_threshold

        if freshness["is_stale"]:
            stale_items.append(freshness)
        else:
            fresh_items.append(freshness)

    return success_response(
        {
            "summary": {
                "total_pairs": len(items),
                "stale_pairs": len(stale_items),
                "fresh_pairs": len(fresh_items),
                "stale_after_hours": stale_after_hours,
            },
            "stale": stale_items,
            "fresh": fresh_items,
        }
    )


@router.post("/market-data/refresh")
async def trigger_market_data_refresh(
    payload: MarketDataHookRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_admin_user),
):
    job_id = str(uuid4())
    db.add(
        JobStatus(
            id=job_id,
            user_id=as_uuid_or_str(current_user["user_id"]),
            job_type="market_data_refresh",
            status="pending",
            progress=0,
            message="Refresh hook accepted",
            job_data=json.dumps(payload.model_dump(mode="json")),
            created_at=datetime.utcnow(),
        )
    )
    await db.commit()

    return success_response(
        {
            "job_id": job_id,
            "status": "pending",
            "hook": "market_data_refresh",
            "payload": payload.model_dump(mode="json"),
            "message": "Refresh hook accepted. Implement worker binding to process this job.",
        }
    )


@router.post("/market-data/upload")
async def trigger_market_data_upload(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_admin_user),
):
    job_id = str(uuid4())
    db.add(
        JobStatus(
            id=job_id,
            user_id=as_uuid_or_str(current_user["user_id"]),
            job_type="market_data_upload",
            status="pending",
            progress=0,
            message="Upload hook accepted",
            job_data=json.dumps(payload),
            created_at=datetime.utcnow(),
        )
    )
    await db.commit()

    return success_response(
        {
            "job_id": job_id,
            "status": "pending",
            "hook": "market_data_upload",
            "message": "Upload hook accepted. Implement parser/ingestion worker to process this job.",
        }
    )


@router.get('/support-tickets')
async def get_admin_support_tickets(skip: int = 0, limit: int = Query(20, ge=1, le=100), status: Optional[str] = None, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_admin_user)):
    stmt = select(SupportTicket, User.email, User.fullname).join(User, User.id == SupportTicket.user_id).order_by(SupportTicket.created_at.desc()).offset(skip).limit(limit)
    count_stmt = select(func.count()).select_from(SupportTicket)
    if status:
        stmt = stmt.where(SupportTicket.status == status)
        count_stmt = count_stmt.where(SupportTicket.status == status)
    rows = (await db.execute(stmt)).all()
    total = (await db.execute(count_stmt)).scalar() or 0
    items = [{
        'id': str(ticket.id), 'user_id': str(ticket.user_id), 'user_email': email, 'user_name': fullname or email, 'subject': ticket.subject,
        'message': ticket.message, 'status': ticket.status, 'priority': ticket.priority, 'created_at': _serialize(ticket.created_at), 'updated_at': _serialize(ticket.updated_at)
    } for ticket, email, fullname in rows]
    return success_response({'items': items, 'total': total, 'skip': skip, 'limit': limit}, 'No data found' if not items else None)


@router.patch('/support-tickets/{ticket_id}')
async def update_admin_support_ticket(ticket_id: str, payload: TicketStatusUpdateRequest, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_admin_user)):
    ticket = (await db.execute(select(SupportTicket).where(cast(SupportTicket.id, String) == str(ticket_id)))).scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail='Ticket not found')
    ticket.status = payload.status
    await db.commit()
    return success_response({}, 'Ticket updated successfully')


@router.post('/support-tickets/{ticket_id}/reply')
async def reply_admin_support_ticket(ticket_id: str, payload: TicketReplyRequest, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_admin_user)):
    ticket = (await db.execute(select(SupportTicket).where(cast(SupportTicket.id, String) == str(ticket_id)))).scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail='Ticket not found')
    reply = SupportTicketReply(ticket_id=as_uuid_or_str(ticket_id), user_id=as_uuid_or_str(current_user['user_id']), message=payload.message)
    db.add(reply)
    ticket.status = 'in_progress'
    await db.commit()
    return success_response({'id': str(reply.id)}, 'Reply sent successfully')
