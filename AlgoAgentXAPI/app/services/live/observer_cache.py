"""Short-lived read-model caching; never used for execution or authorization.

Callers must freshly authorize the deployment BEFORE looking up a cached result.
Redis outages fail open to the original DB query, with a bounded cache I/O wait.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
from typing import Any

from fastapi.encoders import jsonable_encoder

from ...core.redis_manager import redis_manager

CACHE_IO_TIMEOUT = 0.075


def observer_key(endpoint: str, deployment: Any, user: dict, **query: Any) -> str:
    # Include observed deployment changes so pause/delete/config/cursor updates
    # cannot reuse a previous state, even inside the short TTL.
    state = {name: str(getattr(deployment, name, None)) for name in (
        'id', 'updated_at', 'status', 'broker_account_id', 'auto_trade_enabled',
        'auto_runner_enabled', 'last_processed_candle_time', 'next_run_at',
    )}
    payload = [endpoint, str(user['user_id']), str(user.get('role')), state, query]
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()
    return f'live:observer:v1:{digest}'


async def read_observer_cache(key: str) -> dict | None:
    client = redis_manager.client
    if client is None:
        return None
    try:
        raw = await asyncio.wait_for(client.get(key), CACHE_IO_TIMEOUT)
        value = json.loads(raw) if raw else None
        return value if isinstance(value, dict) and value.get('success') is True else None
    except Exception:
        return None


async def store_observer_cache(key: str, response: dict, *, ttl: int = 2) -> dict:
    client = redis_manager.client
    if client is not None and response.get('success') is True:
        try:
            body = json.dumps(jsonable_encoder(response), separators=(',', ':'), allow_nan=False)
            await asyncio.wait_for(client.set(key, body, ex=ttl), CACHE_IO_TIMEOUT)
        except Exception:
            pass
    return response