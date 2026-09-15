-- AlgoAgentX backtest market-data index check.
-- Run the SELECT first. Only run CREATE INDEX if the index is missing.

SELECT
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'public'
  AND tablename = 'market_data'
ORDER BY indexname;

-- Expected performance index:
-- idx_market_data_instrument_tf_ts (instrument_id, timeframe, timestamp)

-- Safe online creation for PostgreSQL if it is missing.
-- IMPORTANT: CREATE INDEX CONCURRENTLY cannot run inside BEGIN/COMMIT.
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_market_data_instrument_tf_ts
ON market_data (instrument_id, timeframe, timestamp);
