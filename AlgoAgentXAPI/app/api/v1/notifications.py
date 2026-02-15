from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated, List
from datetime import datetime

from app.core.dependencies import get_current_user, get_db
from app.schemas.notifications import NotificationResponse
from app.services.notification_service import NotificationService

router = APIRouter(
    prefix="/notifications",
    tags=["notifications"]
)

@router.get("/", response_model=List[NotificationResponse])
async def get_notifications(
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(default=10, ge=1, le=100, description="Number of notifications to return")
):
    """
    Get user notifications ordered by created_at desc
    """
    try:
        notifications = await NotificationService.get_user_notifications(
            db, 
            current_user["user_id"], 
            limit=limit
        )
        return notifications
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving notifications: {str(e)}"
        )

@router.get("/unread-count", response_model=dict)
async def get_unread_count(
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Get count of unread notifications for current user
    """
    try:
        count = await NotificationService.get_unread_count(
            db, 
            current_user["user_id"]
        )
        return {"unread_count": count}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving unread count: {str(e)}"
        )

@router.post("/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_as_read(
    notification_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Mark a notification as read
    """
    try:
        notification = await NotificationService.mark_as_read(
            db, 
            notification_id, 
            current_user["user_id"]
        )
        
        if not notification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found"
            )
        
        return notification
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating notification: {str(e)}"
        )