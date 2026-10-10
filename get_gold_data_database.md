SELECT
    timestamp,
    open,
    high,
    low,
    close,
    volume
FROM market_data
WHERE instrument_id  = 3
  AND timeframe = '5m'
  AND timestamp >= '2026-10-01 00:00:00'
  AND timestamp <  '2026-10-10 00:00:00'
ORDER BY timestamp ASC;