from sqlalchemy import Column, String, Text, Boolean, DateTime, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship, column_property
from ..base import Base
import uuid


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    type = Column(String(50), nullable=False)  # CREDITS_LOW, PAYMENT_SUCCESS, BACKTEST_DONE, SUBSCRIPTION_EXPIRE_SOON, ERROR
    title = Column(Text, nullable=False)
    message = Column(Text, nullable=False)
    extra_data = Column("metadata", JSON, nullable=True)  # Additional context data (renamed from metadata to avoid SQLAlchemy conflict)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship to User
    user = relationship("User", backref="notifications")