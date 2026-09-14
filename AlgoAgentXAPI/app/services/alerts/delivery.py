from __future__ import annotations

from datetime import datetime, timedelta, timezone
import logging

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload

from ...core.config import settings
from ...db.models import AlertEvent, NotificationDelivery, PriceAlert
from .telegram import build_alert_message, resolve_chat_id, send_telegram
from .whatsapp import build_template_dispatch, build_whatsapp_message, resolve_whatsapp_recipient, send_whatsapp

# Attempt 1 is immediate. Confirmed temporary provider/API failures retry after
# 5s and then 20s. There is no unbounded retry loop.
RETRY_DELAYS = [0, 5, 20]
MAX_ATTEMPTS = len(RETRY_DELAYS)
SUPPORTED_CHANNELS = {"TELEGRAM", "WHATSAPP"}

logger = logging.getLogger(__name__)


def _event_status_attr(channel: str) -> str:
    return "telegram_status" if channel == "TELEGRAM" else "whatsapp_status"


def _channel_timeout_seconds(channel: str) -> int:
    if channel == "WHATSAPP":
        return max(10, int(getattr(settings, "twilio_timeout_seconds", 10) or 10) + 5)
    return max(10, int(getattr(settings, "telegram_timeout_seconds", 10) or 10) + 5)


def _is_primary_timing_channel(channel: str, alert: PriceAlert) -> bool:
    # Existing AlertEvent timing columns are channel-neutral legacy fields. Keep
    # Telegram as the primary timing metric when both channels are enabled. If
    # WhatsApp is the only enabled channel, it owns those timing fields.
    return channel == "TELEGRAM" or not bool(alert.telegram_enabled)


async def _mark_stale_sending_ambiguous(db: AsyncSession, now: datetime) -> None:
    """Resolve interrupted sends without risking duplicate messages.

    Telegram and Twilio message creation do not expose a caller-supplied
    idempotency key. If a worker dies after a request may have reached the
    provider but before the response is recorded, replaying can duplicate an
    alert. Stale SENDING rows are therefore surfaced as AMBIGUOUS.
    """
    for channel in SUPPORTED_CHANNELS:
        cutoff = now - timedelta(seconds=_channel_timeout_seconds(channel))
        stale = (await db.execute(
            select(NotificationDelivery)
            .options(noload("*"))
            .where(
                NotificationDelivery.channel == channel,
                NotificationDelivery.status == "SENDING",
                NotificationDelivery.requested_at.is_not(None),
                NotificationDelivery.requested_at <= cutoff,
            )
            .with_for_update(of=NotificationDelivery, skip_locked=True)
        )).scalars().all()
        for delivery in stale:
            delivery.status = "AMBIGUOUS"
            delivery.completed_at = now
            delivery.next_attempt_at = None
            delivery.error = (
                f"Previous {channel.title()} dispatch was interrupted after sending began. "
                "It was not retried automatically to avoid a duplicate notification."
            )
            logger.error(
                "Alert delivery became ambiguous | channel=%s | delivery_id=%s | event_id=%s",
                channel,
                delivery.id,
                delivery.alert_event_id,
            )
            event = (await db.execute(
                select(AlertEvent).where(AlertEvent.id == delivery.alert_event_id)
            )).scalar_one_or_none()
            if event:
                setattr(event, _event_status_attr(channel), "AMBIGUOUS")
                alert = (await db.execute(
                    select(PriceAlert).where(PriceAlert.id == event.alert_id)
                )).scalar_one_or_none()
                if alert and _is_primary_timing_channel(channel, alert):
                    event.notification_response_at = now


async def _dispatch_channel(db: AsyncSession, channel: str, event: AlertEvent, alert: PriceAlert):
    if channel == "TELEGRAM":
        recipient, _ = await resolve_chat_id(db, str(event.user_id))
        if not recipient:
            return None, "No Telegram chat configured for this user and TELEGRAM_DEFAULT_CHAT_ID is empty", False
        result = await send_telegram(recipient, build_alert_message(event, alert))
        return result, result.error, True

    if channel == "WHATSAPP":
        recipient, _ = await resolve_whatsapp_recipient(db, str(event.user_id))
        if not recipient:
            return None, "No WhatsApp number configured for this user and TWILIO_TO_WHATSAPP_NUMBER is empty", False
        template = build_template_dispatch(event, alert)
        result = await send_whatsapp(
            recipient,
            build_whatsapp_message(event, alert),
            content_sid=template.content_sid,
            content_variables=template.variables,
        )
        return result, result.error, True

    return None, f"Unsupported notification channel: {channel}", False


