from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Optional
from uuid import uuid4
import logging

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import String, cast, delete, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.dependencies import get_admin_user, get_current_user, get_db
from ...utils.api_response import success_response
from ...db.models import (
    CreditTransaction,
    CreditTransactionType,
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


def _serialize(value: Any) -> Any:
    if isinstance(value, Decimal):
        try:
            return int(value) if value == int(value) else float(value)
        except Exception:
            return float(value)
    if isinstance(value, datetime):
        return value.isoformat()
    return value


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
        subscription_map[key] = {
            "plan": getattr(plan, "code", None) or "free",
            "status": sub.status,
            "subscription_id": str(sub.id),
        }
    return subscription_map


async def _adjust_credits(
    db: AsyncSession,
    user_id: str,
    amount: int,
    reason: str,
    transaction_type: CreditTransactionType,
) -> dict[str, Any]:
    user = (await db.execute(select(User).where(column_text(User.id) == str(user_id)))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    credit_row = await _ensure_user_credit_row(db, user_id)
    balance_before = int(credit_row.balance or 0)
    signed_amount = amount if transaction_type != CreditTransactionType.DEBIT else -amount
    new_balance = balance_before + signed_amount
    if new_balance < 0:
        raise HTTPException(status_code=400, detail="Insufficient credit balance")

    credit_row.balance = new_balance
    txn = CreditTransaction(
        id=str(uuid4()),
        user_id=user.id,
        transaction_type=transaction_type,
        amount=amount,
        balance_after=new_balance,
        description=reason,
    )
    db.add(txn)
    await db.commit()
    await db.refresh(txn)
    return {
        "message": "Credits updated successfully",
        "transaction": {
            "id": txn.id,
            "user_id": str(user.id),
            "user_email": user.email,
            "credits": signed_amount,
            "type": txn.transaction_type.value,
            "reason": txn.description,
            "balance_after": new_balance,
            "created_at": _serialize(txn.created_at),
        },
    }


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
                cast(CreditTransaction.transaction_type, String).in_([
                    CreditTransactionType.CREDIT.value, 
                    CreditTransactionType.REFUND.value
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
                "plan": subs.get(uid, {}).get("plan", "free"),
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
        recent_orders.append(
            {
                "id": payload["id"],
                "user_id": payload["user_id"],
                "user_email": payload["user_email"],
                "user_name": payload["user_name"],
                "order_number": payment.razorpay_order_id or str(payment.id),
                "status": payment.status,
                "total_amount": int(payment.amount_inr or 0),
                "currency": payment.currency or "INR",
                "payment_method": payment.provider,
                "purpose": payment.purpose,
                "created_at": payload["created_at"],
            }
        )

    # Calculate additional metrics for test compatibility
    paid_count = (await db.execute(select(func.count()).select_from(Payment).where(Payment.status.in_(paid_statuses)))).scalar() or 0
    failed_count = total_orders - paid_count
    
    total_credits_used = (
        await db.execute(
            select(func.coalesce(func.sum(CreditTransaction.amount), 0)).where(
                cast(CreditTransaction.transaction_type, String) == CreditTransactionType.DEBIT.value
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
            "active_subscriptions": total_subscriptions
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
                "plan": subs.get(uid, {}).get("plan", "free"),
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
    return await _adjust_credits(db, payload.user_id, payload.amount, payload.reason, CreditTransactionType.CREDIT)


@router.post("/credits/deduct")
async def deduct_credits(payload: CreditAdjustRequest, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_admin_user)):
    return await _adjust_credits(db, payload.user_id, payload.amount, payload.reason, CreditTransactionType.DEBIT)


@router.get("/credits/ledger")
async def get_credit_ledger(
    skip: int = 0,
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_admin_user),
):
    stmt = (
        select(CreditTransaction, User.email, User.fullname)
        .join(User, User.id == CreditTransaction.user_id)
        .order_by(CreditTransaction.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    count_stmt = select(func.count()).select_from(CreditTransaction)
    if search:
        like = f"%{search}%"
        stmt = stmt.where(or_(User.email.ilike(like), User.fullname.ilike(like), CreditTransaction.description.ilike(like)))
        count_stmt = count_stmt.join(User, User.id == CreditTransaction.user_id).where(
            or_(User.email.ilike(like), User.fullname.ilike(like), CreditTransaction.description.ilike(like))
        )
    rows = (await db.execute(stmt)).all()
    total = (await db.execute(count_stmt)).scalar() or 0
    items = []
    for txn, email, fullname in rows:
        balance_after = int(txn.balance_after or 0)
        credit = int(txn.amount or 0)
        debit_used = credit if txn.transaction_type == CreditTransactionType.DEBIT else 0
        credit_added = credit if txn.transaction_type != CreditTransactionType.DEBIT else 0
        items.append(
            {
                "id": txn.id,
                "user_id": str(txn.user_id),
                "user_email": email or "—",
                "user_name": fullname or email or "—",
                "credits": credit_added if txn.transaction_type != CreditTransactionType.DEBIT else -credit,
                "credits_added": credit_added,
                "credits_used": debit_used,
                "remaining_credits": balance_after,
                "type": txn.transaction_type.value,
                "source": txn.description or txn.transaction_type.value,
                "reason": txn.description,
                "balance_after": balance_after,
                "created_at": _serialize(txn.created_at),
            }
        )
    return success_response({"items": items, "total": total, "skip": skip, "limit": limit}, "No data found" if not items else None)


@router.get("/payments")
async def get_payments(
    skip: int = 0,
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    search: Optional[str] = None,
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
        "created_at": _serialize(payment.created_at),
        "updated_at": _serialize(getattr(payment, "updated_at", None)),
    })


@router.post("/payments/{payment_id}/refund")
async def refund_payment(payment_id: str, payload: PaymentRefundRequest | None = None, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_admin_user)):
    payment = (await db.execute(select(Payment).where(cast(Payment.id, String) == str(payment_id)))).scalar_one_or_none()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    payment.status = "REFUNDED"
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
                "plan": getattr(plan, "code", None) or "free",
                "plan_code": getattr(plan, "code", None) or "free",
                "billing_period": getattr(plan, "billing_period", None) or "NONE",
                "amount": int(getattr(plan, "price_inr", 0) or 0),
                "price_inr": int(getattr(plan, "price_inr", 0) or 0),
                "included_credits": int(getattr(plan, "included_credits", 0) or 0),
                "status": sub.status,
                "start_date": _serialize(sub.start_at),
                "end_date": _serialize(sub.end_at),
                "start_at": _serialize(sub.start_at),
                "end_at": _serialize(sub.end_at),
                "renews": sub.renews,
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
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_admin_user),
):
    skip = (page - 1) * page_size
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
        filters.append(Payment.status == status)
    if search:
        like = f"%{search}%"
        filters.append(or_(Payment.razorpay_order_id.ilike(like), Payment.razorpay_payment_id.ilike(like), Payment.purpose.ilike(like), User.email.ilike(like), User.fullname.ilike(like)))
    if filters:
        stmt = stmt.where(*filters)
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
                "order_number": payment.razorpay_order_id or str(payment.id),
                "order_type": payment.purpose,
                "status": payment.status,
                "total_amount": int(payment.amount_inr or 0),
                "currency": payment.currency or "INR",
                "payment_method": payment.provider,
                "transaction_id": payment.razorpay_payment_id,
                "created_at": _serialize(payment.created_at),
                "updated_at": _serialize(getattr(payment, "updated_at", None)),
            }
        )
    return {"items": items, "total": total, "page": page, "page_size": page_size, "total_pages": (total + page_size - 1) // page_size}


@router.get("/orders/{order_id}")
async def get_order_detail(order_id: str, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_admin_user)):
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
        "status": payment.status,
        "total_amount": int(payment.amount_inr or 0),
        "currency": payment.currency or "INR",
        "payment_method": payment.provider,
        "transaction_id": payment.razorpay_payment_id,
        "created_at": _serialize(payment.created_at),
        "updated_at": _serialize(getattr(payment, "updated_at", None)),
        "items": [],
    })


@router.patch("/orders/{order_id}/status")
async def update_order_status(order_id: str, payload: OrderStatusRequest, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_admin_user)):
    payment = await db.get(Payment, order_id)
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
