from sqlalchemy import Column, String, Integer, DateTime, Text, Index, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from ..base import Base
import uuid


class BillingRefund(Base):
    __tablename__ = "billing_refunds"
    __table_args__ = (
        Index("idx_billing_refunds_payment_id", "payment_id"),
        Index("idx_billing_refunds_status", "status"),
        Index("idx_billing_refunds_created_at", "created_at"),
    )

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    payment_id = Column(PG_UUID(as_uuid=True), nullable=False)
    billing_order_id = Column(String(64), nullable=True)
    user_id = Column(String(36), nullable=False)

    provider = Column(String(50), nullable=False, default="RAZORPAY")
    provider_refund_id = Column(String(100), nullable=True)
    refund_amount_inr = Column(Integer, nullable=False)
    currency = Column(String(3), nullable=False, default="INR")

    reason = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="REQUESTED")  # REQUESTED, PROCESSED, FAILED
    requested_by_user_id = Column(String(36), nullable=True)

    provider_response_json = Column(Text, nullable=True)
    failure_reason = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)
