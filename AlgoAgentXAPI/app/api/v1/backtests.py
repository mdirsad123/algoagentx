
from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert
from typing import List, Optional
from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4
from ...core.dependencies import get_current_user, get_db, check_backtest_limits
from ...services.read_only import ReadOnlyService
from ...services.backtest_service import (
    BacktestService,
    BacktestServiceResponse,
    BacktestError,
    MarketDataNotFoundError,
    InvalidDateRangeError,
    StrategyNotFoundError
)
from ...services.credits.calculation import CreditCalculationService
from ...services.credits.management import CreditManagementService
from ...schemas import BacktestRunRequest, BacktestRunResponse, TradeData, EquityPoint, PerformanceMetric as PerformanceMetricSchema
from ...schemas.credits import InsufficientCreditsError
from ...db.models import Strategy, Instrument, Trade, EquityCurve, PnLCalendar, PerformanceMetric as PerformanceMetricModel
from ...schemas.backtests import PerformanceMetric as PerformanceMetricOut

router = APIRouter()

@router.get("/", response_model=List[PerformanceMetricOut])
async def get_my_backtests(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get backtests for current user
    """
    return await ReadOnlyService.get_backtests_by_user(db, current_user["user_id"])

@router.get("/run", response_model=PerformanceMetricOut)
async def run_backtest(
    strategy_id: str = Query(..., description="Strategy ID"),
    instrument: str = Query(..., description="Instrument symbol"),
    timeframe: str = Query(..., description="Timeframe (e.g., 5m, 15m, 1h, 1d)"),
    start_date: date = Query(..., description="Start date"),
    end_date: date = Query(..., description="End date"),
    initial_capital: Decimal = Query(Decimal("100000"), description="Initial capital"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    limits: dict = Depends(check_backtest_limits)
):
    """
    Run backtest or return existing result.

    DB-first logic: If backtest exists with exact parameters, return stored result.
    Otherwise, execute engine and persist results.
    
    Enforces plan limits:
    - Daily backtest count
    - Maximum date range allowed by plan
    - Credit policy enforcement (subscription vs credit-only)
    """
    # Check date range limit
    date_range_days = (end_date - start_date).days
    if date_range_days > limits["max_date_range_days"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Date range exceeds plan limit. Maximum allowed: {limits['max_date_range_days']} days, requested: {date_range_days} days"
        )

    # Check if strategy exists
    result = await db.execute(select(Strategy).where(Strategy.id == strategy_id))
    strategy = result.scalar_one_or_none()
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    # Map instrument symbol to instrument_id
    instrument_id = await BacktestService.get_instrument_id_by_symbol(db, instrument)
    if not instrument_id:
        raise HTTPException(status_code=404, detail=f"Instrument '{instrument}' not found")

    # Enforce credit policy
    try:
        credit_policy = await BacktestService.check_subscription_and_credits(
            db=db,
            user_id=current_user["user_id"],
            start_date=start_date,
            end_date=end_date,
            timeframe=timeframe
        )
        
        # Log the credit policy decision
        print(f"Credit policy applied: {credit_policy}")
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=str(e)
        )

    return await BacktestService.get_or_create_backtest(
        db=db,
        user_id=current_user["user_id"],
        strategy_id=strategy_id,
        instrument_id=instrument_id,
        timeframe=timeframe,
        start_date=start_date,
        end_date=end_date,
        initial_capital=initial_capital
    )

@router.get("/history")
async def get_backtest_history(
    strategy_id: Optional[str] = Query(None, description="Filter by strategy ID"),
    instrument_id: Optional[int] = Query(None, description="Filter by instrument ID"),
    timeframe: Optional[str] = Query(None, description="Filter by timeframe"),
    start_date_from: Optional[date] = Query(None, description="Filter by start date from"),
    start_date_to: Optional[date] = Query(None, description="Filter by start date to"),
    min_profit: Optional[float] = Query(None, description="Filter by minimum net profit"),
    max_drawdown: Optional[float] = Query(None, description="Filter by maximum drawdown"),
    sort_by: str = Query("created_at", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order (asc/desc)"),
    page: int = Query(1, description="Page number", ge=1),
    page_size: int = Query(20, description="Items per page", ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get backtest history with filtering and pagination.

    Returns past backtests with their metrics.
    """
    from sqlalchemy import and_, or_, desc, asc

    # Build base query
    query = select(PerformanceMetricModel).where(PerformanceMetricModel.user_id == current_user["user_id"])

    # Apply filters
    filters = []
    if strategy_id:
        filters.append(PerformanceMetricModel.strategy_id == strategy_id)
    if instrument_id:
        filters.append(PerformanceMetricModel.instrument_id == instrument_id)
    if timeframe:
        filters.append(PerformanceMetricModel.timeframe == timeframe)
    if start_date_from:
        filters.append(PerformanceMetricModel.start_date >= start_date_from)
    if start_date_to:
        filters.append(PerformanceMetricModel.start_date <= start_date_to)
    if min_profit is not None:
        filters.append(PerformanceMetricModel.net_profit >= min_profit)
    if max_drawdown is not None:
        filters.append(PerformanceMetricModel.max_drawdown <= max_drawdown)

    if filters:
        query = query.where(and_(*filters))

    # Apply sorting
    sort_column = getattr(PerformanceMetricModel, sort_by, PerformanceMetricModel.created_at)
    if sort_order.lower() == "asc":
        query = query.order_by(asc(sort_column))
    else:
        query = query.order_by(desc(sort_column))

    # Get total count
    count_query = query.with_only_columns([PerformanceMetricModel.id])
    total_result = await db.execute(count_query)
    total_count = len(total_result.fetchall())

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    # Execute query
    result = await db.execute(query)
    backtests = result.scalars().all()

    # Get strategy and instrument names
    strategy_ids = list(set(b.strategy_id for b in backtests))
    instrument_ids = list(set(b.instrument_id for b in backtests))

    strategies = {}
    if strategy_ids:
        strategy_result = await db.execute(select(Strategy).where(Strategy.id.in_(strategy_ids)))
        strategies = {s.id: s.name for s in strategy_result.scalars().all()}

    instruments = {}
    if instrument_ids:
        instrument_result = await db.execute(select(Instrument).where(Instrument.id.in_(instrument_ids)))
        instruments = {i.id: i.symbol for i in instrument_result.scalars().all()}

    # Format response
    backtest_list = []
    for backtest in backtests:
        backtest_list.append({
            "id": backtest.id,
            "strategy_id": backtest.strategy_id,
            "strategy_name": strategies.get(backtest.strategy_id, "Unknown"),
            "instrument_id": backtest.instrument_id,
            "instrument_symbol": instruments.get(backtest.instrument_id, "Unknown"),
            "timeframe": backtest.timeframe,
            "start_date": backtest.start_date.isoformat(),
            "end_date": backtest.end_date.isoformat(),
            "initial_capital": float(backtest.initial_capital),
            "final_capital": float(backtest.final_capital) if backtest.final_capital else None,
            "net_profit": float(backtest.net_profit) if backtest.net_profit else None,
            "max_drawdown": float(backtest.max_drawdown) if backtest.max_drawdown else None,
            "sharpe_ratio": float(backtest.sharpe_ratio) if backtest.sharpe_ratio else None,
            "win_rate": float(backtest.win_rate) if backtest.win_rate else None,
            "total_trades": backtest.total_trades,
            "winning_trades": backtest.winning_trades,
            "losing_trades": backtest.losing_trades,
            "status": backtest.status,
            "created_at": backtest.created_at.isoformat() if backtest.created_at else None,
            "updated_at": backtest.updated_at.isoformat() if backtest.updated_at else None,
        })

    return {
        "backtests": backtest_list,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_count": total_count,
            "total_pages": (total_count + page_size - 1) // page_size
        },
        "filters_applied": {
            "strategy_id": strategy_id,
            "instrument_id": instrument_id,
            "timeframe": timeframe,
            "start_date_from": start_date_from.isoformat() if start_date_from else None,
            "start_date_to": start_date_to.isoformat() if start_date_to else None,
            "min_profit": min_profit,
            "max_drawdown": max_drawdown
        }
    }

