from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

import aiohttp
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import settings
from ...db.models import UserNotificationChannel

IST = ZoneInfo("Asia/Kolkata")


@dataclass
class TelegramSendResult:
    ok: bool
    status_code: int | None
    message_id: str | None
    response: dict
    error: str | None = None
    # retryable=True only when Telegram explicitly rejected the request temporarily,
    # or the connection could not be established. Ambiguous failures are never
    # retried automatically because Telegram sendMessage has no idempotency key.
    retryable: bool = False
    ambiguous: bool = False


def telegram_configured() -> bool:
    return bool(str(getattr(settings, "telegram_bot_token", "") or "").strip())


async def resolve_chat_id(db: AsyncSession, user_id: str, explicit: str | None = None) -> tuple[str | None, bool]:
    if explicit:
        return str(explicit).strip(), False
    channel = (await db.execute(
        select(UserNotificationChannel).where(
            UserNotificationChannel.user_id == user_id,
            UserNotificationChannel.channel == "TELEGRAM",
            UserNotificationChannel.enabled.is_(True),
        )
    )).scalar_one_or_none()
    if channel and channel.external_recipient_id:
        return str(channel.external_recipient_id), False
    fallback = str(getattr(settings, "telegram_default_chat_id", "") or "").strip()
    return (fallback or None), bool(fallback)


def _money(value: Decimal | float | str | None) -> str:
    try:
        return f"{Decimal(str(value)):.2f}"
    except Exception:
        return str(value or "—")


def build_alert_message(event, alert) -> str:
    ts = (event.condition_detected_at or datetime.now(tz=IST)).astimezone(IST)
    condition = str(event.condition_type or "").replace("_", " ").title()
    event_id = f"AAX-{str(event.id).split('-')[0].upper()}"
    snapshot = ((event.payload or {}).get("alert_snapshot") or {}) if isinstance(event.payload, dict) else {}
    alert_type = str(snapshot.get("alert_type") or alert.alert_type or "").upper()
    target_price = snapshot.get("target_price", alert.target_price)
    zone_low = snapshot.get("zone_low", alert.zone_low)
    zone_high = snapshot.get("zone_high", alert.zone_high)
    if alert_type in {"ENTERING_ZONE", "LEAVING_ZONE"}:
        verb = "entered" if alert_type == "ENTERING_ZONE" else "left"
        return (
            "🔴 AlgoAgentX Zone Alert\n\n"
            f"{event.symbol} {verb} configured zone\n\n"
            f"Zone: {_money(zone_low)} - {_money(zone_high)}\n"
            f"Current: {_money(event.trigger_price)}\n\n"
            f"Condition: {condition}\n"
            f"Triggered: {ts.strftime('%d-%b-%Y %I:%M:%S %p')} IST\n"
            f"Alert ID: {event_id}"
        )
    return (
        "🔔 AlgoAgentX Price Alert\n\n"
        f"{event.symbol}\n\n"
        f"Target: {_money(target_price)}\n"
        f"Current: {_money(event.trigger_price)}\n\n"
        f"Condition: {condition}\n"
        f"Triggered: {ts.strftime('%d-%b-%Y %I:%M:%S %p')} IST\n"
        f"Alert ID: {event_id}"
    )


async def send_telegram(chat_id: str, text: str) -> TelegramSendResult:
    token = str(getattr(settings, "telegram_bot_token", "") or "").strip()
    if not token:
        return TelegramSendResult(False, None, None, {}, "TELEGRAM_BOT_TOKEN is not configured")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    timeout = aiohttp.ClientTimeout(total=float(getattr(settings, "telegram_timeout_seconds", 10) or 10))
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, json={"chat_id": chat_id, "text": text, "disable_web_page_preview": True}) as response:
                payload = await response.json(content_type=None)
                ok = bool(response.status == 200 and payload.get("ok"))
                result = payload.get("result") or {}
                temporary_rejection = response.status == 429 or response.status >= 500
                return TelegramSendResult(
                    ok=ok,
                    status_code=response.status,
                    message_id=str(result.get("message_id")) if result.get("message_id") is not None else None,
                    response=payload,
                    error=None if ok else str(payload.get("description") or f"Telegram HTTP {response.status}"),
                    retryable=bool(not ok and temporary_rejection),
                    ambiguous=False,
                )
    except aiohttp.ClientConnectorError as exc:
        # The connection was not established, so Telegram could not accept the message.
        return TelegramSendResult(False, None, None, {}, str(exc), retryable=True, ambiguous=False)
    except (asyncio.TimeoutError, aiohttp.ServerTimeoutError, aiohttp.ClientPayloadError, aiohttp.ClientConnectionError) as exc:
        # The request may already have reached Telegram. Retrying sendMessage here can
        # create a duplicate because Bot API has no caller-supplied idempotency key.
        return TelegramSendResult(False, None, None, {}, str(exc), retryable=False, ambiguous=True)
    except Exception as exc:
        return TelegramSendResult(False, None, None, {}, str(exc), retryable=False, ambiguous=True)
