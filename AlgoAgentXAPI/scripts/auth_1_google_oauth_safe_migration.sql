-- Phase AUTH-1 — Backend Google OAuth Foundation
-- Safe/idempotent migration for AlgoAgentX users table.
-- Run manually in DBeaver before enabling GOOGLE_AUTH_ENABLED=true.

BEGIN;

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS auth_provider VARCHAR(50) DEFAULT 'local',
    ADD COLUMN IF NOT EXISTS google_sub VARCHAR(255) NULL,
    ADD COLUMN IF NOT EXISTS avatar_url TEXT NULL,
    ADD COLUMN IF NOT EXISTS email_verified BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMPTZ NULL;

-- OAuth-created users do not have a local password.
ALTER TABLE users
    ALTER COLUMN password_hash DROP NOT NULL;

-- Backfill existing local users safely.
UPDATE users
SET auth_provider = 'local'
WHERE auth_provider IS NULL;

UPDATE users
SET email_verified = FALSE
WHERE email_verified IS NULL;

ALTER TABLE users
    ALTER COLUMN auth_provider SET DEFAULT 'local',
    ALTER COLUMN email_verified SET DEFAULT FALSE;

CREATE UNIQUE INDEX IF NOT EXISTS idx_users_google_sub
ON users (google_sub)
WHERE google_sub IS NOT NULL;

COMMIT;
