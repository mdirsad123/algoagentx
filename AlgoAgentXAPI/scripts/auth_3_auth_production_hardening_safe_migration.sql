-- Phase AUTH-3 — Auth Production Hardening safe migration
-- Run once in DBeaver before restarting the API.

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

ALTER TABLE users
    ALTER COLUMN auth_provider SET DEFAULT 'local',
    ALTER COLUMN email_verified SET DEFAULT FALSE,
    ALTER COLUMN failed_login_count SET DEFAULT 0;

CREATE UNIQUE INDEX IF NOT EXISTS idx_users_google_sub
ON users (google_sub)
WHERE google_sub IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_users_email_lower
ON users (LOWER(email));
