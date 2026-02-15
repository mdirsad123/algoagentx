from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from ...core.dependencies import get_current_user, get_admin_user, get_db
from ...services.ai_screener.job_handlers import AIScreenerJobService
from ...services.job_service import JobService
from ...core.config import settings

router = APIRouter()


@router.post("/news-refresh")
async def trigger_news_refresh(
    background_tasks: BackgroundTasks,
    symbols: Optional[List[str]] = Query(None, description="List of symbols to refresh (optional)"),
    top_n: Optional[int] = Query(None, description="Number of items to fetch per symbol (optional)"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_admin_user)
):
    """
    Admin-only endpoint to manually trigger AI Screener news refresh.
    
    Args:
        background_tasks: FastAPI background tasks
        symbols: List of symbols to refresh (optional)
        top_n: Number of items to fetch per symbol (optional)
        db: Database session
        current_user: Admin user
    
    Returns:
        Job creation response
    """
    try:
        job_id = await AIScreenerJobService.submit_ai_screener_job(
            db=db,
            user_id=current_user["user_id"],
            job_type="ai_screener_news_refresh",
            symbols=symbols,
            top_n=top_n
        )
        
        return {
            "message": "News refresh job created successfully",
            "job_id": job_id,
            "job_type": "ai_screener_news_refresh",
            "symbols": symbols or [],
            "top_n": top_n or settings.ai_screener_top_n,
            "redis_available": settings.is_production  # Would check Redis availability
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create news refresh job: {str(e)}"
        )


@router.post("/announcements-refresh")
async def trigger_announcements_refresh(
    background_tasks: BackgroundTasks,
    symbols: Optional[List[str]] = Query(None, description="List of symbols to refresh (optional)"),
    top_n: Optional[int] = Query(None, description="Number of items to fetch per symbol (optional)"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_admin_user)
):
    """
    Admin-only endpoint to manually trigger AI Screener announcements refresh.
    
    Args:
        background_tasks: FastAPI background tasks
        symbols: List of symbols to refresh (optional)
        top_n: Number of items to fetch per symbol (optional)
        db: Database session
        current_user: Admin user
    
    Returns:
        Job creation response
    """
    try:
        job_id = await AIScreenerJobService.submit_ai_screener_job(
            db=db,
            user_id=current_user["user_id"],
            job_type="ai_screener_announcements_refresh",
            symbols=symbols,
            top_n=top_n
        )
        
        return {
            "message": "Announcements refresh job created successfully",
            "job_id": job_id,
            "job_type": "ai_screener_announcements_refresh",
            "symbols": symbols or [],
            "top_n": top_n or settings.ai_screener_top_n,
            "redis_available": settings.is_production  # Would check Redis availability
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create announcements refresh job: {str(e)}"
        )


@router.get("/news-refresh/status/{job_id}")
async def get_news_refresh_status(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_admin_user)
):
    """
    Get status of a specific news refresh job.
    
    Args:
        job_id: Job ID
        db: Database session
        current_user: Admin user
    
    Returns:
        Job status information
    """
    job_status = await JobService.get_job_status(db, job_id, current_user["user_id"])

    if not job_status:
        raise HTTPException(status_code=404, detail="Job not found")

    return job_status


@router.get("/announcements-refresh/status/{job_id}")
async def get_announcements_refresh_status(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_admin_user)
):
    """
    Get status of a specific announcements refresh job.
    
    Args:
        job_id: Job ID
        db: Database session
        current_user: Admin user
    
    Returns:
        Job status information
    """
    job_status = await JobService.get_job_status(db, job_id, current_user["user_id"])

    if not job_status:
        raise HTTPException(status_code=404, detail="Job not found")

    return job_status


@router.get("/news-refresh/jobs")
async def get_news_refresh_jobs(
    limit: int = Query(50, description="Maximum number of jobs to return"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_admin_user)
):
    """
    Get all news refresh jobs for admin user.
    
    Args:
        limit: Maximum number of jobs to return
        db: Database session
        current_user: Admin user
    
    Returns:
        List of news refresh jobs
    """
    jobs = await JobService.get_user_jobs(
        db=db,
        user_id=current_user["user_id"],
        job_type="ai_screener_news_refresh",
        limit=limit
    )

    return {"jobs": jobs, "total": len(jobs)}


@router.get("/announcements-refresh/jobs")
async def get_announcements_refresh_jobs(
    limit: int = Query(50, description="Maximum number of jobs to return"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_admin_user)
):
    """
    Get all announcements refresh jobs for admin user.
    
    Args:
        limit: Maximum number of jobs to return
        db: Database session
        current_user: Admin user
    
    Returns:
        List of announcements refresh jobs
    """
    jobs = await JobService.get_user_jobs(
        db=db,
        user_id=current_user["user_id"],
        job_type="ai_screener_announcements_refresh",
        limit=limit
    )

    return {"jobs": jobs, "total": len(jobs)}


