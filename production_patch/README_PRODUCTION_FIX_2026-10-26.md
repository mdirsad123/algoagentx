# AlgoAgentX — HTTP 504 / live M5 stability patch (2026-10-26)

## Scope and evidence

- **Confirmed:** `POST /api/v1/live/deployments/{id}/run-full-dry-test` was recorded in supplied API logs as HTTP 200 after **448.919 seconds**. It evaluated strategy synchronously in the FastAPI request.
- **Confirmed:** Gunicorn has `--workers 1` in the server snapshot. API process showed ~74% lifetime CPU and had previously shown ~100% instantaneous CPU. Container RAM is not exhausted (7.9 GiB available, two CPU cores). Neither proves that every 504 came from this route.
- **Confirmed in source:** `LIVE_RUNNER_ENABLED=true` and `LIVE_LEGACY_RUNNER_ENABLED=true` cause the FastAPI lifespan to start the non-cTrader legacy polling/signal loop. `live_market_worker` supports **cTrader** feeds only, not TradeLocker. So the TradeLocker strategy scheduler shares the API process, while the UI incorrectly treats the cTrader event-stream feed count (0 for TradeLocker) as a TradeLocker health failure.
- **Observed:** repeated `Failed to find Server Action "x"` in web logs. The ZIP does not contain the production Nginx config or browser request data to determine whether these are stale clients, malformed requests, mixed deployments, or something else. This patch does **not** claim to fix that independent problem.
- **Unknown:** exact long-running strategy compute duration, broker-provided candle availability, 504 upstream request traces, order path parity and actual M5 latency. These require production monitoring and replay tests.

## Actual source code changes

1. `docker-compose.yml`: API gets `LIVE_LEGACY_RUNNER_ENABLED=false` regardless of production env value; new `live_legacy_runner_worker` runs the legacy polling scheduler as **one separate process**. cTrader workers are unchanged.
2. `app/services/live/live_legacy_runner_worker.py`: launches the existing `auto_runner_loop` and emits a Redis heartbeat under `live_legacy_runner_worker`. Does not alter the strategy, signal generation, TP/SL, order execution, or risk sizing.
3. `app/services/live/auto_runner_service.py`: adds **timing logs only** for the legacy scheduler; no trade decision changes.
4. `app/tasks.py` + `app/services/live/dry_test_jobs.py`: full dry-test uses a Redis-backed, deployment-scoped job with duplicate suppression, queue `live_dry_test`, Celery result state/status, and expiry. Dedicated worker concurrency=1 and a **0.50 vCPU cap** to protect the 2-vCPU live host during expensive QA (dry tests can take longer). There is **no synchronous HTTP fallback** when Redis is down.
5. `app/api/v1/live_deployments.py`: existing dry-test POST now immediately responds with `{job_id,status}`; new authenticated GET `/{deployment_id}/run-full-dry-test/jobs/{job_id}` returns status/results; pipeline health indicates `CTRADER_STREAM` vs `LEGACY_POLLING` and fetches legacy heartbeat.
6. Next.js live page + API helper/types: background dry-test polling; TradeLocker/MT5/Upstox no longer wrongly judged by cTrader feed counter.

**Changed API contract:** `POST .../run-full-dry-test` now returns a queued job rather than the final dry-test result. Existing external clients need to adapt. The bundled Next.js page has been updated.

## High-priority deployment safety notes

- **DO NOT blindly run** `docker compose down`, `docker compose down -v`, `docker system prune --volumes`, or `redis-cli FLUSHALL`.
- **DO NOT scale** `live_legacy_runner_worker` beyond 1 process or enable the legacy scheduler in the API simultaneously. Existing per-deployment transactional guards are retained but should not be relied on to justify duplicate schedulers.
- This package **intentionally omits credentials** (`.env.prod`, `.env`, private keys, broker tokens), local virtual environments, Next.js build caches, runtime data, uploaded files, and database files. Keep the ORIGINAL `.env.prod` on your Oracle server. The archive should be merged into a tested working tree, not used to delete your existing secret/runtime files.
- Back up DB, Redis and the original source/Compose and record open broker positions/orders before changing any live components.
- The source bundle has **NOT been deployed** to Oracle; local static syntax/contract checks are not a substitute for runtime or broker tests. Use DEMO only until parity checks pass.

## Staged production rollout (not automatic)

Perform during a quiet gap, **outside the M5 candle-close boundary**, with a confirmed rollback and no unresolved orders. This is a two-core, ~12 GiB Oracle VM; check `df -h` first (latest reported ~16 GB free) and avoid full rebuilds of unrelated services.

