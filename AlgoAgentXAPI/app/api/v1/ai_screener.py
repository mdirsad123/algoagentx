from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, func, and_, or_, desc, asc, update
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4
from pydantic import BaseModel
import json

from ...core.dependencies import get_current_user, get_db, check_ai_screener_limits, get_admin_user, get_user_entitlements
from ...services.ai_screener.service import AIScreenerService
from ...services.credits.management import CreditManagementService
from ...schemas.credits import InsufficientCreditsError
from ...db.models import JobStatus, Instrument, ScreenerNews, ScreenerAnnouncements, ScreenerRuns
from ...schemas.backtests import PerformanceMetric as PerformanceMetricOut

router = APIRouter()


# Response schemas for new endpoints
class NewsItemResponse(BaseModel):
    title: str
    summary: str
    url: str
    date: datetime
    sentiment_label: str
    sentiment_score: float
    symbol: str

class AnnouncementItemResponse(BaseModel):
    title: str
    summary: str
    url: str
    date: datetime
    symbol: str
    exchange: str
    nse_link: Optional[str] = None
    bse_link: Optional[str] = None

class NewsSearchResponse(BaseModel):
    items: List[NewsItemResponse]
    total: int
    query: str
    date: Optional[str] = None

class TopNewsResponse(BaseModel):
    items: List[NewsItemResponse]
    total: int
    date: str
    sentiment_type: str

class LatestAnnouncementsResponse(BaseModel):
    items: List[AnnouncementItemResponse]
    total: int
    date: Optional[str] = None


@router.post("/run", response_model=dict, status_code=status.HTTP_202_ACCEPTED)
async def run_ai_screener(
    mode: str = Query(..., description="AI screener mode"),
    depth: str = Query(..., description="AI screener depth"),
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    entitlements: dict = Depends(get_user_entitlements)
):
    """
    Submit AI screener job for background execution.

    Returns job_id immediately. Use /jobs/{job_id} to poll status.
    Enforces credit policy:
    - Subscription users: Use included credits first, then require additional credits if exceeded
    - Credit-only users: Always require credits
    - Free trial users: Limited runs, no credit deduction during trial period
    """
    try:
        # Validate AI screener parameters
        valid_modes = ["basic", "advanced", "premium"]
        valid_depths = ["light", "medium", "deep"]
        
        if mode not in valid_modes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid AI screener mode. Valid modes: {valid_modes}"
            )
        
        if depth not in valid_depths:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid AI screener depth. Valid depths: {valid_depths}"
            )

        # Enforce plan-based access to advanced features
        plan_code = entitlements.get("plan_code", "FREE")
        
        # Free users can only access basic mode with light depth
        if plan_code == "FREE":
            if mode != "basic" or depth != "light":
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail={
                        "detail": "Upgrade required",
                        "code": "PLAN_REQUIRED",
                        "message": "Advanced AI screener features require a premium subscription. Free users can only use basic mode with light depth."
                    }
                )
        # Trial users get limited access (same as free but with some premium features)
        elif entitlements.get("is_trial", False):
            if mode not in ["basic", "advanced"] or depth not in ["light", "medium"]:
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail={
                        "detail": "Upgrade required",
                        "code": "PLAN_REQUIRED",
                        "message": "Deep analysis and premium features require a paid subscription. Trial users can access basic and advanced modes with light and medium depth."
                    }
                )
        # Premium users can access all modes and depths
        elif plan_code in ["PREMIUM", "PREMIUM_ANNUAL"]:
            pass  # Allow all modes and depths

        # Enforce credit policy
        try:
            credit_policy = await AIScreenerService.check_subscription_and_credits(
                db=db,
                user_id=current_user["user_id"],
                mode=mode,
                depth=depth
            )
            
            # Log the credit policy decision
            print(f"AI Screener credit policy applied: {credit_policy}")
            
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=str(e)
            )

        # Create job status record
        job_id = await AIScreenerService.create_job_status(
            db=db,
            user_id=current_user["user_id"],
            mode=mode,
            depth=depth,
            policy_result=credit_policy
        )

        # Submit job to background tasks (real AI screener execution)
        if background_tasks:
            background_tasks.add_task(
                _execute_ai_screener_job,
                db=db,
                job_id=job_id,
                user_id=current_user["user_id"],
                mode=mode,
                depth=depth
            )

        return {
            "job_id": job_id,
            "status": "accepted",
            "message": "AI screener job submitted for processing",
            "mode": mode,
            "depth": depth,
            "policy": credit_policy["policy"],
            "cost": credit_policy["cost"],
            "deducted": credit_policy["deducted"],
            "remaining_balance": credit_policy["remaining_balance"],
            "remaining_included": credit_policy["remaining_included"],
            "policy_message": credit_policy["message"],
            "poll_url": f"/api/v1/jobs/{job_id}"
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit AI screener job: {str(e)}"
        )


