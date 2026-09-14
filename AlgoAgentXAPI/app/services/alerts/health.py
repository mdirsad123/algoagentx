from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import settings
from ...core.redis_manager import redis_manager
from ...db.models import AlertFeedHealth, BrokerAccount, PriceAlert
from .telegram import telegram_configured
from .whatsapp import whatsapp_configured
from .worker import WORKER_HEARTBEAT_KEY


async def alert_health(db: AsyncSession, user_id: str) -> dict:
    now = datetime.now(timezone.utc)
    redis_ok = False
    worker = "unhealthy"
    worker_heartbeat = None
    try:
        client = redis_manager.client
        if client is None:
            await redis_manager.initialize()
            client = redis_manager.client
        if client is not None:
            try:
                redis_ok = bool(await client.ping())
            except Exception:
                await redis_manager.close()
                await redis_manager.initialize()
                client = redis_manager.client
                redis_ok = bool(client is not None and await client.ping())
            if redis_ok and client is not None:
                raw = await client.get(WORKER_HEARTBEAT_KEY)
                if isinstance(raw, bytes):
                    raw = raw.decode("utf-8")
                worker_heartbeat = raw
                if raw:
                    ts = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
                    if ts.tzinfo is None:
                        ts = ts.replace(tzinfo=timezone.utc)
                    if now - ts <= timedelta(seconds=int(getattr(settings, "alert_worker_heartbeat_ttl_seconds", 30) or 30)):
                        worker = "healthy"
    except Exception:
        redis_ok = False
    db_ok = True
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        db_ok = False

    active_alert_count = int((await db.execute(
        select(func.count(PriceAlert.id)).where(
            PriceAlert.user_id == user_id,
            PriceAlert.status == "ACTIVE",
        )
    )).scalar_one() or 0)

    account_ids = select(BrokerAccount.id).where(BrokerAccount.user_id == user_id)
    feed_rows = (await db.execute(
        select(AlertFeedHealth)
        .where(or_(AlertFeedHealth.broker_account_id.is_(None), AlertFeedHealth.broker_account_id.in_(account_ids)))
        .order_by(AlertFeedHealth.updated_at.desc())
        .limit(50)
    )).scalars().all()
    stale_seconds = int(getattr(settings, "alert_feed_stale_seconds", 15) or 15)
    feeds = []
    for row in feed_rows:
        # A terminal/agent heartbeat proves the agent is online, but it does NOT prove
        # that live alert ticks are reaching Redis. Market-feed health must therefore
        # be driven primarily by last_tick_at. This prevents a healthy MT5 heartbeat
        # from falsely showing "Connected" while active alerts still have Last Price = 0.
        tick_at = row.last_tick_at
        heartbeat_at = row.last_heartbeat_at
        computed = "DISCONNECTED"
        computed_error = row.connection_error

        if tick_at:
            normalized_tick = tick_at if tick_at.tzinfo else tick_at.replace(tzinfo=timezone.utc)
            tick_age = now - normalized_tick
            if tick_age <= timedelta(seconds=stale_seconds):
                computed = "CONNECTED"
                computed_error = None
            elif tick_age <= timedelta(seconds=stale_seconds * 4):
                computed = "DEGRADED"
                computed_error = computed_error or "Alert quote stream is stale."
            else:
                computed = "DISCONNECTED"
                computed_error = computed_error or "No recent alert quote tick received."
        elif heartbeat_at:
            normalized_heartbeat = heartbeat_at if heartbeat_at.tzinfo else heartbeat_at.replace(tzinfo=timezone.utc)
            heartbeat_age = now - normalized_heartbeat
            if heartbeat_age <= timedelta(seconds=stale_seconds * 4):
                computed = "DEGRADED"
                computed_error = computed_error or "MT5 Agent heartbeat is online, but no live alert quote tick has been received yet."

        feeds.append({
            "provider": row.provider,
            "broker_account_id": str(row.broker_account_id) if row.broker_account_id else None,
            "status": computed,
            "last_tick_at": row.last_tick_at.isoformat() if row.last_tick_at else None,
            "last_heartbeat_at": row.last_heartbeat_at.isoformat() if row.last_heartbeat_at else None,
            "connection_error": computed_error,
        })
    if active_alert_count == 0:
        market_feed = "idle"
    else:
        market_feed = "connected" if any(x["status"] == "CONNECTED" for x in feeds) else ("degraded" if any(x["status"] == "DEGRADED" for x in feeds) else "disconnected")
    last_tick = next((x["last_tick_at"] for x in feeds if x["last_tick_at"]), None)
    return {
        "worker": worker,
        "worker_heartbeat": worker_heartbeat,
        "redis": "healthy" if redis_ok else "unhealthy",
        "database": "healthy" if db_ok else "unhealthy",
        "market_feed": market_feed,
        "active_alert_count": active_alert_count,
        "last_tick": last_tick,
        "telegram": "configured" if telegram_configured() else "not_configured",
        "whatsapp": "configured" if whatsapp_configured() else "not_configured",
        "feeds": feeds,
    }
