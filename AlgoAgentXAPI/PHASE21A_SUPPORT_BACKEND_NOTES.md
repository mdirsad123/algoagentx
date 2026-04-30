# Phase 21A — Support System Backend + Attachments Foundation

## Updated backend files

- `app/db/models/support_tickets.py`
  - Added full support ticket model fields.
  - Added `SupportTicketMessage` conversation table model.
  - Added `SupportTicketAttachment` attachment table model.
  - Kept legacy `SupportTicketReply` model for backward compatibility.

- `app/schemas/support_tickets.py`
  - Added categories, priorities, statuses, admin update, assignment, messages, attachments response schemas.

- `app/api/v1/support_tickets.py`
  - User APIs:
    - `GET /api/v1/support-tickets`
    - `POST /api/v1/support-tickets`
    - `GET /api/v1/support-tickets/{ticket_id}`
    - `POST /api/v1/support-tickets/{ticket_id}/messages`
    - `POST /api/v1/support-tickets/{ticket_id}/reply` legacy alias
    - `PATCH /api/v1/support-tickets/{ticket_id}/close`
    - `GET /api/v1/support-tickets/{ticket_id}/attachments/{attachment_id}`
  - Admin APIs:
    - `GET /api/v1/admin/support-tickets`
    - `GET /api/v1/admin/support-tickets/{ticket_id}`
    - `POST /api/v1/admin/support-tickets/{ticket_id}/messages`
    - `POST /api/v1/admin/support-tickets/{ticket_id}/reply` legacy alias
    - `PATCH /api/v1/admin/support-tickets/{ticket_id}`
    - `POST /api/v1/admin/support-tickets/{ticket_id}/assign`
  - Supports JSON and multipart form-data.
  - Saves attachments under `storage/support_tickets/{ticket_id}/`.
  - Validates extension/content type and max file size.

- `app/api/v1/router.py`
  - Registered new admin support router.

- `app/api/v1/admin.py`
  - Legacy support endpoints moved to `/admin/support-tickets-legacy` so the new full backend owns `/admin/support-tickets`.

- `app/db/models/notifications.py`
  - Added optional support fields `entity_type`, `entity_id`, and `read_at`.

- `support_system_v21A_manual_migration.sql`
  - Safe DBeaver migration for support tickets, messages, attachments, and notification compatibility.

## Manual SQL required

Run `support_system_v21A_manual_migration.sql` in DBeaver before testing the new APIs.

## Attachment settings

Optional environment variables:

```env
SUPPORT_STORAGE_DIR=storage/support_tickets
SUPPORT_ATTACHMENT_MAX_BYTES=10485760
```

Defaults are already set in code if these variables are missing.
