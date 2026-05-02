-- BF-1 optional safety index for fast backtest preview/run market-data lookup.
-- Safe to run multiple times in PostgreSQL.
CREATE INDEX IF NOT EXISTS idx_market_data_lookup
ON market_data (instrument_id, timeframe, timestamp);
