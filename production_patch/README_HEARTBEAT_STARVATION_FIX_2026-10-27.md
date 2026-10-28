# AlgoAgentX — legacy runner heartbeat starvation patch (27 Oct 2026)

## Findings supported by `api_logs(3).txt`

- TradeLocker closed-candle worker persisted 13:10, 13:15, 13:20 and 13:25 open-time candles at ~4–10 s after close.
- Legacy scheduler `strategy_generate` took 466.313, 533.039, 511.438 wall-clock seconds on 80,000 candles. Its CPU seconds were nearly equal to wall seconds: CPU-bound full-history replay.
- Since `generate()` is synchronous and runs inside the same Python asyncio thread as the legacy Redis heartbeat coroutine, 90-second Redis heartbeat TTL can expire even while Docker says `healthy`. The browser displays `OFFLINE` when the Redis health key is missing. This explains status flicker, not the 8–9 min strategy execution itself.
- `RUNNER_CANDLE_GAP` warns skipped intermediate candle evaluations. `next_run_at` may be in the past while the runner remains occupied; increasing the scheduler scan frequency does not fix this.
- API GET requests continue to respond with 200 in the sample. Some requests are slow (e.g. /latency up to ~7s), consistent with shared CPU/I/O contention, but the 500s work is measured inside `generate()`.
- Docker's healthcheck only verifies the command in /proc/1/cmdline, NOT progress, Redis heartbeat, or candle processing freshness.

## Files changed (no signal/order changes)

1. `AlgoAgentXAPI/app/services/live/live_legacy_runner_worker.py`: independent Python thread and synchronous Redis connection refresh worker heartbeat every ~5 s. Reports `phase=PROCESSING` and `cycle_started_at` independently of synchronous strategy execution. Stops thread on worker shutdown. Does NOT dispatch strategy or submit orders.
2. `AlgoAgentXAPI/app/services/live/auto_runner_service.py`: optional scheduler cycle observer callback, used solely by the worker's heartbeat reporter. Existing API scheduler call remains backward compatible.
3. `AlgoAgentXApp/app/(user)/live-trading/[deploymentId]/page.tsx`: differentiate `PROCESSING` (alive and executing, but possibly late) from `OFFLINE` (no Redis heartbeat). `Last Processed Candle` remains the authoritative progress indicator.
4. `production_patch/test_independent_runner_heartbeat.py`: stand-alone no-network concurrency test.

## What this release DOES NOT fix

V6.4 still uses `mode=FULL_HISTORY`. The previous candidate `production_patch/v64/V64_OPTIMIZED_RESEARCH_ONLY.py` is not automatically installed into PostgreSQL. The strategy source actually used by the deployment comes from DB `Strategy.parameters.source_code`. This release does not replace that source and does not claim 80K parity or incremental state. Do NOT set `LIVE_INCREMENTAL_ENABLED=true` for V6.4, and DO NOT assume this release reduces 466–533 seconds to 5 seconds. The 8-minute execution, missed M5 bars, and broker-order delay remain serious issues.

The user's optional stale-order guard is **OFF by default** (`LIVE_RUNNER_STALE_ORDER_GUARD_ENABLED=false`), unchanged here. Existing broker-side risk/duplicate-order guards remain untouched. Without a freshness guard, late demo orders remain possible. Keep Auto Trade OFF during validation.

## Before deploying

1. Ensure your active source is the matching 27 Oct retained-framework ZIP, NOT an older version; compare changes with your Git tree.
2. Back up source, current Docker images, `.env.prod`, live DB (including strategy/source records), and reconciliation state. Preserve volumes. Use a quiet DEMO window; never restart in the middle of a generating V6.4 cycle.
3. Check that the API does not also have a separate legacy runner enabled: Compose `api` should set `LIVE_RUNNER_ENABLED=false`, and only one `live_legacy_runner_worker` replica exists.
4. Leave `LIVE_RUNNER_STALE_ORDER_GUARD_ENABLED=false` as requested. Leave `LIVE_INCREMENTAL_ENABLED=false` for the unverified V6.4 strategy.

## Verify after extracting this ZIP

From the repository root:

```
python production_patch/test_independent_runner_heartbeat.py
cd AlgoAgentXAPI
python -m pytest -q tests/test_retained_strategy_state.py tests/test_incremental_parity_cli.py tests/test_live_strategy_history_profile.py tests/test_every_candle_latency_strategy.py tests/test_broker_candle_parity_guard.py
cd ..
docker compose --env-file .env.prod config --quiet
```

On a DEMO system, restart in a quiet window:

```
docker compose --env-file .env.prod build live_legacy_runner_worker web
docker compose --env-file .env.prod up -d --no-deps live_legacy_runner_worker web
docker compose --env-file .env.prod ps -a live_legacy_runner_worker web
```

While full history is processing (Auto Trade OFF):

```
docker compose --env-file .env.prod logs --since=20m --tail=500 live_legacy_runner_worker
docker compose --env-file .env.prod exec -T redis redis-cli TTL live:worker_health:live_legacy_runner_worker
docker compose --env-file .env.prod exec -T redis redis-cli GET live:worker_health:live_legacy_runner_worker
docker stats --no-stream
```

**Expected:** TTL stays positive during 5–9 minute `strategy_generate`, the JSON `heartbeat_at` moves forward and `phase` reads `PROCESSING`; UI shows `PROCESSING` rather than `OFFLINE`. It may remain PROCESSING for >300 seconds — this is proof of computation backlog, NOT a healthy live latency. `Last Processed Candle` should catch up only after the heavy generation finishes.

If TTL still repeatedly reaches -2, collect Redis logs and `docker stats` (severe CPU starvation/disk stalls can also delay even a separate thread), check redis URL/config and whether multiple Redis containers are in use. If TTL is positive and UI still shows OFFLINE, confirm API and worker point at the same production Redis instance and web/API bundles are rebuilt.

## Actual V6.4 speed improvement — separate release gate

Export the **exact currently deployed DB strategy source** via the included read-only utility and obtain matching live parameters. The `V64_OPTIMIZED_RESEARCH_ONLY.py` candidate requires 80K matched broker-candle parity before you clone the DB strategy for shadow validation. The fundamental required fix remains a separately verified incremental state machine across V3.5 + V4.31B + V6.4 gate; a generic waiting scheduler alone is not enough. No automatic new order sending from a background replay should be introduced to hide lag.

## Rollback

Restore the previous worker/web source or images from backup, then recreate those two services in a quiet window (with Auto Trade OFF). Do not restore database transaction records blindly and do not delete PostgreSQL/Redis volumes. Revalidate processed candle cursor and any open broker position before resuming automatic DEMO trading.

## Validation performed here

- Python compile passed, Compose YAML parsed.
- Dedicated heartbeat test passed (heartbeat continues while asyncio loop blocked, phase transitions observed).
- Existing five focused pytest modules: 16 passed.
- No running Oracle/Docker/TradeLocker end-to-end integration run in this environment. No genuine 80K parity or performance gain verified.
