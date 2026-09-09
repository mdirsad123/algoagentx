from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload

from ...core.config import settings
from ...db.models import AlertEvent, NotificationDelivery, PriceAlert
from .telegram import build_alert_message, resolve_chat_id, send_telegram

# Attempt 1 is immediate. Confirmed temporary Telegram/API failures retry after
# 5s and then 20s. There is no unbounded retry loop.
RETRY_DELAYS = [0, 5, 20]
MAX_ATTEMPTS = len(RETRY_DELAYS)


async def _mark_stale_sending_ambiguous(db: AsyncSession, now: datetime) -> None:
    """Resolve interrupted sends without risking a duplicate Telegram message.

    A worker can stop after Telegram accepts sendMessage but before the DB records
    the response. Telegram Bot API does not support an idempotency key for
    sendMessage, so blindly replaying such an attempt can duplicate a notification.
    We therefore surface stale SENDING attempts as AMBIGUOUS for manual visibility.
    """
    timeout_seconds = max(10, int(getattr(settings, "telegram_timeout_seconds", 10) or 10) + 5)
    cutoff = now - timedelta(seconds=timeout_seconds)
    stale = (await db.execute(
        select(NotificationDelivery)
        .options(noload("*"))
        .where(
            NotificationDelivery.channel == "TELEGRAM",
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
            "Previous Telegram dispatch was interrupted after sending began. "
            "It was not retried automatically to avoid a duplicate notification."
        )
        event = (await db.execute(select(AlertEvent).where(AlertEvent.id == delivery.alert_event_id))).scalar_one_or_none()
        if event:
            event.telegram_status = "AMBIGUOUS"
            event.notification_response_at = now


async def process_due_deliveries(db: AsyncSession, limit: int = 50) -> int:
    now = datetime.now(timezone.utc)
    await _mark_stale_sending_ambiguous(db, now)
    await db.commit()

    delivery_ids = (await db.execute(
        select(NotificationDelivery.id)
        .where(
            NotificationDelivery.channel == "TELEGRAM",
            NotificationDelivery.status.in_(["PENDING", "RETRYING"]),
            or_(NotificationDelivery.next_attempt_at.is_(None), NotificationDelivery.next_attempt_at <= now),
        )
        .order_by(NotificationDelivery.created_at.asc())
        .limit(limit)
    )).scalars().all()

    processed = 0
    for delivery_id in delivery_ids:
        # Claim each delivery durably before any external call. This means a worker
        # restart cannot simply replay an already-started Telegram request.
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

        event = (await db.execute(select(AlertEvent).where(AlertEvent.id == delivery.alert_event_id))).scalar_one_or_none()
        if event is None:
            delivery.status = "FAILED"
            delivery.error = "Alert event no longer exists"
            delivery.completed_at = datetime.now(timezone.utc)
            await db.commit()
            continue
        alert = (await db.execute(select(PriceAlert).where(PriceAlert.id == event.alert_id))).scalar_one_or_none()
        if alert is None:
            delivery.status = "FAILED"
            delivery.error = "Alert no longer exists"
            delivery.completed_at = datetime.now(timezone.utc)
            event.telegram_status = "FAILED"
            await db.commit()
            continue

        chat_id, _ = await resolve_chat_id(db, str(event.user_id))
        delivery.attempt = int(delivery.attempt or 0) + 1
        delivery.requested_at = datetime.now(timezone.utc)
        delivery.status = "SENDING"
        delivery.next_attempt_at = None
        event.telegram_status = "SENDING"
        # notification_sent_at means the Telegram API request started, not phone delivery.
        event.notification_sent_at = delivery.requested_at
        await db.commit()

        if not chat_id:
            result = None
            error = "No Telegram chat configured for this user and TELEGRAM_DEFAULT_CHAT_ID is empty"
        else:
            result = await send_telegram(chat_id, build_alert_message(event, alert))
            error = result.error

        completed = datetime.now(timezone.utc)
        # Re-load after the claim commit so status/result recording is based on the
        # durable delivery row and remains safe if another worker is running.
        delivery = (await db.execute(
            select(NotificationDelivery)
            .options(noload("*"))
            .where(NotificationDelivery.id == delivery_id)
            .with_for_update(of=NotificationDelivery)
        )).scalar_one_or_none()
        event = (await db.execute(select(AlertEvent).where(AlertEvent.id == event.id))).scalar_one_or_none()
        if delivery is None or event is None:
            await db.rollback()
            continue

        delivery.completed_at = completed
        if result and result.ok:
            delivery.status = "SENT"
            delivery.response_code = result.status_code
            delivery.provider_message_id = result.message_id
            delivery.response_payload = result.response
            delivery.error = None
            delivery.next_attempt_at = None
            event.telegram_status = "SENT"
            event.notification_response_at = completed
            event.notification_api_latency_ms = max(0, int((completed - delivery.requested_at).total_seconds() * 1000))
            event.total_internal_latency_ms = max(0, int((completed - event.server_received_at).total_seconds() * 1000))
        else:
            delivery.error = error or "Unknown Telegram delivery error"
            delivery.response_code = result.status_code if result else None
            delivery.response_payload = result.response if result else None
            event.notification_response_at = completed
            if chat_id and delivery.requested_at:
                event.notification_api_latency_ms = max(0, int((completed - delivery.requested_at).total_seconds() * 1000))
            event.total_internal_latency_ms = max(0, int((completed - event.server_received_at).total_seconds() * 1000))

            if result and result.ambiguous:
                delivery.status = "AMBIGUOUS"
                delivery.next_attempt_at = None
                event.telegram_status = "AMBIGUOUS"
            elif result and result.retryable and delivery.attempt < MAX_ATTEMPTS:
                delivery.status = "RETRYING"
                delay = RETRY_DELAYS[min(delivery.attempt, len(RETRY_DELAYS) - 1)]
                delivery.next_attempt_at = completed + timedelta(seconds=delay)
                event.telegram_status = "RETRYING"
            else:
                delivery.status = "FAILED"
                delivery.next_attempt_at = None
                event.telegram_status = "FAILED"

        await db.commit()
        processed += 1
    return processed
