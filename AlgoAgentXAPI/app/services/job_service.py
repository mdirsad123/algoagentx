"""
Job management service for background tasks with Redis fallback support.
"""

import json
import logging
from uuid import uuid4
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_
from sqlalchemy.orm import selectinload
from ..db.models import JobStatus
from ..celery_app import celery_app, is_celery_available
from ..core.redis_manager import redis_manager
from ..tasks import run_backtest_task

logger = logging.getLogger(__name__)


class JobService:
    @staticmethod
    async def create_job(
        db: AsyncSession,
        user_id: str,  # UUID string from auth
        job_type: str,
        job_data: Dict[str, Any],
        max_retries: int = 3
    ) -> str:
        """
        Create a new background job with retry configuration.

        Args:
            db: Database session
            user_id: User ID who initiated the job
            job_type: Type of job (e.g., 'backtest')
            job_data: Job parameters as dictionary
            max_retries: Maximum number of retry attempts

        Returns:
            Job ID
        """
        job_id = str(uuid4())

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

        logger.info(f"Created job {job_id} for user {user_id}, type: {job_type}")
        return job_id

    @staticmethod
    async def get_job_status(db: AsyncSession, job_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get job status by ID with authorization check.

        Args:
            db: Database session
            job_id: Job ID
            user_id: User ID (for authorization)

        Returns:
            Job status dictionary or None if not found
        """
        result = await db.execute(
            select(JobStatus).where(
                JobStatus.id == job_id,
                JobStatus.user_id == user_id
            )
        )
        job = result.scalar_one_or_none()

        if not job:
            return None

        return {
            "id": job.id,
            "job_type": job.job_type,
            "status": job.status,
            "progress": job.progress,
            "message": job.message,
            "retry_count": job.retry_count,
            "max_retries": job.max_retries,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "job_data": json.loads(job.job_data) if job.job_data else None,
            "result_data": json.loads(job.result_data) if job.result_data else None,
            "debit_txn_id": job.debit_txn_id,
        }

    @staticmethod
    async def submit_backtest_job(
        db: AsyncSession,
        user_id: str,  # UUID string from auth
        strategy_id: str,
        instrument_id: int,
        timeframe: str,
        start_date: str,
        end_date: str,
        capital: float
    ) -> str:
        """
        Submit a backtest job with Redis fallback support.

        Args:
            db: Database session
            user_id: User ID
            strategy_id: Strategy ID
            instrument_id: Instrument ID
            timeframe: Timeframe
            start_date: Start date (ISO string)
            end_date: End date (ISO string)
            capital: Initial capital

        Returns:
            Job ID
        """
        # Prepare job data - keep dates as strings for JSON serialization
        job_data = {
            "strategy_id": strategy_id,
            "instrument_id": instrument_id,
            "timeframe": timeframe,
            "start_date": start_date,  # Keep as ISO string
            "end_date": end_date,      # Keep as ISO string
            "capital": capital
        }

        # Create job record
        job_id = await JobService.create_job(
            db=db,
            user_id=user_id,
            job_type="backtest",
            job_data=job_data
        )

        # Try to submit to Celery/Redis
        if is_celery_available() and redis_manager.is_available:
            try:
                logger.info(f"Submitting job {job_id} to Celery with Redis backend")
                run_backtest_task.delay(job_id, user_id, job_data)
                await JobService._update_job_status(
                    db, job_id, "queued", 0, "Job submitted to queue"
                )
                return job_id
            except Exception as e:
                logger.error(f"Failed to submit job {job_id} to Celery: {e}")
                logger.warning("Falling back to direct execution")

        # Fallback: Execute job directly in background
        logger.info(f"Executing job {job_id} directly (Redis unavailable)")
        await JobService._execute_job_directly(db, job_id, user_id, job_data)
        return job_id

    @staticmethod
    async def _execute_job_directly(
        db: AsyncSession,
        job_id: str,
        user_id: str,
        job_data: Dict[str, Any]
    ) -> None:
        """
        Execute job directly without Celery/Redis.
        This method is called when Redis is unavailable.
        """
        try:
            # Update job status to running
            await JobService._update_job_status(
                db, job_id, "running", 10, "Initializing backtest..."
            )

            # Import and run the backtest service directly
            from ..services.backtest_service import BacktestService
            from ..services.metrics import MetricsCalculator
            from datetime import date
            import pandas as pd

            # Convert date strings back to date objects
            start_date = date.fromisoformat(job_data["start_date"])
            end_date = date.fromisoformat(job_data["end_date"])

            # Run the backtest
            service_response = await BacktestService.run_backtest(
                db=db,
                strategy_id=job_data["strategy_id"],
                instrument_id=job_data["instrument_id"],
                timeframe=job_data["timeframe"],
                start_date=start_date,
                end_date=end_date,
                initial_capital=job_data["capital"]
            )

            # Calculate metrics
            equity_df = JobService._create_equity_dataframe(service_response.result.equity_curve)
            trades_df = JobService._create_trades_dataframe(service_response.result.trades)

            metrics = MetricsCalculator.calculate_all_metrics(
                equity_curve=equity_df,
                trades=trades_df,
                initial_capital=job_data["capital"]
            )

            # Save results to database
            backtest_id = await JobService._save_backtest_results(
                db=db,
                user_id=user_id,
                job_data=job_data,
                service_response=service_response,
                metrics=metrics
            )

            # Prepare result data
            result_data = {
                "backtest_id": str(backtest_id),
                "strategy_name": service_response.strategy_name,
                "instrument_symbol": service_response.instrument_symbol,
                "timeframe": service_response.timeframe,
                "start_date": service_response.start_date.isoformat(),
                "end_date": service_response.end_date.isoformat(),
                "initial_capital": float(service_response.initial_capital),
                "final_capital": float(service_response.final_capital),
                "net_profit": metrics["net_profit"],
                "max_drawdown": metrics["max_drawdown"],
                "sharpe_ratio": metrics["sharpe_ratio"],
                "win_rate": metrics["win_rate"],
                "profit_factor": metrics["profit_factor"],
                "total_trades": service_response.total_trades,
                "trades": [
                    {
                        "entry_time": trade.entry_datetime.isoformat(),
                        "exit_time": trade.exit_datetime.isoformat() if trade.exit_datetime else None,
                        "side": trade.direction,
                        "quantity": float(trade.quantity),
                        "entry_price": float(trade.entry_price),
                        "exit_price": float(trade.exit_price) if trade.exit_price else None,
                        "pnl": float(trade.pnl) if trade.pnl else None,
                        "exit_type": trade.exit_reason
                    }
                    for trade in service_response.result.trades
                ],
                "equity_curve": [
                    {
                        "timestamp": service_response.start_date.isoformat(),
                        "equity": float(equity)
                    }
                    for equity in service_response.result.equity_curve
                ]
            }

            # Update job as completed
            await JobService._update_job_status(
                db, job_id, "completed", 100, "Backtest completed successfully", result_data
            )

            logger.info(f"Job {job_id} completed successfully")

        except Exception as e:
            logger.error(f"Job {job_id} failed: {e}")
            await JobService._update_job_status(
                db, job_id, "failed", 0, f"Job failed: {str(e)}"
            )
            raise

    @staticmethod
    async def retry_job(db: AsyncSession, job_id: str, user_id: str) -> bool:
        """
        Retry a failed job with proper retry policy.

        Args:
            db: Database session
            job_id: Job ID
            user_id: User ID

        Returns:
            True if retry was initiated, False otherwise
        """
        result = await db.execute(
            select(JobStatus).where(
                JobStatus.id == job_id,
                JobStatus.user_id == user_id,
                JobStatus.status.in_(["failed", "retry"])
            )
        )
        job = result.scalar_one_or_none()

        if not job or job.retry_count >= job.max_retries:
            logger.warning(f"Job {job_id} cannot be retried - max retries reached or not found")
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
        if job.job_type == "backtest":
            await JobService.submit_backtest_job(
                db=db,
                user_id=user_id,
                strategy_id=job_data["strategy_id"],
                instrument_id=job_data["instrument_id"],
                timeframe=job_data["timeframe"],
                start_date=job_data["start_date"],
                end_date=job_data["end_date"],
                capital=job_data["capital"]
            )

        logger.info(f"Job {job_id} retry initiated (attempt {job.retry_count + 1}/{job.max_retries})")
        return True

    @staticmethod
    async def get_user_jobs(
        db: AsyncSession,
        user_id: str,  # UUID string from auth
        job_type: Optional[str] = None,
        limit: int = 50
    ) -> list:
        """
        Get jobs for a user with pagination and filtering.

        Args:
            db: Database session
            user_id: User ID
            job_type: Optional job type filter
            limit: Maximum number of jobs to return

        Returns:
            List of job dictionaries
        """
        query = select(JobStatus).where(JobStatus.user_id == user_id)

        if job_type:
            query = query.where(JobStatus.job_type == job_type)

        query = query.order_by(JobStatus.created_at.desc()).limit(limit)

        result = await db.execute(query)
        jobs = result.scalars().all()

        return [
            {
                "id": job.id,
                "job_type": job.job_type,
                "status": job.status,
                "progress": job.progress,
                "message": job.message,
                "retry_count": job.retry_count,
                "max_retries": job.max_retries,
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            }
            for job in jobs
        ]

    @staticmethod
    async def cleanup_old_jobs(
        db: AsyncSession,
        days_to_keep: int = 30,
        batch_size: int = 100
    ) -> int:
        """
        Archive old job_status entries to prevent database bloat.
        This is a cleanup job that should be run periodically.

        Args:
            db: Database session
            days_to_keep: Number of days to keep job records
            batch_size: Number of records to delete in each batch

        Returns:
            Number of records deleted
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        total_deleted = 0

        logger.info(f"Starting job cleanup - removing jobs older than {days_to_keep} days")

        while True:
            # Delete in batches to avoid long-running transactions
            result = await db.execute(
                delete(JobStatus)
                .where(
                    and_(
                        JobStatus.created_at < cutoff_date,
                        JobStatus.status.in_(["completed", "failed"])
                    )
                )
                .limit(batch_size)
            )
            
            deleted = result.rowcount
            total_deleted += deleted

            if deleted == 0:
                break

            await db.commit()
            logger.info(f"Deleted batch of {deleted} old job records")

        logger.info(f"Job cleanup completed - total deleted: {total_deleted}")
        return total_deleted

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
        update_data = {
            "status": status,
            "progress": progress,
            "message": message,
            "updated_at": datetime.utcnow()
        }

        if status == "running" and not await JobService._get_job_started_at(db, job_id):
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
        result = await db.execute(
            select(JobStatus.started_at).where(JobStatus.id == job_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    def _create_equity_dataframe(equity_curve: list) -> 'pd.DataFrame':
        """Create pandas DataFrame from equity curve data."""
        import pandas as pd
        return pd.DataFrame({
            'timestamp': range(len(equity_curve)),
            'equity': equity_curve
        })

    @staticmethod
    def _create_trades_dataframe(trades: list) -> 'pd.DataFrame':
        """Create pandas DataFrame from trades data."""
        import pandas as pd
        return pd.DataFrame([
            {
                'entry_time': trade.entry_datetime,
                'exit_time': trade.exit_datetime,
                'pnl': trade.pnl
            }
            for trade in trades
        ])

    @staticmethod
    async def _save_backtest_results(
        db: AsyncSession,
        user_id: str,
        job_data: Dict[str, Any],
        service_response,
        metrics: Dict[str, Any]
    ) -> str:
        """Save backtest results to database."""
        from uuid import uuid4
        from datetime import date
        from decimal import Decimal
        from ..db.models import PerformanceMetric, Trade, EquityCurve, PnLCalendar
        from sqlalchemy import insert

        backtest_id = uuid4()

        try:
            # Save performance metrics
            await db.execute(
                insert(PerformanceMetric).values(
                    id=backtest_id,
                    user_id=user_id,
                    strategy_id=job_data["strategy_id"],
                    instrument_id=job_data["instrument_id"],
                    timeframe=job_data["timeframe"],
                    start_date=date.fromisoformat(job_data["start_date"]),
                    end_date=date.fromisoformat(job_data["end_date"]),
                    initial_capital=Decimal(str(job_data["capital"])),
                    final_capital=Decimal(str(service_response.final_capital)),
                    net_profit=Decimal(str(metrics["net_profit"])),
                    max_drawdown=Decimal(str(metrics["max_drawdown"])),
                    sharpe_ratio=Decimal(str(metrics["sharpe_ratio"])),
                    win_rate=Decimal(str(metrics["win_rate"])),
                    total_trades=service_response.total_trades,
                    status="completed"
                )
            )

            # Save trades
            if service_response.result.trades:
                trade_values = [
                    {
                        "backtest_id": backtest_id,
                        "instrument_id": job_data["instrument_id"],
                        "entry_time": trade.entry_datetime,
                        "exit_time": trade.exit_datetime,
                        "side": trade.direction,
                        "quantity": int(trade.quantity),
                        "entry_price": trade.entry_price,
                        "exit_price": trade.exit_price,
                        "pnl": trade.pnl,
                        "exit_type": trade.exit_reason
                    }
                    for trade in service_response.result.trades
                ]
                await db.execute(insert(Trade), trade_values)

            # Save equity curve
            if service_response.result.equity_curve:
                base_date = service_response.start_date
                equity_values = [
                    {
                        "backtest_id": backtest_id,
                        "timestamp": base_date,
                        "equity": equity
                    }
                    for equity in service_response.result.equity_curve
                ]
                await db.execute(insert(EquityCurve), equity_values)

            # Save PnL calendar
            pnl_data = {}
            for trade in service_response.result.trades:
                day = trade.exit_datetime.date()
                if day not in pnl_data:
                    pnl_data[day] = 0
                pnl_data[day] += trade.pnl

            if pnl_data:
                pnl_values = [
                    {"backtest_id": backtest_id, "date": day, "pnl": pnl}
                    for day, pnl in pnl_data.items()
                ]
                await db.execute(insert(PnLCalendar), pnl_values)

            await db.commit()
            return str(backtest_id)
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to save backtest results for job {job_id}: {e}")
            raise e



