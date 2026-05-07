from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_admin_user, get_db

router = APIRouter()


def _serialize(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _row(row: Any) -> dict[str, Any]:
    return {k: _serialize(v) for k, v in dict(row).items()}


async def _has_table(db: AsyncSession, table_name: str) -> bool:
    return bool((await db.execute(text("""
        SELECT EXISTS (
          SELECT 1 FROM information_schema.tables
          WHERE table_schema = 'public' AND table_name = :table_name
        )
    """), {"table_name": table_name})).scalar())


async def _has_column(db: AsyncSession, table_name: str, column_name: str) -> bool:
    return bool((await db.execute(text("""
        SELECT EXISTS (
          SELECT 1 FROM information_schema.columns
          WHERE table_schema = 'public' AND table_name = :table_name AND column_name = :column_name
        )
    """), {"table_name": table_name, "column_name": column_name})).scalar())


def _date_filter(params: dict[str, Any], column: str = "created_at") -> str:
    parts: list[str] = []
    if params.get("from_date"):
        parts.append(f"{column} >= :from_date")
    if params.get("to_date"):
        parts.append(f"{column} <= :to_date")
    return " AND ".join(parts)


def _coalesce_amount_expr() -> str:
    return "COALESCE(payment_amount, final_amount_inr, amount_inr, 0)"


@router.get("/summary")
async def billing_summary(
    db: AsyncSession = Depends(get_db),
    _admin: dict = Depends(get_admin_user),
):
    has_orders = await _has_table(db, "billing_orders")
    has_payments = await _has_table(db, "payments")
    has_redemptions = await _has_table(db, "billing_coupon_redemptions")

    summary = {
        "total_revenue_usd": 0.0,
        "total_revenue_inr": 0.0,
        "total_gst_collected_inr": 0.0,
        "total_discounts_usd": 0.0,
        "total_paid_orders": 0,
        "pending_orders": 0,
        "failed_orders": 0,
        "coupon_redemptions": 0,
        "credit_topup_revenue_usd": 0.0,
        "subscription_revenue_usd": 0.0,
    }

    if has_orders:
        paid = "UPPER(COALESCE(status,'')) = 'PAID'"
        summary.update(_row((await db.execute(text(f"""
            SELECT
              COALESCE(SUM(CASE WHEN {paid} THEN COALESCE(final_usd,0) ELSE 0 END),0) AS total_revenue_usd,
              COALESCE(SUM(CASE WHEN {paid} THEN COALESCE(final_amount_inr, payment_amount, amount_inr,0) ELSE 0 END),0) AS total_revenue_inr,
              COALESCE(SUM(CASE WHEN {paid} THEN COALESCE(gst_amount_inr,0) ELSE 0 END),0) AS total_gst_collected_inr,
              COALESCE(SUM(CASE WHEN {paid} THEN COALESCE(discount_usd,0) ELSE 0 END),0) AS total_discounts_usd,
              COUNT(*) FILTER (WHERE {paid}) AS total_paid_orders,
              COUNT(*) FILTER (WHERE UPPER(COALESCE(status,'')) IN ('PENDING','CREATED')) AS pending_orders,
              COUNT(*) FILTER (WHERE UPPER(COALESCE(status,'')) IN ('FAILED','CANCELLED')) AS failed_orders,
              COALESCE(SUM(CASE WHEN {paid} AND UPPER(COALESCE(purchase_type,purpose,'')) = 'CREDITS' THEN COALESCE(final_usd,0) ELSE 0 END),0) AS credit_topup_revenue_usd,
              COALESCE(SUM(CASE WHEN {paid} AND UPPER(COALESCE(purchase_type,purpose,'')) = 'SUBSCRIPTION' THEN COALESCE(final_usd,0) ELSE 0 END),0) AS subscription_revenue_usd
            FROM billing_orders
        """))).mappings().first() or {}))
    elif has_payments:
        paid = "UPPER(COALESCE(status,'')) = 'PAID'"
        summary.update(_row((await db.execute(text(f"""
            SELECT
              0::numeric AS total_revenue_usd,
              COALESCE(SUM(CASE WHEN {paid} THEN amount_inr ELSE 0 END),0) AS total_revenue_inr,
              0::numeric AS total_gst_collected_inr,
              0::numeric AS total_discounts_usd,
              COUNT(*) FILTER (WHERE {paid}) AS total_paid_orders,
              COUNT(*) FILTER (WHERE UPPER(COALESCE(status,'')) IN ('PENDING','CREATED')) AS pending_orders,
              COUNT(*) FILTER (WHERE UPPER(COALESCE(status,'')) IN ('FAILED','CANCELLED')) AS failed_orders,
              0::numeric AS credit_topup_revenue_usd,
              0::numeric AS subscription_revenue_usd
            FROM payments
        """))).mappings().first() or {}))

    if has_redemptions:
        summary["coupon_redemptions"] = int((await db.execute(text("SELECT COUNT(*) FROM billing_coupon_redemptions"))).scalar() or 0)

    return summary


@router.get("/orders")
async def billing_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    payment_method: Optional[str] = None,
    purchase_type: Optional[str] = None,
    coupon_code: Optional[str] = None,
    user_email: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _admin: dict = Depends(get_admin_user),
):
    if not await _has_table(db, "billing_orders"):
        return {"items": [], "total": 0, "page": page, "page_size": page_size}
    params: dict[str, Any] = {"limit": page_size, "offset": (page - 1) * page_size, "from_date": from_date, "to_date": to_date}
    where: list[str] = []
    if status:
        where.append("UPPER(o.status) = :status")
        params["status"] = status.upper()
    if payment_method:
        where.append("UPPER(COALESCE(o.payment_method,o.provider,'')) = :payment_method")
        params["payment_method"] = payment_method.upper()
    if purchase_type:
        where.append("UPPER(COALESCE(o.purchase_type,o.purpose,'')) = :purchase_type")
        params["purchase_type"] = purchase_type.upper()
    if coupon_code:
        where.append("UPPER(COALESCE(o.coupon_code,'')) = :coupon_code")
        params["coupon_code"] = coupon_code.upper()
    if user_email:
        where.append("u.email ILIKE :user_email")
        params["user_email"] = f"%{user_email}%"
    date_sql = _date_filter(params, "o.created_at")
    if date_sql:
        where.append(date_sql)
    where_sql = "WHERE " + " AND ".join(where) if where else ""
    q = text(f"""
        SELECT
          o.id::text, o.created_at AS order_date, o.user_id::text, u.email AS user_email, u.fullname AS user_name,
          COALESCE(o.purchase_type,o.purpose) AS purchase_type, o.plan_code, o.billing_period, o.credit_amount,
          COALESCE(o.subtotal_usd,0) AS subtotal_usd, o.coupon_code, COALESCE(o.discount_usd,0) AS discount_usd,
          COALESCE(o.final_usd,0) AS final_usd, COALESCE(o.payment_method,o.provider) AS payment_method,
          COALESCE(o.payment_currency,o.currency) AS payment_currency, {_coalesce_amount_expr()} AS payment_amount,
          COALESCE(o.gst_amount_inr,0) AS gst_inr, COALESCE(o.final_amount_inr,0) AS final_amount_inr,
          o.provider, o.status, COALESCE(o.provider_order_id,o.razorpay_order_id) AS provider_order_id,
          o.razorpay_payment_id AS provider_payment_id, o.payment_id AS linked_payment_id,
          o.billing_order_id, o.verified_at
        FROM billing_orders o
        LEFT JOIN users u ON CAST(u.id AS TEXT) = CAST(o.user_id AS TEXT)
        {where_sql}
        ORDER BY o.created_at DESC
        OFFSET :offset LIMIT :limit
    """)
    rows = (await db.execute(q, params)).mappings().all()
    total = (await db.execute(text(f"""SELECT COUNT(*) FROM billing_orders o LEFT JOIN users u ON CAST(u.id AS TEXT)=CAST(o.user_id AS TEXT) {where_sql}"""), {k:v for k,v in params.items() if k not in {"limit","offset"}})).scalar() or 0
    return {"items": [_row(r) for r in rows], "total": int(total), "page": page, "page_size": page_size}


