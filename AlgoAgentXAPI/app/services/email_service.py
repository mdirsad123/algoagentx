from __future__ import annotations

import asyncio
import html
import logging
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.compat import as_uuid_or_str
from app.db.models.users import User

logger = logging.getLogger(__name__)

DEFAULT_EMAIL_TYPES: dict[str, bool] = {
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

TYPE_TO_EMAIL_PREF: dict[str, str] = {
    "SUPPORT_TICKET_REPLY": "support_replies",
    "SUPPORT_TICKET_STATUS": "ticket_status_updates",
    "SUPPORT_TICKET": "support_new_ticket_admin",
    "SUPPORT_TICKET_USER_REPLY": "user_support_replies_admin",
    "BROKER_CONNECTED": "broker_alerts",
    "BROKER_CONNECT_FAILED": "broker_alerts",
    "BROKER_CONNECTION_FAILED": "broker_alerts",
    "LIVE_ORDER_EXECUTED": "trade_order_updates",
    "LIVE_ORDER_FAILED": "trade_order_updates",
    "LIVE_APPROVAL_REQUEST": "live_approval_requests",
    "PAYMENT_SUCCESS": "billing_payment_updates",
    "PAYMENT_FAILED": "billing_payment_updates",
    "PAYMENT_REFUND": "billing_payment_updates",
    "SUBSCRIPTION_ACTIVATED": "subscription_updates",
    "SUBSCRIPTION_EXPIRED": "subscription_updates",
    "CREDITS_ADDED": "credit_updates",
    "LOW_CREDIT_BALANCE": "credit_updates",
    "STRATEGY_REQUEST_APPROVED": "strategy_request_updates",
    "STRATEGY_REQUEST_REJECTED": "strategy_request_updates",
    "STRATEGY_REQUEST_CREATED": "new_strategy_request_admin",
    "BACKTEST_COMPLETED": "backtest_updates",
    "BACKTEST_FAILED": "backtest_updates",
    "LOGIN_ALERT": "login_alerts",
    "ADMIN_LOGIN_ALERT": "admin_login_alerts",
    "SYSTEM_CRITICAL": "system_critical_alerts_admin",
}


def _setting(name: str, default: Any = None) -> Any:
    return getattr(settings, name, default)


def is_email_enabled() -> bool:
    return bool(_setting("smtp_enabled", False))


def _smtp_username() -> str:
    return str(_setting("smtp_username", None) or _setting("smtp_email", "") or "")


def _smtp_password() -> str:
    return str(_setting("smtp_password", "") or "")


def _smtp_from_email() -> str:
    return str(_setting("smtp_from_email", None) or _smtp_username() or "")


def _smtp_from_name() -> str:
    return str(_setting("smtp_from_name", "AlgoAgentX") or "AlgoAgentX")


def smtp_status() -> dict[str, Any]:
    host = str(_setting("smtp_host", "") or "")
    username = _smtp_username()
    from_email = _smtp_from_email()
    password = _smtp_password()
    enabled = is_email_enabled()
    return {
        "smtp_enabled": enabled,
        "smtp_host_configured": bool(host),
        "smtp_username_configured": bool(username),
        "smtp_from_email": from_email,
        "ready": bool(enabled and host and username and password and from_email),
    }


def _masked(value: str) -> str:
    if not value:
        return ""
    if "@" in value:
        user, domain = value.split("@", 1)
        return f"{user[:2]}***@{domain}"
    return f"{value[:2]}***"


def build_notification_html(title: str, message: str, action_url: str | None = None, action_label: str = "Open in AlgoAgentX") -> str:
    safe_title = html.escape(title or "Notification")
    safe_message = html.escape(message or "").replace("\n", "<br />")
    safe_action = html.escape(action_url or "", quote=True)
    cta = ""
    if action_url:
        cta = f'<p style="margin:26px 0 8px;"><a href="{safe_action}" style="background:#8b5cf6;color:#fff;text-decoration:none;padding:12px 18px;border-radius:12px;font-weight:700;display:inline-block;">{html.escape(action_label)}</a></p>'
    timestamp = datetime.utcnow().strftime("%d %b %Y, %H:%M UTC")
    return f"""
    <!doctype html><html><body style="margin:0;background:#f5f3ff;font-family:Arial,Helvetica,sans-serif;color:#20143a;">
      <div style="max-width:640px;margin:0 auto;padding:28px 16px;">
        <div style="background:linear-gradient(135deg,#4c1d95,#7c3aed,#2563eb);color:#fff;padding:22px 24px;border-radius:20px 20px 0 0;">
          <div style="font-size:22px;font-weight:800;">AlgoAgentX</div>
          <div style="opacity:.85;font-size:13px;margin-top:4px;">Trading workspace notification</div>
        </div>
        <div style="background:#fff;border:1px solid #e9d5ff;border-top:0;padding:26px 24px;border-radius:0 0 20px 20px;box-shadow:0 18px 45px rgba(76,29,149,.12);">
          <h1 style="margin:0 0 12px;font-size:22px;line-height:1.3;color:#2e1065;">{safe_title}</h1>
          <p style="margin:0;color:#4c3b6f;line-height:1.7;font-size:15px;">{safe_message}</p>
          {cta}
          <p style="margin-top:24px;color:#7c6f99;font-size:12px;">Sent at {timestamp}</p>
          <hr style="border:0;border-top:1px solid #ede9fe;margin:22px 0;" />
          <p style="margin:0;color:#8b7aa8;font-size:12px;line-height:1.6;">This email was sent because notifications are enabled for your AlgoAgentX account. You can change email notification preferences from Settings.</p>
        </div>
      </div>
    </body></html>
    """


def _send_sync(to_email: str, subject: str, html_body: str, text_body: str | None = None) -> bool:
    status = smtp_status()
    if not status["ready"]:
        logger.info("SMTP disabled/not ready; skipping email to %s", to_email)
        return False
    if not to_email:
        return False
    host = str(_setting("smtp_host", "") or "")
    port = int(_setting("smtp_port", 587) or 587)
    username = _smtp_username()
    password = _smtp_password()
    from_email = _smtp_from_email()
    from_name = _smtp_from_name()
    timeout = int(_setting("smtp_timeout_seconds", 10) or 10)
    use_tls = bool(_setting("smtp_use_tls", True))
    use_ssl = bool(_setting("smtp_use_ssl", False))

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{from_name} <{from_email}>"
    msg["To"] = to_email
    msg.attach(MIMEText(text_body or html.unescape(html_body.replace("<br />", "\n")), "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    if use_ssl:
        server_ctx = smtplib.SMTP_SSL(host, port, timeout=timeout)
    else:
        server_ctx = smtplib.SMTP(host, port, timeout=timeout)
    with server_ctx as server:
        if use_tls and not use_ssl:
            server.starttls()
        if username and password:
            server.login(username, password)
        server.sendmail(from_email, [to_email], msg.as_string())
    return True


async def send_email(to_email: str, subject: str, html_body: str, text_body: str | None = None) -> bool:
    if not to_email or not is_email_enabled():
        return False
    try:
        return await asyncio.to_thread(_send_sync, to_email, subject, html_body, text_body)
    except Exception as exc:
        logger.warning("Email send failed to %s: %s", to_email, exc)
        return False


async def _get_preferences(db: AsyncSession, user_id: str) -> dict[str, Any]:
    try:
        row = (await db.execute(
            text("SELECT notifications FROM user_settings WHERE CAST(user_id AS TEXT)=:user_id LIMIT 1"),
            {"user_id": str(user_id)},
        )).mappings().first()
        return dict(row["notifications"] or {}) if row else {}
    except Exception as exc:
        logger.debug("Could not read email preferences for %s: %s", user_id, exc)
        return {}


def _email_allowed(preferences: dict[str, Any], notification_type: str, role: str = "user") -> bool:
    master = preferences.get("email_notifications_enabled", True)
    if master is False:
        return False
    email_types = preferences.get("email_notification_types")
    if not isinstance(email_types, dict):
        email_types = {}
    key = TYPE_TO_EMAIL_PREF.get(str(notification_type).upper(), "")
    if key:
        return bool(email_types.get(key, DEFAULT_EMAIL_TYPES.get(key, True)))
    # Unknown notification types are email-off by default to avoid noisy surprises.
    return False


async def send_notification_email(db: AsyncSession, user_id: str, notification: Any) -> bool:
    if not is_email_enabled() or not user_id or notification is None:
        return False
    try:
        user = (await db.execute(select(User).where(User.id == as_uuid_or_str(str(user_id))))).scalar_one_or_none()
        if not user or not getattr(user, "email", None):
            return False
        preferences = await _get_preferences(db, str(user.id))
        if not _email_allowed(preferences, str(getattr(notification, "type", "")), str(getattr(user, "role", "user") or "user")):
            return False
        action_url = getattr(notification, "action_url", None)
        html_body = build_notification_html(getattr(notification, "title", "Notification"), getattr(notification, "message", ""), action_url)
        return await send_email(user.email, f"AlgoAgentX: {getattr(notification, 'title', 'Notification')}", html_body)
    except Exception as exc:
        logger.warning("Notification email skipped for user %s: %s", user_id, exc)
        return False


async def send_login_alert(db: AsyncSession, user: User, ip_address: str | None, user_agent: str | None) -> bool:
    if not user or not getattr(user, "email", None) or not is_email_enabled():
        return False
    notification_type = "ADMIN_LOGIN_ALERT" if str(getattr(user, "role", "user") or "user").lower() == "admin" else "LOGIN_ALERT"
    preferences = await _get_preferences(db, str(user.id))
    if not _email_allowed(preferences, notification_type, str(getattr(user, "role", "user") or "user")):
        return False
    now = datetime.utcnow().strftime("%d %b %Y, %H:%M UTC")
    message = (
        f"A new login happened on your AlgoAgentX account.\n\n"
        f"Login time: {now}\nRole: {getattr(user, 'role', 'user')}\nIP address: {ip_address or 'Not available'}\nBrowser: {user_agent or 'Not available'}\n\n"
        "If this was not you, change your password immediately."
    )
    html_body = build_notification_html("New login to your AlgoAgentX account", message, None)
    return await send_email(user.email, "New login to your AlgoAgentX account", html_body, message)


async def send_admin_login_otp_email(
    email: str,
    otp: str,
    expires_minutes: int,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> bool:
    """Send the admin login OTP email. Plain OTP is never stored; this helper only receives it for delivery."""
    message = (
        "Use the following 6-digit OTP to complete your AlgoAgentX admin login.\n\n"
        f"OTP: {otp}\n"
        f"This OTP expires in {expires_minutes} minutes.\n"
        f"IP address: {ip_address or 'Not available'}\n"
        f"Browser: {user_agent or 'Not available'}\n\n"
        "If you did not request this login, change your password immediately and review your admin account security."
    )
    safe_otp = html.escape(str(otp))
    safe_minutes = html.escape(str(expires_minutes))
    safe_ip = html.escape(ip_address or "Not available")
    safe_agent = html.escape(user_agent or "Not available")
    html_body = f"""
    <!doctype html><html><body style="margin:0;background:#f5f3ff;font-family:Arial,Helvetica,sans-serif;color:#20143a;">
      <div style="max-width:640px;margin:0 auto;padding:28px 16px;">
        <div style="background:linear-gradient(135deg,#4c1d95,#7c3aed,#2563eb);color:#fff;padding:22px 24px;border-radius:20px 20px 0 0;">
          <div style="font-size:22px;font-weight:800;">AlgoAgentX</div>
          <div style="opacity:.85;font-size:13px;margin-top:4px;">Admin login verification</div>
        </div>
        <div style="background:#fff;border:1px solid #e9d5ff;border-top:0;padding:26px 24px;border-radius:0 0 20px 20px;box-shadow:0 18px 45px rgba(76,29,149,.12);">
          <h1 style="margin:0 0 12px;font-size:22px;line-height:1.3;color:#2e1065;">AlgoAgentX Admin Login OTP</h1>
          <p style="margin:0 0 18px;color:#4c3b6f;line-height:1.7;font-size:15px;">Use this 6-digit code to complete your admin login. It expires in {safe_minutes} minutes.</p>
          <div style="font-size:34px;letter-spacing:8px;font-weight:800;color:#4c1d95;background:#f5f3ff;border:1px solid #ddd6fe;border-radius:16px;padding:18px;text-align:center;">{safe_otp}</div>
          <p style="margin:18px 0 0;color:#4c3b6f;line-height:1.7;font-size:14px;"><strong>IP:</strong> {safe_ip}<br /><strong>Browser:</strong> {safe_agent}</p>
          <p style="margin:18px 0 0;color:#991b1b;line-height:1.6;font-size:13px;">If you did not request this login, change your password immediately and review your admin account security.</p>
        </div>
      </div>
    </body></html>
    """
    sent = await send_email(email, "AlgoAgentX Admin Login OTP", html_body, message)
    if not sent and not settings.is_production:
        logger.info("[AUTH DEV] Admin login OTP for %s: %s", email, otp)
    return sent


# Backward-compatible class API used by older modules.
class EmailService:
    async def send_email(self, to_email: str, subject: str, body: str, is_html: bool = False) -> bool:
        return await send_email(to_email, subject, body if is_html else f"<pre>{html.escape(body)}</pre>", None if is_html else body)

    async def send_to_admins(self, subject: str, body: str, is_html: bool = False) -> bool:
        emails = [e.strip() for e in str(_setting("admin_notify_emails", "") or "").split(",") if e.strip()]
        results = [await self.send_email(email, subject, body, is_html) for email in emails]
        return any(results)

    async def send_strategy_request_notification(self, user_email: str, user_name: str, request_title: str) -> bool:
        return await self.send_to_admins("New Strategy Request Submitted", f"New strategy request: {request_title}\nSubmitted by: {user_name} ({user_email})")

    async def send_strategy_deployed_notification(self, user_email: str, user_name: str, strategy_title: str) -> bool:
        return await self.send_email(user_email, "Your Strategy Has Been Deployed", f"Your strategy {strategy_title} has been deployed.")


email_service = EmailService()
