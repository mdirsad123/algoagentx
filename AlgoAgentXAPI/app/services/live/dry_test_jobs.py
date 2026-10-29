"""Authenticated deployment-scoped, bounded dry-test jobs.

HTTP never runs the expensive strategy; Redis metadata only links a task ID to
its deployment. The actual result is stored by Celery's existing Redis backend.
"""
from __future__ import annotations

import asyncio
from uuid import uuid4
from fastapi import HTTPException

from ...celery_app import celery_app
from ...core.redis_manager import redis_manager

JOB_TTL = 21600
LOCK_TTL = 7200


def _text(value):
    return value.decode() if isinstance(value, bytes) else str(value)


async def enqueue(deployment_id: str, *, kind: str = 'drytest') -> dict:
    if kind not in {'drytest', 'compatibility'}:
        raise ValueError('Unsupported validation job kind')
    redis = redis_manager.client
    if redis is None:
        raise HTTPException(status_code=503, detail="Dry-test queue requires Redis; no synchronous fallback")
    lock_key = f"live:{kind}:active:{deployment_id}"
    job_id = str(uuid4())
    claimed = False
    try:
        claimed = bool(await redis.set(lock_key, job_id, ex=LOCK_TTL, nx=True))
        if not claimed:
            existing = await redis.get(lock_key)
            return {"job_id": _text(existing) if existing else None, "status": "QUEUED_OR_RUNNING", "deduplicated": True}
        await redis.set(f"live:{kind}:job:{job_id}", deployment_id, ex=JOB_TTL)
        try:
            # Celery's broker connection is synchronous: never call it on FastAPI's event loop.
            await asyncio.wait_for(
                asyncio.to_thread(
                    celery_app.send_task,
                    ('app.tasks.run_live_compatibility_task' if kind == 'compatibility'
                     else "app.tasks.run_live_full_dry_test_task"),
                    args=[deployment_id], queue="live_dry_test", task_id=job_id,
                ), timeout=10,
            )
        except Exception as exc:
            # Compare and delete so a delayed caller cannot clear another run's lock.
            await redis.eval(
                "if redis.call('get', KEYS[1]) == ARGV[1] then return redis.call('del', KEYS[1]) else return 0 end",
                1, lock_key, job_id,
            )
            await redis.delete(f"live:{kind}:job:{job_id}")
            raise HTTPException(status_code=503, detail=f"Could not enqueue dry test: {type(exc).__name__}") from exc
    except HTTPException:
        raise
    except Exception as exc:
        if claimed:
            try:
                await redis.eval(
                    "if redis.call('get', KEYS[1]) == ARGV[1] then return redis.call('del', KEYS[1]) else return 0 end",
                    1, lock_key, job_id,
                )
            except Exception:
                pass
        raise HTTPException(status_code=503, detail="Dry-test queue unavailable") from exc
    return {"job_id": job_id, "status": "PENDING", "deduplicated": False}


async def status(deployment_id: str, job_id: str, *, kind: str = 'drytest') -> dict:
    if kind not in {'drytest', 'compatibility'}:
        raise ValueError('Unsupported validation job kind')
    redis = redis_manager.client
    if redis is None:
        raise HTTPException(status_code=503, detail="Dry-test status unavailable")
    try:
        owner = await redis.get(f"live:{kind}:job:{job_id}")
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Dry-test status unavailable") from exc
    if owner is None or _text(owner) != deployment_id:
        raise HTTPException(status_code=404, detail="Dry-test job not found for this deployment")
    try:
        task = await asyncio.wait_for(asyncio.to_thread(celery_app.AsyncResult, job_id), timeout=3)
        state, result = await asyncio.wait_for(
            asyncio.to_thread(lambda: (task.state, task.result if task.ready() else None)), timeout=5,
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Dry-test result backend unavailable") from exc
    if state == "SUCCESS":
        return {"job_id": job_id, "status": state, "result": result}
    if state in ("FAILURE", "REVOKED"):
        return {"job_id": job_id, "status": state, "error": str(result)[:400]}
    return {"job_id": job_id, "status": state}
