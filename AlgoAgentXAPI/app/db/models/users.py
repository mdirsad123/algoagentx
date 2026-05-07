from sqlalchemy import Boolean, Column, String, DateTime, Integer, Text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.sql import func
from ..base import Base
import uuid


class User(Base):
    __tablename__ = "users"

    # Use proper UUID column type for PostgreSQL
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=True)
    role = Column(String, default="user")
    fullname = Column(String, nullable=True)
    mobile = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    auth_provider = Column(String(50), nullable=False, default="local", server_default="local")
    google_sub = Column(String(255), nullable=True, unique=True)
    avatar_url = Column(Text, nullable=True)
    email_verified = Column(Boolean, nullable=False, default=False, server_default="false")
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    last_login_provider = Column(String(50), nullable=True)
    failed_login_count = Column(Integer, nullable=False, default=0, server_default="0")


    # Relationships
    support_tickets = relationship("SupportTicket", foreign_keys="SupportTicket.user_id", back_populates="user", cascade="all, delete-orphan")
    support_replies = relationship("SupportTicketReply", back_populates="user")
    support_messages = relationship("SupportTicketMessage", foreign_keys="SupportTicketMessage.sender_id", back_populates="sender")
