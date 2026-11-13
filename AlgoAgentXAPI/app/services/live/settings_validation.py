"""Configuration equality and source-pinned compatibility evidence for settings.

Ordinary settings writes never execute a strategy. Enabling Auto Trade requires
recent deep evidence for the saved configuration plus a fresh lightweight check.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from decimal import Decimal
from pathlib import Path
from functools import lru_cache

from fastapi import HTTPException
from sqlalchemy import select
import redis.asyncio as aioredis

from ...core.redis_manager import redis_manager
from ...core.config import settings

logger = logging.getLogger(__name__)
from ...db.models import Strategy, StrategyRuntimePreset

COMPATIBILITY_TTL = 900
NON_EXECUTION_FIELDS = {
    'name', 'status', 'tradingview_secret', 'auto_trade_enabled',
    'auto_runner_enabled', 'copy_trading_enabled', 'copy_broker_account_ids',
}


@lru_cache(maxsize=1)
def bundled_strategy_digest() -> str:
    # API and validation worker may run different images during a deployment.
    # Never let DB source alone authorize evidence from different bundled code.
    root = Path(__file__).resolve().parents[3]
    digest = hashlib.sha256()
    for path in sorted((root / 'strategies').glob('*.py')):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    for relative in ('app/services/strategy_registry.py', 'app/services/dynamic_strategy_loader.py'):
        digest.update((root / relative).read_bytes())
    return digest.hexdigest()


def changed_settings(row, values: dict) -> dict:
    def equal(current, incoming):
        if current is None or incoming is None:
            return current is incoming
        if isinstance(current, (list, dict)):
            return current == incoming or json.dumps(current, default=str, sort_keys=True) == json.dumps(incoming, default=str, sort_keys=True)
        if isinstance(current, Decimal):
            return current == Decimal(str(incoming))
        return str(current) == str(incoming)
    return {key: value for key, value in values.items()
            if not equal(getattr(row, key, None), value)}


async def configuration_fingerprint(db, row, overrides: dict | None = None) -> str:
    from ...schemas.live_trading import StrategyDeploymentUpdate
    strategy = (await db.execute(select(Strategy).where(Strategy.id == row.strategy_id))).scalar_one_or_none()
    preset = (await db.execute(select(StrategyRuntimePreset).where(
        StrategyRuntimePreset.strategy_id == row.strategy_id,
        StrategyRuntimePreset.is_default.is_(True), StrategyRuntimePreset.is_active.is_(True),
    ))).scalar_one_or_none()
    def canonical(value):
        if isinstance(value, (Decimal, float, int)) and not isinstance(value, bool):
            return format(Decimal(str(value)).normalize(), 'f')
        if isinstance(value, dict):
            return {str(key): canonical(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [canonical(item) for item in value]
        return str(value) if value is not None else None

    values = {name: canonical(getattr(row, name, None)) for name in StrategyDeploymentUpdate.model_fields
              if name not in NON_EXECUTION_FIELDS}
    values.update({name: canonical(value) for name, value in (overrides or {}).items() if name not in NON_EXECUTION_FIELDS})
    source = [str(row.id), str(row.strategy_id), getattr(strategy, 'name', None),
              getattr(strategy, 'parameters', None), getattr(strategy, 'default_runtime_config', None),
              getattr(strategy, 'config_version', None), getattr(preset, 'config_json', None),
              bundled_strategy_digest(), values]
    return hashlib.sha256(json.dumps(source, sort_keys=True, default=str).encode()).hexdigest()


async def require_compatibility_evidence(db, row, values: dict) -> None:
    """Fail-closed Auto Trade authorization with revalidation of existing deep proof.

    The first 80K output verification is still mandatory. If its short-lived
    approval has expired/disappeared, an unchanged source/config can renew it
    by performing a *fresh* lightweight check against the cached verified
    dynamic-output contract. Changed execution settings NEVER inherit proof.
    """
    fingerprint = await configuration_fingerprint(db, row, values)
    # A changed SL/TP/risk/instrument/config cannot borrow the current saved
    # configuration's verification, even if only a single field changed.
    saved_fingerprint = await configuration_fingerprint(db, row)

    client = redis_manager.client
    owns_client = client is None
    if owns_client:
        # The dry-test worker writes evidence using settings.redis_url directly.
        # Use the same Redis DB even if the API's optional shared manager has
        # not recovered from a transient disconnection.
        client = aioredis.from_url(settings.redis_url, socket_connect_timeout=2, socket_timeout=2)
    reason = "approval_missing_or_expired"
    try:
        raw = await asyncio.wait_for(client.get(f'live:compatibility:approved:{row.id}'), 3)
        try:
            evidence = json.loads(raw) if raw else {}
        except (ValueError, TypeError):
            evidence = {}
        if isinstance(evidence, dict) and evidence.get('fingerprint') == fingerprint and evidence.get('status') in {'PASS', 'WARNING'}:
            return

        if isinstance(evidence, dict) and evidence.get('fingerprint'):
            reason = 'approval_config_mismatch'
        if saved_fingerprint != fingerprint:
            reason = 'execution_settings_changed_since_verification'
        else:
            # Do NOT accept an old UI PASS alone: require the server-side,
            # source-pinned deep proof (7-day TTL) plus fresh broker/runtime,
            # history coverage and strategy-contract checks at save time.
            from .compatibility_cache import reuse_deep_cache
            from .compatibility_service import run_live_compatibility_check
            deep_raw = await asyncio.wait_for(client.get(f'live:compatibility:deep_verified:{row.id}'), 3)
            try:
                deep_proof = json.loads(deep_raw) if deep_raw else None
            except (ValueError, TypeError):
                deep_proof = None
            if deep_proof is None:
                reason = 'deep_proof_missing_or_expired'
            elif not isinstance(deep_proof, dict) or deep_proof.get('fingerprint') != fingerprint:
                reason = 'deep_proof_source_or_settings_mismatch'
            else:
                lightweight = await run_live_compatibility_check(db, row.id, deep_strategy_check=False)
                result = reuse_deep_cache(fingerprint, lightweight, deep_proof)
                if result is not None and result.get('status') in {'PASS', 'WARNING'}:
                    await asyncio.wait_for(client.set(
                        f'live:compatibility:approved:{row.id}',
                        json.dumps({'fingerprint': fingerprint, 'status': result['status']}),
                        ex=COMPATIBILITY_TTL,
                    ), 3)
                    logger.info('AUTO_TRADE_COMPATIBILITY_REVALIDATED deployment=%s mode=verified_output_plus_fresh_lightweight', row.id)
                    return
                reason = 'fresh_lightweight_compatibility_failed'
    except Exception as exc:
        logger.warning('AUTO_TRADE_COMPATIBILITY_EVIDENCE_UNAVAILABLE deployment=%s error_type=%s', row.id, type(exc).__name__)
        reason = 'redis_or_compatibility_check_unavailable'
    finally:
        if owns_client:
            await client.aclose()

    logger.warning('AUTO_TRADE_COMPATIBILITY_REJECTED deployment=%s reason=%s', row.id, reason)
    raise HTTPException(status_code=409, detail=(
        f'Auto Trade compatibility approval unavailable ({reason}). '
        'Keep Auto Trade off, save the exact intended settings and run Live Compatibility Check. '
        'If the problem persists, inspect API/validation-worker logs for AUTO_TRADE_COMPATIBILITY.'
    ))
