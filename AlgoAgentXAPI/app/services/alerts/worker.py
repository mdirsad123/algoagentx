from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone

from sqlalchemy import text

from ...core.config import settings
from ...core.redis_manager import redis_manager
from ...db.init_db import check_db_connection
from ...db.session import async_session
from .delivery import process_due_deliveries
from .evaluator import evaluate_quote
from .quote_bus import QUOTE_CHANNEL

logger = logging.getLogger(__name__)
WORKER_HEARTBEAT_KEY = "alerts:worker:heartbeat"


async def _heartbeat_loop() -> None:
    while True:
        try:
            if redis_manager.client is not None:
                await redis_manager.client.set(
                    WORKER_HEARTBEAT_KEY,
                    datetime.now(timezone.utc).isoformat(),
                    ex=max(10, int(getattr(settings, "alert_worker_heartbeat_ttl_seconds", 30) or 30)),
                )
        except Exception as exc:
            logger.warning("Alert worker heartbeat failed: %s", exc)
        await asyncio.sleep(5)


async def _delivery_loop() -> None:
    while True:
        try:
            async with async_session() as db:
                await process_due_deliveries(db)
        except Exception as exc:
            logger.exception("Alert delivery loop error: %s", exc)
        await asyncio.sleep(1)


async def _quote_loop() -> None:
    reconnect_delay = 1.0
    while True:
        if not redis_manager.is_available:
            await redis_manager.initialize()
        client = redis_manager.client
        if client is None:
            await asyncio.sleep(reconnect_delay)
            reconnect_delay = min(reconnect_delay * 2.0, 30.0)
            continue
        pubsub = client.pubsub()
        try:
            reconnect_delay = 1.0
            await pubsub.subscribe(QUOTE_CHANNEL)
            logger.info("Alert worker subscribed to %s", QUOTE_CHANNEL)
            async for message in pubsub.listen():
                if message.get("type") != "message":
                    continue
                try:
                    raw = message.get("data")
                    if isinstance(raw, bytes):
                        raw = raw.decode("utf-8")
                    quote = json.loads(raw)
                    async with async_session() as db:
                        await evaluate_quote(db, quote)
                except Exception as exc:
                    logger.exception("Alert quote evaluation failed: %s", exc)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning("Alert quote subscription disconnected: %s; reconnecting in %.0fs", exc, reconnect_delay)
            try:
                await redis_manager.close()
            except Exception:
                pass
            await asyncio.sleep(reconnect_delay)
            reconnect_delay = min(reconnect_delay * 2.0, 30.0)
        finally:
            try:
                await pubsub.close()
            except Exception:
                pass


async def run_alert_worker() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    logger.info("Starting AlgoAgentX alert worker")
    await check_db_connection()
    await redis_manager.initialize()
    if not redis_manager.is_available:
        logger.warning("Redis unavailable at startup; worker will keep reconnecting")
    await asyncio.gather(_heartbeat_loop(), _delivery_loop(), _quote_loop())


def main() -> None:
    try:
        asyncio.run(run_alert_worker())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
