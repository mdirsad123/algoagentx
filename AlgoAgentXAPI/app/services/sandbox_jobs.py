"""PostgreSQL-owned Sandbox lifecycle; no market or strategy calculations."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, update

from ..db.models.job_status import JobStatus

QUEUED = ("pending", "queued", "retry", "retrying")
RUNNING = ("running", "started")
ACTIVE = QUEUED + RUNNING
QUEUE_TIMEOUT_SECONDS = 14400
RUN_TIMEOUT_SECONDS = 14520  # Dedicated worker hard limit plus delivery grace.


def stale_deadline(job):
    status = str(job.status or "").strip().lower()
    if status not in ACTIVE:
        return None
    start = (job.started_at or job.updated_at or job.created_at) if status in RUNNING else job.created_at
    if start is None:
        return None
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    seconds = RUN_TIMEOUT_SECONDS if status in RUNNING else QUEUE_TIMEOUT_SECONDS
    return start + timedelta(seconds=seconds)


async def claim_sandbox(db, job_id: str) -> bool:
    """Only one delivery may claim a queued job; terminal jobs never restart."""
    result = await db.execute(
        update(JobStatus).where(
            JobStatus.id == job_id, JobStatus.job_type == "strategy_sandbox",
            func.lower(JobStatus.status).in_(QUEUED),
        ).values(status="running", progress=10, message="Running strategy sandbox in background",
                 started_at=datetime.now(timezone.utc)).returning(JobStatus.id)
    )
    claimed = result.scalar_one_or_none() is not None
    await db.commit()
    return claimed


async def update_sandbox_progress(db, job_id: str, progress: int, message: str) -> bool:
    """Publish real engine milestones without touching terminal/cancelled jobs."""
    progress = max(10, min(99, int(progress)))
    result = await db.execute(
        update(JobStatus).where(
            JobStatus.id == job_id, JobStatus.job_type == "strategy_sandbox",
            func.lower(JobStatus.status).in_(RUNNING),
        ).values(progress=progress, message=str(message)[:500]).returning(JobStatus.id)
    )
    changed = result.scalar_one_or_none() is not None
    await db.commit()
    return changed


async def finish_sandbox(db, job_id: str, status: str, message: str, data=None) -> bool:
    """Compare-and-set prevents completion/failure from overwriting cancellation."""
    allowed = RUNNING if status == "completed" else ACTIVE
    result = await db.execute(
        update(JobStatus).where(
            JobStatus.id == job_id, JobStatus.job_type == "strategy_sandbox",
            func.lower(JobStatus.status).in_(allowed),
        ).values(status=status, progress=100 if status == "completed" else 0,
                 message=message, result_data=json.dumps(data, default=str) if data is not None else None,
                 completed_at=datetime.now(timezone.utc)).returning(JobStatus.id)
    )
    changed = result.scalar_one_or_none() is not None
    await db.commit()
    return changed


async def expire_stale_sandbox(db, job):
    deadline = stale_deadline(job)
    if deadline is None or datetime.now(timezone.utc) < deadline:
        return
    # Match the observed timestamps as well as status: a worker may have claimed
    # this job since polling read it. Never expire that newly running execution.
    message = "Sandbox job timed out waiting for a worker" if str(job.status).lower() in QUEUED else "Sandbox worker exceeded its execution deadline"
    await db.execute(
        update(JobStatus).where(
            JobStatus.id == job.id, JobStatus.job_type == "strategy_sandbox",
            JobStatus.status == job.status, JobStatus.updated_at == job.updated_at,
            JobStatus.started_at == job.started_at,
        ).values(status="failed", message=message, completed_at=datetime.now(timezone.utc),
                 result_data=json.dumps({"error": message, "code": "sandbox_timeout"}))
    )
    await db.commit()
    await db.refresh(job)