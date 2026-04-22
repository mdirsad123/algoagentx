-- Backtest Module Safe Migration (AlgoAgentX)
-- Purpose:
-- 1) Keep IDs type-compatible and avoid UUID/string mismatch in backtest relations
-- 2) Add missing backtest metrics/support columns if absent
-- 3) Add high-value indexes for user/admin history and market-data coverage queries

BEGIN;

-- ---------------------------------------------------------------------
-- 0) Performance metrics quality-of-life columns (safe, optional)
-- ---------------------------------------------------------------------
ALTER TABLE IF EXISTS performance_metrics
    ADD COLUMN IF NOT EXISTS profit_factor NUMERIC;

ALTER TABLE IF EXISTS performance_metrics
    ADD COLUMN IF NOT EXISTS winning_trades INTEGER;

ALTER TABLE IF EXISTS performance_metrics
    ADD COLUMN IF NOT EXISTS losing_trades INTEGER;

ALTER TABLE IF EXISTS performance_metrics
    ADD COLUMN IF NOT EXISTS status VARCHAR(32) DEFAULT 'completed';

-- ---------------------------------------------------------------------
-- 1) Align child backtest_id columns to VARCHAR(36) to match
--    performance_metrics.id (String(36) in current model).
-- ---------------------------------------------------------------------
DO $$
DECLARE
    _tbl TEXT;
    _dtype TEXT;
BEGIN
    FOR _tbl IN SELECT unnest(ARRAY['trades', 'equity_curve', 'pnl_calendar']) LOOP
        SELECT data_type
          INTO _dtype
          FROM information_schema.columns
         WHERE table_schema = current_schema()
           AND table_name = _tbl
           AND column_name = 'backtest_id'
         LIMIT 1;

        IF _dtype IS NULL THEN
            CONTINUE;
        END IF;

        -- Drop common FK names safely (if present)
        EXECUTE format('ALTER TABLE %I DROP CONSTRAINT IF EXISTS %I', _tbl, _tbl || '_backtest_id_fkey');
        EXECUTE format('ALTER TABLE %I DROP CONSTRAINT IF EXISTS backtest_id_fkey', _tbl);

        -- Convert UUID->VARCHAR(36) only when needed
        IF _dtype = 'uuid' THEN
            EXECUTE format(
                'ALTER TABLE %I ALTER COLUMN backtest_id TYPE VARCHAR(36) USING backtest_id::text',
                _tbl
            );
        END IF;

        -- Recreate FK (idempotent-safe)
        BEGIN
            EXECUTE format(
                'ALTER TABLE %I ADD CONSTRAINT %I FOREIGN KEY (backtest_id) REFERENCES performance_metrics(id) ON DELETE CASCADE',
                _tbl,
                _tbl || '_backtest_id_fkey'
            );
        EXCEPTION WHEN duplicate_object THEN
            -- already exists
            NULL;
        END;
    END LOOP;
END $$;

-- metrics.backtest_id should also be string-like
DO $$
DECLARE
    _dtype TEXT;
BEGIN
    SELECT data_type
      INTO _dtype
      FROM information_schema.columns
     WHERE table_schema = current_schema()
       AND table_name = 'metrics'
       AND column_name = 'backtest_id'
     LIMIT 1;

    IF _dtype = 'uuid' THEN
        ALTER TABLE metrics ALTER COLUMN backtest_id TYPE VARCHAR(36) USING backtest_id::text;
    END IF;
END $$;

-- ---------------------------------------------------------------------
-- 2) Indexes for user history / admin review / market data checks
-- ---------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_performance_metrics_user_created_at
    ON performance_metrics (user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_performance_metrics_status_created_at
    ON performance_metrics (status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_performance_metrics_strategy_instrument_tf
    ON performance_metrics (strategy_id, instrument_id, timeframe);

CREATE INDEX IF NOT EXISTS idx_performance_metrics_date_range
    ON performance_metrics (start_date, end_date);

CREATE INDEX IF NOT EXISTS idx_job_status_job_type_status_created_at
    ON job_status (job_type, status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_market_data_instrument_timeframe_timestamp
    ON market_data (instrument_id, timeframe, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_trades_backtest_entry_time
    ON trades (backtest_id, entry_time);

CREATE INDEX IF NOT EXISTS idx_equity_curve_backtest_timestamp
    ON equity_curve (backtest_id, timestamp);

CREATE INDEX IF NOT EXISTS idx_pnl_calendar_backtest_date
    ON pnl_calendar (backtest_id, date);

COMMIT;
