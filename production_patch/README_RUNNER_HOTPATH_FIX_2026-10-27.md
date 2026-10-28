# AlgoAgentX TradeLocker V6.4 legacy runner — timing and fail-safe patch (2026-10-27)

**Release classification:** DEMO diagnostic + targeted correctness fixes. **Not** a verified 5-second V6.4 calculation release. Do not promote to a real-money account without an independent replay/live parity audit.

## Evidence from the supplied new `api_logs(1).txt`

- Legacy runner slow cycles completed in `424.758`, `331.661`, `402.560`, `246.419`, and `233.786` seconds (`checked=1 ran=1`). These are the entire scheduler cycles, not necessarily only `generate()`.
- In the attached `docker stats` snapshot the legacy runner CPU was `98.49%` while the API was `0.12%`. High CPU makes V6.4 full-history computation the strongest suspect; **the stage breakdown was not logged by the old code**, so database loading vs strategy class construction vs `generate()` remains unmeasured.
- The supplied command was executed from `PS D:\\Stock_market\\algoagentx>` and Docker reports a **3.766 GiB** memory limit (typical local Docker Desktop). It is **not** evidence that the Oracle server reported earlier (~11.65 GiB) has lost memory.
- PostgreSQL command output included only `(1 row)`; it does not identify a database lock that explains the 400-second cycle.
- Successful TradeLocker candle ingestion is already separate from the slow strategy worker. Changing the 5-second scheduler scan to 1 second cannot fix 233–425 seconds of in-flight CPU work.

## Exactly what changed from 2026-10-27 TradeLocker patch

1. **Wall + CPU timings:** new `runner_diagnostics.py` records `RUNNER_STAGE_START`, `RUNNER_STAGE_DONE`, and `RUNNER_STAGE_SUMMARY` for `resolve_strategy_and_runtime`, `history_readiness_check`, `load_closed_candles`, `build_dataframe`, `strategy_class_init`, `strategy_generate`, `extract_latest_signal`. Every stage includes wall seconds and CPU seconds (and historical candle count when available). `RUNNER_GENERATE_COMPLETE` prints total elapsed. A CPU-heavy `generate()` will show CPU≈wall; DB/network wait produces wall>>CPU.
2. **Opt-in CPU profiler:** set `LIVE_STRATEGY_CPROFILE_ENABLED=true` on the **legacy runner only** to dump top 20 cumulative Python functions. Default `false` because profiler adds overhead. Use only in DEMO or an isolated reproduction.
3. **Fix unsuccessful-result cursor handling:** `success=False` runtime contract/history/HOLD outcomes do not advance `last_processed_candle_time` in the *outer scheduler*. They retry instead; backtest parity can no longer be falsely claimed from advancing a failed run.
4. **Distinguish successful duplicate from skipped lock:** the old scheduler retried every `duplicate=True` even if the engine had already evaluated the candle idempotently; now only `final_action=LOCK_SKIPPED` triggers lock-busy retry.
5. **Cursor-gap visibility:** if the scheduler's previous processed candle and newest candle differ by >1 timeframe, it emits `RUNNER_CANDLE_GAP`. Gaps crossing market closures must be interpreted in market-session context; this is a warning, not exact missing-bar proof.
6. **Opt-in stale-order guard:** `LIVE_RUNNER_STALE_ORDER_GUARD_ENABLED=true` blocks order execution when a finished evaluation's candle was closed more than `LIVE_RUNNER_MAX_ORDER_AGE_AFTER_CLOSE_SECONDS` ago (default 60). It writes `RUNNER_STALE_SIGNAL_BLOCKED`, does **not** submit an order, and advances the candle cursor to avoid repeatedly acting on the same stale signal. **Default OFF** to preserve current behavior until deliberately enabled. This guard is an execution safety policy and may skip trades; research/backtest live order parity will change when it is ON. Never present it as a performance fix.
7. **Dispatch instrumentation:** `RUNNER_DISPATCH` and `RUNNER_DISPATCH_FINISHED` show the exact start and elapsed time around each automatic strategy invocation.

## What has NOT been fixed and why

