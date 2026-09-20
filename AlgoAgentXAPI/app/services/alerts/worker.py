from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone

from ...core.logging_config import configure_logging

configure_logging()

from ...core.config import settings
from ...core.redis_manager import redis_manager
from ...db.init_db import check_db_connection
from ...db.session import async_session
from ...db.models import BrokerAccount, PriceAlert
from ..brokers.factory import get_broker_adapter
from sqlalchemy import select
from .delivery import process_due_deliveries
from .evaluator import evaluate_quote
from .quote_bus import QUOTE_CHANNEL, publish_quote, upsert_feed_health

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
            logger.exception("Alert worker heartbeat failed: %s", exc)
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
            logger.debug("Alert worker subscribed to %s", QUOTE_CHANNEL)
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
            logger.error(
                "Alert quote subscription disconnected: %s; reconnecting in %.0fs",
                exc,
                reconnect_delay,
            )
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


def _provider(value: object) -> str:
    code = str(value or "").upper().strip()
    if code in {"CTRADER_API", "CTRADER OPEN API"}:
        return "CTRADER"
    if code in {"MT5_AGENT", "METATRADER5", "METATRADER 5"}:
        return "MT5"
    return code


async def _cloud_broker_quote_loop() -> None:
    """Feed alerts from cloud/API brokers that do not push ticks through the MT5 agent.

    MT5 remains unchanged: its agent publishes quotes directly. cTrader/Upstox/other
    adapters are polled in the worker and published onto the same Redis quote bus, so
    the existing evaluator/Telegram/WhatsApp pipeline stays provider-agnostic.
    """
    while True:
        try:
            async with async_session() as db:
                alerts = list((await db.execute(
                    select(PriceAlert).where(
                        PriceAlert.status == "ACTIVE",
                        PriceAlert.broker_account_id.is_not(None),
                        PriceAlert.provider != "MT5",
                    )
                )).scalars().all())
                grouped: dict[object, dict[str, object]] = {}
                for alert in alerts:
                    account_id = alert.broker_account_id
                    entry = grouped.setdefault(account_id, {"provider": _provider(alert.provider), "symbols": set()})
                    entry["symbols"].add(str(alert.symbol))

                for account_id, entry in grouped.items():
                    broker = (await db.execute(select(BrokerAccount).where(BrokerAccount.id == account_id))).scalar_one_or_none()
                    if broker is None or str(broker.status or "").upper() != "CONNECTED":
                        continue
                    provider = str(entry["provider"] or _provider(broker.broker_code or broker.broker_name))
                    symbols = sorted(entry["symbols"])
                    adapter = get_broker_adapter(broker, db)
                    try:
                        if hasattr(adapter, "get_quotes"):
                            quotes = await adapter.get_quotes(symbols)
                        else:
                            quotes = []
                            for symbol in symbols:
                                quote = await adapter.get_quote(symbol)
                                if isinstance(quote, dict):
                                    quotes.append(quote)
                        for quote in quotes:
                            if not isinstance(quote, dict) or quote.get("success") is False:
                                continue
                            price = quote.get("price") or quote.get("last") or quote.get("ltp") or quote.get("bid") or quote.get("ask")
                            if price is None:
                                continue
                            await publish_quote(
                                db,
                                provider=provider,
                                broker_account_id=str(account_id),
                                symbol=str(quote.get("symbol") or ""),
                                price=price,
                                bid=quote.get("bid"),
                                ask=quote.get("ask"),
                                market_timestamp=quote.get("market_timestamp"),
                                raw=quote.get("raw") if isinstance(quote.get("raw"), dict) else quote,
                            )
                    except Exception as exc:
                        await upsert_feed_health(
                            db,
                            provider=provider,
                            broker_account_id=str(account_id),
                            status="DEGRADED",
                            last_heartbeat_at=datetime.now(timezone.utc),
                            connection_error=str(exc),
                            metadata={"symbols": symbols},
                        )
                await db.commit()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception("Cloud broker alert quote loop error: %s", exc)
        await asyncio.sleep(2)


async def run_alert_worker() -> None:
    logger.debug("Starting AlgoAgentX alert worker")
    await check_db_connection()
    await redis_manager.initialize()
    if not redis_manager.is_available:
        logger.error("Redis unavailable at startup; worker will keep reconnecting")
    await asyncio.gather(_heartbeat_loop(), _delivery_loop(), _quote_loop(), _cloud_broker_quote_loop())


def main() -> None:
    try:
        asyncio.run(run_alert_worker())
    except KeyboardInterrupt:
        pass
    except Exception:
        logger.critical("Alert worker crashed", exc_info=True)
        raise


if __name__ == "__main__":
    main()
