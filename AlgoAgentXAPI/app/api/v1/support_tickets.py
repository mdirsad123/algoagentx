from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from typing import List
from uuid import UUID

from app.core.dependencies import get_current_user, get_db
from app.db.compat import as_uuid_or_str, column_text
from app.schemas.support_tickets import SupportTicketCreate, SupportTicketReplyCreate
from app.db.models.support_tickets import SupportTicket as SupportTicketModel
from app.db.models.support_tickets import SupportTicketReply as SupportTicketReplyModel
from app.utils.api_response import success_response

router = APIRouter()


def _ticket_payload(ticket):
    return {
        'id': str(ticket.id), 'user_id': str(ticket.user_id), 'subject': ticket.subject, 'message': ticket.message,
        'status': ticket.status, 'priority': ticket.priority, 'created_at': ticket.created_at.isoformat() if ticket.created_at else None,
        'updated_at': ticket.updated_at.isoformat() if ticket.updated_at else None,
        'replies': [{
            'id': str(reply.id), 'ticket_id': str(reply.ticket_id), 'user_id': str(reply.user_id) if reply.user_id else None,
            'message': reply.message, 'created_at': reply.created_at.isoformat() if reply.created_at else None,
        } for reply in getattr(ticket, 'replies', [])]
    }


@router.post('/', status_code=status.HTTP_201_CREATED)
async def create_support_ticket(ticket_data: SupportTicketCreate, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    ticket = SupportTicketModel(user_id=as_uuid_or_str(current_user['user_id']), subject=ticket_data.subject, message=ticket_data.message, priority=ticket_data.priority.value if hasattr(ticket_data.priority, 'value') else str(ticket_data.priority))
    db.add(ticket)
    await db.commit()
    await db.refresh(ticket)
    return success_response(_ticket_payload(ticket), 'Support ticket created successfully')


@router.get('/')
async def get_user_support_tickets(skip: int = 0, limit: int = 10, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    result = await db.execute(select(SupportTicketModel).where(column_text(SupportTicketModel.user_id) == str(current_user['user_id'])).options(selectinload(SupportTicketModel.replies)).offset(skip).limit(limit).order_by(SupportTicketModel.created_at.desc()))
    tickets = result.scalars().all()
    data = [_ticket_payload(ticket) for ticket in tickets]
    return success_response(data, 'No data found' if not data else None)


@router.get('/{ticket_id}')
async def get_support_ticket(ticket_id: UUID, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    result = await db.execute(select(SupportTicketModel).where(SupportTicketModel.id == ticket_id, column_text(SupportTicketModel.user_id) == str(current_user['user_id'])).options(selectinload(SupportTicketModel.replies)))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Ticket not found')
    return success_response(_ticket_payload(ticket))


@router.post('/{ticket_id}/reply', status_code=status.HTTP_201_CREATED)
async def reply_to_support_ticket(ticket_id: UUID, reply_data: SupportTicketReplyCreate, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    result = await db.execute(select(SupportTicketModel).where(SupportTicketModel.id == ticket_id, column_text(SupportTicketModel.user_id) == str(current_user['user_id'])))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Ticket not found')
    reply = SupportTicketReplyModel(ticket_id=ticket_id, user_id=as_uuid_or_str(current_user['user_id']), message=reply_data.message)
    db.add(reply)
    await db.commit()
    await db.refresh(reply)
    if ticket.status == 'open':
        await db.execute(update(SupportTicketModel).where(SupportTicketModel.id == ticket_id).values(status='in_progress'))
        await db.commit()
    return success_response({'id': str(reply.id), 'ticket_id': str(reply.ticket_id), 'message': reply.message, 'created_at': reply.created_at.isoformat() if reply.created_at else None}, 'Reply added successfully')
