from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, insert, func, and_, or_, desc, asc
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4
import json

from ...db.models import JobStatus, ScreenerNews, ScreenerAnnouncements, ScreenerRuns
from ...services.credits.management import CreditManagementService
from ...schemas.credits import InsufficientCreditsError
from .job_handlers import AIScreenerJobService
from .storage import StorageService


class AIScreenerService:
    """Main service for AI Screener operations with credit management."""
    
    @staticmethod
    async def check_subscription_and_credits(
        db: AsyncSession,
        user_id: str,
        mode: str,
        depth: str
    ) -> Dict[str, Any]:
        """
        Check subscription status and enforce credit policy for AI screener.
        
        Args:
            db: Database session
            user_id: User ID
            mode: AI screener mode
            depth: AI screener depth
            
        Returns:
            Policy result with cost, deducted amount, and remaining balance
            
        Raises:
            ValueError: If insufficient credits or plan restrictions
        """
        # Get user's current balance
        current_balance = await CreditManagementService.get_user_balance(db, user_id)
        
        # Calculate cost based on mode and depth
        cost = await CreditManagementService.compute_ai_screener_cost(mode, depth)
        
        # Check if user has sufficient credits
        if current_balance < cost:
            raise ValueError(f"Insufficient credits. Current balance: {current_balance}, Required: {cost}")
        
        # Create debit transaction
        transaction = await CreditManagementService.debit_credits(
            db=db,
            user_id=user_id,
            amount=cost,
            description=f"AI screener run: {mode} mode, {depth} depth",
            metadata={
                "operation": "ai_screener",
                "mode": mode,
                "depth": depth,
                "cost": float(cost)
            }
        )
        
        # Calculate remaining balance
        remaining_balance = current_balance - cost
        
        return {
            "policy": "credits_deducted",
            "cost": float(cost),
            "deducted": float(cost),
            "remaining_balance": float(remaining_balance),
            "remaining_included": 0,  # No included credits for AI screener
            "message": f"AI screener credits deducted: {cost}"
        }
    
    @staticmethod
    async def create_job_status(
        db: AsyncSession,
        user_id: str,
        mode: str,
        depth: str,
        policy_result: Dict[str, Any]
    ) -> str:
        """
        Create job status record for AI screener job.
        
        Args:
            db: Database session
            user_id: User ID
            mode: AI screener mode
            depth: AI screener depth
            policy_result: Credit policy result
            
        Returns:
            Job ID
        """
        job_id = str(uuid4())
        
        # Create job parameters
        parameters = {
            "mode": mode,
            "depth": depth,
            "policy": policy_result.get("policy"),
            "cost": policy_result.get("cost"),
            "deducted": policy_result.get("deducted")
        }
        
        # Create extra data
        extra_data = {
            "policy_message": policy_result.get("message"),
            "remaining_balance": policy_result.get("remaining_balance"),
            "remaining_included": policy_result.get("remaining_included")
        }
        
        # Create job status record
        job = JobStatus(
            id=job_id,
            user_id=user_id,
            job_type="AI_SCREENER",
            status="PENDING",
            progress=0,
            message="AI screener job submitted",
            parameters=parameters,
            extra_data=extra_data,
            max_retries=3,
            retry_count=0
        )
        
        db.add(job)
        await db.commit()
        
        return job_id
    
    @staticmethod
    async def get_job_status(
        db: AsyncSession,
        job_id: str,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get AI screener job status by ID.
        
        Args:
            db: Database session
            job_id: Job ID
            user_id: User ID
            
        Returns:
            Job status information or None if not found
        """
        result = await db.execute(
            select(JobStatus)
            .where(
                JobStatus.id == job_id,
                JobStatus.user_id == user_id,
                JobStatus.job_type == "AI_SCREENER"
            )
        )
        job = result.scalar_one_or_none()
        
        if not job:
            return None
        
        # Build response
        response = {
            "job_id": job.id,
            "status": job.status,
            "progress": job.progress,
            "message": job.message,
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
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "result": job.result
        }
        
        return response
    
    @staticmethod
    async def update_job_status(
        db: AsyncSession,
        job_id: str,
        status: str,
        result: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Update AI screener job status.
        
        Args:
            db: Database session
            job_id: Job ID
            status: New status
            result: Optional result data
        """
        update_data = {
            "status": status,
            "updated_at": datetime.utcnow()
        }
        
        if status == "RUNNING":
            update_data["started_at"] = datetime.utcnow()
        elif status in ["COMPLETED", "FAILED"]:
            update_data["completed_at"] = datetime.utcnow()
        
        if result:
            update_data["result"] = result
        
        await db.execute(
            update(JobStatus)
            .where(JobStatus.id == job_id)
            .values(**update_data)
        )
        await db.commit()
    
    @staticmethod
    async def refund_credits_on_failure(
        db: AsyncSession,
        user_id: str,
        cost: float,
        job_id: str
    ) -> None:
        """
        Refund credits when AI screener job fails.
        
        Args:
            db: Database session
            user_id: User ID
            cost: Amount to refund
            job_id: Job ID for reference
        """
        if cost > 0:
            await CreditManagementService.refund_credits(
                db=db,
                user_id=user_id,
                amount=Decimal(str(cost)),
                description=f"AI screener job failed: {job_id}",
                job_id=job_id,
                metadata={"refunded_for_job": job_id}
            )
    
    @staticmethod
    async def get_top_positive_news(
        db: AsyncSession,
        date: datetime.date,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get top positive news items for a specific date.
        
        Args:
            db: Database session
            date: Target date
            limit: Number of items to return
            
        Returns:
            List of formatted news items
        """
        query = select(ScreenerNews).where(
            and_(
                ScreenerNews.date == date,
                ScreenerNews.sentiment_label == "positive"
            )
        ).order_by(desc(ScreenerNews.sentiment_score)).limit(limit)
        
        result = await db.execute(query)
        news_items = result.scalars().all()
        
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
        
        return formatted_items
    
    @staticmethod
    async def get_top_negative_news(
        db: AsyncSession,
        date: datetime.date,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get top negative news items for a specific date.
        
        Args:
            db: Database session
            date: Target date
            limit: Number of items to return
            
        Returns:
            List of formatted news items
        """
        query = select(ScreenerNews).where(
            and_(
                ScreenerNews.date == date,
                ScreenerNews.sentiment_label == "negative"
            )
        ).order_by(asc(ScreenerNews.sentiment_score)).limit(limit)
        
        result = await db.execute(query)
        news_items = result.scalars().all()
        
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
        
        return formatted_items
    
    @staticmethod
    async def search_news(
        db: AsyncSession,
        query: str,
        date: Optional[datetime.date] = None
    ) -> List[Dict[str, Any]]:
        """
        Search news items by query with optional date filter.
        
        Args:
            db: Database session
            query: Search query (symbol or stock name)
            date: Optional date filter
            
        Returns:
            List of formatted news items
        """
        news_query = select(ScreenerNews)
        filters = []
        
        # Add date filter if provided
        if date:
            filters.append(ScreenerNews.date == date)
        
        # Add search filters (title, summary, or symbol)
        search_filters = or_(
            ScreenerNews.title.ilike(f"%{query}%"),
            ScreenerNews.summary.ilike(f"%{query}%"),
            ScreenerNews.symbol.ilike(f"%{query}%")
        )
        filters.append(search_filters)
        
        if filters:
            news_query = news_query.where(and_(*filters))
        
        result = await db.execute(news_query)
        news_items = result.scalars().all()
        
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
        
        return formatted_items
    
    @staticmethod
    async def get_latest_announcements(
        db: AsyncSession,
        date: Optional[datetime.date] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get latest announcements with optional date filter.
        
        Args:
            db: Database session
            date: Optional date filter
            limit: Number of items to return
            
        Returns:
            List of formatted announcements
        """
        announcements_query = select(ScreenerAnnouncements)
        filters = []
        
        # Add date filter if provided
        if date:
            filters.append(ScreenerAnnouncements.date == date)
        
        if filters:
            announcements_query = announcements_query.where(and_(*filters))
        
        # Order by date descending and limit results
        announcements_query = announcements_query.order_by(
            desc(ScreenerAnnouncements.date),
            desc(ScreenerAnnouncements.time)
        ).limit(limit)
        
        result = await db.execute(announcements_query)
        announcements = result.scalars().all()
        
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
        
        return formatted_items
    
    @staticmethod
    async def get_screener_status(db: AsyncSession) -> Dict[str, Any]:
        """
        Get last run time and status for NEWS and ANNOUNCEMENTS from screener_runs.
        
        Args:
            db: Database session
            
        Returns:
            Status information for both news and announcements
        """
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
    
    @staticmethod
    async def trigger_admin_run(
        db: AsyncSession,
        user_id: str,
        run_type: str,
        symbols: Optional[List[str]] = None,
        top_n: Optional[int] = None
    ) -> str:
        """
        Trigger admin-run AI screener job.
        
        Args:
            db: Database session
            user_id: Admin user ID
            run_type: Type of run (news or announcements)
            symbols: Optional list of symbols
            top_n: Optional number of items per symbol
            
        Returns:
            Job ID
        """
        job_type = f"ADMIN_AI_SCREENER_{run_type.upper()}"
        
        # Create job parameters
        job_data = {
            "symbols": symbols or [],
            "top_n": top_n or 10
        }
        
        # Create job record
        job_id = await AIScreenerJobService.create_ai_screener_job(
            db=db,
            user_id=user_id,
            job_type=job_type,
            job_data=job_data,
            max_retries=3
        )
        
        return job_id