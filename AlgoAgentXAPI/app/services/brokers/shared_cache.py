"""Bounded single-flight broker metadata/session cache; never cache trading state."""
import asyncio
import base64
import hashlib
import json
import os
import time
import uuid
from cryptography.fernet import Fernet

from ...core.redis_manager import redis_manager

_VALUES = {}
_LOCKS = {}


def _cipher():
    secret = os.getenv('ALGOAGENTX_CREDENTIAL_SECRET') or os.getenv('SECRET_KEY')
    if not secret:
        raise RuntimeError('Shared broker session encryption key unavailable')
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest()))


async def cached(key, ttl, loader, *, secret=False, deadline=None):
    """Redis lease losers re-read the winner; no second authentication storm."""
    deadline = min(deadline or float('inf'), time.time() + 15)
    if deadline <= time.time():
        raise TimeoutError('Shared broker cache wait exceeds request budget')
    # Include local contention, Redis I/O and the loader in the same budget.
    async with asyncio.timeout(max(0, deadline - time.time())):
        return await _cached(key, ttl, loader, secret=secret, deadline=deadline)


async def _cached(key, ttl, loader, *, secret, deadline):
    async with _LOCKS.setdefault((asyncio.get_running_loop(), key), asyncio.Lock()):
        redis = redis_manager.client
        if redis is None:
            item = _VALUES.get(key)
            if item and item[0] > time.monotonic():
                return item[1]
            value = await loader()
            _VALUES[key] = (time.monotonic() + ttl, value)
            return value
        cipher = _cipher() if secret else None  # Fail before authenticating without a key.
        owner = uuid.uuid4().hex
        lock_key = key + ':lock'
        while time.time() < deadline:
            raw = await redis.get(key)
            if raw:
                if secret:
                    raw = cipher.decrypt(raw.encode() if isinstance(raw, str) else raw)
                return json.loads(raw)
            if await redis.set(lock_key, owner, nx=True, px=30000):
                try:
                    # Recheck after acquiring: a winner may just have released.
                    raw = await redis.get(key)
                    if raw:
                        if secret:
                            raw = cipher.decrypt(raw.encode() if isinstance(raw, str) else raw)
                        return json.loads(raw)
                    value = await loader()
                    raw = json.dumps(value)
                    if secret:
                        raw = cipher.encrypt(raw.encode()).decode()
                    # A lease that expired during I/O must not publish stale data.
                    published = await redis.eval("if redis.call('get',KEYS[1]) == ARGV[1] then redis.call('set',KEYS[2],ARGV[2],'EX',ARGV[3]); return 1 end return 0",
                                                 2, lock_key, key, owner, raw, ttl)
                    if not published:
                        raise RuntimeError('Shared broker cache lease expired; result discarded')
                    return value
                finally:
                    # Cleanup must not turn cancellation into an unbounded wait.
                    # If Redis is down, the lease expires on its own.
                    try:
                        async with asyncio.timeout(0.1):
                            await redis.eval("if redis.call('get',KEYS[1]) == ARGV[1] then return redis.call('del',KEYS[1]) end return 0", 1, lock_key, owner)
                    except Exception:
                        pass
            await asyncio.sleep(min(0.1, max(0, deadline - time.time())))
        raise TimeoutError('Shared broker cache wait exceeds request budget')


async def invalidate_secret(key, rejected_token):
    item = _VALUES.get(key)
    if item and item[1].get('token') == rejected_token:
        _VALUES.pop(key, None)
    redis = redis_manager.client
    if redis is not None:
        raw = await redis.get(key)
        if raw:
            decoded = json.loads(_cipher().decrypt(raw.encode() if isinstance(raw, str) else raw))
            if decoded.get('token') == rejected_token:
                await redis.eval("if redis.call('get',KEYS[1]) == ARGV[1] then return redis.call('del',KEYS[1]) end return 0", 1, key, raw)