"""Actual PostgreSQL connections/locks/transactions against an isolated DB only."""
import asyncio
import json
import os
from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.services import backtest_jobs as jobs
from app.services.backtest_control import BacktestInterrupted
from app.services.backtest_equity import persist_equity_events

URL = os.getenv("BACKTEST_TEST_DATABASE_URL", "")
pytestmark = pytest.mark.skipif("backtest_repair_test" not in URL, reason="Explicit isolated PostgreSQL required")


async def setup(monkeypatch):
    engine = create_async_engine(URL, poolclass=NullPool)
    monkeypatch.setattr(jobs, "execution_engine", lambda: create_async_engine(URL, poolclass=NullPool))
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    job = str(uuid4())
    async with engine.begin() as conn:
        await conn.execute(text("INSERT INTO job_status (id,user_id,status,job_data) VALUES (:job,'test-user','queued','{}')"), {"job": job})
        await conn.execute(text("INSERT INTO backtest_execution (job_id) VALUES (:job)"), {"job": job})
    return engine, sessions, job


def test_concurrent_delivery_and_completed_replay(monkeypatch):
    async def run():
        engine, sessions, job = await setup(monkeypatch)
        entered, release = asyncio.Event(), asyncio.Event()
        calls = 0
        async def execute(db, user, payload, plan):
            nonlocal calls
            calls += 1
            entered.set()
            await release.wait()
            await jobs.guard_finalization(db)
            await db.execute(text("UPDATE job_status SET status='completed' WHERE id=:job"), {"job": job})
            await db.commit()
            return {"status": "completed"}
        first = asyncio.create_task(jobs.execute_job(job, sessions, execute))
        await entered.wait()
        assert (await jobs.execute_job(job, sessions, execute))["status"] == "already_owned"
        release.set()
        await first
        assert (await jobs.execute_job(job, sessions, execute))["status"] == "completed"
        assert calls == 1
        await engine.dispose()
    asyncio.run(run())


def test_fencing_rolls_back_result_and_charge_effect_together(monkeypatch):
    async def run():
        engine, sessions, job = await setup(monkeypatch)
        async def execute(db, *args):
            await persist_equity_events(db, job, SimpleNamespace(equity_curve=[100., 90.], equity_timestamps=[datetime(2026, 1, 1)] * 2))
            # Simulates ownership changing after a connection loss. No stale
            # result or financial side effect may survive finalization.
            async with engine.begin() as conn:
                await conn.execute(text("UPDATE backtest_execution SET fence=fence+1 WHERE job_id=:job"), {"job": job})
            await jobs.guard_finalization(db)
        with pytest.raises(BacktestInterrupted):
            await jobs.execute_job(job, sessions, execute)
        async with engine.connect() as conn:
            assert (await conn.execute(text("SELECT count(*) FROM equity_curve WHERE backtest_id=:job"), {"job": job})).scalar() == 0
        await engine.dispose()
    asyncio.run(run())


def test_abandoned_connection_releases_lock_and_attempts_are_bounded(monkeypatch):
    async def run():
        engine, sessions, job = await setup(monkeypatch)
        old = await engine.connect()
        await old.execute(text("SELECT pg_advisory_lock(:key)"), {"key": jobs.lock_key(job)})
        await old.commit()
        async def unexpected(*args):
            raise AssertionError("Must not compute")
        assert (await jobs.execute_job(job, sessions, unexpected))["status"] == "already_owned"
        # Physical session disposal models the PostgreSQL side of worker death.
        await old.close()
        async with engine.begin() as conn:
            await conn.execute(text("UPDATE backtest_execution SET attempts=max_attempts WHERE job_id=:job"), {"job": job})
        assert (await jobs.execute_job(job, sessions, unexpected))["status"] == "failed"
        assert (await jobs.execute_job(job, sessions, unexpected))["status"] == "failed"
        await engine.dispose()
    asyncio.run(run())


def test_duplicate_equity_and_atomic_commit(monkeypatch):
    async def run():
        engine, sessions, job = await setup(monkeypatch)
        async def execute(db, *args):
            data = SimpleNamespace(equity_curve=[100., 90., 110.], equity_timestamps=[datetime(2026, 1, 1)] * 3)
            await persist_equity_events(db, job, data, batch_size=2)
            await jobs.guard_finalization(db)
            await db.execute(text("UPDATE job_status SET status='completed' WHERE id=:job"), {"job": job})
            await db.commit()
        await jobs.execute_job(job, sessions, execute)
        await jobs.execute_job(job, sessions, execute)
        async with engine.connect() as conn:
            rows = (await conn.execute(text("SELECT event_sequence,equity FROM equity_curve WHERE backtest_id=:job ORDER BY event_sequence"), {"job": job})).all()
            assert [(r[0], float(r[1])) for r in rows] == [(0,100.),(1,90.),(2,110.)]
        await engine.dispose()
    asyncio.run(run())


def test_requested_cancellation_never_computes(monkeypatch):
    async def run():
        engine, sessions, job = await setup(monkeypatch)
        async with engine.begin() as conn:
            await conn.execute(text("UPDATE backtest_execution SET cancel_requested=true WHERE job_id=:job"), {"job": job})
        async def unexpected(*args):
            raise AssertionError("Cancelled job computed")
        assert (await jobs.execute_job(job, sessions, unexpected))["status"] == "cancelled"
        await engine.dispose()
    asyncio.run(run())


def test_broker_disconnect_keeps_durable_job_and_reconnect_dispatches(monkeypatch):
    async def run():
        engine, sessions, job = await setup(monkeypatch)
        async def offline(*args):
            raise ConnectionError("isolated broker unavailable")
        monkeypatch.setattr(jobs, "dispatch_job", offline)
        with pytest.raises(ConnectionError):
            await jobs.recover_jobs()
        delivered = []
        async def online(job_id):
            delivered.append(job_id)
        monkeypatch.setattr(jobs, "dispatch_job", online)
        await jobs.recover_jobs()
        assert job in delivered
        await engine.dispose()
    asyncio.run(run())