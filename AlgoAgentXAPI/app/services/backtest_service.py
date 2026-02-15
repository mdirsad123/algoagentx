from datetime import date, datetime
from decimal import Decimal
from typing import Optional, Dict, Any, Tuple
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, update
from uuid import uuid4
from ..db.models import MarketData, Strategy, Instrument, PerformanceMetric, Trade, EquityCurve, PnLCalendar, JobStatus, CreditTransaction
from engine.backtest_engine import run_backtest_engine, BacktestParams, BacktestResult
from ..core.config import settings
from ..services.credits.calculation import CreditCalculationService
from ..services.credits.management import CreditManagementService
from ..schemas.credits import InsufficientCreditsError


class BacktestError(Exception):
    """Base exception for backtest errors"""
    pass


class MarketDataNotFoundError(BacktestError):
    """Raised when no market data is found"""
    pass


class InvalidDateRangeError(BacktestError):
    """Raised when date range is invalid"""
    pass


class StrategyNotFoundError(BacktestError):
    """Raised when strategy is not found"""
    pass


class BacktestServiceResponse:
    """Structured response object for backtest service"""
    def __init__(
        self,
        result: BacktestResult,
        strategy_name: str,
        instrument_symbol: str,
        timeframe: str,
        start_date: date,
        end_date: date,
        initial_capital: Decimal
    ):
        self.result = result
        self.strategy_name = strategy_name
        self.instrument_symbol = instrument_symbol
        self.timeframe = timeframe
        self.start_date = start_date
        self.end_date = end_date
        self.initial_capital = initial_capital
        self.final_capital = Decimal(str(result.final_capital))
        self.net_profit = self.final_capital - initial_capital
        self.max_drawdown = Decimal(str(result.max_drawdown))
        self.sharpe_ratio = Decimal(str(result.sharpe_ratio))
        self.win_rate = Decimal(str(result.win_rate))
        self.total_trades = result.total_trades


