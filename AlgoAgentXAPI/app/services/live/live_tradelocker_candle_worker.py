"""Independent TradeLocker candle ingestion (never runs a strategy or places orders).

Exactly one replica. Broker history REST availability can vary; 2s is the earliest
attempt, not a promise that TradeLocker publishes a closed candle by +2s.
"""
from __future__ import annotations

import asyncio
import logging
import signal
import time
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select

from ...core.logging_config import configure_logging
from ...core.redis_manager import redis_manager
from ...db.models import BrokerAccount, BrokerProvider, LiveMarketCandle, StrategyDeployment
from ...db.session import async_session
from .broker_candle_service import refresh_deployment_candles
from .live_event_bus import LiveEventBus, worker_identity
from .live_latency_trace_service import LiveLatencyTraceService, deterministic_trace_id
from .runner_scheduler import latest_expected_closed_candle_open, parse_timeframe_to_seconds

configure_logging()
log = logging.getLogger(__name__)
FETCH_GRACE_SECONDS = 2
RETRY_SECONDS = 5
IDLE_SCAN_SECONDS = 1
MAX_DEPLOYMENTS = 50


def expected_closed_open(now: datetime, timeframe: str):
    opened = latest_expected_closed_candle_open(now, timeframe)
    close_at = opened + timedelta(seconds=parse_timeframe_to_seconds(timeframe))
    return opened, close_at


async def _deployment_ids():
    async with async_session() as db:
        provider = func.upper(func.coalesce(BrokerProvider.code, BrokerAccount.broker_code, BrokerAccount.broker_name, ''))
        stmt = (
            select(StrategyDeployment.id)
            .join(BrokerAccount, BrokerAccount.id == StrategyDeployment.broker_account_id)
            .outerjoin(BrokerProvider, BrokerProvider.id == BrokerAccount.broker_provider_id)
            .where(StrategyDeployment.status == 'RUNNING', StrategyDeployment.auto_runner_enabled.is_(True),
                   BrokerAccount.status == 'CONNECTED', provider == 'TRADELOCKER')
            .order_by(StrategyDeployment.created_at.asc()).limit(MAX_DEPLOYMENTS)
        )
        return list((await db.execute(stmt)).scalars().all())


async def _poll_one(deployment_id: UUID, now: datetime) -> dict:
    async with async_session() as db:
        deployment = (await db.execute(select(StrategyDeployment).where(StrategyDeployment.id == deployment_id))).scalar_one_or_none()
        if not deployment or deployment.status != 'RUNNING' or not deployment.auto_runner_enabled:
            return {'skip': 'inactive'}
        tf = str(deployment.timeframe or 'M5')
        opened, close_at = expected_closed_open(now, tf)
        if now < close_at + timedelta(seconds=FETCH_GRACE_SECONDS):
            return {'skip': 'grace'}
        stored = (await db.execute(select(func.max(LiveMarketCandle.candle_time)).where(
            LiveMarketCandle.deployment_id == deployment_id, LiveMarketCandle.is_closed.is_(True)))).scalar_one_or_none()
        if stored and stored.tzinfo is None: stored = stored.replace(tzinfo=timezone.utc)
        if stored is not None and stored >= opened:
            return {'skip': 'already_stored', 'open': opened.isoformat()}
        broker_id = deployment.broker_account_id
        symbol = str(deployment.broker_symbol or deployment.instrument)
        environment = str(deployment.mode or 'DEMO').upper()
        # Avoid keeping a read transaction open while waiting on external REST.
        await db.rollback()
        started = time.monotonic()
        result = await refresh_deployment_candles(db, deployment_id, count=12)
        elapsed = round(time.monotonic() - started, 3)
        new_open = result.get('latest_candle_time')
        if new_open and new_open.tzinfo is None: new_open = new_open.replace(tzinfo=timezone.utc)
        fresh = bool(new_open is not None and new_open >= opened)
        if fresh:
            # Best-effort telemetry must never delay/fail market ingestion.
            try:
                client = redis_manager.client
                trace = LiveLatencyTraceService(client if redis_manager.is_available else None)
                if trace.enabled:
                    trace_id = deterministic_trace_id(deployment_id, new_open)
                    await trace.start_trace(
                        trace_id=trace_id, deployment_id=str(deployment_id),
                        broker_account_id=str(broker_id) if broker_id else None,
                        candle_open_time=new_open,
                        expected_close_at=new_open + timedelta(seconds=parse_timeframe_to_seconds(tf)),
                        provider='TRADELOCKER', environment=environment,
                        symbol=symbol, timeframe=tf, source='REST_POLL',
                        broker_event_received_at=datetime.now(timezone.utc),
                    )
                    await trace.mark(trace_id, 't3', status='CANDLE_DB_COMMITTED')
                    async with async_session() as metrics_db:
                        await trace.persist(metrics_db, trace_id)
                        await metrics_db.commit()
            except Exception:
                log.exception('Trace persistence failed (noncritical) for %s', deployment_id)
        lag = result.get('ingestion_latency_seconds')
        log.info('TradeLocker candle fetch deployment=%s expected=%s stored=%s ready=%s duration_s=%s ingest_lag_s=%s',
                 deployment_id, opened.isoformat(), str(new_open), fresh, elapsed, lag)
        return {'ready': fresh, 'open': opened.isoformat(), 'lag_s': lag, 'duration_s': elapsed}


