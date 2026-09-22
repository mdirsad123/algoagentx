"""Shared PostgreSQL advisory-lock helpers for one live deployment.

The event pipeline has several independent processes (strategy, reconcile and API
sync requests) that may touch the same deployment/order/position rows.  They all
must use the same lock key so a slow reconciliation cannot interleave with the
strategy transaction and create PostgreSQL deadlocks.
"""

from __future__ import annotations

import hashlib
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


def deployment_lock_key(deployment_id: UUID | str) -> int:
    """Return a stable signed 64-bit PostgreSQL advisory lock key."""
    digest = hashlib.sha256(str(deployment_id).encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big", signed=True)


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
