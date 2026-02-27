from sqlalchemy import Column, UUID, DateTime, Numeric, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from ..base import Base


class EquityCurve(Base):
    __tablename__ = "equity_curve"

    backtest_id = Column(PG_UUID(as_uuid=True), ForeignKey("performance_metrics.id"), primary_key=True)
    timestamp = Column(DateTime(timezone=True), primary_key=True)
    equity = Column(Numeric)

    # Index for analytics
    __table_args__ = (
        Index('idx_equity_curve_backtest_timestamp', 'backtest_id', 'timestamp'),
    )
