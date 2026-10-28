# AlgoAgentX — Generic Incremental Adapter Registry + DEMO Candle Gap Recovery

**28 October 2026 · Code release: source-level/offline verified, broker integration unverified.**

## What this patch actually implements

- Generic-named adapter selection in `incremental_adapter_registry.py`. Existing frozen V6.4 hash-locked hybrid is the first registered adapter. Its code and parameters are *not* changed. Existing `LIVE_V64_*` environment flags remain supported for rollback.
- Native strategy v1 incremental protocol remains available for other strategies that **actually implement** `start_live_incremental` and `on_closed_candle`. Dynamic DB strategies must have `live_incremental_approved_source_sha256` matching their current DB source, in addition to the existing explicit parity switches. A new SHA alone is never enough to transform `generate()` into an incremental algorithm.
- Per-deployment retained state isolation (existing). Cache holds at most **8** retained strategy instances per worker; eviction now logs `RUNNER_INCREMENTAL_STATE_EVICTED`. More deployments than retained capacity can require cold warmups.
- DEMO TradeLocker M5: optional sequential cursor catch-up works with Auto Trade enabled or disabled. The first missing DB candle triggers `RUNNER_CANDLE_BACKFILL_WAIT`; the independent candle worker refetches recent genuine broker candles. No synthetic OHLCV is inserted. Historical/backlogged decisions update state and can be recorded but **cannot place new broker orders**. The most recently closed eligible candle retains the existing normal DEMO order path.
- Read-only database gap diagnostic is included: `app.tools.check_live_candle_gaps_readonly`.
- New generic `WATCH_INCREMENTAL.ps1`, with old watcher kept for compatibility.

## Critical limitations

1. V6.4's current hybrid is **partially incremental**, not fully incremental V4.31B trendline + V6.4 portfolio gate. On the user's local Docker it previously took ~50–59 seconds per incremental evaluation and periodic 80K cold rebuilds are still necessary. **This patch does not claim faster CPU timings or under-60-second candle-to-order latency.**
2. This environment cannot access the user's live TradeLocker DEMO broker or PostgreSQL. No live broker orders were placed, no exact active 80K TradeLocker BUY/SELL parity was established. **Setting `LIVE_INCREMENTAL_PARITY_APPROVED=true` declares an operator approval; it is not a parity test.**
3. New V6.5, or any unrelated algorithm with a new SHA, needs either (a) a separately verified adapter registered in code, or (b) a genuinely incremental native v1 strategy implementation plus correctly recorded current-source parity approval. **Changing only an environment SHA will NOT accelerate arbitrary strategies.** The generic code framework remains reusable.
4. Sequential M5 backfill treats absent timestamps as gaps. True broker session breaks, maintenance and weekends require a verified calendar or a reviewed recovery action. Without that, catch-up deliberately waits rather than inventing candles or advancing the cursor. Backfills older than 120 bars are surfaced, not automatically fabricated or skipped.
5. Auto Trade ON on the dashboard does not override `LIVE_INCREMENTAL_MONITOR_ONLY=true`, and neither it nor SHA matching proves parity. To *attempt* DEMO hybrid orders, `LIVE_INCREMENTAL_MONITOR_ONLY=false` and `LIVE_INCREMENTAL_PARITY_APPROVED=true` must be set; **do this only with an understood risk that frozen-strategy parity is still unverified.** Historical catch-up orders are always suppressed.
6. No admin UI toggle was added. Strategy publish does not automatically certify or register a new algorithm adapter.

## New generic environment controls

Add these to your existing `D:\Stock_market\algoagentx\.env.prod`, and remove all old `LIVE_V64_HYBRID_*` lines to avoid confusion. No database reset, no source overwrite:

```ini
LIVE_INCREMENTAL_ENABLED=true
LIVE_INCREMENTAL_ADAPTER_ENABLED=true
LIVE_INCREMENTAL_MONITOR_ONLY=true
LIVE_INCREMENTAL_PARITY_APPROVED=false
LIVE_INCREMENTAL_MAX_ADVANCES=48
LIVE_INCREMENTAL_AUTHORIZED_SOURCE_SHA256=c50b77c72656ce76ec69b87cca07254520f88d181545a3ee4c60d161a25b2747
LIVE_RUNNER_SEQUENTIAL_CATCHUP_ENABLED=true
LIVE_TRADELOCKER_GAP_BACKFILL_ENABLED=true
LIVE_RUNNER_STALE_ORDER_GUARD_ENABLED=false
```

The example uses **monitor-only** for independent verification, but it does not disable your dashboard Auto Trade setting. If you explicitly elect to test **DEMO broker orders**, change only these two values after examining parity evidence:

