from sqlalchemy import Column, String, Integer, DateTime, Text, Index, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from ..base import Base
import uuid


class BillingDocument(Base):
    __tablename__ = "billing_documents"
    __table_args__ = (
        Index("idx_billing_documents_user_created", "user_id", "created_at"),
        Index("idx_billing_documents_payment_id", "payment_id"),
        Index("idx_billing_documents_billing_order_id", "billing_order_id"),
        Index("idx_billing_documents_document_number", "document_number"),
        Index("idx_billing_documents_document_type", "document_type"),
    )

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(PG_UUID(as_uuid=True), nullable=False)
    payment_id = Column(PG_UUID(as_uuid=True), nullable=True)
    billing_order_id = Column(String(64), nullable=True)

    document_type = Column(String(20), nullable=False)
    document_number = Column(String(100), nullable=False)
    provider = Column(String(50), nullable=False, default="INTERNAL")
    purpose = Column(String(50), nullable=False)

    amount_inr = Column(Integer, nullable=False)
    currency = Column(String(3), nullable=False, default="INR")

    plan_code = Column(String(50), nullable=True)
    billing_period = Column(String(20), nullable=True)
    credits_delta = Column(Integer, nullable=True)

    metadata_json = Column(Text, nullable=True)
    issued_at = Column(DateTime(timezone=True), server_default=func.now())
    emailed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
