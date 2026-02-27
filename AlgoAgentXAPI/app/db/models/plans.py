from sqlalchemy import Column, String, Integer, JSON, Boolean, DateTime, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from ..base import Base
import uuid


class Plan(Base):
    __tablename__ = "plans"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(50), nullable=False, unique=True)  # FREE, PRO, PREMIUM, ULTIMATE
    billing_period = Column(String(20), nullable=False)  # MONTHLY, YEARLY, NONE
    price_inr = Column(Integer, nullable=False, default=0)  # 0 for FREE
    included_credits = Column(Integer, nullable=False, default=0)
    features = Column(JSON, nullable=False)  # JSONB with limits
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())