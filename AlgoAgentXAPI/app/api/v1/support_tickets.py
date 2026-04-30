from __future__ import annotations

import os
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import FileResponse
from starlette.datastructures import UploadFile
from sqlalchemy import String, cast, func, inspect, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.dependencies import get_admin_user, get_current_user, get_db
from app.db.compat import as_uuid_or_str, column_text
from app.db.models import User
from app.services.notification_service import NotificationService
from app.db.models.support_tickets import (
    SupportTicket,
    SupportTicketAttachment,
    SupportTicketMessage,
)
from app.schemas.support_tickets import (
    SupportTicketAdminUpdate,
    SupportTicketAssign,
    TicketCategory,
    TicketPriority,
    TicketStatus,
)
from app.utils.api_response import success_response

router = APIRouter()

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "pdf", "txt", "csv", "xlsx", "docx", "zip"}
ALLOWED_CONTENT_PREFIXES = ("image/", "text/")
ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/zip",
    "application/x-zip-compressed",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/csv",
    "text/plain",
}
STORAGE_ROOT = Path(os.getenv("SUPPORT_STORAGE_DIR", "storage/support_tickets")).resolve()
MAX_ATTACHMENT_BYTES = int(os.getenv("SUPPORT_ATTACHMENT_MAX_BYTES", getattr(settings, "support_attachment_max_bytes", 10 * 1024 * 1024)))


def _now() -> datetime:
    return datetime.utcnow()


def _enum_value(value: Any, default: str) -> str:
    if value is None:
        return default
    return str(getattr(value, "value", value) or default)


def _safe_filename(filename: str) -> str:
    name = Path(filename or "attachment").name
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(name).stem).strip("._") or "attachment"
    suffix = re.sub(r"[^A-Za-z0-9.]+", "", Path(name).suffix.lower())
    return f"{stem[:80]}{suffix[:20]}"


def _file_ext(filename: str) -> str:
    return Path(filename or "").suffix.lower().lstrip(".")


def _is_allowed_file(filename: str, content_type: Optional[str]) -> bool:
    ext = _file_ext(filename)
    if ext not in ALLOWED_EXTENSIONS:
        return False
    ctype = (content_type or "").lower()
    if not ctype:
        return True
    return ctype in ALLOWED_CONTENT_TYPES or ctype.startswith(ALLOWED_CONTENT_PREFIXES)


def _attachment_url(ticket_id: Any, attachment_id: Any) -> str:
    return f"/api/v1/support-tickets/{ticket_id}/attachments/{attachment_id}"


def _attachment_payload(att: SupportTicketAttachment) -> dict[str, Any]:
    return {
        "id": str(att.id),
        "ticket_id": str(att.ticket_id),
        "message_id": str(att.message_id) if att.message_id else None,
        "original_filename": att.original_filename,
        "stored_filename": att.stored_filename,
        "content_type": att.content_type,
        "size_bytes": int(att.size_bytes or 0),
        "created_at": att.created_at.isoformat() if att.created_at else None,
        "download_url": _attachment_url(att.ticket_id, att.id),
    }


def _message_payload(msg: SupportTicketMessage) -> dict[str, Any]:
    return {
        "id": str(msg.id),
        "ticket_id": str(msg.ticket_id),
        "sender_id": str(msg.sender_id) if msg.sender_id else None,
        "sender_role": msg.sender_role,
        "message": msg.message,
        "created_at": msg.created_at.isoformat() if msg.created_at else None,
        "attachments": [_attachment_payload(a) for a in getattr(msg, "attachments", [])],
    }


def _relationship_loaded(obj: Any, name: str) -> bool:
    try:
        return name not in inspect(obj).unloaded
    except Exception:
        return False


def _ticket_payload(ticket: SupportTicket, include_messages: bool = True, user_email: Optional[str] = None, user_name: Optional[str] = None) -> dict[str, Any]:
    ticket_attachments = []
    if _relationship_loaded(ticket, "attachments"):
        ticket_attachments = [_attachment_payload(a) for a in getattr(ticket, "attachments", []) if not a.message_id]

    payload = {
        "id": str(ticket.id),
        "user_id": str(ticket.user_id),
        "user_email": user_email,
        "user_name": user_name,
        "subject": ticket.subject,
        "category": ticket.category or "other",
        "priority": ticket.priority or "medium",
        "status": ticket.status or "open",
        "message": ticket.message,
        "assigned_admin_id": str(ticket.assigned_admin_id) if ticket.assigned_admin_id else None,
        "last_reply_by": ticket.last_reply_by or "user",
        "last_reply_at": ticket.last_reply_at.isoformat() if ticket.last_reply_at else None,
        "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
        "updated_at": ticket.updated_at.isoformat() if ticket.updated_at else None,
        "closed_at": ticket.closed_at.isoformat() if ticket.closed_at else None,
        "attachments": ticket_attachments,
    }
    if include_messages:
        payload["messages"] = [_message_payload(m) for m in getattr(ticket, "messages", [])] if _relationship_loaded(ticket, "messages") else []
    return payload


