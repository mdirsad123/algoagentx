from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from typing import List
from uuid import UUID

from app.core.dependencies import get_current_user, get_db
from app.db.models.users import User
from app.schemas.support_tickets import (
    SupportTicketCreate, SupportTicket, SupportTicketReplyCreate, SupportTicketReply
)
from app.db.models.support_tickets import SupportTicket as SupportTicketModel
from app.db.models.support_tickets import SupportTicketReply as SupportTicketReplyModel

router = APIRouter()

@router.post("/", response_model=SupportTicket, status_code=status.HTTP_201_CREATED)
async def create_support_ticket(
    ticket_data: SupportTicketCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new support ticket"""
    ticket = SupportTicketModel(
        user_id=current_user.id,
        subject=ticket_data.subject,
        message=ticket_data.message,
        priority=ticket_data.priority
    )
    
    db.add(ticket)
    await db.commit()
    await db.refresh(ticket)
    
    return ticket

@router.get("/", response_model=List[SupportTicket])
async def get_user_support_tickets(
    skip: int = 0,
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all support tickets for the current user"""
    result = await db.execute(
        select(SupportTicketModel)
        .where(SupportTicketModel.user_id == current_user.id)
        .options(selectinload(SupportTicketModel.replies))
        .offset(skip)
        .limit(limit)
        .order_by(SupportTicketModel.created_at.desc())
    )
    tickets = result.scalars().all()
    return tickets

@router.get("/{ticket_id}", response_model=SupportTicket)
async def get_support_ticket(
    ticket_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific support ticket by ID"""
    result = await db.execute(
        select(SupportTicketModel)
        .where(
            SupportTicketModel.id == ticket_id,
            SupportTicketModel.user_id == current_user.id
        )
        .options(selectinload(SupportTicketModel.replies))
    )
    ticket = result.scalar_one_or_none()
    
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )
    
    return ticket

@router.post("/{ticket_id}/reply", response_model=SupportTicketReply, status_code=status.HTTP_201_CREATED)
async def reply_to_support_ticket(
    ticket_id: UUID,
    reply_data: SupportTicketReplyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Reply to a support ticket"""
    # First, verify the ticket exists and belongs to the user
    result = await db.execute(
        select(SupportTicketModel)
        .where(
            SupportTicketModel.id == ticket_id,
            SupportTicketModel.user_id == current_user.id
        )
    )
    ticket = result.scalar_one_or_none()
    
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )
    
    # Create the reply
    reply = SupportTicketReplyModel(
        ticket_id=ticket_id,
        user_id=current_user.id,
        message=reply_data.message
    )
    
    db.add(reply)
    await db.commit()
    await db.refresh(reply)
    
    # Update ticket status to in_progress if it was open
    if ticket.status == 'open':
        await db.execute(
            update(SupportTicketModel)
            .where(SupportTicketModel.id == ticket_id)
            .values(status='in_progress')
        )
        await db.commit()
    
    return reply