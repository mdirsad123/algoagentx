from sqlalchemy import Column, Integer, String, Numeric, DateTime
from sqlalchemy.sql import func
from ..base import Base


class Instrument(Base):
    __tablename__ = "instruments"

    id = Column(Integer, primary_key=True)
    symbol = Column(String, nullable=False)
    exchange = Column(String, nullable=False)
    market = Column(String, nullable=False)
    instrument_type = Column(String)
    tick_size = Column(Numeric)
    lot_size = Column(Integer)