class BacktestService:
    @staticmethod
    async def run_backtest(
        db: AsyncSession,
        strategy_id: str,
        instrument_id: int,
        timeframe: str,
        start_date: date,
        end_date: date,
        initial_capital: Decimal = Decimal("100000")
    ) -> BacktestServiceResponse:
        """
        Pure backtest service layer.

        Fetches market data, converts to pandas, runs engine, returns structured result.

        Args:
            db: Database session
            strategy_id: Strategy identifier
            instrument_id: Instrument identifier
            timeframe: Timeframe (e.g., '1d', '1h')
            start_date: Backtest start date
            end_date: Backtest end date
            initial_capital: Starting capital

        Returns:
            BacktestServiceResponse with results

        Raises:
            InvalidDateRangeError: If start_date >= end_date
            MarketDataNotFoundError: If no market data found
            StrategyNotFoundError: If strategy not found
        """
        # Validate date range
        if start_date >= end_date:
            raise InvalidDateRangeError(f"Start date {start_date} must be before end date {end_date}")

        # Fetch market data
        market_data_df = await BacktestService._fetch_market_data(
            db, instrument_id, timeframe, start_date, end_date
        )

        if market_data_df.empty:
            raise MarketDataNotFoundError(
                f"No market data found for instrument {instrument_id}, timeframe {timeframe}, "
                f"period {start_date} to {end_date}"
            )

        # Get strategy details
        strategy_class, strategy_params, strategy_name = await BacktestService._get_strategy_details(db, strategy_id)

        # Get instrument symbol
        instrument_symbol = await BacktestService._get_instrument_symbol(db, instrument_id)

        # Prepare backtest parameters
        backtest_params = BacktestParams(
            initial_capital=float(initial_capital),
            # Configure based on timeframe/market if needed
        )

        # Run the backtest engine
        result = run_backtest_engine(
            market_data=market_data_df,
            strategy_class=strategy_class,
            strategy_params=strategy_params,
            backtest_params=backtest_params
        )

        # Return structured response
        return BacktestServiceResponse(
            result=result,
            strategy_name=strategy_name,
            instrument_symbol=instrument_symbol,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital
        )

    @staticmethod
    async def _fetch_market_data(
        db: AsyncSession,
        instrument_id: int,
        timeframe: str,
        start_date: date,
        end_date: date
    ) -> pd.DataFrame:
        """
        Fetch market data from database and convert to pandas DataFrame.

        Handles timezone conversion assuming database timestamps are in UTC.
        """
        query = select(MarketData).where(
            MarketData.instrument_id == instrument_id,
            MarketData.timeframe == timeframe,
            MarketData.timestamp >= start_date,
            MarketData.timestamp <= end_date
        ).order_by(MarketData.timestamp)

        result = await db.execute(query)
        rows = result.fetchall()

        if not rows:
            return pd.DataFrame()

        data = []
        for row in rows:
            # Convert timestamp to naive datetime (pandas expects naive)
            # Assuming database timestamps are UTC
            timestamp = row.timestamp.replace(tzinfo=None) if row.timestamp.tzinfo else row.timestamp

            data.append({
                "Date": timestamp,
                "Open": float(row.open),
                "High": float(row.high),
                "Low": float(row.low),
                "Close": float(row.close),
                "Volume": float(row.volume or 0)
            })

        df = pd.DataFrame(data)
        # Ensure Date is datetime
        df["Date"] = pd.to_datetime(df["Date"])

        return df

    @staticmethod
    async def _get_strategy_details(db: AsyncSession, strategy_id: str) -> Tuple[Any, Dict[str, Any], str]:
        """Get strategy class, parameters, and name"""
        result = await db.execute(select(Strategy).where(Strategy.id == strategy_id))
        strategy = result.scalar_one_or_none()

        if not strategy:
            raise StrategyNotFoundError(f"Strategy with id {strategy_id} not found")

        # Map strategy name to class
        strategy_class = BacktestService._get_strategy_class_by_name(strategy.name)
        strategy_params = strategy.parameters or {}
        strategy_name = strategy.name

        return strategy_class, strategy_params, strategy_name

    @staticmethod
    def _get_strategy_class_by_name(name: str) -> Any:
        """Map strategy name to class"""
        strategy_map = {
            "EMA Crossover": "strategies.ema_crossover.EMACrossover",
            # Add more strategies here as needed
        }

        if name not in strategy_map:
            raise StrategyNotFoundError(f"Strategy '{name}' not found in strategy map")

        # Dynamic import
        module_name, class_name = strategy_map[name].rsplit(".", 1)
        module = __import__(module_name, fromlist=[class_name])
        return getattr(module, class_name)

    @staticmethod
    async def _get_instrument_symbol(db: AsyncSession, instrument_id: int) -> str:
        """Get instrument symbol by ID"""
        result = await db.execute(select(Instrument.symbol).where(Instrument.id == instrument_id))
        instrument = result.scalar_one_or_none()
        return instrument or f"Instrument_{instrument_id}"

    @staticmethod
    async def get_instrument_id_by_symbol(db: AsyncSession, symbol: str) -> Optional[int]:
        """Get instrument ID by symbol"""
        result = await db.execute(select(Instrument.id).where(Instrument.symbol == symbol))
        return result.scalar_one_or_none()

    @staticmethod
    async def check_credits_and_debit(
        db: AsyncSession,
        user_id: str,
        start_date: date,
        end_date: date,
        timeframe: str,
        job_id: Optional[str] = None
    ) -> int:
        """
        Check if user has sufficient credits and debit them for backtest.
        
        Args:
            db: Database session
            user_id: User ID
            start_date: Backtest start date
            end_date: Backtest end date
            timeframe: Timeframe string
            job_id: Optional job ID for tracking
            
        Returns:
            Cost that was debited
            
        Raises:
            ValueError: If insufficient credits
        """
        # Calculate cost
        cost = CreditCalculationService.calculate_backtest_cost(start_date, end_date, timeframe)
        
        # Get current balance
        current_balance = await CreditManagementService.get_user_balance(db, user_id)
        
        if current_balance < cost:
            raise ValueError(f"Insufficient credits. Current balance: {current_balance}, Required: {cost}")
        
        # Debit credits
        await CreditManagementService.debit_credits(
            db=db,
            user_id=user_id,
            amount=cost,
            description=f"Backtest cost for {timeframe} timeframe, {start_date} to {end_date}",
            job_id=job_id
        )
        
        return cost

    @staticmethod
    async def check_subscription_and_credits(
        db: AsyncSession,
        user_id: str,
        start_date: date,
        end_date: date,
        timeframe: str,
        job_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Check subscription status and enforce credit policy.
        
        Policy:
        - Subscription users: Use included credits first, then require additional credits if exceeded
        - Credit-only users: Always require credits
        - Free trial users: Limited runs, no credit deduction during trial period
        
        Args:
            db: Database session
            user_id: User ID
            start_date: Backtest start date
            end_date: Backtest end date
            timeframe: Timeframe string
            job_id: Optional job ID for tracking
            
        Returns:
            Dict with policy result and cost information
            
        Raises:
            ValueError: If policy violations or insufficient credits
        """
        from ..core.dependencies import get_user_entitlements
        from ..billing.plan_catalog import PlanCode
        
        # Get user entitlements
        entitlements = await get_user_entitlements({"user_id": user_id}, db)
        
        # Calculate cost
        cost = CreditCalculationService.calculate_backtest_cost(start_date, end_date, timeframe)
        current_balance = await CreditManagementService.get_user_balance(db, user_id)
        
        plan_code = entitlements["plan_code"]
        subscription_status = entitlements["subscription_status"]
        included_credits = entitlements["included_credits"]
        is_trial = entitlements["is_trial"]
        
        # Policy implementation
        if is_trial:
            # Free trial: limited runs, no credit deduction
            trial_runs_used = await CreditManagementService.get_trial_backtest_count(db, user_id)
            max_trial_runs = 5  # Allow 5 free trial runs
            
            if trial_runs_used >= max_trial_runs:
                raise ValueError(f"Free trial limit exceeded. Maximum {max_trial_runs} backtest runs allowed.")
            
            return {
                "policy": "trial",
                "cost": 0,
                "deducted": 0,
                "remaining_included": included_credits,
                "remaining_balance": current_balance,
                "message": f"Free trial run (remaining: {max_trial_runs - trial_runs_used - 1})"
            }
        
        elif plan_code != PlanCode.FREE and subscription_status == "ACTIVE":
            # Subscription user: use included credits first
            if included_credits > 0:
                # Use included credits
                if included_credits >= cost:
                    # Included credits cover the cost
                    await CreditManagementService.update_included_credits(
                        db, user_id, -cost
                    )
                    return {
                        "policy": "subscription_included",
                        "cost": cost,
                        "deducted": 0,
                        "remaining_included": included_credits - cost,
                        "remaining_balance": current_balance,
                        "message": f"Used included credits (remaining: {included_credits - cost})"
                    }
                else:
                    # Partially use included credits, rest from balance
                    remaining_cost = cost - included_credits
                    if current_balance < remaining_cost:
                        raise ValueError(f"Insufficient credits. Included credits: {included_credits}, Balance: {current_balance}, Required: {remaining_cost}")
                    
                    # Deduct from included credits and balance
                    await CreditManagementService.update_included_credits(db, user_id, -included_credits)
                    await CreditManagementService.debit_credits(
                        db=db,
                        user_id=user_id,
                        amount=remaining_cost,
                        description=f"Backtest cost (partial from balance) for {timeframe} timeframe, {start_date} to {end_date}",
                        job_id=job_id
                    )
                    
                    return {
                        "policy": "subscription_mixed",
                        "cost": cost,
                        "deducted": remaining_cost,
                        "remaining_included": 0,
                        "remaining_balance": current_balance - remaining_cost,
                        "message": f"Used {included_credits} included credits + {remaining_cost} from balance"
                    }
            else:
                # No included credits, use balance
                if current_balance < cost:
                    raise ValueError(f"Insufficient credits. Balance: {current_balance}, Required: {cost}")
                
                await CreditManagementService.debit_credits(
                    db=db,
                    user_id=user_id,
                    amount=cost,
                    description=f"Backtest cost for {timeframe} timeframe, {start_date} to {end_date}",
                    job_id=job_id
                )
                
                return {
                    "policy": "subscription_balance",
                    "cost": cost,
                    "deducted": cost,
                    "remaining_included": 0,
                    "remaining_balance": current_balance - cost,
                    "message": f"Used {cost} credits from balance"
                }
        
        else:
            # Credit-only user: always require credits
            if current_balance < cost:
                raise ValueError(f"Insufficient credits. Balance: {current_balance}, Required: {cost}")
            
            await CreditManagementService.debit_credits(
                db=db,
                user_id=user_id,
                amount=cost,
                description=f"Backtest cost for {timeframe} timeframe, {start_date} to {end_date}",
                job_id=job_id
            )
            
            return {
                "policy": "credit_only",
                "cost": cost,
                "deducted": cost,
                "remaining_included": 0,
                "remaining_balance": current_balance - cost,
                "message": f"Used {cost} credits from balance"
            }

    @staticmethod
    async def refund_credits_on_failure(
        db: AsyncSession,
        user_id: str,
        cost: int,
        job_id: Optional[str] = None
    ) -> None:
        """
        Refund credits when backtest fails.
        
        Args:
            db: Database session
            user_id: User ID
            cost: Amount to refund
            job_id: Optional job ID for tracking
        """
        await CreditManagementService.refund_credits(
            db=db,
            user_id=user_id,
            amount=cost,
            description=f"Refund for failed backtest job {job_id}",
            job_id=job_id
        )

    @staticmethod
    async def get_or_create_backtest(
        db: AsyncSession,
        user_id: str,
        strategy_id: str,
        instrument_id: int,
        timeframe: str,
        start_date: date,
        end_date: date,
        initial_capital: Decimal
    ) -> BacktestServiceResponse:
        """
        DB-first backtest service: return existing result or run engine and persist.

        Args:
            db: Database session
            user_id: User ID
            strategy_id: Strategy identifier
            instrument_id: Instrument identifier
            timeframe: Timeframe
            start_date: Backtest start date
            end_date: Backtest end date
            initial_capital: Starting capital

        Returns:
            BacktestServiceResponse with results

        Raises:
            InvalidDateRangeError: If start_date >= end_date
            MarketDataNotFoundError: If no market data found
            StrategyNotFoundError: If strategy not found
        """
        # Check if backtest already exists with exact parameters
        existing_backtest = await BacktestService._find_existing_backtest(
            db, user_id, strategy_id, instrument_id, timeframe, start_date, end_date, initial_capital
        )

        if existing_backtest:
            # Return stored result
            return await BacktestService._build_response_from_db(db, existing_backtest)

        # No existing backtest found, run engine and persist results
        service_response = await BacktestService.run_backtest(
            db=db,
            strategy_id=strategy_id,
            instrument_id=instrument_id,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital
        )

        # Persist results to database
        await BacktestService._persist_backtest_results(
            db=db,
            user_id=user_id,
            strategy_id=strategy_id,
            instrument_id=instrument_id,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital,
            service_response=service_response
        )

        return service_response

    @staticmethod
    async def _find_existing_backtest(
        db: AsyncSession,
        user_id: str,
        strategy_id: str,
        instrument_id: int,
        timeframe: str,
        start_date: date,
        end_date: date,
        initial_capital: Decimal
    ) -> Optional[PerformanceMetric]:
        """Find existing backtest with exact parameters"""
        result = await db.execute(
            select(PerformanceMetric).where(
                PerformanceMetric.user_id == user_id,
                PerformanceMetric.strategy_id == strategy_id,
                PerformanceMetric.instrument_id == instrument_id,
                PerformanceMetric.timeframe == timeframe,
                PerformanceMetric.start_date == start_date,
                PerformanceMetric.end_date == end_date,
                PerformanceMetric.initial_capital == initial_capital,
                PerformanceMetric.status == "completed"
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def _build_response_from_db(
        db: AsyncSession,
        backtest: PerformanceMetric
    ) -> BacktestServiceResponse:
        """Build response from existing database record"""
        # Get strategy name
        strategy_result = await db.execute(
            select(Strategy.name).where(Strategy.id == backtest.strategy_id)
        )
        strategy_name = strategy_result.scalar_one_or_none() or "Unknown"

        # Get instrument symbol
        instrument_result = await db.execute(
            select(Instrument.symbol).where(Instrument.id == backtest.instrument_id)
        )
        instrument_symbol = instrument_result.scalar_one_or_none() or "Unknown"

        # Create a mock BacktestResult for the response
        from engine.backtest_engine import BacktestResult
        mock_result = BacktestResult(
            final_capital=float(backtest.final_capital) if backtest.final_capital else 0.0,
            trades=[],  # Would need to fetch from trades table if needed
            equity_curve=[]  # Would need to fetch from equity_curve table if needed
        )

        return BacktestServiceResponse(
            result=mock_result,
            strategy_name=strategy_name,
            instrument_symbol=instrument_symbol,
            timeframe=backtest.timeframe,
            start_date=backtest.start_date,
            end_date=backtest.end_date,
            initial_capital=backtest.initial_capital
        )

    @staticmethod
    async def _persist_backtest_results(
        db: AsyncSession,
        user_id: str,
        strategy_id: str,
        instrument_id: int,
        timeframe: str,
        start_date: date,
        end_date: date,
        initial_capital: Decimal,
        service_response: BacktestServiceResponse
    ):
        """Persist backtest results to database"""
        from datetime import timedelta

        backtest_id = str(uuid4())

        # Save performance metrics
        await db.execute(
            insert(PerformanceMetric).values(
                id=backtest_id,
                user_id=user_id,
                strategy_id=strategy_id,
                instrument_id=instrument_id,
                timeframe=timeframe,
                start_date=start_date,
                end_date=end_date,
                initial_capital=initial_capital,
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
                    "instrument_id": instrument_id,
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
            base_date = start_date
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
