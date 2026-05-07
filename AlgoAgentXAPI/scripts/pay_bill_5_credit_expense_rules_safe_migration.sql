-- PAY-BILL-5: Credit Expense Rules Admin
-- Safe to run multiple times in DBeaver.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS billing_credit_expense_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    operation_type TEXT NOT NULL DEFAULT 'BACKTEST',
    market TEXT NULL,
    instrument_symbol TEXT NULL,
    timeframe TEXT NULL,
    base_credits INTEGER NOT NULL DEFAULT 1,
    per_1000_candles_credits NUMERIC(12, 4) NOT NULL DEFAULT 1,
    min_credits INTEGER NOT NULL DEFAULT 1,
    max_credits INTEGER NULL,
    advanced_filter_multiplier NUMERIC(12, 4) NOT NULL DEFAULT 1,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    priority INTEGER NOT NULL DEFAULT 100,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT billing_credit_expense_rules_operation_type_chk CHECK (operation_type IN ('BACKTEST', 'AI_SCREENER', 'LIVE_DEPLOYMENT', 'OTHER')),
    CONSTRAINT billing_credit_expense_rules_market_chk CHECK (market IS NULL OR market IN ('FOREX', 'INDIAN', 'CRYPTO', 'ALL')),
    CONSTRAINT billing_credit_expense_rules_base_chk CHECK (base_credits >= 0),
    CONSTRAINT billing_credit_expense_rules_per_candles_chk CHECK (per_1000_candles_credits >= 0),
    CONSTRAINT billing_credit_expense_rules_min_chk CHECK (min_credits >= 0),
    CONSTRAINT billing_credit_expense_rules_max_chk CHECK (max_credits IS NULL OR max_credits >= min_credits),
    CONSTRAINT billing_credit_expense_rules_filter_multiplier_chk CHECK (advanced_filter_multiplier > 0)
);

CREATE INDEX IF NOT EXISTS idx_billing_credit_rules_match
    ON billing_credit_expense_rules (operation_type, is_active, priority, market, instrument_symbol, timeframe);

INSERT INTO billing_credit_expense_rules (
    name, operation_type, market, instrument_symbol, timeframe,
    base_credits, per_1000_candles_credits, min_credits, max_credits,
    advanced_filter_multiplier, is_active, priority
)
SELECT
    'Default Backtest Candle Rule', 'BACKTEST', 'ALL', NULL, NULL,
    1, 1, 1, NULL, 1, TRUE, 1000
WHERE NOT EXISTS (
    SELECT 1 FROM billing_credit_expense_rules
    WHERE operation_type = 'BACKTEST' AND market = 'ALL' AND instrument_symbol IS NULL AND timeframe IS NULL
);
