from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select, text, or_
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import settings
from ...db.models import LiveTradeLog, StrategyDeployment
from ...db.session import async_session
from .broker_candle_service import get_latest_closed_candles, refresh_deployment_candles
from .runner_scheduler import calculate_next_runner_after_candle, calculate_next_runner_at, ensure_utc, utc_now
from .strategy_runner import run_strategy_for_deployment
from .trading_safety import check_platform_mode_allowed, get_platform_trading_settings

logger = logging.getLogger(__name__)


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
    try:
        return max(0, int(getattr(deployment, "broker_delay_seconds", None) or 3))
    except Exception:
        return 3


def _retry_delay(deployment: StrategyDeployment) -> int:
    try:
        return max(1, int(getattr(deployment, "missed_candle_retry_seconds", None) or 10))
    except Exception:
        return 10


def _next_scheduled_run(deployment: StrategyDeployment, now):
    return calculate_next_runner_at(now, str(deployment.timeframe or "M5"), _broker_delay(deployment))


async def _schedule_retry(db: AsyncSession, deployment: StrategyDeployment, now, reason: str, result: dict[str, Any]) -> dict[str, Any]:
    retry_at = now + timedelta(seconds=_retry_delay(deployment))
    deployment.next_run_at = retry_at
    deployment.last_runner_at = now
    deployment.last_heartbeat_at = now
    result.update(skipped=True, reason=reason, next_run_at=retry_at.isoformat())
    await _write_log(db, deployment, "AUTO_RUNNER_RETRY_SCHEDULED", reason, "WARNING", {"next_run_at": retry_at.isoformat()})
    await db.commit()
    return result


async def run_deployment_if_due(db: AsyncSession, deployment_id: UUID, *, force: bool = False) -> dict[str, Any]:
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

    # First tick for existing running deployments: schedule, do not stampede-run.
    due_at = _normalize_dt(getattr(deployment, "next_run_at", None))
    if due_at is None and not force:
        due_at = _next_scheduled_run(deployment, now)
        deployment.next_run_at = due_at
        deployment.last_heartbeat_at = now
        await _write_log(db, deployment, "AUTO_RUNNER_SCHEDULED", "Auto runner scheduled for next candle close", metadata={"next_run_at": due_at.isoformat(), "timeframe": deployment.timeframe})
        await db.commit()
        result.update(skipped=True, reason="Auto runner scheduled for next candle close", next_run_at=due_at.isoformat())
        return result

    if due_at is not None and now < due_at and not force:
        result.update(skipped=True, reason="Waiting for next scheduled candle close", next_run_at=due_at.isoformat())
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

        try:
            if deployment.broker_account_id:
                await refresh_deployment_candles(db, deployment.id, count=300)
        except Exception as exc:
            await _write_log(db, deployment, "AUTO_RUNNER_CANDLE_REFRESH_WARNING", f"Broker candle refresh failed; stored candles will be checked: {str(exc)[:240]}", "WARNING")

        candles = await get_latest_closed_candles(db, deployment.id, limit=1)
        latest = candles[0] if candles else None
        latest_closed_candle_time = _normalize_dt(latest.get("candle_time") if latest else None)
        result["latest_closed_candle_time"] = latest_closed_candle_time.isoformat() if latest_closed_candle_time else None
        last_processed = _normalize_dt(getattr(deployment, "last_processed_candle_time", None))
        result["last_processed_candle_time"] = last_processed.isoformat() if last_processed else None

        if latest_closed_candle_time is None:
            return await _schedule_retry(db, deployment, now, "No broker candles available. Retry scheduled.", result)
        if last_processed is not None and latest_closed_candle_time <= last_processed:
            return await _schedule_retry(db, deployment, now, "Broker has not published a new closed candle yet. Retry scheduled.", result)

        runner_result = await run_strategy_for_deployment(db, deployment.id, execute=True)
        deployment = (await db.execute(select(StrategyDeployment).where(StrategyDeployment.id == deployment_id))).scalar_one()
        deployment.last_processed_candle_time = latest_closed_candle_time
        deployment.last_runner_at = now
        deployment.last_heartbeat_at = now
        deployment.next_run_at = calculate_next_runner_after_candle(latest_closed_candle_time, deployment.timeframe, _broker_delay(deployment), now_utc=now)
        deployment.runner_error_count = 0
        deployment.runner_last_error = None
        await _write_log(db, deployment, "AUTO_RUNNER_COMPLETED", runner_result.get("message") or "Auto runner completed", metadata={"runner": runner_result, "latest_closed_candle_time": latest_closed_candle_time.isoformat(), "next_run_at": deployment.next_run_at.isoformat()})
        await db.commit()
        result.update(ran=True, runner=runner_result, message=runner_result.get("message"), next_run_at=deployment.next_run_at.isoformat())
        return result
    except Exception as exc:
        deployment = (await db.execute(select(StrategyDeployment).where(StrategyDeployment.id == deployment_id))).scalar_one_or_none()
        if deployment is not None:
            message = str(getattr(exc, "detail", None) or exc)[:1000]
            deployment.last_runner_at = now
            deployment.last_runner_wakeup_at = now
            deployment.next_run_at = now + timedelta(seconds=_retry_delay(deployment))
            deployment.runner_error_count = int(deployment.runner_error_count or 0) + 1
            deployment.runner_last_error = message
            level = "ERROR"
            event_type = "AUTO_RUNNER_ERROR"
            if deployment.runner_error_count >= 5:
                deployment.status = "PAUSED"
                event_type = "AUTO_RUNNER_AUTO_PAUSED"
                message = f"Auto runner paused deployment after {deployment.runner_error_count} repeated errors. Last error: {message}"
            await _write_log(db, deployment, event_type, message, level, {"error_count": deployment.runner_error_count, "next_run_at": deployment.next_run_at.isoformat()})
            await db.commit()
            result.update(ran=False, error=True, message=message, error_count=deployment.runner_error_count, next_run_at=deployment.next_run_at.isoformat())
            return result
        raise


async def run_due_deployments(db: AsyncSession | None = None) -> dict[str, Any]:
    owns_session = db is None
    session = db or async_session()
    try:
        locked = (await session.execute(text("SELECT pg_try_advisory_lock(26051001)"))).scalar()
        if not locked:
            return {"success": True, "checked": 0, "results": [], "skipped": "AUTO_RUNNER_LOCK_HELD"}
        now = utc_now()
        rows = (await session.execute(
            select(StrategyDeployment.id).where(
                StrategyDeployment.status == "RUNNING",
                StrategyDeployment.auto_runner_enabled.is_(True),
                or_(StrategyDeployment.next_run_at.is_(None), StrategyDeployment.next_run_at <= now),
            ).order_by(StrategyDeployment.next_run_at.asc().nullsfirst(), StrategyDeployment.created_at.asc())
        )).scalars().all()
        results = []
        for deployment_id in rows:
            results.append(await run_deployment_if_due(session, deployment_id))
        return {"success": True, "checked": len(rows), "results": results}
    finally:
        try:
            await session.execute(text("SELECT pg_advisory_unlock(26051001)"))
            await session.commit()
        except Exception:
            try:
                await session.rollback()
            except Exception:
                pass
        if owns_session:
            await session.close()


async def auto_runner_loop() -> None:
    interval = max(1, int(getattr(settings, "live_runner_interval_seconds", 5) or 5))
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
