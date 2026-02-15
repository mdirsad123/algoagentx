from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_
from sqlalchemy.orm import selectinload
from app.db.models.notifications import Notification
from app.schemas.notifications import NotificationCreate, NotificationResponse, MarkReadRequest, MarkAllReadRequest
from uuid import UUID
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_notification(
        self, 
        user_id: str, 
        notification_data: NotificationCreate
    ) -> NotificationResponse:
        """Create a new notification for a user."""
        try:
            notification = Notification(
                user_id=user_id,
                type=notification_data.type,
                title=notification_data.title,
                message=notification_data.message,
                extra_data=notification_data.metadata
            )
            
            self.db.add(notification)
            await self.db.commit()
            await self.db.refresh(notification)
            
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
            await self.db.rollback()
            logger.error(f"Error creating notification: {e}")
            raise

    async def get_notifications(
        self, 
        user_id: str, 
        skip: int = 0, 
        limit: int = 20,
        unread_only: bool = False
    ) -> List[NotificationResponse]:
        """Get notifications for a user with pagination."""
        try:
            query = select(Notification).where(Notification.user_id == user_id)
            
            if unread_only:
                query = query.where(Notification.is_read == False)
            
            query = query.order_by(Notification.created_at.desc()).offset(skip).limit(limit)
            
            result = await self.db.execute(query)
            notifications = result.scalars().all()
            
            return [
                NotificationResponse(
                    id=n.id,
                    user_id=n.user_id,
                    type=n.type,
                    title=n.title,
                    message=n.message,
                metadata=n.extra_data,
                    is_read=n.is_read,
                    created_at=n.created_at
                ) for n in notifications
            ]
        except Exception as e:
            logger.error(f"Error getting notifications: {e}")
            raise

    async def mark_notifications_read(self, request: MarkReadRequest) -> bool:
        """Mark specific notifications as read."""
        try:
            query = update(Notification).where(
                and_(
                    Notification.id.in_(request.notification_ids),
                    Notification.is_read == False
                )
            ).values(is_read=True)
            
            await self.db.execute(query)
            await self.db.commit()
            return True
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error marking notifications as read: {e}")
            raise

    async def mark_all_notifications_read(self, user_id: str) -> bool:
        """Mark all notifications for a user as read."""
        try:
            query = update(Notification).where(
                and_(
                    Notification.user_id == user_id,
                    Notification.is_read == False
                )
            ).values(is_read=True)
            
            await self.db.execute(query)
            await self.db.commit()
            return True
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error marking all notifications as read: {e}")
            raise

    async def get_unread_count(self, user_id: str) -> int:
        """Get count of unread notifications for a user."""
        try:
            query = select(Notification).where(
                and_(
                    Notification.user_id == user_id,
                    Notification.is_read == False
                )
            )
            
            result = await self.db.execute(query)
            notifications = result.scalars().all()
            return len(notifications)
        except Exception as e:
            logger.error(f"Error getting unread count: {e}")
            raise

    async def cleanup_old_notifications(self, days_old: int = 90) -> int:
        """Clean up notifications older than specified days."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            
            # First get the count for logging
            count_query = select(Notification).where(Notification.created_at < cutoff_date)
            count_result = await self.db.execute(count_query)
            count = len(count_result.scalars().all())
            
            # Then delete
            delete_query = update(Notification).where(Notification.created_at < cutoff_date)
            await self.db.execute(delete_query)
            await self.db.commit()
            
            logger.info(f"Cleaned up {count} old notifications")
            return count
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error cleaning up old notifications: {e}")
            raise