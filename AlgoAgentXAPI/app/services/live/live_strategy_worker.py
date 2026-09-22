"""Redis Stream consumer that runs one exact closed candle per task/session."""

from __future__ import annotations

import asyncio
import logging
import signal
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select

from ...core.config import settings
from ...core.redis_manager import redis_manager
from ...db.models import StrategyDeployment
from ...db.session import async_session
from .live_event_bus import LiveEventBus, StreamMessage, worker_identity
from .live_latency_trace_service import LiveLatencyTraceService
from .strategy_runner import run_strategy_for_candle

logger = logging.getLogger(__name__)


def _parse_time(value: Any) -> datetime:
    text = str(value or "").strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


class LiveStrategyWorker:
    def __init__(self, redis_client: Any):
        self.bus = LiveEventBus(redis_client)
        self.trace = LiveLatencyTraceService(redis_client)
        self.worker_id = worker_identity("live-strategy")
        self._stop = asyncio.Event()
        self._semaphore = asyncio.Semaphore(max(1, int(settings.live_worker_concurrency)))
        self._tasks: set[asyncio.Task] = set()
        self._inflight_ids: set[str] = set()
        self._deployment_locks: dict[UUID, asyncio.Lock] = {}
        self._last_event_at: datetime | None = None
        self._last_completed_at: datetime | None = None
        self._last_error: str | None = None
        self._processed = 0
        self._failed = 0

    async def stop(self) -> None:
        self._stop.set()

    async def run(self) -> None:
        stream = settings.live_candle_stream
        group = settings.live_strategy_consumer_group
        await self.bus.ensure_group(stream, group)
        health_task = asyncio.create_task(self._health_loop(), name="live-strategy-health")
        loop = asyncio.get_running_loop()
        last_reclaim = 0.0
        try:
            while not self._stop.is_set():
                messages: list[StreamMessage] = []
                try:
                    if loop.time() - last_reclaim >= 10:
                        messages.extend(
                            await self.bus.reclaim_pending(
                                stream=stream,
                                group=group,
                                consumer=self.worker_id,
                            )
                        )
                        last_reclaim = loop.time()
                    messages.extend(
                        await self.bus.read_group(
                            stream=stream,
                            group=group,
                            consumer=self.worker_id,
                            count=max(1, int(settings.live_worker_concurrency) * 2),
                            block_ms=1000,
                        )
                    )
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    self._last_error = f"stream read: {exc}"
                    await asyncio.sleep(1)
                    continue
                for message in messages:
                    if message.message_id in self._inflight_ids:
                        continue
                    # Keep memory bounded when a strategy or broker call is slow;
                    # unread stream entries remain durable in Redis.
                    max_inflight = max(1, int(settings.live_worker_concurrency) * 2)
                    while len(self._tasks) >= max_inflight:
                        await asyncio.wait(self._tasks, return_when=asyncio.FIRST_COMPLETED)
                    self._inflight_ids.add(message.message_id)
                    task = asyncio.create_task(
                        self._process_message(message),
                        name=f"live-strategy-{message.message_id}",
                    )
                    self._tasks.add(task)
                    task.add_done_callback(
                        lambda completed, message_id=message.message_id: self._task_done(completed, message_id)
                    )
        finally:
            health_task.cancel()
            await asyncio.gather(health_task, return_exceptions=True)
            if self._tasks:
                # Graceful shutdown: let current idempotent work finish briefly;
                # uncompleted messages remain pending for XAUTOCLAIM after restart.
                done, pending = await asyncio.wait(self._tasks, timeout=15)
                for task in pending:
                    task.cancel()
                await asyncio.gather(*pending, return_exceptions=True)

    def _task_done(self, task: asyncio.Task, message_id: str) -> None:
        self._tasks.discard(task)
        self._inflight_ids.discard(message_id)

    async def _process_message(self, message: StreamMessage) -> None:
        try:
            deployment_id = UUID(str(message.payload.get("deployment_id")))
        except (ValueError, TypeError, AttributeError):
            await self._process_message_locked(message)
            return
        lock = self._deployment_locks.setdefault(deployment_id, asyncio.Lock())
        async with lock:
            await self._process_message_locked(message)

    async def _process_message_locked(self, message: StreamMessage) -> None:
        async with self._semaphore:
            payload = message.payload
            trace_id = str(payload.get("trace_id") or "") or None
            self._last_event_at = datetime.now(timezone.utc)
            await self.trace.mark(trace_id, "t5", status="STRATEGY_EVENT_RECEIVED", redis_message_id=message.message_id)
            should_ack = False
            try:
                deployment_id = UUID(str(payload.get("deployment_id")))
                candle_time = _parse_time(payload.get("candle_open_time"))
                async with async_session() as db:
                    deployment = (
                        await db.execute(
                            select(StrategyDeployment).where(StrategyDeployment.id == deployment_id)
                        )
                    ).scalar_one_or_none()
                    if deployment is None:
                        should_ack = True
                        await self.trace.annotate(trace_id, status="DEPLOYMENT_NOT_FOUND")
                    elif deployment.status != "RUNNING" or not deployment.auto_runner_enabled:
                        should_ack = True
                        await self.trace.annotate(trace_id, status="DEPLOYMENT_INACTIVE")
                    else:
                        result = await run_strategy_for_candle(
                            db,
                            deployment_id,
                            candle_time,
                            trace_id or f"{deployment_id}:{candle_time.isoformat()}",
                            execute=True,
                            event_context={
                                "event_id": payload.get("event_id"),
                                "redis_message_id": message.message_id,
                                "source": payload.get("source"),
                                "environment": payload.get("environment"),
                            },
                        )
                        final_action = str(result.get("final_action") or "").upper()
                        retry_required = final_action in {"LOCK_SKIPPED", "HOLD_NOT_ENOUGH_CANDLES"}
                        await self.trace.annotate(
                            trace_id,
                            status="RETRY_PENDING" if retry_required else "COMPLETED",
                            signal_type=result.get("signal"),
                            signal_id=result.get("signal_id"),
                            order_id=result.get("order_id"),
                            final_action=result.get("final_action"),
                            duplicate=result.get("duplicate"),
                        )
                        # A distributed worker may still own the advisory lock.
                        # Leave this event pending so XAUTOCLAIM retries it; ACKing
                        # here would permanently skip a distinct candle.
                        should_ack = not retry_required

                    published_at = datetime.now(timezone.utc)
                    await self.bus.publish_status({
                        "event": "LIVE_CYCLE_COMPLETED" if should_ack else "LIVE_CYCLE_RETRY",
                        "deployment_id": str(deployment_id),
                        "trace_id": trace_id,
                        "candle_open_time": candle_time.isoformat(),
                    })
                    await self.trace.mark(trace_id, "t17", at=published_at)
                    if trace_id:
                        await self.trace.persist(db, trace_id)
                        await db.commit()
                self._processed += 1
                self._last_completed_at = datetime.now(timezone.utc)
                self._last_error = None
            except HTTPException as exc:
                detail = str(exc.detail)
                # Inactive/not-found/duplicate contract failures are terminal;
                # missing candle/DB/transient failures remain pending for reclaim.
                should_ack = exc.status_code in {400, 404} and "not available" not in detail.lower()
                self._failed += 1
                self._last_error = detail[:500]
                await self.trace.annotate(trace_id, status="FAILED" if should_ack else "RETRY_PENDING", error_message=detail)
                await self._publish_and_persist_error(payload, trace_id, detail)
            except (ValueError, KeyError) as exc:
                should_ack = True
                self._failed += 1
                self._last_error = str(exc)[:500]
                await self.trace.annotate(trace_id, status="INVALID_EVENT", error_message=str(exc))
                await self._publish_and_persist_error(payload, trace_id, str(exc))
            except Exception as exc:
                self._failed += 1
                self._last_error = str(exc)[:500]
                await self.trace.annotate(trace_id, status="RETRY_PENDING", error_message=str(exc))
                logger.exception("Live strategy event %s failed; left pending for reclaim", message.message_id)
            finally:
                if should_ack:
                    await self.bus.ack(
                        settings.live_candle_stream,
                        settings.live_strategy_consumer_group,
                        message.message_id,
                    )

    async def _publish_and_persist_error(self, payload: dict[str, Any], trace_id: str | None, error: str) -> None:
        await self.bus.publish_status({
            "event": "LIVE_CYCLE_ERROR",
            "deployment_id": payload.get("deployment_id"),
            "trace_id": trace_id,
            "error": error[:500],
        })
        await self.trace.mark(trace_id, "t17")
        if trace_id:
            async with async_session() as db:
                await self.trace.persist(db, trace_id)
                await db.commit()

    async def _health_loop(self) -> None:
        while not self._stop.is_set():
            await self.bus.heartbeat(
                "live_strategy_worker",
                self.worker_id,
                {
                    "status": "DEGRADED" if self._last_error else "HEALTHY",
                    "active_tasks": len(self._tasks),
                    "processed": self._processed,
                    "failed": self._failed,
                    "last_event_at": self._last_event_at.isoformat() if self._last_event_at else None,
                    "last_completed_at": self._last_completed_at.isoformat() if self._last_completed_at else None,
                    "last_error": self._last_error,
                },
            )
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=5)
            except asyncio.TimeoutError:
                pass


async def main() -> None:
    if not (settings.live_event_pipeline_enabled and settings.live_strategy_stream_enabled):
        logger.warning("Live strategy worker is idle because its feature flags are disabled")
        while True:
            await asyncio.sleep(3600)
    if not await redis_manager.initialize():
        raise RuntimeError("Redis is required by live_strategy_worker")
    worker = LiveStrategyWorker(redis_manager.client)
    loop = asyncio.get_running_loop()
    for signame in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(signame, lambda: asyncio.create_task(worker.stop()))
        except NotImplementedError:
            pass
    try:
        await worker.run()
    finally:
        await redis_manager.close()


if __name__ == "__main__":
    asyncio.run(main())
