from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, func, case, select, and_, or_
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal
from pydantic import BaseModel
import uuid
from ...core.dependencies import get_current_user, get_db, get_admin_user
from ...db.models import User, Payment, UserSubscription, CreditTransaction, JobStatus, Notification, Strategy, PerformanceMetric, SupportTicket, SupportTicketReply

router = APIRouter()


class PaginationResponse(BaseModel):
    """Standard pagination response format"""
    items: List[Any]
    total: int
    page: int
    page_size: int
    total_pages: int


@router.get("/metrics")
async def get_admin_metrics(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_admin_user)
) -> Dict[str, Any]:
    """
    Get comprehensive admin dashboard metrics with efficient aggregate queries.
    
    Returns metrics for:
    - Users (total, active, trial)
    - Payments (total, paid, failed, revenue)
    - Subscriptions (total, active)
    - Credits (issued, used)
    - Strategies (total)
    - Backtests (total)
    - AI Screener Jobs (total, completed, failed)
    """
    try:
        # Get current timestamp for trial calculations
        now = datetime.utcnow()
        
        # 1. User Metrics
        user_query = text("""
            SELECT 
                COUNT(*) as total_users,
                COUNT(CASE WHEN is_active = true THEN 1 END) as active_users,
                COUNT(CASE WHEN created_at >= :trial_cutoff THEN 1 END) as trial_users
            FROM users
        """)
        
        user_result = await db.execute(user_query, {"trial_cutoff": now - timedelta(days=7)})
        user_data = user_result.fetchone()
        
        # 2. Payment Metrics
        payment_query = text("""
            SELECT 
                COUNT(*) as total_payments,
                COUNT(CASE WHEN status = 'PAID' THEN 1 END) as paid_payments,
                COUNT(CASE WHEN status = 'FAILED' THEN 1 END) as failed_payments,
                COALESCE(SUM(CASE WHEN status = 'PAID' THEN amount_inr ELSE 0 END), 0) as revenue_total
            FROM payments
        """)
        
        payment_result = await db.execute(payment_query)
        payment_data = payment_result.fetchone()
        
        # 3. Subscription Metrics
        subscription_query = text("""
            SELECT 
                COUNT(*) as total_subscriptions,
                COUNT(CASE WHEN status = 'ACTIVE' AND end_at > NOW() THEN 1 END) as active_subscriptions
            FROM user_subscriptions
        """)
        
        subscription_result = await db.execute(subscription_query)
        subscription_data = subscription_result.fetchone()
        
        # 4. Credit Metrics
        credit_query = text("""
            SELECT 
                COALESCE(SUM(CASE WHEN type = 'CREDIT' THEN credits ELSE 0 END), 0) as total_credits_issued,
                COALESCE(SUM(CASE WHEN type = 'DEBIT' THEN credits ELSE 0 END), 0) as credits_used
            FROM credit_transactions
        """)
        
        credit_result = await db.execute(credit_query)
        credit_data = credit_result.fetchone()
        
        # 5. Strategy Metrics
        strategy_query = text("""
            SELECT COUNT(*) as total_strategies
            FROM strategies
        """)
        
        strategy_result = await db.execute(strategy_query)
        strategy_data = strategy_result.fetchone()
        
        # 6. Backtest Metrics
        backtest_query = text("""
            SELECT COUNT(*) as total_backtests
            FROM performance_metrics
        """)
        
        backtest_result = await db.execute(backtest_query)
        backtest_data = backtest_result.fetchone()
        
        # 7. AI Screener Job Metrics
        job_query = text("""
            SELECT 
                COUNT(*) as total_ai_screener_jobs,
                COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_jobs,
                COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_jobs
            FROM job_status
            WHERE job_type = 'ai_screener'
        """)
        
        job_result = await db.execute(job_query)
        job_data = job_result.fetchone()
        
        # 8. Recent Activity (for dashboard cards)
        recent_users_query = text("""
            SELECT id, email, role, created_at
            FROM users
            ORDER BY created_at DESC
            LIMIT 5
        """)
        
        recent_users_result = await db.execute(recent_users_query)
        recent_users = [dict(row._mapping) for row in recent_users_result.fetchall()]
        
        recent_payments_query = text("""
            SELECT id, user_id, amount_inr, status, created_at
            FROM payments
            ORDER BY created_at DESC
            LIMIT 5
        """)
        
        recent_payments_result = await db.execute(recent_payments_query)
        recent_payments = [dict(row._mapping) for row in recent_payments_result.fetchall()]
        
        recent_jobs_query = text("""
            SELECT id, user_id, status, progress, message, created_at
            FROM job_status
            WHERE job_type = 'ai_screener'
            ORDER BY created_at DESC
            LIMIT 5
        """)
        
        recent_jobs_result = await db.execute(recent_jobs_query)
        recent_jobs = [dict(row._mapping) for row in recent_jobs_result.fetchall()]
        
        # 9. Support Tickets (Notifications)
        ticket_query = text("""
            SELECT 
                COUNT(*) as total_tickets,
                COUNT(CASE WHEN status = 'unread' THEN 1 END) as unread_tickets
            FROM notifications
        """)
        
        ticket_result = await db.execute(ticket_query)
        ticket_data = ticket_result.fetchone()
        
        # Build response
        return {
            # Core Metrics for Dashboard Cards
            "users": {
                "total": user_data.total_users,
                "active": user_data.active_users,
                "trial": user_data.trial_users,
                "recent": recent_users
            },
            "payments": {
                "total": payment_data.total_payments,
                "paid": payment_data.paid_payments,
                "failed": payment_data.failed_payments,
                "revenue_total": float(payment_data.revenue_total or 0)
            },
            "subscriptions": {
                "total": subscription_data.total_subscriptions,
                "active": subscription_data.active_subscriptions
            },
            "credits": {
                "total_issued": credit_data.total_credits_issued,
                "used": credit_data.credits_used,
                "available": credit_data.total_credits_issued - credit_data.credits_used
            },
            "strategies": {
                "total": strategy_data.total_strategies
            },
            "backtests": {
                "total": backtest_data.total_backtests
            },
            "ai_screener_jobs": {
                "total": job_data.total_ai_screener_jobs,
                "completed": job_data.completed_jobs,
                "failed": job_data.failed_jobs,
                "recent": recent_jobs
            },
            "support_tickets": {
                "total": ticket_data.total_tickets,
                "unread": ticket_data.unread_tickets
            },
            # Recent Activity for Dashboard
            "recent_activity": {
                "recent_users": recent_users,
                "recent_payments": recent_payments,
                "recent_jobs": recent_jobs
            },
            # Metadata
            "generated_at": now.isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to fetch admin metrics: {str(e)}"
        )


