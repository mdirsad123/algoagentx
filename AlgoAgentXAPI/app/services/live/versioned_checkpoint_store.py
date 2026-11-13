"""Append-only checkpoints, with compare-and-swap cursor advancement.

Not an order outbox or task lease implementation. Future workers must also check
their task fencing token in the SAME transaction. All methods are commit-free.
Missing schema, invalid state and stale ownership are errors, never cold fallback.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ...db.models.live_strategy_registry import LiveStrategyCheckpoint, LiveStrategyRuntime
from .incremental_contract import (
    ExecutionIdentity, IncrementalContractError, canonical_json, checkpoint_payload,
    digest_json, utc_timestamp,
)


class StaleCheckpoint(IncrementalContractError):
    pass


async def append_checkpoint(db: AsyncSession, *, identity: ExecutionIdentity, generation: int,
                            expected_sequence: int, expected_cursor: datetime | None,
                            candle_open: datetime, candle_count: int,
                            last_candle: dict, state: dict) -> int:
    if type(expected_sequence) is not int or expected_sequence < 0:
        raise IncrementalContractError("Expected sequence must be nonnegative")
    if (expected_sequence == 0) != (expected_cursor is None):
        raise IncrementalContractError("Initial cursor and sequence must both be empty")
    candle_open = utc_timestamp(candle_open)
    if expected_cursor is not None:
        expected_cursor = utc_timestamp(expected_cursor)
        if candle_open <= expected_cursor:
            raise StaleCheckpoint("Candle must advance the committed cursor")
    sequence = expected_sequence + 1
    payload = checkpoint_payload(identity, generation=generation, sequence=sequence,
        candle_open=candle_open, candle_count=candle_count, last_candle=last_candle, state=state)
    deployment_id, revision_id = UUID(identity.deployment_id), UUID(identity.revision_id)
    # A savepoint makes CAS + insert indivisible even if caller catches an error.
    async with db.begin_nested():
        if expected_sequence:
            previous = await load_checkpoint(db, identity=identity, generation=generation)
            if (previous is None or previous["sequence"] != expected_sequence
                    or candle_count != previous["candle_count"] + 1):
                raise StaleCheckpoint("Each update must advance exactly one stored candle")
        claimed = (await db.execute(update(LiveStrategyRuntime).where(
            LiveStrategyRuntime.deployment_id == deployment_id,
            LiveStrategyRuntime.revision_id == revision_id,
            LiveStrategyRuntime.fingerprint == identity.fingerprint,
            LiveStrategyRuntime.generation == generation,
            LiveStrategyRuntime.state_schema_version == identity.state_schema_version,
            LiveStrategyRuntime.checkpoint_sequence == expected_sequence,
            LiveStrategyRuntime.candle_open == expected_cursor,
            LiveStrategyRuntime.status != "blocked",
        ).values(checkpoint_sequence=sequence, candle_open=candle_open,
                 updated_at=datetime.now(timezone.utc))
            .returning(LiveStrategyRuntime.deployment_id)
            .execution_options(synchronize_session=False))).scalar_one_or_none()
        if claimed is None:
            raise StaleCheckpoint("Stale generation, fingerprint, cursor or sequence; checkpoint rejected")
        db.add(LiveStrategyCheckpoint(
            deployment_id=deployment_id, generation=generation, sequence=sequence,
            revision_id=revision_id, candle_open=candle_open,
            payload=payload, payload_sha256=digest_json(payload),
        ))
        await db.flush()
    return sequence


async def load_checkpoint(db: AsyncSession, *, identity: ExecutionIdentity,
                          generation: int) -> dict | None:
    """Return detached verified JSON. None means this generation has no state yet."""
    r, c = LiveStrategyRuntime.__table__, LiveStrategyCheckpoint.__table__
    row = (await db.execute(select(
        r.c.revision_id, r.c.fingerprint, r.c.generation, r.c.checkpoint_sequence,
        r.c.candle_open, r.c.state_schema_version, r.c.status,
        c.c.payload, c.c.payload_sha256,
    ).select_from(r.outerjoin(c, (c.c.deployment_id == r.c.deployment_id)
        & (c.c.generation == r.c.generation) & (c.c.sequence == r.c.checkpoint_sequence)))
        .where(r.c.deployment_id == UUID(identity.deployment_id)))).mappings().one_or_none()
    if row is None or row["fingerprint"] != identity.fingerprint or row["generation"] != generation:
        raise StaleCheckpoint("Runtime identity changed or is missing")
    if str(row["revision_id"]) != identity.revision_id or row["state_schema_version"] != identity.state_schema_version:
        raise StaleCheckpoint("Runtime revision or state schema changed")
    if row["status"] == "blocked":
        raise IncrementalContractError("Unsupported deployment cannot restore state")
    if row["checkpoint_sequence"] == 0:
        if row["candle_open"] is not None:
            raise IncrementalContractError("Empty checkpoint has a nonempty cursor")
        return None
    payload = row["payload"]
    if not isinstance(payload, dict) or digest_json(payload) != row["payload_sha256"]:
        raise IncrementalContractError("Checkpoint checksum mismatch or missing history")
    # SQLite loses tzinfo in isolated tests; PostgreSQL DateTime(timezone=True)
    # returns aware UTC values. The payload itself always requires explicit UTC.
    cursor = row["candle_open"]
    if cursor is not None and cursor.tzinfo is None and db.get_bind().dialect.name == "sqlite":
        cursor = cursor.replace(tzinfo=timezone.utc)
    try:
        expected = checkpoint_payload(identity, generation=generation,
            sequence=row["checkpoint_sequence"], candle_open=cursor,
            candle_count=payload["candle_count"], last_candle=payload["last_candle"], state=payload["state"])
    except (KeyError, TypeError, ValueError) as exc:
        raise IncrementalContractError("Invalid checkpoint envelope") from exc
    if (expected != payload or str(row["revision_id"]) != identity.revision_id
            or row["state_schema_version"] != identity.state_schema_version):
        raise IncrementalContractError("Checkpoint envelope does not match runtime identity")
    return json.loads(canonical_json(payload))