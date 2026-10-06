SELECT
    timestamp,
    open,
    high,
    low,
    close,
    volume
FROM market_data
WHERE symbol = 'XAUUSD'
  AND timeframe = '5m'
  AND timestamp >= '2026-09-25 00:00:00'
  AND timestamp <  '2026-10-04 00:00:00'
ORDER BY timestamp ASC;