from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from typing import List
from datetime import datetime

from ...db.session import async_session
from ...db.models.strategy_requests import StrategyRequest
from ...db.models.users import User
from ...schemas.strategy_requests import StrategyRequestCreate, StrategyRequestOut
from ...schemas.notifications import NotificationCreate
from ...core.dependencies import get_current_user, get_db
from ...services.notifications import NotificationService
from ...services.email_service import email_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/", response_model=StrategyRequestOut)
async def create_strategy_request(
    request_data: StrategyRequestCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new strategy request for the authenticated user
    """
    try:
        # Create new strategy request
        new_request = StrategyRequest(
            user_id=current_user["user_id"],
            title=request_data.title,
            strategy_type=request_data.strategy_type,
            market=request_data.market,
            timeframe=request_data.timeframe,
            indicators=request_data.indicators,
            entry_rules=request_data.entry_rules,
            exit_rules=request_data.exit_rules,
            risk_rules=request_data.risk_rules,
            notes=request_data.notes,
            status="UNDER_DEVELOPMENT"  # Default status
        )

        db.add(new_request)
        await db.commit()
        await db.refresh(new_request)

        # Get user details for notifications
        user_query = select(User).where(User.id == current_user["user_id"])
        user_result = await db.execute(user_query)
        user = user_result.scalar_one_or_none()

        if user:
            # Send in-app notification to admins
            try:
                notification_service = NotificationService(db)
                notification_data = NotificationCreate(
                    type="STRATEGY_REQUEST",
                    title="New Strategy Request",
                    message=f"{user.name or user.email} requested {request_data.title}",
                    metadata={
                        "request_id": str(new_request.id),
                        "user_id": current_user["user_id"],
                        "user_email": user.email,
                        "user_name": user.name
                    }
                )
                
                # Get all admin users and send notifications
                admin_users_query = select(User).where(User.role == "admin")
                admin_users_result = await db.execute(admin_users_query)
                admin_users = admin_users_result.scalars().all()
                
                for admin_user in admin_users:
                    await notification_service.create_notification(admin_user.id, notification_data)
                
            except Exception as e:
                logger.error("Failed to create admin notification: %s", str(e))
                # Don't fail the request if notification fails

            # Send email notification to admins
            try:
                await email_service.send_strategy_request_notification(
                    user_email=user.email,
                    user_name=user.name or user.email,
                    request_title=request_data.title
                )
            except Exception as e:
                logger.error("Failed to send admin email notification: %s", str(e))
                # Don't fail the request if email fails

        return StrategyRequestOut(
            id=new_request.id,
            user_id=new_request.user_id,
            title=new_request.title,
            strategy_type=new_request.strategy_type,
            market=new_request.market,
            timeframe=new_request.timeframe,
            indicators=new_request.indicators,
            entry_rules=new_request.entry_rules,
            exit_rules=new_request.exit_rules,
            risk_rules=new_request.risk_rules,
            notes=new_request.notes,
            status=new_request.status,
            admin_notes=new_request.admin_notes,
            assigned_to=new_request.assigned_to,
            deployed_strategy_id=new_request.deployed_strategy_id,
            created_at=new_request.created_at,
            updated_at=new_request.updated_at
        )

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create strategy request: {str(e)}"
        )

@router.get("/me", response_model=List[StrategyRequestOut])
async def get_user_strategy_requests(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all strategy requests for the authenticated user, ordered by created_at desc
    """
    try:
        # Query strategy requests for the current user
        stmt = select(StrategyRequest).where(
            StrategyRequest.user_id == current_user["user_id"]
        ).order_by(StrategyRequest.created_at.desc())

        result = await db.execute(stmt)
        requests = result.scalars().all()

        # Convert to response models
        return [
            StrategyRequestOut(
                id=req.id,
                user_id=req.user_id,
                title=req.title,
                strategy_type=req.strategy_type,
                market=req.market,
                timeframe=req.timeframe,
                indicators=req.indicators,
                entry_rules=req.entry_rules,
                exit_rules=req.exit_rules,
                risk_rules=req.risk_rules,
                notes=req.notes,
                status=req.status,
                admin_notes=req.admin_notes,
                assigned_to=req.assigned_to,
                deployed_strategy_id=req.deployed_strategy_id,
                created_at=req.created_at,
                updated_at=req.updated_at
            )
            for req in requests
        ]

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve strategy requests: {str(e)}"
        )