@router.get("/{backtest_id}", response_model=PerformanceMetricOut)
async def get_backtest_by_id(
    backtest_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get backtest by ID
    """
    backtest = await ReadOnlyService.get_backtest_by_id(db, backtest_id)
    if not backtest:
        raise HTTPException(status_code=404, detail="Backtest not found")
    # Check if user owns this backtest
    if str(backtest.user_id) != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    return backtest

@router.get("/{backtest_id}/trades")
async def get_backtest_trades(
    backtest_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get trades for a backtest
    """
    # First verify ownership
    backtest = await ReadOnlyService.get_backtest_by_id(db, backtest_id)
    if not backtest or str(backtest.user_id) != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    return await ReadOnlyService.get_trades_by_backtest(db, backtest_id)

@router.get("/{backtest_id}/equity-curve")
async def get_backtest_equity_curve(
    backtest_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get equity curve for a backtest
    """
    # First verify ownership
    backtest = await ReadOnlyService.get_backtest_by_id(db, backtest_id)
    if not backtest or str(backtest.user_id) != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    return await ReadOnlyService.get_equity_curve_by_backtest(db, backtest_id)

@router.get("/{backtest_id}/pnl-calendar")
async def get_backtest_pnl_calendar(
    backtest_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get PnL calendar for a backtest
    """
    # First verify ownership
    backtest = await ReadOnlyService.get_backtest_by_id(db, backtest_id)
    if not backtest or str(backtest.user_id) != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    return await ReadOnlyService.get_pnl_calendar_by_backtest(db, backtest_id)


@router.post("/run", response_model=dict, status_code=status.HTTP_202_ACCEPTED)
async def run_backtest_post(
    request: BacktestRunRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Submit backtest job for background execution.

    Returns job_id immediately. Use /jobs/{job_id} to poll status.
    Falls back to FastAPI BackgroundTasks if Redis/Celery is unavailable.
    """
    from ...services.background_service import BackgroundService
    from ...core.redis_manager import redis_manager
    import logging

    logger = logging.getLogger(__name__)

    try:
        # Log raw incoming payload
        logger.info(f"Backtest request received - User: {current_user['user_id']}, Strategy: {request.strategy_id}, Instrument: {request.instrument_id}")
        logger.debug(f"Raw request payload: strategy_id={request.strategy_id}, instrument_id={request.instrument_id}, timeframe={request.timeframe}, start_date={request.start_date}, end_date={request.end_date}, capital={request.capital}")

        # Validate date range
        if request.start_date >= request.end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Start date must be before end date"
            )

        # Additional validation: ensure dates are not in the future
        from datetime import date
        today = date.today()
        if request.start_date > today or request.end_date > today:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Backtest dates cannot be in the future"
            )

        logger.debug(f"Converted payload: start_date={request.start_date.isoformat()}, end_date={request.end_date.isoformat()}")

        # Check credits and debit before submitting job
        try:
            # Compute cost and debit credits atomically
            debit_transaction = await CreditManagementService.check_and_debit_backtest_credits(
                db=db,
                user_id=current_user["user_id"],
                start_date=request.start_date,
                end_date=request.end_date,
                timeframe=request.timeframe
            )
            
            logger.info(f"Debited {debit_transaction.amount} credits for backtest job {debit_transaction.id}")
            
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=InsufficientCreditsError(
                    needed=float(debit_transaction.amount) if 'debit_transaction' in locals() else 0,
                    balance=float(await CreditManagementService.get_user_balance(db, current_user["user_id"]))
                ).dict()
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )

        # Submit job with Redis/Celery fallback to FastAPI BackgroundTasks
        job_id = await BackgroundService.submit_backtest_job(
            user_id=current_user["user_id"],
            strategy_id=request.strategy_id,
            instrument_id=request.instrument_id,
            timeframe=request.timeframe,
            start_date=request.start_date.isoformat(),
            end_date=request.end_date.isoformat(),
            capital=float(request.capital),
            background_tasks=background_tasks,
            debit_transaction_id=str(debit_transaction.id)  # Pass debit transaction ID for potential refund
        )

        # Log the execution method used
        if redis_manager.is_available:
            execution_method = "Redis/Celery"
        else:
            execution_method = "FastAPI BackgroundTasks (Redis unavailable)"

        return {
            "job_id": job_id,
            "status": "accepted",
            "message": f"Backtest job submitted for processing using {execution_method}",
            "execution_method": execution_method,
            "poll_url": f"/api/v1/jobs/{job_id}",
            "debit_transaction_id": str(debit_transaction.id),
            "debited_amount": float(debit_transaction.amount),
            "remaining_balance": float(debit_transaction.balance_after)
        }

    except Exception as e:
        logger.error(f"Failed to submit backtest job: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit backtest job: {str(e)}"
        )


async def _save_backtest_results(
    db: AsyncSession,
    user_id: int,
    request: BacktestRunRequest,
    service_response: BacktestServiceResponse
):
    """
    Save backtest results to database.

    Returns the backtest_id.
    """
    from datetime import datetime, timedelta

    backtest_id = uuid4()

    # Save performance metrics
    await db.execute(
        insert(PerformanceMetricModel).values(
            id=backtest_id,
            user_id=user_id,
            strategy_id=request.strategy_id,
            instrument_id=request.instrument_id,
            timeframe=request.timeframe,
            start_date=request.start_date,
            end_date=request.end_date,
            initial_capital=request.capital,
            final_capital=service_response.final_capital,
            net_profit=service_response.net_profit,
            max_drawdown=service_response.max_drawdown,
            sharpe_ratio=service_response.sharpe_ratio,
            win_rate=service_response.win_rate,
            total_trades=service_response.total_trades,
            winning_trades=int(service_response.total_trades * float(service_response.win_rate)),
            losing_trades=int(service_response.total_trades * (1 - float(service_response.win_rate))),
            status="completed"
        )
    )

    # Save trades
    if service_response.result.trades:
        trade_values = [
            {
                "backtest_id": backtest_id,
                "instrument_id": request.instrument_id,
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
        base_date = datetime.combine(service_response.start_date, datetime.min.time())
        equity_values = [
            {
                "backtest_id": backtest_id,
                "timestamp": base_date + timedelta(days=i),
                "equity": equity
            }
            for i, equity in enumerate(service_response.result.equity_curve)
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
    return backtest_id
