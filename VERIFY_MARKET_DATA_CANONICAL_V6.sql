-- Read-only. Run in the SAME local PROD PostgreSQL database used by the API.
-- No changes are made. If a schema table is missing, apply the existing V5
-- market-data migration BEFORE trying the V6 canonical publishing action.
BEGIN READ ONLY;
SET LOCAL TIME ZONE 'UTC';

SELECT current_database() AS db_name, current_schema() AS schema_name,
       current_setting('TimeZone') AS session_timezone,
       to_regclass('public.market_data_canonical_provenance') AS provenance_table;

SELECT table_name, column_name, data_type, numeric_precision, numeric_scale
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name IN ('market_data', 'market_data_feed_candles')
  AND column_name IN ('timestamp','open','high','low','close')
ORDER BY table_name, column_name;

-- Actual stored source candles versus the BACKTEST table for each cTrader feed.
SELECT c.id AS feed_id, i.symbol AS market_master_symbol, c.provider,
       c.broker_symbol, c.timeframe, c.is_primary, c.publish_approved,
       c.last_status,
       (SELECT count(*) FROM market_data_feed_candles fc WHERE fc.feed_id = c.id) AS source_rows,
       (SELECT max(fc.timestamp) FROM market_data_feed_candles fc WHERE fc.feed_id = c.id) AS source_latest_utc,
       (SELECT count(*) FROM market_data m WHERE m.instrument_id = c.instrument_id
         AND m.timeframe = c.timeframe) AS canonical_rows,
       (SELECT max(m.timestamp) FROM market_data m WHERE m.instrument_id = c.instrument_id
         AND m.timeframe = c.timeframe) AS canonical_latest_utc
FROM market_data_sync_configs c
JOIN instruments i ON i.id = c.instrument_id
WHERE upper(i.symbol) IN ('BTCUSD','XAUUSD')
  AND c.timeframe = '5m'
ORDER BY i.symbol, c.is_primary DESC, c.created_at DESC;

-- What the API's Publish Missing preview SHOULD report, for BTCUSD cTrader.
SELECT c.id AS feed_id, c.broker_symbol,
       count(fc.timestamp) AS source_rows,
       count(m.timestamp) AS existing_canonical_overlaps,
       count(fc.timestamp) - count(m.timestamp) AS source_rows_not_yet_in_backtest
FROM market_data_sync_configs c
JOIN instruments i ON i.id = c.instrument_id
JOIN market_data_feed_candles fc ON fc.feed_id = c.id
LEFT JOIN market_data m ON m.instrument_id = c.instrument_id
   AND m.timeframe = c.timeframe AND m.timestamp = fc.timestamp
WHERE upper(i.symbol) = 'BTCUSD' AND c.timeframe = '5m'
  AND c.provider = 'CTRADER'
GROUP BY c.id, c.broker_symbol ORDER BY source_rows DESC;

-- Last 10 canonical BTCUSD M5 bars with a FIVE-decimal view (no data update).
SELECT m.timestamp AS utc_open_time,
       round(m.open, 5)::numeric(65,5) AS open_5dp,
       round(m.high, 5)::numeric(65,5) AS high_5dp,
       round(m.low, 5)::numeric(65,5) AS low_5dp,
       round(m.close, 5)::numeric(65,5) AS close_5dp,
       m.volume
FROM market_data m JOIN instruments i ON i.id = m.instrument_id
WHERE upper(i.symbol) = 'BTCUSD' AND m.timeframe = '5m'
ORDER BY m.timestamp DESC LIMIT 10;

-- Has publication actually run? Latest audit rows for any cTrader feed.
SELECT r.feed_id, c.broker_symbol, r.status, r.created_at,
       r.fetched AS source_rows_reviewed, r.inserted AS canonical_rows_inserted,
       r.updated AS canonical_rows_added_by_incremental_sync,
       r.last_after, r.error
FROM market_data_sync_runs r
JOIN market_data_sync_configs c ON c.id=r.feed_id
WHERE c.provider='CTRADER'
ORDER BY r.created_at DESC LIMIT 20;
COMMIT;
