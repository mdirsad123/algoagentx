from __future__ import annotations

import os
from typing import Any, Optional


class LiveNotificationService:
    """Skeleton notification service for future email, Telegram, and webhook alerts.

    Integrations are no-op unless environment variables are configured.
    """

    async def send_email(self, subject: str, message: str, to_email: Optional[str] = None, metadata: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        if not (os.getenv("SMTP_HOST") and (to_email or os.getenv("ALERT_EMAIL_TO"))):
            return {"sent": False, "channel": "email", "reason": "SMTP/recipient not configured"}
        return {"sent": False, "channel": "email", "reason": "Email provider adapter not wired yet"}

    async def send_telegram(self, message: str, metadata: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        if not (os.getenv("TELEGRAM_BOT_TOKEN") and os.getenv("TELEGRAM_CHAT_ID")):
            return {"sent": False, "channel": "telegram", "reason": "Telegram env not configured"}
        return {"sent": False, "channel": "telegram", "reason": "Telegram provider adapter not wired yet"}

    async def send_webhook(self, event: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not os.getenv("LIVE_ALERT_WEBHOOK_URL"):
            return {"sent": False, "channel": "webhook", "reason": "Webhook env not configured"}
        return {"sent": False, "channel": "webhook", "reason": "Webhook provider adapter not wired yet"}


notification_service = LiveNotificationService()
