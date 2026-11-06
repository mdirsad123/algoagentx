-- READ ONLY: run against local PROD DB. No changes to market_data.
SELECT c.id AS feed_id, c.provider, c.broker_symbol, c.timeframe, c.enabled, c.is_primary, c.publish_approved,
       c.is_archived, i.symbol AS market_master_instrument,
       (SELECT count(*) FROM market_data_feed_candles f WHERE f.feed_id = c.id) AS source_candles,
       (SELECT count(*) FROM market_data m WHERE m.instrument_id = c.instrument_id AND m.timeframe = c.timeframe) AS backtest_candles,
       (SELECT max(m.timestamp) FROM market_data m WHERE m.instrument_id = c.instrument_id AND m.timeframe = c.timeframe) AS backtest_latest_utc,
       (SELECT count(*) FROM market_data_canonical_provenance p WHERE p.feed_id = c.id) AS published_from_feed
FROM market_data_sync_configs c JOIN instruments i ON i.id = c.instrument_id
WHERE upper(i.symbol) IN ('BTCUSD', 'XAUUSD')
ORDER BY i.symbol, c.provider, c.broker_symbol;

-- See recent actual canonical timestamps and their provenance, with null = legacy historical candle.
SELECT i.symbol, m.timeframe, m.timestamp, m.open, m.high, m.low, m.close,
       c.provider AS newly_published_provider, c.broker_symbol AS newly_published_symbol
FROM market_data m JOIN instruments i ON i.id = m.instrument_id
LEFT JOIN market_data_canonical_provenance p
  ON p.instrument_id = m.instrument_id AND p.timeframe = m.timeframe AND p.timestamp = m.timestamp
LEFT JOIN market_data_sync_configs c ON c.id = p.feed_id
WHERE upper(i.symbol) IN ('BTCUSD','XAUUSD') AND m.timeframe = '5m'
ORDER BY m.timestamp DESC LIMIT 25;
