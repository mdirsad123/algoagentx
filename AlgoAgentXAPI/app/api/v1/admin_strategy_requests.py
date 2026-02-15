from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text, update
from typing import List, Optional
from datetime import datetime
from uuid import UUID

from ...db.session import async_session
from ...db.models.strategy_requests import StrategyRequest
from ...db.models.strategies import Strategy
from ...db.models.users import User
from ...schemas.strategy_requests import (
    StrategyRequestAdminUpdate, 
    StrategyRequestAdminListResponse,
    StrategyRequestAdminDetailResponse
)
from ...schemas.notifications import NotificationCreate
from ...core.dependencies import get_admin_user, get_db
from ...services.notifications import NotificationService
from ...services.email_service import email_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/", response_model=List[StrategyRequestAdminListResponse])
async def list_strategy_requests(
    status: Optional[str] = Query(None, description="Filter by status"),
    admin_user: dict = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List strategy requests with optional status filter
    Include basic user identity (email/name) for admin reference
    """
    try:
        # Build base query with user join
        query = text("""
            SELECT 
                sr.id,
                sr.title,
                sr.strategy_type,
                sr.market,
                sr.timeframe,
                sr.status,
                sr.user_id,
                u.email as user_email,
                u.name as user_name,
                sr.created_at
            FROM strategy_requests sr
            JOIN users u ON sr.user_id = u.id
        """)
        
        params = {}
        
        # Add status filter if provided
        if status:
            query = text(str(query) + " WHERE sr.status = :status")
            params["status"] = status
        
        # Order by created_at desc
        query = text(str(query) + " ORDER BY sr.created_at DESC")
        
        result = await db.execute(query, params)
        requests = result.fetchall()
        
        # Convert to response models
        return [
            StrategyRequestAdminListResponse(
                id=req.id,
                title=req.title,
                strategy_type=req.strategy_type,
                market=req.market,
                timeframe=req.timeframe,
                status=req.status,
                user_id=req.user_id,
                user_email=req.user_email,
                user_name=req.user_name,
                created_at=req.created_at
            )
            for req in requests
        ]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve strategy requests: {str(e)}"
        )

@router.get("/{request_id}", response_model=StrategyRequestAdminDetailResponse)
async def get_strategy_request_detail(
    request_id: UUID,
    admin_user: dict = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get full detail of a specific strategy request
    """
    try:
        # Query strategy request with user details
        query = text("""
            SELECT 
                sr.id,
                sr.title,
                sr.strategy_type,
                sr.market,
                sr.timeframe,
                sr.indicators,
                sr.entry_rules,
                sr.exit_rules,
                sr.risk_rules,
                sr.notes,
                sr.status,
                sr.admin_notes,
                sr.assigned_to,
                sr.deployed_strategy_id,
                sr.user_id,
                u.email as user_email,
                u.name as user_name,
                sr.created_at,
                sr.updated_at
            FROM strategy_requests sr
            JOIN users u ON sr.user_id = u.id
            WHERE sr.id = :request_id
        """)
        
        result = await db.execute(query, {"request_id": str(request_id)})
        request = result.fetchone()
        
        if not request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Strategy request not found"
            )
        
        return StrategyRequestAdminDetailResponse(
            id=request.id,
            title=request.title,
            strategy_type=request.strategy_type,
            market=request.market,
            timeframe=request.timeframe,
            indicators=request.indicators,
            entry_rules=request.entry_rules,
            exit_rules=request.exit_rules,
            risk_rules=request.risk_rules,
            notes=request.notes,
            status=request.status,
            admin_notes=request.admin_notes,
            assigned_to=request.assigned_to,
            deployed_strategy_id=request.deployed_strategy_id,
            user_id=request.user_id,
            user_email=request.user_email,
            user_name=request.user_name,
            created_at=request.created_at,
            updated_at=request.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve strategy request: {str(e)}"
        )

