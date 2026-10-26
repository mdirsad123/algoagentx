# AlgoAgentX TradeLocker M5 diagnostic/isolation patch — 2026-10-27

**Target: DEMO verification first. Not a proven low-latency trading release.**

This ZIP extends `AlgoAgentX_Production_Stability_Fix_2026-10-26` and includes the previous legacy scheduler + dry-test isolation. It addresses the supplied 27-Oct dashboard screenshots. No V6.4 strategy code, trading rules, history warmup task or DB migration has been changed.

## Evidence and fixes

1. **Slow candles:** In prior package `auto_runner_loop` fetched TradeLocker bars and ran full-window V6.4 evaluation **sequentially** inside one legacy runner process. If `generate()` is CPU heavy, its next candle fetch is delayed. This patch creates `live_tradelocker_candle_worker` (exactly one replica), a data-only polling process independent from the strategy process. It starts attempting after M5 close +2s and retries missing broker candles at ~5-second intervals. It NEVER sends orders, invokes V6.4, or modifies trading decisions. The legacy runner reads DB and skips its own TradeLocker broker fetch when flag `LIVE_TRADELOCKER_CANDLE_WORKER_ENABLED=true` (set by Docker Compose only on legacy runner). Other brokers use old path.
2. **Ingest latency always blank:** `get_latest_closed_candles` dropped `created_at` from its SELECT and result mapping, although both snapshot endpoints expected it. Added `created_at`, and now records actual insertion time explicitly in the short broker refresh (PostgreSQL transaction `now()` would report the time the transaction began before REST I/O). Original first-ingest timestamp is preserved when a candle is upserted again. Warmup rows created before the patch may have inaccurate times; verify fresh incoming bars instead.
3. **Legacy health warning:** Pipeline health exposes `live_tradelocker_candle_worker` Redis heartbeat; frontend displays independent TradeLocker Candle Worker / Legacy Strategy Runner. cTrader stream feed count is never used to judge TradeLocker REST health. Worker heartbeat reports STARTING/HEALTHY/DEGRADED, records last successful poll and fetch error.
4. **Broker summary balance vs local $5000 equity:** Top account-value card uses the exact cached TradeLocker account snapshot shown in Broker Summary. If broker EQUITY is missing and there are zero tracked open positions, it displays last broker BALANCE as a clearly labeled proxy, **not actual broker equity**. If tracked open positions are present and broker equity missing, it shows Unavailable, never a fabricated value. Local realized/unrealized PnL stays explicitly local. No financial figures are manufactured; an account statement or reconciliation is still needed to verify broker-wide PnL.
5. **Close→send p50/p95:** Adds best-effort TradeLocker order-path stages `t11` and `t12` around actual `place_market_order` and later `t13`/`t14` ONLY when response confirms ACCEPTED/FILLED. Each new bar has a deterministic Redis/DB trace and V6.4 strategy processing passes its trace ID. During a HOLD-only period, close→send metrics remain genuinely unavailable (`—`), rather than zero. The t1 REST response time is approximate and not a native broker event stream.

## Remaining limitations (critical)

- A separate fetcher cannot speed up the frozen V6.4 `generate()` calculation. If it takes >300s, the strategy scheduler can still miss its 5-minute execution deadline or skip intermediate bars while consuming newest data. Do not call this release backtest/live parity verified; profile live strategy computation and build a separately parity-tested incremental version.
- TradeLocker broker may delay publication of finalized OHLC data. Close+2s is the **first attempt**, not guaranteed freshness. Watch the log `expected=`, `stored=`, `ready=`, `ingest_lag_s=`, `duration_s=`.
- Ingest latency is first local DB insertion, **not a measure of TradeLocker server publication latency**. Browser polling causes additional display latency; use API returned times to distinguish them.
- HTTP 504 / Next.js `Failed to find Server Action` may still need proxy/server-action investigation. This patch does not prove those errors fixed.
- Redis trace capture requires `LIVE_LATENCY_TRACE_ENABLED` and a functioning Redis connection. Actual broker order latency metrics require an order to be sent and recorded. No need to place an artificial order just to create a percentile.
- Current broker summary uses cached account data from the last successful sync; if not freshly synced, the figure may be stale. Broker equity remains Unavailable when TradeLocker omits it.
- Previous package's full dry-test remains separate Celery job, still does a full backtest-style calculation. `0.5 CPU` throttle protects market data but may make manual QA slower.

## Pre-deployment safety

