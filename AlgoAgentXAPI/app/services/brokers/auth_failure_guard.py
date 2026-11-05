"""Quarantine only rejected cTrader token fingerprints, never healthy accounts."""
import hashlib
from ...core.redis_manager import redis_manager

_INVALID = set()


def invalid_token_error(exc):
    value = str(exc).upper()
    return 'CH_ACCESS_TOKEN_INVALID' in value or 'ACCESS TOKEN EXPIRED' in value


def token_key(token):
    return 'ctrader:invalid-token:' + hashlib.sha256(token.encode()).hexdigest()


async def check_token(token):
    key = token_key(token)
    redis = redis_manager.client
    if key in _INVALID or (redis is not None and await redis.exists(key)):
        raise ValueError('CH_ACCESS_TOKEN_INVALID - Reconnect cTrader; rejected token is quarantined')


async def reject_token(token):
    key = token_key(token)
    _INVALID.add(key)
    if redis_manager.client is not None:
        # No credentials stored. A renewed token has a different fingerprint.
        await redis_manager.client.set(key, '1', ex=30 * 86400)