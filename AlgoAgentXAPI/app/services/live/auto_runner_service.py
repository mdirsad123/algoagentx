from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select, update, or_
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import settings
from ...db.models import BrokerAccount, BrokerProvider, LiveTradeLog, StrategyDeployment
from ...db.session import async_session
from .broker_candle_service import get_latest_closed_candles, refresh_deployment_candles
from .runner_scheduler import calculate_next_runner_after_candle, calculate_next_runner_at, ensure_utc, latest_expected_closed_candle_open, utc_now
from .strategy_runner import run_strategy_for_deployment
from .trading_safety import check_platform_mode_allowed, get_platform_trading_settings

logger = logging.getLogger(__name__)
_RUNNER_SCAN_LOCK = asyncio.Lock()
# Per-process retry counter keyed by deployment + expected closed candle OPEN time.
# It limits active broker refreshes to 20 one-second attempts per candle while
# still allowing the scheduler to notice a candle already ingested by another path.
_CANDLE_RETRY_ATTEMPTS: dict[tuple[str, str], int] = {}

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


async def run_deployment_if_due(db: AsyncSession, deployment_id: UUID, *, force: bool = False, claimed: bool = False) -> dict[str, Any]:
    deployment = (await db.execute(select(StrategyDeployment).where(StrategyDeployment.id == deployment_id))).scalar_one_or_none()
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

    # The candle itself is authoritative. next_run_at is now display/diagnostic
    # metadata only; it must never delay a candle that is already closed.
    due_at = _normalize_dt(getattr(deployment, "next_run_at", None))
    expected_closed_open, fetch_eligible_at, strategy_eligible_at = _eligible_expected_closed_candle_open(
        deployment,
        now,
    )
    last_processed = _normalize_dt(getattr(deployment, "last_processed_candle_time", None))

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
        await _write_log(db, deployment, "AUTO_RUNNER_WAKEUP", "Auto runner woke after candle close", metadata={"timeframe": deployment.timeframe, "scheduled_at": due_at.isoformat() if due_at else None})

        # First inspect the database. If another fast candle-ingestion path already
        # stored the bar (as shown by Market Data Snapshot latency), use it immediately
        # for market-data readiness; strategy timing is gated separately below.
        candles = await get_latest_closed_candles(db, deployment.id, limit=1)
        latest = candles[0] if candles else None
        latest_closed_candle_time = _normalize_dt(latest.get("candle_time") if latest else None)

        # Only hit the broker when the exact expected just-closed candle is not yet
        # present locally. Do at most 20 broker refresh attempts, one every 1 second.
        # After attempt 20 we stop hammering cTrader, but the 1-second scheduler still
        # checks the local DB; if another ingestion path stores the candle, strategy
        # execution becomes eligible according to STRATEGY_RUN_DELAY_SECONDS.
        if latest_closed_candle_time is None or latest_closed_candle_time < expected_closed_open:
            attempts = int(_CANDLE_RETRY_ATTEMPTS.get(retry_key, 0))
            if attempts < MAX_CANDLE_RETRY_ATTEMPTS:
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

        if latest_closed_candle_time is None or latest_closed_candle_time < expected_closed_open:
            attempts = int(_CANDLE_RETRY_ATTEMPTS.get(retry_key, 0))
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

        # A newer candle is present. Market data may arrive before the strategy's
        # configured execution delay. Keep the candle stored, but do not run the
        # strategy until STRATEGY_RUN_DELAY_SECONDS has elapsed after candle close.
        if not force and now < strategy_eligible_at:
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

        # Candle is available: clear retry state before strategy execution.
        _CANDLE_RETRY_ATTEMPTS.pop(retry_key, None)
        runner_result = await run_strategy_for_deployment(db, deployment.id, execute=True, refresh_broker_candles=False)
        # If another request (for example Run Strategy Once) owned the per-deployment
        # runner lock, do not mark this candle processed. A skipped lock must be
        # retried, otherwise Auto Runner can silently miss an entire candle.
        if bool(runner_result.get("duplicate")) or str(runner_result.get("final_action") or "").upper() == "LOCK_SKIPPED":
            deployment = (await db.execute(select(StrategyDeployment).where(StrategyDeployment.id == deployment_id))).scalar_one()
            return await _schedule_retry(db, deployment, utc_now(), "Runner was busy; retry scheduled without consuming the candle.", result)

        deployment = (await db.execute(select(StrategyDeployment).where(StrategyDeployment.id == deployment_id))).scalar_one()
        deployment.last_processed_candle_time = latest_closed_candle_time
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
            deployment_ids = (await session.execute(
                query.order_by(StrategyDeployment.created_at.asc()).limit(100)
            )).scalars().all()

            results: list[dict[str, Any]] = []
            for deployment_id in deployment_ids:
                results.append(await run_deployment_if_due(session, deployment_id, claimed=True))
            return {"success": True, "checked": len(deployment_ids), "results": results}
        finally:
            if owns_session:
                await session.close()


async def auto_runner_loop() -> None:
    interval = 1
    logger.info("Live auto runner loop started, scheduler scan interval=%ss", interval)
    while True:
        try:
            await run_due_deployments()
        except asyncio.CancelledError:
            logger.info("Live auto runner loop cancelled")
            raise
        except Exception:
            logger.exception("Live auto runner loop failed; continuing")
        await asyncio.sleep(interval)
