# Live Candle Latency Fix — 2026-08-30

- MT5 Agent fetches the current bar too (`start_pos=0` path).
- API decides whether a candle is closed using open time + timeframe + grace.
- Live runner scheduler scan defaults to 1 second.
- MT5 Agent command polling defaults to 1 second; heartbeat remains 5 seconds.
- Snapshot exposes candle OPEN time, calculated close time, and first-ingestion latency.

For M5, a candle with open time 20:05 closes at 20:10. Seeing `20:05` as the latest candle time at 20:10 is normal because `candle_time` is the bar OPEN timestamp.
