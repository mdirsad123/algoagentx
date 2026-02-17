from sqlalchemy import Column, String, DateTime, UUID, Integer
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..base import Base
import uuid


class User(Base):
    __tablename__ = "users"

    # Use String to handle both UUID strings and Integer IDs
    # The DB may have TEXT/VARCHAR UUID or INTEGER auto-increment
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="user")
    fullname = Column(String, nullable=True)
    mobile = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    support_tickets = relationship("SupportTicket", back_populates="user", cascade="all, delete-orphan")
    support_replies = relationship("SupportTicketReply", back_populates="user")
