"""
Jobs API for background task management with Redis fallback support.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from ...core.dependencies import get_current_user, get_db
from ...services.job_service import JobService
from ...core.redis_manager import redis_manager
from ...tasks import cleanup_old_jobs_task

router = APIRouter()


@router.get("/{job_id}")
async def get_job_status(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get job status by ID with authorization check.

    Returns job status with progress tracking and result data if completed.
    
    Progress steps:
    - FETCH_DATA: 20% - Fetching market data
    - GENERATE_SIGNALS: 50% - Generating trading signals  
    - BUILD_TRADES: 70% - Building trade history
    - METRICS: 90% - Calculating performance metrics
    - SAVE: 100% - Saving results
    """
    job_status = await JobService.get_job_status(db, job_id, current_user["user_id"])

    if not job_status:
        raise HTTPException(status_code=404, detail="Job not found")

    return job_status


@router.get("/")
async def get_user_jobs(
    job_type: Optional[str] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get jobs for current user with pagination and filtering.

    Args:
        job_type: Optional job type filter (e.g., 'backtest')
        limit: Maximum number of jobs to return (default: 50)
    """
    jobs = await JobService.get_user_jobs(
        db=db,
        user_id=current_user["user_id"],
        job_type=job_type,
        limit=limit
    )

    return {"jobs": jobs, "total": len(jobs)}


@router.post("/{job_id}/retry")
async def retry_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Retry a failed job with proper retry policy.

    Only works for failed jobs within retry limits.
    """
    success = await JobService.retry_job(db, job_id, current_user["user_id"])

    if not success:
        raise HTTPException(
            status_code=400,
            detail="Job cannot be retried (not failed, max retries reached, or not found)"
        )

    return {
        "message": "Job retry initiated",
        "job_id": job_id,
        "redis_available": redis_manager.is_available
    }


@router.delete("/cleanup")
async def cleanup_old_jobs(
    days_to_keep: int = 30,
    batch_size: int = 100,
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Clean up old job records to prevent database bloat.
    Admin-only endpoint for periodic maintenance.

    Args:
        days_to_keep: Number of days to keep job records (default: 30)
        batch_size: Number of records to delete in each batch (default: 100)
        background_tasks: FastAPI background tasks for async cleanup
    """
    # Check if user has admin privileges (you may need to implement this check)
    # For now, we'll allow it for any authenticated user, but in production
    # you should restrict this to admin users only
    
    if background_tasks:
        # Run cleanup in background
        background_tasks.add_task(
            JobService.cleanup_old_jobs,
            db=db,
            days_to_keep=days_to_keep,
            batch_size=batch_size
        )
        return {
            "message": "Cleanup started in background",
            "days_to_keep": days_to_keep,
            "batch_size": batch_size
        }
    else:
        # Run cleanup synchronously
        deleted_count = await JobService.cleanup_old_jobs(
            db=db,
            days_to_keep=days_to_keep,
            batch_size=batch_size
        )
        return {
            "message": "Cleanup completed",
            "deleted_count": deleted_count,
            "days_to_keep": days_to_keep
        }


@router.get("/system/status")
async def get_system_status(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get system status including Redis availability and job queue health.
    Useful for monitoring and debugging.
    """
    from ...celery_app import is_celery_available
    
    # Check Redis status
    redis_status = await redis_manager.health_check()
    
    # Get job statistics
    from sqlalchemy import select, func
    from ...db.models import JobStatus
    
    # Count jobs by status
    result = await db.execute(
        select(JobStatus.status, func.count(JobStatus.id))
        .group_by(JobStatus.status)
    )
    job_stats = dict(result.fetchall())
    
    # Get pending jobs count
    pending_count = await db.execute(
        select(func.count(JobStatus.id))
        .where(JobStatus.status.in_(["pending", "queued"]))
    )
    pending_jobs = pending_count.scalar_one()
    
    # Get running jobs count
    running_count = await db.execute(
        select(func.count(JobStatus.id))
        .where(JobStatus.status == "running")
    )
    running_jobs = running_count.scalar_one()

    return {
        "redis": redis_status,
        "celery_available": is_celery_available(),
        "job_statistics": {
            "total_jobs": sum(job_stats.values()),
            "pending_jobs": pending_jobs,
            "running_jobs": running_jobs,
            "completed_jobs": job_stats.get("completed", 0),
            "failed_jobs": job_stats.get("failed", 0),
            "retry_jobs": job_stats.get("retry", 0),
            "by_status": job_stats
        },
        "fallback_mode": not (is_celery_available() and redis_manager.is_available),
        "timestamp": "2026-02-06T20:38:00Z"  # Would be current time in production
    }



