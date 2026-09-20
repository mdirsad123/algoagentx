# Auto Runner: 10 x 1-second candle retry

- Scheduler scans RUNNING + Auto Runner deployments every 1 second.
- At each timeframe boundary it expects the exact just-closed candle.
- If missing, it performs at most 10 broker refresh attempts, one per second.
- If the candle arrives on attempt 1-10, the strategy runs immediately.
- After attempt 10, active broker refresh is capped to avoid hammering cTrader; the local candle DB is still checked every second, so another ingestion path can still trigger the strategy as soon as the candle appears.
- Retry state is keyed by deployment + candle-open timestamp and resets at the next timeframe boundary.
- Duplicate orders remain blocked by: `last_processed_candle_time`, per-deployment PostgreSQL transaction lock, signal DB idempotency, and broker client-order idempotency keys.