@router.get("/payments")
async def billing_payments(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    payment_method: Optional[str] = None,
    purchase_type: Optional[str] = None,
    user_email: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _admin: dict = Depends(get_admin_user),
):
    if not await _has_table(db, "payments"):
        return {"items": [], "total": 0, "skip": skip, "limit": limit}
    has_orders = await _has_table(db, "billing_orders")
    params: dict[str, Any] = {"skip": skip, "limit": limit, "from_date": from_date, "to_date": to_date}
    where: list[str] = []
    if status:
        where.append("UPPER(p.status) = :status")
        params["status"] = status.upper()
    if payment_method:
        where.append("UPPER(COALESCE(o.payment_method,p.provider,'')) = :payment_method")
        params["payment_method"] = payment_method.upper()
    if purchase_type:
        where.append("UPPER(COALESCE(o.purchase_type,p.purpose,'')) = :purchase_type")
        params["purchase_type"] = purchase_type.upper()
    if user_email:
        where.append("u.email ILIKE :user_email")
        params["user_email"] = f"%{user_email}%"
    date_sql = _date_filter(params, "p.created_at")
    if date_sql:
        where.append(date_sql)
    where_sql = "WHERE " + " AND ".join(where) if where else ""
    join_order = "LEFT JOIN billing_orders o ON (o.payment_id = CAST(p.id AS TEXT) OR o.billing_order_id = p.billing_order_id)" if has_orders else "LEFT JOIN (SELECT NULL::text AS payment_id, NULL::text AS billing_order_id, NULL::text AS payment_method, NULL::text AS purchase_type, NULL::numeric AS final_usd, NULL::numeric AS discount_usd, NULL::text AS coupon_code) o ON false"
    rows = (await db.execute(text(f"""
        SELECT p.id::text, p.user_id::text, u.email AS user_email, u.fullname AS user_name,
          p.provider, COALESCE(o.payment_method,p.provider) AS method, COALESCE(o.payment_currency,p.currency) AS currency,
          COALESCE(o.payment_amount,p.amount_inr,0) AS amount, p.status, p.billing_order_id AS linked_order,
          COALESCE(o.purchase_type,p.purpose) AS purchase_type, COALESCE(o.final_usd,0) AS final_usd,
          COALESCE(o.discount_usd,0) AS discount_usd, o.coupon_code,
          p.razorpay_order_id, p.razorpay_payment_id, p.verified_at, p.created_at, p.updated_at,
          COALESCE(p.razorpay_payment_id,p.razorpay_order_id,p.billing_order_id,p.id::text) AS provider_reference
        FROM payments p
        {join_order}
        LEFT JOIN users u ON CAST(u.id AS TEXT) = CAST(p.user_id AS TEXT)
        {where_sql}
        ORDER BY p.created_at DESC
        OFFSET :skip LIMIT :limit
    """), params)).mappings().all()
    total = (await db.execute(text(f"""SELECT COUNT(*) FROM payments p {join_order} LEFT JOIN users u ON CAST(u.id AS TEXT)=CAST(p.user_id AS TEXT) {where_sql}"""), {k:v for k,v in params.items() if k not in {"skip","limit"}})).scalar() or 0
    return {"items": [_row(r) for r in rows], "total": int(total), "skip": skip, "limit": limit}


