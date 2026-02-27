from sqlalchemy import Column, UUID, String, Numeric, DateTime, ForeignKey
from sqlalchemy.sql import func
from ..base import Base


class Metric(Base):
    __tablename__ = "metrics"

    id = Column(UUID, primary_key=True)
    backtest_id = Column(String, ForeignKey("performance_metrics.id"))
    name = Column(String, nullable=False)
    value = Column(Numeric)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
