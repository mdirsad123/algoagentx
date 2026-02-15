import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import SQLAlchemyError
import json
from uuid import uuid4

from ...celery_app import celery_app, is_celery_available
from ...core.redis_manager import redis_manager
from ...db.models import ScreenerNews, ScreenerAnnouncements, ScreenerRuns
from . import NewsFetcherService, AnnouncementsFetcherService, SentimentEngineService, StorageService
from ...core.config import settings
from ...schemas.screener import ScreenerNewsCreate, ScreenerAnnouncementsCreate

logger = logging.getLogger(__name__)


class AIScreenerJobService:
    """Service for handling AI Screener background jobs"""
    
    @staticmethod
    async def create_ai_screener_job(
        db: AsyncSession,
        user_id: str,
        job_type: str,
        job_data: Dict[str, Any],
        max_retries: int = 3
    ) -> str:
        """
        Create a new AI Screener job with retry configuration.

        Args:
            db: Database session
            user_id: User ID who initiated the job
            job_type: Type of job (ai_screener_news_refresh or ai_screener_announcements_refresh)
            job_data: Job parameters as dictionary
            max_retries: Maximum number of retry attempts

        Returns:
            Job ID
        """
        job_id = str(uuid4())

        # Create job record in JobStatus table
        from ..db.models import JobStatus
        job = JobStatus(
            id=job_id,
            user_id=user_id,
            job_type=job_type,
            status="pending",
            progress=0,
            message="Job queued",
            job_data=json.dumps(job_data),
            max_retries=max_retries,
            retry_count=0
        )

        db.add(job)
        await db.commit()

        logger.info(f"Created AI Screener job {job_id} for user {user_id}, type: {job_type}")
        return job_id

    @staticmethod
    async def submit_ai_screener_job(
        db: AsyncSession,
        user_id: str,
        job_type: str,
        symbols: Optional[list] = None,
        top_n: Optional[int] = None
    ) -> str:
        """
        Submit an AI Screener job with Redis fallback support.

        Args:
            db: Database session
            user_id: User ID
            job_type: Job type (ai_screener_news_refresh or ai_screener_announcements_refresh)
            symbols: List of symbols to fetch data for (optional)
            top_n: Number of items to fetch per symbol (optional)

        Returns:
            Job ID
        """
        # Prepare job data
        job_data = {
            "symbols": symbols or [],
            "top_n": top_n or settings.ai_screener_top_n
        }

        # Create job record
        job_id = await AIScreenerJobService.create_ai_screener_job(
            db=db,
            user_id=user_id,
            job_type=job_type,
            job_data=job_data
        )

        # Try to submit to Celery/Redis
        if is_celery_available() and redis_manager.is_available:
            try:
                logger.info(f"Submitting AI Screener job {job_id} to Celery with Redis backend")
                # Import tasks here to avoid circular imports
                from ..tasks import run_ai_screener_news_task, run_ai_screener_announcements_task
                
                if job_type == "ai_screener_news_refresh":
                    run_ai_screener_news_task.delay(job_id, user_id, job_data)
                elif job_type == "ai_screener_announcements_refresh":
                    run_ai_screener_announcements_task.delay(job_id, user_id, job_data)
                else:
                    raise ValueError(f"Unknown job type: {job_type}")
                
                await AIScreenerJobService._update_job_status(
                    db, job_id, "queued", 0, "Job submitted to queue"
                )
                return job_id
            except Exception as e:
                logger.error(f"Failed to submit AI Screener job {job_id} to Celery: {e}")
                logger.warning("Falling back to direct execution")

        # Fallback: Execute job directly in background
        logger.info(f"Executing AI Screener job {job_id} directly (Redis unavailable)")
        await AIScreenerJobService._execute_ai_screener_job_directly(
            db, job_id, user_id, job_type, job_data
        )
        return job_id

    @staticmethod
    async def _execute_ai_screener_job_directly(
        db: AsyncSession,
        job_id: str,
        user_id: str,
        job_type: str,
        job_data: Dict[str, Any]
    ) -> None:
        """
        Execute AI Screener job directly without Celery/Redis with improved error resilience.
        This method is called when Redis is unavailable.
        """
        try:
            # Update job status to running
            await AIScreenerJobService._update_job_status(
                db, job_id, "running", 10, "Initializing AI Screener..."
            )

            # Create storage service
            storage_service = StorageService(db)

            # Create screener run record
            run_id = await storage_service.create_screener_run(
                run_type=job_type,
                status="RUNNING"
            )

            try:
                if job_type == "ai_screener_news_refresh":
                    await AIScreenerJobService._execute_news_refresh(
                        db, job_id, user_id, job_data, storage_service, run_id
                    )
                elif job_type == "ai_screener_announcements_refresh":
                    await AIScreenerJobService._execute_announcements_refresh(
                        db, job_id, user_id, job_data, storage_service, run_id
                    )
                else:
                    raise ValueError(f"Unknown job type: {job_type}")

                # Update job as completed
                await AIScreenerJobService._update_job_status(
                    db, job_id, "completed", 100, "AI Screener completed successfully"
                )

                # Update screener run as completed
                await storage_service.update_screener_run_status(
                    run_id, "completed", finished_at=datetime.utcnow()
                )

                logger.info(f"AI Screener job {job_id} completed successfully")

            except Exception as e:
                # Update screener run as failed
                await storage_service.update_screener_run_status(
                    run_id, "failed", finished_at=datetime.utcnow(), error=str(e)
                )
                raise

        except Exception as e:
            logger.error(f"AI Screener job {job_id} failed: {e}", exc_info=True)
            try:
                await AIScreenerJobService._update_job_status(
                    db, job_id, "failed", 0, f"Job failed: {str(e)}"
                )
            except Exception as status_error:
                logger.error(f"Failed to update job status for {job_id}: {status_error}")
            raise AIScreenerError(f"AI Screener job {job_id} failed: {e}")


    @staticmethod
    async def _execute_news_refresh(
        db: AsyncSession,
        job_id: str,
        user_id: str,
        job_data: Dict[str, Any],
        storage_service: StorageService,
        run_id: str
    ) -> None:
        """Execute news refresh job"""
        try:
            # Update progress
            await AIScreenerJobService._update_job_status(
                db, job_id, "running", 30, "Fetching news data..."
            )

            # Create services
            news_fetcher = NewsFetcherService()
            sentiment_engine = SentimentEngineService()

            # Get symbols to process
            symbols = job_data.get("symbols", [])
            if not symbols:
                # Default symbols if none provided
                symbols = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK"]

            all_news_items = []
            
            for symbol in symbols:
                try:
                    # Update progress for each symbol
                    progress = 30 + (symbols.index(symbol) * 50 // len(symbols))
                    await AIScreenerJobService._update_job_status(
                        db, job_id, "running", progress, f"Processing news for {symbol}..."
                    )

                    # Fetch news for symbol
                    news_items = await news_fetcher.fetch_news_for_symbol(
                        symbol=symbol,
                        top_n=job_data.get("top_n", 10),
                        sources=settings.ai_screener_sources.split(",")
                    )

                    if news_items:
                        # Analyze sentiment
                        analyzed_news = sentiment_engine.analyze_news_sentiment(news_items)
                        all_news_items.extend(analyzed_news)

                except Exception as e:
                    logger.error(f"Error processing news for symbol {symbol}: {e}")
                    continue

            # Update progress
            await AIScreenerJobService._update_job_status(
                db, job_id, "running", 90, "Storing news data..."
            )

            # Store news items
            stored_count = await storage_service.store_news_items(all_news_items, run_id)

            # Prepare result data
            result_data = {
                "run_id": run_id,
                "symbols_processed": len(symbols),
                "news_items_fetched": len(all_news_items),
                "news_items_stored": stored_count,
                "symbols": symbols
            }

            # Update job status with result
            await AIScreenerJobService._update_job_status(
                db, job_id, "completed", 100, "News refresh completed successfully", result_data
            )

        except Exception as e:
            logger.error(f"News refresh failed: {e}")
            raise

    @staticmethod
    async def _execute_announcements_refresh(
        db: AsyncSession,
        job_id: str,
        user_id: str,
        job_data: Dict[str, Any],
        storage_service: StorageService,
        run_id: str
    ) -> None:
        """Execute announcements refresh job"""
        try:
            # Update progress
            await AIScreenerJobService._update_job_status(
                db, job_id, "running", 30, "Fetching announcements data..."
            )

            # Create services
            announcements_fetcher = AnnouncementsFetcherService()
            sentiment_engine = SentimentEngineService()

            # Get symbols to process
            symbols = job_data.get("symbols", [])
            if not symbols:
                # Default symbols if none provided
                symbols = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK"]

            all_announcements = []
            
            for symbol in symbols:
                try:
                    # Update progress for each symbol
                    progress = 30 + (symbols.index(symbol) * 50 // len(symbols))
                    await AIScreenerJobService._update_job_status(
                        db, job_id, "running", progress, f"Processing announcements for {symbol}..."
                    )

                    # Fetch announcements for symbol
                    announcements = await announcements_fetcher.fetch_announcements_for_symbol(
                        symbol=symbol,
                        top_n=job_data.get("top_n", 10)
                    )

                    if announcements:
                        # Analyze sentiment
                        analyzed_announcements = sentiment_engine.analyze_announcement_sentiment(announcements)
                        all_announcements.extend(analyzed_announcements)

                except Exception as e:
                    logger.error(f"Error processing announcements for symbol {symbol}: {e}")
                    continue

            # Update progress
            await AIScreenerJobService._update_job_status(
                db, job_id, "running", 90, "Storing announcements data..."
            )

            # Store announcements
            stored_count = await storage_service.store_announcements(all_announcements, run_id)

            # Prepare result data
            result_data = {
                "run_id": run_id,
                "symbols_processed": len(symbols),
                "announcements_fetched": len(all_announcements),
                "announcements_stored": stored_count,
                "symbols": symbols
            }

            # Update job status with result
            await AIScreenerJobService._update_job_status(
                db, job_id, "completed", 100, "Announcements refresh completed successfully", result_data
            )

        except Exception as e:
            logger.error(f"Announcements refresh failed: {e}")
            raise

    @staticmethod
    async def retry_ai_screener_job(db: AsyncSession, job_id: str, user_id: str) -> bool:
        """
        Retry a failed AI Screener job with proper retry policy.

        Args:
            db: Database session
            job_id: Job ID
            user_id: User ID

        Returns:
            True if retry was initiated, False otherwise
        """
        from ..db.models import JobStatus
        
        result = await db.execute(
            select(JobStatus).where(
                JobStatus.id == job_id,
                JobStatus.user_id == user_id,
                JobStatus.status.in_(["failed", "retry"]),
                JobStatus.job_type.in_(["ai_screener_news_refresh", "ai_screener_announcements_refresh"])
            )
        )
        job = result.scalar_one_or_none()

        if not job or job.retry_count >= job.max_retries:
            logger.warning(f"AI Screener job {job_id} cannot be retried - max retries reached or not found")
            return False

        # Reset job status for retry
        await db.execute(
            update(JobStatus)
            .where(JobStatus.id == job_id)
            .values(
                status="pending",
                progress=0,
                message="Job queued for retry",
                retry_count=job.retry_count + 1,
                started_at=None,
                completed_at=None,
                result_data=None,
                updated_at=datetime.utcnow()
            )
        )
        await db.commit()

        # Re-submit job with retry logic
        job_data = json.loads(job.job_data)
        await AIScreenerJobService.submit_ai_screener_job(
            db=db,
            user_id=user_id,
            job_type=job.job_type,
            symbols=job_data.get("symbols"),
            top_n=job_data.get("top_n")
        )

        logger.info(f"AI Screener job {job_id} retry initiated (attempt {job.retry_count + 1}/{job.max_retries})")
        return True

    @staticmethod
    async def _update_job_status(
        db: AsyncSession,
        job_id: str,
        status: str,
        progress: int,
        message: str,
        result_data: Optional[Dict] = None
    ) -> None:
        """Update job status in database with proper error handling."""
        from ..db.models import JobStatus
        
        update_data = {
            "status": status,
            "progress": progress,
            "message": message,
            "updated_at": datetime.utcnow()
        }

        if status == "running" and not await AIScreenerJobService._get_job_started_at(db, job_id):
            update_data["started_at"] = datetime.utcnow()

        if status in ["completed", "failed"]:
            update_data["completed_at"] = datetime.utcnow()

        if result_data:
            update_data["result_data"] = json.dumps(result_data)

        await db.execute(
            update(JobStatus)
            .where(JobStatus.id == job_id)
            .values(**update_data)
        )
        await db.commit()

    @staticmethod
    async def _get_job_started_at(db: AsyncSession, job_id: str) -> Optional[datetime]:
        """Check if job has been started."""
        from ..db.models import JobStatus
        
        result = await db.execute(
            select(JobStatus.started_at).where(JobStatus.id == job_id)
        )
        return result.scalar_one_or_none()


# Celery task definitions are defined in app.tasks module to avoid circular imports


def _handle_job_failure(task_self, job_id: str, user_id: str, exc: Exception) -> None:
    """Handle AI Screener job failure with retry logic."""
    try:
        # Get current retry count
        from ..db.session import get_db_session
        import asyncio
        
        async def get_retry_info():
            async with get_db_session() as db:
                from ..db.models import JobStatus
                result = await db.execute(
                    select(JobStatus.retry_count, JobStatus.max_retries)
                    .where(JobStatus.id == job_id)
                )
                row = result.fetchone()
                return row if row else (0, 3)
        
        retry_count, max_retries = asyncio.run(get_retry_info())

        if retry_count < max_retries:
            # Retry with exponential backoff
            delay = 60 * (2 ** retry_count)  # 60s, 120s, 240s
            logger.warning(f"AI Screener job {job_id} retrying... (attempt {retry_count + 1}/{max_retries})")
            
            # Update job status
            async def update_status():
                async with get_db_session() as db:
                    await AIScreenerJobService._update_job_status(
                        db, job_id, "retry", 0,
                        f"Job failed, retrying... (attempt {retry_count + 1}/{max_retries}): {str(exc)}"
                    )
            
            asyncio.run(update_status())
            
            # Retry with exponential backoff
            task_self.retry(countdown=delay, exc=exc)
        else:
            # Max retries reached - mark as failed
            logger.error(f"AI Screener job {job_id} failed permanently after {max_retries} retries")
            
            async def mark_failed():
                async with get_db_session() as db:
                    await AIScreenerJobService._update_job_status(
                        db, job_id, "failed", 0,
                        f"Job failed permanently after {max_retries} retries: {str(exc)}"
                    )
            
            asyncio.run(mark_failed())
            raise exc
    except Exception as handler_error:
        logger.error(f"Error in AI Screener job failure handler for job {job_id}: {handler_error}")
        raise exc