async def process_due_deliveries(db: AsyncSession, limit: int = 50) -> int:
    now = datetime.now(timezone.utc)
    await _mark_stale_sending_ambiguous(db, now)
    await db.commit()

    delivery_ids = (await db.execute(
        select(NotificationDelivery.id)
        .where(
            NotificationDelivery.channel.in_(sorted(SUPPORTED_CHANNELS)),
            NotificationDelivery.status.in_(["PENDING", "RETRYING"]),
            or_(NotificationDelivery.next_attempt_at.is_(None), NotificationDelivery.next_attempt_at <= now),
        )
        .order_by(NotificationDelivery.created_at.asc())
        .limit(limit)
    )).scalars().all()

    processed = 0
    for delivery_id in delivery_ids:
        delivery = (await db.execute(
            select(NotificationDelivery)
            .options(noload("*"))
            .where(
                NotificationDelivery.id == delivery_id,
                NotificationDelivery.status.in_(["PENDING", "RETRYING"]),
            )
            .with_for_update(of=NotificationDelivery, skip_locked=True)
        )).scalar_one_or_none()
        if delivery is None:
            continue

        channel = str(delivery.channel or "").upper()
        event = (await db.execute(
            select(AlertEvent).where(AlertEvent.id == delivery.alert_event_id)
        )).scalar_one_or_none()
        if event is None:
            delivery.status = "FAILED"
            delivery.error = "Alert event no longer exists"
            delivery.completed_at = datetime.now(timezone.utc)
            logger.error("Alert delivery failed | channel=%s | delivery_id=%s | reason=%s", channel, delivery.id, delivery.error)
            await db.commit()
            continue

        alert = (await db.execute(
            select(PriceAlert).where(PriceAlert.id == event.alert_id)
        )).scalar_one_or_none()
        if alert is None:
            delivery.status = "FAILED"
            delivery.error = "Alert no longer exists"
            delivery.completed_at = datetime.now(timezone.utc)
            setattr(event, _event_status_attr(channel), "FAILED")
            logger.error("Alert delivery failed | channel=%s | delivery_id=%s | reason=%s", channel, delivery.id, delivery.error)
            await db.commit()
            continue

        delivery.attempt = int(delivery.attempt or 0) + 1
        delivery.requested_at = datetime.now(timezone.utc)
        delivery.status = "SENDING"
        delivery.next_attempt_at = None
        setattr(event, _event_status_attr(channel), "SENDING")
        if _is_primary_timing_channel(channel, alert):
            # Means provider API request started, not handset delivery.
            event.notification_sent_at = delivery.requested_at
        await db.commit()

        result, error, recipient_present = await _dispatch_channel(db, channel, event, alert)
        completed = datetime.now(timezone.utc)

        delivery = (await db.execute(
            select(NotificationDelivery)
            .options(noload("*"))
            .where(NotificationDelivery.id == delivery_id)
            .with_for_update(of=NotificationDelivery)
        )).scalar_one_or_none()
        event = (await db.execute(
            select(AlertEvent).where(AlertEvent.id == event.id)
        )).scalar_one_or_none()
        if delivery is None or event is None:
            await db.rollback()
            continue

        alert = (await db.execute(
            select(PriceAlert).where(PriceAlert.id == event.alert_id)
        )).scalar_one_or_none()
        if alert is None:
            delivery.status = "FAILED"
            delivery.error = "Alert no longer exists"
            delivery.completed_at = completed
            setattr(event, _event_status_attr(channel), "FAILED")
            await db.commit()
            continue

        delivery.completed_at = completed
        primary_timing = _is_primary_timing_channel(channel, alert)
        if result and result.ok:
            delivery.status = "SENT"
            delivery.response_code = result.status_code
            delivery.provider_message_id = result.message_id
            delivery.response_payload = result.response
            delivery.error = None
            delivery.next_attempt_at = None
            setattr(event, _event_status_attr(channel), "SENT")
            if primary_timing:
                event.notification_response_at = completed
                event.notification_api_latency_ms = max(0, int((completed - delivery.requested_at).total_seconds() * 1000))
                event.total_internal_latency_ms = max(0, int((completed - event.server_received_at).total_seconds() * 1000))
        else:
            provider_name = "Telegram" if channel == "TELEGRAM" else "Twilio WhatsApp"
            delivery.error = error or f"Unknown {provider_name} delivery error"
            delivery.response_code = result.status_code if result else None
            delivery.response_payload = result.response if result else None
            if primary_timing:
                event.notification_response_at = completed
                if recipient_present and delivery.requested_at:
                    event.notification_api_latency_ms = max(0, int((completed - delivery.requested_at).total_seconds() * 1000))
                event.total_internal_latency_ms = max(0, int((completed - event.server_received_at).total_seconds() * 1000))

            if result and result.ambiguous:
                delivery.status = "AMBIGUOUS"
                delivery.next_attempt_at = None
                setattr(event, _event_status_attr(channel), "AMBIGUOUS")
            elif result and result.retryable and delivery.attempt < MAX_ATTEMPTS:
                delivery.status = "RETRYING"
                delay = RETRY_DELAYS[min(delivery.attempt, len(RETRY_DELAYS) - 1)]
                delivery.next_attempt_at = completed + timedelta(seconds=delay)
                setattr(event, _event_status_attr(channel), "RETRYING")
            else:
                delivery.status = "FAILED"
                delivery.next_attempt_at = None
                setattr(event, _event_status_attr(channel), "FAILED")

            logger.error(
                "Alert delivery failed | channel=%s | delivery_id=%s | event_id=%s | status=%s | attempt=%s | error=%s",
                channel,
                delivery.id,
                event.id,
                delivery.status,
                delivery.attempt,
                delivery.error,
            )

        await db.commit()
        processed += 1
    return processed
