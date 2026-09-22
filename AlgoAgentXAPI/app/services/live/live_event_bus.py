"""Durable Redis Stream contracts for the event-driven live pipeline."""

from __future__ import annotations

import asyncio
import json
import socket
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from ...core.config import settings

LIVE_STATUS_STREAM = "live:pipeline_status"
HEALTH_KEY_PREFIX = "live:worker_health:"
TRACE_KEY_PREFIX = "live:trace:"
ORDER_RESULT_KEY_PREFIX = "live:ctrader_order_result:"
ORDER_DEDUPE_KEY_PREFIX = "live:ctrader_order_dedupe:"


def utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def worker_identity(role: str) -> str:
    return f"{role}-{socket.gethostname()}-{uuid.uuid4().hex[:8]}"


def _json_default(value: Any) -> Any:
    if isinstance(value, (datetime, Decimal, uuid.UUID)):
        return str(value)
    raise TypeError(f"Unsupported JSON value: {type(value).__name__}")


def json_dumps(value: Any) -> str:
    return json.dumps(value, default=_json_default, separators=(",", ":"), sort_keys=True)


def _text(value: Any) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def decode_stream_fields(fields: dict[Any, Any]) -> dict[str, Any]:
    decoded = {_text(key): _text(value) for key, value in (fields or {}).items()}
    raw = decoded.get("data")
    if raw:
        try:
            payload = json.loads(raw)
            return payload if isinstance(payload, dict) else {"data": payload}
        except Exception:
            return {"raw": raw}
    return decoded


@dataclass(frozen=True)
class StreamMessage:
    message_id: str
    payload: dict[str, Any]


