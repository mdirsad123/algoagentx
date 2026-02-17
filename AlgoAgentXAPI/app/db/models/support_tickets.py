from sqlalchemy import Column, String, Text, TIMESTAMP, ForeignKey, Enum, UUID
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import ENUM
import uuid
from ..base import Base

# Define enums
ticket_status_enum = ENUM('open', 'in_progress', 'closed', name='ticket_status')
ticket_priority_enum = ENUM('low', 'medium', 'high', name='ticket_priority')

# Create enum classes for import
class TicketStatus:
    OPEN = 'open'
    IN_PROGRESS = 'in_progress'
    CLOSED = 'closed'

class TicketPriority:
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'

class SupportTicket(Base):
    __tablename__ = "support_tickets"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    subject = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    status = Column(ticket_status_enum, default='open', nullable=False)
    priority = Column(ticket_priority_enum, default='medium', nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="support_tickets")
    replies = relationship("SupportTicketReply", back_populates="ticket", cascade="all, delete-orphan")

class SupportTicketReply(Base):
    __tablename__ = "support_ticket_replies"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_id = Column(PGUUID(as_uuid=True), ForeignKey("support_tickets.id"), nullable=False)
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True)  # nullable for system messages
    message = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    
    # Relationships
    ticket = relationship("SupportTicket", back_populates="replies")
    user = relationship("User", back_populates="support_replies")