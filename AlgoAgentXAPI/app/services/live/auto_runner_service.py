from __future__ import annotations

import asyncio
import os
import logging
import time
from datetime import timedelta
from typing import Any, Callable
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select, update, or_
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import settings
from ...db.models import BrokerAccount, BrokerProvider, LiveMarketCandle, LiveTradeLog, StrategyDeployment
from ...db.session import async_session
from .broker_candle_service import get_latest_closed_candles, refresh_deployment_candles
from .runner_scheduler import calculate_next_runner_after_candle, calculate_next_runner_at, ensure_utc, latest_expected_closed_candle_open, parse_timeframe_to_seconds, utc_now
from .strategy_runner import run_strategy_for_deployment
from ..brokers.factory import get_broker_code
from .live_latency_trace_service import LiveLatencyTraceService, deterministic_trace_id
from .live_event_bus import LiveEventBus
from ...core.redis_manager import redis_manager
from .trading_safety import check_platform_mode_allowed, get_platform_trading_settings
from .runner_cache import warmup_gate, history_ready_cache, eligible_scan_cache
from .candle_catchup import plan_recovery, required_broker_fetch_bars
from .candle_worker_health import collector_owns_broker_ingestion
from .deployment_lock import deployment_worker_index

logger = logging.getLogger(__name__)
_RUNNER_SCAN_LOCK = asyncio.Lock()
# Per-process retry counter keyed by deployment + expected closed candle OPEN time.
# It limits active broker refreshes to 20 one-second attempts per candle while
# still allowing the scheduler to notice a candle already ingested by another path.
_CANDLE_RETRY_ATTEMPTS: dict[tuple[str, str], int] = {}
# Throttle a known missing-bar log instead of flooding every scheduler tick.
_GAP_WAIT_LOG_AT: dict[str, float] = {}
# Bounded, per-process DEMO history-refetch budget. A reboot restarts the
# attempts but cannot authorize an order or skip a candle by itself.
# Only successful broker-history calls count toward a no-bar cold re-seed.
_DEMO_GAP_RECOVERY: dict[str, dict[str, Any]] = {}
_DEMO_GAP_MAX_FETCH_ATTEMPTS = 3
_DEMO_GAP_FETCH_SPACING_SECONDS = 12.0
_DEMO_GAP_RESEED_RETRY_SECONDS = 300.0
# Only dedicated TradeLocker+DB-backed runners use this idle throttle.
# Never block Run Once, other brokers or a new M5 candle boundary.
_TRADELOCKER_NO_CANDLE_IDLE: dict[str, tuple[str, object, int]] = {}


def _tradelocker_idle_probe_time(now, timeframe: str, misses: int):
    """A few short DB-only probes, then next closed-candle boundary."""
    from .candle_poll_schedule import runner_no_data_probe_time
    return runner_no_data_probe_time(
        now, timeframe, misses,
        fast_probes=int(getattr(settings, 'live_runner_dedicated_candle_fast_probes', 3)),
        probe_seconds=int(getattr(settings, 'live_runner_dedicated_candle_probe_seconds', 5)),
        run_delay_seconds=STRATEGY_RUN_DELAY_SECONDS,
        max_idle_probe_seconds=int(getattr(settings, 'live_runner_dedicated_candle_max_idle_probe_seconds', 30)),
    )


async def _wait_for_dedicated_tradelocker_candle(db, deployment, expected_open, now, result):
    key = str(deployment.id)
    stamp = expected_open.isoformat()
    earlier = _TRADELOCKER_NO_CANDLE_IDLE.get(key)
    misses = earlier[2] + 1 if earlier and earlier[0] == stamp else 1
    due_at = _tradelocker_idle_probe_time(now, str(deployment.timeframe or 'M5'), misses)
    _TRADELOCKER_NO_CANDLE_IDLE[key] = (stamp, due_at, misses)
    result.update(skipped=True, reason='WAITING_FOR_NEW_TRADELOCKER_CANDLE',
                  next_run_at=due_at.isoformat())
    # UI should show the next meaningful poll, not a 1-second retry storm.
    # Log only the first miss and the boundary-backoff transition.
    fast_probes = max(0, int(getattr(settings, 'live_runner_dedicated_candle_fast_probes', 3)))
    if misses == 1 or misses == fast_probes:
        logger.info('RUNNER_NO_NEW_CANDLE_IDLE deployment=%s expected_open=%s '
                    'db_checks=%s next_db_probe_at=%s', key, stamp, misses, due_at.isoformat())
    deployment.next_run_at = due_at
    await db.commit()
    return result



def _sequential_monitor_enabled(deployment: StrategyDeployment, *, force: bool) -> bool:
    # Chronological catch-up for every M5 deployment. This does
    # not turn strategies incremental: unsupported code uses FULL_HISTORY.
    # Recovery of older bars is state-only, never a delayed broker order.
    return (str(deployment.mode or '').upper() in {'DEMO', 'LIVE', 'PAPER'}
            and str(deployment.timeframe or '').upper() in {'M5', '5M'})

# Live timing knobs — change these values only when you want to tune timing.
MARKET_DATA_FETCH_DELAY_SECONDS = 1   # start fetching closed candle after +1s
STRATEGY_RUN_DELAY_SECONDS = 2        # first strategy run eligibility after +2s
CANDLE_RETRY_DELAY_SECONDS = 1        # retry missing candle every 1s
MAX_CANDLE_RETRY_ATTEMPTS = 20

def _normalize_dt(value: Any):
    if value is None:
        return None
    if hasattr(value, "tzinfo"):
        return ensure_utc(value)
    text_value = str(value).strip()
    if not text_value:
        return None
    if text_value.endswith("Z"):
        text_value = text_value[:-1] + "+00:00"
    try:
        from datetime import datetime, timezone
        parsed = datetime.fromisoformat(text_value)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except Exception:
        return None


