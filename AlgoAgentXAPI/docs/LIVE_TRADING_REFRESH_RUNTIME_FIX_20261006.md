# AlgoAgentX Live Trading Refresh + Runtime Regression Fix

Date: 06-Oct-2026

## Root causes fixed

1. `POST /api/v1/live/deployments/{id}/refresh-candles` referenced `Strategy` without importing the model, causing `NameError: name 'Strategy' is not defined`.
2. The previous parity patch hard-coded runtime contracts by strategy class. That could reject or overwrite otherwise valid user settings (RR, SL mode, partial exit, etc.).
3. Live Settings built runtime compatibility data with `exit_on_opposite_signal: true` even when the desired platform default was OFF.
4. Backend/Admin/Backtest shared defaults also had Opposite Signal Exit ON.
5. Initial live market bootstrap used only 300 bars (~299 closed M5 bars after excluding the forming candle).

## Final behavior

- `Strategy` is imported correctly in `live_deployments.py`; Refresh Candles no longer crashes for this reason.
- Runtime values are deployment/preset-driven. No V1.37/V3.5 name-based RR/SL/partial-exit forcing remains.
- Exit On Opposite Signal defaults to OFF in backend runtime defaults, Admin strategy defaults, shared frontend runtime defaults, Backtest defaults and Live Settings runtime payload.
- Universal live history default is 20,000 closed bars for every strategy.
- Per-strategy override remains optional through `live_history_bars`, `required_history_bars`, `LIVE_HISTORY_BARS`, or `REQUIRED_HISTORY_BARS`, capped at 100,000.
- Initial market bootstrap is 1,000 bars (normally ~999 closed bars if the latest bar is still forming).
- Refresh/Dry-run strategy warm-up backfills the universal 20,000-bar history using paged broker history.
- Broker history warm-up retries up to 3 times before returning a clear incomplete-history result.
- Explicit `LIVE_RUNTIME_CONTRACT` is still supported only if a future strategy deliberately declares one; no contract is inferred merely from class/name.

## Validation

Targeted regression suite: 38 tests passed.

Covered areas include:
- universal strategy-history profile
- no implicit runtime contract forcing
- dynamic strategy registry
- copy-trading position isolation
- copy-trading primary regression
- copy symbol resolution
- partial-exit management
- runtime partial-exit config
- optional live safety limits

Python compile checks passed for backend/strategies/MT5 agent.

## Deployment

Replace the project, then rebuild:

```bash
docker compose --env-file .env.prod -f docker-compose.yml up -d --build
```

Create a fresh deployment for clean validation.

Expected initial candle snapshot after worker bootstrap: roughly 999 closed bars (depending on whether a candle is forming).

Click **Refresh Candles**. It should no longer raise the `Strategy` NameError and should backfill toward 20,000 closed bars.

Then run **Full Dry Test**.

Opposite Signal Exit should resolve OFF by default. Other settings (RR, SL mode, partial exit, BE/trailing, max positions) should follow the strategy preset/deployment settings instead of being forcibly rewritten by strategy class.
