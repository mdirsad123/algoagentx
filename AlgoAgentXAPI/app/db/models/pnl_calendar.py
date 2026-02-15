from sqlalchemy import Column, UUID, Date, Numeric, ForeignKey, Index
from ..base import Base

class PnLCalendar(Base):
    __tablename__ = "pnl_calendar"

    backtest_id = Column(UUID(as_uuid=True), ForeignKey("performance_metrics.id"), primary_key=True)
    date = Column(Date, primary_key=True)
    pnl = Column(Numeric)

    # Index for analytics
    __table_args__ = (
        Index('idx_pnl_calendar_backtest_date', 'backtest_id', 'date'),
    )
