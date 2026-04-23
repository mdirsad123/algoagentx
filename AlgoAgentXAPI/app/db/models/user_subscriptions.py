from sqlalchemy import Column, String, DateTime, Boolean, Integer, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from ..base import Base
import uuid


class UserSubscription(Base):
    __tablename__ = "user_subscriptions"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(PG_UUID(as_uuid=True), nullable=False)
    plan_id = Column(PG_UUID(as_uuid=True), nullable=False)
    status = Column(String(20), nullable=False)
    start_at = Column(DateTime(timezone=True), nullable=False)
    end_at = Column(DateTime(timezone=True), nullable=False)
    trial_end_at = Column(DateTime(timezone=True), nullable=True)
    renews = Column(Boolean, default=True)
    razorpay_subscription_id = Column(String(100), nullable=True)
    razorpay_customer_id = Column(String(100), nullable=True)

    plan_code_snapshot = Column(String(50), nullable=True)
    billing_period_snapshot = Column(String(20), nullable=True)
    plan_price_inr = Column(Integer, nullable=True)
    included_credits_total = Column(Integer, nullable=True)
    included_credits_remaining = Column(Integer, nullable=True)
    last_credit_refill_at = Column(DateTime(timezone=True), nullable=True)
    next_credit_refill_at = Column(DateTime(timezone=True), nullable=True)
    last_refill_cycle_key = Column(String(80), nullable=True)
    source_payment_id = Column(PG_UUID(as_uuid=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
