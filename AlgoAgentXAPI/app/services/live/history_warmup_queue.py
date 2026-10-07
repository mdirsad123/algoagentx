from __future__ import annotations

from typing import Any


def enqueue_history_warmup(deployment_id: Any, required_count: int) -> dict[str, Any]:
    """Queue a live-history warm-up and return immediately.

    Heavy broker history must never run inside a browser request or the strategy
    event worker. A short Redis enqueue lock prevents every 5-minute candle or
    repeated Compatibility click from flooding the dedicated queue.
    """
    import redis
    from ...core.config import settings
    from ...tasks import warm_live_strategy_history_task

    deployment_text = str(deployment_id)
    queue_key = f"live:history:warmup:queued:{deployment_text}"
    r = None
    try:
        r = redis.Redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=3,
            socket_timeout=3,
        )
        if not r.set(queue_key, "1", nx=True, ex=600):
            return {"queued": True, "deduplicated": True}
        result = warm_live_strategy_history_task.apply_async(
            args=[deployment_text, int(required_count)],
            queue="live_history",
        )
        return {"queued": True, "task_id": str(result.id), "deduplicated": False}
    except Exception as exc:
        try:
            if r is not None:
                r.delete(queue_key)
        except Exception:
            pass
        return {"queued": False, "error": str(exc)}
    finally:
        try:
            if r is not None:
                r.close()
        except Exception:
            pass
