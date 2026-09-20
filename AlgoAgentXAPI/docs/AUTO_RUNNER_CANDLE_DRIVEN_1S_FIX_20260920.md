# Candle-driven Auto Runner — 1 second retry

The Auto Runner no longer trusts `next_run_at` as the execution gate.

For each RUNNING deployment with Auto Runner enabled:

1. The scheduler scans once per second.
2. It computes the exact candle that should already be closed from wall-clock time.
   Example M5 at 21:00:01 => expected candle OPEN is 20:55:00.
3. If `last_processed_candle_time` already covers that candle, it does nothing.
4. If not, it first checks the local candle table.
5. If the candle is already stored, the strategy runs immediately.
6. If it is missing, the runner fetches a small 12-bar broker window.
7. If still missing, it retries one second later.
8. Once processed, idempotency prevents the same candle from executing twice.

This removes 30–120 second drift caused by stale `next_run_at` or scheduler lease state.
`next_run_at` is retained only as UI/diagnostic information.
