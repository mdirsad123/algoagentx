-- PAY-BILL-5A Credit Top-up Pack Master safe migration
-- Safe to run multiple times in DBeaver.

BEGIN;

CREATE TABLE IF NOT EXISTS billing_credit_topup_packs (
    id UUID PRIMARY KEY,
    code TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    credits INTEGER NOT NULL,
    price_usd NUMERIC(12, 2) NOT NULL,
    bonus_credits INTEGER NOT NULL DEFAULT 0,
    description TEXT NULL,
    is_popular BOOLEAN NOT NULL DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    sort_order INTEGER NOT NULL DEFAULT 100,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_billing_credit_topup_packs_credits CHECK (credits > 0),
    CONSTRAINT chk_billing_credit_topup_packs_price CHECK (price_usd > 0),
    CONSTRAINT chk_billing_credit_topup_packs_bonus CHECK (bonus_credits >= 0)
);

ALTER TABLE billing_credit_topup_packs
    ADD COLUMN IF NOT EXISTS bonus_credits INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS description TEXT NULL,
    ADD COLUMN IF NOT EXISTS is_popular BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS sort_order INTEGER NOT NULL DEFAULT 100,
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

CREATE OR REPLACE FUNCTION set_billing_credit_topup_packs_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_billing_credit_topup_packs_updated_at ON billing_credit_topup_packs;
CREATE TRIGGER trg_billing_credit_topup_packs_updated_at
BEFORE UPDATE ON billing_credit_topup_packs
FOR EACH ROW
EXECUTE FUNCTION set_billing_credit_topup_packs_updated_at();

INSERT INTO billing_credit_topup_packs (id, code, title, credits, price_usd, bonus_credits, description, is_popular, is_active, sort_order)
VALUES
    ('11111111-1111-4111-8111-111111111111', 'STARTER_10', '10 Credits', 10, 1.00, 0, 'Starter pack for quick checks', FALSE, TRUE, 10),
    ('22222222-2222-4222-8222-222222222222', 'BASIC_250', '250 Credits', 250, 25.00, 0, 'Basic top-up pack', FALSE, TRUE, 20),
    ('33333333-3333-4333-8333-333333333333', 'POPULAR_500', '500 Credits', 500, 45.00, 0, 'Best value for active traders', TRUE, TRUE, 30),
    ('44444444-4444-4444-8444-444444444444', 'PRO_1000', '1000 Credits', 1000, 90.00, 0, 'Pro pack for frequent backtesting', FALSE, TRUE, 40)
ON CONFLICT (code) DO NOTHING;

CREATE INDEX IF NOT EXISTS idx_billing_credit_topup_packs_active_sort
    ON billing_credit_topup_packs (is_active, sort_order, code);

CREATE INDEX IF NOT EXISTS idx_billing_credit_topup_packs_code_upper
    ON billing_credit_topup_packs (UPPER(code));

COMMIT;
