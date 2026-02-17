from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from typing import List, Optional
from datetime import datetime
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

    # Admin-specific methods
    @staticmethod
    async def get_user_count(db: AsyncSession) -> int:
        """Get total user count"""
        result = await db.execute(select(func.count()).select_from(User))
        return result.scalar()

    @staticmethod
    async def get_active_user_count(db: AsyncSession) -> int:
        """Get active user count"""
        result = await db.execute(select(func.count()).select_from(User).where(User.is_active == True))
        return result.scalar()

    @staticmethod
    async def get_payment_count(db: AsyncSession) -> int:
        """Get total payment count"""
        result = await db.execute(text("SELECT COUNT(*) FROM payments"))
        return result.scalar()

    @staticmethod
    async def get_total_revenue(db: AsyncSession) -> float:
        """Get total revenue from successful payments"""
        result = await db.execute(text("SELECT COALESCE(SUM(amount), 0) FROM payments WHERE status = 'SUCCESS'"))
        return float(result.scalar() or 0)

    @staticmethod
    async def get_total_credits(db: AsyncSession) -> int:
        """Get total credits across all users"""
        result = await db.execute(text("SELECT COALESCE(SUM(credits), 0) FROM credit_transactions"))
        return result.scalar()

    @staticmethod
    async def get_active_subscription_count(db: AsyncSession) -> int:
        """Get active subscription count"""
        result = await db.execute(text("""
            SELECT COUNT(*) FROM user_subscriptions 
            WHERE status = 'ACTIVE' AND end_at > NOW()
        """))
        return result.scalar()

    @staticmethod
    async def get_recent_users(db: AsyncSession, limit: int = 5) -> List[UserSchema]:
        """Get recent users"""
        result = await db.execute(
            select(User).order_by(User.created_at.desc()).limit(limit)
        )
        users = result.scalars().all()
        return [UserSchema.from_orm(user) for user in users]

    @staticmethod
    async def get_recent_payments(db: AsyncSession, limit: int = 5) -> List[dict]:
        """Get recent payments"""
        result = await db.execute(text("""
            SELECT * FROM payments 
            ORDER BY created_at DESC 
            LIMIT :limit
        """), {"limit": limit})
        return [dict(row._mapping) for row in result.fetchall()]

    @staticmethod
    async def get_recent_screener_jobs(db: AsyncSession, limit: int = 5) -> List[dict]:
        """Get recent AI screener jobs"""
        result = await db.execute(text("""
            SELECT * FROM ai_screener_jobs 
            ORDER BY created_at DESC 
            LIMIT :limit
        """), {"limit": limit})
        return [dict(row._mapping) for row in result.fetchall()]

    @staticmethod
    async def get_users_paginated(db: AsyncSession, skip: int = 0, limit: int = 20, search: Optional[str] = None) -> List[UserSchema]:
        """Get users with pagination and search"""
        query = select(User)
        if search:
            query = query.where(User.email.ilike(f"%{search}%"))
        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        users = result.scalars().all()
        return [UserSchema.from_orm(user) for user in users]

    @staticmethod
    async def get_payments_paginated(db: AsyncSession, skip: int = 0, limit: int = 20, status: Optional[str] = None) -> List[dict]:
        """Get payments with pagination and filtering"""
        query = text("""
            SELECT * FROM payments 
        """)
        params = {}
        if status:
            query += text("WHERE status = :status ")
            params["status"] = status
        query += text("ORDER BY created_at DESC OFFSET :skip LIMIT :limit")
        params.update({"skip": skip, "limit": limit})
        
        result = await db.execute(query, params)
        return [dict(row._mapping) for row in result.fetchall()]

    @staticmethod
    async def get_subscriptions_paginated(db: AsyncSession, skip: int = 0, limit: int = 20, status: Optional[str] = None) -> List[dict]:
        """Get subscriptions with pagination and filtering"""
        query = text("""
            SELECT us.*, p.code, p.billing_period, p.price_inr
            FROM user_subscriptions us
            JOIN plans p ON us.plan_id = p.id
        """)
        params = {}
        if status:
            query += text("WHERE us.status = :status ")
            params["status"] = status
        query += text("ORDER BY us.created_at DESC OFFSET :skip LIMIT :limit")
        params.update({"skip": skip, "limit": limit})
        
        result = await db.execute(query, params)
        return [dict(row._mapping) for row in result.fetchall()]

    @staticmethod
    async def get_subscription_count(db: AsyncSession) -> int:
        """Get total subscription count"""
        result = await db.execute(text("SELECT COUNT(*) FROM user_subscriptions"))
        return result.scalar()

    @staticmethod
    async def get_credits_paginated(db: AsyncSession, skip: int = 0, limit: int = 20) -> List[dict]:
        """Get credit transactions with pagination"""
        query = text("""
            SELECT ct.*, u.email as user_email
            FROM credit_transactions ct
            JOIN users u ON ct.user_id = u.id
            ORDER BY ct.created_at DESC 
            OFFSET :skip LIMIT :limit
        """)
        
        result = await db.execute(query, {"skip": skip, "limit": limit})
        return [dict(row._mapping) for row in result.fetchall()]

    @staticmethod
    async def get_credit_transaction_count(db: AsyncSession) -> int:
        """Get total credit transaction count"""
        result = await db.execute(text("SELECT COUNT(*) FROM credit_transactions"))
        return result.scalar()

    @staticmethod
    async def get_notifications_paginated(db: AsyncSession, skip: int = 0, limit: int = 20, status: Optional[str] = None) -> List[dict]:
        """Get notifications with pagination and filtering"""
        query = text("""
            SELECT n.*, u.email as user_email
            FROM notifications n
            JOIN users u ON n.user_id = u.id
        """)
        params = {}
        if status:
            query += text("WHERE n.status = :status ")
            params["status"] = status
        query += text("ORDER BY n.created_at DESC OFFSET :skip LIMIT :limit")
        params.update({"skip": skip, "limit": limit})
        
        result = await db.execute(query, params)
        return [dict(row._mapping) for row in result.fetchall()]

    @staticmethod
    async def get_notification_count(db: AsyncSession) -> int:
        """Get total notification count"""
        result = await db.execute(text("SELECT COUNT(*) FROM notifications"))
        return result.scalar()
