from sqlalchemy import Column, String, Text, Float, Date, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..base import Base
import uuid


class ScreenerNews(Base):
    __tablename__ = "screener_news"
    __table_args__ = (
        UniqueConstraint('symbol', 'news_date', 'title', name='uq_news_symbol_date_title'),
    )

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symbol = Column(String(20), nullable=False, index=True)
    stock_name = Column(String(200), nullable=False)
    news_date = Column(Date, nullable=False, index=True)
    title = Column(Text, nullable=False)
    summary = Column(Text, nullable=True)
    url = Column(Text, nullable=False)
    source = Column(String(100), nullable=False)
    sentiment_label = Column(String(20), nullable=False)  # VERY_POSITIVE / POSITIVE / NEUTRAL / NEGATIVE / VERY_NEGATIVE
    sentiment_score = Column(Float, nullable=False)
    confidence = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
