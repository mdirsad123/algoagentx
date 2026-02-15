from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update
from typing import List, Optional
from uuid import UUID

from ..db.models.notifications import Notification
from ..schemas.notifications import NotificationResponse


class NotificationService:
    @staticmethod
    async def get_user_notifications(
        db: AsyncSession, 
        user_id: str, 
        limit: int = 10
    ) -> List[NotificationResponse]:
        """
        Get user notifications ordered by created_at desc
        """
        try:
            result = await db.execute(
                select(Notification)
                .where(Notification.user_id == user_id)
                .order_by(Notification.created_at.desc())
                .limit(limit)
            )
            notifications = result.scalars().all()
            
            # Convert to response models
            return [
                NotificationResponse(
                    id=notification.id,
                    user_id=notification.user_id,
                    type=notification.type,
                    title=notification.title,
                    message=notification.message,
                    metadata=notification.extra_data,
                    is_read=notification.is_read,
                    created_at=notification.created_at
                )
                for notification in notifications
            ]
        except Exception as e:
            raise e

    @staticmethod
    async def get_unread_count(
        db: AsyncSession, 
        user_id: str
    ) -> int:
        """
        Get count of unread notifications for current user
        """
        try:
            result = await db.execute(
                select(func.count(Notification.id))
                .where(
                    Notification.user_id == user_id,
                    Notification.is_read == False
                )
            )
            count = result.scalar() or 0
            return count
        except Exception as e:
            raise e

    @staticmethod
    async def mark_as_read(
        db: AsyncSession, 
        notification_id: str, 
        user_id: str
    ) -> Optional[NotificationResponse]:
        """
        Mark a notification as read
        """
        try:
            # First get the notification to verify it exists and belongs to the user
            result = await db.execute(
                select(Notification)
                .where(
                    Notification.id == UUID(notification_id),
                    Notification.user_id == user_id
                )
            )
            notification = result.scalar_one_or_none()
            
            if not notification:
                return None
            
            # Update the notification
            await db.execute(
                update(Notification)
                .where(Notification.id == UUID(notification_id))
                .values(is_read=True)
            )
            await db.commit()
            
            # Refresh and return
            await db.refresh(notification)
            
            return NotificationResponse(
                id=notification.id,
                user_id=notification.user_id,
                type=notification.type,
                title=notification.title,
                message=notification.message,
                metadata=notification.extra_data,
                is_read=notification.is_read,
                created_at=notification.created_at
            )
        except Exception as e:
            await db.rollback()
            raise e