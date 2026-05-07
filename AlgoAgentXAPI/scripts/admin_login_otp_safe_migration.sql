-- AUTH-ADMIN-OTP-1: Admin Email OTP Login Security Upgrade
-- Safe/idempotent migration. Run in DBeaver against your AlgoAgentX PostgreSQL database.

BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS admin_login_otps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    otp_hash TEXT NOT NULL,
    purpose TEXT NOT NULL DEFAULT 'ADMIN_LOGIN',
    attempts INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 5,
    expires_at TIMESTAMPTZ NOT NULL,
    used_at TIMESTAMPTZ NULL,
    resend_available_at TIMESTAMPTZ NULL,
    last_sent_at TIMESTAMPTZ NULL,
    ip_address TEXT NULL,
    user_agent TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE admin_login_otps
    ADD COLUMN IF NOT EXISTS purpose TEXT NOT NULL DEFAULT 'ADMIN_LOGIN',
    ADD COLUMN IF NOT EXISTS attempts INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS max_attempts INTEGER NOT NULL DEFAULT 5,
    ADD COLUMN IF NOT EXISTS used_at TIMESTAMPTZ NULL,
    ADD COLUMN IF NOT EXISTS resend_available_at TIMESTAMPTZ NULL,
    ADD COLUMN IF NOT EXISTS last_sent_at TIMESTAMPTZ NULL,
    ADD COLUMN IF NOT EXISTS ip_address TEXT NULL,
    ADD COLUMN IF NOT EXISTS user_agent TEXT NULL,
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();

CREATE INDEX IF NOT EXISTS idx_admin_login_otps_user_id ON admin_login_otps(user_id);
CREATE INDEX IF NOT EXISTS idx_admin_login_otps_email ON admin_login_otps(LOWER(email));
CREATE INDEX IF NOT EXISTS idx_admin_login_otps_expires_at ON admin_login_otps(expires_at);
CREATE INDEX IF NOT EXISTS idx_admin_login_otps_unused ON admin_login_otps(user_id, expires_at) WHERE used_at IS NULL;

CREATE OR REPLACE FUNCTION set_admin_login_otps_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_admin_login_otps_updated_at ON admin_login_otps;
CREATE TRIGGER trg_admin_login_otps_updated_at
BEFORE UPDATE ON admin_login_otps
FOR EACH ROW
EXECUTE FUNCTION set_admin_login_otps_updated_at();

COMMIT;
