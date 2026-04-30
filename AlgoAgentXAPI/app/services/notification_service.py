from __future__ import annotations

import logging
from typing import Any, Iterable, Optional
from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.compat import as_uuid_or_str
from app.db.models.notifications import Notification
from app.schemas.notifications import NotificationResponse
from app.services import email_service

logger = logging.getLogger(__name__)


def _to_response(notification: Notification) -> NotificationResponse:
    return NotificationResponse(
        id=notification.id,
        user_id=str(notification.user_id),
        type=notification.type,
        title=notification.title,
        message=notification.message,
        severity=notification.severity or "info",
        entity_type=notification.entity_type,
        entity_id=notification.entity_id,
        action_url=notification.action_url,
        metadata=notification.extra_data or {},
        is_read=bool(notification.is_read),
        created_at=notification.created_at,
        read_at=notification.read_at,
    )


class NotificationService:
    @staticmethod
    async def create_notification(
        db: AsyncSession,
        user_id: str,
        title: str,
        message: str,
        notification_type: str,
        severity: str = "info",
        entity_type: str | None = None,
        entity_id: str | None = None,
        action_url: str | None = None,
        metadata: Optional[dict[str, Any]] = None,
        auto_commit: bool = False,
        send_email: bool = True,
    ) -> Notification | None:
        notification = Notification(
            user_id=as_uuid_or_str(str(user_id)),
            title=title,
            message=message,
            type=notification_type,
            severity=severity or "info",
            entity_type=entity_type or (metadata or {}).get("entity_type"),
            entity_id=str(entity_id or (metadata or {}).get("entity_id") or "") or None,
            action_url=action_url or (metadata or {}).get("action_url"),
            extra_data=metadata or {},
        )
        db.add(notification)
        if auto_commit:
            await db.commit()
            await db.refresh(notification)
        else:
            try:
                await db.flush()
            except Exception:
                # Some callers create notifications inside larger transactions. Let caller handle rollback.
                raise

        if send_email:
            try:
                sent = await email_service.send_notification_email(db, str(user_id), notification)
                if sent:
                    notification.email_sent = True
                    notification.email_sent_at = datetime.utcnow()
                    notification.email_error = None
                else:
                    notification.email_sent = False
                if auto_commit:
                    await db.commit()
                    await db.refresh(notification)
            except Exception as exc:
                logger.warning("Notification email skipped: %s", exc)
                try:
                    notification.email_error = str(exc)[:1000]
                    if auto_commit:
                        await db.commit()
                except Exception:
                    pass
        return notification

    @staticmethod
    async def create_notification_safely(db: AsyncSession, *args: Any, **kwargs: Any) -> None:
        try:
            await NotificationService.create_notification(db, *args, **kwargs)
        except Exception as exc:
            logger.warning("Notification creation skipped: %s", exc)

    @staticmethod
    async def get_user_notifications(
        db: AsyncSession,
        user_id: str,
        limit: int = 20,
        offset: int = 0,
        unread_only: bool = False,
    ) -> list[NotificationResponse]:
        stmt = select(Notification).where(Notification.user_id == as_uuid_or_str(str(user_id)))
        if unread_only:
            stmt = stmt.where(Notification.is_read == False)  # noqa: E712
        stmt = stmt.order_by(Notification.created_at.desc()).offset(offset).limit(limit)
        rows = (await db.execute(stmt)).scalars().all()
        return [_to_response(row) for row in rows]

    @staticmethod
    async def get_unread_count(db: AsyncSession, user_id: str) -> int:
        count = await db.scalar(
            select(func.count(Notification.id)).where(
                Notification.user_id == as_uuid_or_str(str(user_id)),
                Notification.is_read == False,  # noqa: E712
            )
        )
        return int(count or 0)

    @staticmethod
    async def mark_as_read(db: AsyncSession, notification_id: str, user_id: str) -> NotificationResponse | None:
        stmt = select(Notification).where(
            Notification.id == UUID(str(notification_id)),
            Notification.user_id == as_uuid_or_str(str(user_id)),
        )
        notification = (await db.execute(stmt)).scalar_one_or_none()
        if not notification:
            return None
        notification.is_read = True
        notification.read_at = datetime.utcnow()
        await db.commit()
        await db.refresh(notification)
        return _to_response(notification)

    @staticmethod
    async def mark_many_as_read(db: AsyncSession, user_id: str, notification_ids: Iterable[str | UUID]) -> int:
        ids = [UUID(str(item)) for item in notification_ids]
        if not ids:
            return 0
        result = await db.execute(
            update(Notification)
            .where(
                Notification.user_id == as_uuid_or_str(str(user_id)),
                Notification.id.in_(ids),
                Notification.is_read == False,  # noqa: E712
            )
            .values(is_read=True, read_at=datetime.utcnow())
        )
        await db.commit()
        return int(result.rowcount or 0)

    @staticmethod
    async def mark_all_as_read(db: AsyncSession, user_id: str) -> int:
        result = await db.execute(
            update(Notification)
            .where(
                Notification.user_id == as_uuid_or_str(str(user_id)),
                Notification.is_read == False,  # noqa: E712
            )
            .values(is_read=True, read_at=datetime.utcnow())
        )
        await db.commit()
        return int(result.rowcount or 0)

    @staticmethod
    async def delete_notification(db: AsyncSession, notification_id: str, user_id: str) -> bool:
        result = await db.execute(
            delete(Notification).where(
                Notification.id == UUID(str(notification_id)),
                Notification.user_id == as_uuid_or_str(str(user_id)),
            )
        )
        await db.commit()
        return bool(result.rowcount)
