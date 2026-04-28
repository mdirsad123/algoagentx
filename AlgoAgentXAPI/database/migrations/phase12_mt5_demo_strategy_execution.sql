-- Phase 12: MT5 DEMO strategy execution safety/index migration
-- Run this manually in DBeaver before testing Phase 12.
-- This migration does not enable real-money LIVE trading.

BEGIN;

-- Keep platform safety defaults explicit. LIVE remains disabled.
INSERT INTO platform_trading_settings (
    paper_trading_enabled,
    demo_trading_enabled,
    live_trading_enabled,
    global_kill_switch,
    updated_at
)
SELECT TRUE, TRUE, FALSE, FALSE, NOW()
WHERE NOT EXISTS (SELECT 1 FROM platform_trading_settings);

UPDATE platform_trading_settings
SET live_trading_enabled = FALSE,
    updated_at = NOW()
WHERE live_trading_enabled IS DISTINCT FROM FALSE;

-- Remove duplicate ENGINE signals for the same deployment + candle + signal before adding the guard index.
WITH ranked AS (
    SELECT
        id,
        ROW_NUMBER() OVER (
            PARTITION BY deployment_id, source, signal_type, candle_time
            ORDER BY created_at DESC, id DESC
        ) AS rn
    FROM live_signals
    WHERE source = 'ENGINE'
      AND candle_time IS NOT NULL
)
DELETE FROM live_signals s
USING ranked r
WHERE s.id = r.id
  AND r.rn > 1;

-- Hard guard against duplicate strategy-runner signals on the same closed candle.
CREATE UNIQUE INDEX IF NOT EXISTS ux_live_signals_engine_dep_candle_signal
ON live_signals (deployment_id, source, signal_type, candle_time)
WHERE source = 'ENGINE' AND candle_time IS NOT NULL;

-- Helpful Phase 12 read-path indexes.
CREATE INDEX IF NOT EXISTS idx_live_orders_dep_signal_status
ON live_orders (deployment_id, signal_id, status);

CREATE INDEX IF NOT EXISTS idx_live_trade_logs_dep_event_created
ON live_trade_logs (deployment_id, event_type, created_at DESC);

COMMIT;