```ini
LIVE_INCREMENTAL_MONITOR_ONLY=false
LIVE_INCREMENTAL_PARITY_APPROVED=true
```

They are *not* interchangeable. Setting `MONITOR_ONLY=true` will suppress orders even if dashboard Auto Trade ON.

> For a new V6.5 strategy, its new SHA is not automatically on the adapter's immutable source allowlist. A new adapter or native incremental methods + per-source verified approval are required. You cannot just edit one SHA and claim exact parity.

## Windows Docker commands

Work in `D:\Stock_market\algoagentx`. Back up your current project and `.env.prod`; merge ZIP source over the same root (no secrets in ZIP). Wait until the workers are not submitting an order or holding an in-progress calculation before recreating them; do not reset DB/Redis/volumes.

```powershell
docker compose --env-file .env.prod config --quiet
docker compose --env-file .env.prod up -d --no-deps --build --force-recreate live_legacy_runner_worker live_tradelocker_candle_worker
docker compose --env-file .env.prod exec -T live_legacy_runner_worker python -c "from app.core.config import settings as s;print('incremental',s.live_incremental_enabled,'registry',s.live_incremental_adapter_enabled,'monitor',s.live_incremental_monitor_only,'parity_declared',s.live_incremental_parity_approved,'sequential',s.live_runner_sequential_catchup_enabled,'backfill',s.live_tradelocker_gap_backfill_enabled)"
powershell -ExecutionPolicy Bypass -File .\WATCH_INCREMENTAL.ps1
```

Read-only gap inspection:

```powershell
docker compose --env-file .env.prod exec -T live_legacy_runner_worker python -m app.tools.check_live_candle_gaps_readonly --deployment-id c6e13e59-a984-4a63-909b-c65d5d7ef114
```

## Expected logs

- `RUNNER_INCREMENTAL_ADAPTER_SELECTED ... adapter=v64_hybrid_v1` → source pin and runtime contract matched.
- `RUNNER_INCREMENTAL_PRIMED ... bars=80000` → successful cold state initialization.
- `RUNNER_INCREMENTAL_DONE` and `RUNNER_GENERATE_COMPLETE ... mode=RETAINED_INCREMENTAL` → next candle incremental evaluation.
- `RUNNER_INCREMENTAL_ADAPTER_FALLBACK ... reason=... mode=FULL_HISTORY` → no qualified adapter; the existing original strategy handles it.
- `RUNNER_CANDLE_CATCHUP` → oldest stored unprocessed candle first; historical order suppressed.
- `RUNNER_CANDLE_BACKFILL_WAIT` then `TRADELOCKER_GAP_BACKFILLED` → collector recovered real missing broker candle.
- `TRADELOCKER_GAP_UNRESOLVED` / `TRADELOCKER_GAP_BEYOND_LOOKBACK` → do not silently skip or fabricate bar.

## Multiple strategies

| Strategy | Path | Source SHA action |
|---|---|---|
| Two deployments of the **same frozen V6.4** | Two separate retained states, same registered adapter | One matching configured SHA |
| New strategy with no incremental methods | Existing **FULL_HISTORY**, potentially slow | A new SHA has no speed effect |
| New strategy with v1 incremental methods | Generic native retained-state engine *only if* approved | Store `live_incremental_approved_source_sha256` equal to current DB code SHA; plus `live_incremental_enabled=true`, `live_incremental_parity_verified=true` |
| Different V6.5 logic without incremental methods | Build, test and register new algorithm-specific adapter | New source SHA **plus** new implementation + parity tests |

## Offline test evidence

- Focused registry, source pinning, V6.4 gate, sequential candle planner, retained-state, loader and runtime-contract tests: 42 passed with test-suite's expected default `LIVE_STRATEGY_HISTORY_DEFAULT_BARS=2000`. The actual V6.4 deployment continues requiring **80K**; no production history setting was changed.
- Without the test-only override, one existing runtime-contract test fails because it expects the generic default 2,000 while this project's configured default is 80,000. Not caused by these new code changes.
- No full broker end-to-end replay, order-placement test, or exact V4.31B + portfolio-gate rolling parity certification was performed in this patch.

## Rollback

Set `LIVE_INCREMENTAL_ADAPTER_ENABLED=false`, `LIVE_INCREMENTAL_ENABLED=false`, `LIVE_RUNNER_SEQUENTIAL_CATCHUP_ENABLED=false`, `LIVE_TRADELOCKER_GAP_BACKFILL_ENABLED=false` and remove old `LIVE_V64_HYBRID_ENABLED` to force original full-history execution, then recreate the two idle workers. You may also restore original runner code from your backup. This does **not** change dashboard Auto Trade or reset persistent data. Preserve all live position and reconciliation services.
