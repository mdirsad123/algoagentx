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


def _approach_transition(alert: PriceAlert, previous: Decimal | None, current: Decimal) -> dict[str, Any] | None:
    """Return approach event metadata when price first crosses into the approach band.

    Zone direction is automatic:
    - from below: useful for a resistance zone
    - from above: useful for a support zone

    The alert does not need a separate support/resistance flag.
    """
    if previous is None or not bool(getattr(alert, "approach_enabled", False)):
        return None
    raw_distance = getattr(alert, "approach_distance", None)
    if raw_distance is None:
        return None
    distance = Decimal(raw_distance)
    if distance <= 0:
        return None

    if alert.alert_type == "CROSSING_UP":
        target = Decimal(alert.target_price)
        threshold = target - distance
        if previous < threshold <= current < target:
            return {
                "event_type": "APPROACHING_TARGET",
                "side": "BELOW",
                "boundary": target,
                "distance_to_boundary": max(Decimal("0"), target - current),
            }
        return None

    if alert.alert_type == "CROSSING_DOWN":
        target = Decimal(alert.target_price)
        threshold = target + distance
        if previous > threshold >= current > target:
            return {
                "event_type": "APPROACHING_TARGET",
                "side": "ABOVE",
                "boundary": target,
                "distance_to_boundary": max(Decimal("0"), current - target),
            }
        return None

    if alert.alert_type != "ENTERING_ZONE":
        # Phase 2A intentionally does not add proximity behavior to LEAVING_ZONE.
        return None

    low, high = Decimal(alert.zone_low), Decimal(alert.zone_high)
    below_threshold = low - distance
    above_threshold = high + distance

    if previous < below_threshold <= current < low:
        return {
            "event_type": "APPROACHING_ZONE",
            "side": "BELOW",
            "boundary": low,
            "distance_to_boundary": max(Decimal("0"), low - current),
        }
    if previous > above_threshold >= current > high:
        return {
            "event_type": "APPROACHING_ZONE",
            "side": "ABOVE",
            "boundary": high,
            "distance_to_boundary": max(Decimal("0"), current - high),
        }
    return None


def _can_rearm_approach(alert: PriceAlert, price: Decimal, now: datetime) -> bool:
    """Rearm an approach warning only after cooldown and a real move away.

    This prevents repeated notifications when price oscillates around the
    approach threshold. For zones, moving far enough to either side rearms the
    next approach cycle, so the same rule supports both resistance and support.
    """
    if alert.trigger_mode != "RECURRING" or not bool(getattr(alert, "approach_enabled", False)):
        return False
    raw_distance = getattr(alert, "approach_distance", None)
    if raw_distance is None:
        return False

    last_sent = getattr(alert, "last_approach_triggered_at", None)
    cooldown_seconds = int(getattr(alert, "cooldown_seconds", 0) or 0)
    if last_sent:
        normalized = last_sent if last_sent.tzinfo else last_sent.replace(tzinfo=timezone.utc)
        if now < normalized + timedelta(seconds=cooldown_seconds):
            return False

    approach_distance = Decimal(raw_distance)
    reset_distance = Decimal(getattr(alert, "rearm_distance", 0) or 0)

    if alert.alert_type == "CROSSING_UP":
        reset_level = Decimal(alert.target_price) - approach_distance - reset_distance
        return price <= reset_level
    if alert.alert_type == "CROSSING_DOWN":
        reset_level = Decimal(alert.target_price) + approach_distance + reset_distance
        return price >= reset_level
    if alert.alert_type == "ENTERING_ZONE":
        low = Decimal(alert.zone_low)
        high = Decimal(alert.zone_high)
        return (
            price <= low - approach_distance - reset_distance
            or price >= high + approach_distance + reset_distance
        )
    return False


def _snapshot(alert: PriceAlert) -> dict[str, Any]:
    return {
        "symbol": alert.symbol,
        "provider": alert.provider,
        "alert_type": alert.alert_type,
        "target_price": str(alert.target_price) if alert.target_price is not None else None,
        "zone_low": str(alert.zone_low) if alert.zone_low is not None else None,
        "zone_high": str(alert.zone_high) if alert.zone_high is not None else None,
        "trigger_mode": alert.trigger_mode,
        "cooldown_seconds": int(alert.cooldown_seconds or 0),
        "rearm_distance": str(alert.rearm_distance or 0),
        "approach_enabled": bool(getattr(alert, "approach_enabled", False)),
        "approach_distance": (
            str(alert.approach_distance)
            if getattr(alert, "approach_distance", None) is not None
            else None
        ),
    }


def _new_event(
    *,
    alert: PriceAlert,
    quote: dict[str, Any],
    event_type: str,
    current: Decimal,
    previous: Decimal | None,
    market_ts: datetime,
    received_at: datetime,
    detected_at: datetime,
    idempotency_key: str,
    extra_payload: dict[str, Any] | None = None,
) -> AlertEvent:
    payload = {
        "quote": quote,
        "alert_snapshot": _snapshot(alert),
    }
    if extra_payload:
        payload.update(extra_payload)
    return AlertEvent(
        alert_id=alert.id,
        user_id=alert.user_id,
        symbol=alert.symbol,
        provider=alert.provider,
        condition_type=event_type,
        trigger_price=current,
        previous_price=previous,
        market_timestamp=market_ts,
        server_received_at=received_at,
        condition_detected_at=detected_at,
        notification_queued_at=detected_at if (alert.telegram_enabled or alert.whatsapp_enabled) else None,
        telegram_status="PENDING" if alert.telegram_enabled else "DISABLED",
        browser_status="DISABLED",
        whatsapp_status="PENDING" if alert.whatsapp_enabled else "DISABLED",
        feed_to_server_latency_ms=_ms((received_at - market_ts).total_seconds()),
        evaluation_latency_ms=_ms((detected_at - received_at).total_seconds()),
        total_internal_latency_ms=_ms((detected_at - received_at).total_seconds()),
        idempotency_key=idempotency_key,
        payload=payload,
    )


