-- Add missing columns to users table
ALTER TABLE users ADD COLUMN IF NOT EXISTS fullname VARCHAR;
ALTER TABLE users ADD COLUMN IF NOT EXISTS mobile VARCHAR;