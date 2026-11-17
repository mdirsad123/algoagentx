"""Dedicated existing live-history Celery queue for CPU-heavy verified cold reseeds."""
from __future__ import annotations


def enqueue_verified_gap_reseed(deployment_id, missing_open, latest_open) -> dict:
    import redis
    from ...core.config import settings
    from ...tasks import verified_gap_reseed_task

    key = f'live:gap:reseed:queued:{deployment_id}:{missing_open.isoformat()}'
    client = redis.Redis.from_url(settings.redis_url, decode_responses=True,
                                  socket_connect_timeout=2, socket_timeout=2)
    try:
        if not client.set(key, '1', nx=True, ex=2500):
            return {'queued': True, 'deduplicated': True}
        try:
            result = verified_gap_reseed_task.apply_async(
                args=[str(deployment_id), missing_open.isoformat(), latest_open.isoformat()],
                queue='live_history',
            )
        except Exception:
            client.delete(key)
            raise
        return {'queued': True, 'task_id': str(result.id), 'deduplicated': False}
    except Exception as exc:
        return {'queued': False, 'error_type': type(exc).__name__}
    finally:
        client.close()