@router.get("/history")
async def get_ai_screener_history(
    mode: Optional[str] = Query(None, description="Filter by AI screener mode"),
    depth: Optional[str] = Query(None, description="Filter by AI screener depth"),
    status_filter: Optional[str] = Query(None, description="Filter by job status"),
    start_date_from: Optional[datetime] = Query(None, description="Filter by start date from"),
    start_date_to: Optional[datetime] = Query(None, description="Filter by start date to"),
    sort_by: str = Query("created_at", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order (asc/desc)"),
    page: int = Query(1, description="Page number", ge=1),
    page_size: int = Query(20, description="Items per page", ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get AI screener job history with filtering and pagination.
    """
    from sqlalchemy import and_, or_, desc, asc

    # Build base query
    query = select(JobStatus).where(
        JobStatus.user_id == current_user["user_id"],
        JobStatus.job_type == "AI_SCREENER"
    )

    # Apply filters
    filters = []
    if mode:
        filters.append(JobStatus.parameters["mode"].astext == mode)
    if depth:
        filters.append(JobStatus.parameters["depth"].astext == depth)
    if status_filter:
        filters.append(JobStatus.status == status_filter)
    if start_date_from:
        filters.append(JobStatus.created_at >= start_date_from)
    if start_date_to:
        filters.append(JobStatus.created_at <= start_date_to)

    if filters:
        query = query.where(and_(*filters))

    # Apply sorting
    sort_column = getattr(JobStatus, sort_by, JobStatus.created_at)
    if sort_order.lower() == "asc":
        query = query.order_by(asc(sort_column))
    else:
        query = query.order_by(desc(sort_column))

    # Get total count
    count_query = query.with_only_columns([JobStatus.id])
    total_result = await db.execute(count_query)
    total_count = len(total_result.fetchall())

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    # Execute query
    result = await db.execute(query)
    jobs = result.scalars().all()

    # Format response
    job_list = []
    for job in jobs:
        job_list.append({
            "job_id": job.id,
            "status": job.status,
            "mode": job.parameters.get("mode"),
            "depth": job.parameters.get("depth"),
            "policy": job.parameters.get("policy"),
            "cost": job.parameters.get("cost"),
            "deducted": job.parameters.get("deducted"),
            "policy_message": job.extra_data.get("policy_message") if hasattr(job, 'extra_data') and job.extra_data else None,
            "remaining_balance": job.extra_data.get("remaining_balance") if hasattr(job, 'extra_data') and job.extra_data else None,
            "remaining_included": job.extra_data.get("remaining_included") if hasattr(job, 'extra_data') and job.extra_data else None,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "updated_at": job.updated_at.isoformat() if job.updated_at else None,
            "result": job.result
        })

    return {
        "jobs": job_list,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_count": total_count,
            "total_pages": (total_count + page_size - 1) // page_size
        },
        "filters_applied": {
            "mode": mode,
            "depth": depth,
            "status": status_filter,
            "start_date_from": start_date_from.isoformat() if start_date_from else None,
            "start_date_to": start_date_to.isoformat() if start_date_to else None
        }
    }


@router.get("/{job_id}", response_model=dict)
async def get_ai_screener_job_status(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get AI screener job status by ID.
    """
    job_status = await AIScreenerService.get_job_status(db, job_id, current_user["user_id"])
    
    if not job_status:
        raise HTTPException(status_code=404, detail="AI screener job not found")
    
    return job_status


async def _execute_ai_screener_job(
    db: AsyncSession,
    job_id: str,
    user_id: str,
    mode: str,
    depth: str
):
    """
    Execute real AI screener job using ScreenerNews and ScreenerAnnouncements data.
    Builds result payload and stores in JobStatus.result.
    """
    from sqlalchemy import select, desc, asc, func
    from datetime import date, datetime
    
    try:
        # Mark job as RUNNING
        await AIScreenerService.update_job_status(
            db, job_id, "RUNNING", 
            {"message": "Processing AI screener analysis..."}
        )
        
        # Get today's date for filtering
        today = date.today()
        
        # Query top positive news (top 10 by sentiment score)
        positive_news_query = select(ScreenerNews).where(
            and_(
                ScreenerNews.date == today,
                ScreenerNews.sentiment_label == "positive"
            )
        ).order_by(desc(ScreenerNews.sentiment_score)).limit(10)
        
        positive_result = await db.execute(positive_news_query)
        positive_news = positive_result.scalars().all()
        
        # Query top negative news (top 10 by sentiment score, ascending for most negative)
        negative_news_query = select(ScreenerNews).where(
            and_(
                ScreenerNews.date == today,
                ScreenerNews.sentiment_label == "negative"
            )
        ).order_by(asc(ScreenerNews.sentiment_score)).limit(10)
        
        negative_result = await db.execute(negative_news_query)
        negative_news = negative_result.scalars().all()
        
        # Query latest announcements (top 20 by date/time)
        announcements_query = select(ScreenerAnnouncements).where(
            ScreenerAnnouncements.date == today
        ).order_by(desc(ScreenerAnnouncements.date), desc(ScreenerAnnouncements.time)).limit(20)
        
        announcements_result = await db.execute(announcements_query)
        announcements = announcements_result.scalars().all()
        
        # Build result payload
        result = {
            "status": "completed",
            "mode": mode,
            "depth": depth,
            "analysis_date": today.isoformat(),
            "execution_time": datetime.utcnow().isoformat(),
            "top_positive_news": [
                {
                    "title": news.title,
                    "summary": news.summary,
                    "url": news.url,
                    "symbol": news.symbol,
                    "sentiment_score": float(news.sentiment_score),
                    "sentiment_label": news.sentiment_label,
                    "date": news.date.isoformat()
                }
                for news in positive_news
            ],
            "top_negative_news": [
                {
                    "title": news.title,
                    "summary": news.summary,
                    "url": news.url,
                    "symbol": news.symbol,
                    "sentiment_score": float(news.sentiment_score),
                    "sentiment_label": news.sentiment_label,
                    "date": news.date.isoformat()
                }
                for news in negative_news
            ],
            "latest_announcements": [
                {
                    "title": ann.title,
                    "summary": ann.summary,
                    "url": ann.url,
                    "symbol": ann.symbol,
                    "exchange": ann.exchange,
                    "nse_link": ann.nse_link,
                    "bse_link": ann.bse_link,
                    "date": ann.date.isoformat(),
                    "time": ann.time.isoformat() if ann.time else None
                }
                for ann in announcements
            ],
            "summary": {
                "total_positive_news": len(positive_news),
                "total_negative_news": len(negative_news),
                "total_announcements": len(announcements),
                "analysis_mode": mode,
                "analysis_depth": depth,
                "processing_time": "Real-time analysis completed"
            }
        }
        
        # Mark job as COMPLETED with result
        await AIScreenerService.update_job_status(db, job_id, "COMPLETED", result)
        
    except Exception as e:
        # Handle any unexpected errors
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in AI screener execution job {job_id}: {e}")
        
        # Mark job as FAILED
        error_result = {
            "status": "failed",
            "error": str(e),
            "execution_time": datetime.utcnow().isoformat()
        }
        
        try:
            await AIScreenerService.update_job_status(db, job_id, "FAILED", error_result)
            
            # Refund credits on failure
            job = await db.execute(select(JobStatus).where(JobStatus.id == job_id))
            job_record = job.scalar_one_or_none()
            if job_record:
                cost = job_record.parameters.get("cost", 0)
                await AIScreenerService.refund_credits_on_failure(db, user_id, cost, job_id)
                
        except Exception as status_error:
            logger.error(f"Failed to update job status for {job_id}: {status_error}")


# PUBLIC/USER ENDPOINTS

@router.get("/news/top-positive", response_model=TopNewsResponse)
async def get_top_positive_news(
    date: str = Query(..., description="Date in YYYY-MM-DD format"),
    limit: int = Query(10, ge=1, le=100, description="Number of items to return"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get top positive news items for a specific date.
    """
    try:
        # Parse date
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date format. Use YYYY-MM-DD format."
            )

        # Query top positive news
        query = select(ScreenerNews).where(
            and_(
                ScreenerNews.date == target_date,
                ScreenerNews.sentiment_label == "positive"
            )
        ).order_by(desc(ScreenerNews.sentiment_score)).limit(limit)

        result = await db.execute(query)
        news_items = result.scalars().all()

        # Format response
        formatted_items = []
        for item in news_items:
            formatted_items.append({
                "title": item.title,
                "summary": item.summary,
                "url": item.url,
                "date": item.date,
                "sentiment_label": item.sentiment_label,
                "sentiment_score": float(item.sentiment_score),
                "symbol": item.symbol
            })

        return {
            "items": formatted_items,
            "total": len(formatted_items),
            "date": date,
            "sentiment_type": "positive"
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch top positive news: {str(e)}"
        )


@router.get("/news/top-negative", response_model=TopNewsResponse)
async def get_top_negative_news(
    date: str = Query(..., description="Date in YYYY-MM-DD format"),
    limit: int = Query(10, ge=1, le=100, description="Number of items to return"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get top negative news items for a specific date.
    """
    try:
        # Parse date
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date format. Use YYYY-MM-DD format."
            )

        # Query top negative news
        query = select(ScreenerNews).where(
            and_(
                ScreenerNews.date == target_date,
                ScreenerNews.sentiment_label == "negative"
            )
        ).order_by(asc(ScreenerNews.sentiment_score)).limit(limit)

        result = await db.execute(query)
        news_items = result.scalars().all()

        # Format response
        formatted_items = []
        for item in news_items:
            formatted_items.append({
                "title": item.title,
                "summary": item.summary,
                "url": item.url,
                "date": item.date,
                "sentiment_label": item.sentiment_label,
                "sentiment_score": float(item.sentiment_score),
                "symbol": item.symbol
            })

        return {
            "items": formatted_items,
            "total": len(formatted_items),
            "date": date,
            "sentiment_type": "negative"
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch top negative news: {str(e)}"
        )


@router.get("/news/search", response_model=NewsSearchResponse)
async def search_news(
    query: str = Query(..., min_length=2, description="Search query (symbol or stock name)"),
    date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format"),
    db: AsyncSession = Depends(get_db)
):
    """
    Search news items by query (symbol or stock name) with optional date filter.
    """
    try:
        # Parse optional date
        target_date = None
        if date:
            try:
                target_date = datetime.strptime(date, "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid date format. Use YYYY-MM-DD format."
                )

        # Build query
        news_query = select(ScreenerNews)
        filters = []

        # Add date filter if provided
        if target_date:
            filters.append(ScreenerNews.date == target_date)

        # Add search filters (title, summary, or symbol)
        search_filters = or_(
            ScreenerNews.title.ilike(f"%{query}%"),
            ScreenerNews.summary.ilike(f"%{query}%"),
            ScreenerNews.symbol.ilike(f"%{query}%")
        )
        filters.append(search_filters)

        if filters:
            news_query = news_query.where(and_(*filters))

        # Execute query
        result = await db.execute(news_query)
        news_items = result.scalars().all()

        # Format response
        formatted_items = []
        for item in news_items:
            formatted_items.append({
                "title": item.title,
                "summary": item.summary,
                "url": item.url,
                "date": item.date,
                "sentiment_label": item.sentiment_label,
                "sentiment_score": float(item.sentiment_score),
                "symbol": item.symbol
            })

        return {
            "items": formatted_items,
            "total": len(formatted_items),
            "query": query,
            "date": date
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search news: {str(e)}"
        )


@router.get("/announcements/latest", response_model=LatestAnnouncementsResponse)
async def get_latest_announcements(
    date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format"),
    limit: int = Query(50, ge=1, le=200, description="Number of items to return"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get latest announcements with optional date filter and NSE/BSE links.
    """
    try:
        # Parse optional date
        target_date = None
        if date:
            try:
                target_date = datetime.strptime(date, "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid date format. Use YYYY-MM-DD format."
                )

        # Build query
        announcements_query = select(ScreenerAnnouncements)
        filters = []

        # Add date filter if provided
        if target_date:
            filters.append(ScreenerAnnouncements.date == target_date)

        if filters:
            announcements_query = announcements_query.where(and_(*filters))

        # Order by date descending and limit results
        announcements_query = announcements_query.order_by(
            desc(ScreenerAnnouncements.date),
            desc(ScreenerAnnouncements.time)
        ).limit(limit)

        # Execute query
        result = await db.execute(announcements_query)
        announcements = result.scalars().all()

        # Format response
        formatted_items = []
        for item in announcements:
            formatted_items.append({
                "title": item.title,
                "summary": item.summary,
                "url": item.url,
                "date": item.date,
                "symbol": item.symbol,
                "exchange": item.exchange,
                "nse_link": item.nse_link,
                "bse_link": item.bse_link
            })

        return {
            "items": formatted_items,
            "total": len(formatted_items),
            "date": date
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch latest announcements: {str(e)}"
        )


@router.get("/status")
async def get_screener_status(
    db: AsyncSession = Depends(get_db)
):
    """
    Get last run time and status for NEWS and ANNOUNCEMENTS from screener_runs.
    """
    try:
        # Query for latest news run
        news_query = select(ScreenerRuns).where(
            ScreenerRuns.run_type == "NEWS"
        ).order_by(desc(ScreenerRuns.started_at)).limit(1)

        news_result = await db.execute(news_query)
        latest_news_run = news_result.scalar_one_or_none()

        # Query for latest announcements run
        announcements_query = select(ScreenerRuns).where(
            ScreenerRuns.run_type == "ANNOUNCEMENTS"
        ).order_by(desc(ScreenerRuns.started_at)).limit(1)

        announcements_result = await db.execute(announcements_query)
        latest_announcements_run = announcements_result.scalar_one_or_none()

        # Format response
        return {
            "news": {
                "last_run": latest_news_run.started_at.isoformat() if latest_news_run else None,
                "status": latest_news_run.status if latest_news_run else "never_run",
                "finished_at": latest_news_run.finished_at.isoformat() if latest_news_run and latest_news_run.finished_at else None,
                "error": latest_news_run.error if latest_news_run else None
            },
            "announcements": {
                "last_run": latest_announcements_run.started_at.isoformat() if latest_announcements_run else None,
                "status": latest_announcements_run.status if latest_announcements_run else "never_run",
                "finished_at": latest_announcements_run.finished_at.isoformat() if latest_announcements_run and latest_announcements_run.finished_at else None,
                "error": latest_announcements_run.error if latest_announcements_run else None
            }
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch screener status: {str(e)}"
        )


# ADMIN ENDPOINTS

@router.post("/admin/run", response_model=dict, status_code=status.HTTP_202_ACCEPTED)
async def admin_trigger_ai_screener_run(
    type: str = Query(..., description="Type of AI screener run (news or announcements)"),
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_db),
    admin_user: dict = Depends(get_admin_user)
):
    """
    Admin endpoint to trigger manual AI screener runs.
    """
    try:
        valid_types = ["news", "announcements"]
        if type not in valid_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid AI screener type. Valid types: {valid_types}"
            )

        # Create job for admin run
        job_id = str(uuid4())
        
        job = JobStatus(
            id=job_id,
            user_id=admin_user["user_id"],
            job_type="ADMIN_AI_SCREENER",
            status="PENDING",
            progress=0,
            message=f"Admin-triggered {type} refresh",
            job_data=json.dumps({"type": type, "triggered_by": "admin"}),
            max_retries=3,
            retry_count=0
        )

        db.add(job)
        await db.commit()

        # Submit to background tasks
        if background_tasks:
            if type == "news":
                background_tasks.add_task(
                    _admin_run_news_refresh,
                    db=db,
                    job_id=job_id,
                    admin_user_id=admin_user["user_id"]
                )
            else:
                background_tasks.add_task(
                    _admin_run_announcements_refresh,
                    db=db,
                    job_id=job_id,
                    admin_user_id=admin_user["user_id"]
                )

        return {
            "job_id": job_id,
            "status": "accepted",
            "message": f"Admin-triggered {type} refresh submitted for processing",
            "type": type,
            "triggered_by": admin_user["user_id"],
            "poll_url": f"/api/v1/jobs/{job_id}"
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger admin AI screener run: {str(e)}"
        )


async def _admin_run_news_refresh(db: AsyncSession, job_id: str, admin_user_id: str):
    """Admin background task to run news refresh"""
    try:
        # Update job status to running
        await db.execute(
            update(JobStatus)
            .where(JobStatus.id == job_id)
            .values(
                status="RUNNING",
                progress=10,
                message="Initializing admin news refresh...",
                started_at=datetime.utcnow()
            )
        )
        await db.commit()

        # Import and run news refresh service
        from ...services.ai_screener.job_handlers import AIScreenerJobService
        from ...services.ai_screener import StorageService

        storage_service = StorageService(db)
        run_id = await storage_service.create_screener_run(
            run_type="admin_news_refresh",
            status="RUNNING"
        )

        try:
            # Execute news refresh with default parameters
            await AIScreenerJobService._execute_news_refresh(
                db, job_id, admin_user_id, 
                {"symbols": [], "top_n": 10},  # Default parameters
                storage_service, run_id
            )

            # Update job as completed
            await db.execute(
                update(JobStatus)
                .where(JobStatus.id == job_id)
                .values(
                    status="COMPLETED",
                    progress=100,
                    message="Admin news refresh completed successfully",
                    completed_at=datetime.utcnow()
                )
            )
            await db.commit()

            # Update screener run as completed
            await storage_service.update_screener_run_status(
                run_id, "completed", finished_at=datetime.utcnow()
            )

        except Exception as e:
            # Update screener run as failed
            await storage_service.update_screener_run_status(
                run_id, "failed", finished_at=datetime.utcnow(), error=str(e)
            )
            raise

    except Exception as e:
        # Mark job as failed
        await db.execute(
            update(JobStatus)
            .where(JobStatus.id == job_id)
            .values(
                status="FAILED",
                progress=0,
                message=f"Admin news refresh failed: {str(e)}",
                completed_at=datetime.utcnow()
            )
        )
        await db.commit()


async def _admin_run_announcements_refresh(db: AsyncSession, job_id: str, admin_user_id: str):
    """Admin background task to run announcements refresh"""
    try:
        # Update job status to running
        await db.execute(
            update(JobStatus)
            .where(JobStatus.id == job_id)
            .values(
                status="RUNNING",
                progress=10,
                message="Initializing admin announcements refresh...",
                started_at=datetime.utcnow()
            )
        )
        await db.commit()

        # Import and run announcements refresh service
        from ...services.ai_screener.job_handlers import AIScreenerJobService
        from ...services.ai_screener import StorageService

        storage_service = StorageService(db)
        run_id = await storage_service.create_screener_run(
            run_type="admin_announcements_refresh",
            status="RUNNING"
        )

        try:
            # Execute announcements refresh with default parameters
            await AIScreenerJobService._execute_announcements_refresh(
                db, job_id, admin_user_id,
                {"symbols": [], "top_n": 10},  # Default parameters
                storage_service, run_id
            )

            # Update job as completed
            await db.execute(
                update(JobStatus)
                .where(JobStatus.id == job_id)
                .values(
                    status="COMPLETED",
                    progress=100,
                    message="Admin announcements refresh completed successfully",
                    completed_at=datetime.utcnow()
                )
            )
            await db.commit()

            # Update screener run as completed
            await storage_service.update_screener_run_status(
                run_id, "completed", finished_at=datetime.utcnow()
            )

        except Exception as e:
            # Update screener run as failed
            await storage_service.update_screener_run_status(
                run_id, "failed", finished_at=datetime.utcnow(), error=str(e)
            )
            raise

    except Exception as e:
        # Mark job as failed
        await db.execute(
            update(JobStatus)
            .where(JobStatus.id == job_id)
            .values(
                status="FAILED",
                progress=0,
                message=f"Admin announcements refresh failed: {str(e)}",
                completed_at=datetime.utcnow()
            )
        )
        await db.commit()
