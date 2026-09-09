from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload

from ...core.redis_manager import redis_manager
from ...db.models import AlertEvent, NotificationDelivery, PriceAlert


def _dt(value: Any, fallback: datetime) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if value:
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except Exception:
            pass
    return fallback


def _ms(delta_seconds: float) -> int:
    return max(0, int(delta_seconds * 1000))


def _inside(price: Decimal, low: Decimal, high: Decimal) -> bool:
    return low <= price <= high


def _can_rearm(alert: PriceAlert, price: Decimal, now: datetime) -> bool:
    if alert.trigger_mode != "RECURRING":
        return False
    if alert.rearm_eligible_at and now < alert.rearm_eligible_at:
        return False
    distance = Decimal(alert.rearm_distance or 0)
    if alert.alert_type == "CROSSING_UP":
        return price <= Decimal(alert.target_price) - distance
    if alert.alert_type == "CROSSING_DOWN":
        return price >= Decimal(alert.target_price) + distance
    if alert.alert_type == "ENTERING_ZONE":
        return not _inside(price, Decimal(alert.zone_low), Decimal(alert.zone_high))
    if alert.alert_type == "LEAVING_ZONE":
        return _inside(price, Decimal(alert.zone_low), Decimal(alert.zone_high))
    return False


def _transition_matches(alert: PriceAlert, previous: Decimal | None, current: Decimal) -> bool:
    if previous is None:
        return False
    if alert.alert_type == "CROSSING_UP":
        target = Decimal(alert.target_price)
        return previous < target <= current
    if alert.alert_type == "CROSSING_DOWN":
        target = Decimal(alert.target_price)
        return previous > target >= current
    low, high = Decimal(alert.zone_low), Decimal(alert.zone_high)
    was_inside = _inside(previous, low, high)
    is_inside = _inside(current, low, high)
    if alert.alert_type == "ENTERING_ZONE":
        return (not was_inside) and is_inside
    if alert.alert_type == "LEAVING_ZONE":
        return was_inside and (not is_inside)
    return False


async def evaluate_quote(db: AsyncSession, quote: dict[str, Any]) -> list[str]:
    provider = str(quote.get("provider") or "").upper()
    symbol = str(quote.get("symbol") or "").strip()
    symbol_upper = symbol.upper()
    broker_account_id = quote.get("broker_account_id")
    current = Decimal(str(quote.get("price")))
    now = datetime.now(timezone.utc)
    received_at = _dt(quote.get("server_received_at"), now)
    market_ts = _dt(quote.get("market_timestamp"), received_at)

    filters = [
        PriceAlert.provider == provider,
        func.upper(PriceAlert.symbol) == symbol_upper,
        PriceAlert.status == "ACTIVE",
    ]
    if broker_account_id:
        try:
            filters.append(PriceAlert.broker_account_id == UUID(str(broker_account_id)))
        except Exception:
            filters.append(PriceAlert.broker_account_id == broker_account_id)
    else:
        filters.append(PriceAlert.broker_account_id.is_(None))

    rows = (await db.execute(
        select(PriceAlert)
        .options(noload("*"))
        .where(*filters)
        .with_for_update(of=PriceAlert, skip_locked=True)
    )).scalars().all()
    triggered: list[str] = []
    for alert in rows:
        if alert.expires_at and now >= alert.expires_at:
            alert.status = "EXPIRED"
            alert.runtime_state = "EXPIRED"
            continue

        previous = Decimal(alert.last_price) if alert.last_price is not None else None
        alert.last_price = current
        alert.last_market_timestamp = market_ts

        if alert.runtime_state in {"TRIGGERED", "COOLDOWN", "REARM_WAIT"} and _can_rearm(alert, current, now):
            alert.runtime_state = "ARMED"

        if alert.runtime_state != "ARMED" or not _transition_matches(alert, previous, current):
            continue

        lock_key = f"alert_lock:{alert.id}"
        client = redis_manager.client
        lock_acquired = True
        if client is not None:
            lock_acquired = bool(await client.set(lock_key, "1", nx=True, ex=10))
        if not lock_acquired:
            continue

        try:
            alert.trigger_sequence = int(alert.trigger_sequence or 0) + 1
            sequence = alert.trigger_sequence
            idempotency_key = f"{alert.id}:{sequence}"
            detected_at = datetime.now(timezone.utc)
            event = AlertEvent(
                alert_id=alert.id,
                user_id=alert.user_id,
                symbol=alert.symbol,
                provider=alert.provider,
                condition_type=alert.alert_type,
                trigger_price=current,
                previous_price=previous,
                market_timestamp=market_ts,
                server_received_at=received_at,
                condition_detected_at=detected_at,
                notification_queued_at=detected_at if alert.telegram_enabled else None,
                telegram_status="PENDING" if alert.telegram_enabled else "DISABLED",
                browser_status="DISABLED",
                whatsapp_status="DISABLED",
                feed_to_server_latency_ms=_ms((received_at - market_ts).total_seconds()),
                evaluation_latency_ms=_ms((detected_at - received_at).total_seconds()),
                total_internal_latency_ms=_ms((detected_at - received_at).total_seconds()),
                idempotency_key=idempotency_key,
                payload={
                    "quote": quote,
                    "alert_state_before": "ARMED",
                    "trigger_sequence": sequence,
                    "alert_snapshot": {
                        "symbol": alert.symbol,
                        "provider": alert.provider,
                        "alert_type": alert.alert_type,
                        "target_price": str(alert.target_price) if alert.target_price is not None else None,
                        "zone_low": str(alert.zone_low) if alert.zone_low is not None else None,
                        "zone_high": str(alert.zone_high) if alert.zone_high is not None else None,
                        "trigger_mode": alert.trigger_mode,
                        "cooldown_seconds": int(alert.cooldown_seconds or 0),
                        "rearm_distance": str(alert.rearm_distance or 0),
                    },
                },
            )
            db.add(event)
            await db.flush()
            if alert.telegram_enabled:
                db.add(NotificationDelivery(alert_event_id=event.id, channel="TELEGRAM", status="PENDING", attempt=0, next_attempt_at=detected_at))

            alert.trigger_count = int(alert.trigger_count or 0) + 1
            alert.last_triggered_at = detected_at
            if alert.trigger_mode == "ONCE":
                alert.status = "COMPLETED"
                alert.runtime_state = "TRIGGERED"
            else:
                alert.runtime_state = "COOLDOWN"
                alert.rearm_eligible_at = detected_at + timedelta(seconds=int(alert.cooldown_seconds or 0))
            triggered.append(str(event.id))
        finally:
            if client is not None:
                try:
                    await client.delete(lock_key)
                except Exception:
                    pass

    await db.commit()
    return triggered
