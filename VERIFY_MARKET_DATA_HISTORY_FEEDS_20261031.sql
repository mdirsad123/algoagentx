-- READ-ONLY: run in pgAdmin / psql on your AlgoAgentX local-prod database.
-- The V2 patch introduces NO migrations or table/column changes.
SELECT provider, broker_symbol, timeframe, enabled, is_primary,
       last_status, last_error, initial_start, checkpoint, last_synced_at
FROM market_data_sync_configs ORDER BY updated_at DESC LIMIT 40;

SELECT c.provider, c.broker_symbol, c.timeframe,
       count(m.timestamp) AS stored_source_candles,
       min(m.timestamp) AS earliest_source_candle,
       max(m.timestamp) AS latest_source_candle
FROM market_data_sync_configs c
LEFT JOIN market_data_feed_candles m ON m.feed_id = c.id
GROUP BY c.id, c.provider, c.broker_symbol, c.timeframe
ORDER BY c.broker_symbol, c.timeframe;

SELECT status, error, started_at, finished_at,
       fetched, inserted, skipped, invalid, last_before, last_after
FROM market_data_sync_runs
ORDER BY created_at DESC LIMIT 20;
