"""Native incremental JSON checkpoint persistence.

Only strategies implementing the public native contract use this store. All
records are keyed by deployment + source/runtime fingerprint, and are written
inside the same caller transaction as the candle cursor when possible.
"""
from __future__ import annotations

from hashlib import sha256
import json
import logging
from typing import Any

import pandas as pd
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from .retained_strategy_state import RetainedEntry, canonical_candle, candle_fingerprint, retained_states, utc, MAX_RETAINED

log = logging.getLogger(__name__)


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _missing_table(exc: DBAPIError) -> bool:
    return getattr(exc.orig, 'sqlstate', None) == '42P01'


async def read_checkpoint(db, deployment_id: str, fingerprint: str, source_sha: str, last_processed) -> dict | None:
    try:
        async with db.begin_nested():
            row = (await db.execute(text("""
        SELECT candle_open, candle_count, state_schema_version, last_candle, state_json, state_sha256
        FROM live_incremental_checkpoints
        WHERE deployment_id=:id AND fingerprint=:fp AND source_sha256=:sha
            """), {"id": str(deployment_id), "fp": fingerprint, "sha": source_sha})).mappings().first()
    except DBAPIError as exc:
        if not _missing_table(exc):
            raise
        log.warning("NATIVE_INCREMENTAL_CHECKPOINT_UNAVAILABLE deployment=%s reason=missing_table", deployment_id)
        return None
    if not row or utc(row["candle_open"]) != utc(last_processed):
        return None
    try:
        data = row["state_json"]
        if sha256(_canonical(data).encode()).hexdigest() != row["state_sha256"]:
            raise ValueError("checkpoint checksum mismatch")
        return dict(row)
    except (ValueError, TypeError):
        log.warning("NATIVE_INCREMENTAL_CHECKPOINT_INVALID deployment=%s", deployment_id)
        return None


async def restore_native_checkpoint(db, *, deployment_id: str, fingerprint: str,
                                    source_sha: str, last_processed,
                                    strategy_class: type, params: dict, prior_candle: dict,
                                    fields: dict, observed_capital: str) -> bool:
    saved = await read_checkpoint(db, deployment_id, fingerprint, source_sha, last_processed)
    if saved is None:
        return False
    try:
        candle = canonical_candle(saved["last_candle"])
        if utc(candle['Date']) != utc(last_processed) or int(saved['candle_count']) < 1:
            raise ValueError("Checkpoint cursor/count mismatch")
        if candle_fingerprint(candle) != candle_fingerprint(prior_candle):
            raise ValueError("Last closed broker candle changed")
        canonical = pd.DataFrame([candle])
        if int(saved["state_schema_version"]) != int(getattr(strategy_class, "LIVE_INCREMENTAL_STATE_SCHEMA_VERSION", 1)):
            raise ValueError("State schema version mismatch")
        restored = strategy_class(canonical, **params)
        restored.restore(saved["state_json"], {"interface_version": 1, "restored": True})
        if _canonical(restored.snapshot()) != _canonical(saved['state_json']):
            raise ValueError("Restored state does not round-trip")
        if len(retained_states._entries) >= MAX_RETAINED:
            retained_states._entries.pop(next(iter(retained_states._entries)))
        retained_states._entries[str(deployment_id)] = RetainedEntry(
            fingerprint=fingerprint, candle_time=utc(saved["candle_open"]),
            strategy=restored, candle_count=int(saved["candle_count"]),
            last_candle_fingerprint=candle_fingerprint(candle),
            fields=dict(fields), last_candle=dict(candle), observed_capital=observed_capital,
        )
        log.info("NATIVE_INCREMENTAL_RESTORED deployment=%s bars=%s", deployment_id, saved["candle_count"])
        return True
    except Exception:
        log.exception("NATIVE_INCREMENTAL_RESTORE_FAILED deployment=%s", deployment_id)
        return False


async def stage_native_checkpoint(db, *, deployment_id: str, fingerprint: str,
                                  source_sha: str, candle_time) -> bool:
    entry = retained_states._entries.get(str(deployment_id))
    if entry is None or not bool(getattr(entry.strategy, "LIVE_INCREMENTAL_NATIVE", False)):
        return False
    if entry.fingerprint != fingerprint or utc(entry.candle_time) != utc(candle_time):
        return False
    try:
        state = entry.strategy.snapshot()
        encoded = _canonical(state)
        last_candle = canonical_candle(entry.last_candle)
        last_candle['Date'] = last_candle['Date'].isoformat()
        async with db.begin_nested():
            await db.execute(text("""
            INSERT INTO live_incremental_checkpoints
                (deployment_id, source_sha256, fingerprint, candle_open, candle_count,
                 state_schema_version, last_candle, state_json, state_sha256, updated_at)
            VALUES (:id, :sha, :fp, :candle, :bars, :schema, CAST(:last AS jsonb),
                    CAST(:state AS jsonb), :checksum, NOW())
            ON CONFLICT (deployment_id) DO UPDATE SET
                source_sha256=EXCLUDED.source_sha256,
                fingerprint=EXCLUDED.fingerprint,
                candle_open=EXCLUDED.candle_open,
                candle_count=EXCLUDED.candle_count,
                state_schema_version=EXCLUDED.state_schema_version,
                last_candle=EXCLUDED.last_candle,
                state_json=EXCLUDED.state_json,
                state_sha256=EXCLUDED.state_sha256,
                updated_at=NOW()
        """), {
            "id": str(deployment_id), "sha": source_sha, "fp": fingerprint,
            "candle": utc(candle_time), "bars": entry.candle_count,
            "schema": int(getattr(entry.strategy, "LIVE_INCREMENTAL_STATE_SCHEMA_VERSION", 1)),
            "last": _canonical(last_candle), "state": encoded,
            "checksum": sha256(encoded.encode()).hexdigest(),
        })
        return True
    except DBAPIError as exc:
        if not _missing_table(exc):
            raise
        log.warning("NATIVE_INCREMENTAL_CHECKPOINT_UNAVAILABLE deployment=%s reason=missing_table", deployment_id)
        return False
    except (TypeError, ValueError):
        # Invalid JSON state is an author contract violation, not permission to
        # affect broker execution. Log and continue; next restart may cold-warm.
        log.exception("NATIVE_INCREMENTAL_SNAPSHOT_NOT_JSON deployment=%s", deployment_id)
        return False
