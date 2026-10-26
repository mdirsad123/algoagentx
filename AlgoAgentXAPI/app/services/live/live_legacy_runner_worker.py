"""Dedicated process for non-cTrader legacy polling and strategy execution.

Only one instance should run. The API disables its own legacy runner via the
Compose environment override; the database transaction guard remains unchanged.
"""
from __future__ import annotations

import asyncio
import logging
import signal

from ...core.logging_config import configure_logging
from ...core.redis_manager import redis_manager
from .auto_runner_service import auto_runner_loop
from .live_event_bus import LiveEventBus, worker_identity

configure_logging()
logger = logging.getLogger(__name__)


async def _heartbeat(stop: asyncio.Event) -> None:
    worker_id = worker_identity("live-legacy-runner")
    while not stop.is_set():
        try:
            if not redis_manager.is_available:
                await redis_manager.ensure_connected()
            client = redis_manager.client
            if client is not None:
                await LiveEventBus(client).heartbeat(
                    "live_legacy_runner_worker", worker_id,
                    {"status": "HEALTHY", "mode": "LEGACY_POLLING", "message": "MT5/TradeLocker/Upstox runner process active"},
                )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Legacy runner heartbeat failed")
        try:
            await asyncio.wait_for(stop.wait(), timeout=5)
        except asyncio.TimeoutError:
            pass


async def main() -> None:
    await redis_manager.initialize()
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for name in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(name, stop.set)
        except NotImplementedError:
            pass
    runner = asyncio.create_task(auto_runner_loop(), name="legacy-broker-scheduler")
    heartbeat = asyncio.create_task(_heartbeat(stop), name="legacy-runner-heartbeat")
    logger.warning("Dedicated legacy runner ACTIVE; ensure the API legacy runner is disabled")
    shutdown = asyncio.create_task(stop.wait(), name="legacy-worker-shutdown")
    try:
        done, _ = await asyncio.wait({runner, shutdown}, return_when=asyncio.FIRST_COMPLETED)
        if runner in done and not stop.is_set():
            # Avoid publishing a misleading HEALTHY heartbeat if the runner exits.
            exc = runner.exception() if not runner.cancelled() else None
            raise RuntimeError("Legacy strategy scheduler exited unexpectedly") from exc
    finally:
        shutdown.cancel()
        for task in (runner, heartbeat):
            task.cancel()
        await asyncio.gather(runner, heartbeat, return_exceptions=True)
        await redis_manager.close()


if __name__ == "__main__":
    asyncio.run(main())
