-- Align billing-related foreign key columns with UUID user ids.
-- Run this only if your database still has VARCHAR user_id columns in the billing tables.
-- Safe for PostgreSQL when the values are already UUID strings.

ALTER TABLE user_credits
    ALTER COLUMN user_id TYPE UUID USING NULLIF(user_id::text, '')::uuid;

ALTER TABLE payments
    ALTER COLUMN user_id TYPE UUID USING NULLIF(user_id::text, '')::uuid;

ALTER TABLE user_subscriptions
    ALTER COLUMN user_id TYPE UUID USING NULLIF(user_id::text, '')::uuid;

ALTER TABLE billing_documents
    ALTER COLUMN user_id TYPE UUID USING NULLIF(user_id::text, '')::uuid;

-- Optional but recommended if billing_orders.user_id should also track users.id as UUID.
-- Uncomment only if your billing_orders table currently stores UUID strings and you want strict typing.
-- ALTER TABLE billing_orders
--     ALTER COLUMN user_id TYPE UUID USING NULLIF(user_id::text, '')::uuid;
