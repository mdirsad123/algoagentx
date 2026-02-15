-- Fix users table schema by adding missing columns
ALTER TABLE users ADD COLUMN IF NOT EXISTS fullname VARCHAR;
ALTER TABLE users ADD COLUMN IF NOT EXISTS mobile VARCHAR;

-- Verify the columns were added
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'users' 
AND column_name IN ('fullname', 'mobile');