async def _write_log(db: AsyncSession, deployment: StrategyDeployment, event_type: str, message: str, level: str = "INFO", metadata: dict[str, Any] | None = None) -> None:
    db.add(LiveTradeLog(
        deployment_id=deployment.id,
        user_id=deployment.user_id,
        event_type=event_type,
        level=level,
        message=message,
        metadata_json=metadata or {},
    ))


def _broker_delay(deployment: StrategyDeployment) -> int:
    # Market-data fetch starts shortly after candle close.
    return MARKET_DATA_FETCH_DELAY_SECONDS


def _strategy_run_delay(deployment: StrategyDeployment) -> int:
    # Strategy execution is intentionally delayed separately from candle fetching.
    # Change STRATEGY_RUN_DELAY_SECONDS above (for example 5 -> 10 or 5 -> 1).
    return STRATEGY_RUN_DELAY_SECONDS


def _retry_delay(deployment: StrategyDeployment) -> int:
    # Retry missing candle data independently of strategy delay.
    return CANDLE_RETRY_DELAY_SECONDS


def _eligible_expected_closed_candle_open(deployment: StrategyDeployment, now):
    """Return (expected_open, fetch_eligible_at, strategy_eligible_at).

    Example M5 with defaults:
      candle 11:55 closes at 12:00
      market-data fetch may start at 12:00:01
      strategy may run from 12:00:05
    """
    expected_open = latest_expected_closed_candle_open(now, str(deployment.timeframe or "M5"))
    timeframe_seconds = __import__(
        "app.services.live.runner_scheduler",
        fromlist=["parse_timeframe_to_seconds"],
    ).parse_timeframe_to_seconds(str(deployment.timeframe or "M5"))

    candle_close_at = expected_open + timedelta(seconds=timeframe_seconds)
    fetch_eligible_at = candle_close_at + timedelta(seconds=_broker_delay(deployment))
    strategy_eligible_at = candle_close_at + timedelta(seconds=_strategy_run_delay(deployment))
    return expected_open, fetch_eligible_at, strategy_eligible_at


def _next_scheduled_run(deployment: StrategyDeployment, now):
    # UI/strategy schedule refers to strategy execution time, not first market-data fetch.
    return calculate_next_runner_at(
        now,
        str(deployment.timeframe or "M5"),
        _strategy_run_delay(deployment),
    )


async def _schedule_retry(db: AsyncSession, deployment: StrategyDeployment, now, reason: str, result: dict[str, Any]) -> dict[str, Any]:
    retry_at = now + timedelta(seconds=_retry_delay(deployment))
    deployment.next_run_at = retry_at
    deployment.last_runner_at = now
    deployment.last_heartbeat_at = now
    result.update(skipped=True, reason=reason, next_run_at=retry_at.isoformat())
    await _write_log(db, deployment, "AUTO_RUNNER_RETRY_SCHEDULED", reason, "WARNING", {"next_run_at": retry_at.isoformat()})
    await db.commit()
    return result


