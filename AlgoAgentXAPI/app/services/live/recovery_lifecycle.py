"""Owned, bounded recovery coordination; PostgreSQL remains authoritative.

The lease exceeds the Celery hard limit (2400s). A killed child cannot retain
ownership forever, and an old delivery can neither release nor overwrite its
successor. The PostgreSQL runner lock and cursor/checkpoint transaction provide
the final execution fence, independently of Redis availability.
"""
from __future__ import annotations

import time
from uuid import uuid4

LEASE_SECONDS = 2500
MAX_ATTEMPTS = 4
POLICY_VERSION = '2'


def keys(deployment_id):
    prefix = 'live:gap:reseed:'
    return (f'{prefix}lease:{deployment_id}', f'{prefix}queued:{deployment_id}',
            f'{prefix}status:{deployment_id}')


def release_owned(client, key, owner):
    return client.eval("""
        if redis.call('GET', KEYS[1]) == ARGV[1] then
            return redis.call('DEL', KEYS[1])
        end
        return 0
    """, 1, key, owner)


def claim(client, deployment_id, task_id, missing, target):
    """Atomic admission: one body per deployment, including duplicate delivery."""
    lease, queue, status = keys(deployment_id)
    token = str(uuid4())
    result = client.eval("""
        if redis.call('EXISTS', KEYS[1]) == 1 then return 0 end
        local queued = redis.call('GET', KEYS[2])
        if queued and queued ~= ARGV[1] then return -1 end
        local same = redis.call('HGET', KEYS[3], 'missing_open') == ARGV[3]
        local stage = redis.call('HGET', KEYS[3], 'status')
        if same and stage == 'RECOVERED' then return -2 end
        local count = 0
        if same and redis.call('HGET', KEYS[3], 'policy_version') == ARGV[7] then
            count = tonumber(redis.call('HGET', KEYS[3], 'cycle_attempts') or '0')
            if count >= tonumber(ARGV[8]) then return -3 end
            if stage == 'REQUIRES_ATTENTION' then return -4 end
            local retry = tonumber(redis.call('HGET', KEYS[3], 'retry_at') or '0')
            if stage == 'RETRYABLE' and retry > tonumber(ARGV[5]) then return -5 end
        end
        local attempts = 0
        if same then attempts = tonumber(redis.call('HGET', KEYS[3], 'attempts') or '0') end
        redis.call('SET', KEYS[1], ARGV[2], 'EX', ARGV[6])
        redis.call('SET', KEYS[2], ARGV[1], 'EX', ARGV[6])
        redis.call('HSET', KEYS[3], 'status', 'RUNNING', 'task_id', ARGV[1],
            'run_token', ARGV[2], 'missing_open', ARGV[3], 'target_open', ARGV[4],
            'started_at', ARGV[5], 'attempts', attempts + 1,
            'cycle_attempts', count + 1, 'policy_version', ARGV[7],
            'reason', '', 'retry_at', '0')
        return count + 1
    """, 3, lease, queue, status, task_id, token, missing, target,
        int(time.time()), LEASE_SECONDS, POLICY_VERSION, MAX_ATTEMPTS)
    return (token, int(result)) if result > 0 else (None, int(result))


def finish(client, deployment_id, task_id, token, *, stage, reason, retry_at):
    lease, queue, status = keys(deployment_id)
    return client.eval("""
        if redis.call('GET', KEYS[1]) ~= ARGV[2]
            or redis.call('HGET', KEYS[3], 'task_id') ~= ARGV[1]
            or redis.call('HGET', KEYS[3], 'run_token') ~= ARGV[2] then return 0 end
        redis.call('HSET', KEYS[3], 'status', ARGV[3], 'reason', ARGV[4],
            'retry_at', ARGV[5], 'finished_at', ARGV[6])
        redis.call('DEL', KEYS[1])
        if redis.call('GET', KEYS[2]) == ARGV[1] then redis.call('DEL', KEYS[2]) end
        return 1
    """, 3, lease, queue, status, task_id, token, stage, reason[:200], retry_at, int(time.time()))


def worker_lost(client, deployment_id, task_id, missing, reason):
    """Parent-process cleanup after worker loss/hard timeout, fenced atomically."""
    lease, queue, status = keys(deployment_id)
    return client.eval("""
        if redis.call('HGET', KEYS[3], 'task_id') ~= ARGV[1]
            or redis.call('HGET', KEYS[3], 'missing_open') ~= ARGV[2]
            or redis.call('HGET', KEYS[3], 'status') ~= 'RUNNING' then return 0 end
        local token = redis.call('HGET', KEYS[3], 'run_token')
        local owner = redis.call('GET', KEYS[1])
        if owner and owner ~= token then return 0 end
        local attempts = tonumber(redis.call('HGET', KEYS[3], 'cycle_attempts') or '0')
        local stage = 'RETRYABLE'
        if attempts >= tonumber(ARGV[5]) then stage = 'REQUIRES_ATTENTION' end
        local delay = math.min(1800, 300 * 2 ^ math.min(math.max(attempts - 1, 0), 3))
        redis.call('HSET', KEYS[3], 'status', stage, 'reason', ARGV[3],
            'failed_at', ARGV[4], 'retry_at', tonumber(ARGV[4]) + delay)
        if owner == token then redis.call('DEL', KEYS[1]) end
        if redis.call('GET', KEYS[2]) == ARGV[1] then redis.call('DEL', KEYS[2]) end
        return 1
    """, 3, lease, queue, status, task_id, missing, reason, int(time.time()), MAX_ATTEMPTS)


def exception_reason(exc):
    """No raw HTTP body/credentials in Redis; validation failures stay terminal."""
    code = getattr(exc, 'status_code', None)
    # The internal runner wraps DB/transport errors as HTTP 500. Preserve a
    # known transient cause without treating every programming error as retryable.
    cause = getattr(exc, '__cause__', None)
    if code == 500 and cause is not None:
        from .verified_recovery import TRANSIENT_RECOVERY_REASONS
        if type(cause).__name__ in TRANSIENT_RECOVERY_REASONS:
            return type(cause).__name__
    if code is not None:
        return f'HTTP_{int(code)}'
    return type(exc).__name__