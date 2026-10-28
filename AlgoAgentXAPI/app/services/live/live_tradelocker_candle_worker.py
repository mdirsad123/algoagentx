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

from ...core.config import settings
from ...core.logging_config import configure_logging
from ...core.redis_manager import redis_manager
from ...db.models import BrokerAccount, BrokerProvider, LiveMarketCandle, StrategyDeployment
from ...db.session import async_session
from .broker_candle_service import refresh_deployment_candles
from .live_event_bus import LiveEventBus, worker_identity
from .live_latency_trace_service import LiveLatencyTraceService, deterministic_trace_id
from .runner_scheduler import latest_expected_closed_candle_open, parse_timeframe_to_seconds
from .candle_catchup import plan_recovery, required_broker_fetch_bars, utc
from .candle_poll_schedule import next_poll_delay
from .candle_worker_health import collector_status

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
        # The caller's snapshot predates the awaited deployment lookup. Evaluate
        # readiness using the current UTC time, including boundary crossings.
        now = datetime.now(timezone.utc)
        opened, close_at = expected_closed_open(now, tf)
        if now < close_at + timedelta(seconds=FETCH_GRACE_SECONDS):
            return {
                "skip": "grace",
                "timeframe": tf,
                "open": opened.isoformat(),
                "retry_at": (
                    close_at + timedelta(seconds=FETCH_GRACE_SECONDS)
                ).isoformat(),
            }
        stored = (await db.execute(select(func.max(LiveMarketCandle.candle_time)).where(
            LiveMarketCandle.deployment_id == deployment_id, LiveMarketCandle.is_closed.is_(True)))).scalar_one_or_none()
        if stored and stored.tzinfo is None: stored = stored.replace(tzinfo=timezone.utc)
        if stored is not None and stored >= opened:
            return {'skip': 'already_stored', 'open': opened.isoformat(), 'timeframe': tf}
        broker_id = deployment.broker_account_id
        symbol = str(deployment.broker_symbol or deployment.instrument)
        environment = str(deployment.mode or 'DEMO').upper()
        # Avoid keeping a read transaction open while waiting on external REST.
        await db.rollback()
        started = time.monotonic()
        log.info('TRADELOCKER_FETCH_START deployment=%s expected_open=%s last_stored=%s',
                 deployment_id, opened.isoformat(), stored.isoformat() if stored else None)
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
        return {'ready': fresh, 'open': opened.isoformat(), 'lag_s': lag, 'duration_s': elapsed, 'timeframe': tf}


async def _repair_pending_gap(deployment_id: UUID) -> dict:
    """Attempt a bounded broker refill for the FIRST unevaluated M5 candle.

    Never invent OHLCV, advance the strategy cursor or place orders. A genuine
    exchange/session closure can legitimately have no such broker candle;
    leave it visible for review rather than synthesizing a false bar.
    """
    async with async_session() as db:
        deployment = (await db.execute(select(StrategyDeployment).where(
            StrategyDeployment.id == deployment_id))).scalar_one_or_none()
        if not deployment or not deployment.last_processed_candle_time:
            return {'status': 'no_cursor'}
        # Guard this optional repair against affecting non-M5 strategies.
        if str(deployment.timeframe or '').upper() not in {'M5', '5M', '5MIN'}:
            return {'status': 'other_timeframe'}
        previous = utc(deployment.last_processed_candle_time)
        newest = (await db.execute(select(func.max(LiveMarketCandle.candle_time)).where(
            LiveMarketCandle.deployment_id == deployment_id,
            LiveMarketCandle.timeframe == deployment.timeframe,
            LiveMarketCandle.is_closed.is_(True),
        ))).scalar_one_or_none()
        if newest is None or utc(newest) <= previous:
            return {'status': 'no_backlog'}
        first_pending = (await db.execute(select(func.min(LiveMarketCandle.candle_time)).where(
            LiveMarketCandle.deployment_id == deployment_id,
            LiveMarketCandle.timeframe == deployment.timeframe,
            LiveMarketCandle.is_closed.is_(True),
            LiveMarketCandle.candle_time > previous,
        ))).scalar_one_or_none()
        plan = plan_recovery(last_processed=previous, first_pending=first_pending,
                             newest=newest, timeframe_seconds=300)
        if plan.action != 'WAIT_FOR_BACKFILL':
            return {'status': 'sequence_ready', 'pending_bars': plan.pending_bars}
        count = required_broker_fetch_bars(newest=newest, previous=previous,
                                           timeframe_seconds=300, limit=120)
        if count is None:
            log.error('TRADELOCKER_GAP_BEYOND_LOOKBACK deployment=%s missing_open=%s '
                      'last_processed=%s newest=%s no_cursor_change=true',
                      deployment_id, plan.missing_open, previous, newest)
            return {'status': 'older_than_max_lookback'}
        # Release read transaction before making an external REST call.
        await db.rollback()
        try:
            result = await refresh_deployment_candles(db, deployment_id, count=count)
        except Exception as exc:
            log.warning('TRADELOCKER_GAP_BACKFILL_ERROR deployment=%s missing=%s error=%s',
                        deployment_id, plan.missing_open, str(exc)[:200])
            return {'status': 'refetch_error'}
        present = (await db.execute(select(func.count(LiveMarketCandle.id)).where(
            LiveMarketCandle.deployment_id == deployment_id,
            LiveMarketCandle.timeframe == deployment.timeframe,
            LiveMarketCandle.is_closed.is_(True),
            LiveMarketCandle.candle_time == plan.missing_open,
        ))).scalar_one()
        if int(present or 0):
            log.warning('TRADELOCKER_GAP_BACKFILLED deployment=%s recovered_open=%s requested_bars=%s '
                        'upserted=%s', deployment_id, plan.missing_open, count,
                        result.get('upserted_count'))
            return {'status': 'recovered', 'candle': plan.missing_open.isoformat()}
        log.warning('TRADELOCKER_GAP_UNRESOLVED deployment=%s missing_open=%s requested_bars=%s '
                    'broker_did_not_return_missing_bar=true', deployment_id, plan.missing_open, count)
        return {'status': 'not_in_broker_history'}


