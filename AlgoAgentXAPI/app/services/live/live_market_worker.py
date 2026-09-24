"""Persistent cTrader market-data and order-I/O worker.

Normal operation is driven by live trendbars carried on ``ProtoOASpotEvent``.
Historical requests are limited to startup, reconnect and the +3s/+8s missing
candle watchdog.  Strategy execution is deliberately not performed here.
"""

from __future__ import annotations

import asyncio
import logging
import signal
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert

from ...core.config import settings
from ...core.redis_manager import redis_manager
from ...db.models import BrokerAccount, BrokerOrderEvent, LiveBrokerOrderIntent, LiveMarketCandle, StrategyDeployment
from ...db.session import async_session
from ...utils.credential_crypto import decrypt_credential
from ..brokers.ctrader import CTraderAdapter, _money_value, _without_secret
from ..brokers.ctrader_connection_manager import (
    PT_CLOSE_POSITION_REQ,
    PT_EXECUTION_EVENT,
    PT_NEW_ORDER_REQ,
    PT_SPOT_EVENT,
    PersistentCTraderConnection,
    ctrader_connection_manager,
)
from ..brokers.factory import get_broker_code
from .live_event_bus import LiveEventBus, StreamMessage, utc_iso, worker_identity
from .live_latency_trace_service import (
    LiveLatencyTraceService,
    deterministic_trace_id,
)

logger = logging.getLogger(__name__)

PERIOD_BY_TIMEFRAME = {
    "M1": 1,
    "M2": 2,
    "M3": 3,
    "M4": 4,
    "M5": 5,
    "M10": 6,
    "M15": 7,
    "M30": 8,
    "H1": 9,
    "H4": 10,
    "H12": 11,
    "D1": 12,
    "W1": 13,
    "MN1": 14,
}

