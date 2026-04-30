from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class TicketCategory(str, Enum):
    ASK_AI = "ask_ai"
    TECHNICAL = "technical"
    BILLING = "billing"
    BROKER = "broker"
    LIVE_TRADING = "live_trading"
    BACKTEST = "backtest"
    STRATEGY = "strategy"
    OTHER = "other"


class TicketStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    WAITING_USER = "waiting_user"
    RESOLVED = "resolved"
    CLOSED = "closed"


class TicketPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class SupportTicketCreate(BaseModel):
    subject: str = Field(..., min_length=1, max_length=255)
    category: TicketCategory = TicketCategory.OTHER
    priority: TicketPriority = TicketPriority.MEDIUM
    message: str = Field(..., min_length=1)


class SupportTicketReplyCreate(BaseModel):
    message: str = Field(..., min_length=1)


class SupportTicketAdminUpdate(BaseModel):
    status: Optional[TicketStatus] = None
    priority: Optional[TicketPriority] = None
    category: Optional[TicketCategory] = None
    assigned_admin_id: Optional[UUID] = None


class SupportTicketAssign(BaseModel):
    admin_id: Optional[UUID] = None


class SupportTicketAttachmentOut(BaseModel):
    id: UUID
    ticket_id: UUID
    message_id: Optional[UUID] = None
    original_filename: str
    content_type: Optional[str] = None
    size_bytes: int
    created_at: datetime
    download_url: str

    class Config:
        from_attributes = True


class SupportTicketMessageOut(BaseModel):
    id: UUID
    ticket_id: UUID
    sender_id: Optional[UUID] = None
    sender_role: str
    message: str
    created_at: datetime
    attachments: list[SupportTicketAttachmentOut] = []

    class Config:
        from_attributes = True


class SupportTicketOut(BaseModel):
    id: UUID
    user_id: UUID
    subject: str
    category: str
    priority: str
    status: str
    message: str
    assigned_admin_id: Optional[UUID] = None
    last_reply_by: str
    last_reply_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    closed_at: Optional[datetime] = None
    messages: list[SupportTicketMessageOut] = []
    attachments: list[SupportTicketAttachmentOut] = []

    class Config:
        from_attributes = True


class SupportTicketListResponse(BaseModel):
    items: list[dict[str, Any]]
    total: int
    skip: int
    limit: int
