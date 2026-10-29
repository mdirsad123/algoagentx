"""Configuration equality and source-pinned compatibility evidence for settings.

Ordinary settings writes never execute a strategy. Enabling Auto Trade requires
recent deep evidence for the saved configuration plus a fresh lightweight check.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
from decimal import Decimal
from pathlib import Path
from functools import lru_cache

from fastapi import HTTPException
from sqlalchemy import select

from ...core.redis_manager import redis_manager
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
    fingerprint = await configuration_fingerprint(db, row, values)
    client = redis_manager.client
    try:
        raw = await asyncio.wait_for(client.get(f'live:compatibility:approved:{row.id}'), 1) if client else None
        evidence = json.loads(raw) if raw else {}
    except Exception:
        evidence = {}
    if not isinstance(evidence, dict) or evidence.get('fingerprint') != fingerprint or evidence.get('status') not in {'PASS', 'WARNING'}:
        raise HTTPException(status_code=409, detail=(
            'Enabling Auto Trade requires a completed compatibility check for these saved settings. '
            'Save configuration with Auto Trade off, run Check separately, then enable Auto Trade. '
            'Ordinary settings and copy-trading changes do not require strategy readiness.'
        ))