from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.schemas.notifications import MarkReadRequest, NotificationResponse, UnreadCountResponse
from app.services.notification_service import NotificationService

router = APIRouter()


def _user_id(current_user: dict) -> str:
    return str(current_user.get("user_id") or current_user.get("id") or "")


@router.get("", response_model=list[NotificationResponse])
@router.get("/", response_model=list[NotificationResponse])
async def get_notifications(
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    unread_only: bool = Query(False),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    skip: int | None = Query(None, ge=0),
):
    actual_offset = offset if skip is None else skip
    return await NotificationService.get_user_notifications(
        db=db,
        user_id=_user_id(current_user),
        limit=limit,
        offset=actual_offset,
        unread_only=unread_only,
    )


@router.get("/unread-count", response_model=UnreadCountResponse)
async def get_unread_count(
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    count = await NotificationService.get_unread_count(db, _user_id(current_user))
    return UnreadCountResponse(unread_count=count)


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_as_read(
    notification_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    notification = await NotificationService.mark_as_read(db, notification_id, _user_id(current_user))
    if not notification:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    return notification


@router.post("/mark-read")
async def mark_notifications_read_legacy(
    payload: MarkReadRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    updated = await NotificationService.mark_many_as_read(db, _user_id(current_user), payload.notification_ids)
    return {"success": True, "updated": updated}


@router.patch("/read-all")
async def mark_all_notifications_read(
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    updated = await NotificationService.mark_all_as_read(db, _user_id(current_user))
    return {"success": True, "updated": updated}


@router.post("/mark-all-read")
async def mark_all_notifications_read_legacy(
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    updated = await NotificationService.mark_all_as_read(db, _user_id(current_user))
    return {"success": True, "updated": updated}


@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    deleted = await NotificationService.delete_notification(db, notification_id, _user_id(current_user))
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    return {"success": True}
