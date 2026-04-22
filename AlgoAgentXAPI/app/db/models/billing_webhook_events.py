from sqlalchemy import Column, String, DateTime, Text, Index, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from ..base import Base
import uuid


class BillingWebhookEvent(Base):
    __tablename__ = "billing_webhook_events"
    __table_args__ = (
        Index("idx_billing_webhook_events_provider_event", "provider", "event_type"),
        Index("idx_billing_webhook_events_payment_id", "payment_id"),
        Index("idx_billing_webhook_events_billing_order_id", "billing_order_id"),
        Index("idx_billing_webhook_events_received_at", "received_at"),
    )

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider = Column(String(50), nullable=False)  # RAZORPAY
    event_type = Column(String(100), nullable=False)
    event_key = Column(String(191), nullable=True)
    payload_hash = Column(String(128), nullable=True)
    signature = Column(String(255), nullable=True)
    payload_json = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default="RECEIVED")  # RECEIVED, PROCESSED, IGNORED, FAILED
    processing_error = Column(Text, nullable=True)

    payment_id = Column(PG_UUID(as_uuid=True), nullable=True)
    billing_order_id = Column(String(64), nullable=True)
    purpose = Column(String(50), nullable=True)

    received_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)
