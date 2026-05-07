from datetime import datetime, timedelta, timezone
import bcrypt
import hashlib
import logging
import secrets
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from jose import jwt
from sqlalchemy import select, text, update
from sqlalchemy.exc import SQLAlchemyError

from ...core.config import settings
from ...core.security import get_current_user
from ...db.models import User
from ...db.models.password_reset_tokens import PasswordResetToken
from ...db.session import async_session
from ...schemas import UserCreate, UserLogin, GoogleLoginRequest, ForgotPasswordRequest, ResetPasswordRequest

logger = logging.getLogger(__name__)
router = APIRouter()

GENERIC_LOGIN_ERROR = "Invalid email or password"
RESET_GENERIC_MESSAGE = "If this email exists, password reset instructions have been sent."


def _normalize_email(email: str | None) -> str:
    return (email or "").strip().lower()


def _token_hash(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def _expiry_delta(remember_me: bool) -> timedelta:
    if remember_me:
        return timedelta(days=int(getattr(settings, "remember_me_expire_days", 30) or 30))
    return timedelta(minutes=int(getattr(settings, "access_token_expire_minutes", 1440) or 1440))


def _create_access_token(user: User, remember_me: bool = False) -> str:
    expires_at = datetime.now(timezone.utc) + _expiry_delta(remember_me)
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role,
        "exp": expires_at,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def _user_response(user: User) -> dict:
    return {
        "id": str(user.id),
        "email": user.email,
        "role": user.role,
        "fullname": user.fullname,
        "avatar_url": getattr(user, "avatar_url", None),
        "auth_provider": getattr(user, "auth_provider", "local") or "local",
        "email_verified": bool(getattr(user, "email_verified", False)),
    }


async def _find_user_by_email(db, email: str) -> Optional[User]:
    stmt = select(User).where(text("LOWER(email) = :email")).params(email=_normalize_email(email))
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def _increment_failed_login(db, user: Optional[User]) -> None:
    if not user:
        return
    try:
        user.failed_login_count = int(getattr(user, "failed_login_count", 0) or 0) + 1
        await db.commit()
    except Exception as exc:
        await db.rollback()
        logger.warning(f"[AUTH] Failed login counter update skipped: {exc}")


async def _mark_login_success(db, user: User, provider: str) -> None:
    user.failed_login_count = 0
    user.last_login_at = datetime.now(timezone.utc)
    user.last_login_provider = provider
    await db.commit()
    await db.refresh(user)


async def _send_password_reset_email(email: str, reset_link: str) -> None:
    try:
        from app.services.email_service import send_email
        await send_email(
            to_email=email,
            subject="Reset your AlgoAgentX password",
            body=(
                "Use this link to reset your AlgoAgentX password. "
                "The link will expire soon.\n\n"
                f"{reset_link}"
            ),
        )
        return
    except Exception as exc:
        if getattr(settings, "smtp_enabled", False):
            logger.warning(f"[AUTH] Password reset email service skipped: {exc}")

    if not settings.is_production:
        logger.info(f"[AUTH DEV] Password reset link for {email}: {reset_link}")


@router.post("/login")
async def login(login_data: UserLogin, request: Request):
    try:
        email = _normalize_email(login_data.email)
        async with async_session() as db:
            user = await _find_user_by_email(db, email)
            if not user or not user.password_hash:
                await _increment_failed_login(db, user)
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=GENERIC_LOGIN_ERROR)

            try:
                password_valid = bcrypt.checkpw(
                    login_data.password.encode("utf-8"),
                    str(user.password_hash).strip().encode("utf-8"),
                )
            except Exception as exc:
                logger.warning(f"[AUTH] Password verification failed safely for {email}: {exc}")
                password_valid = False

            if not password_valid:
                await _increment_failed_login(db, user)
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=GENERIC_LOGIN_ERROR)

            await _mark_login_success(db, user, "local")
            token = _create_access_token(user, remember_me=bool(getattr(login_data, "remember_me", False)))

            try:
                from app.services.email_service import send_login_alert
                await send_login_alert(
                    db,
                    user,
                    request.client.host if request.client else None,
                    request.headers.get("user-agent"),
                )
            except Exception as email_exc:
                logger.warning(f"[AUTH] Login alert email skipped: {email_exc}")

            return {"access_token": token, "token_type": "bearer", "user": _user_response(user)}
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"[AUTH] Database error during login: {e}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")


@router.post("/signup")
async def signup(user_data: UserCreate):
    try:
        async with async_session() as db:
            email = _normalize_email(user_data.email)
            existing_user = await _find_user_by_email(db, email)
            if existing_user:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User with this email already exists")

            if user_data.mobile:
                result = await db.execute(select(User).where(User.mobile == user_data.mobile))
                if result.scalar_one_or_none():
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User with this mobile number already exists")

            hashed_password = bcrypt.hashpw(user_data.password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
            new_user = User(
                email=email,
                password_hash=hashed_password,
                role="user",
                fullname=user_data.fullname,
                mobile=user_data.mobile,
                auth_provider="local",
                email_verified=False,
            )
            db.add(new_user)
            await db.commit()
            await db.refresh(new_user)
            return {"message": "User created successfully", "user": _user_response(new_user)}
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"[AUTH] Database error during signup: {e}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")


