from datetime import datetime, timedelta, timezone
import uuid
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
from ...db.models import User, AdminLoginOtp
from ...db.models.password_reset_tokens import PasswordResetToken
from ...db.session import async_session
from ...schemas import UserCreate, UserLogin, GoogleLoginRequest, ForgotPasswordRequest, ResetPasswordRequest, AdminOtpVerifyRequest, AdminOtpResendRequest

logger = logging.getLogger(__name__)
router = APIRouter()

GENERIC_LOGIN_ERROR = "Invalid email or password"
RESET_GENERIC_MESSAGE = "If this email exists, password reset instructions have been sent."

GENERIC_OTP_ERROR = "Invalid or expired OTP session"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip() or None
    return request.client.host if request.client else None


def _otp_hash(otp: str, session_id: str) -> str:
    raw = f"{str(otp).strip()}:{str(session_id)}:{settings.jwt_secret_key}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _generate_otp() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def _as_aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


async def _create_admin_otp_session(db, user: User, request: Request) -> AdminLoginOtp:
    now = _utcnow()
    session_id = uuid.uuid4()
    otp = _generate_otp()
    expires_minutes = int(getattr(settings, "admin_otp_expire_minutes", 10) or 10)
    cooldown_seconds = int(getattr(settings, "admin_otp_resend_cooldown_seconds", 60) or 60)
    max_attempts = int(getattr(settings, "admin_otp_max_attempts", 5) or 5)
    otp_row = AdminLoginOtp(
        id=session_id,
        user_id=user.id,
        email=user.email,
        otp_hash=_otp_hash(otp, str(session_id)),
        max_attempts=max_attempts,
        expires_at=now + timedelta(minutes=expires_minutes),
        resend_available_at=now + timedelta(seconds=cooldown_seconds),
        last_sent_at=now,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    db.add(otp_row)
    await db.commit()
    await db.refresh(otp_row)

    try:
        from app.services.email_service import send_admin_login_otp_email
        await send_admin_login_otp_email(
            user.email,
            otp,
            expires_minutes,
            _client_ip(request),
            request.headers.get("user-agent"),
        )
    except Exception as exc:
        logger.warning("[AUTH] Admin OTP email send skipped for %s: %s", user.email, exc)
        if not settings.is_production:
            logger.info("[AUTH DEV] Admin login OTP generated for %s (last2=%s)", user.email, otp[-2:])

    logger.info("[AUTH] Admin password verified; OTP session created for user_id=%s", user.id)
    return otp_row


async def _load_admin_otp_session(db, raw_session_id: str) -> AdminLoginOtp | None:
    try:
        session_uuid = uuid.UUID(str(raw_session_id))
    except Exception:
        return None
    result = await db.execute(select(AdminLoginOtp).where(AdminLoginOtp.id == session_uuid))
    return result.scalar_one_or_none()


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

            if str(getattr(user, "role", "user") or "user").lower() == "admin" and bool(getattr(settings, "admin_otp_enabled", True)):
                otp_row = await _create_admin_otp_session(db, user, request)
                return {
                    "requires_otp": True,
                    "otp_session_id": str(otp_row.id),
                    "message": "OTP sent to admin email",
                }

            await _mark_login_success(db, user, "local")
            token = _create_access_token(user, remember_me=bool(getattr(login_data, "remember_me", False)))

            try:
                from app.services.email_service import send_login_alert
                await send_login_alert(
                    db,
                    user,
                    _client_ip(request),
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


@router.post("/admin/verify-otp")
async def verify_admin_otp(body: AdminOtpVerifyRequest, request: Request):
    otp = str(body.otp or "").strip()
    if not otp.isdigit() or len(otp) != 6:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=GENERIC_OTP_ERROR)

    async with async_session() as db:
        otp_row = await _load_admin_otp_session(db, body.otp_session_id)
        now = _utcnow()
        if not otp_row or otp_row.used_at is not None:
            logger.warning("[AUTH] Admin OTP verify failed: missing/used session")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=GENERIC_OTP_ERROR)

        if _as_aware(otp_row.expires_at) <= now:
            otp_row.used_at = now
            await db.commit()
            logger.warning("[AUTH] Admin OTP expired for email=%s", otp_row.email)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=GENERIC_OTP_ERROR)

        if int(otp_row.attempts or 0) >= int(otp_row.max_attempts or 5):
            otp_row.used_at = now
            await db.commit()
            logger.warning("[AUTH] Admin OTP max attempts already reached for email=%s", otp_row.email)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=GENERIC_OTP_ERROR)

        expected_hash = otp_row.otp_hash or ""
        supplied_hash = _otp_hash(otp, str(otp_row.id))
        if not secrets.compare_digest(expected_hash, supplied_hash):
            otp_row.attempts = int(otp_row.attempts or 0) + 1
            if otp_row.attempts >= int(otp_row.max_attempts or 5):
                otp_row.used_at = now
                logger.warning("[AUTH] Admin OTP max attempts reached for email=%s", otp_row.email)
            else:
                logger.warning("[AUTH] Admin OTP verify failed for email=%s attempt=%s", otp_row.email, otp_row.attempts)
            await db.commit()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=GENERIC_OTP_ERROR)

        result = await db.execute(select(User).where(User.id == otp_row.user_id))
        user = result.scalar_one_or_none()
        if not user or str(getattr(user, "role", "user") or "user").lower() != "admin":
            otp_row.used_at = now
            await db.commit()
            logger.warning("[AUTH] Admin OTP session has invalid user for email=%s", otp_row.email)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=GENERIC_OTP_ERROR)

        otp_row.used_at = now
        await _mark_login_success(db, user, "local_otp")
        token = _create_access_token(user, remember_me=bool(body.remember_me))

        try:
            from app.services.email_service import send_login_alert
            await send_login_alert(db, user, _client_ip(request), request.headers.get("user-agent"))
        except Exception as email_exc:
            logger.warning(f"[AUTH] Admin login alert email skipped: {email_exc}")

        logger.info("[AUTH] Admin OTP verified successfully for user_id=%s", user.id)
        return {"access_token": token, "token_type": "bearer", "user": _user_response(user)}


