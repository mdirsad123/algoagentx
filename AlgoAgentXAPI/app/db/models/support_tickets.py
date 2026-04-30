from __future__ import annotations

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..base import Base


class TicketStatus:
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    WAITING_USER = "waiting_user"
    RESOLVED = "resolved"
    CLOSED = "closed"


class TicketPriority:
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class SupportTicket(Base):
    __tablename__ = "support_tickets"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    subject = Column(String(255), nullable=False)
    category = Column(String(50), nullable=False, default="other", server_default="other", index=True)
    priority = Column(String(20), nullable=False, default=TicketPriority.MEDIUM, server_default=TicketPriority.MEDIUM, index=True)
    status = Column(String(30), nullable=False, default=TicketStatus.OPEN, server_default=TicketStatus.OPEN, index=True)
    message = Column(Text, nullable=False)
    assigned_admin_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    last_reply_by = Column(String(20), nullable=False, default="user", server_default="user")
    last_reply_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    closed_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", foreign_keys=[user_id], back_populates="support_tickets")
    assigned_admin = relationship("User", foreign_keys=[assigned_admin_id])
    messages = relationship("SupportTicketMessage", back_populates="ticket", cascade="all, delete-orphan", order_by="SupportTicketMessage.created_at")
    attachments = relationship("SupportTicketAttachment", back_populates="ticket", cascade="all, delete-orphan", order_by="SupportTicketAttachment.created_at")


class SupportTicketMessage(Base):
    __tablename__ = "support_ticket_messages"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_id = Column(PGUUID(as_uuid=True), ForeignKey("support_tickets.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    sender_role = Column(String(20), nullable=False, default="user", server_default="user")
    message = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    ticket = relationship("SupportTicket", back_populates="messages")
    sender = relationship("User", foreign_keys=[sender_id], back_populates="support_messages")
    attachments = relationship("SupportTicketAttachment", back_populates="message", cascade="all, delete-orphan", order_by="SupportTicketAttachment.created_at")


class SupportTicketAttachment(Base):
    __tablename__ = "support_ticket_attachments"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_id = Column(PGUUID(as_uuid=True), ForeignKey("support_tickets.id", ondelete="CASCADE"), nullable=False, index=True)
    message_id = Column(PGUUID(as_uuid=True), ForeignKey("support_ticket_messages.id", ondelete="SET NULL"), nullable=True, index=True)
    uploaded_by_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    original_filename = Column(String(255), nullable=False)
    stored_filename = Column(String(255), nullable=False)
    file_path = Column(Text, nullable=False)
    content_type = Column(String(255), nullable=True)
    size_bytes = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    ticket = relationship("SupportTicket", back_populates="attachments")
    message = relationship("SupportTicketMessage", back_populates="attachments")
    uploaded_by = relationship("User", foreign_keys=[uploaded_by_id])


# Backward-compatible legacy reply model. Older code and older migrations created
# support_ticket_replies; keep the mapping so imports do not break.
class SupportTicketReply(Base):
    __tablename__ = "support_ticket_replies"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_id = Column(PGUUID(as_uuid=True), ForeignKey("support_tickets.id"), nullable=False)
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="support_replies")
