from __future__ import annotations

import json
from typing import Any

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.schemas.profile_settings import ChangePasswordRequest, ProfileResponse, ProfileStats, ProfileUpdate, SettingsResponse, SettingsUpdate

profile_router = APIRouter()
settings_router = APIRouter()

DEFAULT_PREFERENCES = {"default_broker": "", "default_strategy": "", "default_timeframe": "15m", "default_risk_mode": "balanced"}
DEFAULT_INAPP_NOTIFICATIONS = {
    "support_replies": True,
    "trade_order_updates": True,
    "live_approval_requests": True,
    "broker_connection_alerts": True,
    "billing_payment_updates": True,
    "strategy_request_updates": True,
}
DEFAULT_EMAIL_TYPES = {
    "support_replies": True,
    "support_new_ticket_admin": True,
    "ticket_status_updates": True,
    "login_alerts": False,
    "admin_login_alerts": True,
    "trade_order_updates": True,
    "live_approval_requests": True,
    "broker_alerts": True,
    "billing_payment_updates": True,
    "subscription_updates": True,
    "credit_updates": True,
    "strategy_request_updates": True,
    "backtest_updates": False,
    "user_support_replies_admin": True,
    "new_strategy_request_admin": True,
    "failed_payment_refund_admin": True,
    "failed_order_admin": True,
    "system_critical_alerts_admin": True,
}
DEFAULT_NOTIFICATIONS = {
    **DEFAULT_INAPP_NOTIFICATIONS,
    "email_notifications_enabled": True,
    "email_notification_types": DEFAULT_EMAIL_TYPES,
}
DEFAULT_SAFETY = {"require_live_approval_before_execution": True, "live_sync_warning_enabled": True, "default_order_confirmation_required": True}
DEFAULT_ADMIN_ALERTS = {"new_support_ticket": True, "new_strategy_request": True, "failed_payment": True, "failed_order": True, "broker_connection_issue": True}


def _user_id(current_user: dict) -> str:
    value = current_user.get("user_id") or current_user.get("id")
    if not value:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user session")
    return str(value)


async def _get_user_row(db: AsyncSession, user_id: str):
    result = await db.execute(text("SELECT * FROM users WHERE CAST(id AS TEXT) = :user_id LIMIT 1"), {"user_id": user_id})
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return row


def _deep_merge(defaults: dict[str, Any], saved: Any) -> dict[str, Any]:
    if not isinstance(saved, dict):
        saved = {}
    merged = {**defaults, **saved}
    for key, default_value in defaults.items():
        if isinstance(default_value, dict):
            saved_value = saved.get(key) if isinstance(saved.get(key), dict) else {}
            merged[key] = _deep_merge(default_value, saved_value)
    return merged


async def _table_exists(db: AsyncSession, table_name: str) -> bool:
    try:
        return bool(await db.scalar(text("SELECT to_regclass(:table_name) IS NOT NULL"), {"table_name": f"public.{table_name}"}))
    except Exception:
        return False


async def _safe_count(db: AsyncSession, sql: str, params: dict[str, Any]) -> int:
    try:
        return int((await db.scalar(text(sql), params)) or 0)
    except Exception:
        return 0


async def _safe_scalar(db: AsyncSession, sql: str, params: dict[str, Any]) -> Any:
    try:
        return await db.scalar(text(sql), params)
    except Exception:
        return None


async def _profile_stats(db: AsyncSession, user_id: str, role: str) -> ProfileStats:
    total_backtests = await _safe_count(db, "SELECT COUNT(*) FROM backtests WHERE CAST(user_id AS TEXT) = :user_id", {"user_id": user_id})
    connected_brokers = await _safe_count(db, "SELECT COUNT(*) FROM broker_accounts WHERE CAST(user_id AS TEXT) = :user_id AND UPPER(COALESCE(status, '')) IN ('CONNECTED', 'ACTIVE')", {"user_id": user_id})
    credit_balance = await _safe_scalar(db, "SELECT balance FROM user_credits WHERE CAST(user_id AS TEXT) = :user_id LIMIT 1", {"user_id": user_id})
    active_subscription = await _safe_scalar(db, "SELECT COALESCE(plan_code_snapshot, status) FROM user_subscriptions WHERE CAST(user_id AS TEXT) = :user_id AND UPPER(COALESCE(status, '')) IN ('ACTIVE', 'TRIAL') ORDER BY created_at DESC NULLS LAST LIMIT 1", {"user_id": user_id})
    return ProfileStats(total_backtests=total_backtests, connected_brokers=connected_brokers, active_subscription=str(active_subscription) if active_subscription else None, credit_balance=int(credit_balance or 0), admin_console_access=str(role).lower() == "admin")


