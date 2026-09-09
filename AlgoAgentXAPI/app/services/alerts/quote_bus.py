from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.redis_manager import redis_manager
from ...db.models import AlertFeedHealth

QUOTE_CHANNEL = "alerts:quotes"


def _norm(value: str | None) -> str:
    return str(value or "").strip().upper()


def quote_key(provider: str, broker_account_id: str | None, symbol: str) -> str:
    return f"latest_price:{_norm(provider)}:{broker_account_id or 'GLOBAL'}:{_norm(symbol)}"


def _health_throttle_key(provider: str, broker_account_id: str | None) -> str:
    return f"alert_feed_db_touch:{_norm(provider)}:{broker_account_id or 'GLOBAL'}"


async def upsert_feed_health(
    db: AsyncSession,
    *,
    provider: str,
    broker_account_id: str | None,
    status: str,
    last_tick_at: datetime | None = None,
    last_heartbeat_at: datetime | None = None,
    last_reconnect_at: datetime | None = None,
    connection_error: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Concurrency-safe Postgres upsert for one provider/account health row."""
    now = datetime.now(timezone.utc)
    account_uuid = uuid.UUID(str(broker_account_id)) if broker_account_id else None
    values: dict[str, Any] = {
        "id": uuid.uuid4(),
        "provider": _norm(provider),
        "broker_account_id": account_uuid,
        "status": str(status or "DISCONNECTED").upper(),
        "last_tick_at": last_tick_at,
        "last_heartbeat_at": last_heartbeat_at,
        "last_reconnect_at": last_reconnect_at,
        "connection_error": connection_error,
        "metadata_json": metadata,
        "updated_at": now,
    }
    update_values: dict[str, Any] = {
        "status": values["status"],
        "connection_error": connection_error,
        "updated_at": now,
    }
    if last_tick_at is not None:
        update_values["last_tick_at"] = last_tick_at
    if last_heartbeat_at is not None:
        update_values["last_heartbeat_at"] = last_heartbeat_at
    if last_reconnect_at is not None:
        update_values["last_reconnect_at"] = last_reconnect_at
    if metadata is not None:
        update_values["metadata_json"] = metadata

    stmt = pg_insert(AlertFeedHealth).values(**values).on_conflict_do_update(
        constraint="uq_alert_feed_health_provider_account",
        set_=update_values,
    )
    await db.execute(stmt)


async def publish_quote(
    db: AsyncSession,
    *,
    provider: str,
    broker_account_id: str | None,
    symbol: str,
    price: Decimal,
    bid: Decimal | None = None,
    ask: Decimal | None = None,
    market_timestamp: datetime | None = None,
    raw: dict[str, Any] | None = None,
) -> dict[str, Any]:
    received_at = datetime.now(timezone.utc)
    market_ts = market_timestamp or received_at
    if market_ts.tzinfo is None:
        market_ts = market_ts.replace(tzinfo=timezone.utc)
    payload = {
        "provider": _norm(provider),
        "broker_account_id": broker_account_id,
        "symbol": _norm(symbol),
        "price": str(price),
        "bid": str(bid) if bid is not None else None,
        "ask": str(ask) if ask is not None else None,
        "market_timestamp": market_ts.isoformat(),
        "server_received_at": received_at.isoformat(),
        "raw": raw or {},
    }
    encoded = json.dumps(payload, separators=(",", ":"), default=str)

    client = redis_manager.client
    if client is None:
        await redis_manager.initialize()
        client = redis_manager.client

    redis_error: Exception | None = None
    if client is not None:
        try:
            await client.set(quote_key(provider, broker_account_id, symbol), encoded, ex=300)
            await client.publish(QUOTE_CHANNEL, encoded)
        except Exception as exc:
            redis_error = exc
            # Redis may have restarted after API startup. Recreate the client once and retry.
            try:
                await redis_manager.close()
                await redis_manager.initialize()
                client = redis_manager.client
                if client is not None:
                    await client.set(quote_key(provider, broker_account_id, symbol), encoded, ex=300)
                    await client.publish(QUOTE_CHANNEL, encoded)
                    redis_error = None
            except Exception as retry_exc:
                redis_error = retry_exc
    else:
        redis_error = RuntimeError("Redis client is unavailable")

    if redis_error is not None or client is None:
        # The market source may still be online, but alerts cannot be evaluated
        # without the Redis event bus. Surface this as degraded instead of falsely
        # claiming the alert path is protected.
        await upsert_feed_health(
            db,
            provider=provider,
            broker_account_id=broker_account_id,
            status="DEGRADED",
            last_heartbeat_at=received_at,
            connection_error=f"Redis quote publish failed: {redis_error}",
            metadata={"last_symbol": _norm(symbol)},
        )
        await db.flush()
        raise RuntimeError("Real-time alert Redis event bus is unavailable") from redis_error

    # Persist health at most once every 5 seconds per account. Tick-to-worker flow
    # stays Redis-only and low latency; PostgreSQL does not receive a write per tick.
    should_persist = await client.set(_health_throttle_key(provider, broker_account_id), "1", nx=True, ex=5)
    if should_persist:
        await upsert_feed_health(
            db,
            provider=provider,
            broker_account_id=broker_account_id,
            status="CONNECTED",
            last_tick_at=received_at,
            last_heartbeat_at=received_at,
            connection_error=None,
            metadata={"last_symbol": _norm(symbol)},
        )
        await db.flush()
    return payload
