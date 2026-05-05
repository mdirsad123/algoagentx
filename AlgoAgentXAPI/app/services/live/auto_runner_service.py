from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import settings
from ...db.models import LiveTradeLog, StrategyDeployment
from ...db.session import async_session
from .broker_candle_service import get_latest_closed_candles, refresh_deployment_candles
from .strategy_runner import run_strategy_for_deployment
from .trading_safety import check_platform_mode_allowed, get_platform_trading_settings

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_dt(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def timeframe_minutes(timeframe: str) -> int:
    """Convert a platform timeframe such as M5/H1/D1 into minutes."""
    tf = str(timeframe or "").strip().lower()
    aliases = {"m1": 1, "1m": 1, "m5": 5, "5m": 5, "m15": 15, "15m": 15, "m30": 30, "30m": 30, "h1": 60, "1h": 60, "h4": 240, "4h": 240, "d1": 1440, "1d": 1440, "day": 1440, "daily": 1440}
    if tf in aliases:
        return aliases[tf]
    match = re.match(r"^(\d+)\s*([mhd])", tf)
    if match:
        n = max(1, int(match.group(1)))
        unit = match.group(2)
        return n if unit == "m" else n * 60 if unit == "h" else n * 1440
    return 1


def calculate_next_due_by_timeframe(timeframe: str, last_processed_candle_time: datetime | None = None) -> datetime:
    """Return when the next broker candle should be safely available.

    MT5/Upstox candle_time is the candle OPEN time. For M5, the candle stamped
    20:05 is only closed after 20:10. After we process candle 20:00, the next
    strategy run should happen just after 20:10, not at 20:05. This prevents
    repeated 10-second runner checks and avoids using a forming candle.
    """
    base = last_processed_candle_time or datetime.fromtimestamp(0, tz=timezone.utc)
    if base.tzinfo is None:
        base = base.replace(tzinfo=timezone.utc)
    minutes = timeframe_minutes(timeframe)
    # last_processed is an OPEN timestamp of the last processed closed candle.
    # next candle opens at +minutes and closes at +2*minutes. Add small broker
    # grace so the terminal has time to publish the just-closed candle.
    return base + timedelta(minutes=minutes * 2, seconds=2)


async def _write_log(db: AsyncSession, deployment: StrategyDeployment, event_type: str, message: str, level: str = "INFO", metadata: dict[str, Any] | None = None) -> None:
    db.add(LiveTradeLog(
        deployment_id=deployment.id,
        user_id=deployment.user_id,
        event_type=event_type,
        level=level,
        message=message,
        metadata_json=metadata or {},
    ))


async def run_deployment_if_due(db: AsyncSession, deployment_id: UUID) -> dict[str, Any]:
    deployment = (await db.execute(select(StrategyDeployment).where(StrategyDeployment.id == deployment_id))).scalar_one_or_none()
    if deployment is None:
        raise HTTPException(status_code=404, detail="Deployment not found")

    now = _utcnow()
    result: dict[str, Any] = {
        "deployment_id": str(deployment.id),
        "status": deployment.status,
        "auto_runner_enabled": bool(getattr(deployment, "auto_runner_enabled", False)),
        "ran": False,
        "skipped": False,
    }

    if str(deployment.status or "").upper() != "RUNNING":
        result.update(skipped=True, reason="Deployment is not RUNNING")
        return result
    if not bool(getattr(deployment, "auto_runner_enabled", False)):
        result.update(skipped=True, reason="Auto runner is disabled")
        return result
    if not bool(getattr(deployment, "auto_trade_enabled", False)):
        result.update(skipped=True, reason="Auto trade is disabled")
        return result

    mode_check = await check_platform_mode_allowed(db, str(deployment.mode or ""))
    if not mode_check.allowed:
        result.update(skipped=True, reason=mode_check.reason or "Platform trading disabled")
        await _write_log(db, deployment, "AUTO_RUNNER_SKIPPED", result["reason"], "WARNING")
        deployment.last_runner_at = now
        await db.commit()
        return result

    platform_settings = await get_platform_trading_settings(db)
    if bool(platform_settings.global_kill_switch):
        result.update(skipped=True, reason="Global kill switch is ON")
        await _write_log(db, deployment, "AUTO_RUNNER_SKIPPED", result["reason"], "WARNING")
        deployment.last_runner_at = now
        await db.commit()
        return result

    # Run on the next closed-candle boundary, not merely N minutes after the
    # previous runner tick. Example: if the last manual run happened at 13:43 on
    # M5, the auto runner should still process the 13:45 candle as soon as it is
    # closed instead of waiting until 13:48.
    last_processed_before_refresh = _normalize_dt(getattr(deployment, "last_processed_candle_time", None))
    due_at = calculate_next_due_by_timeframe(deployment.timeframe, last_processed_before_refresh)
    result["next_due_at"] = due_at.isoformat()
    if last_processed_before_refresh is not None and now < due_at:
        result.update(skipped=True, reason="Waiting for next closed candle")
        return result

    try:
        await _write_log(db, deployment, "AUTO_RUNNER_TICK", "Auto runner checking latest closed candle", metadata={"timeframe": deployment.timeframe})
        if deployment.broker_account_id:
            await refresh_deployment_candles(db, deployment.id, count=300)
        candles = await get_latest_closed_candles(db, deployment.id, limit=1)
        latest = candles[0] if candles else None
        latest_closed_candle_time = _normalize_dt(latest.get("candle_time") if latest else None)
        if latest_closed_candle_time is None:
            result.update(skipped=True, reason="No closed candle available")
            deployment.last_runner_at = now
            await _write_log(db, deployment, "AUTO_RUNNER_SKIPPED", result["reason"], "WARNING")
            await db.commit()
            return result

        last_processed = _normalize_dt(getattr(deployment, "last_processed_candle_time", None))
        result["latest_closed_candle_time"] = latest_closed_candle_time.isoformat()
        result["last_processed_candle_time"] = last_processed.isoformat() if last_processed else None
        if last_processed is not None and latest_closed_candle_time <= last_processed:
            result.update(skipped=True, reason="Latest closed candle already processed")
            deployment.last_runner_at = now
            deployment.last_heartbeat_at = now
            await db.commit()
            return result

        runner_result = await run_strategy_for_deployment(db, deployment.id, execute=True)
        deployment = (await db.execute(select(StrategyDeployment).where(StrategyDeployment.id == deployment_id))).scalar_one()
        deployment.last_processed_candle_time = latest_closed_candle_time
        deployment.last_runner_at = now
        deployment.last_heartbeat_at = now
        deployment.runner_error_count = 0
        deployment.runner_last_error = None
        await _write_log(db, deployment, "AUTO_RUNNER_COMPLETED", runner_result.get("message") or "Auto runner completed", metadata={"runner": runner_result, "latest_closed_candle_time": latest_closed_candle_time.isoformat()})
        await db.commit()
        result.update(ran=True, runner=runner_result, message=runner_result.get("message"))
        return result
    except Exception as exc:
        deployment = (await db.execute(select(StrategyDeployment).where(StrategyDeployment.id == deployment_id))).scalar_one_or_none()
        if deployment is not None:
            message = str(getattr(exc, "detail", None) or exc)[:1000]
            deployment.last_runner_at = now
            deployment.runner_error_count = int(deployment.runner_error_count or 0) + 1
            deployment.runner_last_error = message
            level = "ERROR"
            event_type = "AUTO_RUNNER_ERROR"
            if deployment.runner_error_count >= 5:
                deployment.status = "PAUSED"
                event_type = "AUTO_RUNNER_AUTO_PAUSED"
                message = f"Auto runner paused deployment after {deployment.runner_error_count} repeated errors. Last error: {message}"
            await _write_log(db, deployment, event_type, message, level, {"error_count": deployment.runner_error_count})
            await db.commit()
            result.update(ran=False, error=True, message=message, error_count=deployment.runner_error_count)
            return result
        raise


async def run_due_deployments(db: AsyncSession | None = None) -> dict[str, Any]:
    owns_session = db is None
    session = db or async_session()
    try:
        rows = (await session.execute(
            select(StrategyDeployment.id).where(
                StrategyDeployment.status == "RUNNING",
                StrategyDeployment.auto_runner_enabled.is_(True),
                StrategyDeployment.auto_trade_enabled.is_(True),
            ).order_by(StrategyDeployment.last_runner_at.asc().nullsfirst(), StrategyDeployment.created_at.asc())
        )).scalars().all()
        results = []
        for deployment_id in rows:
            results.append(await run_deployment_if_due(session, deployment_id))
        return {"success": True, "checked": len(rows), "results": results}
    finally:
        if owns_session:
            await session.close()


async def auto_runner_loop() -> None:
    interval = max(5, int(getattr(settings, "live_runner_interval_seconds", 10) or 10))
    logger.info("Live auto runner loop started, interval=%ss", interval)
    while True:
        try:
            await run_due_deployments()
        except asyncio.CancelledError:
            logger.info("Live auto runner loop cancelled")
            raise
        except Exception:
            logger.exception("Live auto runner loop failed; continuing")
        await asyncio.sleep(interval)