1. This is a **source package**, not a ready-running server. Inspect diff against your actual Oracle checkout; verify Docker Compose services, `.env.prod`, deployment flags, and broker/symbol configuration. It does not ship secrets, Redis DB or Postgres data.
2. Safely backup original source/Compose and database; capture current broker positions/orders and `last_processed_candle_time`, last stored candle and balance before deployment.
3. Only DEMO. Do not deploy at a candle-close boundary, while there are unknown/pending broker orders, or without rollback capability. **Do not run `docker compose down -v` or any Redis flush.**
4. `docker compose --env-file .env.prod config --quiet` must pass, and dry-run/candle/strategy worker images must build. Check host free disk; the original VM had ~16 GB free, 2 vCPUs.

## Staged rollout (source files first, then controlled services)

Commands run inside `~/stock_market/algoagentx` **after** merging the reviewed files while preserving server `.env.prod` and volumes. Build before switching anything:

```bash
cd ~/stock_market/algoagentx
python3 -m compileall -q AlgoAgentXAPI/app
docker compose --env-file .env.prod config --quiet
docker compose --env-file .env.prod build api live_legacy_runner_worker live_tradelocker_candle_worker live_dry_test_worker web
```

For a server still on the ORIGINAL version (without the previous patch):

```bash
# During a quiet M5 window, change ownership of legacy scheduler:
docker compose --env-file .env.prod up -d --no-deps api
# Check new API has LIVE_LEGACY_RUNNER_ENABLED=false (Compose config,
# without dumping secrets) and health success; THEN start once:
docker compose --env-file .env.prod up -d --no-deps live_tradelocker_candle_worker
docker compose --env-file .env.prod up -d --no-deps live_legacy_runner_worker
# The REST candle poller should start BEFORE the strategy runner.
docker compose --env-file .env.prod up -d --no-deps live_dry_test_worker web
```

For a server ALREADY on the previous 2026-10-26 package, no need to stop/recreate API; add the candle worker, then recreate only legacy worker to enable its no-duplicate-broker-fetch flag:

```bash
docker compose --env-file .env.prod up -d --no-deps live_tradelocker_candle_worker
docker compose --env-file .env.prod up -d --no-deps live_legacy_runner_worker
```

The second command restarts the strategy runner: do only in a safe window, inspect broker positions/order state before/after, and verify the processed candle cursor.

## Verification (read-only)

```bash
docker compose --env-file .env.prod ps -a
docker stats --no-stream
docker compose --env-file .env.prod logs --since=20m --tail=350 live_tradelocker_candle_worker live_legacy_runner_worker api
docker compose --env-file .env.prod exec -T redis redis-cli GET live:worker_health:live_tradelocker_candle_worker
```

Use the signed-in UI `/candles`, `/pipeline-health`, `/latency` requests. Record at least 10 successive M5 closes. For each, verify expected UTC close, first broker fetch, DB inserted timestamp, strategy start/finish, and if there was a real signal, order request/confirmation status. Also validate whether `get_latest_closed_candles` `created_at` corresponds to new bars, not old warmup rows.

## Rollback plan

- If candle polling fails or causes broker rate limiting, stop **only** new `live_tradelocker_candle_worker` in the quiet window, and restore legacy runner code/config from the prior package (which resumes old inline broker polling). The legacy runner has a bounded Redis heartbeat check and can fall back to inline fetching when the candle worker disappears, but for a clean rollback restore the previous flag/code instead of relying on emergency fallback indefinitely.
- If reverting to pre-2026-10-26 version, also restore API-owned scheduler and old dry-test API contract/frontend together. Never allow API and legacy runner to own the scheduler simultaneously.
- Keep broker reconciliation/position state intact. Do not delete volumes. Pause Auto Trade if an execution-path mismatch appears; inspect broker positions and pending orders before restarting any strategy service.

## Acceptance criteria

- Candle worker heartbeat fresh and next closed M5 bar persisted with measured non-null ingestion latency (when broker data actually available).
- Strategy runner heartbeat independent of broker fetcher; no duplicate broker polling during steady state.
- Top account-value metric no longer shows stale $5,000 equity while broker summary shows $5,101 balance without clarification.
- Pipeline health correctly indicates TradeLocker REST mode; no fake broker event stream.
- p50/p95 appear only after at least one real order send trace with valid `t12` timestamp; otherwise remain unavailable.
- No duplicate orders, no cursor regression, no missed candles during 10+ observed intervals. If `generate()` takes >300s, do **not** declare live timing safe: move to separately tested incremental V6.4 research.
