from sqlalchemy import Column, String, DateTime, Boolean, UUID, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from ..base import Base
import uuid


class UserSubscription(Base):
    __tablename__ = "user_subscriptions"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(36), nullable=False)  # String to handle both UUID and Integer
    plan_id = Column(PG_UUID(as_uuid=True), nullable=False)
    status = Column(String(20), nullable=False)  # TRIALING, ACTIVE, CANCELED, EXPIRED
    start_at = Column(DateTime(timezone=True), nullable=False)
    end_at = Column(DateTime(timezone=True), nullable=False)
    trial_end_at = Column(DateTime(timezone=True), nullable=True)
    renews = Column(Boolean, default=True)
    razorpay_subscription_id = Column(String(100), nullable=True)
    razorpay_customer_id = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())