from sqlalchemy import Column, String, Integer, DateTime, Text, Index, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from ..base import Base
import uuid


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (
        Index("idx_payments_user_created", "user_id", "created_at"),
        Index("idx_payments_billing_order_id", "billing_order_id"),
        Index("idx_payments_plan_code", "plan_code"),
        Index("idx_payments_subscription_id", "subscription_id"),
    )

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(36), nullable=False)  # String to handle both UUID and Integer
    provider = Column(String(50), nullable=False)  # RAZORPAY
    purpose = Column(String(50), nullable=False)  # SUBSCRIPTION, CREDITS_TOPUP
    amount_inr = Column(Integer, nullable=False)
    currency = Column(String(3), default='INR')
    status = Column(String(20), nullable=False)  # CREATED, PAID, FAILED, REFUNDED
    billing_order_id = Column(String(64), nullable=True)
    razorpay_order_id = Column(String(100), nullable=True)
    razorpay_payment_id = Column(String(100), nullable=True)
    razorpay_signature = Column(String(200), nullable=True)

    # Subscription intent snapshot fields (legacy-safe, nullable)
    plan_id = Column(PG_UUID(as_uuid=True), nullable=True)
    plan_code = Column(String(50), nullable=True)
    billing_period = Column(String(20), nullable=True)
    subscription_id = Column(String(64), nullable=True)

    failure_reason = Column(Text, nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