- **V6.4 `generate()` acceleration is not implemented.** Strategy definition is loaded from `Strategy.parameters.source_code` inside PostgreSQL. Neither the ZIP nor these logs prove the live stored source and parameters match a particular research `.py`. A safe incremental engine needs that exact code, feature/state dependencies, 80K initialization contract and matched-bar signal parity tests. Shortening the history to 500 bars or blindly caching mutable features would change signals.
- **400s cycle >300s M5 interval is still possible after this patch.** The timing patch tells us exactly where. Do not turn Auto Trade on just because the isolated market-data worker is fast.
- **Long transaction/advisory lock remains unchanged.** Its duration should be redesigned only after a process-level idempotency/claim protocol is proved safe. Releasing it mid-generation without atomic final claims risks duplicate orders.
- **404/504/asyncpg timeouts/Next.js Server Action errors are not claimed resolved.** They require matching proxy, API, DB pool, and frontend request timings.
- No Docker resource limits, core trade rules, V6.4 entry/exit rules, risk size, stop/TP, database migration, `.env.prod`, or Redis state changed.

## Staged deployment — preserve state

1. Snapshot deployed source/Compose, database backup, and broker orders. Record last processed candle and any pending order. Do not deploy while a legacy runner cycle is processing or immediately at M5 close. Keep DEMO Auto Trade OFF during initial profiling.
2. Extract this ZIP to a **new staging folder** and `diff -ru` the currently deployed code. Do not copy over `.env.prod` or Docker volumes. Validate locally:

```bash
python3 production_patch/verify_runner_timing_fix_2026-10-27.py
python3 production_patch/verify_tradelocker_patch.py
python3 -m compileall -q AlgoAgentXAPI/app
# Validate with your server configuration; suppress env secrets in outputs.
docker compose --env-file .env.prod config --quiet
```

3. Build only affected images during a quiet window; ensure free disk first:

```bash
docker compose --env-file .env.prod build live_legacy_runner_worker api
# controlled handoff (existing code already owns exactly one legacy scheduler)
docker compose --env-file .env.prod up -d --no-deps live_legacy_runner_worker
# restart API separately only if Run Once diagnostics must be updated;
# this is not necessary for automatic runner timing logs.
```

4. Prefer leaving both optional switches OFF initially:

```ini
LIVE_STRATEGY_CPROFILE_ENABLED=false
LIVE_RUNNER_STALE_ORDER_GUARD_ENABLED=false
LIVE_RUNNER_MAX_ORDER_AGE_AFTER_CLOSE_SECONDS=60
```

If you choose stale-order fail-closed safety for DEMO, explicitly enable it before the worker restart and accept that late orders will be blocked:

```ini
LIVE_RUNNER_STALE_ORDER_GUARD_ENABLED=true
```

5. Collect logs for **two entire M5 cycles**, then decide whether profiling is required:

```bash
docker compose --env-file .env.prod logs --since=25m --tail=2000 live_legacy_runner_worker | grep -E 'RUNNER_STAGE_|RUNNER_GENERATE_COMPLETE|RUNNER_DISPATCH|RUNNER_CANDLE_GAP|RUNNER_STALE|Legacy scheduler slow'
docker stats --no-stream
```

Look for `stage=strategy_generate wall_s=... cpu_s=...`. If `generate` dominates, the fix is a parity-tested incremental V6.4 engine; if `load_closed_candles` dominates, optimize the index/query; if wall>>CPU during history or DB stages, inspect PostgreSQL wait/connection pools.

## Rollback

- Restore original 2026-10-27 TradeLocker ZIP's `strategy_runner.py`, `auto_runner_service.py` and `config.py` from a saved backup, then rebuild/recreate **only** affected services in a safe window. The new `runner_diagnostics.py` file is harmless if left unused.
- Do not stop/recreate `live_tradelocker_candle_worker`, drop volumes, flush Redis, or reset PostgreSQL to roll back timing instrumentation.
- Reconcile existing broker orders and the processed candle cursor before resuming Auto Trade. If a candle was skipped during downtime, **never submit its historical order blindly**.

## Acceptance gates to unlock further optimization

- At least two runs provide complete timings and exact CPU vs wall evidence.
- Exact DB-stored V6.4 `source_code_sha256`, parameter values, runtime configuration and full baseline strategy source are compared.
- Incremental vs full-history outputs match for each closed bar across out-of-sample replay (signal, SL, TP, features affecting decisions); no look-ahead or missed M5 bars.
- Post-restart state parity, single-position atomicity, deduplication and broker reconciliation verified on DEMO.
- End-to-end candle-close-to-decision time is consistently below the M5 interval **before** enabling unattended demo order placement.