async def _parse_ticket_request(request: Request) -> tuple[dict[str, Any], list[UploadFile]]:
    content_type = (request.headers.get("content-type") or "").lower()
    files: list[UploadFile] = []
    if "multipart/form-data" in content_type:
        form = await request.form()
        data = {k: v for k, v in form.multi_items() if not isinstance(v, UploadFile)}
        for key in ("attachments", "files", "file"):
            for value in form.getlist(key):
                if isinstance(value, UploadFile) and value.filename:
                    files.append(value)
        return data, files
    try:
        payload = await request.json()
        return dict(payload or {}), []
    except Exception:
        return {}, []


async def _save_attachments(
    db: AsyncSession,
    *,
    ticket_id: UUID,
    uploaded_by_id: str,
    files: Iterable[UploadFile],
    message_id: Optional[UUID] = None,
) -> list[SupportTicketAttachment]:
    saved: list[SupportTicketAttachment] = []
    if not files:
        return saved
    ticket_dir = (STORAGE_ROOT / str(ticket_id)).resolve()
    if STORAGE_ROOT not in ticket_dir.parents and ticket_dir != STORAGE_ROOT:
        raise HTTPException(status_code=400, detail="Invalid storage path")
    ticket_dir.mkdir(parents=True, exist_ok=True)

    for file in files:
        original = file.filename or "attachment"
        if not _is_allowed_file(original, file.content_type):
            raise HTTPException(status_code=400, detail=f"Unsupported attachment type: {original}")
        content = await file.read()
        size = len(content)
        if size > MAX_ATTACHMENT_BYTES:
            raise HTTPException(status_code=413, detail=f"Attachment too large: {original}. Max size is {MAX_ATTACHMENT_BYTES // (1024 * 1024)}MB")
        safe_name = _safe_filename(original)
        stored_name = f"{uuid.uuid4().hex}_{safe_name}"
        path = (ticket_dir / stored_name).resolve()
        if ticket_dir not in path.parents:
            raise HTTPException(status_code=400, detail="Invalid attachment path")
        path.write_bytes(content)
        att = SupportTicketAttachment(
            ticket_id=ticket_id,
            message_id=message_id,
            uploaded_by_id=as_uuid_or_str(uploaded_by_id),
            original_filename=original,
            stored_filename=stored_name,
            file_path=str(path.relative_to(Path.cwd().resolve())) if str(path).startswith(str(Path.cwd().resolve())) else str(path),
            content_type=file.content_type,
            size_bytes=size,
        )
        db.add(att)
        saved.append(att)
    return saved


async def _create_notification(db: AsyncSession, user_id: Any, title: str, message: str, notification_type: str, metadata: Optional[dict[str, Any]] = None) -> None:
    try:
        data = metadata or {}
        await NotificationService.create_notification(
            db=db,
            user_id=str(user_id),
            title=title,
            message=message,
            notification_type=notification_type,
            severity=str(data.get("severity") or "info"),
            entity_type=data.get("entity_type"),
            entity_id=str(data.get("entity_id")) if data.get("entity_id") is not None else None,
            action_url=data.get("action_url"),
            metadata=data,
            auto_commit=False,
            send_email=True,
        )
    except Exception:
        # Notifications and emails must not block support workflow.
        pass


async def _admin_user_ids(db: AsyncSession) -> list[str]:
    try:
        rows = (await db.execute(select(User.id).where(func.lower(cast(User.role, String)) == "admin"))).scalars().all()
        return [str(r) for r in rows]
    except Exception:
        return []


async def _notify_admins(db: AsyncSession, title: str, message: str, ticket_id: UUID, preferred_admin_id: Optional[Any] = None) -> None:
    admin_ids = [str(preferred_admin_id)] if preferred_admin_id else await _admin_user_ids(db)
    for admin_id in admin_ids:
        await _create_notification(db, admin_id, title, message, "SUPPORT_TICKET", {"entity_type": "support_ticket", "entity_id": str(ticket_id), "action_url": f"/admin/support-tickets/{ticket_id}"})


