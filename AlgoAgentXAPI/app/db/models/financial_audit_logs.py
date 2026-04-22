from sqlalchemy import Column, String, DateTime, Text, Index, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from ..base import Base
import uuid


class FinancialAuditLog(Base):
    __tablename__ = "financial_audit_logs"
    __table_args__ = (
        Index("idx_financial_audit_logs_created", "created_at"),
        Index("idx_financial_audit_logs_action_type", "action_type"),
        Index("idx_financial_audit_logs_user_id", "user_id"),
        Index("idx_financial_audit_logs_payment_id", "payment_id"),
        Index("idx_financial_audit_logs_order_id", "billing_order_id"),
    )

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    action_type = Column(String(80), nullable=False)
    actor_user_id = Column(String(36), nullable=True)
    user_id = Column(String(36), nullable=True)

    payment_id = Column(PG_UUID(as_uuid=True), nullable=True)
    billing_order_id = Column(String(64), nullable=True)
    subscription_id = Column(PG_UUID(as_uuid=True), nullable=True)
    credit_transaction_id = Column(String(64), nullable=True)
    refund_id = Column(PG_UUID(as_uuid=True), nullable=True)

    status = Column(String(30), nullable=False, default="SUCCESS")
    message = Column(Text, nullable=True)
    metadata_json = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
