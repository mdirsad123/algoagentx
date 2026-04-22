-- Safe migration for DB-driven backtest pricing rules
-- PostgreSQL-compatible, additive only.

BEGIN;

CREATE TABLE IF NOT EXISTS backtest_pricing_rule_sets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(120) NOT NULL,
    version VARCHAR(40) NOT NULL DEFAULT 'v1',
    description TEXT NULL,

    is_active BOOLEAN NOT NULL DEFAULT FALSE,
    is_locked BOOLEAN NOT NULL DEFAULT FALSE,

    base_cost NUMERIC(10,2) NOT NULL DEFAULT 2,
    range_days_step INTEGER NOT NULL DEFAULT 30,
    min_credit_charge INTEGER NOT NULL DEFAULT 1,
    max_credit_charge INTEGER NULL,

    date_range_buckets JSONB NOT NULL,
    timeframe_multipliers JSONB NOT NULL,

    strategy_complexity_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    strategy_complexity_step NUMERIC(10,4) NOT NULL DEFAULT 0,
    strategy_complexity_cap NUMERIC(10,4) NOT NULL DEFAULT 0,
    plan_discounts JSONB NULL,

    created_by VARCHAR(36) NULL,
    updated_by VARCHAR(36) NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_backtest_pricing_rule_sets_active
    ON backtest_pricing_rule_sets (is_active, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_backtest_pricing_rule_sets_version
    ON backtest_pricing_rule_sets (version);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM backtest_pricing_rule_sets
        WHERE is_active = TRUE
    ) THEN
        INSERT INTO backtest_pricing_rule_sets (
            name,
            version,
            description,
            is_active,
            is_locked,
            base_cost,
            range_days_step,
            min_credit_charge,
            max_credit_charge,
            date_range_buckets,
            timeframe_multipliers,
            strategy_complexity_enabled,
            strategy_complexity_step,
            strategy_complexity_cap,
            plan_discounts
        ) VALUES (
            'Default Backtest Pricing',
            'v1',
            'Seeded default rule set for backtest credit pricing',
            TRUE,
            FALSE,
            2.00,
            30,
            1,
            NULL,
            '[
               {"max_days": 30, "multiplier": 1.0},
               {"max_days": 90, "multiplier": 1.35},
               {"max_days": 365, "multiplier": 1.9},
               {"max_days": null, "multiplier": 2.6}
             ]'::jsonb,
            '[
               {"max_minutes": 15, "multiplier": 1.6},
               {"max_minutes": 60, "multiplier": 1.3},
               {"max_minutes": 240, "multiplier": 1.05},
               {"max_minutes": null, "multiplier": 0.85}
             ]'::jsonb,
            FALSE,
            0,
            0,
            '{}'::jsonb
        );
    END IF;
END
$$;

COMMIT;
