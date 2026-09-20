# Auto Runner boundary / no-auto-pause fix

- M5 boundaries remain aligned to 08:10, 08:15, 08:20, 08:25, etc.
- Auto Runner first checks at approximately boundary + 1 second.
- If the broker has not published the newly closed candle, it retries in <= 5 seconds.
- As soon as the new closed candle is stored, the strategy executes immediately.
- `last_processed_candle_time` prevents duplicate execution on the same candle.
- Generic runner/network/candle exceptions no longer change deployment status to PAUSED.
- Repeated errors remain RUNNING and retry with a bounded 5–30 second backoff.
- Explicit Pause/Stop, kill switch, and funded-risk safety controls are unchanged.
