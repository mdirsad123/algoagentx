from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from uuid import UUID
from enum import Enum

class TicketStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    CLOSED = "closed"

class TicketPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class SupportTicketBase(BaseModel):
    subject: str = Field(..., min_length=1, max_length=255)
    message: str = Field(..., min_length=1)
    priority: TicketPriority = TicketPriority.MEDIUM

class SupportTicketCreate(SupportTicketBase):
    pass

class SupportTicketReplyBase(BaseModel):
    message: str = Field(..., min_length=1)

class SupportTicketReplyCreate(SupportTicketReplyBase):
    pass

class SupportTicketReply(SupportTicketReplyBase):
    id: UUID
    ticket_id: UUID
    user_id: Optional[UUID] = None
    created_at: datetime

    class Config:
        from_attributes = True

class SupportTicket(SupportTicketBase):
    id: UUID
    user_id: UUID
    status: TicketStatus = TicketStatus.OPEN
    created_at: datetime
    updated_at: datetime
    replies: List[SupportTicketReply] = []

    class Config:
        from_attributes = True

class SupportTicketUpdate(BaseModel):
    status: Optional[TicketStatus] = None
    priority: Optional[TicketPriority] = None

class SupportTicketAdminUpdate(SupportTicketUpdate):
    subject: Optional[str] = Field(None, min_length=1, max_length=255)
    message: Optional[str] = Field(None, min_length=1)