from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from ..db.models import (
    User, Strategy, PerformanceMetric, Trade, EquityCurve, PnLCalendar, metrics, Instrument
)
from ..schemas import (
    User as UserSchema,
    Strategy as StrategySchema,
    PerformanceMetric as PerformanceMetricSchema,
    Metric as MetricSchema,
    Instrument as InstrumentSchema
)


class ReadOnlyService:
    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id: str) -> Optional[UserSchema]:
        """Get user by ID"""
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        return UserSchema.from_orm(user) if user else None

    @staticmethod
    async def get_strategies_by_user(db: AsyncSession, user_id: str) -> List[StrategySchema]:
        """Get all strategies created by a user"""
        result = await db.execute(select(Strategy).where(Strategy.created_by == user_id))
        strategies = result.scalars().all()
        return [StrategySchema.from_orm(strategy) for strategy in strategies]

    @staticmethod
    async def get_all_strategies(db: AsyncSession) -> List[StrategySchema]:
        """Get all strategies"""
        result = await db.execute(select(Strategy))
        strategies = result.scalars().all()
        return [StrategySchema.from_orm(strategy) for strategy in strategies]

    @staticmethod
    async def get_all_instruments(db: AsyncSession) -> List[InstrumentSchema]:
        """Get all instruments"""
        result = await db.execute(select(Instrument))
        instruments = result.scalars().all()
        return [InstrumentSchema.from_orm(instrument) for instrument in instruments]

    @staticmethod
    async def get_backtests_by_user(db: AsyncSession, user_id: str) -> List[PerformanceMetricSchema]:
        """Get all backtests for a user"""
        result = await db.execute(select(PerformanceMetric).where(PerformanceMetric.user_id == user_id))
        backtests = result.scalars().all()
        return [PerformanceMetricSchema.from_orm(backtest) for backtest in backtests]

    @staticmethod
    async def get_backtest_by_id(db: AsyncSession, backtest_id: str) -> Optional[PerformanceMetricSchema]:
        """Get backtest by ID"""
        result = await db.execute(select(PerformanceMetric).where(PerformanceMetric.id == backtest_id))
        backtest = result.scalar_one_or_none()
        return PerformanceMetricSchema.from_orm(backtest) if backtest else None

    @staticmethod
    async def get_trades_by_backtest(db: AsyncSession, backtest_id: str) -> List[dict]:
        """Get all trades for a backtest"""
        result = await db.execute(select(Trade).where(Trade.backtest_id == backtest_id))
        trades = result.scalars().all()
        return [trade.__dict__ for trade in trades]

    @staticmethod
    async def get_equity_curve_by_backtest(db: AsyncSession, backtest_id: str) -> List[dict]:
        """Get equity curve for a backtest"""
        result = await db.execute(
            select(EquityCurve).where(EquityCurve.backtest_id == backtest_id)
            .order_by(EquityCurve.timestamp)
        )
        curves = result.scalars().all()
        return [curve.__dict__ for curve in curves]

    @staticmethod
    async def get_pnl_calendar_by_backtest(db: AsyncSession, backtest_id: str) -> List[dict]:
        """Get PnL calendar for a backtest"""
        result = await db.execute(
            select(PnLCalendar).where(PnLCalendar.backtest_id == backtest_id)
            .order_by(PnLCalendar.date)
        )
        pnls = result.scalars().all()
        return [pnl.__dict__ for pnl in pnls]

    @staticmethod
    async def get_metrics_by_backtest(db: AsyncSession, backtest_id: str) -> List[MetricSchema]:
        """Get metrics for a backtest"""
        result = await db.execute(select(metrics).where(metrics.backtest_id == backtest_id))
        metrics = result.scalars().all()
        return [MetricSchema.from_orm(metric) for metric in metrics]
