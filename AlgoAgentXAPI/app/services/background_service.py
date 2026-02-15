"""
Background task service with Redis fallback support.
"""
import pandas as pd
import logging
import asyncio
from typing import Dict, Any, Optional, Callable
from fastapi import BackgroundTasks
from .job_service import JobService
from ..celery_app import celery_app, is_celery_available
from ..core.redis_manager import redis_manager
from ..db.session import get_db_session
from ..services.credits.calculation import CreditCalculationService
from ..services.credits.management import CreditManagementService

logger = logging.getLogger(__name__)


class BackgroundService:
    """Service for managing background tasks with Redis fallback."""

    @staticmethod
    async def submit_backtest_job(
        user_id: str,
        strategy_id: str,
        instrument_id: int,
        timeframe: str,
        start_date: str,
        end_date: str,
        capital: float,
        background_tasks: Optional[BackgroundTasks] = None
    ) -> str:
        """
        Submit backtest job with Redis/Celery fallback to FastAPI BackgroundTasks.
        
        Args:
            user_id: User ID
            strategy_id: Strategy ID
            instrument_id: Instrument ID
            timeframe: Timeframe
            start_date: Start date (ISO string)
            end_date: End date (ISO string)
            capital: Initial capital
            background_tasks: FastAPI BackgroundTasks instance (for fallback)
            
        Returns:
            Job ID
        """
        # Create job data
        job_data = {
            "strategy_id": strategy_id,
            "instrument_id": instrument_id,
            "timeframe": timeframe,
            "start_date": start_date,
            "end_date": end_date,
            "capital": capital
        }

        # Create database session for job creation
        async with get_db_session() as db:
            # Create job record
            job_id = await JobService.create_job(
                db=db,
                user_id=user_id,
                job_type="backtest",
                job_data=job_data
            )

        # Try to use Celery/Redis if available
        if is_celery_available() and redis_manager.is_available:
            try:
                logger.info(f"Submitting job {job_id} to Celery with Redis backend")
                from ..tasks import run_backtest_task
                run_backtest_task.delay(job_id, user_id, job_data)
                return job_id
            except Exception as e:
                logger.error(f"Failed to submit job {job_id} to Celery: {e}")
                logger.warning("Falling back to FastAPI BackgroundTasks")

        # Fallback to FastAPI BackgroundTasks
        if background_tasks is not None:
            logger.info(f"Using FastAPI BackgroundTasks for job {job_id} (Redis unavailable)")
            background_tasks.add_task(
                BackgroundService._execute_backtest_sync,
                job_id=job_id,
                user_id=user_id,
                job_data=job_data
            )
            return job_id
        else:
            # If no background_tasks provided, execute synchronously and update job status
            logger.warning(f"No background_tasks provided for job {job_id}, executing synchronously")
            await BackgroundService._execute_backtest_sync(
                job_id=job_id,
                user_id=user_id,
                job_data=job_data
            )
            return job_id

    @staticmethod
    async def _execute_backtest_sync(
        job_id: str,
        user_id: str,
        job_data: Dict[str, Any]
    ):
        """
        Execute backtest synchronously in the background.
        This method will be called by FastAPI BackgroundTasks when Redis is unavailable.
        """
        cost = 0
        debit_txn_id = None
        
        try:
            logger.info(f"Executing backtest job {job_id} synchronously (Redis unavailable)")
            
            # Update job status to running
            await BackgroundService._update_job_status(
                job_id=job_id,
                status="running",
                progress=10,
                message="Initializing backtest..."
            )

            # Run the backtest using the existing service
            async with get_db_session() as db:
                from ..services.backtest_service import BacktestService
                from ..services.metrics import MetricsCalculator
                import pandas as pd
                from datetime import date

                # Convert date strings back to date objects
                start_date = date.fromisoformat(job_data["start_date"])
                end_date = date.fromisoformat(job_data["end_date"])

                # Step 0: CHECK_CREDITS (10%)
                await BackgroundService._update_job_status(
                    job_id=job_id,
                    status="running",
                    progress=10,
                    message="Checking credits..."
                )

                # Check credits and debit them
                cost = await BacktestService.check_credits_and_debit(
                    db=db,
                    user_id=user_id,
                    start_date=start_date,
                    end_date=end_date,
                    timeframe=job_data["timeframe"],
                    job_id=job_id
                )

                # Get the debit transaction ID for job tracking
                debit_txn = await CreditManagementService.get_transaction_history(
                    db=db,
                    user_id=user_id,
                    limit=1
                )
                if debit_txn:
                    debit_txn_id = debit_txn[0].id

                # Update job with debit transaction ID
                await BackgroundService._update_job_debit_txn(db, job_id, debit_txn_id)

                # Step 1: FETCH_DATA (20%)
                await BackgroundService._update_job_status(
                    job_id=job_id,
                    status="running",
                    progress=20,
                    message="Fetching market data..."
                )

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

                # Step 2: GENERATE_SIGNALS (50%)
                await BackgroundService._update_job_status(
                    job_id=job_id,
                    status="running",
                    progress=50,
                    message="Generating trading signals..."
                )

                # Step 3: BUILD_TRADES (70%)
                await BackgroundService._update_job_status(
                    job_id=job_id,
                    status="running",
                    progress=70,
                    message="Building trade history..."
                )

                # Calculate metrics
                equity_df = BackgroundService._create_equity_dataframe(service_response.result.equity_curve)
                trades_df = BackgroundService._create_trades_dataframe(service_response.result.trades)

                metrics = MetricsCalculator.calculate_all_metrics(
                    equity_curve=equity_df,
                    trades=trades_df,
                    initial_capital=job_data["capital"]
                )

                # Step 4: METRICS (90%)
                await BackgroundService._update_job_status(
                    job_id=job_id,
                    status="running",
                    progress=90,
                    message="Calculating performance metrics..."
                )

                # Save results to database
                backtest_id = await BackgroundService._save_backtest_results(
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

                # Step 5: SAVE (100%)
                await BackgroundService._update_job_status(
                    job_id=job_id,
                    status="completed",
                    progress=100,
                    message="Backtest completed successfully",
                    result_data=result_data
                )

        except Exception as e:
            logger.error(f"Backtest job {job_id} failed: {e}")
            
            # Refund credits on failure
            if cost > 0 and user_id:
                try:
                    async with get_db_session() as db:
                        await BacktestService.refund_credits_on_failure(
                            db=db,
                            user_id=user_id,
                            cost=cost,
                            job_id=job_id
                        )
                    logger.info(f"Refunded {cost} credits for failed job {job_id}")
                except Exception as refund_error:
                    logger.error(f"Failed to refund credits for job {job_id}: {refund_error}")
            
            await BackgroundService._update_job_status(
                job_id=job_id,
                status="failed",
                progress=0,
                message=f"Job failed: {str(e)}"
            )
            raise

    @staticmethod
    async def _update_job_debit_txn(db, job_id: str, debit_txn_id: str):
        """Update job with debit transaction ID."""
        from ..db.models import JobStatus
        from sqlalchemy import update
        from datetime import datetime

        await db.execute(
            update(JobStatus)
            .where(JobStatus.id == job_id)
            .values(debit_txn_id=debit_txn_id, updated_at=datetime.utcnow())
        )
        await db.commit()

    @staticmethod
    async def _update_job_status(
        job_id: str,
        status: str,
        progress: int,
        message: str,
        result_data: Optional[Dict] = None
    ):
        """Update job status in database."""
        async with get_db_session() as db:
            from ..db.models import JobStatus
            from sqlalchemy import update
            from datetime import datetime
            import json

            update_data = {
                "status": status,
                "progress": progress,
                "message": message,
                "updated_at": datetime.utcnow()
            }

            if status == "running" and not await BackgroundService._get_job_started_at(job_id):
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
    async def _get_job_started_at(job_id: str):
        """Check if job has been started."""
        async with get_db_session() as db:
            from ..db.models import JobStatus
            from sqlalchemy import select

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
        db,
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
            raise e