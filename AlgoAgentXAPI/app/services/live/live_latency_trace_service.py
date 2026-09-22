"""Low-overhead T0-T17 tracing for the live event pipeline."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import settings
from ...db.models import LiveExecutionTrace, LiveOrder, LiveSignal
from .live_event_bus import TRACE_KEY_PREFIX, json_dumps


TRACE_STAGE_FIELDS = {
    "t0": "t0_expected_close_at",
    "t1": "t1_broker_event_received_at",
    "t2": "t2_candle_normalized_at",
    "t3": "t3_candle_db_commit_at",
    "t4": "t4_redis_event_published_at",
    "t5": "t5_strategy_event_received_at",
    "t6": "t6_strategy_started_at",
    "t7": "t7_strategy_finished_at",
    "t8": "t8_signal_persisted_at",
    "t9": "t9_execution_started_at",
    "t10": "t10_risk_checks_finished_at",
    "t11": "t11_order_request_queued_at",
    "t12": "t12_order_request_sent_at",
    "t13": "t13_broker_order_accepted_at",
    "t14": "t14_broker_fill_received_at",
    "t15": "t15_local_order_updated_at",
    "t16": "t16_local_position_updated_at",
    "t17": "t17_ui_event_published_at",
}

TRACE_DB_FIELDS = set(TRACE_STAGE_FIELDS.values()) | {
    "trace_id",
    "deployment_id",
    "broker_account_id",
    "signal_id",
    "order_id",
    "candle_open_time",
    "expected_close_at",
    "provider",
    "environment",
    "symbol",
    "timeframe",
    "source",
    "status",
    "signal_type",
    "error_message",
}

DERIVED_METRICS = {
    "broker_candle_latency_ms": ("t0_expected_close_at", "t1_broker_event_received_at"),
    "candle_persist_latency_ms": ("t1_broker_event_received_at", "t3_candle_db_commit_at"),
    "event_bus_latency_ms": ("t4_redis_event_published_at", "t5_strategy_event_received_at"),
    "strategy_queue_latency_ms": ("t5_strategy_event_received_at", "t6_strategy_started_at"),
    "strategy_compute_latency_ms": ("t6_strategy_started_at", "t7_strategy_finished_at"),
    "pretrade_latency_ms": ("t8_signal_persisted_at", "t11_order_request_queued_at"),
    "order_send_latency_ms": ("t11_order_request_queued_at", "t12_order_request_sent_at"),
    "broker_ack_latency_ms": ("t12_order_request_sent_at", "t13_broker_order_accepted_at"),
    "broker_fill_latency_ms": ("t12_order_request_sent_at", "t14_broker_fill_received_at"),
    "close_to_strategy_ms": ("t0_expected_close_at", "t6_strategy_started_at"),
    "close_to_order_send_ms": ("t0_expected_close_at", "t12_order_request_sent_at"),
    "close_to_broker_ack_ms": ("t0_expected_close_at", "t13_broker_order_accepted_at"),
    "close_to_fill_ms": ("t0_expected_close_at", "t14_broker_fill_received_at"),
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime | str | None) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def deterministic_trace_id(deployment_id: str | UUID, candle_open_time: datetime | str) -> str:
    candle = _as_utc(candle_open_time)
    candle_key = candle.isoformat() if candle else str(candle_open_time)
    return f"{deployment_id}:{candle_key}"


def compute_metrics(trace: dict[str, Any]) -> dict[str, float]:
    metrics: dict[str, float] = {}
    for name, (start_field, end_field) in DERIVED_METRICS.items():
        start = _as_utc(trace.get(start_field))
        end = _as_utc(trace.get(end_field))
        if start is None or end is None:
            continue
        metrics[name] = round((end - start).total_seconds() * 1000.0, 3)
    return metrics


class LiveLatencyTraceService:
    def __init__(self, redis_client: Any):
        self.redis = redis_client
        self.enabled = bool(settings.live_latency_trace_enabled and redis_client is not None)
        self.ttl_seconds = max(86400, int(settings.live_latency_trace_retention_days or 30) * 86400)

    def key(self, trace_id: str) -> str:
        return f"{TRACE_KEY_PREFIX}{trace_id}"

    async def start_trace(
        self,
        *,
        trace_id: str,
        deployment_id: str,
        broker_account_id: str | None,
        candle_open_time: datetime,
        expected_close_at: datetime,
        provider: str,
        environment: str,
        symbol: str,
        timeframe: str,
        source: str,
        broker_event_received_at: datetime | None = None,
    ) -> None:
        if not self.enabled:
            return
        values = {
            "trace_id": trace_id,
            "deployment_id": str(deployment_id),
            "broker_account_id": str(broker_account_id) if broker_account_id else "",
            "candle_open_time": candle_open_time.isoformat(),
            "expected_close_at": expected_close_at.isoformat(),
            "provider": provider,
            "environment": environment,
            "symbol": symbol,
            "timeframe": timeframe,
            "source": source,
            "status": "MARKET_EVENT_RECEIVED",
            "t0_expected_close_at": expected_close_at.isoformat(),
            "perf_t0_ns": str(time.perf_counter_ns()),
        }
        if broker_event_received_at:
            values["t1_broker_event_received_at"] = broker_event_received_at.isoformat()
            values["perf_t1_ns"] = str(time.perf_counter_ns())
        pipeline = self.redis.pipeline(transaction=False)
        # The +3s/+8s watchdog may rediscover a candle while the original
        # event is still executing. Preserve the first broker arrival and
        # downstream stages instead of resetting the trace on rediscovery.
        for field, value in values.items():
            pipeline.hsetnx(self.key(trace_id), field, value)
        pipeline.expire(self.key(trace_id), self.ttl_seconds)
        await pipeline.execute()

    async def mark(
        self,
        trace_id: str | None,
        stage: str,
        *,
        at: datetime | None = None,
        status: str | None = None,
        **fields: Any,
    ) -> None:
        if not self.enabled or not trace_id:
            return
        db_field = TRACE_STAGE_FIELDS.get(stage, stage if stage in TRACE_STAGE_FIELDS.values() else None)
        if db_field is None:
            raise ValueError(f"Unknown live latency trace stage: {stage}")
        timestamp = at or _now()
        mapping: dict[str, str] = {
            db_field: timestamp.isoformat(),
            f"perf_{stage}_ns": str(time.perf_counter_ns()),
        }
        if status:
            mapping["status"] = str(status)
        for key, value in fields.items():
            if value is None:
                continue
            if isinstance(value, (dict, list, tuple)):
                mapping[key] = json_dumps(value)
            else:
                mapping[key] = str(value)
        pipeline = self.redis.pipeline(transaction=False)
        pipeline.hset(self.key(trace_id), mapping=mapping)
        pipeline.expire(self.key(trace_id), self.ttl_seconds)
        await pipeline.execute()

    async def annotate(self, trace_id: str | None, **fields: Any) -> None:
        if not self.enabled or not trace_id:
            return
        mapping: dict[str, str] = {}
        for key, value in fields.items():
            if value is None:
                continue
            mapping[key] = json_dumps(value) if isinstance(value, (dict, list, tuple)) else str(value)
        if mapping:
            await self.redis.hset(self.key(trace_id), mapping=mapping)
            await self.redis.expire(self.key(trace_id), self.ttl_seconds)

    async def snapshot(self, trace_id: str) -> dict[str, Any]:
        if not self.enabled:
            return {}
        raw = await self.redis.hgetall(self.key(trace_id))
        result: dict[str, Any] = {}
        for key, value in (raw or {}).items():
            clean_key = key.decode() if isinstance(key, bytes) else str(key)
            clean_value = value.decode() if isinstance(value, bytes) else str(value)
            result[clean_key] = clean_value
        return result

    async def persist(self, db: AsyncSession, trace_id: str) -> dict[str, Any]:
        """Upsert one trace after the critical step; caller controls commit."""
        trace = await self.snapshot(trace_id)
        if not trace:
            return {}
        metrics = compute_metrics(trace)
        perf = {key: int(value) for key, value in trace.items() if key.startswith("perf_") and str(value).isdigit()}
        metadata = self._metadata(trace)
        values: dict[str, Any] = {}
        for field in TRACE_DB_FIELDS:
            value = trace.get(field)
            if value in (None, ""):
                continue
            if field in TRACE_STAGE_FIELDS.values() or field in {"candle_open_time", "expected_close_at"}:
                values[field] = _as_utc(value)
            elif field in {"deployment_id", "broker_account_id", "signal_id", "order_id"}:
                values[field] = UUID(str(value))
            else:
                values[field] = value
        values.setdefault("t0_expected_close_at", values.get("expected_close_at"))

        # Redis tracing can outlive a failed strategy transaction. In that case
        # t8/t15 may contain UUIDs for a signal/order that was rolled back. Never
        # let diagnostic persistence fail the worker with a foreign-key error;
        # keep the timing trace and drop only dangling relational references.
        signal_id = values.get("signal_id")
        if signal_id is not None:
            signal_exists = (await db.execute(
                select(LiveSignal.id).where(LiveSignal.id == signal_id).limit(1)
            )).scalar_one_or_none()
            if signal_exists is None:
                values.pop("signal_id", None)
                metadata["dangling_signal_id"] = str(signal_id)
        order_id = values.get("order_id")
        if order_id is not None:
            order_exists = (await db.execute(
                select(LiveOrder.id).where(LiveOrder.id == order_id).limit(1)
            )).scalar_one_or_none()
            if order_exists is None:
                values.pop("order_id", None)
                metadata["dangling_order_id"] = str(order_id)

        values["metrics_json"] = metrics
        values["perf_json"] = perf
        values["metadata_json"] = metadata
        required = {"trace_id", "deployment_id", "candle_open_time", "expected_close_at", "symbol", "timeframe", "t0_expected_close_at"}
        if not required.issubset(values):
            return {"persisted": False, "missing": sorted(required - set(values))}
        update_values = {
            key: value
            for key, value in values.items()
            if key not in {"trace_id", "deployment_id", "candle_open_time"}
        }
        stmt = insert(LiveExecutionTrace).values(**values)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_live_execution_trace_deployment_candle",
            set_=update_values,
        )
        await db.execute(stmt)
        return {"persisted": True, "metrics": metrics}

    @staticmethod
    def _metadata(trace: dict[str, Any]) -> dict[str, Any]:
        excluded = TRACE_DB_FIELDS | {"expected_close_at"} | set(TRACE_STAGE_FIELDS.values())
        metadata: dict[str, Any] = {}
        for key, value in trace.items():
            if key in excluded or key.startswith("perf_"):
                continue
            if key in {"metrics_json", "perf_json", "metadata_json"}:
                continue
            if isinstance(value, str) and value[:1] in {"{", "["}:
                try:
                    metadata[key] = json.loads(value)
                    continue
                except Exception:
                    pass
            metadata[key] = value
        return metadata
