from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID


class NotificationBase(BaseModel):
    type: str = Field(..., description="Notification type (CREDITS_LOW, PAYMENT_SUCCESS, BACKTEST_DONE, SUBSCRIPTION_EXPIRE_SOON, ERROR, STRATEGY_REQUEST, STRATEGY_DEPLOYED)")
    title: str = Field(..., description="Notification title")
    message: str = Field(..., description="Notification message")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional context data")


class NotificationCreate(NotificationBase):
    pass


class NotificationUpdate(BaseModel):
    is_read: bool = Field(..., description="Whether the notification has been read")


class NotificationResponse(NotificationBase):
    id: UUID
    user_id: str
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True


class MarkReadRequest(BaseModel):
    notification_ids: list[UUID] = Field(..., description="List of notification IDs to mark as read")


class MarkAllReadRequest(BaseModel):
    pass