# AlgoAgentX local Docker — Warmup/runner cache and backoff patch (27 Oct 2026)

## What is fixed and what is NOT fixed

This patch uses the *latest hybrid source package* as its base; no DB-stored Strategy source is automatically replaced.

**Fixed / improved:**
- During a new 80,000-candle warmup, the legacy auto runner no longer keeps attempting a full strategy run every 1–5 seconds while its `live_history_worker` is still backfilling. A per-deployment local gate reads the existing Redis warmup completion status every ~5 seconds. READY is merely a hint to perform a fresh **authoritative SQL readiness check**. Without Redis, the gate allows a DB retry at most 20 seconds later. It never waits indefinitely.
- Eligible deployment ID scans are cached for **2 seconds**. `run_deployment_if_due` still re-reads the actual deployment status and Auto Runner ON/OFF from PostgreSQL before any evaluation; a stopped strategy cannot be re-enabled through this cache.
- Successful history counts are cached as **positive-only hints for 20 seconds**, with a matching deployment/strategy/broker/symbol/timeframe signature. Full-history candle loading STILL verifies all required candles and the candle's exact timestamp. Any insufficient data immediately invalidates the hint.
- Dynamic strategy compilation/source caching was already implemented via `_load_dynamic_strategy_class_cached` (`@lru_cache(maxsize=64)`). Existing behavior is retained; source edits cause a new key. No stale strategy source added.

**Not fixed:** existing V6.4 DB `generate()` still recomputes ~80,000 bars every M5 candle. Your supplied Windows Docker logs show 254–412 seconds in that calculation. Caching scheduling metadata can never turn this into under-60-second execution. The enclosed `V64_HYBRID_INCREMENTAL_EXPERIMENT.py` from the prior candidate only partially optimizes V3.5; V4.31B and V6.4 portfolio replay remain heavy. Do not claim parity/enable auto-orders without authentic 80K rolling-candle validation.

`LIVE_INCREMENTAL_ENABLED=false` remains the correct default. No stale-order blocking flag is enabled; all existing order safety checks remain in place.

## Local Windows Docker deployment

**Use PowerShell in** `D:\Stock_market\algoagentx` after extracting the ZIP to a staging directory and reviewing/cherry-picking the changes. Preserve your existing `.env.prod`, PostgreSQL, Redis, Strategy database records, and user data. Do not blindly overwrite custom project files.

1. Verify service names and your current state:

```powershell
docker compose --env-file .env.prod config --services
docker compose --env-file .env.prod ps -a
```

2. Confirm TradeLocker has no unresolved broker request/open position, set demo Auto Trade OFF, and wait until current strategy execution completes. **Never interrupt mid-order**. Stop only the legacy runner for a controlled hotpath update:

```powershell
docker compose --env-file .env.prod stop -t 30 live_legacy_runner_worker
```

3. From the updated merged project root:

```powershell
docker compose --env-file .env.prod config --quiet
docker compose --env-file .env.prod build live_legacy_runner_worker
docker compose --env-file .env.prod up -d --no-deps --force-recreate live_legacy_runner_worker
```

For this patch the **API, frontend, Postgres, Redis, candle worker, history worker and other workers need not be recreated**. The included changed Python files run inside the legacy worker image. Docker rebuild from scratch may take time; preserving the existing source/volumes is important.

4. Monitor:

```powershell
docker compose --env-file .env.prod logs --since=30m --tail=2000 live_legacy_runner_worker | Select-String -Pattern 'WARMUP|RUNNER_DISPATCH|LOCK_SKIPPED|RUNNER_GENERATE_COMPLETE|strategy_generate|RETAINED_INCREMENTAL'
docker compose --env-file .env.prod logs --since=30m --tail=100 live_history_worker
docker stats --no-stream
```

Expected during new deployment warmup: `RUNNER_WARMUP_WAIT` once; no repeated heavy evaluations before READY; `RUNNER_WARMUP_READY` or bounded SQL fallback; then (only when enough candles exist) the original `FULL_HISTORY` calculation. **There is no speed guarantee for that calculation.**

## Regression tests

From `AlgoAgentXAPI`:

```powershell
python -m pytest -q tests/test_runner_hotpath_cache_20261027.py tests/test_retained_strategy_state.py tests/test_incremental_parity_cli.py
python -m compileall -q app/services/live
```

The latest package was tested with 13 focused Python tests passing, Python compilation, Docker Compose YAML parsing, and ZIP integrity. Full runtime integration and 80K TradeLocker signal parity were not tested in the packaging environment.

## Risk, cache correctness, and rollback

- A late Start/Stop update might take <=2s to appear in the *scan list*, but `run_deployment_if_due` always reads the current DB flags. The kill switch, broker position and signal idempotency checks are untouched.
- A stale positive readiness hint can't force a trade if candles were removed: the 80K load still checks count and exact target bar. History/readiness gaps should be investigated; don't interpret a cached count as candle continuity proof.
- If Redis is unavailable, the gate falls back to SQL within 20 seconds (and resumes backoff only if history is still insufficient).
- On a worker restart all local caches reset safely.
- To roll back, restore **only** the three changed Python runner files from your source backup (`runner_cache.py` is new, `auto_runner_service.py` and `strategy_runner.py` changed); rebuild/recreate `live_legacy_runner_worker` as above. Do not clear Redis/DB or delete historical candles.

## Actual <60-second fix still required

1. Extract exact active DB Strategy source and non-secret params; confirm SHA256 against the frozen research baseline.
2. Benchmark V3.5, V4.31B and V6.4 gate separately on identical 80K finalized TradeLocker candles.
3. Implement genuine per-candle state transitions for all three components, with versioned state/checkpoints.
4. Verify full-history vs stateful candle-by-candle BUY/SELL/HOLD, entry, SL, TP, position/risk and window-expiry parity over long periods and restart/gap scenarios.
5. Enable `LIVE_INCREMENTAL_ENABLED=true` **only** after the exact active Strategy record has a compatible, parity-approved incremental source and the deployment has been validated in DEMO with Auto Trade OFF.
