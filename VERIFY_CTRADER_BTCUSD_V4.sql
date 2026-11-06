-- AlgoAgentX V4: READ-ONLY PostgreSQL verification for cTrader BTCUSD source candles.
-- Safe to run repeatedly; contains SELECT statements only. No schema or data modifications.
-- Query 1: configured cTrader BTCUSD feeds and ACTUAL source candle counts.
SELECT
    c.id AS feed_id,
    i.symbol AS market_master_instrument,
    c.provider,
    c.subaccount_id,
    c.broker_symbol,
    c.timeframe,
    c.last_status,
    c.enabled AS automatic_enabled,
    c.is_primary,
    c.publish_approved,
    COUNT(fc.timestamp) AS saved_source_candles,
    MIN(fc.timestamp) AS earliest_source_candle_utc,
    MAX(fc.timestamp) AS latest_source_candle_utc
FROM market_data_sync_configs AS c
JOIN instruments AS i ON i.id = c.instrument_id
LEFT JOIN market_data_feed_candles AS fc ON fc.feed_id = c.id
WHERE UPPER(c.provider) = 'CTRADER'
  AND UPPER(c.broker_symbol) LIKE 'BTCUSD%'
GROUP BY c.id, i.symbol
ORDER BY c.created_at DESC;

-- Query 2: latest 10 stored cTrader BTCUSD OHLCV candles (all subaccounts are named).
SELECT
    c.id AS feed_id,
    c.subaccount_id,
    c.broker_symbol,
    c.timeframe,
    fc.timestamp AS candle_open_utc,
    fc.timestamp AT TIME ZONE 'Asia/Kolkata' AS candle_open_ist,
    fc.open, fc.high, fc.low, fc.close, fc.volume
FROM market_data_feed_candles AS fc
JOIN market_data_sync_configs AS c ON c.id = fc.feed_id
WHERE UPPER(c.provider) = 'CTRADER'
  AND UPPER(c.broker_symbol) LIKE 'BTCUSD%'
ORDER BY fc.timestamp DESC
LIMIT 10;

-- Query 3: last ten cTrader BTCUSD sync runs; preview/dry_run does NOT insert.
SELECT
    r.created_at,
    r.status,
    r.dry_run,
    r.fetched,
    r.inserted,
    r.updated,
    r.skipped,
    r.invalid,
    r.last_after,
    r.error,
    c.broker_symbol,
    c.timeframe
FROM market_data_sync_runs AS r
JOIN market_data_sync_configs AS c ON c.id = r.feed_id
WHERE UPPER(c.provider) = 'CTRADER'
  AND UPPER(c.broker_symbol) LIKE 'BTCUSD%'
ORDER BY r.created_at DESC
LIMIT 10;

-- Query 4: LEGACY canonical backtest candles for mapped BTCUSD instruments.
-- It is normal for this count to differ from the source count.
SELECT
    c.id AS source_feed_id,
    i.symbol AS market_master_instrument,
    c.timeframe,
    (SELECT COUNT(*) FROM market_data AS m
     WHERE m.instrument_id = c.instrument_id AND m.timeframe = c.timeframe) AS legacy_backtest_candles,
    c.is_primary,
    c.publish_approved
FROM market_data_sync_configs AS c
JOIN instruments AS i ON i.id = c.instrument_id
WHERE UPPER(c.provider) = 'CTRADER'
  AND UPPER(c.broker_symbol) LIKE 'BTCUSD%'
ORDER BY c.created_at DESC;