async def _heartbeat(stop: asyncio.Event, stats: dict):
    identifier = worker_identity('tradelocker-candle')
    while not stop.is_set():
        try:
            if not redis_manager.is_available:
                await redis_manager.ensure_connected()
            client = redis_manager.client
            if client is not None:
                # A live container is not proof of fresh market data.
                last_candle = stats.get('last_candle_at')
                try:
                    last_dt = datetime.fromisoformat(str(last_candle)) if last_candle else None
                    stale = bool(last_dt and (datetime.now(timezone.utc) - last_dt).total_seconds() > 650)
                except (TypeError, ValueError):
                    stale = False
                status = ('DEGRADED' if stats.get('last_error') or stale else
                          'STARTING' if stats.get('deployments') and not last_candle else 'HEALTHY')
                await LiveEventBus(client).heartbeat('live_tradelocker_candle_worker', identifier,
                    {'status': status, 'mode': 'TRADELOCKER_REST_POLL', **stats})
        except asyncio.CancelledError: raise
        except Exception: log.exception('TradeLocker heartbeat unavailable')
        try: await asyncio.wait_for(stop.wait(), 5)
        except asyncio.TimeoutError: pass


async def _run(stop: asyncio.Event, stats: dict):
    next_attempt: dict[UUID, float] = {}
    while not stop.is_set():
        started = time.monotonic()
        try:
            ids = await _deployment_ids()
            stats['deployments'] = len(ids)
            for stale in set(next_attempt).difference(ids): next_attempt.pop(stale, None)
            now = datetime.now(timezone.utc)
            for deployment_id in ids:
                if time.monotonic() < next_attempt.get(deployment_id, 0): continue
                try:
                    result = await _poll_one(deployment_id, now)
                    next_attempt[deployment_id] = time.monotonic() + (RETRY_SECONDS if not result.get('ready') else 1)
                    if result.get('ready'):
                        stats['last_candle_at'] = datetime.now(timezone.utc).isoformat()
                        stats['last_error'] = None
                        stats['latest_ingestion_latency_seconds'] = result.get('lag_s')
                except asyncio.CancelledError: raise
                except Exception as exc:
                    log.exception('TradeLocker candle fetch failed deployment=%s', deployment_id)
                    stats['last_error'] = f'{type(exc).__name__}: {str(exc)[:180]}'
                    next_attempt[deployment_id] = time.monotonic() + RETRY_SECONDS
        except asyncio.CancelledError: raise
        except Exception:
            log.exception('TradeLocker polling scan failed')
        try: await asyncio.wait_for(stop.wait(), max(0.1, IDLE_SCAN_SECONDS - (time.monotonic()-started)))
        except asyncio.TimeoutError: pass


async def main():
    await redis_manager.initialize()
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try: loop.add_signal_handler(sig, stop.set)
        except NotImplementedError: pass
    stats = {'deployments': 0, 'last_error': None}
    pulse = asyncio.create_task(_heartbeat(stop, stats))
    runner = asyncio.create_task(_run(stop, stats))
    log.warning('TradeLocker independent candle polling started; exactly one replica only')
    try:
        done, _ = await asyncio.wait({runner, asyncio.create_task(stop.wait())}, return_when=asyncio.FIRST_COMPLETED)
        if runner in done and not stop.is_set():
            raise RuntimeError('Candle fetch task exited unexpectedly') from runner.exception()
    finally:
        stop.set()
        for task in (runner, pulse): task.cancel()
        await asyncio.gather(runner, pulse, return_exceptions=True)
        await redis_manager.close()


if __name__ == '__main__':
    asyncio.run(main())
