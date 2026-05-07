-- AUTH-FIX-2: Forgot Password + Reset Password safe migration
-- Run this once in DBeaver before testing the reset-password flow.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS auth_provider VARCHAR(50) DEFAULT 'local',
    ADD COLUMN IF NOT EXISTS google_sub VARCHAR(255) NULL,
    ADD COLUMN IF NOT EXISTS avatar_url TEXT NULL,
    ADD COLUMN IF NOT EXISTS email_verified BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMPTZ NULL,
    ADD COLUMN IF NOT EXISTS last_login_provider VARCHAR(50) NULL,
    ADD COLUMN IF NOT EXISTS failed_login_count INTEGER NOT NULL DEFAULT 0;

ALTER TABLE users
    ALTER COLUMN password_hash DROP NOT NULL;

UPDATE users SET email = LOWER(TRIM(email)) WHERE email IS NOT NULL AND email <> LOWER(TRIM(email));
UPDATE users SET auth_provider = 'local' WHERE auth_provider IS NULL OR auth_provider = '';
UPDATE users SET email_verified = FALSE WHERE email_verified IS NULL;
UPDATE users SET failed_login_count = 0 WHERE failed_login_count IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_users_google_sub
ON users (google_sub)
WHERE google_sub IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_users_email_lower
ON users (LOWER(email));

CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash TEXT NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    used_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    request_ip TEXT NULL,
    user_agent TEXT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_password_reset_tokens_token_hash
ON password_reset_tokens (token_hash);

CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_user_id
ON password_reset_tokens (user_id);

CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_valid_lookup
ON password_reset_tokens (token_hash, expires_at)
WHERE used_at IS NULL;