async def _persist_delivery(
    db: AsyncSession,
    event: AlertEvent,
    *,
    telegram_enabled: bool,
    whatsapp_enabled: bool,
    detected_at: datetime,
) -> None:
    db.add(event)
    await db.flush()
    if telegram_enabled:
        db.add(
            NotificationDelivery(
                alert_event_id=event.id,
                channel="TELEGRAM",
                status="PENDING",
                attempt=0,
                next_attempt_at=detected_at,
            )
        )
    if whatsapp_enabled:
        db.add(
            NotificationDelivery(
                alert_event_id=event.id,
                channel="WHATSAPP",
                status="PENDING",
                attempt=0,
                next_attempt_at=detected_at,
            )
        )


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

    # Phase 2A adds no extra PostgreSQL query per tick. Approach and main checks
    # run against the same locked alert rows already used by Phase 1.
    rows = (
        await db.execute(
            select(PriceAlert)
            .options(noload("*"))
            .where(*filters)
            .with_for_update(of=PriceAlert, skip_locked=True)
        )
    ).scalars().all()

    triggered: list[str] = []
    for alert in rows:
        if alert.expires_at and now >= alert.expires_at:
            alert.status = "EXPIRED"
            alert.runtime_state = "EXPIRED"
            alert.approach_state = "DISABLED"
            continue

        previous = Decimal(alert.last_price) if alert.last_price is not None else None
        alert.last_price = current
        alert.last_market_timestamp = market_ts

        if alert.runtime_state in {"TRIGGERED", "COOLDOWN", "REARM_WAIT"} and _can_rearm(alert, current, now):
            alert.runtime_state = "ARMED"

        if (
            bool(getattr(alert, "approach_enabled", False))
            and getattr(alert, "approach_state", "DISABLED") in {"APPROACH_SENT", "RESET_WAIT"}
            and _can_rearm_approach(alert, current, now)
        ):
            alert.approach_state = "WAITING"

        approach_match = None
        if (
            alert.runtime_state == "ARMED"
            and bool(getattr(alert, "approach_enabled", False))
            and getattr(alert, "approach_state", "DISABLED") == "WAITING"
        ):
            approach_match = _approach_transition(alert, previous, current)

        main_match = alert.runtime_state == "ARMED" and _transition_matches(alert, previous, current)
        if approach_match is None and not main_match:
            continue

        lock_key = f"alert_lock:{alert.id}"
        client = redis_manager.client
        lock_acquired = True
        if client is not None:
            lock_acquired = bool(await client.set(lock_key, "1", nx=True, ex=10))
        if not lock_acquired:
            continue

        try:
            if approach_match is not None and alert.approach_state == "WAITING":
                detected_at = datetime.now(timezone.utc)
                approach_sequence = int(alert.approach_trigger_count or 0) + 1
                approach_event = _new_event(
                    alert=alert,
                    quote=quote,
                    event_type=str(approach_match["event_type"]),
                    current=current,
                    previous=previous,
                    market_ts=market_ts,
                    received_at=received_at,
                    detected_at=detected_at,
                    idempotency_key=f"{alert.id}:approach:{approach_sequence}",
                    extra_payload={
                        "event_kind": "APPROACH",
                        "approach": {
                            "sequence": approach_sequence,
                            "side": approach_match["side"],
                            "boundary": str(approach_match["boundary"]),
                            "distance_to_boundary": str(approach_match["distance_to_boundary"]),
                        },
                    },
                )
                await _persist_delivery(
                    db,
                    approach_event,
                    telegram_enabled=alert.telegram_enabled,
                    whatsapp_enabled=alert.whatsapp_enabled,
                    detected_at=detected_at,
                )
                alert.approach_trigger_count = approach_sequence
                alert.last_approach_triggered_at = detected_at
                alert.approach_state = "APPROACH_SENT"
                triggered.append(str(approach_event.id))

            if main_match and alert.runtime_state == "ARMED":
                alert.trigger_sequence = int(alert.trigger_sequence or 0) + 1
                sequence = alert.trigger_sequence
                detected_at = datetime.now(timezone.utc)
                event = _new_event(
                    alert=alert,
                    quote=quote,
                    event_type=alert.alert_type,
                    current=current,
                    previous=previous,
                    market_ts=market_ts,
                    received_at=received_at,
                    detected_at=detected_at,
                    idempotency_key=f"{alert.id}:{sequence}",
                    extra_payload={
                        "event_kind": "MAIN",
                        "alert_state_before": "ARMED",
                        "trigger_sequence": sequence,
                    },
                )
                await _persist_delivery(
                    db,
                    event,
                    telegram_enabled=alert.telegram_enabled,
                    whatsapp_enabled=alert.whatsapp_enabled,
                    detected_at=detected_at,
                )

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
