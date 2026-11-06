"""PostgreSQL-owned execution. Redis is delivery, never the source of truth.

A session advisory lock prevents concurrent owners. Every attempt receives a
monotonic fence; finalization locks and checks that fence in the same transaction
as results, charges and completed status. The heartbeat uses the lock connection
so losing the connection stops cooperative work; it never silently reconnects.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import socket
from contextvars import ContextVar
from pathlib import Path
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool
from sqlalchemy.exc import DBAPIError

from app.core.config import settings
from app.services.backtest_control import ExecutionControl, BacktestInterrupted, current_control

logger = logging.getLogger(__name__)
current_claim = ContextVar("backtest_job_claim", default=None)
TERMINAL = {"completed", "failed", "cancelled"}


def lock_key(job_id):
    return int.from_bytes(hashlib.sha256(("backtest:" + str(job_id)).encode()).digest()[:8], "big", signed=True)


def memory_metrics():
    metrics = {}
    try:
        for line in Path("/proc/self/status").read_text().splitlines():
            if line.startswith(("VmRSS:", "VmHWM:")):
                key, value, _ = line.split()
                metrics["rss_bytes" if key == "VmRSS:" else "peak_rss_bytes"] = int(value) * 1024
    except OSError:
        pass
    return metrics


def execution_engine():
    return create_async_engine(settings.database_url, poolclass=NullPool,
                              connect_args={"command_timeout": 15, "timeout": 10})


async def register_job(db, job_id):
    await db.execute(text("INSERT INTO backtest_execution (job_id) VALUES (:job) ON CONFLICT (job_id) DO NOTHING"), {"job": job_id})


async def dispatch_job(job_id):
    from app.backtest_celery import backtest_app
    # Only a durable job identifier travels over Redis. Parameters come from PG.
    await asyncio.to_thread(backtest_app.send_task, "app.tasks.run_backtest_v2_task",
                            args=[str(job_id)], queue="backtest", retry=False)


async def request_cancellation(db, job_id, user_id):
    """Internal service API; caller must authorize. Does not revoke/kill workers."""
    result = await db.execute(text("""
        UPDATE backtest_execution e SET cancel_requested=true
        FROM job_status j WHERE j.id=e.job_id AND j.id=:job
          AND CAST(j.user_id AS text)=:user AND j.status IN ('queued','pending','running','retry')
        RETURNING e.job_id
    """), {"job": str(job_id), "user": str(user_id)})
    return result.scalar_one_or_none() is not None


class JobClaim:
    def __init__(self, connection, job_id, owner, fence, control):
        self.connection = connection
        self.job_id = job_id
        self.owner = owner
        self.fence = fence
        self.control = control

    async def heartbeat(self):
        while True:
            await asyncio.sleep(10)
            try:
                telemetry = {**self.control.snapshot(), **memory_metrics()}
                result = await self.connection.execute(text("""
                    UPDATE backtest_execution SET heartbeat_at=now(), stage=:stage,
                        telemetry=CAST(:telemetry AS json)
                    WHERE job_id=:job AND fence=:fence AND owner=:owner
                    RETURNING cancel_requested
                """), {"job": self.job_id, "owner": self.owner, "fence": self.fence,
                       "stage": telemetry["stage"], "telemetry": json.dumps(telemetry)})
                cancelled = result.scalar_one()
                await self.connection.commit()
                if cancelled:
                    self.control.reason = "Cancellation requested"
                    self.control.stopped.set()
                    return
                logger.info("Backtest telemetry job=%s attempt_fence=%s metrics=%s", self.job_id, self.fence, telemetry)
            except Exception:
                self.control.reason = "Database ownership heartbeat failed"
                self.control.stopped.set()
                logger.exception("Backtest ownership heartbeat failed job=%s", self.job_id)
                return

    async def finalize_guard(self, db):
        self.control.checkpoint("finalizing")
        row = (await db.execute(text("""
            SELECT fence, owner, cancel_requested FROM backtest_execution
            WHERE job_id=:job FOR UPDATE
        """), {"job": self.job_id})).mappings().one()
        if row["fence"] != self.fence or row["owner"] != self.owner or row["cancel_requested"]:
            raise BacktestInterrupted("Finalization fenced or cancellation requested")
        await db.execute(text("""
            UPDATE backtest_execution SET stage='completed', heartbeat_at=now(),
                telemetry=CAST(:telemetry AS json) WHERE job_id=:job
        """), {"job": self.job_id, "telemetry": json.dumps({**self.control.snapshot(), **memory_metrics()})})


async def guard_finalization(db):
    claim = current_claim.get()
    if claim is not None:
        await claim.finalize_guard(db)


async def execute_job(job_id, session_factory, execute):
    lock_engine = execution_engine()
    control = ExecutionControl()
    owner = f"{socket.gethostname()}:{os.getpid()}:{uuid4()}"
    heartbeat = None
    control_token = claim_token = None
    try:
        async with lock_engine.connect() as conn:
            acquired = (await conn.execute(text("SELECT pg_try_advisory_lock(:key)"), {"key": lock_key(job_id)})).scalar()
            await conn.commit()
            if not acquired:
                return {"job_id": job_id, "status": "already_owned"}
            try:
                job = (await conn.execute(text("""
                    SELECT j.status, j.user_id, j.job_data, j.result_data, e.attempts,
                           e.max_attempts, e.cancel_requested
                    FROM job_status j JOIN backtest_execution e ON e.job_id=j.id
                    WHERE j.id=:job FOR UPDATE OF e
                """), {"job": job_id})).mappings().one_or_none()
                if job is None:
                    raise RuntimeError("Backtest job is not registered for durable execution")
                if job["status"] in TERMINAL:
                    await conn.rollback()
                    return {"job_id": job_id, "status": job["status"]}
                if job["cancel_requested"] or job["attempts"] >= job["max_attempts"]:
                    status = "cancelled" if job["cancel_requested"] else "failed"
                    reason = "Cancellation requested" if status == "cancelled" else "Crash recovery attempt limit reached"
                    await conn.execute(text("UPDATE job_status SET status=:status, message=:reason, completed_at=now() WHERE id=:job"),
                                       {"job": job_id, "status": status, "reason": reason})
                    await conn.execute(text("UPDATE backtest_execution SET stage=:status, failure_reason=:reason WHERE job_id=:job"),
                                       {"job": job_id, "status": status, "reason": reason})
                    await conn.commit()
                    return {"job_id": job_id, "status": status}
                fence = (await conn.execute(text("""
                    UPDATE backtest_execution SET fence=fence+1, attempts=attempts+1,
                        owner=:owner, heartbeat_at=now(), stage='initializing', failure_reason=NULL
                    WHERE job_id=:job RETURNING fence
                """), {"job": job_id, "owner": owner})).scalar_one()
                await conn.execute(text("""
                    UPDATE job_status SET status='running', retry_count=:attempt,
                        started_at=COALESCE(started_at,now()), updated_at=now() WHERE id=:job
                """), {"job": job_id, "attempt": job["attempts"]})
                await conn.commit()
                claim = JobClaim(conn, job_id, owner, fence, control)
                control_token = current_control.set(control)
                claim_token = current_claim.set(claim)
                heartbeat = asyncio.create_task(claim.heartbeat())
                payload = json.loads(job["job_data"])
                plan_code = payload.pop("_plan_code", None)
                try:
                    async with session_factory() as db:
                        return await execute(db, str(job["user_id"]), payload, plan_code)
                except Exception as exc:
                    # Session closes/rolls back before terminal state. A SIGKILL
                    # leaves RUNNING for the dispatcher, not an unbounded retry.
                    async with session_factory() as db:
                        row = (await db.execute(text("SELECT fence, cancel_requested FROM backtest_execution WHERE job_id=:job FOR UPDATE"),
                                                {"job": job_id})).mappings().one()
                        if row["fence"] == fence:
                            transient = isinstance(exc, (ConnectionError, TimeoutError, DBAPIError))
                            status = "cancelled" if row["cancel_requested"] else (
                                "queued" if transient and job["attempts"] + 1 < job["max_attempts"] else "failed")
                            reason = f"{type(exc).__name__}: {getattr(exc, 'detail', None) or exc}"[:4000]
                            await db.execute(text("UPDATE job_status SET status=:status, message=:reason, completed_at=CASE WHEN :status='queued' THEN NULL ELSE now() END WHERE id=:job AND status <> 'completed'"),
                                             {"job": job_id, "status": status, "reason": reason})
                            await db.execute(text("UPDATE backtest_execution SET failure_reason=:reason, stage=:status, dispatched_at=now() WHERE job_id=:job AND stage <> 'completed'"),
                                             {"job": job_id, "status": status, "reason": reason})
                            await db.commit()
                    raise
            finally:
                if heartbeat is not None:
                    heartbeat.cancel()
                    try:
                        await heartbeat
                    except asyncio.CancelledError:
                        pass
                # NullPool ensures the session lock cannot leak into another job.
                try:
                    await conn.rollback()
                    await conn.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": lock_key(job_id)})
                    await conn.commit()
                except Exception:
                    await conn.invalidate()
    finally:
        if control_token is not None:
            current_control.reset(control_token)
        if claim_token is not None:
            current_claim.reset(claim_token)
        await lock_engine.dispose()


async def recover_jobs():
    """Recover jobs without flooding Redis with copies of valid waiting tasks.

    A newly created job is dispatched once. Queued tasks are *not* automatically
    resent while waiting for a busy worker; otherwise one multi-hour backtest
    generates hundreds of duplicate messages. An abandoned RUNNING job can be
    resubmitted only after its heartbeat has expired AND its advisory lock is
    no longer held. Redis reconnects can deliver an additional copy; the
    execution claim makes that delivery a no-op.

    The only reconciliation of an old, already dispatched QUEUED task requires
    an explicit operator action, since PostgreSQL cannot prove that the broker
    still holds or has lost the waiting message.
    """
    engine = execution_engine()
    try:
        async with engine.connect() as conn:
            rows = (await conn.execute(text("""
                SELECT e.job_id, j.status, e.attempts, e.max_attempts,
                       e.cancel_requested, e.dispatched_at, e.heartbeat_at
                FROM backtest_execution e JOIN job_status j ON j.id=e.job_id
                WHERE j.status IN ('queued','pending','running','retry')
                  AND (
                      (j.status IN ('queued','pending','retry') AND e.dispatched_at IS NULL)
                      OR (j.status='running'
                          AND e.heartbeat_at < now() - interval '120 seconds'
                          AND (e.dispatched_at IS NULL
                               OR e.dispatched_at < now() - interval '120 seconds'))
                  )
                ORDER BY e.created_at LIMIT 100
            """))).mappings().all()
            await conn.commit()
            for row in rows:
                job_id = row["job_id"]
                acquired = (await conn.execute(text("SELECT pg_try_advisory_lock(:key)"),
                                               {"key": lock_key(job_id)})).scalar()
                await conn.commit()
                if not acquired:
                    continue
                try:
                    # Recheck under a row lock after the advisory lock: an
                    # unrelated worker may have completed/claimed the job.
                    state = (await conn.execute(text("""
                        SELECT e.attempts, e.max_attempts, e.cancel_requested,
                               e.dispatched_at, e.heartbeat_at, j.status
                        FROM backtest_execution e JOIN job_status j ON j.id=e.job_id
                        WHERE e.job_id=:job FOR UPDATE OF e
                    """), {"job": job_id})).mappings().one_or_none()
                    if not state or state["status"] in TERMINAL:
                        await conn.rollback()
                        continue
                    if state["cancel_requested"] or state["attempts"] >= state["max_attempts"]:
                        status = "cancelled" if state["cancel_requested"] else "failed"
                        reason = ("Cancellation requested" if status == "cancelled"
                                  else "Backtest crash recovery attempt limit reached")
                        await conn.execute(text("""
                            UPDATE job_status SET status=:status, message=:reason,
                                completed_at=now(), updated_at=now()
                            WHERE id=:job AND status NOT IN ('completed','failed','cancelled')
                        """), {"job": job_id, "status": status, "reason": reason})
                        await conn.execute(text("""
                            UPDATE backtest_execution SET stage=:status, failure_reason=:reason
                            WHERE job_id=:job
                        """), {"job": job_id, "status": status, "reason": reason})
                        await conn.commit()
                        continue
                    if state["status"] in ("queued", "pending", "retry"):
                        should_dispatch = state["dispatched_at"] is None
                    else:
                        from datetime import datetime, timedelta, timezone
                        now = datetime.now(timezone.utc)
                        hb = state["heartbeat_at"]
                        sent = state["dispatched_at"]
                        should_dispatch = (hb is not None and hb < now - timedelta(seconds=120)
                                           and (sent is None or sent < now - timedelta(seconds=120)))
                    if not should_dispatch:
                        await conn.rollback()
                        continue
                    # Commit the read transaction before invoking external broker.
                    await conn.commit()
                    await dispatch_job(job_id)
                    await conn.execute(text("""
                        UPDATE backtest_execution SET dispatched_at=now()
                        WHERE job_id=:job
                    """), {"job": job_id})
                    await conn.commit()
                finally:
                    await conn.rollback()
                    await conn.execute(text("SELECT pg_advisory_unlock(:key)"),
                                       {"key": lock_key(job_id)})
                    await conn.commit()
    finally:
        await engine.dispose()
