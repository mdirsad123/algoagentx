"""Dedicated Celery app: nothing on the live/backtest queues is imported or scheduled."""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from uuid import UUID
from zoneinfo import ZoneInfo

from celery import Celery
from celery.schedules import crontab
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from ...core.config import settings
from ...db.session import async_session, engine
from ...db.models import MarketDataSyncBatch, MarketDataSyncConfig, MarketDataSyncRun
from .daily_sync import enabled_globally, run_sync, safe_error

logger = logging.getLogger(__name__)
TIMEZONE = os.getenv("MARKET_DATA_SYNC_TIMEZONE", "Asia/Kolkata")
HOUR, MINUTE = [int(x) for x in os.getenv("MARKET_DATA_SYNC_LOCAL_TIME", "03:00").split(":")]
celery_app = Celery("algoagentx_market_data_history", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.update(
    timezone=TIMEZONE,
    enable_utc=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_default_queue="market_data_daily",
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    broker_transport_options={"visibility_timeout": 21600},
    beat_schedule={"market-history-once-daily": {
        "task": "market_data_daily.dispatch", "schedule": crontab(hour=HOUR, minute=MINUTE), "options": {"queue": "market_data_daily"},
    }},
)


async def _enqueue_run(config_id: str, run_key: str, *, scheduled_date=None):
    async with async_session() as db:
        stmt = pg_insert(MarketDataSyncRun.__table__).values(
            feed_id=UUID(config_id), run_key=run_key, scheduled_date=scheduled_date, status="QUEUED"
        ).on_conflict_do_nothing(index_elements=["run_key"]).returning(MarketDataSyncRun.id)
        run_id = (await db.execute(stmt)).scalar_one_or_none()
        if run_id is None:
            # Crash-safe replay: a durable QUEUED audit row may have been written
            # before the Celery message reached Redis. Requeue it on Beat restart.
            run_id = (await db.execute(select(MarketDataSyncRun.id).where(
                MarketDataSyncRun.run_key == run_key, MarketDataSyncRun.status == "QUEUED"))).scalar_one_or_none()
        await db.commit()
        return str(run_id) if run_id else None


async def dispatch_for_date(scheduled_date):
    if not enabled_globally():
        return {"status": "DISABLED", "scheduled_date": str(scheduled_date)}
    # Unique INSERT prevents another Beat replica from dispatching same calendar date.
    async with async_session() as db:
        inserted = (await db.execute(pg_insert(MarketDataSyncBatch.__table__).values(
            scheduled_date=scheduled_date).on_conflict_do_nothing(index_elements=["scheduled_date"]).returning(MarketDataSyncBatch.scheduled_date))).scalar_one_or_none()
        if inserted is None:
            await db.rollback()
            batch = await db.get(MarketDataSyncBatch, scheduled_date)
            if batch and batch.dispatched_at:
                return {"status": "ALREADY_DISPATCHED", "scheduled_date": str(scheduled_date)}
        configs = (await db.execute(select(MarketDataSyncConfig.id).where(MarketDataSyncConfig.enabled.is_(True), MarketDataSyncConfig.is_archived.is_(False)).order_by(MarketDataSyncConfig.created_at))).scalars().all()
        # Commit schedule ownership before queueing; audit run rows are durable.
        await db.commit()
    run_ids = []
    for config_id in configs:
        run_id = await _enqueue_run(str(config_id), f"daily:{scheduled_date}:{config_id}", scheduled_date=scheduled_date)
        if run_id:
            run_ids.append(run_id)
    # Mark 'dispatched' only after the tasks have been submitted.
    for i, run_id in enumerate(run_ids):
        process_market_history.apply_async(args=[run_id], queue="market_data_daily", countdown=i * max(0, int(os.getenv("MARKET_DATA_SYNC_STAGGER_SECONDS", "3"))))
    async with async_session() as db:
        batch = await db.get(MarketDataSyncBatch, scheduled_date)
        batch.dispatched_at = datetime.now(timezone.utc)
        await db.commit()
    return {"status": "DISPATCHED", "count": len(run_ids), "scheduled_date": str(scheduled_date)}


async def _run_and_dispose(coroutine):
    try:
        return await coroutine
    finally:
        await engine.dispose()


@celery_app.task(name="market_data_daily.dispatch")
def dispatch_market_history():
    local_date = datetime.now(ZoneInfo(TIMEZONE)).date()
    return asyncio.run(_run_and_dispose(dispatch_for_date(local_date)))


async def _process_one(run_id: str):
    async with async_session() as db:
        row = (await db.execute(select(MarketDataSyncRun).where(MarketDataSyncRun.id == UUID(run_id)).with_for_update(skip_locked=True))).scalar_one_or_none()
        if row is None:
            return "NOT_FOUND_OR_LOCKED"
        if row.status != "QUEUED":
            return row.status
        config = await db.get(MarketDataSyncConfig, row.feed_id)
        if config is None or config.is_archived or (row.scheduled_date is not None and not config.enabled):
            row.status = "DISABLED"
            row.finished_at = datetime.now(timezone.utc)
            await db.commit()
            return "DISABLED"
        row.status = "RUNNING"
        row.started_at = datetime.now(timezone.utc)
        config.last_status = "RUNNING"
        await db.commit()
        try:
            final_status = await run_sync(db, config, row)
            row.status = final_status
            config.last_status = final_status
            config.last_error = None
            row.finished_at = datetime.now(timezone.utc)
            await db.commit()
            return final_status
        except Exception as exc:
            await db.rollback()
            # refresh after rollback; never persist secrets from upstream exception strings
            row = await db.get(MarketDataSyncRun, UUID(run_id))
            config = await db.get(MarketDataSyncConfig, row.feed_id)
            status, error = safe_error(exc)
            row.status, row.error, row.finished_at = status, error, datetime.now(timezone.utc)
            config.last_status, config.last_error = status, error
            await db.commit()
            logger.warning("Market history run failed: run=%s feed=%s provider=%s stage_code=%s exception_class=%s",
                           run_id, str(config.id), config.provider, error[:140], type(exc).__name__)
            return status


@celery_app.task(name="market_data_daily.process")
def process_market_history(run_id: str):
    return asyncio.run(_run_and_dispose(_process_one(run_id)))


async def _recover_undelivered_batches():
    from datetime import timedelta
    from sqlalchemy import select
    from ...db.models import MarketDataSyncBatch
    today = datetime.now(ZoneInfo(TIMEZONE)).date()
    async with async_session() as db:
        dates = (await db.execute(select(MarketDataSyncBatch.scheduled_date).where(
            MarketDataSyncBatch.dispatched_at.is_(None),
            MarketDataSyncBatch.scheduled_date >= today - timedelta(days=7)))).scalars().all()
    for day in dates:
        await dispatch_for_date(day)


# Recover only when the dedicated scheduler starts/restarts, not in API/live processes.
from celery.signals import beat_init

@beat_init.connect
def _on_history_beat_start(**kwargs):
    if enabled_globally():
        try:
            asyncio.run(_run_and_dispose(_recover_undelivered_batches()))
        except Exception:
            logger.warning("History scheduler will retry undelivered batch on next restart")


async def _process_publish(run_id: str):
    """A separate audit run executes canonical filling on the low-priority history queue."""
    from .feed_publish import publish_all_missing
    async with async_session() as db:
        run = (await db.execute(select(MarketDataSyncRun).where(
            MarketDataSyncRun.id == UUID(run_id)).with_for_update(skip_locked=True))).scalar_one_or_none()
        if run is None or run.status != "QUEUED":
            return "NOT_FOUND_OR_ALREADY_STARTED"
        config = await db.get(MarketDataSyncConfig, run.feed_id)
        if config is None or config.is_archived or not config.is_primary or not config.publish_approved:
            run.status, run.finished_at = "DISABLED", datetime.now(timezone.utc)
            await db.commit()
            return "DISABLED"
        run.status, run.started_at = "RUNNING", datetime.now(timezone.utc)
        config.last_status = "RUNNING"
        await db.commit()
        try:
            status = await publish_all_missing(db, config, run)
            run.status, run.finished_at = status, datetime.now(timezone.utc)
            config.last_status, config.last_error = status, None
            await db.commit()
            logger.info("Canonical missing-candle publish finished run=%s feed=%s status=%s canonical_inserted=%d source_examined=%d",
                        run_id, config.id, status, run.inserted, run.fetched)
            return status
        except Exception as exc:
            await db.rollback()
            run = await db.get(MarketDataSyncRun, UUID(run_id))
            config = await db.get(MarketDataSyncConfig, run.feed_id)
            status, error = safe_error(exc)
            run.status, run.error, run.finished_at = status, error, datetime.now(timezone.utc)
            if config is not None:
                config.last_status, config.last_error = status, error
            await db.commit()
            original = getattr(exc, "orig", exc)
            sqlstate = getattr(original, "sqlstate", None) or getattr(original, "pgcode", None) or "N/A"
            logger.error("Canonical missing-candle publish failed run=%s feed=%s code=%s exception_class=%s sanitized_reason=%s",
                         run_id, run.feed_id, str(sqlstate)[:8], type(exc).__name__, error[:140])
            return status


@celery_app.task(name="market_data_daily.publish_missing")
def process_market_canonical_publish(run_id: str):
    return asyncio.run(_run_and_dispose(_process_publish(run_id)))