@router.get("/users")
async def get_admin_users(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search by email or name"),
    status: Optional[str] = Query(None, description="Filter by status (active, inactive)"),
    role: Optional[str] = Query(None, description="Filter by role (user, admin)"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_admin_user)
):
    """
    Get admin list of users with pagination, search, and filtering
    """
    try:
        # Calculate offset for pagination
        skip = (page - 1) * page_size
        
        # Build query with filters
        query = text("""
            SELECT u.id, u.email, u.full_name, u.role, u.is_active, u.created_at, u.updated_at
            FROM users u
            WHERE 1=1
        """)
        
        params = {}
        conditions = []
        
        if search:
            conditions.append("(u.email ILIKE :search OR u.full_name ILIKE :search)")
            params["search"] = f"%{search}%"
        
        if status:
            if status.lower() == "active":
                conditions.append("u.is_active = true")
            elif status.lower() == "inactive":
                conditions.append("u.is_active = false")
        
        if role:
            conditions.append("u.role = :role")
            params["role"] = role
        
        if conditions:
            query = text(str(query) + " AND " + " AND ".join(conditions))
        
        query = query + text(" ORDER BY u.created_at DESC OFFSET :skip LIMIT :limit")
        params.update({"skip": skip, "limit": page_size})
        
        # Get total count for pagination
        count_query = text("""
            SELECT COUNT(*) FROM users u WHERE 1=1
        """)
        count_conditions = conditions.copy()
        if count_conditions:
            count_query = text(str(count_query) + " AND " + " AND ".join(count_conditions))
        
        total_result = await db.execute(count_query, params)
        total = total_result.scalar()
        
        # Get paginated results
        result = await db.execute(query, params)
        users = [dict(row._mapping) for row in result.fetchall()]
        
        # Calculate total pages
        total_pages = (total + page_size - 1) // page_size
        
        return PaginationResponse(
            items=users,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch users: {str(e)}")


@router.get("/payments")
async def get_admin_payments(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status: Optional[str] = Query(None, description="Filter by payment status"),
    from_date: Optional[str] = Query(None, description="Filter from date (YYYY-MM-DD)"),
    to_date: Optional[str] = Query(None, description="Filter to date (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_admin_user)
):
    """
    Get admin list of payments with pagination and filtering
    """
    try:
        # Calculate offset for pagination
        skip = (page - 1) * page_size
        
        # Build query with filters
        query = text("""
            SELECT p.id, p.user_id, p.provider, p.purpose, p.amount_inr, p.currency, 
                   p.status, p.razorpay_order_id, p.razorpay_payment_id, p.created_at, p.updated_at
            FROM payments p
            WHERE 1=1
        """)
        
        params = {}
        conditions = []
        
        if status:
            conditions.append("p.status = :status")
            params["status"] = status
        
        if from_date:
            try:
                from_dt = datetime.strptime(from_date, "%Y-%m-%d")
                conditions.append("p.created_at >= :from_date")
                params["from_date"] = from_dt
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid from_date format. Use YYYY-MM-DD")
        
        if to_date:
            try:
                to_dt = datetime.strptime(to_date, "%Y-%m-%d")
                conditions.append("p.created_at <= :to_date")
                params["to_date"] = to_dt
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid to_date format. Use YYYY-MM-DD")
        
        if conditions:
            query = text(str(query) + " AND " + " AND ".join(conditions))
        
        query = query + text(" ORDER BY p.created_at DESC OFFSET :skip LIMIT :limit")
        params.update({"skip": skip, "limit": page_size})
        
        # Get total count for pagination
        count_query = text("""
            SELECT COUNT(*) FROM payments p WHERE 1=1
        """)
        count_conditions = conditions.copy()
        if count_conditions:
            count_query = text(str(count_query) + " AND " + " AND ".join(count_conditions))
        
        total_result = await db.execute(count_query, params)
        total = total_result.scalar()
        
        # Get paginated results
        result = await db.execute(query, params)
        payments = [dict(row._mapping) for row in result.fetchall()]
        
        # Calculate total pages
        total_pages = (total + page_size - 1) // page_size
        
        return PaginationResponse(
            items=payments,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch payments: {str(e)}")


@router.get("/subscriptions")
async def get_admin_subscriptions(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status: Optional[str] = Query(None, description="Filter by subscription status"),
    plan: Optional[str] = Query(None, description="Filter by plan code"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_admin_user)
):
    """
    Get admin list of subscriptions with pagination and filtering
    """
    try:
        # Calculate offset for pagination
        skip = (page - 1) * page_size
        
        # Build query with filters
        query = text("""
            SELECT us.id, us.user_id, us.plan_id, us.status, us.start_at, us.end_at, 
                   us.trial_end_at, us.renews, us.razorpay_subscription_id, us.razorpay_customer_id,
                   us.created_at, p.code as plan_code, p.billing_period, p.price_inr, p.name as plan_name
            FROM user_subscriptions us
            JOIN plans p ON us.plan_id = p.id
            WHERE 1=1
        """)
        
        params = {}
        conditions = []
        
        if status:
            conditions.append("us.status = :status")
            params["status"] = status
        
        if plan:
            conditions.append("p.code = :plan")
            params["plan"] = plan
        
        if conditions:
            query = text(str(query) + " AND " + " AND ".join(conditions))
        
        query = query + text(" ORDER BY us.created_at DESC OFFSET :skip LIMIT :limit")
        params.update({"skip": skip, "limit": page_size})
        
        # Get total count for pagination
        count_query = text("""
            SELECT COUNT(*) FROM user_subscriptions us
            JOIN plans p ON us.plan_id = p.id
            WHERE 1=1
        """)
        count_conditions = conditions.copy()
        if count_conditions:
            count_query = text(str(count_query) + " AND " + " AND ".join(count_conditions))
        
        total_result = await db.execute(count_query, params)
        total = total_result.scalar()
        
        # Get paginated results
        result = await db.execute(query, params)
        subscriptions = [dict(row._mapping) for row in result.fetchall()]
        
        # Calculate total pages
        total_pages = (total + page_size - 1) // page_size
        
        return PaginationResponse(
            items=subscriptions,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch subscriptions: {str(e)}")


@router.get("/credits/ledger")
async def get_admin_credits_ledger(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    from_date: Optional[str] = Query(None, description="Filter from date (YYYY-MM-DD)"),
    to_date: Optional[str] = Query(None, description="Filter to date (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_admin_user)
):
    """
    Get admin credits ledger with pagination and filtering
    """
    try:
        # Calculate offset for pagination
        skip = (page - 1) * page_size
        
        # Build query with filters
        query = text("""
            SELECT ct.id, ct.user_id, ct.transaction_type, ct.amount, ct.balance_after, 
                   ct.description, ct.backtest_id, ct.job_id, ct.created_at,
                   u.email as user_email, u.full_name as user_name
            FROM credit_transactions ct
            JOIN users u ON ct.user_id = u.id
            WHERE 1=1
        """)
        
        params = {}
        conditions = []
        
        if user_id:
            conditions.append("ct.user_id = :user_id")
            params["user_id"] = user_id
        
        if from_date:
            try:
                from_dt = datetime.strptime(from_date, "%Y-%m-%d")
                conditions.append("ct.created_at >= :from_date")
                params["from_date"] = from_dt
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid from_date format. Use YYYY-MM-DD")
        
        if to_date:
            try:
                to_dt = datetime.strptime(to_date, "%Y-%m-%d")
                conditions.append("ct.created_at <= :to_date")
                params["to_date"] = to_dt
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid to_date format. Use YYYY-MM-DD")
        
        if conditions:
            query = text(str(query) + " AND " + " AND ".join(conditions))
        
        query = query + text(" ORDER BY ct.created_at DESC OFFSET :skip LIMIT :limit")
        params.update({"skip": skip, "limit": page_size})
        
        # Get total count for pagination
        count_query = text("""
            SELECT COUNT(*) FROM credit_transactions ct
            JOIN users u ON ct.user_id = u.id
            WHERE 1=1
        """)
        count_conditions = conditions.copy()
        if count_conditions:
            count_query = text(str(count_query) + " AND " + " AND ".join(count_conditions))
        
        total_result = await db.execute(count_query, params)
        total = total_result.scalar()
        
        # Get paginated results
        result = await db.execute(query, params)
        credits = [dict(row._mapping) for row in result.fetchall()]
        
        # Calculate total pages
        total_pages = (total + page_size - 1) // page_size
        
        return PaginationResponse(
            items=credits,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch credits ledger: {str(e)}")


@router.get("/support-tickets")
async def get_admin_support_tickets(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status: Optional[str] = Query(None, description="Filter by ticket status"),
    priority: Optional[str] = Query(None, description="Filter by ticket priority"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_admin_user)
):
    """
    Get all support tickets for admin with pagination and filtering
    """
    try:
        # Calculate offset for pagination
        skip = (page - 1) * page_size
        
        # Build query with filters
        query = text("""
            SELECT st.id, st.user_id, st.subject, st.message, st.status, st.priority, 
                   st.created_at, st.updated_at, u.email as user_email, u.full_name as user_name
            FROM support_tickets st
            JOIN users u ON st.user_id = u.id
            WHERE 1=1
        """)
        
        params = {}
        conditions = []
        
        if status:
            conditions.append("st.status = :status")
            params["status"] = status
        
        if priority:
            conditions.append("st.priority = :priority")
            params["priority"] = priority
        
        if conditions:
            query = text(str(query) + " AND " + " AND ".join(conditions))
        
        query = query + text(" ORDER BY st.created_at DESC OFFSET :skip LIMIT :limit")
        params.update({"skip": skip, "limit": page_size})
        
        # Get total count for pagination
        count_query = text("""
            SELECT COUNT(*) FROM support_tickets st
            JOIN users u ON st.user_id = u.id
            WHERE 1=1
        """)
        count_conditions = conditions.copy()
        if count_conditions:
            count_query = text(str(count_query) + " AND " + " AND ".join(count_conditions))
        
        total_result = await db.execute(count_query, params)
        total = total_result.scalar()
        
        # Get paginated results
        result = await db.execute(query, params)
        tickets = [dict(row._mapping) for row in result.fetchall()]
        
        # Calculate total pages
        total_pages = (total + page_size - 1) // page_size
        
        return PaginationResponse(
            items=tickets,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch support tickets: {str(e)}")


@router.get("/support-tickets/{ticket_id}")
async def get_admin_support_ticket(
    ticket_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_admin_user)
):
    """
    Get a specific support ticket by ID for admin
    """
    try:
        # Get ticket with user info
        ticket_query = text("""
            SELECT st.id, st.user_id, st.subject, st.message, st.status, st.priority, 
                   st.created_at, st.updated_at, u.email as user_email, u.full_name as user_name
            FROM support_tickets st
            JOIN users u ON st.user_id = u.id
            WHERE st.id = :ticket_id
        """)
        
        ticket_result = await db.execute(ticket_query, {"ticket_id": ticket_id})
        ticket = ticket_result.fetchone()
        
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")
        
        # Get replies for this ticket
        replies_query = text("""
            SELECT str.id, str.ticket_id, str.user_id, str.message, str.created_at,
                   u.email as user_email, u.full_name as user_name
            FROM support_ticket_replies str
            LEFT JOIN users u ON str.user_id = u.id
            WHERE str.ticket_id = :ticket_id
            ORDER BY str.created_at ASC
        """)
        
        replies_result = await db.execute(replies_query, {"ticket_id": ticket_id})
        replies = [dict(row._mapping) for row in replies_result.fetchall()]
        
        ticket_data = dict(ticket._mapping)
        ticket_data["replies"] = replies
        
        return ticket_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch support ticket: {str(e)}")


@router.patch("/support-tickets/{ticket_id}")
async def update_support_ticket(
    ticket_id: str,
    update_data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_admin_user)
):
    """
    Update support ticket status or priority
    """
    try:
        # Check if ticket exists
        ticket_query = text("""
            SELECT id, status, priority FROM support_tickets WHERE id = :ticket_id
        """)
        
        ticket_result = await db.execute(ticket_query, {"ticket_id": ticket_id})
        ticket = ticket_result.fetchone()
        
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")
        
        # Build update query
        update_fields = []
        params = {"ticket_id": ticket_id}
        
        if "status" in update_data:
            status = update_data["status"]
            if status not in ["open", "in_progress", "closed"]:
                raise HTTPException(status_code=400, detail="Invalid status")
            update_fields.append("status = :status")
            params["status"] = status
        
        if "priority" in update_data:
            priority = update_data["priority"]
            if priority not in ["low", "medium", "high"]:
                raise HTTPException(status_code=400, detail="Invalid priority")
            update_fields.append("priority = :priority")
            params["priority"] = priority
        
        if not update_fields:
            raise HTTPException(status_code=400, detail="No valid fields to update")
        
        # Update ticket
        update_query = text(f"""
            UPDATE support_tickets 
            SET {', '.join(update_fields)}, updated_at = NOW()
            WHERE id = :ticket_id
        """)
        
        await db.execute(update_query, params)
        await db.commit()
        
        return {"message": "Ticket updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update ticket: {str(e)}")


@router.post("/support-tickets/{ticket_id}/reply")
async def admin_reply_to_support_ticket(
    ticket_id: str,
    reply_data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_admin_user)
):
    """
    Admin reply to a support ticket
    """
    try:
        # Check if ticket exists
        ticket_query = text("""
            SELECT id FROM support_tickets WHERE id = :ticket_id
        """)
        
        ticket_result = await db.execute(ticket_query, {"ticket_id": ticket_id})
        ticket = ticket_result.fetchone()
        
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")
        
        # Validate reply data
        if "message" not in reply_data or not reply_data["message"].strip():
            raise HTTPException(status_code=400, detail="Message is required")
        
        # Create reply
        reply_query = text("""
            INSERT INTO support_ticket_replies (ticket_id, user_id, message, created_at)
            VALUES (:ticket_id, :user_id, :message, NOW())
            RETURNING id, ticket_id, user_id, message, created_at
        """)
        
        reply_result = await db.execute(reply_query, {
            "ticket_id": ticket_id,
            "user_id": current_user["id"],
            "message": reply_data["message"].strip()
        })
        
        reply = reply_result.fetchone()
        await db.commit()
        
        # Update ticket status to in_progress if it was open
        status_update_query = text("""
            UPDATE support_tickets 
            SET status = 'in_progress', updated_at = NOW()
            WHERE id = :ticket_id AND status = 'open'
        """)
        
        await db.execute(status_update_query, {"ticket_id": ticket_id})
        await db.commit()
        
        return {
            "message": "Reply added successfully",
            "reply": dict(reply._mapping)
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to add reply: {str(e)}")


@router.put("/users/{user_id}/status")
async def update_user_status(
    user_id: str,
    is_active: bool,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_admin_user)
):
    """
    Activate or deactivate a user
    """
    try:
        user = await ReadOnlyService.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Update user status
        user.is_active = is_active
        await db.commit()
        
        return {"message": f"User {'activated' if is_active else 'deactivated'} successfully"}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/users/{user_id}/role")
async def update_user_role(
    user_id: str,
    role: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_admin_user)
):
    """
    Update user role (make admin/customer)
    """
    try:
        user = await ReadOnlyService.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Validate role
        if role not in ["user", "admin"]:
            raise HTTPException(status_code=400, detail="Invalid role. Must be 'user' or 'admin'")
        
        # Update user role
        user.role = role
        await db.commit()
        
        return {"message": f"User role updated to {role} successfully"}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/orders")
async def get_admin_orders(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status: Optional[str] = Query(None, description="Filter by order status"),
    search: Optional[str] = Query(None, description="Search by order ID or user email"),
    from_date: Optional[str] = Query(None, description="Filter from date (YYYY-MM-DD)"),
    to_date: Optional[str] = Query(None, description="Filter to date (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_admin_user)
):
    """
    Get admin list of orders with pagination and filtering
    """
    try:
        # Calculate offset for pagination
        skip = (page - 1) * page_size
        
        # Build query with filters
        query = text("""
            SELECT o.id, o.user_id, o.order_number, o.status, o.total_amount, o.currency,
                   o.payment_method, o.created_at, o.updated_at, u.email as user_email, u.full_name as user_name
            FROM orders o
            JOIN users u ON o.user_id = u.id
            WHERE 1=1
        """)
        
        params = {}
        conditions = []
        
        if status:
            conditions.append("o.status = :status")
            params["status"] = status
        
        if search:
            conditions.append("(o.order_number ILIKE :search OR u.email ILIKE :search OR u.full_name ILIKE :search)")
            params["search"] = f"%{search}%"
        
        if from_date:
            try:
                from_dt = datetime.strptime(from_date, "%Y-%m-%d")
                conditions.append("o.created_at >= :from_date")
                params["from_date"] = from_dt
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid from_date format. Use YYYY-MM-DD")
        
        if to_date:
            try:
                to_dt = datetime.strptime(to_date, "%Y-%m-%d")
                conditions.append("o.created_at <= :to_date")
                params["to_date"] = to_dt
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid to_date format. Use YYYY-MM-DD")
        
        if conditions:
            query = text(str(query) + " AND " + " AND ".join(conditions))
        
        query = query + text(" ORDER BY o.created_at DESC OFFSET :skip LIMIT :limit")
        params.update({"skip": skip, "limit": page_size})
        
        # Get total count for pagination
        count_query = text("""
            SELECT COUNT(*) FROM orders o
            JOIN users u ON o.user_id = u.id
            WHERE 1=1
        """)
        count_conditions = conditions.copy()
        if count_conditions:
            count_query = text(str(count_query) + " AND " + " AND ".join(count_conditions))
        
        total_result = await db.execute(count_query, params)
        total = total_result.scalar()
        
        # Get paginated results
        result = await db.execute(query, params)
        orders = [dict(row._mapping) for row in result.fetchall()]
        
        # Calculate total pages
        total_pages = (total + page_size - 1) // page_size
        
        return PaginationResponse(
            items=orders,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch orders: {str(e)}")


@router.get("/orders/{order_id}")
async def get_admin_order(
    order_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_admin_user)
):
    """
    Get a specific order by ID with items
    """
    try:
        # Get order with user info
        order_query = text("""
            SELECT o.id, o.user_id, o.order_number, o.status, o.total_amount, o.currency,
                   o.payment_method, o.created_at, o.updated_at, u.email as user_email, u.full_name as user_name
            FROM orders o
            JOIN users u ON o.user_id = u.id
            WHERE o.id = :order_id
        """)
        
        order_result = await db.execute(order_query, {"order_id": order_id})
        order = order_result.fetchone()
        
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        # Get order items
        items_query = text("""
            SELECT oi.id, oi.order_id, oi.product_type, oi.product_id, oi.quantity, oi.unit_price, oi.total_price,
                   p.name as product_name, p.description as product_description
            FROM order_items oi
            LEFT JOIN products p ON oi.product_id = p.id
            WHERE oi.order_id = :order_id
            ORDER BY oi.created_at ASC
        """)
        
        items_result = await db.execute(items_query, {"order_id": order_id})
        items = [dict(row._mapping) for row in items_result.fetchall()]
        
        order_data = dict(order._mapping)
        order_data["items"] = items
        
        return order_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch order: {str(e)}")


@router.patch("/orders/{order_id}/status")
async def update_order_status(
    order_id: str,
    status: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_admin_user)
):
    """
    Update order status
    """
    try:
        # Check if order exists
        order_query = text("""
            SELECT id, status FROM orders WHERE id = :order_id
        """)
        
        order_result = await db.execute(order_query, {"order_id": order_id})
        order = order_result.fetchone()
        
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        # Validate status
        valid_statuses = ["pending", "processing", "completed", "cancelled", "refunded"]
        if status not in valid_statuses:
            raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}")
        
        # Update order status
        update_query = text("""
            UPDATE orders 
            SET status = :status, updated_at = NOW()
            WHERE id = :order_id
        """)
        
        await db.execute(update_query, {"order_id": order_id, "status": status})
        await db.commit()
        
        return {"message": f"Order status updated to {status} successfully"}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update order status: {str(e)}")


@router.get("/payments/{payment_id}")
async def get_admin_payment(
    payment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_admin_user)
):
    """
    Get a specific payment by ID
    """
    try:
        # Get payment with user info
        payment_query = text("""
            SELECT p.id, p.user_id, p.provider, p.purpose, p.amount_inr, p.currency,
                   p.status, p.razorpay_order_id, p.razorpay_payment_id, p.created_at, p.updated_at,
                   u.email as user_email, u.full_name as user_name
            FROM payments p
            JOIN users u ON p.user_id = u.id
            WHERE p.id = :payment_id
        """)
        
        payment_result = await db.execute(payment_query, {"payment_id": payment_id})
        payment = payment_result.fetchone()
        
        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")
        
        return dict(payment._mapping)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch payment: {str(e)}")


@router.post("/credits/adjust")
async def adjust_user_credits(
    adjust_data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_admin_user)
):
    """
    Admin credit adjustment (credit/debit) for a user
    """
    try:
        user_id = adjust_data.get("user_id")
        amount = adjust_data.get("amount")
        reason = adjust_data.get("reason", "")
        
        # Validate inputs
        if not user_id:
            raise HTTPException(status_code=400, detail="user_id is required")
        if amount is None:
            raise HTTPException(status_code=400, detail="amount is required")
        if not reason.strip():
            raise HTTPException(status_code=400, detail="reason is required")
        
        # Validate amount (can be positive or negative)
        try:
            amount = float(amount)
        except ValueError:
            raise HTTPException(status_code=400, detail="amount must be a valid number")
        
        # Check if user exists
        user_query = text("""
            SELECT id, email FROM users WHERE id = :user_id
        """)
        
        user_result = await db.execute(user_query, {"user_id": user_id})
        user = user_result.fetchone()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get current balance
        balance_query = text("""
            SELECT COALESCE(SUM(CASE WHEN type = 'CREDIT' THEN credits ELSE 0 END), 0) - 
                   COALESCE(SUM(CASE WHEN type = 'DEBIT' THEN credits ELSE 0 END), 0) as balance
            FROM credit_transactions
            WHERE user_id = :user_id
        """)
        
        balance_result = await db.execute(balance_query, {"user_id": user_id})
        current_balance = balance_result.scalar() or 0
        
        # Calculate new balance
        new_balance = current_balance + amount
        
        # Validate that balance doesn't go negative (if this is a debit)
        if new_balance < 0:
            raise HTTPException(status_code=400, detail="Credit adjustment would result in negative balance")
        
        # Create credit transaction
        transaction_type = "CREDIT" if amount > 0 else "DEBIT"
        abs_amount = abs(amount)
        
        transaction_query = text("""
            INSERT INTO credit_transactions (id, user_id, credits, type, reason, balance_after, created_at)
            VALUES (:id, :user_id, :credits, :type, :reason, :balance_after, NOW())
            RETURNING id, user_id, credits, type, reason, balance_after, created_at
        """)
        
        transaction_result = await db.execute(transaction_query, {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "credits": abs_amount,
            "type": transaction_type,
            "reason": f"Admin adjustment: {reason}",
            "balance_after": new_balance
        })
        
        transaction = transaction_result.fetchone()
        await db.commit()
        
        return {
            "message": "Credit adjustment successful",
            "transaction": dict(transaction._mapping),
            "new_balance": new_balance
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to adjust credits: {str(e)}")
