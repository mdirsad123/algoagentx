from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime, timedelta
from ...core.dependencies import get_current_user, get_db, get_admin_user
from ...services.read_only import ReadOnlyService
from ...schemas import User, NotificationResponse, PerformanceMetric

router = APIRouter()


@router.get("/metrics")
async def get_admin_metrics(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_admin_user)
):
    """
    Get admin dashboard metrics
    """
    try:
        # Get user counts
        total_users = await ReadOnlyService.get_user_count(db)
        active_users = await ReadOnlyService.get_active_user_count(db)
        
        # Get payment stats
        total_payments = await ReadOnlyService.get_payment_count(db)
        total_revenue = await ReadOnlyService.get_total_revenue(db)
        
        # Get credit stats
        total_credits = await ReadOnlyService.get_total_credits(db)
        active_subscriptions = await ReadOnlyService.get_active_subscription_count(db)
        
        # Get recent activity
        recent_users = await ReadOnlyService.get_recent_users(db, limit=5)
        recent_payments = await ReadOnlyService.get_recent_payments(db, limit=5)
        recent_screener_jobs = await ReadOnlyService.get_recent_screener_jobs(db, limit=5)
        
        return {
            "users": {
                "total": total_users,
                "active": active_users,
                "recent": recent_users
            },
            "payments": {
                "total": total_payments,
                "revenue": float(total_revenue or 0),
                "recent": recent_payments
            },
            "credits": {
                "total": total_credits,
                "active_subscriptions": active_subscriptions
            },
            "screener_jobs": {
                "recent": recent_screener_jobs
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users")
async def get_all_users(
    skip: int = 0,
    limit: int = 20,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_admin_user)
):
    """
    Get all users with pagination and search
    """
    try:
        users = await ReadOnlyService.get_users_paginated(db, skip=skip, limit=limit, search=search)
        total = await ReadOnlyService.get_user_count(db)
        
        return {
            "users": users,
            "total": total,
            "skip": skip,
            "limit": limit
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/payments")
async def get_all_payments(
    skip: int = 0,
    limit: int = 20,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_admin_user)
):
    """
    Get all payments with pagination and filtering
    """
    try:
        payments = await ReadOnlyService.get_payments_paginated(db, skip=skip, limit=limit, status=status)
        total = await ReadOnlyService.get_payment_count(db)
        
        return {
            "payments": payments,
            "total": total,
            "skip": skip,
            "limit": limit
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/subscriptions")
async def get_all_subscriptions(
    skip: int = 0,
    limit: int = 20,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_admin_user)
):
    """
    Get all subscriptions with pagination and filtering
    """
    try:
        subscriptions = await ReadOnlyService.get_subscriptions_paginated(db, skip=skip, limit=limit, status=status)
        total = await ReadOnlyService.get_subscription_count(db)
        
        return {
            "subscriptions": subscriptions,
            "total": total,
            "skip": skip,
            "limit": limit
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/credits")
async def get_all_credits(
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_admin_user)
):
    """
    Get all credit transactions with pagination
    """
    try:
        credits = await ReadOnlyService.get_credits_paginated(db, skip=skip, limit=limit)
        total = await ReadOnlyService.get_credit_transaction_count(db)
        
        return {
            "credits": credits,
            "total": total,
            "skip": skip,
            "limit": limit
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/support-tickets")
async def get_support_tickets(
    skip: int = 0,
    limit: int = 20,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_admin_user)
):
    """
    Get support tickets (notifications) with pagination and filtering
    """
    try:
        tickets = await ReadOnlyService.get_notifications_paginated(db, skip=skip, limit=limit, status=status)
        total = await ReadOnlyService.get_notification_count(db)
        
        return {
            "tickets": tickets,
            "total": total,
            "skip": skip,
            "limit": limit
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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