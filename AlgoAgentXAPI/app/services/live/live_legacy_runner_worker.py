"""Dedicated legacy scheduler worker.

Scheduler and strategy run on the asyncio loop.  Dynamic generate() is a
synchronous, CPU-heavy call, so its health heartbeat MUST NOT share that loop.
The heartbeat's independent sync Redis connection is monitoring only; it never
starts a strategy or places an order.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import multiprocessing as mp
import signal
import threading
from datetime import datetime, timezone

import redis

from ...core.config import settings
from ...core.logging_config import configure_logging
from ...core.redis_manager import redis_manager
from .auto_runner_service import auto_runner_loop
from .live_event_bus import HEALTH_KEY_PREFIX, worker_identity

configure_logging()
logger = logging.getLogger(__name__)


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class RunnerMonitor:
    """Thread-safe telemetry; only asyncio scheduler writes phase transitions."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._phase = "WAITING"
        self._started_at: str | None = None
        self._last_finished_at: str | None = None

    def observe_cycle(self, phase: str) -> None:
        with self._lock:
            if phase == "STARTED":
                self._phase = "PROCESSING"
                self._started_at = _iso()
            elif phase == "FINISHED":
                self._phase = "WAITING"
                self._last_finished_at = _iso()
                self._started_at = None

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "phase": self._phase,
                "cycle_started_at": self._started_at,
                "last_cycle_finished_at": self._last_finished_at,
            }


def publish_heartbeat_forever(
    stop: threading.Event,
    monitor: RunnerMonitor,
    *,
    interval_seconds: float = 5,
    redis_factory=None,
) -> None:
    """Independently refresh Redis TTL even while generate() blocks asyncio.

    Designed for one worker process; the per-role Redis key is NOT an election
    lock. Only one legacy runner replica is permitted (unchanged requirement).
    """
    factory = redis_factory or redis.Redis.from_url
    worker_id = worker_identity("live-legacy-runner")
    key = f"{HEALTH_KEY_PREFIX}live_legacy_runner_worker"
    ttl = max(5, int(settings.live_worker_health_ttl_seconds or 90))
    client = None
    while not stop.is_set():
        try:
            if client is None:
                # The sync client has a separate Redis socket/pool from the
                # event-loop client's connection; do not share async objects.
                client = factory(
                    redis_manager._get_redis_url(),
                    socket_connect_timeout=2,
                    socket_timeout=2,
                    decode_responses=False,
                    health_check_interval=15,
                )
            payload = {
                "role": "live_legacy_runner_worker",
                "worker_id": worker_id,
                "heartbeat_at": _iso(),
                "status": "HEALTHY",  # Process heartbeat only, NOT signal freshness.
                "mode": "LEGACY_POLLING",
                "message": "Worker alive; phase shows whether scheduler is processing",
                **monitor.snapshot(),
            }
            client.set(key, json.dumps(payload, separators=(",", ":")), ex=ttl)
        except Exception:
            logger.warning("Legacy worker Redis heartbeat failed; will reconnect", exc_info=True)
            if client is not None:
                try:
                    client.close()
                except Exception:
                    pass
            client = None
        stop.wait(interval_seconds)
    if client is not None:
        try:
            client.close()
        except Exception:
            pass


async def _shard_runner() -> None:
    """One scheduler shard with its own event loop, DB engine and retained cache."""
    await redis_manager.initialize()
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop.set)
        except NotImplementedError:
            pass
    runner = asyncio.create_task(auto_runner_loop(), name="legacy-runner-shard")
    logger.warning("Legacy runner process shard=%s/%s active", os.environ.get("LIVE_LEGACY_RUNNER_SHARD_INDEX"), os.environ.get("LIVE_LEGACY_RUNNER_SHARD_COUNT"))
    try:
        await stop.wait()
    finally:
        runner.cancel()
        await asyncio.gather(runner, return_exceptions=True)
        await redis_manager.close()


def _shard_entry(index: int, count: int) -> None:
    # Spawn, never fork: asyncpg/SQLAlchemy engines must not cross forks.
    os.environ["LIVE_LEGACY_RUNNER_SHARD_INDEX"] = str(index)
    os.environ["LIVE_LEGACY_RUNNER_SHARD_COUNT"] = str(count)
    asyncio.run(_shard_runner())


async def _supervise_process_pool(stop: asyncio.Event, processes: int) -> None:
    ctx = mp.get_context("spawn")
    children: dict[int, mp.Process] = {}

    def launch(i: int) -> None:
        child = ctx.Process(target=_shard_entry, args=(i, processes),
                            name=f"algoagentx-legacy-runner-{i}", daemon=False)
        child.start()
        children[i] = child
        logger.warning("Live strategy pool shard STARTED index=%s/%s pid=%s", i, processes, child.pid)

    monitor = RunnerMonitor()
    thread_stop = threading.Event()
    pulse = threading.Thread(target=publish_heartbeat_forever, args=(thread_stop, monitor),
                             name="legacy-runner-pool-heartbeat", daemon=True)
    pulse.start()
    try:
        for i in range(processes):
            launch(i)
        while not stop.is_set():
            for i, child in list(children.items()):
                if not child.is_alive():
                    logger.error("Live strategy process shard exited index=%s code=%s restarting", i, child.exitcode)
                    await asyncio.to_thread(child.join, 1)
                    launch(i)
            try:
                await asyncio.wait_for(stop.wait(), timeout=3)
            except asyncio.TimeoutError:
                pass
    finally:
        for child in children.values():
            if child.is_alive():
                child.terminate()
        for child in children.values():
            await asyncio.to_thread(child.join, 10)
            if child.is_alive():
                child.kill()
                await asyncio.to_thread(child.join, 3)
        thread_stop.set()
        await asyncio.to_thread(pulse.join, 3)


async def main() -> None:
    processes = int(getattr(settings, "live_legacy_runner_processes", 1))
    if processes > 1:
        # One Docker service, a configurable pool of independent CPU processes.
        # Existing single-process mode remains the backward-compatible default.
        stop = asyncio.Event()
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, stop.set)
            except NotImplementedError:
                pass
        await _supervise_process_pool(stop, processes)
        return
    await redis_manager.initialize()
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop.set)
        except NotImplementedError:
            pass

    monitor = RunnerMonitor()
    thread_stop = threading.Event()
    pulse = threading.Thread(
        target=publish_heartbeat_forever,
        args=(thread_stop, monitor),
        name="legacy-runner-sync-redis-heartbeat",
        daemon=True,
    )
    pulse.start()
    runner = asyncio.create_task(
        auto_runner_loop(cycle_observer=monitor.observe_cycle),
        name="legacy-broker-scheduler",
    )
    logger.warning("Dedicated legacy runner ACTIVE; ensure the API legacy runner is disabled")
    shutdown = asyncio.create_task(stop.wait(), name="legacy-worker-shutdown")
    try:
        done, _ = await asyncio.wait({runner, shutdown}, return_when=asyncio.FIRST_COMPLETED)
        if runner in done and not stop.is_set():
            exc = runner.exception() if not runner.cancelled() else None
            raise RuntimeError("Legacy strategy scheduler exited unexpectedly") from exc
    finally:
        # Stop the independent heartbeat BEFORE cancellation. Old Redis keys
        # expire naturally; don't delete another replica's key on shutdown.
        thread_stop.set()
        shutdown.cancel()
        runner.cancel()
        await asyncio.gather(runner, return_exceptions=True)
        await asyncio.to_thread(pulse.join, 3)
        await redis_manager.close()


if __name__ == "__main__":
    asyncio.run(main())