@router.post("/news-refresh/{job_id}/retry")
async def retry_news_refresh_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_admin_user)
):
    """
    Retry a failed news refresh job.
    
    Args:
        job_id: Job ID
        db: Database session
        current_user: Admin user
    
    Returns:
        Retry status
    """
    success = await AIScreenerJobService.retry_ai_screener_job(db, job_id, current_user["user_id"])

    if not success:
        raise HTTPException(
            status_code=400,
            detail="Job cannot be retried (not failed, max retries reached, or not found)"
        )

    return {
        "message": "News refresh job retry initiated",
        "job_id": job_id,
        "redis_available": settings.is_production
    }


@router.post("/announcements-refresh/{job_id}/retry")
async def retry_announcements_refresh_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_admin_user)
):
    """
    Retry a failed announcements refresh job.
    
    Args:
        job_id: Job ID
        db: Database session
        current_user: Admin user
    
    Returns:
        Retry status
    """
    success = await AIScreenerJobService.retry_ai_screener_job(db, job_id, current_user["user_id"])

    if not success:
        raise HTTPException(
            status_code=400,
            detail="Job cannot be retried (not failed, max retries reached, or not found)"
        )

    return {
        "message": "Announcements refresh job retry initiated",
        "job_id": job_id,
        "redis_available": settings.is_production
    }


@router.get("/system/status")
async def get_ai_screener_system_status(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_admin_user)
):
    """
    Get AI Screener system status including job statistics and configuration.
    
    Args:
        db: Database session
        current_user: Admin user
    
    Returns:
        System status information
    """
    from sqlalchemy import select, func
    from ..db.models import JobStatus
    
    # Count AI Screener jobs by status
    result = await db.execute(
        select(JobStatus.status, func.count(JobStatus.id))
        .where(JobStatus.job_type.in_(["ai_screener_news_refresh", "ai_screener_announcements_refresh"]))
        .group_by(JobStatus.status)
    )
    job_stats = dict(result.fetchall())
    
    # Get pending AI Screener jobs count
    pending_count = await db.execute(
        select(func.count(JobStatus.id))
        .where(
            JobStatus.job_type.in_(["ai_screener_news_refresh", "ai_screener_announcements_refresh"]),
            JobStatus.status.in_(["pending", "queued"])
        )
    )
    pending_jobs = pending_count.scalar_one()
    
    # Get running AI Screener jobs count
    running_count = await db.execute(
        select(func.count(JobStatus.id))
        .where(
            JobStatus.job_type.in_(["ai_screener_news_refresh", "ai_screener_announcements_refresh"]),
            JobStatus.status == "running"
        )
    )
    running_jobs = running_count.scalar_one()

    return {
        "ai_screener_enabled": settings.ai_screener_enabled,
        "ai_screener_sources": settings.ai_screener_sources,
        "ai_screener_top_n": settings.ai_screener_top_n,
        "job_statistics": {
            "total_ai_screener_jobs": sum(job_stats.values()),
            "pending_jobs": pending_jobs,
            "running_jobs": running_jobs,
            "completed_jobs": job_stats.get("completed", 0),
            "failed_jobs": job_stats.get("failed", 0),
            "retry_jobs": job_stats.get("retry", 0),
            "by_status": job_stats
        },
        "configuration": {
            "default_symbols": ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK"],
            "max_retries": 3,
            "retry_delay_base": 60,
            "job_timeout_minutes": 30
        },
        "timestamp": datetime.utcnow().isoformat()
    }


@router.delete("/cleanup")
async def cleanup_old_ai_screener_jobs(
    days_to_keep: int = Query(30, description="Number of days to keep job records"),
    batch_size: int = Query(100, description="Number of records to delete in each batch"),
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_admin_user)
):
    """
    Clean up old AI Screener job records to prevent database bloat.
    Admin-only endpoint for periodic maintenance.
    
    Args:
        days_to_keep: Number of days to keep job records (default: 30)
        batch_size: Number of records to delete in each batch (default: 100)
        background_tasks: FastAPI background tasks for async cleanup
        db: Database session
        current_user: Admin user
    
    Returns:
        Cleanup status
    """
    if background_tasks:
        # Run cleanup in background
        background_tasks.add_task(
            JobService.cleanup_old_jobs,
            db=db,
            days_to_keep=days_to_keep,
            batch_size=batch_size
        )
        return {
            "message": "AI Screener job cleanup started in background",
            "days_to_keep": days_to_keep,
            "batch_size": batch_size,
            "job_types": ["ai_screener_news_refresh", "ai_screener_announcements_refresh"]
        }
    else:
        # Run cleanup synchronously
        deleted_count = await JobService.cleanup_old_jobs(
            db=db,
            days_to_keep=days_to_keep,
            batch_size=batch_size
        )
        return {
            "message": "AI Screener job cleanup completed",
            "deleted_count": deleted_count,
            "days_to_keep": days_to_keep,
            "job_types": ["ai_screener_news_refresh", "ai_screener_announcements_refresh"]
        }