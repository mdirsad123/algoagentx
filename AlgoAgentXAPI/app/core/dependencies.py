from typing import Generator, Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from contextlib import asynccontextmanager
from decimal import Decimal

from .security import get_user_from_token
from ..db.session import async_session
from ..billing.plan_catalog import PlanCatalog, PlanCode, BillingPeriod

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """
    Dependency to get current authenticated user from JWT token
    """
    token = credentials.credentials
    user = get_user_from_token(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


@asynccontextmanager
async def get_db() -> AsyncSession:
    """
    Dependency to get database session
    """
    session = async_session()
    try:
        yield session
    finally:
        await session.close()


async def get_read_only_user(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Dependency for read-only operations, ensures user has read access
    """
    # Add any additional read-only checks if needed
    return current_user


async def get_user_entitlements(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get user's subscription entitlements and plan benefits
    
    Logic:
    1. Check for active subscription
    2. If none: check if within 7 days of user.created_at (FREE trial)
    3. Else: FREE limited access
    
    Returns:
        Dict with plan info, limits, trial status, and credits
    """
    user_id = current_user["user_id"]
    
    try:
        # Check for active subscription
        subscription_query = text("""
            SELECT us.*, p.code, p.billing_period, p.price_inr, p.included_credits, p.features
            FROM user_subscriptions us
            JOIN plans p ON us.plan_id = p.id
            WHERE us.user_id = :user_id 
            AND us.status = 'ACTIVE'
            AND us.end_at > NOW()
            ORDER BY us.created_at DESC
            LIMIT 1
        """)
        
        result = await db.execute(subscription_query, {"user_id": user_id})
        subscription = result.fetchone()
        
        if subscription:
            # Active subscription found
            plan_features = PlanCatalog.get_plan_features(subscription.code, subscription.billing_period)
            
            return {
                "plan_code": subscription.code,
                "billing_period": subscription.billing_period,
                "price_inr": subscription.price_inr,
                "included_credits": subscription.included_credits,
                "features": plan_features,
                "subscription_id": subscription.id,
                "subscription_status": "ACTIVE",
                "trial_remaining_days": 0,
                "is_trial": False,
                "is_premium": subscription.code != PlanCode.FREE
            }
        
        # No active subscription, check for FREE trial
        user_query = text("""
            SELECT created_at FROM users WHERE id = :user_id
        """)
        
        user_result = await db.execute(user_query, {"user_id": user_id})
        user_row = user_result.fetchone()
        
        if user_row:
            user_created_at = user_row.created_at
            trial_end_date = user_created_at + timedelta(days=7)
            now = datetime.utcnow()
            
            if now <= trial_end_date:
                # User is in FREE trial period
                plan_features = PlanCatalog.get_plan_features(PlanCode.FREE, BillingPeriod.NONE)
                
                return {
                    "plan_code": PlanCode.FREE,
                    "billing_period": BillingPeriod.NONE,
                    "price_inr": 0,
                    "included_credits": 50,  # Default FREE trial credits
                    "features": plan_features,
                    "subscription_id": None,
                    "subscription_status": "TRIAL",
                    "trial_remaining_days": max(0, (trial_end_date - now).days),
                    "is_trial": True,
                    "is_premium": False
                }
        
        # No subscription and trial expired - FREE limited access
        plan_features = PlanCatalog.get_plan_features(PlanCode.FREE, BillingPeriod.NONE)
        
        return {
            "plan_code": PlanCode.FREE,
            "billing_period": BillingPeriod.NONE,
            "price_inr": 0,
            "included_credits": 0,
            "features": plan_features,
            "subscription_id": None,
            "subscription_status": "EXPIRED",
            "trial_remaining_days": 0,
            "is_trial": False,
            "is_premium": False
        }
        
    except Exception as e:
        # Fallback to FREE plan if there's any error
        plan_features = PlanCatalog.get_plan_features(PlanCode.FREE, BillingPeriod.NONE)
        
        return {
            "plan_code": PlanCode.FREE,
            "billing_period": BillingPeriod.NONE,
            "price_inr": 0,
            "included_credits": 0,
            "features": plan_features,
            "subscription_id": None,
            "subscription_status": "ERROR",
            "trial_remaining_days": 0,
            "is_trial": False,
            "is_premium": False
        }


async def check_backtest_limits(
    current_user: dict = Depends(get_current_user),
    entitlements: Dict[str, Any] = Depends(get_user_entitlements),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Check if user can run backtest based on plan limits
    
    Validates:
    - Daily backtest count limit
    - Maximum date range allowed
    """
    plan_features = entitlements["features"]
    max_backtests_per_day = plan_features.get("backtests_per_day", 5)
    max_date_range_days = plan_features.get("max_date_range_days", 30)
    
    # Check daily backtest count
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    
    backtest_count_query = text("""
        SELECT COUNT(*) as count FROM backtests 
        WHERE user_id = :user_id AND created_at >= :start_date AND created_at < :end_date
    """)
    
    result = await db.execute(backtest_count_query, {
        "user_id": current_user["user_id"],
        "start_date": today_start,
        "end_date": today_end
    })
    
    daily_count = result.scalar() or 0
    
    if daily_count >= max_backtests_per_day:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Daily backtest limit exceeded. Plan allows {max_backtests_per_day} backtests per day."
        )
    
    return {
        "max_date_range_days": max_date_range_days,
        "daily_backtest_count": daily_count,
        "max_backtests_per_day": max_backtests_per_day,
        "can_run_backtest": True
    }


async def check_ai_screener_limits(
    current_user: dict = Depends(get_current_user),
    entitlements: Dict[str, Any] = Depends(get_user_entitlements),
    db: AsyncSession = Depends(get_db),
    mode: str = None,
    depth: str = None
) -> Dict[str, Any]:
    """
    Check if user can run AI screener based on plan limits
    
    Validates:
    - Daily AI runs count limit
    - Plan-based access to advanced/premium modes and deep depth
    """
    plan_features = entitlements["features"]
    max_ai_runs_per_day = plan_features.get("ai_runs_per_day", 3)
    plan_code = entitlements.get("plan_code", "FREE")
    
    # Check daily AI runs count
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    
    # Count AI screener runs from credit transactions
    ai_runs_count_query = text("""
        SELECT COUNT(*) as count FROM credit_transactions 
        WHERE user_id = :user_id AND type = 'DEBIT' AND reason LIKE '%AI%' 
        AND created_at >= :start_date AND created_at < :end_date
    """)
    
    result = await db.execute(ai_runs_count_query, {
        "user_id": current_user["user_id"],
        "start_date": today_start,
        "end_date": today_end
    })
    
    daily_count = result.scalar() or 0
    
    if daily_count >= max_ai_runs_per_day:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Daily AI screener limit exceeded. Plan allows {max_ai_runs_per_day} runs per day."
        )
    
    # Check plan-based access to advanced features
    if mode and depth:
        # Free users can only access basic mode with light depth
        if plan_code == "FREE":
            if mode != "basic" or depth != "light":
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail={
                        "detail": "Upgrade required",
                        "code": "PLAN_REQUIRED",
                        "message": "Advanced AI screener features require a premium subscription. Free users can only use basic mode with light depth."
                    }
                )
        # Premium users can access all modes and depths
        elif plan_code in ["PREMIUM", "PREMIUM_ANNUAL"]:
            pass  # Allow all modes and depths
        # Trial users get limited access (same as free but with some premium features)
        elif entitlements.get("is_trial", False):
            if mode not in ["basic", "advanced"] or depth not in ["light", "medium"]:
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail={
                        "detail": "Upgrade required",
                        "code": "PLAN_REQUIRED",
                        "message": "Deep analysis and premium features require a paid subscription. Trial users can access basic and advanced modes with light and medium depth."
                    }
                )
    
    return {
        "daily_ai_runs_count": daily_count,
        "max_ai_runs_per_day": max_ai_runs_per_day,
        "can_run_ai_screener": True,
        "plan_code": plan_code,
        "is_trial": entitlements.get("is_trial", False),
        "allowed_modes": ["basic"] if plan_code == "FREE" else (["basic", "advanced"] if entitlements.get("is_trial", False) else ["basic", "advanced", "premium"]),
        "allowed_depths": ["light"] if plan_code == "FREE" else (["light", "medium"] if entitlements.get("is_trial", False) else ["light", "medium", "deep"])
    }


async def get_admin_user(
    current_user: dict = Depends(get_current_user)
) -> dict:
    """
    Dependency to ensure user has admin role
    """
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user
