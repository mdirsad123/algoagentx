-- AlgoAgentX Phase 21A — Support System Backend + Attachments Foundation
-- Safe manual migration for PostgreSQL / DBeaver.
-- Run this against your AlgoAgentX database before testing the updated API.

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 1) Upgrade / create support_tickets table
CREATE TABLE IF NOT EXISTS support_tickets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    subject VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE support_tickets
    ADD COLUMN IF NOT EXISTS category VARCHAR(50) NOT NULL DEFAULT 'other',
    ADD COLUMN IF NOT EXISTS status VARCHAR(30) NOT NULL DEFAULT 'open',
    ADD COLUMN IF NOT EXISTS priority VARCHAR(20) NOT NULL DEFAULT 'medium',
    ADD COLUMN IF NOT EXISTS assigned_admin_id UUID NULL REFERENCES users(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS last_reply_by VARCHAR(20) NOT NULL DEFAULT 'user',
    ADD COLUMN IF NOT EXISTS last_reply_at TIMESTAMPTZ NULL,
    ADD COLUMN IF NOT EXISTS closed_at TIMESTAMPTZ NULL;

-- Convert old enum columns to varchar so new statuses/priorities work safely.
ALTER TABLE support_tickets ALTER COLUMN status DROP DEFAULT;
ALTER TABLE support_tickets ALTER COLUMN priority DROP DEFAULT;
ALTER TABLE support_tickets ALTER COLUMN status TYPE VARCHAR(30) USING status::text;
ALTER TABLE support_tickets ALTER COLUMN priority TYPE VARCHAR(20) USING priority::text;
ALTER TABLE support_tickets ALTER COLUMN status SET DEFAULT 'open';
ALTER TABLE support_tickets ALTER COLUMN priority SET DEFAULT 'medium';

UPDATE support_tickets SET category = 'other' WHERE category IS NULL OR category = '';
UPDATE support_tickets SET status = 'open' WHERE status IS NULL OR status = '';
UPDATE support_tickets SET priority = 'medium' WHERE priority IS NULL OR priority = '';
UPDATE support_tickets SET last_reply_by = 'user' WHERE last_reply_by IS NULL OR last_reply_by = '';
UPDATE support_tickets SET last_reply_at = created_at WHERE last_reply_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_support_tickets_user_id ON support_tickets(user_id);
CREATE INDEX IF NOT EXISTS idx_support_tickets_status ON support_tickets(status);
CREATE INDEX IF NOT EXISTS idx_support_tickets_category ON support_tickets(category);
CREATE INDEX IF NOT EXISTS idx_support_tickets_priority ON support_tickets(priority);
CREATE INDEX IF NOT EXISTS idx_support_tickets_assigned_admin_id ON support_tickets(assigned_admin_id);
CREATE INDEX IF NOT EXISTS idx_support_tickets_created_at ON support_tickets(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_support_tickets_updated_at ON support_tickets(updated_at DESC);

-- 2) New conversation messages table
CREATE TABLE IF NOT EXISTS support_ticket_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticket_id UUID NOT NULL REFERENCES support_tickets(id) ON DELETE CASCADE,
    sender_id UUID NULL REFERENCES users(id) ON DELETE SET NULL,
    sender_role VARCHAR(20) NOT NULL DEFAULT 'user',
    message TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_support_ticket_messages_ticket_id ON support_ticket_messages(ticket_id);
CREATE INDEX IF NOT EXISTS idx_support_ticket_messages_sender_id ON support_ticket_messages(sender_id);
CREATE INDEX IF NOT EXISTS idx_support_ticket_messages_created_at ON support_ticket_messages(created_at);

-- Copy old first ticket message into new messages if missing.
INSERT INTO support_ticket_messages (ticket_id, sender_id, sender_role, message, created_at)
SELECT st.id, st.user_id, 'user', st.message, st.created_at
FROM support_tickets st
WHERE NOT EXISTS (
    SELECT 1 FROM support_ticket_messages m
    WHERE m.ticket_id = st.id AND m.sender_role = 'user' AND m.message = st.message
);

-- Copy legacy support_ticket_replies when that old table exists.
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'support_ticket_replies') THEN
        INSERT INTO support_ticket_messages (ticket_id, sender_id, sender_role, message, created_at)
        SELECT r.ticket_id, r.user_id,
               CASE WHEN COALESCE(u.role, 'user') = 'admin' THEN 'admin' ELSE 'user' END,
               r.message,
               r.created_at
        FROM support_ticket_replies r
        LEFT JOIN users u ON u.id = r.user_id
        WHERE NOT EXISTS (
            SELECT 1 FROM support_ticket_messages m
            WHERE m.ticket_id = r.ticket_id
              AND COALESCE(m.sender_id::text, '') = COALESCE(r.user_id::text, '')
              AND m.message = r.message
              AND m.created_at = r.created_at
        );
    END IF;
END $$;

-- 3) Attachments
CREATE TABLE IF NOT EXISTS support_ticket_attachments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticket_id UUID NOT NULL REFERENCES support_tickets(id) ON DELETE CASCADE,
    message_id UUID NULL REFERENCES support_ticket_messages(id) ON DELETE SET NULL,
    uploaded_by_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    original_filename VARCHAR(255) NOT NULL,
    stored_filename VARCHAR(255) NOT NULL,
    file_path TEXT NOT NULL,
    content_type VARCHAR(255) NULL,
    size_bytes INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_support_ticket_attachments_ticket_id ON support_ticket_attachments(ticket_id);
CREATE INDEX IF NOT EXISTS idx_support_ticket_attachments_message_id ON support_ticket_attachments(message_id);
CREATE INDEX IF NOT EXISTS idx_support_ticket_attachments_uploaded_by_id ON support_ticket_attachments(uploaded_by_id);
CREATE INDEX IF NOT EXISTS idx_support_ticket_attachments_created_at ON support_ticket_attachments(created_at);

-- 4) Notifications compatibility. Existing table in your project already has metadata JSON.
CREATE TABLE IF NOT EXISTS notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    metadata JSONB NULL,
    entity_type VARCHAR(50) NULL,
    entity_id VARCHAR(100) NULL,
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE notifications
    ADD COLUMN IF NOT EXISTS metadata JSONB NULL,
    ADD COLUMN IF NOT EXISTS entity_type VARCHAR(50) NULL,
    ADD COLUMN IF NOT EXISTS entity_id VARCHAR(100) NULL,
    ADD COLUMN IF NOT EXISTS read_at TIMESTAMPTZ NULL,
    ADD COLUMN IF NOT EXISTS is_read BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON notifications(user_id);
CREATE INDEX IF NOT EXISTS idx_notifications_is_read ON notifications(is_read);
CREATE INDEX IF NOT EXISTS idx_notifications_created_at ON notifications(created_at DESC);