async def _read_settings(db: AsyncSession, user_id: str, role: str) -> SettingsResponse:
    if not await _table_exists(db, "user_settings"):
        return SettingsResponse(preferences=DEFAULT_PREFERENCES, notifications=DEFAULT_NOTIFICATIONS, safety=DEFAULT_SAFETY, admin_alerts=DEFAULT_ADMIN_ALERTS if str(role).lower() == "admin" else {})
    row = (await db.execute(text("SELECT preferences, notifications, safety, admin_alerts FROM user_settings WHERE CAST(user_id AS TEXT) = :user_id LIMIT 1"), {"user_id": user_id})).mappings().first()
    is_admin = str(role).lower() == "admin"
    return SettingsResponse(
        preferences=_deep_merge(DEFAULT_PREFERENCES, row["preferences"] if row else {}),
        notifications=_deep_merge(DEFAULT_NOTIFICATIONS, row["notifications"] if row else {}),
        safety=_deep_merge(DEFAULT_SAFETY, row["safety"] if row else {}),
        admin_alerts=_deep_merge(DEFAULT_ADMIN_ALERTS, row["admin_alerts"] if row and is_admin else {}) if is_admin else {},
    )


@profile_router.get("/me", response_model=ProfileResponse)
async def get_profile(current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    user_id = _user_id(current_user)
    row = await _get_user_row(db, user_id)
    role = str(row.get("role") or "user")
    stats = await _profile_stats(db, user_id, role)
    return ProfileResponse(
        id=row["id"], email=row["email"], role=role,
        full_name=row.get("fullname"), fullname=row.get("fullname"), mobile=row.get("mobile"),
        company=row.get("company") if "company" in row else None,
        created_at=row.get("created_at"), last_login_at=row.get("last_login_at") if "last_login_at" in row else None,
        account_status=row.get("status") if "status" in row and row.get("status") else "active", stats=stats,
    )


@profile_router.patch("/me", response_model=ProfileResponse)
async def update_profile(payload: ProfileUpdate, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    user_id = _user_id(current_user)
    await _get_user_row(db, user_id)
    full_name = payload.full_name if payload.full_name is not None else payload.fullname
    if full_name is not None:
        full_name = full_name.strip()
        if not full_name:
            raise HTTPException(status_code=400, detail="Full name cannot be empty")
        await db.execute(text("UPDATE users SET fullname = :fullname WHERE CAST(id AS TEXT) = :user_id"), {"fullname": full_name, "user_id": user_id})
    if payload.mobile is not None:
        await db.execute(text("UPDATE users SET mobile = :mobile WHERE CAST(id AS TEXT) = :user_id"), {"mobile": payload.mobile.strip() or None, "user_id": user_id})
    await db.commit()
    return await get_profile(current_user, db)


@profile_router.post("/change-password")
async def change_password(payload: ChangePasswordRequest, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    user_id = _user_id(current_user)
    row = await _get_user_row(db, user_id)
    stored_hash = str(row.get("password_hash") or "").strip()
    if not stored_hash:
        raise HTTPException(status_code=400, detail="Password login is not configured for this account")
    try:
        ok = bcrypt.checkpw(payload.current_password.encode("utf-8"), stored_hash.encode("utf-8"))
    except Exception:
        ok = False
    if not ok:
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if payload.current_password == payload.new_password:
        raise HTTPException(status_code=400, detail="New password must be different from current password")
    new_hash = bcrypt.hashpw(payload.new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    await db.execute(text("UPDATE users SET password_hash = :password_hash WHERE CAST(id AS TEXT) = :user_id"), {"password_hash": new_hash, "user_id": user_id})
    await db.commit()
    return {"message": "Password updated successfully"}


@settings_router.get("/me", response_model=SettingsResponse)
async def get_settings(current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    user_id = _user_id(current_user)
    row = await _get_user_row(db, user_id)
    return await _read_settings(db, user_id, str(row.get("role") or "user"))


@settings_router.patch("/me", response_model=SettingsResponse)
async def update_settings(payload: SettingsUpdate, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    user_id = _user_id(current_user)
    row = await _get_user_row(db, user_id)
    role = str(row.get("role") or "user")
    existing = await _read_settings(db, user_id, role)
    preferences = _deep_merge(DEFAULT_PREFERENCES, {**existing.preferences, **(payload.preferences or {})})
    notifications = _deep_merge(DEFAULT_NOTIFICATIONS, {**existing.notifications, **(payload.notifications or {})})
    safety = _deep_merge(DEFAULT_SAFETY, {**existing.safety, **(payload.safety or {})})
    admin_alerts = _deep_merge(DEFAULT_ADMIN_ALERTS, {**existing.admin_alerts, **(payload.admin_alerts or {})}) if role.lower() == "admin" else {}
    if not await _table_exists(db, "user_settings"):
        raise HTTPException(status_code=503, detail="user_settings table is missing. Run the Phase 21D SQL migration first.")
    await db.execute(text("""
        INSERT INTO user_settings (user_id, preferences, notifications, safety, admin_alerts)
        VALUES (CAST(:user_id AS UUID), CAST(:preferences AS JSONB), CAST(:notifications AS JSONB), CAST(:safety AS JSONB), CAST(:admin_alerts AS JSONB))
        ON CONFLICT (user_id) DO UPDATE SET preferences = EXCLUDED.preferences, notifications = EXCLUDED.notifications, safety = EXCLUDED.safety, admin_alerts = EXCLUDED.admin_alerts, updated_at = NOW()
    """), {"user_id": user_id, "preferences": json.dumps(preferences), "notifications": json.dumps(notifications), "safety": json.dumps(safety), "admin_alerts": json.dumps(admin_alerts)})
    await db.commit()
    return SettingsResponse(preferences=preferences, notifications=notifications, safety=safety, admin_alerts=admin_alerts)
