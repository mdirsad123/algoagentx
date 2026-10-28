# V6.4 Hybrid Retained-State Candidate — DEMO/RESEARCH ONLY

## Important distinctions

- The *existing* legacy worker already waits for new TradeLocker M5 candles. Previous performance logs show that 80K `generate()` is the bottleneck, not the status polls.
- This patch adds `production_patch/v64/V64_HYBRID_INCREMENTAL_EXPERIMENT.py`, a source-specific dynamic strategy candidate. It retains V3.5 zone, setup, counter and pending-trade state after one full warmup. For each later finalized candle it advances V3.5 by one bar, **but recomputes V4.31B trendline signals and the V6.4 portfolio gate on accumulated historical candles**. Therefore this is HYBRID, not fully O(1), and it is **NOT guaranteed to process real 80K bars within 60 seconds**.
- Synthetic rolling-window tests comparing the entire output row pass. No real TradeLocker 80K candle CSV, executed broker-fill comparison, or true uninterrupted M5 forward-test was supplied in this session. The experiment has **not** been certified against the DB-stored deployed strategy source or parameters.
- The existing code in `AlgoAgentXAPI/app/services/live/retained_strategy_state.py` offers process-local per-deployment retention, contiguous M5 guard, source/runtime fingerprint guard, and cold warmup on restart. A restart still needs full warmup. The code retains V6.4 source algorithm only when the new candidate is selected for an explicit experimental deployment.
- The V3.5 candle transition is copied from the original `generate` loop, including zone lifecycle, pending entries and stop/target calculations. Only after independent real-history full-vs-hybrid parity AND runtime checks should an operator consider enabling demo orders.

## Offline validation, no broker calls or orders

1. Export at least 80,010 authentic finalized candles from the same broker/symbol/timeframe in chronological UTC order with `Date,Open,High,Low,Close,Volume` headers. **Use active strategy `strategy_params` exactly** (not assumed defaults).
2. From project root:

```bash
cd AlgoAgentXAPI
python -m pytest -q tests/test_retained_strategy_state.py tests/test_incremental_parity_cli.py
cd ..
python production_patch/v64/test_hybrid_incremental.py --short
python -m py_compile production_patch/v64/V64_HYBRID_INCREMENTAL_EXPERIMENT.py
```

3. For the real 80K CSV, from `AlgoAgentXAPI` working directory (source path adjusted):

```bash
python -m app.tools.check_live_incremental_parity \
  --source ../production_patch/v64/V64_HYBRID_INCREMENTAL_EXPERIMENT.py \
  --csv ../tradelocker_m5_80010.csv --history-bars 80000 --checks 10 \
  --parameters-json '{}' --report ../v64_incremental_80k_parity.json
```

Replace `{}` with actual JSON strategy parameters. This will be **very CPU-expensive** since the checker runs full 80K reference `generate()` 10 times. Run it *offline*, **not on the live order execution worker**. For extra confidence compare all output columns, final signal reason/SL/TP and the source hash, and validate many rolling candles and difficult market regimes. Do not approve solely on the 10 samples.

## `LIVE_INCREMENTAL_ENABLED=true` — when?

**Keep false now.** `LIVE_INCREMENTAL_ENABLED=true` is only a global allowance, not a proof of correctness. The shared runner additionally requires all of these:

- The active Strategy DB record must contain the tested candidate source with `LIVE_INCREMENTAL_VERSION = 1`, `start_live_incremental`, `on_closed_candle`.
- In its `Strategy.parameters`, set `"live_incremental_enabled": true` and `"live_incremental_parity_verified": true` only after full source-hash and exact real 80K rolling-window parity approval.
- Enable `LIVE_INCREMENTAL_ENABLED=true` globally only after validation of the experimental deployment; restart the *one* `live_legacy_runner_worker` replica during a quiescent demo window.

For an unchanged V6.4 DB record, toggling the global flag **does not** accelerate anything. NEVER set parity_verified based only on these synthetic checks. The default environment `.env.prod.example` stays false. The optional stale-order guard remains false as previously requested.

## Safe rebuild — staging and backups first

1. Back up `.env.prod`, source, existing Strategy DB record including DB-stored source/parameters, and PostgreSQL; preserve volumes. Check the source-hash of the deployed record. Clone the strategy for tests; **do not overwrite the frozen production V6.4 record**.
2. Build in staging; run the tests above and `docker compose --env-file .env.prod config --quiet`.
3. If the only code change is a DB-strategy version, rebuilding Docker does not update DB source; make the cloned strategy source selection deliberately. Avoid simultaneous workers on the same deployment.
4. For **backend/worker source changes**, during a safe demo window and with execution disabled, rebuild/recreate exactly one legacy worker:

```bash
docker compose --env-file .env.prod build live_legacy_runner_worker
docker compose --env-file .env.prod up -d --no-deps --force-recreate live_legacy_runner_worker
```

If the API backend changed and needs the new code, build/recreate `api` **separately**, and only if required. A DB-only strategy source update requires no image rebuild. `live_tradelocker_candle_worker`, Redis, PostgreSQL, `live_history_worker` and UI are **not** to be restarted just to change a strategy source. Never `docker compose down -v` / prune DB/Redis volumes.

5. Verify exactly one legacy runner, heartbeat continuously updating, cold `FULL_HISTORY` once then `RETAINED_INCREMENTAL` only after parity-controlled activation, and inspect cursor and signal/order idempotency. If any difference occurs, turn Auto Trade OFF, set global `LIVE_INCREMENTAL_ENABLED=false`, recreate worker in a quiet demo window, verify positions/cursor, then return to the frozen source.

## Important failure / performance limits

- Code-level full-history source optimized variant is still independent from DB-stored active source; this package does not silently mutate PostgreSQL strategies.
- Strict parity on small synthetic data is NOT sufficient to claim real 80K equality, long-lived rolling-window equivalence, or <60-second execution.
- The V4.31B and V6.4 gate remain O(N) / event calculations, which may still exceed your desired deadline. Use the reporter timings on real 80K candles before enabling Auto Trade.
- Do not remove `RUNNING`/Auto Runner, duplicate-order locks, broker position reconciliation or other safety checks. Measured status-check durations were sub-second; calculation takes hundreds of seconds.
