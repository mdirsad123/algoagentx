from sqlalchemy import Column, String, Text, Boolean, DateTime, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..base import Base
import uuid


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String(80), nullable=False, index=True)
    severity = Column(String(30), nullable=False, server_default="info", default="info")
    entity_type = Column(String(80), nullable=True)
    entity_id = Column(String(120), nullable=True)
    action_url = Column(String(500), nullable=True)
    extra_data = Column("metadata", JSON, nullable=True)
    is_read = Column(Boolean, nullable=False, server_default="false", default=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    read_at = Column(DateTime(timezone=True), nullable=True)
    email_sent = Column(Boolean, nullable=False, server_default="false", default=False)
    email_sent_at = Column(DateTime(timezone=True), nullable=True)
    email_error = Column(Text, nullable=True)

    user = relationship("User", backref="notifications")
