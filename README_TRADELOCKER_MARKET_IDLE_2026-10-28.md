# AlgoAgentX — TradeLocker idle-session polling & runner throttle

**Date: 2026-10-28 | Scope: Broker-data REST polling / idle scheduler only.**

## Confirmed issue (user's api_logs(7).txt)

From 2026-10-27 21:05 to 21:31 UTC, the TradeLocker candle worker repeatedly returned `ready=False`, with `stored=2026-10-27 20:55:00+00:00`. Across the supplied excerpt there were **252 TradeLocker history GET requests** and **253 `ready=False` log records**, with no `ready=True` and no newly generated candles. Broker HTTP 200 simply means the request succeeded, not that a new closed candle was published.

The market break shown in the UI at **02:30 IST** is consistent with the candle OPEN time **02:25 IST**; that candle closed at **02:30 IST**. The worker was then asking for new candles that did not exist yet.

## What changed

1. When a new M5 close is expected, one TradeLocker REST fetch is made at the candle boundary +2s. If the just-closed candle is not immediately published, there are **at most 2 quick retries 8s apart** (configurable). If still absent, the worker backs off to the next M5 close +2s. Once the market is inactive for longer, this means **one TradeLocker history GET every 5 minutes**, including weekend/session breaks. No 02:30/03:30 hours or DST offsets are hard-coded. The time alignment is derived from the *deployment timeframe*, not always M5.
2. After a candle is stored, the next broker fetch is scheduled for the **next expected close**. There is no unnecessary successful `already_stored` scan on every second.
3. Deployment discovery is cached for 15 seconds; the worker sleeps until its next due scan/poll, rather than spinning every second. No data is fabricated or lost intentionally. Historical gap repair remains separate, rate limited to once per 5 minutes.
4. Dedicated TradeLocker runner avoids calling full strategy generation and avoids writing a new `AUTO_RUNNER_WAKEUP` database row for missing candles. It does a few DB-only checks, then DB-only checks no more frequently than ~30 seconds during prolonged no-data periods. A late candle can therefore take **up to 30s extra to notice** while idle; the candle worker normally captures active-session candles in the first 2 retries. The scheduler still has a lightweight heartbeat and may wake to inspect state.
5. When candle data resumes, existing hybrid/generic incremental selection, 80K warmup, price/SL/TP, order and safety logic are unchanged. **No Auto Trade UI changes or forced MONITOR_ONLY overrides.**

### Known session-gap limitation (not hidden)

The existing sequential catch-up guard treats any missing M5 timestamp as a potentially missing trade candle. This new polling patch **does not automatically certify a long weekend or broker maintenance gap as a safe session closure**. After the market reopens, `RUNNER_CANDLE_BACKFILL_WAIT` / `TRADELOCKER_GAP_BEYOND_LOOKBACK` may still require a verified session calendar / broker-proof policy before advancing a cursor. NEVER fill closed-market minutes with zero-volume synthetic candles. The new patch fixes wasteful *polling*, not that separate session-gap verification issue.

## Windows Docker redeploy

1. Back up the current project and `.env.prod`. Merge ZIP into `D:\Stock_market\algoagentx`. Do not overwrite your existing `.env.prod`; this ZIP intentionally does **not** contain that file.
2. In `.env.prod`, **add the settings from `MARKET_IDLE_ENV_ADDITIONS_2026-10-28.txt`**. Keep all current strategy source SHA, 80K warmup, incremental adapters, Auto Trade, order config and broker credentials as they are. Remove duplicates of the listed keys if necessary.
3. Wait for any strategy execution to finish and avoid recreating containers during an in-progress order submission. Rebuild **two** affected workers only:

```powershell
cd D:\Stock_market\algoagentx
docker compose --env-file .env.prod config --quiet
docker compose --env-file .env.prod up -d --no-deps --build --force-recreate live_tradelocker_candle_worker live_legacy_runner_worker
```

4. Confirm the flags inside each container and inspect logs:

```powershell
docker compose --env-file .env.prod exec -T live_tradelocker_candle_worker python -c "from app.core.config import settings as s;print('BOUNDARY=',s.live_tradelocker_boundary_poll_enabled,'FAST_RETRIES=',s.live_tradelocker_fast_empty_retries,'RETRY_SECONDS=',s.live_tradelocker_empty_retry_seconds)"
docker compose --env-file .env.prod exec -T live_legacy_runner_worker python -c "from app.core.config import settings as s;print('RUNNER_IDLE=',s.live_runner_dedicated_candle_idle_enabled,'MAX_DB_IDLE_S=',s.live_runner_dedicated_candle_max_idle_probe_seconds,'RUNNER_SCAN=',s.live_runner_interval_seconds)"
docker compose --env-file .env.prod logs -f --tail=100 live_tradelocker_candle_worker live_legacy_runner_worker
```

### Expected logs

During market break/weekend:

```
TradeLocker candle fetch ... ready=False
TRADELOCKER_NO_NEW_CANDLE_BACKOFF ... next_poll_in_s=...
RUNNER_NO_NEW_CANDLE_IDLE ... next_db_probe_at=...
```

After the initial 2 quick retries, TradeLocker REST history calls should be approx 5 minutes apart for M5; not once every 5 seconds. When market resumes:

```
TradeLocker candle fetch ... ready=True
RUNNER_DISPATCH ...
RUNNER_INCREMENTAL_DONE ...
RUNNER_GENERATE_COMPLETE ... mode=RETAINED_INCREMENTAL
```

If the cursor is blocked by a real missing bar or unverified session gap, the existing guard shows `RUNNER_CANDLE_BACKFILL_WAIT`. This is a separate correctness issue, not evidence that the new REST backoff is failing. No real connected TradeLocker/DB execution was available to test here.

## Rollback

Set `LIVE_TRADELOCKER_BOUNDARY_POLL_ENABLED=false` and `LIVE_RUNNER_DEDICATED_CANDLE_IDLE_ENABLED=false` and recreate the two idle workers. This restores old frequent retry behavior without touching strategy source, database or positions. For the exact prior release, restore its source from your local backup. Note that `LIVE_RUNNER_INTERVAL_SECONDS=5` is independently configurable.

## Offline checks

32 focused tests passed; Python syntax compilation passed. Tested M5, M1, M15, weekend and UTC boundary alignment. The full broker-integrated end-to-end and live order routing tests were not run.