async def _commit_notifications_safely(db: AsyncSession) -> None:
    try:
        await db.commit()
    except Exception:
        await db.rollback()


async def _load_ticket_for_user(db: AsyncSession, ticket_id: UUID, user_id: str, include_messages: bool = False) -> SupportTicket:
    stmt = select(SupportTicket).where(SupportTicket.id == ticket_id, column_text(SupportTicket.user_id) == str(user_id))
    if include_messages:
        stmt = stmt.options(selectinload(SupportTicket.messages).selectinload(SupportTicketMessage.attachments), selectinload(SupportTicket.attachments))
    ticket = (await db.execute(stmt)).scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


async def _load_ticket_admin(db: AsyncSession, ticket_id: UUID, include_messages: bool = False) -> SupportTicket:
    stmt = select(SupportTicket).where(SupportTicket.id == ticket_id)
    if include_messages:
        stmt = stmt.options(selectinload(SupportTicket.messages).selectinload(SupportTicketMessage.attachments), selectinload(SupportTicket.attachments))
    ticket = (await db.execute(stmt)).scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


@router.get("")
@router.get("/")
async def get_user_support_tickets(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    stmt = select(SupportTicket).where(column_text(SupportTicket.user_id) == str(current_user["user_id"]))
    count_stmt = select(func.count()).select_from(SupportTicket).where(column_text(SupportTicket.user_id) == str(current_user["user_id"]))
    if status_filter:
        stmt = stmt.where(SupportTicket.status == status_filter)
        count_stmt = count_stmt.where(SupportTicket.status == status_filter)
    total = int((await db.execute(count_stmt)).scalar() or 0)
    tickets = (await db.execute(stmt.order_by(SupportTicket.updated_at.desc(), SupportTicket.created_at.desc()).offset(skip).limit(limit))).scalars().all()
    return success_response({"items": [_ticket_payload(t, include_messages=False) for t in tickets], "total": total, "skip": skip, "limit": limit})


@router.post("", status_code=status.HTTP_201_CREATED)
@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_support_ticket(request: Request, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    data, files = await _parse_ticket_request(request)
    subject = str(data.get("subject") or "").strip()
    message = str(data.get("message") or "").strip()
    if not subject or not message:
        raise HTTPException(status_code=422, detail="subject and message are required")
    category = _enum_value(data.get("category"), TicketCategory.OTHER.value)
    priority = _enum_value(data.get("priority"), TicketPriority.MEDIUM.value)
    if category not in {c.value for c in TicketCategory}:
        category = TicketCategory.OTHER.value
    if priority not in {p.value for p in TicketPriority}:
        priority = TicketPriority.MEDIUM.value

    ticket = SupportTicket(
        user_id=as_uuid_or_str(current_user["user_id"]),
        subject=subject,
        category=category,
        priority=priority,
        status=TicketStatus.OPEN.value,
        message=message,
        last_reply_by="user",
        last_reply_at=_now(),
    )
    db.add(ticket)
    await db.flush()
    msg = SupportTicketMessage(ticket_id=ticket.id, sender_id=as_uuid_or_str(current_user["user_id"]), sender_role="user", message=message)
    db.add(msg)
    await db.flush()
    await _save_attachments(db, ticket_id=ticket.id, uploaded_by_id=current_user["user_id"], files=files, message_id=msg.id)
    ticket_id = ticket.id
    await db.commit()
    await _notify_admins(db, "New support ticket", f"New ticket: {subject}", ticket_id)
    await _commit_notifications_safely(db)
    ticket = await _load_ticket_for_user(db, ticket_id, str(current_user["user_id"]), include_messages=True)
    return success_response(_ticket_payload(ticket), "Support ticket created successfully")


@router.get("/{ticket_id}")
async def get_support_ticket(ticket_id: UUID, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    ticket = await _load_ticket_for_user(db, ticket_id, str(current_user["user_id"]), include_messages=True)
    return success_response(_ticket_payload(ticket))


@router.post("/{ticket_id}/messages", status_code=status.HTTP_201_CREATED)
async def user_reply_to_ticket(ticket_id: UUID, request: Request, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    data, files = await _parse_ticket_request(request)
    message = str(data.get("message") or "").strip()
    if not message and not files:
        raise HTTPException(status_code=422, detail="message or attachment is required")
    ticket = await _load_ticket_for_user(db, ticket_id, str(current_user["user_id"]))
    if ticket.status == TicketStatus.CLOSED.value:
        ticket.status = TicketStatus.OPEN.value
        ticket.closed_at = None
    msg = SupportTicketMessage(ticket_id=ticket.id, sender_id=as_uuid_or_str(current_user["user_id"]), sender_role="user", message=message or "Attachment uploaded")
    db.add(msg)
    await db.flush()
    await _save_attachments(db, ticket_id=ticket.id, uploaded_by_id=current_user["user_id"], files=files, message_id=msg.id)
    ticket.last_reply_by = "user"
    ticket.last_reply_at = _now()
    ticket.updated_at = _now()
    subject_for_notification = ticket.subject
    assigned_admin_id = ticket.assigned_admin_id
    await db.commit()
    await _notify_admins(db, "User replied to support ticket", f"User replied: {subject_for_notification}", ticket_id, assigned_admin_id)
    await _commit_notifications_safely(db)
    refreshed = await _load_ticket_for_user(db, ticket_id, str(current_user["user_id"]), include_messages=True)
    return success_response(_message_payload(refreshed.messages[-1]), "Reply added successfully")


@router.post("/{ticket_id}/reply", status_code=status.HTTP_201_CREATED)
async def user_reply_legacy(ticket_id: UUID, request: Request, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    return await user_reply_to_ticket(ticket_id, request, db, current_user)


@router.patch("/{ticket_id}/close")
async def close_support_ticket(ticket_id: UUID, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    ticket = await _load_ticket_for_user(db, ticket_id, str(current_user["user_id"]))
    ticket.status = TicketStatus.CLOSED.value
    ticket.closed_at = _now()
    ticket.updated_at = _now()
    ticket.last_reply_by = "user"
    await db.commit()
    return success_response({"id": str(ticket.id), "status": ticket.status}, "Ticket closed successfully")


@router.get("/{ticket_id}/attachments/{attachment_id}")
async def download_support_attachment(ticket_id: UUID, attachment_id: UUID, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    att = (await db.execute(select(SupportTicketAttachment).where(SupportTicketAttachment.id == attachment_id, SupportTicketAttachment.ticket_id == ticket_id))).scalar_one_or_none()
    if not att:
        raise HTTPException(status_code=404, detail="Attachment not found")
    ticket = await _load_ticket_admin(db, ticket_id) if str(current_user.get("role", "")).lower() == "admin" else await _load_ticket_for_user(db, ticket_id, str(current_user["user_id"]))
    path = Path(att.file_path)
    if not path.is_absolute():
        path = Path.cwd() / path
    path = path.resolve()
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="Attachment file missing")
    return FileResponse(path, media_type=att.content_type or "application/octet-stream", filename=att.original_filename)


admin_router = APIRouter()


@admin_router.get("")
@admin_router.get("/")
async def admin_list_support_tickets(
    status_filter: Optional[str] = Query(None, alias="status"),
    category: Optional[str] = None,
    priority: Optional[str] = None,
    search: Optional[str] = None,
    user_id: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_admin_user),
):
    stmt = select(SupportTicket, User.email, User.fullname).join(User, User.id == SupportTicket.user_id)
    count_stmt = select(func.count()).select_from(SupportTicket).join(User, User.id == SupportTicket.user_id)
    filters = []
    if status_filter:
        filters.append(SupportTicket.status == status_filter)
    if category:
        filters.append(SupportTicket.category == category)
    if priority:
        filters.append(SupportTicket.priority == priority)
    if user_id:
        filters.append(column_text(SupportTicket.user_id) == str(user_id))
    if search:
        pattern = f"%{search}%"
        filters.append(or_(SupportTicket.subject.ilike(pattern), SupportTicket.message.ilike(pattern), User.email.ilike(pattern), User.fullname.ilike(pattern)))
    for condition in filters:
        stmt = stmt.where(condition)
        count_stmt = count_stmt.where(condition)
    total = int((await db.execute(count_stmt)).scalar() or 0)
    rows = (await db.execute(stmt.order_by(SupportTicket.updated_at.desc(), SupportTicket.created_at.desc()).offset(skip).limit(limit))).all()
    items = [_ticket_payload(ticket, include_messages=False, user_email=email, user_name=fullname or email) for ticket, email, fullname in rows]
    return success_response({"items": items, "total": total, "skip": skip, "limit": limit})


@admin_router.get("/{ticket_id}")
async def admin_get_support_ticket(ticket_id: UUID, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_admin_user)):
    ticket = await _load_ticket_admin(db, ticket_id, include_messages=True)
    user = (await db.execute(select(User).where(User.id == ticket.user_id))).scalar_one_or_none()
    return success_response(_ticket_payload(ticket, user_email=getattr(user, "email", None), user_name=getattr(user, "fullname", None) or getattr(user, "email", None)))


@admin_router.post("/{ticket_id}/messages", status_code=status.HTTP_201_CREATED)
async def admin_reply_to_ticket(ticket_id: UUID, request: Request, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_admin_user)):
    data, files = await _parse_ticket_request(request)
    message = str(data.get("message") or "").strip()
    if not message and not files:
        raise HTTPException(status_code=422, detail="message or attachment is required")
    ticket = await _load_ticket_admin(db, ticket_id)
    new_status = str(data.get("status") or TicketStatus.WAITING_USER.value)
    if new_status not in {s.value for s in TicketStatus}:
        new_status = TicketStatus.WAITING_USER.value
    msg = SupportTicketMessage(ticket_id=ticket.id, sender_id=as_uuid_or_str(current_user["user_id"]), sender_role="admin", message=message or "Attachment uploaded")
    db.add(msg)
    await db.flush()
    await _save_attachments(db, ticket_id=ticket.id, uploaded_by_id=current_user["user_id"], files=files, message_id=msg.id)
    ticket.status = new_status
    ticket.assigned_admin_id = ticket.assigned_admin_id or as_uuid_or_str(current_user["user_id"])
    ticket.last_reply_by = "admin"
    ticket.last_reply_at = _now()
    ticket.updated_at = _now()
    ticket_owner_id = ticket.user_id
    subject_for_notification = ticket.subject
    await db.commit()
    await _create_notification(db, ticket_owner_id, "Support ticket updated", f"Admin replied to: {subject_for_notification}", "SUPPORT_TICKET_REPLY", {"entity_type": "support_ticket", "entity_id": str(ticket_id), "action_url": f"/support-tickets/{ticket_id}"})
    await _commit_notifications_safely(db)
    refreshed = await _load_ticket_admin(db, ticket_id, include_messages=True)
    return success_response(_message_payload(refreshed.messages[-1]), "Admin reply sent successfully")


@admin_router.post("/{ticket_id}/reply", status_code=status.HTTP_201_CREATED)
async def admin_reply_legacy(ticket_id: UUID, request: Request, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_admin_user)):
    return await admin_reply_to_ticket(ticket_id, request, db, current_user)


@admin_router.patch("/{ticket_id}")
async def admin_update_support_ticket(ticket_id: UUID, payload: SupportTicketAdminUpdate, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_admin_user)):
    ticket = await _load_ticket_admin(db, ticket_id)
    changed = False
    old_status = ticket.status
    for field in ("status", "priority", "category", "assigned_admin_id"):
        value = getattr(payload, field, None)
        if value is not None:
            setattr(ticket, field, as_uuid_or_str(str(value)) if field == "assigned_admin_id" else _enum_value(value, getattr(ticket, field)))
            changed = True
    if ticket.status == TicketStatus.CLOSED.value and not ticket.closed_at:
        ticket.closed_at = _now()
    elif ticket.status != TicketStatus.CLOSED.value:
        ticket.closed_at = None
    if changed:
        ticket.updated_at = _now()
    ticket_owner_id = ticket.user_id
    subject_for_notification = ticket.subject
    new_status_for_notification = ticket.status
    status_changed = old_status != ticket.status
    await db.commit()
    if status_changed:
        await _create_notification(db, ticket_owner_id, "Support ticket status changed", f"Ticket '{subject_for_notification}' status is now {new_status_for_notification}.", "SUPPORT_TICKET_STATUS", {"entity_type": "support_ticket", "entity_id": str(ticket_id), "status": new_status_for_notification, "action_url": f"/support-tickets/{ticket_id}"})
        await _commit_notifications_safely(db)
    return success_response(_ticket_payload(ticket, include_messages=False), "Ticket updated successfully")


@admin_router.post("/{ticket_id}/assign")
async def admin_assign_support_ticket(ticket_id: UUID, payload: SupportTicketAssign | None = None, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_admin_user)):
    ticket = await _load_ticket_admin(db, ticket_id)
    assign_to = str(payload.admin_id) if payload and payload.admin_id else str(current_user["user_id"])
    ticket.assigned_admin_id = as_uuid_or_str(assign_to)
    ticket.status = TicketStatus.IN_PROGRESS.value if ticket.status == TicketStatus.OPEN.value else ticket.status
    ticket.updated_at = _now()
    await db.commit()
    return success_response({"id": str(ticket.id), "assigned_admin_id": str(ticket.assigned_admin_id), "status": ticket.status}, "Ticket assigned successfully")
