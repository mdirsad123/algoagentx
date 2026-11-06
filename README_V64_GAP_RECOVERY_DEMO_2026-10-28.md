# AlgoAgentX V6.4 — DEMO Monitor Candle Gap Recovery (2026-10-28)

**Status:** tested in offline source/unit tests; *NOT tested against your local live Docker / TradeLocker account*. Experimental monitor-only. It does **not** prove live strategy parity or production order suitability.

## What we found

Log `previous_open=19:40 newest_open=19:50` means an intermediate 19:45 *runner evaluation* was not confirmed; it does not by itself prove 19:45 OHLCV was missing in PostgreSQL. Original dedicated TradeLocker worker returned immediately when the newest candle existed, without checking older holes. Original legacy runner chose newest eligible candle and marked it processed after evaluating, potentially skipping 19:45 even if stored. This patch addresses both, only in explicitly configured DEMO hybrid monitor mode.

**Changes (no modifications to frozen strategy source or TradeLocker order engine):**

1. `live_tradelocker_candle_worker.py`: independent, read-only checks of first pending bar relative to runner cursor; when gap present, fetch at least 36 and at most 120 recent broker candles using existing `refresh_deployment_candles` upsert (every 2 minutes at most). Emits `TRADELOCKER_GAP_BACKFILLED` or `TRADELOCKER_GAP_UNRESOLVED`. No artificial candles. Does not advance last-processed cursor or submit orders.
2. `auto_runner_service.py`: **only when** `LIVE_RUNNER_SEQUENTIAL_CATCHUP_ENABLED=true`, DEMO, `LIVE_V64_HYBRID_ENABLED=true` and `LIVE_V64_HYBRID_MONITOR_ONLY=true`: always dispatch first next M5 candle (oldest unevaluated) rather than newest. Emits `RUNNER_CANDLE_CATCHUP` for backlog; if immediate next M5 open is absent in DB, waits and emits `RUNNER_CANDLE_BACKFILL_WAIT` (max every 30s). Never skips a missing M5 candle or moves cursor on failed evaluation. It won't silently place historical orders because monitor-only suppresses all broker order submissions in this runner.
3. `candle_catchup.py`: UTC and recovery classification helpers.
4. `check_live_candle_gaps_readonly.py`: SELECT-only DB diagnostic.
5. `tests/test_candle_catchup_20261028.py`: nine deterministic tests.
6. `config.py`: two new optional flags **OFF by default**.
7. `WATCH_V64_HYBRID.ps1`: includes runner + candle worker recovery markers.

**Caveat:** TradeLocker may legitimately have no M5 candles during weekends, holidays or market pauses. This patch deliberately does not invent such bars, force-fill them or assume a session closure automatically. It may halt sequential catch-up at a genuine closed-market interval; review the broker data and make an explicit session-boundary recovery decision before enabling unattended automation. It is not a full session-aware broker calendar/replay implementation. Gap older than 120 bars is logged as `TRADELOCKER_GAP_BEYOND_LOOKBACK` rather than blindly fetching huge history repeatedly.

## Setup — Windows PowerShell (local Docker Desktop)

**Safety:** Dashboard Auto Trade OFF. Retain current `.env.prod`, DB volumes, PostgreSQL/Redis, and position/reconciliation workers. Prefer applying when current legacy runner is idle. This patch does not enable any order recovery for skipped historical signals.

From `D:\Stock_market\algoagentx`, back up the folder first. Extract the update ZIP into a temporary directory, then merge the source files over the *same* project root (inspect file diff). Do NOT delete volumes or replace your `.env.prod`.

Keep these settings; important: `LIVE_V64_HYBRID_PARITY_APPROVED=false` while research verification is incomplete:

```ini
LIVE_INCREMENTAL_ENABLED=true
LIVE_V64_HYBRID_ENABLED=true
LIVE_V64_HYBRID_MONITOR_ONLY=true
LIVE_V64_HYBRID_PARITY_APPROVED=false
LIVE_V64_HYBRID_MAX_ADVANCES=48
LIVE_V64_HYBRID_AUTHORIZED_SOURCE_SHA256=c50b77c72656ce76ec69b87cca07254520f88d181545a3ee4c60d161a25b2747
LIVE_RUNNER_SEQUENTIAL_CATCHUP_ENABLED=true
LIVE_TRADELOCKER_GAP_BACKFILL_ENABLED=true
LIVE_RUNNER_STALE_ORDER_GUARD_ENABLED=false
```

That exact active SHA was reported in your logs and is *not* proof by itself of 80K TradeLocker BUY/SELL parity. The existing strict gate still requires the frozen source to match its allowlist. Never change the hash to work around a mismatch.

After confirming the worker is idle / no broker submission is pending:

```powershell
cd D:\Stock_market\algoagentx
docker compose --env-file .env.prod config --quiet
docker compose --env-file .env.prod up -d --no-deps --build --force-recreate live_legacy_runner_worker live_tradelocker_candle_worker

docker compose --env-file .env.prod exec -T live_legacy_runner_worker python -c "from app.core.config import settings as s; print('HYBRID=',s.live_v64_hybrid_enabled,'MONITOR=',s.live_v64_hybrid_monitor_only,'PARITY_APPROVED=',s.live_v64_hybrid_parity_approved,'SEQUENTIAL=',s.live_runner_sequential_catchup_enabled,'BACKFILL=',s.live_tradelocker_gap_backfill_enabled)"

powershell -ExecutionPolicy Bypass -File .\WATCH_V64_HYBRID.ps1
```

**Read-only DB check** (works without running the watcher or restarting anything):

```powershell
docker compose --env-file .env.prod exec -T live_legacy_runner_worker python -m app.tools.check_live_candle_gaps_readonly --deployment-id c6e13e59-a984-4a63-909b-c65d5d7ef114
```

Expected log flow after cold warmup (possibly several minutes initially):

```text
RUNNER_V64_HYBRID_SELECTED ... monitor_only=True
RUNNER_INCREMENTAL_PRIMED ... bars=80000
RUNNER_CANDLE_CATCHUP ... next_open=... pending_bars=...
RUNNER_INCREMENTAL_DONE ...
RUNNER_GENERATE_COMPLETE ... mode=RETAINED_INCREMENTAL
```

When *DB candle* is actually missing:

```text
RUNNER_CANDLE_BACKFILL_WAIT ... missing_open=... cursor_unchanged=true
TRADELOCKER_GAP_BACKFILLED ... recovered_open=...
```

Or, when broker doesn't return the candle:

```text
TRADELOCKER_GAP_UNRESOLVED ... broker_did_not_return_missing_bar=true
```

Do **not** try to hide that error by moving `last_processed_candle_time` forward or inserting a synthetic OHLCV. A genuine broker session gap requires reviewed handling. Don't expect a full-history `strategy_generate` stage to disappear on initial cold warmup or 48-advance rebase.

## Rollback

Set both new flags `LIVE_RUNNER_SEQUENTIAL_CATCHUP_ENABLED=false` and `LIVE_TRADELOCKER_GAP_BACKFILL_ENABLED=false`, then recreate the two workers *only when safe*. Revert the source files to the previous archived version if desired. No migrations, DB resets, redis wipes or destructive actions necessary. Keep Auto Trade OFF while parity is unverified.
