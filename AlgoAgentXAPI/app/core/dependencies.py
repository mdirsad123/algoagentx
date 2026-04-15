from typing import Dict, Any
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from .security import get_user_from_token
from ..db.session import async_session
from ..billing.plan_catalog import PlanCatalog, PlanCode, BillingPeriod

security = HTTPBearer()


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    token = credentials.credentials
    user = get_user_from_token(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def get_db() -> AsyncSession:
    session = async_session()
    try:
        yield session
    finally:
        await session.close()


async def get_read_only_user(current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    return current_user


async def get_user_entitlements(current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    user_id = current_user["user_id"]
    try:
        subscription_query = text("""
            SELECT us.*, p.code, p.billing_period, p.price_inr, p.included_credits, p.features
            FROM user_subscriptions us
            JOIN plans p ON us.plan_id = p.id
            WHERE CAST(us.user_id AS TEXT) = :user_id
              AND us.status = 'ACTIVE'
              AND us.end_at > CURRENT_TIMESTAMP
            ORDER BY us.created_at DESC
            LIMIT 1
        """)
        result = await db.execute(subscription_query, {"user_id": str(user_id)})
        subscription = result.fetchone()
        if subscription:
            plan_features = PlanCatalog.get_plan_features(subscription.code, subscription.billing_period)
            return {
                "plan_code": subscription.code,
                "billing_period": subscription.billing_period,
                "price_inr": subscription.price_inr,
                "included_credits": subscription.included_credits,
                "features": plan_features,
                "subscription_id": str(subscription.id),
                "subscription_status": "ACTIVE",
                "trial_remaining_days": 0,
                "is_trial": False,
                "is_premium": subscription.code != PlanCode.FREE,
            }

        user_query = text("SELECT created_at FROM users WHERE CAST(id AS TEXT) = :user_id")
        user_result = await db.execute(user_query, {"user_id": str(user_id)})
        user_row = user_result.fetchone()
        if user_row and user_row.created_at:
            user_created_at = user_row.created_at
            now = datetime.now(user_created_at.tzinfo) if getattr(user_created_at, "tzinfo", None) else datetime.utcnow()
            trial_end_date = user_created_at + timedelta(days=7)
            if now <= trial_end_date:
                plan_features = PlanCatalog.get_plan_features(PlanCode.FREE, BillingPeriod.NONE)
                return {
                    "plan_code": PlanCode.FREE,
                    "billing_period": BillingPeriod.NONE,
                    "price_inr": 0,
                    "included_credits": 50,
                    "features": plan_features,
                    "subscription_id": None,
                    "subscription_status": "TRIAL",
                    "trial_remaining_days": max(0, (trial_end_date - now).days),
                    "is_trial": True,
                    "is_premium": False,
                }
    except Exception:
        pass

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
        "is_premium": False,
    }


async def check_backtest_limits(
    current_user: dict = Depends(get_current_user),
    entitlements: Dict[str, Any] = Depends(get_user_entitlements),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Backward-compatible limit helper for existing modules."""
    plan_features = entitlements.get("features", {})
    max_backtests_per_day = int(plan_features.get("backtests_per_day", 5) or 5)
    max_date_range_days = int(plan_features.get("max_date_range_days", 30) or 30)

    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)

    try:
        result = await db.execute(
            text("""
                SELECT COUNT(*) AS count
                FROM backtests
                WHERE CAST(user_id AS TEXT) = :user_id
                  AND created_at >= :start_date
                  AND created_at < :end_date
            """),
            {"user_id": str(current_user["user_id"]), "start_date": today_start, "end_date": today_end},
        )
        daily_count = int(result.scalar() or 0)
    except Exception:
        daily_count = 0

    if daily_count >= max_backtests_per_day:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Daily backtest limit exceeded. Plan allows {max_backtests_per_day} backtests per day.",
        )

    return {
        "max_date_range_days": max_date_range_days,
        "daily_backtest_count": daily_count,
        "max_backtests_per_day": max_backtests_per_day,
        "can_run_backtest": True,
    }


async def check_ai_screener_limits(
    current_user: dict = Depends(get_current_user),
    entitlements: Dict[str, Any] = Depends(get_user_entitlements),
    db: AsyncSession = Depends(get_db),
    mode: str | None = None,
    depth: str | None = None,
) -> Dict[str, Any]:
    """Backward-compatible AI screener limit helper for existing routers."""
    plan_features = entitlements.get("features", {})
    max_ai_runs_per_day = int(plan_features.get("ai_runs_per_day", 3) or 3)
    plan_code = entitlements.get("plan_code", PlanCode.FREE)

    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)

    try:
        result = await db.execute(
            text("""
                SELECT COUNT(*) AS count
                FROM credit_transactions
                WHERE CAST(user_id AS TEXT) = :user_id
                  AND type = 'DEBIT'
                  AND reason LIKE '%AI%'
                  AND created_at >= :start_date
                  AND created_at < :end_date
            """),
            {"user_id": str(current_user["user_id"]), "start_date": today_start, "end_date": today_end},
        )
        daily_count = int(result.scalar() or 0)
    except Exception:
        daily_count = 0

    if daily_count >= max_ai_runs_per_day:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Daily AI screener limit exceeded. Plan allows {max_ai_runs_per_day} runs per day.",
        )

    is_trial = bool(entitlements.get("is_trial", False))
    if mode and depth:
        if plan_code == PlanCode.FREE and (mode != "basic" or depth != "light"):
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail={
                    "detail": "Upgrade required",
                    "code": "PLAN_REQUIRED",
                    "message": "Advanced AI screener features require a premium subscription. Free users can only use basic mode with light depth.",
                },
            )
        elif is_trial and (mode not in ["basic", "advanced"] or depth not in ["light", "medium"]):
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail={
                    "detail": "Upgrade required",
                    "code": "PLAN_REQUIRED",
                    "message": "Deep analysis and premium features require a paid subscription. Trial users can access basic and advanced modes with light and medium depth.",
                },
            )

    return {
        "daily_ai_runs_count": daily_count,
        "max_ai_runs_per_day": max_ai_runs_per_day,
        "can_run_ai_screener": True,
        "plan_code": plan_code,
        "is_trial": is_trial,
        "allowed_modes": ["basic"] if plan_code == PlanCode.FREE else (["basic", "advanced"] if is_trial else ["basic", "advanced", "premium"]),
        "allowed_depths": ["light"] if plan_code == PlanCode.FREE else (["light", "medium"] if is_trial else ["light", "medium", "deep"]),
    }


async def get_admin_user(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user