@router.patch("/{request_id}")
async def update_strategy_request(
    request_id: UUID,
    update_data: StrategyRequestAdminUpdate,
    admin_user: dict = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update strategy request status/admin_notes/assigned_to
    If status becomes DEPLOYED:
    - Create or update a Strategy row
    - Set strategy.owner_user_id = request.user_id
    - Set deployed_at = now()
    - Link request.deployed_strategy_id = strategy.id
    """
    try:
        # Start transaction
        async with db.begin():
            # Get the current strategy request
            request_query = text("""
                SELECT sr.*, u.id as user_id, u.email, u.name
                FROM strategy_requests sr
                JOIN users u ON sr.user_id = u.id
                WHERE sr.id = :request_id
            """)
            
            result = await db.execute(request_query, {"request_id": str(request_id)})
            request = result.fetchone()
            
            if not request:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Strategy request not found"
                )
            
            # Build update query for strategy request
            update_fields = []
            params = {"request_id": str(request_id)}
            
            if update_data.status is not None:
                update_fields.append("status = :status")
                params["status"] = update_data.status
            
            if update_data.admin_notes is not None:
                update_fields.append("admin_notes = :admin_notes")
                params["admin_notes"] = update_data.admin_notes
            
            if update_data.assigned_to is not None:
                update_fields.append("assigned_to = :assigned_to")
                params["assigned_to"] = update_data.assigned_to
            
            if update_data.deployed_strategy_id is not None:
                update_fields.append("deployed_strategy_id = :deployed_strategy_id")
                params["deployed_strategy_id"] = str(update_data.deployed_strategy_id)
            
            if update_fields:
                update_query = text(f"""
                    UPDATE strategy_requests 
                    SET {', '.join(update_fields)}, updated_at = NOW()
                    WHERE id = :request_id
                """)
                await db.execute(update_query, params)
            
            # Handle deployment logic if status is DEPLOYED
            new_status = update_data.status or request.status
            if new_status == "DEPLOYED":
                deployed_strategy_id = update_data.deployed_strategy_id
                
                if deployed_strategy_id:
                    # Use existing strategy
                    strategy_query = text("""
                        SELECT * FROM strategies WHERE id = :strategy_id
                    """)
                    strategy_result = await db.execute(strategy_query, {"strategy_id": str(deployed_strategy_id)})
                    existing_strategy = strategy_result.fetchone()
                    
                    if not existing_strategy:
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND,
                            detail="Specified strategy not found"
                        )
                    
                    # Update strategy owner and deployed_at
                    update_strategy_query = text("""
                        UPDATE strategies 
                        SET owner_user_id = :owner_user_id, 
                            parameters = COALESCE(:parameters, parameters)
                        WHERE id = :strategy_id
                    """)
                    await db.execute(update_strategy_query, {
                        "strategy_id": str(deployed_strategy_id),
                        "owner_user_id": request.user_id,
                        "parameters": {
                            "strategy_request_id": str(request_id),
                            "deployed_by": admin_user["user_id"],
                            "deployed_at": datetime.utcnow().isoformat()
                        }
                    })
                    
                else:
                    # Create new strategy from request
                    strategy_id = str(UUID(int=0))  # Generate new UUID
                    create_strategy_query = text("""
                        INSERT INTO strategies (
                            id, name, description, parameters, created_by, created_at
                        ) VALUES (
                            :strategy_id, :name, :description, :parameters, :created_by, NOW()
                        )
                    """)
                    
                    await db.execute(create_strategy_query, {
                        "strategy_id": strategy_id,
                        "name": f"Deployed: {request.title}",
                        "description": f"Strategy deployed from request {request.title}",
                        "parameters": {
                            "strategy_request_id": str(request_id),
                            "original_request": {
                                "title": request.title,
                                "strategy_type": request.strategy_type,
                                "market": request.market,
                                "timeframe": request.timeframe,
                                "indicators": request.indicators,
                                "entry_rules": request.entry_rules,
                                "exit_rules": request.exit_rules,
                                "risk_rules": request.risk_rules,
                                "notes": request.notes
                            },
                            "deployed_by": admin_user["user_id"],
                            "deployed_at": datetime.utcnow().isoformat()
                        },
                        "created_by": request.user_id
                    })
                    
                    # Update request with deployed strategy ID
                    update_request_query = text("""
                        UPDATE strategy_requests 
                        SET deployed_strategy_id = :strategy_id
                        WHERE id = :request_id
                    """)
                    await db.execute(update_request_query, {
                        "request_id": str(request_id),
                        "strategy_id": strategy_id
                    })
            
            # Send notification to user if strategy was deployed
            if new_status == "DEPLOYED":
                try:
                    # Send in-app notification to user
                    notification_service = NotificationService(db)
                    notification_data = NotificationCreate(
                        type="STRATEGY_DEPLOYED",
                        title="Strategy Deployed",
                        message=f"Your strategy '{request.title}' is ready.",
                        metadata={
                            "request_id": str(request_id),
                            "strategy_id": str(deployed_strategy_id) if deployed_strategy_id else strategy_id,
                            "deployed_by": admin_user["user_id"]
                        }
                    )
                    await notification_service.create_notification(request.user_id, notification_data)
                    
                    # Send email notification to user
                    await email_service.send_strategy_deployed_notification(
                        user_email=request.email,
                        user_name=request.name or request.email,
                        strategy_title=request.title
                    )
                    
                except Exception as e:
                    logger.error("Failed to send deployment notification: %s", str(e))
                    # Don't fail the deployment if notification fails

            await db.commit()
            
        return {"message": "Strategy request updated successfully"}
        
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update strategy request: {str(e)}"
        )