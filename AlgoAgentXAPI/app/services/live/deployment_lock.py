"""Shared PostgreSQL advisory-lock helpers for one live deployment.

The event pipeline has several independent processes (strategy, reconcile and API
sync requests) that may touch the same deployment/order/position rows.  They all
must use the same lock key so a slow reconciliation cannot interleave with the
strategy transaction and create PostgreSQL deadlocks.
"""

from __future__ import annotations

import hashlib
from contextlib import asynccontextmanager
from functools import wraps
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


def deployment_lock_key(deployment_id: UUID | str) -> int:
    """Return a stable signed 64-bit PostgreSQL advisory lock key."""
    digest = hashlib.sha256(str(deployment_id).encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big", signed=True)


def deployment_worker_index(deployment_id: UUID | str, workers: int) -> int:
    if workers < 1:
        raise ValueError("Worker count must be positive")
    return deployment_lock_key(deployment_id) % workers


@asynccontextmanager
async def deployment_run_lock(db: AsyncSession, deployment_id: UUID | str):
    # Dedicated session lock survives commits inside broker/copy execution.
    # Separate namespace avoids conflicting with the existing transaction lock.
    engine = db.bind
    async with engine.connect() as connection:
        key = deployment_lock_key(f"runner:{deployment_id}")
        try:
            acquired = bool((await connection.execute(
                text("SELECT pg_try_advisory_lock(:key)"), {"key": key},
            )).scalar())
            await connection.commit()
            yield acquired
        finally:
            try:
                await connection.rollback()
                await connection.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": key})
                await connection.commit()
            except BaseException:
                # Never return a possibly locked socket to the connection pool.
                await connection.invalidate()
                raise


def serialize_deployment_run(run):
    @wraps(run)
    async def guarded(db, deployment_id, *args, **kwargs):
        async with deployment_run_lock(db, deployment_id) as acquired:
            if not acquired:
                return {"success": True, "deployment_id": str(deployment_id),
                        "executed": False, "duplicate": True, "final_action": "LOCK_SKIPPED",
                        "message": "Another runner is already processing this deployment."}
            try:
                return await run(db, deployment_id, *args, **kwargs)
            except BaseException:
                from .retained_strategy_state import retained_states
                retained_states.invalidate(str(deployment_id), 'runner_aborted')
                raise
    return guarded


async def try_deployment_xact_lock(db: AsyncSession, deployment_id: UUID | str) -> bool:
    """Try to serialize DB state changes for a deployment in this transaction."""
    return bool(
        (
            await db.execute(
                text("SELECT pg_try_advisory_xact_lock(:key)"),
                {"key": deployment_lock_key(deployment_id)},
            )
        ).scalar()
    )