async def _heartbeat(stop: asyncio.Event, stats: dict):
    identifier = worker_identity('tradelocker-candle')
    while not stop.is_set():
        try:
            if not redis_manager.is_available:
                await redis_manager.ensure_connected()
            client = redis_manager.client
            if client is not None:
                # Process liveness cannot establish market-data freshness.
                # An unfetched candle must not produce perpetual STARTING status.
                status = collector_status(stats, datetime.now(timezone.utc))
                await LiveEventBus(client).heartbeat('live_tradelocker_candle_worker', identifier,
                    {'status': status, 'mode': 'TRADELOCKER_REST_POLL', **stats})
        except asyncio.CancelledError: raise
        except Exception: log.exception('TradeLocker heartbeat unavailable')
        try: await asyncio.wait_for(stop.wait(), 5)
        except asyncio.TimeoutError: pass


async def _run(stop: asyncio.Event, stats: dict):
    next_attempt: dict[UUID, float] = {}
    next_gap_repair: dict[UUID, float] = {}
    missing_streak: dict[UUID, int] = {}
    missing_open: dict[UUID, str] = {}
    cached_deployments: list[UUID] = []
    next_registry_scan = 0.0
    last_scan_log_at = -1e20
    registry_refresh = max(5, int(getattr(settings, 'live_tradelocker_registry_refresh_seconds', 15)))
    while not stop.is_set():
        try:
            monotonic_now = time.monotonic()
            if monotonic_now >= next_registry_scan:
                cached_deployments = await asyncio.wait_for(_deployment_ids(), timeout=20.0)
                stats['last_registry_scan_at'] = datetime.now(timezone.utc).isoformat()
                if time.monotonic() - last_scan_log_at >= 60 or len(cached_deployments) != stats.get('deployments'):
                    log.info('TRADELOCKER_REGISTRY_SCAN matched=%s deployments=%s',
                             len(cached_deployments), ','.join(str(d) for d in cached_deployments))
                    last_scan_log_at = time.monotonic()
                next_registry_scan = time.monotonic() + registry_refresh
                stats['deployments'] = len(cached_deployments)
                for mapping in (next_attempt, next_gap_repair, missing_streak, missing_open):
                    for stale in set(mapping).difference(cached_deployments):
                        mapping.pop(stale, None)
            for deployment_id in cached_deployments:
                # Gap history is repaired independently and no more than once
                # per 5 minutes; it must not trigger a rapid polling storm.
                if bool(getattr(settings, 'live_tradelocker_gap_backfill_enabled', False)) and \
                        time.monotonic() >= next_gap_repair.get(deployment_id, 0):
                    next_gap_repair[deployment_id] = time.monotonic() + 300.0
                    try:
                        await _repair_pending_gap(deployment_id)
                    except asyncio.CancelledError:
                        raise
                    except Exception:
                        log.exception('TRADELOCKER_GAP_REPAIR_FAILED deployment=%s', deployment_id)
                if time.monotonic() < next_attempt.get(deployment_id, 0):
                    continue
                try:
                    now = datetime.now(timezone.utc)
                    stats['last_poll_attempt_at'] = datetime.now(timezone.utc).isoformat()
                    log.info('TRADELOCKER_POLL_ATTEMPT deployment=%s at=%s', deployment_id, stats['last_poll_attempt_at'])
                    # Bound DB + broker HTTP waits; no blocking of the whole collector forever.
                    result = await asyncio.wait_for(_poll_one(deployment_id, now), timeout=60.0)
                    reason = str(result.get('skip') or '')
                    stats['last_poll_result_at'] = datetime.now(timezone.utc).isoformat()
                    stats['last_skip_reason'] = reason or None
                    # A grace/inactive result performed no data check. It must
                    # not clear a real failure or renew collector ownership.
                    if reason not in {'grace', 'inactive'}:
                        stats['last_poll_completed_at'] = stats['last_poll_result_at']
                        stats['last_error'] = None
                        if not reason:
                            stats['last_successful_broker_response_at'] = stats['last_poll_result_at']
                    ready = bool(result.get('ready'))
                    no_data = not ready and reason not in {'grace', 'already_stored', 'inactive'}
                    if reason:
                        log.info('TRADELOCKER_POLL_SKIP deployment=%s reason=%s expected=%s',
                                 deployment_id, reason, result.get('open'))
                    if no_data:
                        # Reopening can publish after the idle boundary probe.
                        # Renew only the configured bounded retry budget when
                        # the expected closed-candle bucket actually advances.
                        bucket = str(result.get('open') or '')
                        if bucket and missing_open.get(deployment_id) != bucket:
                            missing_streak.pop(deployment_id, None)
                            missing_open[deployment_id] = bucket
                        missing_streak[deployment_id] = missing_streak.get(deployment_id, 0) + 1
                    elif reason != 'grace':
                        missing_streak.pop(deployment_id, None)
                        missing_open.pop(deployment_id, None)
                    if reason == 'grace':
                        # Honor the attempted boundary even when handling the
                        # skip after its grace deadline; never defer it one M5.
                        retry_at = datetime.fromisoformat(result['retry_at'])
                        wait_s = next_poll_delay(
                            datetime.now(timezone.utc), str(result.get('timeframe') or 'M5'),
                            skip_reason=reason, retry_at=retry_at,
                            grace_seconds=FETCH_GRACE_SECONDS,
                        )
                        next_attempt[deployment_id] = time.monotonic() + wait_s
                        log.info('TRADELOCKER_GRACE_RETRY deployment=%s retry_at=%s delay_s=%.3f',
                                 deployment_id, retry_at.isoformat(), wait_s)
                    elif bool(getattr(settings, 'live_tradelocker_boundary_poll_enabled', True)):
                        # For multi-timeframe deployments, use the selected
                        # timeframe rather than a hard-coded M5 interval.
                        # _poll_one returns the timeframe to avoid guessing.
                        tf = str(result.get('timeframe') or 'M5')
                        wait_s = next_poll_delay(
                            datetime.now(timezone.utc), tf, ready=ready,
                            empty_streak=missing_streak.get(deployment_id, 0),
                            fast_retries=int(getattr(settings, 'live_tradelocker_fast_empty_retries', 2)),
                            fast_retry_seconds=float(getattr(settings, 'live_tradelocker_empty_retry_seconds', 8)),
                            grace_seconds=FETCH_GRACE_SECONDS, skip_reason=reason,
                            idle_grace_seconds=int(getattr(settings, 'live_tradelocker_idle_boundary_grace_seconds', 10)),
                        )
                        if no_data and missing_streak[deployment_id] == int(getattr(settings, 'live_tradelocker_fast_empty_retries', 2)) + 1:
                            log.info('TRADELOCKER_NO_NEW_CANDLE_BACKOFF deployment=%s timeframe=%s '
                                     'empty_attempts=%s next_poll_in_s=%.1f no_session_hours_assumed=true',
                                     deployment_id, tf, missing_streak[deployment_id], wait_s)
                        next_attempt[deployment_id] = time.monotonic() + wait_s
                    else:
                        next_attempt[deployment_id] = time.monotonic() + (RETRY_SECONDS if not ready else 1.0)
                    if ready:
                        stats['last_candle_at'] = datetime.now(timezone.utc).isoformat()
                        stats['last_error'] = None
                        stats['latest_ingestion_latency_seconds'] = result.get('lag_s')
                        stats['market_data_state'] = 'NEW_CANDLE'
                    elif no_data:
                        stats['market_data_state'] = 'NO_NEW_CANDLE'
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    log.exception('TradeLocker candle fetch failed deployment=%s', deployment_id)
                    stats['last_error'] = f'{type(exc).__name__}: {str(exc)[:180]}'
                    stats['last_poll_error_at'] = datetime.now(timezone.utc).isoformat()
                    next_attempt[deployment_id] = time.monotonic() + RETRY_SECONDS
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception('TradeLocker polling scan failed')
            next_registry_scan = time.monotonic() + RETRY_SECONDS
        # Sleep until the next scheduled wakeup, not one second at a time.
        now_mono = time.monotonic()
        deadlines = [next_registry_scan] + [next_attempt.get(d, now_mono + registry_refresh) for d in cached_deployments]
        if bool(getattr(settings, 'live_tradelocker_gap_backfill_enabled', False)):
            deadlines += [next_gap_repair.get(d, now_mono + registry_refresh) for d in cached_deployments]
        pause = min(30.0, max(0.1, min(deadlines, default=now_mono + registry_refresh) - now_mono))
        try:
            await asyncio.wait_for(stop.wait(), pause)
        except asyncio.TimeoutError:
            pass


async def main():
    await redis_manager.initialize()
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try: loop.add_signal_handler(sig, stop.set)
        except NotImplementedError: pass
    stats = {'deployments': 0, 'last_error': None, 'started_at': datetime.now(timezone.utc).isoformat()}
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