@router.post("/admin/resend-otp")
async def resend_admin_otp(body: AdminOtpResendRequest, request: Request):
    async with async_session() as db:
        otp_row = await _load_admin_otp_session(db, body.otp_session_id)
        now = _utcnow()
        if not otp_row or otp_row.used_at is not None or _as_aware(otp_row.expires_at) <= now:
            logger.warning("[AUTH] Admin OTP resend failed: invalid session")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=GENERIC_OTP_ERROR)

        resend_available_at = _as_aware(otp_row.resend_available_at)
        if resend_available_at and resend_available_at > now:
            remaining = max(1, int((resend_available_at - now).total_seconds()))
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=f"Please wait {remaining} seconds before requesting a new OTP")

        result = await db.execute(select(User).where(User.id == otp_row.user_id))
        user = result.scalar_one_or_none()
        if not user or str(getattr(user, "role", "user") or "user").lower() != "admin":
            otp_row.used_at = now
            await db.commit()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=GENERIC_OTP_ERROR)

        otp = _generate_otp()
        expires_minutes = int(getattr(settings, "admin_otp_expire_minutes", 10) or 10)
        cooldown_seconds = int(getattr(settings, "admin_otp_resend_cooldown_seconds", 60) or 60)
        otp_row.otp_hash = _otp_hash(otp, str(otp_row.id))
        otp_row.attempts = 0
        otp_row.expires_at = now + timedelta(minutes=expires_minutes)
        otp_row.last_sent_at = now
        otp_row.resend_available_at = now + timedelta(seconds=cooldown_seconds)
        otp_row.ip_address = _client_ip(request)
        otp_row.user_agent = request.headers.get("user-agent")
        await db.commit()

        try:
            from app.services.email_service import send_admin_login_otp_email
            await send_admin_login_otp_email(user.email, otp, expires_minutes, _client_ip(request), request.headers.get("user-agent"))
        except Exception as exc:
            logger.warning("[AUTH] Admin OTP resend email skipped for %s: %s", user.email, exc)
            if not settings.is_production:
                logger.info("[AUTH DEV] Resent admin login OTP generated for %s (last2=%s)", user.email, otp[-2:])

        logger.info("[AUTH] Admin OTP resent for user_id=%s", user.id)
        return {"message": "OTP sent to admin email", "resend_cooldown_seconds": cooldown_seconds}


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
