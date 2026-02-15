from sqlalchemy import Column, String, Text, Date, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..base import Base
import uuid


class ScreenerAnnouncements(Base):
    __tablename__ = "screener_announcements"
    __table_args__ = (
        UniqueConstraint('symbol', 'announce_date', 'title', 'exchange', name='uq_announcements_symbol_date_title_exchange'),
    )

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symbol = Column(String(20), nullable=False, index=True)
    stock_name = Column(String(200), nullable=False)
    exchange = Column(String(10), nullable=False)  # NSE/BSE
    announce_date = Column(Date, nullable=False, index=True)
    title = Column(Text, nullable=False)
    url = Column(Text, nullable=False)
    category = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
