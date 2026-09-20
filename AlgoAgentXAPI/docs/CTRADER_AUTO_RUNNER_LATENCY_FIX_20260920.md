# cTrader Auto Runner / Candle Latency Fix — 2026-09-20

## Fixed

- Removed the session-level PostgreSQL advisory-lock pattern from the auto-runner scheduler.
  That pattern could leave a lock attached to a pooled PostgreSQL connection after commit,
  causing Auto Runner to appear ON while future scheduler scans were skipped.
- Added atomic per-deployment scheduler leasing through `next_run_at`, so multiple API
  workers cannot normally claim the same due deployment and a crashed worker recovers
  automatically after the short lease.
- Fixed next-candle scheduling semantics. `LiveMarketCandle.candle_time` is candle OPEN
  time, so after processing an M5 candle opened at 19:10 the next strategy wake-up is
  19:20:03, not 19:15:03.
- Auto Runner now refreshes only a small recent candle window (12 bars) before a strategy
  cycle instead of downloading 300 historical bars each retry.
- Removed the duplicate second 300-bar refresh inside the strategy runner when the
  Auto Runner already refreshed candles.
- Missing broker candle publication now retries every <=3 seconds rather than waiting
  up to 10 seconds.
- If a manual Run Strategy Once overlaps Auto Runner and owns the runner lock, Auto
  Runner no longer marks that candle as processed. It schedules a short retry instead.
- Deployment detail UI polling reduced from 10 seconds to 5 seconds so candle/runner
  state is visible sooner.

## Expected M5 flow

Candle 19:15 opens
→ 19:20:03 Auto Runner wakes
→ fetch latest 12 broker bars
→ if 19:15 bar is published, store it and run strategy immediately
→ otherwise retry approximately every 3 seconds
→ BUY/SELL/HOLD generated from the new closed candle
→ when Auto Trade is enabled, eligible BUY/SELL executes automatically

Manual `Run Strategy Once` remains available for diagnostics but is not required for
normal automatic operation.
