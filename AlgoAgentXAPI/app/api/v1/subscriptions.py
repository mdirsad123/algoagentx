from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import String, cast, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import settings
from ...core.dependencies import get_current_user, get_db
from ...db.models import Payment, Plan, UserCredit, UserSubscription
from ...db.compat import as_uuid_or_str, column_text
from ...utils.api_response import success_response

router = APIRouter()


def _period_days(period: str) -> int:
    return 365 if str(period).upper() in {"YEARLY", "ANNUAL"} else 30


@router.get("/")
async def list_my_subscriptions(db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    rows = (
        await db.execute(
            select(UserSubscription, Plan)
            .outerjoin(Plan, Plan.id == UserSubscription.plan_id)
            .where(cast(UserSubscription.user_id, String) == str(current_user["user_id"]))
            .order_by(UserSubscription.created_at.desc())
        )
    ).all()
    data = [{
        "id": str(sub.id),
        "user_id": str(sub.user_id),
        "plan_id": str(sub.plan_id),
        "plan_code": getattr(plan, "code", None),
        "billing_period": getattr(plan, "billing_period", None),
        "price_inr": int(getattr(plan, "price_inr", 0) or 0),
        "included_credits": int(getattr(plan, "included_credits", 0) or 0),
        "status": sub.status,
        "start_at": sub.start_at.isoformat() if sub.start_at else None,
        "end_at": sub.end_at.isoformat() if sub.end_at else None,
        "renews": sub.renews,
        "created_at": sub.created_at.isoformat() if sub.created_at else None,
    } for sub, plan in rows]
    return success_response(data, "No data found" if not data else None)


@router.post("/upgrade")
async def upgrade_subscription(request: dict, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    plan_code = request.get("plan_code")
    billing_period = str(request.get("billing_period") or "MONTHLY").upper()
    if not plan_code:
        raise HTTPException(status_code=400, detail="plan_code is required")
    plan = (
        await db.execute(select(Plan).where(Plan.code == plan_code, Plan.billing_period == billing_period))
    ).scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    now = datetime.utcnow()
    sub = UserSubscription(
        user_id=as_uuid_or_str(current_user["user_id"]),
        plan_id=plan.id,
        status="ACTIVE",
        start_at=now,
        end_at=now + timedelta(days=_period_days(billing_period)),
        renews=True,
    )
    db.add(sub)
    credit_row = (await db.execute(select(UserCredit).where(column_text(UserCredit.user_id) == str(current_user["user_id"])))).scalar_one_or_none()
    if not credit_row:
        credit_row = UserCredit(user_id=as_uuid_or_str(current_user["user_id"]), balance=0)
        db.add(credit_row)
        await db.flush()
    credit_row.balance = int(credit_row.balance or 0) + int(plan.included_credits or 0)
    await db.commit()
    return success_response({"subscription_id": str(sub.id), "status": sub.status}, "Subscription upgraded successfully")


@router.get("/me")
async def get_my_subscription(db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    row = (
        await db.execute(
            select(UserSubscription, Plan)
            .outerjoin(Plan, Plan.id == UserSubscription.plan_id)
            .where(cast(UserSubscription.user_id, String) == str(current_user["user_id"]))
            .order_by(UserSubscription.created_at.desc())
            .limit(1)
        )
    ).first()
    if not row:
        return success_response(None, "No data found")
    sub, plan = row
    return success_response({
        "id": str(sub.id),
        "plan_code": getattr(plan, "code", None),
        "billing_period": getattr(plan, "billing_period", None),
        "status": sub.status,
        "start_at": sub.start_at.isoformat() if sub.start_at else None,
        "end_at": sub.end_at.isoformat() if sub.end_at else None,
        "renews": sub.renews,
    })


@router.get("/plans")
async def get_available_plans(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(Plan).where(Plan.is_active == True).order_by(Plan.price_inr.asc()))).scalars().all()
    plans = [{
        "id": str(row.id),
        "code": row.code,
        "billing_period": row.billing_period,
        "price_inr": int(row.price_inr or 0),
        "included_credits": int(row.included_credits or 0),
        "features": row.features or {},
    } for row in rows]
    grouped = {"monthly": [p for p in plans if p["billing_period"] == "MONTHLY"], "yearly": [p for p in plans if p["billing_period"] in {"YEARLY", "ANNUAL"}]}
    return success_response(grouped)


@router.post("/razorpay/create")
async def create_subscription_checkout(request: dict, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    plan_code = request.get("plan_code")
    billing_period = str(request.get("billing_period") or "MONTHLY").upper()
    if not plan_code:
        raise HTTPException(status_code=400, detail="plan_code is required")
    plan = (
        await db.execute(select(Plan).where(Plan.code == plan_code, Plan.billing_period == billing_period))
    ).scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    payment = Payment(
        user_id=as_uuid_or_str(current_user["user_id"]),
        provider="RAZORPAY",
        purpose="SUBSCRIPTION",
        amount_inr=int(plan.price_inr or 0),
        currency="INR",
        status="CREATED",
        razorpay_order_id=f"suborder_{uuid4().hex[:14]}",
    )
    db.add(payment)
    await db.commit()
    return success_response({
        "subscription_id": f"sub_{uuid4().hex[:14]}",
        "order_id": payment.razorpay_order_id,
        "key_id": settings.razorpay_key_id or "rzp_test_placeholder",
        "plan_code": plan_code,
        "billing_period": billing_period,
        "amount": int(plan.price_inr or 0) * 100,
    }, "Subscription checkout created successfully")


@router.post("/cancel/{subscription_id}")
async def cancel_subscription(subscription_id: str, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    sub = await db.get(UserSubscription, subscription_id)
    if not sub or str(sub.user_id) != str(current_user["user_id"]):
        raise HTTPException(status_code=404, detail="Subscription not found")
    sub.status = "CANCELED"
    sub.renews = False
    await db.commit()
    return success_response({"id": str(sub.id), "status": sub.status}, "Subscription canceled successfully")


@router.get("/razorpay/config")
async def get_razorpay_subscription_config():
    return success_response({"key_id": settings.razorpay_key_id or "rzp_test_placeholder", "configured": bool(settings.razorpay_key_id)})


@router.post("/razorpay/webhook")
async def razorpay_subscription_webhook(request: Request):
    payload = await request.json()
    return success_response({"received": True, "event": payload.get("event")}, "Webhook accepted")