@router.get("/coupon-redemptions")
async def coupon_redemptions(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    coupon_code: Optional[str] = None,
    user_email: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _admin: dict = Depends(get_admin_user),
):
    if not await _has_table(db, "billing_coupon_redemptions"):
        return {"items": [], "total": 0, "skip": skip, "limit": limit}
    params: dict[str, Any] = {"skip": skip, "limit": limit}
    where: list[str] = []
    if coupon_code:
        where.append("UPPER(r.coupon_code) = :coupon_code")
        params["coupon_code"] = coupon_code.upper()
    if user_email:
        where.append("u.email ILIKE :user_email")
        params["user_email"] = f"%{user_email}%"
    where_sql = "WHERE " + " AND ".join(where) if where else ""
    rows = (await db.execute(text(f"""
        SELECT r.id::text, r.coupon_id::text, r.coupon_code, r.user_id::text, u.email AS user_email, u.fullname AS user_name,
          r.order_id, r.discount_usd, r.redeemed_at
        FROM billing_coupon_redemptions r
        LEFT JOIN users u ON CAST(u.id AS TEXT)=CAST(r.user_id AS TEXT)
        {where_sql}
        ORDER BY r.redeemed_at DESC
        OFFSET :skip LIMIT :limit
    """), params)).mappings().all()
    total = (await db.execute(text(f"SELECT COUNT(*) FROM billing_coupon_redemptions r LEFT JOIN users u ON CAST(u.id AS TEXT)=CAST(r.user_id AS TEXT) {where_sql}"), {k:v for k,v in params.items() if k not in {"skip","limit"}})).scalar() or 0
    return {"items": [_row(r) for r in rows], "total": int(total), "skip": skip, "limit": limit}


@router.get("/user-audit/{user_id}")
async def user_billing_audit(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: dict = Depends(get_admin_user),
):
    payload: dict[str, Any] = {"user_id": user_id, "orders": [], "payments": [], "subscriptions": [], "credits": [], "coupon_redemptions": []}
    if await _has_table(db, "billing_orders"):
        payload["orders"] = [_row(r) for r in (await db.execute(text("SELECT * FROM billing_orders WHERE CAST(user_id AS TEXT)=:user_id ORDER BY created_at DESC LIMIT 50"), {"user_id": user_id})).mappings().all()]
    if await _has_table(db, "payments"):
        payload["payments"] = [_row(r) for r in (await db.execute(text("SELECT * FROM payments WHERE CAST(user_id AS TEXT)=:user_id ORDER BY created_at DESC LIMIT 50"), {"user_id": user_id})).mappings().all()]
    if await _has_table(db, "user_subscriptions"):
        payload["subscriptions"] = [_row(r) for r in (await db.execute(text("SELECT * FROM user_subscriptions WHERE CAST(user_id AS TEXT)=:user_id ORDER BY created_at DESC LIMIT 50"), {"user_id": user_id})).mappings().all()]
    if await _has_table(db, "credit_transactions"):
        payload["credits"] = [_row(r) for r in (await db.execute(text("SELECT * FROM credit_transactions WHERE CAST(user_id AS TEXT)=:user_id ORDER BY created_at DESC LIMIT 100"), {"user_id": user_id})).mappings().all()]
    if await _has_table(db, "billing_coupon_redemptions"):
        payload["coupon_redemptions"] = [_row(r) for r in (await db.execute(text("SELECT * FROM billing_coupon_redemptions WHERE CAST(user_id AS TEXT)=:user_id ORDER BY redeemed_at DESC LIMIT 50"), {"user_id": user_id})).mappings().all()]
    return payload