MINUTES_BY_TIMEFRAME = {
    "M1": 1,
    "M2": 2,
    "M3": 3,
    "M4": 4,
    "M5": 5,
    "M10": 10,
    "M15": 15,
    "M30": 30,
    "H1": 60,
    "H4": 240,
    "H12": 720,
    "D1": 1440,
    "W1": 10080,
    "MN1": 43200,
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_timeframe(value: Any) -> str:
    clean = str(value or "M5").strip().upper().replace(" ", "")
    aliases = {
        "1M": "M1", "2M": "M2", "3M": "M3", "4M": "M4", "5M": "M5",
        "10M": "M10", "15M": "M15", "30M": "M30", "1H": "H1", "4H": "H4",
        "12H": "H12", "1D": "D1", "1W": "W1", "1MO": "MN1",
    }
    clean = aliases.get(clean, clean)
    if clean not in PERIOD_BY_TIMEFRAME:
        raise ValueError(f"Unsupported cTrader live timeframe: {value}")
    return clean


def _parse_dt(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    text = str(value or "").strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _decode_trendbar(bar: dict[str, Any], *, symbol: str, timeframe: str) -> dict[str, Any]:
    low = int(bar.get("low") or 0)
    opened = low + int(bar.get("deltaOpen") or 0)
    high = low + int(bar.get("deltaHigh") or 0)
    close = low + int(bar.get("deltaClose") or 0)
    minute_stamp = int(bar.get("utcTimestampInMinutes") or 0)
    if not minute_stamp:
        raise ValueError("cTrader trendbar has no utcTimestampInMinutes")
    candle_time = datetime.fromtimestamp(minute_stamp * 60, tz=timezone.utc)
    scale = Decimal("100000")
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "candle_time": candle_time,
        "open": Decimal(opened) / scale,
        "high": Decimal(high) / scale,
        "low": Decimal(low) / scale,
        "close": Decimal(close) / scale,
        "volume": Decimal(str(bar.get("volume"))) if bar.get("volume") not in (None, "") else None,
        "raw_payload": _without_secret(bar),
    }


def _expected_close(candle_time: datetime, timeframe: str) -> datetime:
    return candle_time + timedelta(minutes=MINUTES_BY_TIMEFRAME[timeframe])


def _latest_expected_open(now: datetime, timeframe: str) -> datetime:
    minutes = MINUTES_BY_TIMEFRAME[timeframe]
    epoch_minute = int(now.timestamp() // 60)
    aligned_current = (epoch_minute // minutes) * minutes
    return datetime.fromtimestamp((aligned_current - minutes) * 60, tz=timezone.utc)


@dataclass
class FeedRegistration:
    deployment_id: UUID
    broker_account_id: UUID
    environment: str
    account_id: int
    symbol: str
    symbol_id: int
    timeframe: str
    period: int
    client_id: str
    client_secret: str
    access_token: str
    last_closed_time: datetime | None = None
    watchdog_attempts: dict[str, int] = field(default_factory=dict)

    @property
    def subscription_key(self) -> tuple[str, int, int, int]:
        return (self.environment, self.account_id, self.symbol_id, self.period)


class LiveMarketWorker:
    def __init__(self, redis_client: Any):
        self.bus = LiveEventBus(redis_client)
        self.trace = LiveLatencyTraceService(redis_client)
        self.worker_id = worker_identity("live-market")
        self.feeds: dict[UUID, FeedRegistration] = {}
        self.current_bars: dict[tuple[str, int, int, int], dict[str, Any]] = {}
        self._registered_handlers: set[str] = set()
        self._candle_queue: asyncio.Queue[tuple[FeedRegistration, dict[str, Any], str, datetime]] = asyncio.Queue(maxsize=10000)
        self._stop = asyncio.Event()
        self._last_market_event_at: datetime | None = None
        self._last_candle_published_at: datetime | None = None
        self._last_order_at: datetime | None = None
        self._last_error: str | None = None
        self._feed_semaphore = asyncio.Semaphore(max(1, int(settings.live_worker_concurrency)))
        self._order_semaphore = asyncio.Semaphore(max(1, int(settings.live_worker_concurrency)))
        self._order_inflight_ids: set[str] = set()
        self._tasks: set[asyncio.Task] = set()

    async def run(self) -> None:
        await self.bus.ensure_group(settings.live_order_request_stream, settings.live_order_consumer_group)
        loops = [
            asyncio.create_task(self._registry_loop(), name="live-market-registry"),
            asyncio.create_task(self._candle_processor_loop(), name="live-market-candles"),
            asyncio.create_task(self._order_consumer_loop(), name="live-market-orders"),
            asyncio.create_task(self._watchdog_loop(), name="live-market-watchdog"),
            asyncio.create_task(self._health_loop(), name="live-market-health"),
        ]
        try:
            await self._stop.wait()
        finally:
            for task in loops:
                task.cancel()
            await asyncio.gather(*loops, return_exceptions=True)
            for task in list(self._tasks):
                task.cancel()
            await asyncio.gather(*self._tasks, return_exceptions=True)
            await ctrader_connection_manager.stop()

    async def stop(self) -> None:
        self._stop.set()

    def _spawn(self, coroutine: Any, *, name: str) -> None:
        task = asyncio.create_task(coroutine, name=name)
        self._tasks.add(task)

        def _finished(done: asyncio.Task) -> None:
            self._tasks.discard(done)
            if done.cancelled():
                return
            try:
                exc = done.exception()
            except asyncio.CancelledError:
                return
            if exc is not None:
                self._last_error = f"{name}: {exc}"[:1000]
                logger.error("Background live-market task %s failed: %s", name, exc, exc_info=exc)

        # Always retrieve task exceptions so asyncio never emits
        # 'Task exception was never retrieved' for broker events.
        task.add_done_callback(_finished)

    async def _registry_loop(self) -> None:
        while not self._stop.is_set():
            try:
                await self.refresh_registry()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self._last_error = f"registry: {exc}"
                logger.exception("Live market deployment registry refresh failed")
            try:
                await asyncio.wait_for(
                    self._stop.wait(), timeout=max(5, int(settings.live_market_deployment_scan_seconds))
                )
            except asyncio.TimeoutError:
                pass

    async def refresh_registry(self) -> None:
        async with async_session() as db:
            rows = (
                await db.execute(
                    select(StrategyDeployment, BrokerAccount)
                    .join(BrokerAccount, BrokerAccount.id == StrategyDeployment.broker_account_id)
                    .where(
                        StrategyDeployment.status == "RUNNING",
                        StrategyDeployment.auto_runner_enabled.is_(True),
                        StrategyDeployment.mode.in_(["DEMO", "LIVE"]),
                        BrokerAccount.status == "CONNECTED",
                    )
                )
            ).all()
            ctrader_rows = [
                (deployment, broker)
                for deployment, broker in rows
                if get_broker_code(broker) in {"CTRADER", "CTRADER_API"}
            ]
            registrations = await asyncio.gather(
                *(self._build_registration(deployment, broker) for deployment, broker in ctrader_rows),
                return_exceptions=True,
            )

        active_ids: set[UUID] = set()
        activations: list[tuple[FeedRegistration, FeedRegistration | None, asyncio.Task]] = []
        for row, result in zip(ctrader_rows, registrations):
            deployment, _broker = row
            if isinstance(result, Exception):
                self._last_error = f"deployment {deployment.id}: {result}"
                logger.error("Could not register cTrader deployment %s: %s", deployment.id, result)
                # Preserve an already-live feed across a transient registry/auth
                # refresh error.  A deployment removed from the query is still
                # unregistered below.
                if deployment.id in self.feeds:
                    active_ids.add(deployment.id)
                continue
            active_ids.add(result.deployment_id)
            previous = self.feeds.get(result.deployment_id)
            self.feeds[result.deployment_id] = result
            if previous is None or previous.subscription_key != result.subscription_key:
                activations.append((
                    result,
                    previous,
                    asyncio.create_task(
                        self._activate_feed(result),
                        name=f"activate-live-feed-{result.deployment_id}",
                    ),
                ))

        # New/changed deployments bootstrap concurrently. A slow broker account
        # must not delay another deployment becoming live.
        for result, previous, task in activations:
            try:
                await task
            except Exception as exc:
                self._last_error = f"deployment {result.deployment_id}: {exc}"
                logger.exception("Could not activate cTrader deployment %s", result.deployment_id)
                if previous is None:
                    self.feeds.pop(result.deployment_id, None)
                    active_ids.discard(result.deployment_id)
                else:
                    self.feeds[result.deployment_id] = previous

        removed_ids = set(self.feeds) - active_ids
        for deployment_id in removed_ids:
            removed = self.feeds.pop(deployment_id)
            if not any(feed.subscription_key == removed.subscription_key for feed in self.feeds.values()):
                connection = ctrader_connection_manager.connection(removed.environment)
                if connection is not None:
                    try:
                        await connection.unsubscribe_live_trendbar(removed.account_id, removed.symbol_id, removed.period)
                    except Exception:
                        logger.warning("Could not unsubscribe removed cTrader feed %s", removed.subscription_key)

    async def _build_registration(self, deployment: StrategyDeployment, broker: BrokerAccount) -> FeedRegistration:
        metadata = broker.metadata_json if isinstance(broker.metadata_json, dict) else {}
        selected = metadata.get("ctrader_selected_account") or metadata.get("selected_account")
        if not isinstance(selected, dict):
            raise ValueError("selected cTrader account is missing")
        account_raw = selected.get("ctrader_account_id") or selected.get("account_number")
        if account_raw in (None, ""):
            raise ValueError("selected cTrader account id is missing")
        environment = "LIVE" if bool(selected.get("is_live")) or str(selected.get("account_type") or broker.mode).upper() == "LIVE" else "DEMO"
        if environment == "LIVE" and not bool(settings.ctrader_live_trading_enabled):
            # Market data is safe in LIVE, but make the state explicit; order code
            # continues to reject unless the existing platform flag is enabled.
            logger.info("Registering LIVE cTrader market data with LIVE execution disabled")
        timeframe = _normalize_timeframe(deployment.timeframe)
        symbol = str(deployment.broker_symbol or deployment.instrument_key or deployment.instrument).strip().upper()
        client_id = str(broker.oauth_client_id or settings.ctrader_client_id or "").strip()
        account_secret = decrypt_credential(broker.encrypted_client_secret)
        client_secret = str(account_secret or settings.ctrader_client_secret or "").strip()
        access_token = str(decrypt_credential(broker.encrypted_token) or "").strip()
        if not client_id or not client_secret or not access_token:
            raise ValueError("cTrader client credentials/access token are incomplete")

        symbol_id = self._symbol_id_from_metadata(metadata, symbol)
        connection = await ctrader_connection_manager.get_connection(
            environment=environment,
            client_id=client_id,
            client_secret=client_secret,
        )
        await connection.authorize_account(int(account_raw), access_token)
        if symbol_id is None:
            symbol_id = await self._resolve_symbol_id(connection, int(account_raw), symbol)
        previous = self.feeds.get(deployment.id)
        return FeedRegistration(
            deployment_id=deployment.id,
            broker_account_id=broker.id,
            environment=environment,
            account_id=int(account_raw),
            symbol=symbol,
            symbol_id=int(symbol_id),
            timeframe=timeframe,
            period=PERIOD_BY_TIMEFRAME[timeframe],
            client_id=client_id,
            client_secret=client_secret,
            access_token=access_token,
            last_closed_time=previous.last_closed_time if previous else None,
            watchdog_attempts=dict(previous.watchdog_attempts) if previous else {},
        )

    @staticmethod
    def _symbol_id_from_metadata(metadata: dict[str, Any], symbol: str) -> int | None:
        rows = metadata.get("ctrader_symbols_preview") or metadata.get("symbols") or []
        for row in rows if isinstance(rows, list) else []:
            if not isinstance(row, dict):
                continue
            name = str(row.get("symbol_name") or row.get("symbol") or row.get("trading_symbol") or "").upper()
            if name == symbol and (row.get("symbol_id") or row.get("id")) not in (None, ""):
                return int(row.get("symbol_id") or row.get("id"))
        return None

    @staticmethod
    async def _resolve_symbol_id(connection: PersistentCTraderConnection, account_id: int, symbol: str) -> int:
        payload = await connection.get_symbols(account_id)
        rows = payload.get("symbol") or []
        for row in rows if isinstance(rows, list) else []:
            if not isinstance(row, dict):
                continue
            name = str(row.get("symbolName") or row.get("symbol") or "").upper()
            if name == symbol and row.get("symbolId") not in (None, ""):
                return int(row["symbolId"])
        raise ValueError(f"cTrader symbol {symbol} was not found")

    async def _activate_feed(self, feed: FeedRegistration) -> None:
        connection = ctrader_connection_manager.connection(feed.environment)
        if connection is None:
            raise RuntimeError(f"cTrader {feed.environment} connection is unavailable")
        if feed.environment not in self._registered_handlers:
            connection.add_event_handler(
                PT_SPOT_EVENT,
                lambda message, env=feed.environment: self._handle_spot_event(env, message),
            )
            connection.add_event_handler(
                PT_EXECUTION_EVENT,
                lambda message, env=feed.environment: self._handle_execution_event(env, message),
            )
            connection.add_reconnect_handler(
                lambda reconnect, env=feed.environment: self._on_connection_ready(env, reconnect)
            )
            self._registered_handlers.add(feed.environment)

        # Subscribe to the live stream first. A temporary historical-trendbar
        # timeout must not prevent the deployment from receiving future closed
        # candles. Historical bootstrap is recovery/warm-up, not a prerequisite
        # for keeping the persistent market stream alive.
        await connection.subscribe_spots(feed.account_id, [feed.symbol_id])
        await connection.subscribe_live_trendbar(feed.account_id, feed.symbol_id, feed.period)
        try:
            await self._bootstrap_feed(feed)
        except Exception as exc:
            self._last_error = f"bootstrap {feed.deployment_id}: {exc}"[:1000]
            logger.warning(
                "cTrader live feed %s subscribed but initial candle bootstrap failed; retrying in background: %s",
                feed.deployment_id,
                exc,
            )
            self._spawn(
                self._retry_bootstrap_feed(feed),
                name=f"bootstrap-retry-{feed.deployment_id}",
            )

    async def _retry_bootstrap_feed(self, feed: FeedRegistration) -> None:
        delays = (2, 5, 10, 20)
        last_error: Exception | None = None
        for delay in delays:
            if self._stop.is_set() or feed.deployment_id not in self.feeds:
                return
            await asyncio.sleep(delay)
            try:
                await self._bootstrap_feed(feed)
                if self._last_error and self._last_error.startswith(f"bootstrap {feed.deployment_id}:"):
                    self._last_error = None
                logger.info("cTrader candle bootstrap recovered for deployment %s", feed.deployment_id)
                return
            except Exception as exc:
                last_error = exc
        if last_error is not None:
            self._last_error = f"bootstrap {feed.deployment_id}: {last_error}"[:1000]
            logger.error("cTrader candle bootstrap still failing for deployment %s: %s", feed.deployment_id, last_error)

    async def _bootstrap_feed(self, feed: FeedRegistration) -> None:
        bars = await self._fetch_bars(feed, max(20, int(settings.live_market_bootstrap_candles)))
        now = _now()
        closed = [bar for bar in bars if _expected_close(bar["candle_time"], feed.timeframe) <= now]
        forming = [bar for bar in bars if _expected_close(bar["candle_time"], feed.timeframe) > now]
        if closed:
            await self._store_historical(feed, closed)
            feed.last_closed_time = max(bar["candle_time"] for bar in closed)
        if forming:
            self.current_bars[feed.subscription_key] = max(forming, key=lambda row: row["candle_time"])
        # Recover only the latest few unprocessed candles; never emit all 300.
        await self._backfill_feed(feed, publish_missing=True)

    async def _fetch_bars(self, feed: FeedRegistration, count: int) -> list[dict[str, Any]]:
        connection = ctrader_connection_manager.connection(feed.environment)
        if connection is None:
            raise RuntimeError("cTrader connection unavailable")
        safe_count = max(1, min(int(count), 2000))
        now = _now()
        from_at = now - timedelta(minutes=MINUTES_BY_TIMEFRAME[feed.timeframe] * (safe_count + 5))
        payload = await connection.get_trendbars({
            "ctidTraderAccountId": feed.account_id,
            "fromTimestamp": int(from_at.timestamp() * 1000),
            "toTimestamp": int(now.timestamp() * 1000),
            "period": feed.period,
            "symbolId": feed.symbol_id,
            "count": safe_count,
        })
        rows = payload.get("trendbar") or payload.get("trendbars") or []
        bars: list[dict[str, Any]] = []
        for row in rows if isinstance(rows, list) else []:
            if not isinstance(row, dict) or row.get("low") is None:
                continue
            try:
                bars.append(_decode_trendbar(row, symbol=feed.symbol, timeframe=feed.timeframe))
            except Exception:
                continue
        bars.sort(key=lambda item: item["candle_time"])
        return bars[-safe_count:]

    async def _store_historical(self, feed: FeedRegistration, bars: list[dict[str, Any]]) -> None:
        async with async_session() as db:
            for candle in bars:
                values = self._candle_values(feed, candle, source="CTRADER_BOOTSTRAP")
                stmt = insert(LiveMarketCandle).values(**values).on_conflict_do_update(
                    constraint="uq_live_market_candles_dep_symbol_tf_time",
                    set_={
                        "broker_account_id": values["broker_account_id"],
                        "open": values["open"],
                        "high": values["high"],
                        "low": values["low"],
                        "close": values["close"],
                        "volume": values["volume"],
                        "source": values["source"],
                        "is_closed": True,
                        "raw_payload": values["raw_payload"],
                        "updated_at": func.now(),
                    },
                )
                await db.execute(stmt)
            await db.commit()

    def _handle_spot_event(self, environment: str, message: dict[str, Any]) -> None:
        try:
            received_at = _parse_dt(message.get("_received_at"))
        except (TypeError, ValueError):
            received_at = _now()
        self._last_market_event_at = received_at
        payload = message.get("payload") if isinstance(message.get("payload"), dict) else {}
        symbol_id = int(payload.get("symbolId") or 0)
        account_value = payload.get("ctidTraderAccountId")
        account_id = int(account_value) if account_value not in (None, "") else None
        trendbars = payload.get("trendbar") or payload.get("trendbars") or []
        for raw_bar in trendbars if isinstance(trendbars, list) else []:
            if not isinstance(raw_bar, dict):
                continue
            period_value = int(raw_bar.get("period") or 0)
            candidates = [
                feed for feed in self.feeds.values()
                if feed.environment == environment
                and feed.symbol_id == symbol_id
                and (not period_value or feed.period == period_value)
                and (account_id is None or feed.account_id == account_id)
            ]
            if not candidates:
                continue
            template = candidates[0]
            try:
                current = _decode_trendbar(raw_bar, symbol=template.symbol, timeframe=template.timeframe)
            except Exception as exc:
                self._last_error = f"trendbar normalize: {exc}"
                continue
            cache_key = template.subscription_key
            previous = self.current_bars.get(cache_key)
            self.current_bars[cache_key] = current
            if previous and current["candle_time"] > previous["candle_time"]:
                for feed in candidates:
                    try:
                        self._candle_queue.put_nowait((feed, previous, "CTRADER_LIVE_TRENDBAR", received_at))
                    except asyncio.QueueFull:
                        self._last_error = "closed-candle queue is full; watchdog recovery required"

    def _handle_execution_event(self, environment: str, message: dict[str, Any]) -> None:
        # Never perform database I/O in the sole WebSocket receive coroutine.
        self._spawn(
            self._persist_execution_event(environment, message),
            name=f"ctrader-{environment.lower()}-execution-event",
        )

    async def _persist_execution_event(self, environment: str, message: dict[str, Any]) -> None:
        """Persist broker execution events without touching hot strategy rows.

        The previous implementation updated strategy_deployments, live_orders and
        live_positions immediately from this background task. That can race the
        strategy worker, which is still holding its transaction/advisory lock while
        creating the local signal/order/position. The result is a classic lock
        cycle and PostgreSQL DeadlockDetectedError.

        The event worker now performs only a short append-only BrokerOrderEvent
        transaction. Local order/position repair is deliberately owned by the
        reconcile worker after the strategy transaction commits. Immediate order
        responses still update local state in execution_engine, so this change does
        not add latency to the normal filled-order path.
        """
        payload = message.get("payload") if isinstance(message.get("payload"), dict) else {}
        account_value = payload.get("ctidTraderAccountId")
        account_id = int(account_value) if account_value not in (None, "") else None
        feeds = [
            feed for feed in self.feeds.values()
            if feed.environment == environment and (account_id is None or feed.account_id == account_id)
        ]
        if not feeds:
            return

        order_payload = payload.get("order") if isinstance(payload.get("order"), dict) else {}
        trade_data = order_payload.get("tradeData") if isinstance(order_payload.get("tradeData"), dict) else {}
        broker_order_id, broker_position_id = CTraderAdapter._execution_ids(payload)
        client_order_id = order_payload.get("clientOrderId") or trade_data.get("label")
        execution_type = int(payload.get("executionType") or 0)
        status = (
            "FILLED" if execution_type == 3 else
            "PARTIAL" if execution_type == 11 else
            "PLACED" if execution_type == 2 else
            "CANCELLED" if execution_type == 5 else
            "REJECTED" if execution_type == 7 else
            "UPDATED"
        )
        now = _now()
        try:
            broker_received_at = _parse_dt(message.get("_received_at"))
        except (TypeError, ValueError):
            broker_received_at = now

        safe_payload = {**_without_secret(payload), "_received_at": broker_received_at.isoformat()}
        # A deadlock here should be very unlikely because this is append-only, but
        # retry twice so a transient FK/index lock never kills the background task.
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                async with async_session() as db:
                    for feed in feeds:
                        relevant = bool(
                            client_order_id
                            and (
                                str(client_order_id).startswith(f"AX-{str(feed.deployment_id)[:8]}-")
                                or str(feed.deployment_id) in str(client_order_id)
                            )
                        )
                        db.add(BrokerOrderEvent(
                            broker_provider_code="CTRADER",
                            broker_account_id=feed.broker_account_id,
                            deployment_id=feed.deployment_id,
                            broker_order_id=broker_order_id,
                            event_type="CTRADER_EXECUTION_EVENT",
                            raw_payload=safe_payload,
                            # Relevant AlgoAgentX events are replayed after the local
                            # order transaction commits. Unrelated broker events are
                            # still visible in the event log but need no replay.
                            processed=not relevant,
                        ))
                    await db.commit()
                last_error = None
                break
            except Exception as exc:
                last_error = exc
                if "deadlock" not in str(exc).lower() or attempt >= 2:
                    raise
                await asyncio.sleep(0.05 * (attempt + 1))

        if last_error is not None:
            raise last_error

        await self.bus.publish_status({
            "event": "CTRADER_EXECUTION_EVENT",
            "environment": environment,
            "broker_order_id": broker_order_id,
            "broker_position_id": broker_position_id,
            "client_order_id": client_order_id,
            "status": status,
            "broker_received_at": broker_received_at.isoformat(),
        })
        self._last_order_at = now

    async def _candle_processor_loop(self) -> None:
        while not self._stop.is_set():
            feed, candle, source, received_at = await self._candle_queue.get()
            await self._feed_semaphore.acquire()
            async def _process(
                feed: FeedRegistration = feed,
                candle: dict[str, Any] = candle,
                source: str = source,
                received_at: datetime = received_at,
            ) -> None:
                try:
                    await self._persist_and_publish(feed, candle, source, received_at)
                except Exception as exc:
                    self._last_error = f"candle {feed.deployment_id}: {exc}"
                    logger.exception("Closed candle processing failed for %s", feed.deployment_id)
                finally:
                    self._feed_semaphore.release()
                    self._candle_queue.task_done()
            self._spawn(_process(), name=f"live-candle-{feed.deployment_id}")

    async def _persist_and_publish(
        self,
        feed: FeedRegistration,
        candle: dict[str, Any],
        source: str,
        received_at: datetime,
    ) -> None:
        candle_time = candle["candle_time"]
        expected_close_at = _expected_close(candle_time, feed.timeframe)
        trace_id = deterministic_trace_id(feed.deployment_id, candle_time)
        await self.trace.start_trace(
            trace_id=trace_id,
            deployment_id=str(feed.deployment_id),
            broker_account_id=str(feed.broker_account_id),
            candle_open_time=candle_time,
            expected_close_at=expected_close_at,
            provider="CTRADER",
            environment=feed.environment,
            symbol=feed.symbol,
            timeframe=feed.timeframe,
            source=source,
            broker_event_received_at=received_at,
        )
        await self.trace.mark(trace_id, "t2", status="CANDLE_NORMALIZED")

        async with async_session() as db:
            deployment = (
                await db.execute(select(StrategyDeployment).where(StrategyDeployment.id == feed.deployment_id))
            ).scalar_one_or_none()
            if deployment is None or deployment.status != "RUNNING" or not deployment.auto_runner_enabled:
                await self.trace.annotate(trace_id, status="DEPLOYMENT_INACTIVE")
                return
            values = self._candle_values(feed, candle, source=source, trace_id=trace_id)
            stmt = insert(LiveMarketCandle).values(**values).on_conflict_do_update(
                constraint="uq_live_market_candles_dep_symbol_tf_time",
                set_={
                    "broker_account_id": values["broker_account_id"],
                    "open": values["open"],
                    "high": values["high"],
                    "low": values["low"],
                    "close": values["close"],
                    "volume": values["volume"],
                    "source": values["source"],
                    "is_closed": True,
                    "raw_payload": values["raw_payload"],
                    "updated_at": func.now(),
                },
            )
            await db.execute(stmt)
            processed_at = deployment.last_processed_candle_time
            if processed_at is not None and processed_at.tzinfo is None:
                processed_at = processed_at.replace(tzinfo=timezone.utc)
            already_processed = bool(processed_at and processed_at >= candle_time)
            await db.commit()
        persisted_at = _now()
        await self.trace.mark(trace_id, "t3", at=persisted_at, status="CANDLE_STORED")
        feed.last_closed_time = max(filter(None, [feed.last_closed_time, candle_time]))
        if already_processed:
            await self.trace.annotate(trace_id, status="ALREADY_PROCESSED")
            return

        publish_requested_at = _now()
        event = {
            "event_id": str(uuid.uuid4()),
            "deployment_id": str(feed.deployment_id),
            "broker_account_id": str(feed.broker_account_id),
            "provider": "CTRADER",
            "environment": feed.environment,
            "symbol": feed.symbol,
            "symbol_id": str(feed.symbol_id),
            "timeframe": feed.timeframe,
            "candle_open_time": candle_time.isoformat(),
            "expected_close_at": expected_close_at.isoformat(),
            "broker_event_received_at": received_at.isoformat(),
            "candle_persisted_at": persisted_at.isoformat(),
            "redis_publish_requested_at": publish_requested_at.isoformat(),
            "source": source,
            "trace_id": trace_id,
        }
        stream_id = await self.bus.publish_candle(event)
        published_at = _now()
        await self.trace.mark(trace_id, "t4", at=published_at, status="CANDLE_EVENT_PUBLISHED", redis_stream_id=stream_id)
        self._last_candle_published_at = published_at
        self._last_error = None

    @staticmethod
    def _candle_values(
        feed: FeedRegistration,
        candle: dict[str, Any],
        *,
        source: str,
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        raw = candle.get("raw_payload") if isinstance(candle.get("raw_payload"), dict) else {}
        if trace_id:
            raw = {**raw, "trace_id": trace_id}
        return {
            "deployment_id": feed.deployment_id,
            "broker_account_id": feed.broker_account_id,
            "symbol": feed.symbol,
            "timeframe": feed.timeframe,
            "candle_time": candle["candle_time"],
            "open": candle["open"],
            "high": candle["high"],
            "low": candle["low"],
            "close": candle["close"],
            "volume": candle.get("volume"),
            "source": source,
            "is_closed": True,
            "raw_payload": raw,
        }

    async def _backfill_feed(self, feed: FeedRegistration, *, publish_missing: bool) -> None:
        bars = await self._fetch_bars(feed, max(2, int(settings.live_market_backfill_candles)))
        now = _now()
        closed = [bar for bar in bars if _expected_close(bar["candle_time"], feed.timeframe) <= now]
        if not closed:
            return
        if not publish_missing:
            await self._store_historical(feed, closed)
            return
        async with async_session() as db:
            deployment = (
                await db.execute(select(StrategyDeployment).where(StrategyDeployment.id == feed.deployment_id))
            ).scalar_one_or_none()
            processed = deployment.last_processed_candle_time if deployment else None
            started_at = deployment.started_at if deployment else None
            if processed is not None and processed.tzinfo is None:
                processed = processed.replace(tzinfo=timezone.utc)
            if started_at is not None and started_at.tzinfo is None:
                started_at = started_at.replace(tzinfo=timezone.utc)
        for candle in closed:
            if processed and candle["candle_time"] <= processed:
                continue
            if not processed and started_at and _expected_close(candle["candle_time"], feed.timeframe) < started_at:
                continue
            await self._persist_and_publish(feed, candle, "CTRADER_RECOVERY_BACKFILL", _now())

    def _on_connection_ready(self, environment: str, reconnect: bool) -> None:
        if reconnect:
            self._spawn(self._recover_environment(environment), name=f"ctrader-{environment.lower()}-recovery")

    async def _recover_environment(self, environment: str) -> None:
        feeds = [item for item in self.feeds.values() if item.environment == environment]
        results = await asyncio.gather(
            *(self._backfill_feed(feed, publish_missing=True) for feed in feeds),
            return_exceptions=True,
        )
        for feed, result in zip(feeds, results):
            if isinstance(result, Exception):
                self._last_error = f"reconnect backfill {feed.deployment_id}: {result}"

    async def _watchdog_loop(self) -> None:
        while not self._stop.is_set():
            await self._watchdog_check_once(_now())
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=1.0)
            except asyncio.TimeoutError:
                pass

    async def _watchdog_check_once(self, now: datetime) -> None:
        first = max(1, int(settings.live_candle_fallback_first_seconds))
        second = max(first + 1, int(settings.live_candle_fallback_second_seconds))
        recoveries: list[tuple[FeedRegistration, str, datetime]] = []
        for feed in list(self.feeds.values()):
            expected_open = _latest_expected_open(now, feed.timeframe)
            seconds_after_close = (now - _expected_close(expected_open, feed.timeframe)).total_seconds()
            if seconds_after_close < first or (feed.last_closed_time and feed.last_closed_time >= expected_open):
                continue
            key = expected_open.isoformat()
            attempt = feed.watchdog_attempts.get(key, 0)
            threshold = first if attempt == 0 else second
            if seconds_after_close < threshold or attempt >= 2:
                continue
            feed.watchdog_attempts[key] = attempt + 1
            recoveries.append((feed, key, expected_open))

        async def recover(feed: FeedRegistration, key: str, expected_open: datetime) -> None:
            try:
                await self._backfill_feed(feed, publish_missing=True)
                if feed.last_closed_time and feed.last_closed_time >= expected_open:
                    feed.watchdog_attempts.pop(key, None)
            except Exception as exc:
                self._last_error = f"watchdog {feed.deployment_id}: {exc}"

        await asyncio.gather(
            *(recover(feed, key, expected_open) for feed, key, expected_open in recoveries),
            return_exceptions=True,
        )

    async def _order_consumer_loop(self) -> None:
        group = settings.live_order_consumer_group
        consumer = self.worker_id
        stream = settings.live_order_request_stream
        last_reclaim = 0.0
        loop = asyncio.get_running_loop()
        while not self._stop.is_set():
            messages: list[StreamMessage] = []
            try:
                if loop.time() - last_reclaim >= 10:
                    messages.extend(await self.bus.reclaim_pending(stream=stream, group=group, consumer=consumer))
                    last_reclaim = loop.time()
                messages.extend(await self.bus.read_group(stream=stream, group=group, consumer=consumer, count=20, block_ms=1000))
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self._last_error = f"order stream: {exc}"
                await asyncio.sleep(1)
                continue
            for message in messages:
                if message.message_id in self._order_inflight_ids:
                    continue
                await self._order_semaphore.acquire()
                self._order_inflight_ids.add(message.message_id)
                self._spawn(self._process_order_message(message), name=f"ctrader-order-{message.message_id}")

    async def _process_order_message(self, message: StreamMessage) -> None:
        request_id = ""
        idempotency_key = ""
        try:
            payload = message.payload
            request_id = str(payload.get("request_id") or "")
            idempotency_key = str(payload.get("idempotency_key") or "")
            if not request_id or not idempotency_key:
                raise ValueError("Invalid cTrader order gateway event")
            cached = await self.bus.get_order_dedupe(idempotency_key)
            if cached and not self.bus.order_dedupe_in_progress(cached):
                response = {**cached, "gateway_deduplicated": True}
            else:
                claimed = False
                if not cached:
                    claimed = await self.bus.claim_order_dedupe(
                        idempotency_key,
                        request_id,
                        ttl_seconds=max(300, int(settings.live_order_dedupe_ttl_seconds)),
                    )
                if claimed:
                    response = await self._execute_gateway_request(payload)
                    await self.bus.set_order_dedupe(idempotency_key, response)
                else:
                    response = await self.bus.wait_order_dedupe_result(
                        idempotency_key,
                        timeout_seconds=max(3, int(settings.ctrader_order_timeout_seconds) + 5),
                    )
                    if response is None:
                        response = {
                            "success": False,
                            "status": "PENDING",
                            "message": (
                                "An identical cTrader broker action is already in flight or its outcome is "
                                "uncertain; duplicate send blocked and reconciliation required."
                            ),
                            "raw_response": {
                                "provider": "CTRADER",
                                "gateway": "PERSISTENT_SESSION",
                                "dedupe_state": "PROCESSING",
                            },
                        }
            await self.bus.set_order_result(request_id, response)
            await self.bus.ack(settings.live_order_request_stream, settings.live_order_consumer_group, message.message_id)
        except Exception as exc:
            self._last_error = f"order {request_id}: {exc}"
            response = {
                "success": False,
                "status": "FAILED",
                "message": str(exc),
                "raw_response": {"provider": "CTRADER", "gateway": "PERSISTENT_SESSION"},
            }
            if request_id:
                await self.bus.set_order_result(request_id, response)
                if idempotency_key:
                    await self.bus.set_order_dedupe(idempotency_key, response, ttl_seconds=300)
            await self.bus.ack(settings.live_order_request_stream, settings.live_order_consumer_group, message.message_id)
        finally:
            self._order_inflight_ids.discard(message.message_id)
            self._order_semaphore.release()

    async def _execute_gateway_request(self, request: dict[str, Any]) -> dict[str, Any]:
        broker_id = UUID(str(request.get("broker_account_id")))
        trace_id = str(request.get("trace_id") or "") or None
        async with async_session() as db:
            broker = (await db.execute(select(BrokerAccount).where(BrokerAccount.id == broker_id))).scalar_one_or_none()
            if broker is None or broker.status != "CONNECTED" or get_broker_code(broker) not in {"CTRADER", "CTRADER_API"}:
                raise ValueError("Connected cTrader broker account is required")
            metadata = broker.metadata_json if isinstance(broker.metadata_json, dict) else {}
            selected = metadata.get("ctrader_selected_account") or metadata.get("selected_account")
            if not isinstance(selected, dict):
                raise ValueError("Selected cTrader account is missing")
            environment = "LIVE" if bool(selected.get("is_live")) or str(selected.get("account_type") or broker.mode).upper() == "LIVE" else "DEMO"
            if environment == "LIVE" and not bool(settings.ctrader_live_trading_enabled):
                raise ValueError("cTrader live order execution is disabled by platform configuration")
            if environment == "DEMO" and not bool(settings.ctrader_demo_trading_enabled):
                raise ValueError("cTrader demo order execution is disabled by platform configuration")
            account_id = int(selected.get("ctrader_account_id") or selected.get("account_number"))
            client_id = str(broker.oauth_client_id or settings.ctrader_client_id or "").strip()
            client_secret = str(decrypt_credential(broker.encrypted_client_secret) or settings.ctrader_client_secret or "").strip()
            token = str(decrypt_credential(broker.encrypted_token) or "").strip()
        connection = await ctrader_connection_manager.get_connection(
            environment=environment, client_id=client_id, client_secret=client_secret
        )
        await connection.authorize_account(account_id, token)

        def broker_received_at(payload: dict[str, Any]) -> datetime:
            try:
                return datetime.fromisoformat(str(payload.get("_received_at")))
            except (TypeError, ValueError):
                return _now()

        async def on_ack(payload: dict[str, Any]) -> None:
            await self.trace.mark(trace_id, "t13", at=broker_received_at(payload), status="BROKER_ACCEPTED")

        async def on_fill(payload: dict[str, Any]) -> None:
            await self.trace.mark(trace_id, "t14", at=broker_received_at(payload), status="BROKER_FILLED")

        async def on_sent(payload: dict[str, Any]) -> None:
            sent_at_raw = payload.get("sent_at")
            try:
                sent_at = datetime.fromisoformat(str(sent_at_raw)) if sent_at_raw else _now()
            except (TypeError, ValueError):
                sent_at = _now()
            await self.trace.mark(trace_id, "t12", at=sent_at, status="ORDER_SENT")

        action = str(request.get("action") or "PLACE_MARKET").upper()
        client_order_id = str(request.get("client_order_id") or request.get("idempotency_key") or "")[:50]
        if action in {"PLACE_MARKET", "CLOSE_POSITION"} and not client_order_id:
            raise ValueError("A deterministic cTrader clientOrderId is required")
        if action == "PLACE_MARKET":
            order = request.get("order") if isinstance(request.get("order"), dict) else {}
            symbol = str(order.get("symbol") or "").upper()
            symbol_id = self._symbol_id_from_metadata(metadata, symbol)
            if symbol_id is None:
                symbol_id = await self._resolve_symbol_id(connection, account_id, symbol)
            full = await connection.get_full_symbol(account_id, symbol_id)
            full_rows = full.get("symbol") or []
            full_symbol = full_rows[0] if isinstance(full_rows, list) and full_rows else {}
            lots = Decimal(str(order.get("qty") or 0))
            protocol_volume = CTraderAdapter._lots_to_protocol_volume(lots, full_symbol)
            side = str(order.get("side") or "").upper()
            if side not in {"BUY", "SELL"}:
                raise ValueError("cTrader order side must be BUY or SELL")
            payload: dict[str, Any] = {
                "ctidTraderAccountId": account_id,
                "symbolId": int(symbol_id),
                "orderType": 1,
                "tradeSide": 1 if side == "BUY" else 2,
                "volume": protocol_volume,
                "clientOrderId": client_order_id,
                "label": client_order_id[:100],
                "comment": str(order.get("comment") or "AlgoAgentX persistent cTrader")[:512],
            }
            entry = Decimal(str(order.get("price"))) if order.get("price") not in (None, "") else None
            for request_key, protocol_key in (("stop_loss", "relativeStopLoss"), ("target", "relativeTakeProfit")):
                value = order.get(request_key)
                if value in (None, ""):
                    continue
                if entry is None or entry <= 0:
                    raise ValueError("Entry price is required for cTrader relative SL/TP")
                relative = CTraderAdapter._price_distance_to_relative(entry, Decimal(str(value)), full_symbol)
                if relative > 0:
                    payload[protocol_key] = relative
            previous_result = await self._reserve_broker_intent(request, action, client_order_id)
            if previous_result is not None:
                return previous_result
            execution = await connection.submit_trade(
                payload_type=PT_NEW_ORDER_REQ,
                payload=payload,
                on_sent=on_sent,
                on_ack=on_ack,
                on_fill=on_fill,
            )
            requested_lots = str(lots)
        elif action == "CLOSE_POSITION":
            position_id = int(str(request.get("position_id")))
            snapshot = await connection.reconcile(account_id)
            positions = snapshot.get("position") or []
            position = next(
                (row for row in positions if isinstance(row, dict) and int(row.get("positionId") or 0) == position_id),
                None,
            )
            if position is None:
                raise ValueError(f"cTrader position {position_id} was not found")
            trade_data = position.get("tradeData") if isinstance(position.get("tradeData"), dict) else {}
            symbol_id = int(trade_data.get("symbolId") or 0)
            full = await connection.get_full_symbol(account_id, symbol_id)
            full_rows = full.get("symbol") or []
            full_symbol = full_rows[0] if isinstance(full_rows, list) and full_rows else {}
            requested_protocol = CTraderAdapter._lots_to_protocol_volume(Decimal(str(request.get("qty") or 0)), full_symbol)
            existing_protocol = int(trade_data.get("volume") or requested_protocol)
            protocol_volume = min(existing_protocol, requested_protocol)
            previous_result = await self._reserve_broker_intent(request, action, client_order_id)
            if previous_result is not None:
                return previous_result
            execution = await connection.submit_trade(
                payload_type=PT_CLOSE_POSITION_REQ,
                payload={"ctidTraderAccountId": account_id, "positionId": position_id, "volume": protocol_volume},
                on_sent=on_sent,
                on_ack=on_ack,
                on_fill=on_fill,
            )
            requested_lots = str(request.get("qty") or 0)
        elif action == "RECONCILE_ACCOUNT":
            snapshot = await connection.reconcile(account_id)
            trader_payload, pnl_payload = await asyncio.gather(
                connection.get_trader(account_id),
                connection.get_position_unrealized_pnl(account_id),
            )
            normalized = await self._normalize_account_snapshot(
                connection,
                account_id=account_id,
                snapshot=snapshot,
                trader_payload=trader_payload,
                pnl_payload=pnl_payload,
                selected_account=selected,
            )
            return {
                "success": True,
                "status": "SYNCED",
                "message": "cTrader account snapshot received over persistent session",
                **normalized,
                "raw_response": {"provider": "CTRADER", "gateway": "PERSISTENT_SESSION"},
            }
        else:
            raise ValueError(f"Unsupported cTrader gateway action: {action}")

        order_payload = execution.get("order") if isinstance(execution.get("order"), dict) else {}
        deal = execution.get("deal") if isinstance(execution.get("deal"), dict) else {}
        position_payload = execution.get("position") if isinstance(execution.get("position"), dict) else {}
        broker_order_id, broker_position_id = CTraderAdapter._execution_ids(execution)
        executed_price = deal.get("executionPrice") or order_payload.get("executionPrice") or position_payload.get("price")
        execution_type = int(execution.get("executionType") or 0)
        filled = execution_type == 3
        partial = execution_type == 11
        self._last_order_at = _now()
        result = {
            "success": True,
            "status": "FILLED" if filled else "PARTIAL" if partial else "PLACED",
            "message": "cTrader order filled through persistent session" if filled else "cTrader order accepted; fill requires broker reconciliation",
            "broker_order_id": broker_order_id,
            "executed_price": str(executed_price) if executed_price not in (None, "") else None,
            "raw_response": {
                "provider": "CTRADER",
                "gateway": "PERSISTENT_SESSION",
                "environment": environment,
                "position_id": broker_position_id,
                "requested_lots": requested_lots,
                "protocol_volume": protocol_volume,
                "execution": _without_secret(execution),
            },
        }
        await self._complete_broker_intent(str(request["idempotency_key"]), result)
        return result

    async def _reserve_broker_intent(
        self, request: dict[str, Any], action: str, client_order_id: str,
    ) -> dict[str, Any] | None:
        """Commit an irreversible send reservation before the broker request."""
        key = str(request["idempotency_key"])
        async with async_session() as db:
            reservation = insert(LiveBrokerOrderIntent).values(
                idempotency_key=key,
                client_order_id=client_order_id,
                deployment_id=UUID(str(request["deployment_id"])),
                broker_account_id=UUID(str(request["broker_account_id"])),
                action=action,
                status="RESERVED",
            ).on_conflict_do_nothing(
                constraint="uq_live_broker_order_intents_key"
            ).returning(LiveBrokerOrderIntent.id)
            created = (await db.execute(reservation)).scalar_one_or_none()
            await db.commit()
            if created is not None:
                return None
            existing = (
                await db.execute(select(LiveBrokerOrderIntent).where(LiveBrokerOrderIntent.idempotency_key == key))
            ).scalar_one_or_none()
            if existing is not None and existing.status == "COMPLETED" and existing.result_json:
                return {**existing.result_json, "gateway_deduplicated": True}
        return {
            "success": False,
            "status": "PENDING",
            "message": "This broker order may already have been sent. Duplicate blocked; reconcile the account and review the order intent.",
            "raw_response": {"provider": "CTRADER", "gateway": "PERSISTENT_SESSION", "dedupe_state": "RESERVED"},
        }

    async def _complete_broker_intent(self, key: str, result: dict[str, Any]) -> None:
        async with async_session() as db:
            intent = (
                await db.execute(select(LiveBrokerOrderIntent).where(LiveBrokerOrderIntent.idempotency_key == key))
            ).scalar_one()
            intent.status = "COMPLETED"
            intent.result_json = result
            intent.updated_at = _now()
            await db.commit()

    async def _normalize_account_snapshot(
        self,
        connection: PersistentCTraderConnection,
        *,
        account_id: int,
        snapshot: dict[str, Any],
        trader_payload: dict[str, Any],
        pnl_payload: dict[str, Any],
        selected_account: dict[str, Any],
    ) -> dict[str, Any]:
        lights_payload = await connection.get_symbols(account_id)
        lights = lights_payload.get("symbol") or []
        names = {
            int(row.get("symbolId")): str(row.get("symbolName") or row.get("symbolId"))
            for row in lights if isinstance(row, dict) and row.get("symbolId") not in (None, "")
        }
        positions_raw = snapshot.get("position") or []
        orders_raw = snapshot.get("order") or []
        symbol_ids: set[int] = set()
        for row in list(positions_raw) + list(orders_raw):
            if not isinstance(row, dict):
                continue
            trade = row.get("tradeData") if isinstance(row.get("tradeData"), dict) else {}
            if trade.get("symbolId") not in (None, ""):
                symbol_ids.add(int(trade["symbolId"]))
        full_by_id: dict[int, dict[str, Any]] = {}
        for symbol_id in symbol_ids:
            try:
                response = await connection.get_full_symbol(account_id, symbol_id)
                rows = response.get("symbol") or []
                if isinstance(rows, list) and rows and isinstance(rows[0], dict):
                    full_by_id[symbol_id] = rows[0]
            except Exception:
                full_by_id[symbol_id] = {}

        positions: list[dict[str, Any]] = []
        for row in positions_raw if isinstance(positions_raw, list) else []:
            if not isinstance(row, dict):
                continue
            trade = row.get("tradeData") if isinstance(row.get("tradeData"), dict) else {}
            symbol_id = int(trade.get("symbolId") or 0)
            protocol_volume = int(trade.get("volume") or 0)
            positions.append({
                "success": True,
                "position_id": str(row.get("positionId") or ""),
                "broker_position_id": str(row.get("positionId") or ""),
                "symbol": names.get(symbol_id, str(symbol_id)),
                "side": "LONG" if int(trade.get("tradeSide") or 1) == 1 else "SHORT",
                "volume": str(CTraderAdapter._protocol_volume_to_lots(protocol_volume, full_by_id.get(symbol_id))),
                "protocol_volume": protocol_volume,
                "price_open": row.get("price"),
                "price_current": row.get("price"),
                "sl": row.get("stopLoss"),
                "tp": row.get("takeProfit"),
                "status": row.get("positionStatus"),
                "time": trade.get("openTimestamp"),
                "raw": _without_secret(row),
            })

        order_status = {1: "PLACED", 2: "FILLED", 3: "REJECTED", 4: "EXPIRED", 5: "CANCELLED"}
        orders: list[dict[str, Any]] = []
        for row in orders_raw if isinstance(orders_raw, list) else []:
            if not isinstance(row, dict):
                continue
            trade = row.get("tradeData") if isinstance(row.get("tradeData"), dict) else {}
            symbol_id = int(trade.get("symbolId") or 0)
            orders.append({
                "success": True,
                "order_id": str(row.get("orderId") or ""),
                "status": order_status.get(int(row.get("orderStatus") or 0), str(row.get("orderStatus") or "PLACED")),
                "symbol": names.get(symbol_id, str(symbol_id)),
                "side": "BUY" if int(trade.get("tradeSide") or 1) == 1 else "SELL",
                "price": row.get("executionPrice") or row.get("limitPrice") or row.get("stopPrice"),
                "executed_price": row.get("executionPrice"),
                "protocol_volume": trade.get("volume"),
                "client_order_id": row.get("clientOrderId"),
                "raw": _without_secret(row),
            })

        trader = trader_payload.get("trader") if isinstance(trader_payload.get("trader"), dict) else trader_payload
        money_digits = int(trader.get("moneyDigits") or 0) if isinstance(trader, dict) else 0
        balance = _money_value(trader.get("balance"), money_digits) if isinstance(trader, dict) else None
        pnl_digits = int(pnl_payload.get("moneyDigits") or money_digits or 0)
        unrealized = 0.0
        pnl_rows = pnl_payload.get("positionUnrealizedPnL") or []
        for row in pnl_rows if isinstance(pnl_rows, list) else []:
            if isinstance(row, dict):
                value = _money_value(row.get("netUnrealizedPnL"), pnl_digits)
                unrealized += float(value or 0)
        equity = float(balance) + unrealized if balance is not None else None
        return {
            "orders": orders,
            "positions": positions,
            "account_info": {
                "connected": True,
                "message": "cTrader account financial state refreshed over persistent session",
                "account_login": str(trader.get("traderLogin") or account_id) if isinstance(trader, dict) else str(account_id),
                "server": f"cTrader Open API ({connection.environment.lower()})",
                "balance": balance,
                "equity": equity,
                "unrealized_pnl": unrealized,
                "currency": selected_account.get("currency") or "USD",
                "orders_enabled": bool(selected_account.get("trading_enabled", True)),
            },
        }

    async def _health_loop(self) -> None:
        while not self._stop.is_set():
            connection_health = ctrader_connection_manager.health()
            degraded = any(feed.watchdog_attempts for feed in self.feeds.values()) or bool(self._last_error)
            await self.bus.heartbeat(
                "live_market_worker",
                self.worker_id,
                {
                    "status": "DEGRADED" if degraded else "HEALTHY",
                    "feeds": len(self.feeds),
                    "feed_deployments": [str(deployment_id) for deployment_id in self.feeds],
                    "candle_queue_depth": self._candle_queue.qsize(),
                    "last_market_event_at": self._last_market_event_at.isoformat() if self._last_market_event_at else None,
                    "last_candle_published_at": self._last_candle_published_at.isoformat() if self._last_candle_published_at else None,
                    "last_order_at": self._last_order_at.isoformat() if self._last_order_at else None,
                    "last_error": self._last_error,
                    "connections": connection_health,
                },
            )
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=5)
            except asyncio.TimeoutError:
                pass


async def main() -> None:
    if not (
        settings.live_event_pipeline_enabled
        and settings.live_market_worker_enabled
        and settings.ctrader_persistent_connection_enabled
    ):
        logger.warning("Live market worker is idle because its event-pipeline flags are disabled")
        while True:
            await asyncio.sleep(3600)
    if not await redis_manager.initialize():
        raise RuntimeError("Redis is required by live_market_worker")
    worker = LiveMarketWorker(redis_manager.client)
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
