from sqlalchemy import Column, String, Integer, DateTime, Boolean, JSON, func
from sqlalchemy.dialects.postgresql import UUID
from ..base import Base
import uuid


class Payment(Base):
    __tablename__ = "payments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(36), nullable=False)  # String to handle both UUID and Integer
    provider = Column(String(50), nullable=False)  # RAZORPAY
    purpose = Column(String(50), nullable=False)  # SUBSCRIPTION, CREDITS_TOPUP
    amount_inr = Column(Integer, nullable=False)
    currency = Column(String(3), default='INR')
    status = Column(String(20), nullable=False)  # CREATED, PAID, FAILED, REFUNDED
    razorpay_order_id = Column(String(100), nullable=True)
    razorpay_payment_id = Column(String(100), nullable=True)
    razorpay_signature = Column(String(200), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
