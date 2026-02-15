from sqlalchemy import Column, UUID, String, DateTime, Numeric, ForeignKey, Integer, Date
from ..base import Base

class MarketData(Base):
    __tablename__ = "market_data"

    instrument_id = Column(Integer, ForeignKey("instruments.id"), primary_key=True)
    timeframe = Column(String, primary_key=True)
    timestamp = Column(DateTime(timezone=True), primary_key=True)
    open = Column(Numeric)
    high = Column(Numeric)
    low = Column(Numeric)
    close = Column(Numeric)
    volume = Column(Numeric)