@router.post("/google")
async def google_login(payload: GoogleLoginRequest):
    if not getattr(settings, "google_auth_enabled", False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Google login is disabled")
    if not getattr(settings, "google_client_id", ""):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Google OAuth is not configured")

    try:
        from google.auth.transport import requests as google_requests
        from google.oauth2 import id_token
    except Exception as exc:
        logger.error(f"[AUTH] google-auth dependency is missing: {exc}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Google OAuth dependency is not installed")

    try:
        info = id_token.verify_oauth2_token(payload.credential, google_requests.Request(), settings.google_client_id)
    except Exception as exc:
        logger.warning(f"[AUTH] Invalid Google credential: {exc}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Google credential")

    if info.get("aud") != settings.google_client_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Google audience")
    email = _normalize_email(info.get("email"))
    if not email or not info.get("email_verified"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Google email is not verified")

    allowed_domain = (getattr(settings, "google_allowed_email_domain", "") or "").strip().lower()
    if allowed_domain and not email.endswith("@" + allowed_domain.lstrip("@")):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Google login is not allowed for this email domain")

    google_sub = str(info.get("sub") or "")
    if not google_sub:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Google account")

    async with async_session() as db:
        result = await db.execute(select(User).where(User.google_sub == google_sub))
        user = result.scalar_one_or_none()
        if not user:
            user = await _find_user_by_email(db, email)

        if user and user.role == "admin" and not getattr(settings, "google_admin_login_enabled", False):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Google login is not enabled for admin accounts")

        if user:
            user.google_sub = user.google_sub or google_sub
            user.avatar_url = info.get("picture") or getattr(user, "avatar_url", None)
            user.email_verified = True
            if not user.auth_provider or user.auth_provider == "local":
                user.auth_provider = "google" if not user.password_hash else "local_google"
        else:
            user = User(
                email=email,
                password_hash=None,
                role="user",
                fullname=info.get("name") or email.split("@")[0],
                auth_provider="google",
                google_sub=google_sub,
                avatar_url=info.get("picture"),
                email_verified=True,
            )
            db.add(user)

        await _mark_login_success(db, user, "google")
        token = _create_access_token(user, remember_me=bool(getattr(payload, "remember_me", False)))
        return {"access_token": token, "token_type": "bearer", "user": _user_response(user)}


@router.get("/verify")
async def verify_token_route(current_user: dict = Depends(get_current_user)):
    return {"valid": True, "user": current_user}


@router.get("/me")
async def me(current_user: dict = Depends(get_current_user)):
    return {"user": current_user}


@router.post("/forgot-password")
async def forgot_password(body: ForgotPasswordRequest, request: Request):
    email = _normalize_email(body.email)
    async with async_session() as db:
        user = await _find_user_by_email(db, email)
        if user and user.password_hash:
            raw_token = secrets.token_urlsafe(32)
            expires_at = datetime.now(timezone.utc) + timedelta(minutes=int(getattr(settings, "password_reset_token_minutes", 30) or 30))
            reset_record = PasswordResetToken(
                user_id=user.id,
                token_hash=_token_hash(raw_token),
                expires_at=expires_at,
                request_ip=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
            )
            db.add(reset_record)
            await db.commit()
            frontend_url = (getattr(settings, "frontend_url", "http://localhost:3000") or "http://localhost:3000").rstrip("/")
            reset_link = f"{frontend_url}/auth/reset-password?token={raw_token}"
            await _send_password_reset_email(email, reset_link)
            response = {"message": RESET_GENERIC_MESSAGE}
            if not settings.is_production and not getattr(settings, "smtp_enabled", False):
                response["dev_reset_link"] = reset_link
            return response

    return {"message": RESET_GENERIC_MESSAGE}


@router.post("/reset-password")
async def reset_password(body: ResetPasswordRequest):
    raw_token = (body.token or "").strip()
    new_password = body.new_password or ""
    if not raw_token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token")
    if len(new_password) < 8:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password must be at least 8 characters")

    async with async_session() as db:
        now = datetime.now(timezone.utc)
        result = await db.execute(
            select(PasswordResetToken).where(
                PasswordResetToken.token_hash == _token_hash(raw_token),
                PasswordResetToken.used_at.is_(None),
                PasswordResetToken.expires_at > now,
            )
        )
        token_row = result.scalar_one_or_none()
        if not token_row:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token")

        result = await db.execute(select(User).where(User.id == token_row.user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token")

        user.password_hash = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        if user.auth_provider == "google":
            user.auth_provider = "local_google"
        token_row.used_at = now
        await db.execute(
            update(PasswordResetToken)
            .where(PasswordResetToken.user_id == user.id, PasswordResetToken.used_at.is_(None), PasswordResetToken.id != token_row.id)
            .values(used_at=now)
        )
        await db.commit()
        return {"message": "Password reset successful. You can now log in with your new password."}


# ============= DEV-ONLY DEBUG ENDPOINTS =============

@router.get("/debug/db")
async def debug_database():
    if settings.is_production:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Endpoint not found")
    async with async_session() as db:
        result = await db.execute(text("SELECT current_database()"))
        current_db = result.scalar_one_or_none()
        result = await db.execute(text("SELECT COUNT(*) FROM users"))
        user_count = result.scalar_one_or_none()
        result = await db.execute(text("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name='users'
            ORDER BY ordinal_position
        """))
        schema_info = result.fetchall()
        return {
            "environment": settings.env,
            "database": {"name": current_db, "host": settings.database_host, "port": settings.database_port, "url": settings.masked_database_url},
            "users_table": {"total_count": user_count, "schema": [{"column": r[0], "type": r[1], "nullable": r[2]} for r in schema_info]},
        }


@router.post("/debug/reset-password")
async def debug_reset_password(body: dict):
    if settings.is_production:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Endpoint not found")
    email = _normalize_email(body.get("email"))
    new_password = body.get("new_password") or ""
    if not email or len(new_password) < 8:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email and password of at least 8 characters are required")
    async with async_session() as db:
        user = await _find_user_by_email(db, email)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        user.password_hash = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        await db.commit()
        return {"success": True, "message": "Password reset successful", "note": "Development-only endpoint"}
