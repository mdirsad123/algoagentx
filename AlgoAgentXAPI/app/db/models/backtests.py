from sqlalchemy import Column, String, Date, Numeric, UUID, Integer, ForeignKey, DateTime, Index
from sqlalchemy.sql import func
from ..base import Base

class PerformanceMetric(Base):
    __tablename__ = "performance_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=func.gen_random_uuid())
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    strategy_id = Column(String, ForeignKey("strategies.id"), index=True)
    instrument_id = Column(Integer, ForeignKey("instruments.id"), index=True)
    timeframe = Column(String)
    start_date = Column(Date)
    end_date = Column(Date)
    initial_capital = Column(Numeric)
    final_capital = Column(Numeric)
    net_profit = Column(Numeric)
    max_drawdown = Column(Numeric)
    sharpe_ratio = Column(Numeric)
    sortino_ratio = Column(Numeric)
    calmar_ratio = Column(Numeric)
    win_rate = Column(Numeric)
    total_trades = Column(Integer)
    winning_trades = Column(Integer)
    losing_trades = Column(Integer)
    status = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Indexes for analytics
    __table_args__ = (
        Index('idx_performance_metrics_user_strategy', 'user_id', 'strategy_id'),
        Index('idx_performance_metrics_instrument', 'instrument_id'),
        Index('idx_performance_metrics_dates', 'start_date', 'end_date'),
    )
