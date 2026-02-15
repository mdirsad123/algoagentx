"""
Celery tasks for background job processing with Redis fallback support.
"""
from datetime import date
import pandas as pd
import json
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from .celery_app import celery_app, is_celery_available
from .db.session import async_session, engine
from .db.models import JobStatus, PerformanceMetric, Trade, EquityCurve, PnLCalendar
from .services.backtest_service import BacktestService
from .services.metrics import MetricsCalculator
from .services.credits.management import CreditManagementService
from .services.ai_screener.job_handlers import AIScreenerJobService

logger = logging.getLogger(__name__)


def get_sync_db():
    """Get synchronous database session for Celery tasks."""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def run_backtest_task(self, job_id: str, user_id: str, backtest_params: Dict[str, Any]):
    """
    Celery task to run backtest in background with proper error handling and retry policy.

    Args:
        job_id: Unique job identifier
        user_id: User who initiated the job
        backtest_params: Dictionary with backtest parameters
    """
    try:
        logger.info(f"Starting backtest task - Job: {job_id}, User: {user_id}")
        logger.debug(f"Backtest parameters: {backtest_params}")

        # Update job status to running
        update_job_status(job_id, "running", 10, "Initializing backtest...")

        # Get database session
        db = get_sync_db()

        try:
            # Step 1: FETCH_DATA (20%)
            update_job_status(job_id, "running", 20, "Fetching market data...")

            # Convert date strings back to date objects for the backtest service
            from .db.session import get_db_session
            async def run_async_backtest():
                async with get_db_session() as async_db:
                    return await BacktestService.run_backtest(
                        db=async_db,
                        strategy_id=backtest_params["strategy_id"],
                        instrument_id=backtest_params["instrument_id"],
                        timeframe=backtest_params["timeframe"],
                        start_date=date.fromisoformat(backtest_params["start_date"]),
                        end_date=date.fromisoformat(backtest_params["end_date"]),
                        initial_capital=backtest_params["capital"]
                    )

            service_response = asyncio.run(run_async_backtest())

            # Step 2: GENERATE_SIGNALS (50%)
            update_job_status(job_id, "running", 50, "Generating trading signals...")

            # Step 3: BUILD_TRADES (70%)
            update_job_status(job_id, "running", 70, "Building trade history...")

            # Calculate additional metrics if needed
            equity_df = create_equity_dataframe(service_response.result.equity_curve)
            trades_df = create_trades_dataframe(service_response.result.trades)

            metrics = MetricsCalculator.calculate_all_metrics(
                equity_curve=equity_df,
                trades=trades_df,
                initial_capital=backtest_params["capital"]
            )

            # Step 4: METRICS (90%)
            update_job_status(job_id, "running", 90, "Calculating performance metrics...")

            # Save results to database
            backtest_id = save_backtest_results(
                db=db,
                user_id=user_id,
                backtest_params=backtest_params,
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
            update_job_status(
                job_id,
                "completed",
                100,
                "Backtest completed successfully",
                json.dumps(result_data)
            )

            logger.info(f"Job {job_id} completed successfully")
            return result_data

        finally:
            db.close()

    except Exception as exc:
        logger.error(f"Job {job_id} failed: {exc}", exc_info=True)
        return handle_job_failure(self, job_id, user_id, exc)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def run_ai_screener_news_task(self, job_id: str, user_id: str, job_data: Dict[str, Any]):
    """Celery task to run AI Screener news refresh in background."""
    try:
        logger.info(f"Starting AI Screener news task - Job: {job_id}, User: {user_id}")
        
        # Import here to avoid circular imports
        from .db.session import get_db_session
        import asyncio
        
        async def run_async_task():
            async with get_db_session() as db:
                # Create storage service
                from .services.ai_screener import StorageService
                storage_service = StorageService(db)

                # Create screener run record
                run_id = await storage_service.create_screener_run(
                    run_type="ai_screener_news_refresh",
                    status="RUNNING"
                )

                try:
                    # Execute news refresh
                    await AIScreenerJobService._execute_news_refresh(
                        db, job_id, user_id, job_data, storage_service, run_id
                    )

                    # Update screener run as completed
                    await storage_service.update_screener_run_status(
                        run_id, "completed", finished_at=datetime.utcnow()
                    )

                    logger.info(f"AI Screener news task {job_id} completed successfully")

                except Exception as e:
                    # Update screener run as failed
                    await storage_service.update_screener_run_status(
                        run_id, "failed", finished_at=datetime.utcnow(), error=str(e)
                    )
                    raise

        asyncio.run(run_async_task())
        return {"job_id": job_id, "status": "completed"}

    except Exception as exc:
        logger.error(f"AI Screener news task {job_id} failed: {exc}", exc_info=True)
        return AIScreenerJobService._handle_job_failure(self, job_id, user_id, exc)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def run_ai_screener_announcements_task(self, job_id: str, user_id: str, job_data: Dict[str, Any]):
    """Celery task to run AI Screener announcements refresh in background."""
    try:
        logger.info(f"Starting AI Screener announcements task - Job: {job_id}, User: {user_id}")
        
        # Import here to avoid circular imports
        from .db.session import get_db_session
        import asyncio
        
        async def run_async_task():
            async with get_db_session() as db:
                # Create storage service
                from .services.ai_screener import StorageService
                storage_service = StorageService(db)

                # Create screener run record
                run_id = await storage_service.create_screener_run(
                    run_type="ai_screener_announcements_refresh",
                    status="RUNNING"
                )

                try:
                    # Execute announcements refresh
                    await AIScreenerJobService._execute_announcements_refresh(
                        db, job_id, user_id, job_data, storage_service, run_id
                    )

                    # Update screener run as completed
                    await storage_service.update_screener_run_status(
                        run_id, "completed", finished_at=datetime.utcnow()
                    )

                    logger.info(f"AI Screener announcements task {job_id} completed successfully")

                except Exception as e:
                    # Update screener run as failed
                    await storage_service.update_screener_run_status(
                        run_id, "failed", finished_at=datetime.utcnow(), error=str(e)
                    )
                    raise

        asyncio.run(run_async_task())
        return {"job_id": job_id, "status": "completed"}

    except Exception as exc:
        logger.error(f"AI Screener announcements task {job_id} failed: {exc}", exc_info=True)
        return AIScreenerJobService._handle_job_failure(self, job_id, user_id, exc)


def handle_job_failure(task_self, job_id: str, user_id: str, exc: Exception) -> None:
    """Handle job failure with retry logic and credit refund."""
    try:
        # Get current retry count
        retry_count = get_current_retry_count(job_id)
        max_retries = get_job_max_retries(job_id)

        if retry_count < max_retries:
            # Retry with exponential backoff
            delay = 60 * (2 ** retry_count)  # 60s, 120s, 240s
            logger.warning(f"Job {job_id} retrying... (attempt {retry_count + 1}/{max_retries})")
            
            update_job_status(
                job_id,
                "retry",
                0,
                f"Job failed, retrying... (attempt {retry_count + 1}/{max_retries}): {str(exc)}"
            )
            
            # Retry with exponential backoff
            task_self.retry(countdown=delay, exc=exc)
        else:
            # Max retries reached - mark as failed and refund credits
            logger.error(f"Job {job_id} failed permanently after {max_retries} retries")
            return mark_job_failed(job_id, user_id, exc, retry_count)

    except Exception as handler_error:
        logger.error(f"Error in failure handler for job {job_id}: {handler_error}", exc_info=True)
        # Still raise the original exception
        raise exc


def mark_job_failed(job_id: str, user_id: str, exc: Exception, retry_count: int) -> None:
    """Mark job as failed and attempt to refund credits."""
    try:
        # Get debit transaction ID from job status
        db = get_sync_db()
        try:
            job = db.query(JobStatus).filter(JobStatus.id == job_id).first()
            debit_txn_id = job.debit_txn_id if job else None

            refund_info = None
            if debit_txn_id:
                try:
                    # Attempt to refund credits
                    refund_transaction = CreditManagementService.refund_transaction(
                        db=db,
                        transaction_id=debit_txn_id
                    )
                    refund_info = {
                        "refund_transaction_id": str(refund_transaction.id),
                        "refund_amount": float(refund_transaction.amount)
                    }
                    logger.info(f"Auto-refunded credits for failed job {job_id}: {refund_transaction.amount}")
                except Exception as refund_exc:
                    logger.error(f"Failed to auto-refund credits for job {job_id}: {refund_exc}")

            # Update job status with failure details
            failure_details = {
                "error": str(exc),
                "retry_count": retry_count,
                "max_retries": get_job_max_retries(job_id)
            }
            if refund_info:
                failure_details["refund"] = refund_info

            update_job_status(
                job_id,
                "failed",
                0,
                f"Job failed permanently after {retry_count} retries: {str(exc)}",
                json.dumps(failure_details)
            )

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Failed to mark job {job_id} as failed: {e}")

    # Raise the original exception to trigger Celery failure handling
    raise exc


@celery_app.task(bind=True, max_retries=3, default_retry_delay=300)  # 5 minute delay for cleanup
def cleanup_old_jobs_task(self, days_to_keep: int = 30, batch_size: int = 100):
    """
    Periodic task to clean up old job records to prevent database bloat.
    This task runs independently of Redis availability.
    """
    try:
        logger.info(f"Starting job cleanup - removing jobs older than {days_to_keep} days")
        
        db = get_sync_db()
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        total_deleted = 0

        try:
            while True:
                # Delete in batches to avoid long-running transactions
                result = db.execute(
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

                db.commit()
                logger.info(f"Deleted batch of {deleted} old job records")

            logger.info(f"Job cleanup completed - total deleted: {total_deleted}")
            return {"deleted_count": total_deleted, "days_kept": days_to_keep}

        finally:
            db.close()

    except Exception as exc:
        logger.error(f"Job cleanup failed: {exc}", exc_info=True)
        # Retry cleanup task with longer delays
        self.retry(countdown=600, exc=exc)  # Retry after 10 minutes


def update_job_status(job_id: str, status: str, progress: int, message: str, result_data: str = None):
    """Update job status in database with proper error handling."""
    db = get_sync_db()

    try:
        update_data = {
            "status": status,
            "progress": progress,
            "message": message,
            "updated_at": datetime.utcnow()
        }

        if status == "running" and not get_job_started_at(job_id):
            update_data["started_at"] = datetime.utcnow()

        if status in ["completed", "failed"]:
            update_data["completed_at"] = datetime.utcnow()

        if result_data:
            update_data["result_data"] = result_data

        db.execute(
            update(JobStatus)
            .where(JobStatus.id == job_id)
            .values(**update_data)
        )
        db.commit()
    except Exception as e:
        logger.error(f"Failed to update job status for {job_id}: {e}")
        db.rollback()
        raise e
    finally:
        db.close()


def get_current_retry_count(job_id: str) -> int:
    """Get current retry count for job."""
    db = get_sync_db()
    try:
        job = db.query(JobStatus).filter(JobStatus.id == job_id).first()
        return job.retry_count if job else 0
    except Exception as e:
        logger.error(f"Failed to get retry count for job {job_id}: {e}")
        return 0
    finally:
        db.close()


def get_job_max_retries(job_id: str) -> int:
    """Get maximum retry count for job."""
    db = get_sync_db()
    try:
        job = db.query(JobStatus).filter(JobStatus.id == job_id).first()
        return job.max_retries if job else 3
    except Exception as e:
        logger.error(f"Failed to get max retries for job {job_id}: {e}")
        return 3
    finally:
        db.close()


def get_job_started_at(job_id: str):
    """Check if job has been started."""
    db = get_sync_db()
    try:
        job = db.query(JobStatus).filter(JobStatus.id == job_id).first()
        return job.started_at if job else None
    except Exception as e:
        logger.error(f"Failed to get started_at for job {job_id}: {e}")
        return None
    finally:
        db.close()


def create_equity_dataframe(equity_curve: list) -> 'pd.DataFrame':
    """Create pandas DataFrame from equity curve data."""
    import pandas as pd
    return pd.DataFrame({
        'timestamp': range(len(equity_curve)),
        'equity': equity_curve
    })


def create_trades_dataframe(trades: list) -> 'pd.DataFrame':
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


def save_backtest_results(db, user_id: str, backtest_params: Dict[str, Any],
                         service_response, metrics: Dict[str, Any]) -> str:
    """Save backtest results to database with proper error handling."""
    from uuid import uuid4
    from datetime import date
    from decimal import Decimal

    backtest_id = uuid4()

    try:
        # Save performance metrics
        db.add(PerformanceMetric(
            id=backtest_id,
            user_id=user_id,
            strategy_id=backtest_params["strategy_id"],
            instrument_id=backtest_params["instrument_id"],
            timeframe=backtest_params["timeframe"],
            start_date=date.fromisoformat(backtest_params["start_date"]),
            end_date=date.fromisoformat(backtest_params["end_date"]),
            initial_capital=Decimal(str(backtest_params["capital"])),
            final_capital=Decimal(str(service_response.final_capital)),
            net_profit=Decimal(str(metrics["net_profit"])),
            max_drawdown=Decimal(str(metrics["max_drawdown"])),
            sharpe_ratio=Decimal(str(metrics["sharpe_ratio"])),
            win_rate=Decimal(str(metrics["win_rate"])),
            total_trades=service_response.total_trades,
            status="completed"
        ))

        # Save trades
        if service_response.result.trades:
            for trade in service_response.result.trades:
                db.add(Trade(
                    backtest_id=backtest_id,
                    instrument_id=backtest_params["instrument_id"],
                    entry_time=trade.entry_datetime,
                    exit_time=trade.exit_datetime,
                    side=trade.direction,
                    quantity=int(trade.quantity),
                    entry_price=Decimal(str(trade.entry_price)),
                    exit_price=Decimal(str(trade.exit_price)) if trade.exit_price else None,
                    pnl=Decimal(str(trade.pnl)) if trade.pnl else None,
                    exit_type=trade.exit_reason
                ))

        # Save equity curve
        if service_response.result.equity_curve:
            base_date = service_response.start_date
            for i, equity in enumerate(service_response.result.equity_curve):
                db.add(EquityCurve(
                    backtest_id=backtest_id,
                    timestamp=base_date,
                    equity=Decimal(str(equity))
                ))

        # Save PnL calendar
        pnl_data = {}
        for trade in service_response.result.trades:
            day = trade.exit_datetime.date()
            if day not in pnl_data:
                pnl_data[day] = 0
            pnl_data[day] += trade.pnl

        if pnl_data:
            for day, pnl in pnl_data.items():
                db.add(PnLCalendar(
                    backtest_id=backtest_id,
                    date=day,
                    pnl=Decimal(str(pnl))
                ))

        db.commit()
        return str(backtest_id)

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to save backtest results for job {backtest_params.get('job_id', 'unknown')}: {e}")
        raise e