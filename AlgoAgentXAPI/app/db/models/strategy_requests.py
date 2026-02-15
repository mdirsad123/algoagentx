from sqlalchemy import Column, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.sql import func, text
from sqlalchemy.orm import relationship
from ..base import Base
import uuid


class StrategyRequest(Base):
    __tablename__ = "strategy_requests"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    title = Column(Text, nullable=False)
    strategy_type = Column(Text, nullable=True)
    market = Column(Text, nullable=True)
    timeframe = Column(Text, nullable=True)
    indicators = Column(JSON, nullable=True)
    entry_rules = Column(Text, nullable=False)
    exit_rules = Column(Text, nullable=False)
    risk_rules = Column(Text, nullable=False)
    notes = Column(Text, nullable=True)
    status = Column(String, nullable=False, server_default="UNDER_DEVELOPMENT")
    admin_notes = Column(Text, nullable=True)
    assigned_to = Column(Text, nullable=True)
    deployed_strategy_id = Column(PG_UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationship to User
    user = relationship("User", backref="strategy_requests")