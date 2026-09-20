# Fast candle fetch + immediate strategy execution

Live runner policy:

- Timeframe close is the reference boundary.
- First broker candle fetch starts approximately 1 second after close.
- If the exact just-closed candle is not available, broker refresh retries every 1 second.
- Up to 20 active broker refresh attempts are allowed for that candle, covering the observed 10–15 second cTrader publication delay without adding an artificial strategy wait.
- The local candle table is checked before and after every broker refresh.
- As soon as the exact expected closed candle is stored, the strategy runs immediately.
- There is no separate +10s or +15s strategy grace period.
- Once the candle is processed, `last_processed_candle_time` prevents that candle from being processed again.
- Existing runner transaction locking and signal/order idempotency remain in place to prevent duplicate orders.
- `next_run_at` is scheduled for the next timeframe close +1 second.

Example M5:

01:20:00 candle closes
01:20:01 first fetch
01:20:02 retry if missing
01:20:03 retry if missing
...
01:20:11 candle becomes available
01:20:11 strategy runs immediately
next scheduled boundary: 01:25:01
