"""Legacy notification service adapter.

New API code uses app.services.notification_service.NotificationService static helpers.
Older manager code constructs NotificationService(db), so this adapter keeps that path working.
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.notifications import NotificationCreate, NotificationResponse, MarkReadRequest
from app.services.notification_service import NotificationService as StaticNotificationService


class NotificationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_notification(self, user_id: str, notification_data: NotificationCreate) -> NotificationResponse:
        notification = await StaticNotificationService.create_notification(
            self.db,
            user_id=user_id,
            title=notification_data.title,
            message=notification_data.message,
            notification_type=notification_data.type,
            severity=notification_data.severity or "info",
            entity_type=notification_data.entity_type,
            entity_id=notification_data.entity_id,
            action_url=notification_data.action_url,
            metadata=notification_data.metadata or {},
            auto_commit=True,
        )
        await self.db.refresh(notification)
        from app.services.notification_service import _to_response
        return _to_response(notification)

    async def get_notifications(self, user_id: str, skip: int = 0, limit: int = 20, unread_only: bool = False):
        return await StaticNotificationService.get_user_notifications(self.db, user_id, limit=limit, offset=skip, unread_only=unread_only)

    async def mark_notifications_read(self, request: MarkReadRequest) -> bool:
        # Legacy method did not scope by user; no current callers need this path. Keep safe no-op behavior.
        return True

    async def mark_all_notifications_read(self, user_id: str) -> bool:
        await StaticNotificationService.mark_all_as_read(self.db, user_id)
        return True

    async def get_unread_count(self, user_id: str) -> int:
        return await StaticNotificationService.get_unread_count(self.db, user_id)