class LiveEventBus:
    def __init__(self, redis_client: Any):
        if redis_client is None:
            raise RuntimeError("Redis is required for the event-driven live pipeline")
        self.redis = redis_client
        self.maxlen = max(1000, int(settings.live_stream_maxlen or 100000))

    async def ensure_group(self, stream: str, group: str, *, start_id: str = "0-0") -> None:
        try:
            await self.redis.xgroup_create(stream, group, id=start_id, mkstream=True)
        except Exception as exc:
            if "BUSYGROUP" not in str(exc):
                raise

    async def publish_candle(self, payload: dict[str, Any]) -> str:
        message_id = await self.redis.xadd(
            settings.live_candle_stream,
            {"data": json_dumps(payload)},
            maxlen=self.maxlen,
            approximate=True,
        )
        return _text(message_id)

    async def publish_order_request(self, payload: dict[str, Any]) -> str:
        message_id = await self.redis.xadd(
            settings.live_order_request_stream,
            {"data": json_dumps(payload)},
            maxlen=self.maxlen,
            approximate=True,
        )
        return _text(message_id)

    async def publish_status(self, payload: dict[str, Any]) -> str:
        event = {"published_at": utc_iso(), **payload}
        message_id = await self.redis.xadd(
            LIVE_STATUS_STREAM,
            {"data": json_dumps(event)},
            maxlen=min(self.maxlen, 20000),
            approximate=True,
        )
        return _text(message_id)

    async def read_group(
        self,
        *,
        stream: str,
        group: str,
        consumer: str,
        count: int = 10,
        block_ms: int = 1000,
    ) -> list[StreamMessage]:
        rows = await self.redis.xreadgroup(
            group,
            consumer,
            streams={stream: ">"},
            count=max(1, int(count)),
            block=max(1, int(block_ms)),
        )
        return self._normalize_read(rows)

    async def reclaim_pending(
        self,
        *,
        stream: str,
        group: str,
        consumer: str,
        min_idle_ms: int | None = None,
        count: int = 25,
    ) -> list[StreamMessage]:
        min_idle = max(1000, int(min_idle_ms or settings.live_pending_reclaim_idle_ms))
        result = await self.redis.xautoclaim(
            stream,
            group,
            consumer,
            min_idle_time=min_idle,
            start_id="0-0",
            count=max(1, int(count)),
        )
        # redis-py returns (next_id, messages[, deleted_ids]).
        messages = result[1] if isinstance(result, (tuple, list)) and len(result) >= 2 else []
        return [
            StreamMessage(message_id=_text(message_id), payload=decode_stream_fields(fields))
            for message_id, fields in messages or []
        ]

    async def ack(self, stream: str, group: str, message_id: str) -> int:
        return int(await self.redis.xack(stream, group, message_id) or 0)

    async def heartbeat(self, role: str, worker_id: str, payload: dict[str, Any]) -> None:
        ttl = max(5, int(settings.live_worker_health_ttl_seconds or 30))
        data = {
            "role": role,
            "worker_id": worker_id,
            "heartbeat_at": utc_iso(),
            **payload,
        }
        await self.redis.set(f"{HEALTH_KEY_PREFIX}{role}", json_dumps(data), ex=ttl)

    async def get_health(self, role: str) -> dict[str, Any] | None:
        raw = await self.redis.get(f"{HEALTH_KEY_PREFIX}{role}")
        if not raw:
            return None
        try:
            value = json.loads(_text(raw))
            return value if isinstance(value, dict) else None
        except Exception:
            return None

    async def set_order_result(self, request_id: str, payload: dict[str, Any], *, ttl_seconds: int = 300) -> None:
        key = f"{ORDER_RESULT_KEY_PREFIX}{request_id}"
        body = json_dumps(payload)
        pipeline = self.redis.pipeline(transaction=False)
        pipeline.rpush(key, body)
        pipeline.expire(key, max(30, int(ttl_seconds)))
        await pipeline.execute()

    async def wait_order_result(self, request_id: str, *, timeout_seconds: int) -> dict[str, Any]:
        key = f"{ORDER_RESULT_KEY_PREFIX}{request_id}"
        loop = asyncio.get_running_loop()
        deadline = loop.time() + max(1, int(timeout_seconds))
        row = None
        # Keep each blocking call below RedisManager's socket timeout while still
        # returning immediately as soon as RPUSH wakes BLPOP.
        while row is None and loop.time() < deadline:
            row = await self.redis.blpop(key, timeout=1)
        if not row:
            raise TimeoutError("Timed out waiting for the persistent cTrader order gateway")
        raw = row[1] if isinstance(row, (tuple, list)) and len(row) > 1 else row
        await self.redis.delete(key)
        value = json.loads(_text(raw))
        return value if isinstance(value, dict) else {"success": False, "message": "Invalid order gateway response"}

    async def get_order_dedupe(self, idempotency_key: str) -> dict[str, Any] | None:
        raw = await self.redis.get(f"{ORDER_DEDUPE_KEY_PREFIX}{idempotency_key}")
        if not raw:
            return None
        try:
            value = json.loads(_text(raw))
            return value if isinstance(value, dict) else None
        except Exception:
            return None

    @staticmethod
    def order_dedupe_in_progress(payload: dict[str, Any] | None) -> bool:
        return str((payload or {}).get("_state") or "").upper() == "PROCESSING"

    async def claim_order_dedupe(
        self,
        idempotency_key: str,
        request_id: str,
        *,
        ttl_seconds: int = 300,
    ) -> bool:
        """Atomically claim an external broker side effect before it is sent."""
        marker = {
            "_state": "PROCESSING",
            "owner_request_id": str(request_id),
            "claimed_at": utc_iso(),
        }
        claimed = await self.redis.set(
            f"{ORDER_DEDUPE_KEY_PREFIX}{idempotency_key}",
            json_dumps(marker),
            ex=max(60, int(ttl_seconds)),
            nx=True,
        )
        return bool(claimed)

    async def wait_order_dedupe_result(
        self,
        idempotency_key: str,
        *,
        timeout_seconds: int,
    ) -> dict[str, Any] | None:
        loop = asyncio.get_running_loop()
        deadline = loop.time() + max(1, int(timeout_seconds))
        while loop.time() < deadline:
            value = await self.get_order_dedupe(idempotency_key)
            if value and not self.order_dedupe_in_progress(value):
                return value
            await asyncio.sleep(0.05)
        return None

    async def set_order_dedupe(self, idempotency_key: str, payload: dict[str, Any], *, ttl_seconds: int = 86400) -> None:
        await self.redis.set(
            f"{ORDER_DEDUPE_KEY_PREFIX}{idempotency_key}",
            json_dumps(payload),
            ex=max(300, int(ttl_seconds)),
        )

    @staticmethod
    def _normalize_read(rows: Any) -> list[StreamMessage]:
        messages: list[StreamMessage] = []
        for _stream, stream_rows in rows or []:
            for message_id, fields in stream_rows or []:
                messages.append(
                    StreamMessage(
                        message_id=_text(message_id),
                        payload=decode_stream_fields(fields),
                    )
                )
        return messages
