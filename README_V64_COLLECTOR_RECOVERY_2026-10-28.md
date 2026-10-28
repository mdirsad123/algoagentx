# AlgoAgentX V6.4 — TradeLocker collector watchdog and runner stale-feed fallback

## What the provided logs actually establish
* New deployment `0349cc95-6677-4a7e-b7d1-e4c8cbd46b88` was eligible in the database; `_deployment_ids()` returned it.
* Dedicated history worker completed 80,005 stored candles at 2026-10-28 10:58:42 UTC.
* Candle worker emitted its startup line, but the supplied logs **do not show a subsequent candle fetch**. The runner emitted repeated `RUNNER_NO_NEW_CANDLE_IDLE` and no first `RUNNER_GENERATE_COMPLETE` for that deployment.
* The exact internal reason for the absence of candle-worker logs cannot be proven without runtime task stacks; a stalled DB/REST call, unhealthy process loop and silent skipped polls were all previously indistinguishable.

## Code changes, isolated from strategy logic
1. Add bounded (60-second) per-deployment polling calls and (20-second) registry scans; failures are logged and retried. No synthetic candles.
2. Log `TRADELOCKER_REGISTRY_SCAN`, `TRADELOCKER_POLL_ATTEMPT`, `TRADELOCKER_POLL_SKIP`, `TRADELOCKER_FETCH_START` and existing `TradeLocker candle fetch` to identify exactly where a worker is stuck.
3. Heartbeat status now reflects actual poll progress: no deployment is `IDLE`; no first poll after 90 seconds is `DEGRADED`; no completed poll in 420 seconds is `DEGRADED`. Session-closed broker polls can be HEALTHY if they complete (no false market-hours rule).
4. Runner does not trust bare `HEALTHY` or everlasting `STARTING` heartbeat. A healthy independent collector needs a recent completed poll timestamp and recent heartbeat.
5. If collector is stale, the runner may perform **only one** inline TradeLocker refresh for each M5 bucket. Afterwards it uses DB-only idle checks, to avoid API storms. All strategy/order protections remain intact.
6. The V6.4 strategy source, strategy_runner, hybrid incremental adapter and 80,000 history requirement are **unchanged**.
7. Long-gap/backfill experiments remain **disabled** by provided config. Skipped real candles and full rolling parity are not solved by this operational reliability patch.

## Safe deployment (Windows PowerShell)
1. Backup `D:\Stock_market\algoagentx` and your private original `.env.prod`.
2. Extract this ZIP into a SEPARATE folder, then copy the `AlgoAgentXAPI`, `AlgoAgentXApp`, and root code/config folders to `D:\Stock_market\algoagentx`. **Do not overwrite `.env.prod`, `.env`, credentials, or database volumes.**
3. From project root, run:

```powershell
cd D:\Stock_market\algoagentx
powershell -ExecutionPolicy Bypass -File .\APPLY_V64_COLLECTOR_FIX.ps1
docker compose --env-file .env.prod config --quiet
docker compose --env-file .env.prod up -d --no-deps --build --force-recreate live_tradelocker_candle_worker live_legacy_runner_worker
docker compose --env-file .env.prod logs -f --tail=120 live_tradelocker_candle_worker live_legacy_runner_worker
```

The script backs up `.env.prod` and edits only explicitly named non-secret settings. It keeps the user's authorized strategy SHA and real broker credentials unchanged.

## Expected log sequence
* `TRADELOCKER_REGISTRY_SCAN matched=1 ...0349cc95...`
* `TRADELOCKER_POLL_ATTEMPT deployment=...`
* `TRADELOCKER_FETCH_START deployment=...` (only if a closed candle not yet stored)
* `TradeLocker candle fetch ... ready=True`
* `RUNNER_INCREMENTAL_PRIMED bars=80000` then `RUNNER_GENERATE_COMPLETE mode=FULL_HISTORY` once after runner restart; subsequent consecutive M5 candles should show `RUNNER_INCREMENTAL_DONE` + `RETAINED_INCREMENTAL`.

If collector still hangs: look for last reached log marker. `TRADELOCKER_REGISTRY_SCAN` alone means fetching hasn't been entered; `TRADELOCKER_POLL_ATTEMPT` but no fetch/skip means DB readiness path; `TRADELOCKER_FETCH_START` but no completion means broker/DB refresh stalled, capped by 60 seconds. If collector reports `DEGRADED`, runner logs `RUNNER_TRADELOCKER_COLLECTOR_STALE` and performs at most one fallback fetch for a candle.

## Test scope and limitations
Offline: pure collector-health tests, market-boundary tests, retained-strategy-state unit tests, incremental adapter-registry tests and existing gap-planning tests. Python compileall and archive-integrity checks. Actual TradeLocker REST, Postgres, Redis, Docker and 80K rolling signal/SL/TP parity **cannot be validated in this offline environment**. Old `test_demo_observed_long_gap_20261028.py` is stale relative to this rollback because it references a removed API; not counted as passing. Do not infer the 2022-2026 backtest metrics or demo order results from these tests.