async def _try_demo_gap_recovery(
    db: AsyncSession, deployment: StrategyDeployment, *, recovery, latest_closed_candle_time,
    interval_s: int,
) -> dict[str, Any] | None:
    """Try three broker refetches; optionally cold-reseed an audited DEMO adapter.

    No synthetic bars, no jump of an unverified cursor, and no historical orders.
    Small holes are eligible only after three broker refetches and cold re-seeding; LIVE and unregistered adapters stay blocked.
    """
    deployment_id = deployment.id
    key = str(deployment_id)
    if not recovery.missing_open or recovery.pending_bars < 2:
        return None
    broker = (await db.execute(select(BrokerAccount).where(
        BrokerAccount.id == deployment.broker_account_id))).scalar_one_or_none()
    if broker is None or get_broker_code(broker) != 'TRADELOCKER':
        return None

    missing_key = recovery.missing_open.isoformat()
    state = _DEMO_GAP_RECOVERY.get(key)
    if state is None or state['missing'] != missing_key:
        state = {'missing': missing_key, 'attempts': 0, 'successes': 0,
                 'last_attempt': -1e12, 'last_reseed': -1e12, 'reseed_failures': 0}
        _DEMO_GAP_RECOVERY[key] = state
    moment = time.monotonic()
    if state['attempts'] < _DEMO_GAP_MAX_FETCH_ATTEMPTS:
        if moment - state['last_attempt'] < _DEMO_GAP_FETCH_SPACING_SECONDS:
            return None
        count = required_broker_fetch_bars(
            newest=latest_closed_candle_time,
            previous=deployment.last_processed_candle_time,
            timeframe_seconds=interval_s, margin=20, limit=2000,
        )
        if count is None:
            logger.error('RUNNER_DEMO_GAP_TOO_OLD deployment=%s missing=%s manual_review_required=true',
                         deployment_id, missing_key)
            return None
        state['attempts'] += 1
        state['last_attempt'] = moment
        # Close the read transaction before the broker network request.
        await db.rollback()
        try:
            refresh = await refresh_deployment_candles(db, deployment_id, count=count)
            state['successes'] += 1
            logger.warning('RUNNER_DEMO_GAP_FETCH deployment=%s missing=%s attempt=%s/%s '
                           'broker_history_succeeded=true requested=%s upserted=%s',
                           deployment_id, missing_key, state['attempts'],
                           _DEMO_GAP_MAX_FETCH_ATTEMPTS, count, refresh.get('upserted_count'))
        except Exception as exc:
            # A network/broker failure cannot establish that the candle did not
            # exist. Do not promote such failures into a skip authorization.
            await db.rollback()
            logger.error('RUNNER_DEMO_GAP_FETCH_ERROR deployment=%s missing=%s attempt=%s/%s error=%s',
                         deployment_id, missing_key, state['attempts'],
                         _DEMO_GAP_MAX_FETCH_ATTEMPTS, str(exc)[:200])
        return None

    if state['successes'] < 2:
        # No reliable history evidence: remain blocked, not a blind skip.
        return None
    if state['reseed_failures'] >= 2 or moment - state['last_reseed'] < _DEMO_GAP_RESEED_RETRY_SECONDS:
        return None
    # Even a short hole is replayed only after attempts fail. Require two
    # actually published consecutive broker M5 candles before cold re-seeding.
    minimum_missing = max(1, int(getattr(settings, 'live_runner_demo_observed_gap_min_missing_bars', 6)))
    two = await get_latest_closed_candles(db, deployment_id, limit=2)
    if len(two) != 2:
        return None
    newest = _normalize_dt(two[0].get('candle_time'))
    preceding = _normalize_dt(two[1].get('candle_time'))
    first_pending = (await db.execute(select(func.min(LiveMarketCandle.candle_time)).where(
        LiveMarketCandle.deployment_id == deployment_id,
        LiveMarketCandle.timeframe == deployment.timeframe,
        LiveMarketCandle.is_closed.is_(True),
        LiveMarketCandle.candle_time > deployment.last_processed_candle_time,
    ))).scalar_one_or_none()
    from .candle_catchup import utc
    from .gap_resume_policy import eligible_for_demo_cold_reseed
    if first_pending is None or newest is None or preceding is None:
        return None
    missing_slots = max(0, int((utc(first_pending) - utc(deployment.last_processed_candle_time)).total_seconds()
                                // interval_s) - 1)
    if not eligible_for_demo_cold_reseed(
        mode=str(deployment.mode or ''), enabled=True,
        timeframe_seconds=interval_s,
        missing_slots=missing_slots, min_missing_slots=minimum_missing,
        attempts=state['attempts'], successful_refetches=state['successes'],
        broker_source_verified=all(str(x.get('source') or '').upper() == 'TRADELOCKER' for x in two),
        last_two_broker_bars_consecutive=(newest == preceding + timedelta(seconds=interval_s)),
    ):
        return None
    # Cold 80K reseed of the exact registered strategy at the *last observed*
    # candle. The entire reseed candle is historical: suppress broker orders,
    # regardless of Auto Trade state or the global stale-order guard.
    state['last_reseed'] = moment
    await db.rollback()
    logger.warning('RUNNER_DEMO_GAP_RESEED_START deployment=%s missing=%s target=%s '
                   'attempts=%s broker_history_successes=%s historical_orders_suppressed=true',
                   deployment_id, missing_key, newest, state['attempts'], state['successes'])
    try:
        output = await run_strategy_for_deployment(
            db, deployment_id, execute=True, refresh_broker_candles=False,
            candle_time=newest, suppress_broker_order_for_catchup=True,
            allow_demo_gap_reseed=True,
        )
    except Exception as exc:
        await db.rollback()
        state['reseed_failures'] += 1
        logger.error('RUNNER_DEMO_GAP_RESEED_FAILED deployment=%s target=%s error=%s',
                     deployment_id, newest, str(exc)[:220])
        return None
    action = str(output.get('final_action') or '')
    if output.get('success') and action not in {'LOCK_SKIPPED','HOLD_CANDLE_GAP','CANDLE_ALREADY_PROCESSED'}:
        _DEMO_GAP_RECOVERY.pop(key, None)
        logger.warning('RUNNER_DEMO_GAP_RESEED_DONE deployment=%s target=%s action=%s '
                       'broker_orders_suppressed=true next_fresh_candle_only=true',
                       deployment_id, newest, action)
        return {'deployment_id': key, 'ran': True, 'success': True,
                'recovery_action': 'DEMO_COLD_RESEEDED',
                'historical_orders_suppressed': True,
                'last_processed_candle_time': newest.isoformat()}
    if action != 'LOCK_SKIPPED':
        state['reseed_failures'] += 1
    logger.warning('RUNNER_DEMO_GAP_RESEED_NOT_COMPLETED deployment=%s target=%s action=%s',
                   deployment_id, newest, action)
    return None


async def run_deployment_if_due(db: AsyncSession, deployment_id: UUID, *, force: bool = False, claimed: bool = False) -> dict[str, Any]:
    deployment = (await db.execute(select(StrategyDeployment).where(
        StrategyDeployment.id == deployment_id).execution_options(populate_existing=True))).scalar_one_or_none()
    if deployment is None:
        raise HTTPException(status_code=404, detail="Deployment not found")

    now = utc_now()
    result: dict[str, Any] = {
        "deployment_id": str(deployment.id),
        "status": deployment.status,
        "auto_runner_enabled": bool(getattr(deployment, "auto_runner_enabled", False)),
        "ran": False,
        "skipped": False,
        "next_run_at": getattr(deployment, "next_run_at", None).isoformat() if getattr(deployment, "next_run_at", None) else None,
    }

    if str(deployment.status or "").upper() != "RUNNING":
        result.update(skipped=True, reason="Deployment is not RUNNING")
        return result
    if not force and not bool(getattr(deployment, "auto_runner_enabled", False)):
        result.update(skipped=True, reason="Auto runner is disabled")
        return result

    # A new deployment may still be backfilling 80K candles. Suppress
    # duplicate expensive dispatch/history checks while the dedicated Celery
    # warm-up runs. Poll only a short-lived Redis *hint*; always retry the SQL
    # readiness check on READY, FAILED, or bounded fallback. This never bypasses
    # RUNNING/Auto Runner checks, and force=True is deliberately unaffected.
    if not force and warmup_gate.contains(deployment.id):
        progress = None
        if warmup_gate.due_for_probe(deployment.id):
            client = redis_manager.client if redis_manager.is_available else None
            if client is not None:
                try:
                    progress = await asyncio.wait_for(
                        client.hgetall(f"live:history:warmup:status:{deployment.id}"), timeout=0.15,
                    )
                except Exception:
                    progress = None
        if warmup_gate.blocked(deployment.id, redis_status=progress):
            result.update(skipped=True, reason='WARMING_UP: waiting for background historical candles')
            return result

    # The candle itself is authoritative. next_run_at is now display/diagnostic
    # metadata only; it must never delay a candle that is already closed.
    due_at = _normalize_dt(getattr(deployment, "next_run_at", None))
    expected_closed_open, fetch_eligible_at, strategy_eligible_at = _eligible_expected_closed_candle_open(
        deployment,
        now,
    )
    last_processed = _normalize_dt(getattr(deployment, "last_processed_candle_time", None))

    # A prolonged broker-data pause is not a reason to run the strategy or
    # rewrite retry logs each second. The expected bucket changes every M5;
    # this check expires automatically at the next bucket or on Run Once.
    idle = _TRADELOCKER_NO_CANDLE_IDLE.get(str(deployment.id))
    if not force and bool(getattr(settings, 'live_runner_dedicated_candle_idle_enabled', True)) and idle:
        if idle[0] == expected_closed_open.isoformat() and now < idle[1]:
            result.update(skipped=True, reason='WAITING_FOR_NEW_TRADELOCKER_CANDLE',
                          next_run_at=idle[1].isoformat())
            return result
        if idle[0] != expected_closed_open.isoformat():
            _TRADELOCKER_NO_CANDLE_IDLE.pop(str(deployment.id), None)

    # Market-data path starts early (+1s by default).
    # This does NOT delay candle ingestion until the strategy execution time.
    if not force and now < fetch_eligible_at:
        deployment.next_run_at = strategy_eligible_at
        result.update(
            skipped=True,
            reason=f"Waiting for market-data fetch window (+{_broker_delay(deployment)}s)",
            next_run_at=strategy_eligible_at.isoformat(),
        )
        await db.commit()
        return result
    result["expected_closed_candle_time"] = expected_closed_open.isoformat()
    result["last_processed_candle_time"] = last_processed.isoformat() if last_processed else None

    retry_key = (str(deployment.id), expected_closed_open.isoformat())
    # Drop stale retry keys for this deployment when a new timeframe boundary arrives.
    for key in list(_CANDLE_RETRY_ATTEMPTS):
        if key[0] == str(deployment.id) and key != retry_key:
            _CANDLE_RETRY_ATTEMPTS.pop(key, None)

    # If the newest expected candle is already processed, do no broker/network work.
    # The outer loop checks again one second later and the expected timestamp advances
    # exactly on M1/M5/M15/etc boundaries.
    if not force and last_processed is not None and last_processed >= expected_closed_open:
        _TRADELOCKER_NO_CANDLE_IDLE.pop(str(deployment.id), None)
        _CANDLE_RETRY_ATTEMPTS.pop(retry_key, None)
        next_boundary = calculate_next_runner_at(
            now,
            str(deployment.timeframe or "M5"),
            _strategy_run_delay(deployment),
        )
        deployment.next_run_at = next_boundary
        result.update(
            skipped=True,
            reason="Latest closed candle already processed",
            next_run_at=next_boundary.isoformat(),
        )
        await db.commit()
        return result

    mode_check = await check_platform_mode_allowed(db, str(deployment.mode or ""))
    if not mode_check.allowed:
        result.update(skipped=True, reason=mode_check.reason or "Platform trading disabled")
        deployment.last_runner_at = now
        deployment.next_run_at = now + timedelta(seconds=_retry_delay(deployment))
        await _write_log(db, deployment, "AUTO_RUNNER_SKIPPED", result["reason"], "WARNING")
        await db.commit()
        return result

    platform_settings = await get_platform_trading_settings(db)
    if bool(platform_settings.global_kill_switch):
        result.update(skipped=True, reason="Global kill switch is ON")
        deployment.last_runner_at = now
        deployment.next_run_at = now + timedelta(seconds=_retry_delay(deployment))
        await _write_log(db, deployment, "AUTO_RUNNER_SKIPPED", result["reason"], "WARNING")
        await db.commit()
        return result

    try:
        deployment.last_runner_wakeup_at = now
        # No per-second wakeup log: write an execution log only after a
        # genuinely new broker candle has been observed. Market closures can
        # last hours/days and should not fill PostgreSQL with wakeup rows.

        # First inspect the database. If another fast candle-ingestion path already
        # stored the bar (as shown by Market Data Snapshot latency), use it immediately
        # for market-data readiness; strategy timing is gated separately below.
        candles = await get_latest_closed_candles(db, deployment.id, limit=1)
        latest = candles[0] if candles else None
        latest_closed_candle_time = _normalize_dt(latest.get("candle_time") if latest else None)
        # Available backlog must not wait for the newest bucket to be ingested.
        available_backlog = bool(last_processed is not None and latest_closed_candle_time is not None
                                 and latest_closed_candle_time > last_processed)

        # Only hit the broker when the exact expected just-closed candle is not yet
        # present locally. Do at most 20 broker refresh attempts, one every 1 second.
        # After attempt 20 we stop hammering cTrader, but the 1-second scheduler still
        # checks the local DB; if another ingestion path stores the candle, strategy
        # execution becomes eligible according to STRATEGY_RUN_DELAY_SECONDS.
        if not available_backlog and (latest_closed_candle_time is None or latest_closed_candle_time < expected_closed_open):
            # TradeLocker dedicated data-only worker continues to poll while this
            # scheduler spends time on the full V6.4 calculation. Prevent duplicate
            # REST requests from competing for the same broker rate limits.
            external_tradelocker_ingestion = False
            broker = None
            if getattr(settings, 'live_tradelocker_candle_worker_enabled', False) and deployment.broker_account_id:
                broker = (await db.execute(select(BrokerAccount).where(BrokerAccount.id == deployment.broker_account_id))).scalar_one_or_none()
                external_tradelocker_ingestion = bool(broker and get_broker_code(broker) == 'TRADELOCKER')
                if external_tradelocker_ingestion:
                    # Fail safely back to the original inline broker refresh if
                    # the dedicated fetcher is absent. Never wait unboundedly
                    # for a Redis health read on this time-sensitive path.
                    client = redis_manager.client if redis_manager.is_available else None
                    try:
                        heartbeat = await asyncio.wait_for(
                            LiveEventBus(client).get_health('live_tradelocker_candle_worker'),
                            timeout=0.15,
                        ) if client is not None else None
                        external_tradelocker_ingestion = collector_owns_broker_ingestion(heartbeat, utc_now())
                        if not external_tradelocker_ingestion:
                            logger.warning('RUNNER_TRADELOCKER_COLLECTOR_STALE deployment=%s status=%s last_poll_completed=%s inline_refresh_allowed=true',
                                           deployment.id, (heartbeat or {}).get('status'),
                                           (heartbeat or {}).get('last_poll_completed_at'))
                    except Exception:
                        external_tradelocker_ingestion = False
            if external_tradelocker_ingestion:
                if bool(getattr(settings, 'live_runner_dedicated_candle_idle_enabled', True)) and not force:
                    return await _wait_for_dedicated_tradelocker_candle(
                        db, deployment, expected_closed_open, utc_now(), result)
                return await _schedule_retry(db, deployment, utc_now(),
                    f'Waiting for dedicated TradeLocker candle worker to store {expected_closed_open.isoformat()}', result)
            attempts = int(_CANDLE_RETRY_ATTEMPTS.get(retry_key, 0))
            fallback_limit = (1 if (getattr(settings, 'live_tradelocker_candle_worker_enabled', False)
                                    and broker is not None and get_broker_code(broker) == 'TRADELOCKER')
                              else MAX_CANDLE_RETRY_ATTEMPTS)
            if attempts < fallback_limit:
                attempts += 1
                _CANDLE_RETRY_ATTEMPTS[retry_key] = attempts
                result["candle_retry_attempt"] = attempts
                result["candle_retry_max"] = MAX_CANDLE_RETRY_ATTEMPTS
                try:
                    if deployment.broker_account_id:
                        await refresh_deployment_candles(db, deployment.id, count=12)
                except Exception as exc:
                    await _write_log(
                        db,
                        deployment,
                        "AUTO_RUNNER_CANDLE_REFRESH_WARNING",
                        f"Broker candle refresh attempt {attempts}/{MAX_CANDLE_RETRY_ATTEMPTS} failed; retrying in 1s: {str(exc)[:240]}",
                        "WARNING",
                    )

                candles = await get_latest_closed_candles(db, deployment.id, limit=1)
                latest = candles[0] if candles else None
                latest_closed_candle_time = _normalize_dt(latest.get("candle_time") if latest else None)
            else:
                result["candle_retry_attempt"] = attempts
                result["candle_retry_max"] = MAX_CANDLE_RETRY_ATTEMPTS

        result["latest_closed_candle_time"] = latest_closed_candle_time.isoformat() if latest_closed_candle_time else None

        if not available_backlog and (latest_closed_candle_time is None or latest_closed_candle_time < expected_closed_open):
            attempts = int(_CANDLE_RETRY_ATTEMPTS.get(retry_key, 0))
            # When a dedicated TradeLocker collector has stalled, one bounded
            # inline fetch per M5 bucket is sufficient. Idle DB-only checks
            # continue; never storm the broker every scheduler tick.
            if (not force and getattr(settings, 'live_tradelocker_candle_worker_enabled', False)
                    and broker is not None and get_broker_code(broker) == 'TRADELOCKER'
                    and not external_tradelocker_ingestion and attempts >= 1):
                return await _wait_for_dedicated_tradelocker_candle(
                    db, deployment, expected_closed_open, utc_now(), result)
            if attempts >= MAX_CANDLE_RETRY_ATTEMPTS:
                reason = (
                    f"Expected closed candle {expected_closed_open.isoformat()} is still missing after "
                    f"{MAX_CANDLE_RETRY_ATTEMPTS} broker refresh attempts. Broker refresh is capped; "
                    "local candle DB will still be checked every 1s until this candle appears or the next boundary arrives."
                )
                deployment.next_run_at = utc_now() + timedelta(seconds=1)
                deployment.last_runner_at = utc_now()
                deployment.last_heartbeat_at = utc_now()
                result.update(skipped=True, reason=reason, next_run_at=deployment.next_run_at.isoformat())
                # Log exhaustion only once, on the final active broker-refresh attempt.
                if attempts == MAX_CANDLE_RETRY_ATTEMPTS:
                    await _write_log(db, deployment, "AUTO_RUNNER_CANDLE_RETRY_EXHAUSTED", reason, "WARNING", {
                        "attempts": attempts,
                        "expected_closed_candle_time": expected_closed_open.isoformat(),
                    })
                    _CANDLE_RETRY_ATTEMPTS[retry_key] = MAX_CANDLE_RETRY_ATTEMPTS + 1
                await db.commit()
                return result
            return await _schedule_retry(
                db,
                deployment,
                utc_now(),
                f"Waiting for expected closed candle {expected_closed_open.isoformat()}; broker refresh attempt {attempts}/{MAX_CANDLE_RETRY_ATTEMPTS}, retrying in 1s.",
                result,
            )

        _TRADELOCKER_NO_CANDLE_IDLE.pop(str(deployment.id), None)

        latest_closed_candle_time = min(latest_closed_candle_time, expected_closed_open)
        # A newer candle is present. Market data may arrive before the strategy's
        # configured execution delay. Keep the candle stored, but do not run the
        # strategy until STRATEGY_RUN_DELAY_SECONDS has elapsed after candle close.
        if not force and not available_backlog and now < strategy_eligible_at:
            deployment.next_run_at = strategy_eligible_at
            result.update(
                skipped=True,
                reason=(
                    f"Closed candle is ready; waiting for strategy delay "
                    f"(+{_strategy_run_delay(deployment)}s)"
                ),
                next_run_at=strategy_eligible_at.isoformat(),
            )
            await db.commit()
            return result

        # A newer candle is present and strategy delay has elapsed.
        # Process it immediately. This also handles recovery after API restart.
        if last_processed is not None and latest_closed_candle_time <= last_processed:
            return await _schedule_retry(
                db,
                deployment,
                utc_now(),
                "New closed candle not visible yet; retrying in 1s.",
                result,
            )

        # Advance consecutive closed candles in ascending order. Backlogged
        # history updates indicators/portfolio state but cannot place old orders.
        suppress_broker_order_for_catchup = False
        if _sequential_monitor_enabled(deployment, force=force) and last_processed is not None:
            interval_s = parse_timeframe_to_seconds(str(deployment.timeframe or 'M5'))
            first_pending = (await db.execute(
                select(func.min(LiveMarketCandle.candle_time)).where(
                    LiveMarketCandle.deployment_id == deployment_id,
                    LiveMarketCandle.timeframe == deployment.timeframe,
                    LiveMarketCandle.is_closed.is_(True),
                    LiveMarketCandle.candle_time > last_processed,
                    LiveMarketCandle.candle_time <= latest_closed_candle_time,
                )
            )).scalar_one_or_none()
            recovery = plan_recovery(
                last_processed=last_processed, first_pending=first_pending,
                newest=latest_closed_candle_time, timeframe_seconds=interval_s,
            )
            if recovery.action == 'WAIT_FOR_BACKFILL':
                # Default remains fail-closed. The operator may separately opt
                # into DEMO-only, source-pinned cold re-seeding after three
                # bounded broker-history requests fail to recover a long gap.
                if (not force and str(deployment.mode or '').upper() == 'DEMO'
                        and bool(getattr(settings, 'live_runner_demo_observed_gap_resume_enabled', False))
                        and deployment.broker_account_id):
                    recovery_result = await _try_demo_gap_recovery(
                        db, deployment, recovery=recovery,
                        latest_closed_candle_time=latest_closed_candle_time,
                        interval_s=interval_s,
                    )
                    if recovery_result is not None:
                        return recovery_result
                    # Broker refresh commits/rolls back the current transaction;
                    # SQLAlchemy expires ORM attributes on rollback. Reload the
                    # deployment before the ordinary WAIT path writes timestamps.
                    await db.refresh(deployment)
                moment = time.monotonic()
                if moment - _GAP_WAIT_LOG_AT.get(str(deployment_id), -1e12) > 30:
                    logger.warning(
                        'RUNNER_CANDLE_BACKFILL_WAIT deployment=%s missing_open=%s newest_open=%s pending_bars=%s '
                        'cursor_unchanged=true', deployment_id,
                        recovery.missing_open.isoformat(), latest_closed_candle_time.isoformat(),
                        recovery.pending_bars,
                    )
                    _GAP_WAIT_LOG_AT[str(deployment_id)] = moment
                    # The dedicated collector owns TradeLocker backfill. Other
                    # polling deployments get one bounded repair attempt, never
                    # fabricated bars or a cursor jump across missing history.
                    collector_owned = False
                    if deployment.broker_account_id and getattr(settings, 'live_tradelocker_candle_worker_enabled', False):
                        gap_broker = (await db.execute(select(BrokerAccount).where(
                            BrokerAccount.id == deployment.broker_account_id))).scalar_one_or_none()
                        collector_owned = bool(gap_broker and get_broker_code(gap_broker) == 'TRADELOCKER')
                    if deployment.broker_account_id and not collector_owned:
                        repair_count = required_broker_fetch_bars(
                            newest=latest_closed_candle_time, previous=last_processed,
                            timeframe_seconds=interval_s)
                        if repair_count is not None:
                            await refresh_deployment_candles(db, deployment.id, count=repair_count)
                # Dedicated TradeLocker collector attempts bounded refetch.
                # Waiting instead of generating signals against discontinuous
                # candle inputs is deliberate; market closures may be legitimate.
                # Don't insert a LiveTradeLog row on every idle retry;
                # periodic warning above is the readable diagnostic marker.
                deployment.next_run_at = utc_now() + timedelta(seconds=5)
                deployment.last_runner_at = utc_now()
                result.update(skipped=True, reason='CANDLE_BACKFILL_WAIT',
                              missing_candle_open=recovery.missing_open.isoformat(),
                              next_run_at=deployment.next_run_at.isoformat())
                await db.commit()
                return result
            if recovery.action == 'PROCESS_NEXT':
                latest_closed_candle_time = recovery.target
                suppress_broker_order_for_catchup = recovery.pending_bars > 1
                if suppress_broker_order_for_catchup:
                    logger.warning(
                        'RUNNER_CANDLE_CATCHUP deployment=%s next_open=%s pending_bars=%s '
                        'broker_orders_suppressed=true', deployment_id,
                        recovery.target.isoformat(), recovery.pending_bars,
                    )
            _GAP_WAIT_LOG_AT.pop(str(deployment_id), None)
            _DEMO_GAP_RECOVERY.pop(str(deployment_id), None)

        eligible_at = latest_closed_candle_time + timedelta(
            seconds=parse_timeframe_to_seconds(str(deployment.timeframe or 'M5')) + _strategy_run_delay(deployment))
        if utc_now() < eligible_at:
            result.update(skipped=True, reason='Waiting for closed-candle strategy delay',
                          next_run_at=eligible_at.isoformat())
            return result

        # Candle is available: clear retry state before strategy execution.
        await _write_log(db, deployment, "AUTO_RUNNER_WAKEUP", "New closed candle ready for strategy evaluation", metadata={"timeframe": deployment.timeframe, "scheduled_at": due_at.isoformat() if due_at else None})
        _CANDLE_RETRY_ATTEMPTS.pop(retry_key, None)
        # Link the legacy REST cycle to the same trace as the data-only worker.
        # A missing Redis trace is harmless: strategy still executes as before.
        trace_id = None
        if deployment.broker_account_id and getattr(settings, 'live_tradelocker_candle_worker_enabled', False):
            broker = (await db.execute(select(BrokerAccount).where(BrokerAccount.id == deployment.broker_account_id))).scalar_one_or_none()
            if broker and get_broker_code(broker) == 'TRADELOCKER':
                trace_id = deterministic_trace_id(deployment.id, latest_closed_candle_time)
        # Observability only: a slow full-history strategy run can move the
        # DB cursor multiple M5 bars ahead without evaluating intermediate bars.
        # Never silently describe this as full backtest/live parity.
        if last_processed is not None:
            timeframe_s = parse_timeframe_to_seconds(str(deployment.timeframe or "M5"))
            elapsed_bars = int((latest_closed_candle_time - last_processed).total_seconds() // timeframe_s)
            if elapsed_bars > 1:
                logger.error(
                    "RUNNER_CANDLE_GAP deployment=%s previous_open=%s newest_open=%s inferred_bars_between=%s "
                    "intermediate_bar_evaluations_not_confirmed=true",
                    deployment_id, last_processed.isoformat(), latest_closed_candle_time.isoformat(), elapsed_bars - 1,
                )

        logger.warning(
            "RUNNER_DISPATCH deployment=%s candle_open=%s last_processed_open=%s age_since_close_s=%.3f",
            deployment_id, latest_closed_candle_time.isoformat(),
            last_processed.isoformat() if last_processed else None,
            max(0.0, (utc_now() - (latest_closed_candle_time + timedelta(seconds=parse_timeframe_to_seconds(str(deployment.timeframe or "M5"))))).total_seconds()),
        )
        dispatch_started = time.monotonic()
        runner_result = await run_strategy_for_deployment(
            db, deployment.id, execute=True, refresh_broker_candles=False,
            candle_time=latest_closed_candle_time, trace_id=trace_id,
            suppress_broker_order_for_catchup=suppress_broker_order_for_catchup)
        if not runner_result.get("success", False):
            if runner_result.get('error_code') in {'STRATEGY_HISTORY_INSUFFICIENT', 'NOT_ENOUGH_LIVE_CANDLES'}:
                warmup_gate.record_missing(deployment.id,
                    int(runner_result.get('required_history_bars') or getattr(settings, 'live_strategy_history_default_bars', 80000)))
                history_ready_cache.invalidate(deployment.id)
            deployment = (await db.execute(select(StrategyDeployment).where(StrategyDeployment.id == deployment_id))).scalar_one()
            return await _schedule_retry(
                db, deployment, utc_now(),
                "Strategy result unsuccessful (history/contract/other HOLD); candle NOT marked processed",
                result,
            )
        warmup_gate.clear(deployment.id)
        logger.warning(
            "RUNNER_DISPATCH_FINISHED deployment=%s candle_open=%s elapsed_s=%.3f action=%s success=%s",
            deployment_id, latest_closed_candle_time.isoformat(),
            time.monotonic() - dispatch_started, runner_result.get("final_action"), runner_result.get("success"),
        )
        # If another request (for example Run Strategy Once) owned the per-deployment
        # runner lock, do not mark this candle processed. A skipped lock must be
        # retried, otherwise Auto Runner can silently miss an entire candle.
        # A duplicate *signal* is an idempotently completed evaluation, while a
        # lock-skipped *run* never evaluated the candle. Only the latter retries.
        # Retrying successful duplicates can create a perpetual re-run storm.
        if str(runner_result.get("final_action") or "").upper() == "LOCK_SKIPPED":
            deployment = (await db.execute(select(StrategyDeployment).where(StrategyDeployment.id == deployment_id))).scalar_one()
            return await _schedule_retry(db, deployment, utc_now(), "Runner was busy; retry scheduled without consuming the candle.", result)

        deployment = (await db.execute(select(StrategyDeployment).where(StrategyDeployment.id == deployment_id))).scalar_one()
        # The runner alone commits the authoritative cursor/checkpoint. A later
        # scheduler transaction must never rewind a concurrently advanced cursor.
        deployment.last_runner_at = now
        deployment.last_heartbeat_at = now
        deployment.next_run_at = calculate_next_runner_at(
            utc_now(),
            deployment.timeframe,
            _strategy_run_delay(deployment),
        )
        deployment.runner_error_count = 0
        deployment.runner_last_error = None
        await _write_log(db, deployment, "AUTO_RUNNER_COMPLETED", runner_result.get("message") or "Auto runner completed", metadata={"runner": runner_result, "latest_closed_candle_time": latest_closed_candle_time.isoformat(), "next_run_at": deployment.next_run_at.isoformat()})
        await db.commit()
        result.update(ran=True, runner=runner_result, message=runner_result.get("message"), next_run_at=deployment.next_run_at.isoformat())
        # Best-effort diagnostics after the trading cursor commit; failure here
        # must not cause this candle to be re-executed or change its risk outcome.
        if trace_id:
            try:
                client = redis_manager.client
                trace = LiveLatencyTraceService(client if redis_manager.is_available else None)
                if trace.enabled:
                    async with async_session() as trace_db:
                        await trace.persist(trace_db, trace_id)
                        await trace_db.commit()
            except Exception:
                logger.exception('TradeLocker trace persistence failed (noncritical) deployment=%s', deployment_id)
        return result
    except Exception as exc:
        # Any flush/execute failure leaves SQLAlchemy in a failed transaction.
        # Roll back *before* issuing the recovery SELECT; otherwise the recovery
        # path itself raises PendingRollbackError and the scheduler can keep
        # failing even after the original transient DB error is gone.
        try:
            await db.rollback()
        except Exception:
            logger.exception("Auto runner rollback failed for deployment %s", deployment_id)

        deployment = (await db.execute(select(StrategyDeployment).where(StrategyDeployment.id == deployment_id))).scalar_one_or_none()
        if deployment is not None:
            message = str(getattr(exc, "detail", None) or exc)[:1000]
            deployment.last_runner_at = now
            deployment.last_runner_wakeup_at = now
            deployment.next_run_at = now + timedelta(seconds=_retry_delay(deployment))
            deployment.runner_error_count = int(deployment.runner_error_count or 0) + 1
            deployment.runner_last_error = message
            level = "ERROR"
            event_type = "AUTO_RUNNER_ERROR_RETRY"
            # Scheduler/network/candle errors must not silently pause a running
            # deployment. Safety pauses remain the responsibility of explicit
            # user controls, kill switch, and funded-risk guard.
            error_retry_seconds = _retry_delay(deployment)
            deployment.next_run_at = now + timedelta(seconds=error_retry_seconds)
            message = f"{message} Auto runner remains RUNNING and will retry in {error_retry_seconds}s."
            await _write_log(db, deployment, event_type, message, level, {"error_count": deployment.runner_error_count, "next_run_at": deployment.next_run_at.isoformat()})
            await db.commit()
            result.update(ran=False, error=True, message=message, error_count=deployment.runner_error_count, next_run_at=deployment.next_run_at.isoformat())
            return result
        raise


async def run_due_deployments(db: AsyncSession | None = None) -> dict[str, Any]:
    """Low-latency scheduler scan.

    Every second, inspect every RUNNING + Auto Runner deployment. The actual trigger
    is the newest expected closed candle, not `next_run_at`. This prevents stale or
    drifted schedule metadata from delaying a strategy by 30-120 seconds.

    Duplicate execution remains protected by the per-deployment PostgreSQL advisory
    transaction lock inside `run_strategy_for_deployment` plus signal idempotency.
    """
    owns_session = db is None
    session = db or async_session()

    if _RUNNER_SCAN_LOCK.locked() and owns_session:
        if owns_session:
            await session.close()
        return {"success": True, "checked": 0, "results": [], "skipped": "AUTO_RUNNER_SCAN_BUSY"}

    async with _RUNNER_SCAN_LOCK:
        try:
            query = select(StrategyDeployment.id).where(
                    StrategyDeployment.status == "RUNNING",
                    StrategyDeployment.auto_runner_enabled.is_(True),
                )
            if settings.live_event_pipeline_enabled and settings.live_market_worker_enabled:
                # The market worker owns cTrader feeds even during the
                # market-only rollout phase. Keep the original scheduler alive
                # for MT5, Upstox, and other brokers in the same API process.
                provider = func.upper(func.coalesce(
                    BrokerProvider.code, BrokerAccount.broker_code,
                    BrokerAccount.broker_name, "MT5",
                ))
                query = (
                    query.outerjoin(BrokerAccount, BrokerAccount.id == StrategyDeployment.broker_account_id)
                    .outerjoin(BrokerProvider, BrokerProvider.id == BrokerAccount.broker_provider_id)
                    .where(provider.notin_(("CTRADER", "CTRADER_API")))
                )
            # ID scan cache is advisory for *this worker process only*. The
            # dispatch function always SELECTs the current deployment status;
            # stale cache entries therefore cannot re-enable a stopped runner.
            cached_ids = eligible_scan_cache.get(
                event_pipeline_enabled=bool(settings.live_event_pipeline_enabled),
                market_worker_enabled=bool(settings.live_market_worker_enabled),
            ) if owns_session else None
            if cached_ids is None:
                deployment_ids = (await session.execute(
                    query.order_by(StrategyDeployment.created_at.asc())
                )).scalars().all()
                if owns_session:
                    eligible_scan_cache.store(list(deployment_ids),
                        event_pipeline_enabled=bool(settings.live_event_pipeline_enabled),
                        market_worker_enabled=bool(settings.live_market_worker_enabled))
            else:
                deployment_ids = list(cached_ids)

            # Optional persistent multi-process pool. Every process sees the same
            # deployment registry but owns a deterministic subset; source/runtime
            # are still resolved from DB and execution remains lock-protected.
            # No separate container/adapter is created for each deployment.
            shard_count = max(1, int(os.environ.get("LIVE_LEGACY_RUNNER_SHARD_COUNT", "1")))
            shard_index = int(os.environ.get("LIVE_LEGACY_RUNNER_SHARD_INDEX", "0"))
            if not 0 <= shard_index < shard_count:
                raise ValueError("Invalid live runner shard index")
            if shard_count > 1:
                # Registry additions/removals never move existing deployments.
                deployment_ids = [deployment_id for deployment_id in deployment_ids
                                  if deployment_worker_index(deployment_id, shard_count) == shard_index]
            results: list[dict[str, Any]] = []
            for deployment_id in deployment_ids:
                results.append(await run_deployment_if_due(session, deployment_id, claimed=True))
            return {"success": True, "checked": len(deployment_ids), "results": results}
        finally:
            if owns_session:
                await session.close()


async def auto_runner_loop(cycle_observer: Callable[[str], None] | None = None) -> None:
    interval = max(1, int(getattr(settings, "live_runner_interval_seconds", 1) or 1))
    logger.info("Live auto runner loop started, scheduler scan interval=%ss", interval)
    while True:
        started = time.monotonic()
        try:
            if cycle_observer is not None:
                cycle_observer("STARTED")
            result = await run_due_deployments()
            elapsed = time.monotonic() - started
            # Lightweight timing only; never change execution/retry decisions.
            results = result.get("results") or []
            ran = sum(bool(item.get("ran")) for item in results)
            if elapsed >= 30:
                logger.warning("Legacy scheduler slow cycle: duration=%.3fs checked=%s ran=%s", elapsed, result.get("checked"), ran)
            elif elapsed >= 5 or ran:
                logger.info("Legacy scheduler cycle: duration=%.3fs checked=%s ran=%s", elapsed, result.get("checked"), ran)
        except asyncio.CancelledError:
            logger.info("Live auto runner loop cancelled")
            raise
        except Exception:
            logger.exception("Live auto runner loop failed; continuing")
        finally:
            if cycle_observer is not None:
                cycle_observer("FINISHED")
        await asyncio.sleep(interval)
