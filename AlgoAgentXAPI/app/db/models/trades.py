from sqlalchemy import Column, BigInteger, Integer, DateTime, String, Numeric, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from ..base import Base


class Trade(Base):
    __tablename__ = "trades"

    id = Column(BigInteger, primary_key=True)
    backtest_id = Column(PG_UUID(as_uuid=True), ForeignKey("performance_metrics.id"), index=True)
    instrument_id = Column(Integer, ForeignKey("instruments.id"))
    entry_time = Column(DateTime(timezone=True), index=True)
    exit_time = Column(DateTime(timezone=True))
    side = Column(String)
    quantity = Column(Integer)
    entry_price = Column(Numeric)
    exit_price = Column(Numeric)
    pnl = Column(Numeric)
    exit_type = Column(String)

    # Index for analytics
    __table_args__ = (
        Index('idx_trades_backtest_entry', 'backtest_id', 'entry_time'),
    )
