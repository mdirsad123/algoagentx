from typing import Dict, Any
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import String, cast, select, text

from .security import get_user_from_token
from ..db.session import async_session
from ..db.models import Plan
from ..services.subscriptions import SubscriptionLifecycleService, SubscriptionLifecycleState

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


async def get_user_entitlements(current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    user_id = str(current_user["user_id"])
    try:
        cycle = await SubscriptionLifecycleService.ensure_user_subscription_cycle(
            db,
            user_id,
            for_update=False,
            auto_commit=False,
        )
        subscription = cycle.get("subscription")
        plan: Plan | None = cycle.get("plan")
        lifecycle_state = str(cycle.get("lifecycle_state") or SubscriptionLifecycleState.NONE.value)

        if subscription and lifecycle_state in {
            SubscriptionLifecycleState.ACTIVE.value,
            SubscriptionLifecycleState.TRIAL.value,
        }:
            plan_code = str(getattr(subscription, "plan_code_snapshot", None) or getattr(plan, "code", None) or "FREE").upper()
            billing_period = str(getattr(subscription, "billing_period_snapshot", None) or getattr(plan, "billing_period", None) or "NONE").upper()
            features = getattr(plan, "features", None) or {}
            subscription_state = "TRIAL" if lifecycle_state == SubscriptionLifecycleState.TRIAL.value else "ACTIVE"
            return {
                "plan_code": plan_code,
                "billing_period": billing_period,
                "price_inr": int(getattr(subscription, "plan_price_inr", None) or getattr(plan, "price_inr", 0) or 0),
                "included_credits": int(cycle.get("included_remaining") or 0),
                "included_credits_total": int(cycle.get("included_total") or 0),
                "next_credit_refill_at": cycle.get("next_refill_at"),
                "last_credit_refill_at": cycle.get("last_refill_at"),
                "features": features,
                "subscription_id": str(subscription.id),
                "subscription_status": subscription_state,
                "subscription_state": subscription_state,
                "trial_remaining_days": 0,
                "is_trial": lifecycle_state == SubscriptionLifecycleState.TRIAL.value,
                "is_premium": plan_code != "FREE",
            }
    except Exception:
        pass

    free_plan = (
        await db.execute(
            select(Plan)
            .where(cast(Plan.code, String).ilike("FREE"), Plan.is_active == True)
            .order_by(Plan.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    free_features = getattr(free_plan, "features", None) or {}
    return {
        "plan_code": "FREE",
        "billing_period": "NONE",
        "price_inr": 0,
        "included_credits": 0,
        "included_credits_total": int(getattr(free_plan, "included_credits", 0) or 0),
        "next_credit_refill_at": None,
        "last_credit_refill_at": None,
        "features": free_features,
        "subscription_id": None,
        "subscription_status": "EXPIRED",
        "subscription_state": "EXPIRED",
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
    plan_code = str(entitlements.get("plan_code") or "FREE").upper()

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
        if plan_code == "FREE" and (mode != "basic" or depth != "light"):
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
        "allowed_modes": ["basic"] if plan_code == "FREE" else (["basic", "advanced"] if is_trial else ["basic", "advanced", "premium"]),
        "allowed_depths": ["light"] if plan_code == "FREE" else (["light", "medium"] if is_trial else ["light", "medium", "deep"]),
    }


async def get_admin_user(current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    """Require an active admin account from the database for every admin API call.

    Production hardening note: a JWT with role=admin is not enough by itself.
    The user may have been demoted, disabled, deleted, or the token may be stale.
    """
    user_id = current_user.get("user_id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication credentials")

    try:
        result = await db.execute(
            text("""
                SELECT role
                FROM users
                WHERE CAST(id AS TEXT) = :user_id
                LIMIT 1
            """),
            {"user_id": str(user_id)},
        )
        row = result.first()
    except Exception:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Unable to verify admin session")

    if not row:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication credentials")

    db_role = str(row[0] or "").lower()

    if db_role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    current_user["role"] = "admin"
    return current_user