1. **Back up** your server's current checkout, `docker-compose.yml`, `.env.prod`, PostgreSQL database (consistent `pg_dump`), and Redis persistence as appropriate. Verify the backup actually restores on another path; avoid copying plaintext credentials into chat.
2. Extract this ZIP in a **new staging folder** and review `production_patch/CHANGED_FILES.txt`. Diff changed files against current server. Merge code without overwriting your existing `.env.prod` or runtime/DB volumes.
3. Run `python -m compileall -q AlgoAgentXAPI/app` and `python production_patch/verify_static_patch.py` (uses PyYAML if installed; fallback checks are standard-library). Validate `docker compose --env-file .env.prod config --quiet` **locally on the server**, without sharing rendered secret-bearing config.
4. Build the 4 relevant images first: `docker compose --env-file .env.prod build api web live_legacy_runner_worker live_dry_test_worker`.
5. **Critical scheduler handoff:** first start **new API only** (which disables its legacy scheduler) via `docker compose --env-file .env.prod up -d --no-deps api`. Confirm `docker compose ... logs --tail=50 api` shows no legacy runner start and `/health` responds. **Then immediately start the legacy runner** with `docker compose --env-file .env.prod up -d --no-deps live_legacy_runner_worker`. This staged handoff has a short unavoidable gap; avoid candle boundaries and check cursor recovery. Do not start the dedicated legacy runner before disabling the old API scheduler; doing so risks two active pollers.
6. Start the dry-test worker: `docker compose --env-file .env.prod up -d --no-deps live_dry_test_worker`. Inspect its startup logs for registration of `app.tasks.run_live_full_dry_test_task` and queue `live_dry_test`.
7. Update only the web service: `docker compose --env-file .env.prod up -d --no-deps web`, then hard refresh the browser and inspect browser Network requests. No other live worker image needs restarting for this patch.
8. Verify all services and worker heartbeats, compare `last_processed_candle_time`, broker positions and orders against the pre-change baseline, and perform a queued dry test with an *authorized DEMO deployment* while watching separate API latency.
9. Hold further production changes if you see duplicate entries, unexplained open orders, missed candles, stale legacy heartbeat, or nonresponsive API. Roll back immediately via the original source/Compose and reassess broker state first.

## Verification commands (read-only)

```bash
cd ~/stock_market/algoagentx
docker compose --env-file .env.prod ps -a
docker stats --no-stream
docker compose --env-file .env.prod logs --since=20m --tail=350 api live_legacy_runner_worker live_dry_test_worker live_strategy_worker live_market_worker
docker compose --env-file .env.prod exec -T redis redis-cli --scan --pattern 'live:worker_health:*'
free -h
df -h
```

Browser Network (signed in): POST dry test should return a `job_id` quickly, then GET polling calls should be short. Dry-test worker should consume CPU separately from API; live scheduler continues to run in legacy worker even while the test computes.

**Acceptance checklist (must be checked on the server):**
- FastAPI GET `/health` and ordinary authenticated routes remain responsive while dry test is active; no repeated 504s attributable to dry test or legacy CPU load.
- No second legacy scheduler in API; exactly one `live_legacy_runner_worker`; heartbeat fresh.
- Both MT5/TradeLocker legacy and cTrader event-pipeline modes display the correct worker status.
- No missed, duplicate, or out-of-order M5 candle processing; record broker close timestamp → DB store → evaluate → send → accept → fill.
- Preserve original V6.4 strategy outputs, next-open semantics, 1% risk, 2R targeting and global single-open-position control; compare controlled replay and DEMO traces (same candle source, symbol, timestamp, settings, and costs).
- 504 reverse-proxy and `Failed to find Server Action "x"` issues must be **separately investigated** if still present. Review Nginx access/error logs correlated with request IDs and exact times; inspect browser Network response headers, stale-cache behavior and deployment artifact consistency. **Do not** increase proxy timeouts as a first-line fix.

## Rollback

If any signal timing/order anomaly appears, **do not** use an untested emergency toggle while positions are unknown. Verify current broker positions, pending orders and the last processed candle. Coordinate a handoff away from candle boundaries:

1. Stop the **new dedicated legacy runner only**: `docker compose --env-file .env.prod stop live_legacy_runner_worker` (avoid changing other workers).
2. Restore the original API code and Compose, rebuild and restart **API only** using its original deployment procedure (legacy scheduler enabled again via original `.env.prod` if previously enabled).
3. Stop the dry-test worker if unwanted. Restore original Next.js frontend when the API contract is reverted.
4. Compare broker/DB orders and strategy cursor to the pre-change snapshots; never purge Redis or Postgres volumes.

If the current API cannot be restored promptly, keep the system in DEMO and use your established manual broker safeguards. There is no claim of automatic recovery after a missing candle during handoff.

## Unresolved after this code patch

- No Oracle live workload profiling, integration tests against live DB/Redis/TradeLocker, or Nginx config review were possible in this offline sandbox.
- If the **strategy itself** takes >300 seconds to evaluate 80K bars, moving it to a separate process does **not** solve the missed-M5-deadline problem. Collect the new `Legacy scheduler slow cycle` logs; then profile the actual frozen V6.4 calculation, develop causally correct incremental state in a research branch, and compare every signal before promotion. Do not silently change V6.4 execution logic in this stability patch.
- No CPU/RAM quotas were increased (there is substantial available memory; the root issue is process isolation/CPU scheduling, not RAM allocation).
