# AlgoAgentX — V6.4 source-specific optimization / retained framework

## What is actually provided

1. **Existing universal waiting/retained-state engine** remains in `AlgoAgentXAPI/app/services/live/retained_strategy_state.py` and `strategy_runner.py`. It caches a strategy instance ONLY for strategies exposing `LIVE_INCREMENTAL_VERSION=1`, `start_live_incremental(generated)` and `on_closed_candle(candle)`, with explicit per-strategy flags. The legacy worker already waits/polls for the next finalized closed broker candle.
2. `production_patch/v64/V64_BASELINE_RESEARCH_ONLY.py` is a byte-for-byte copy of the V6.4 Python source supplied by the user on 27 October 2026. **Confirm the database-stored deployed source and parameters match before relying on any comparison.**
3. `production_patch/v64/V64_OPTIMIZED_RESEARCH_ONLY.py` is a candidate implementation with **full-history** speed changes only: cached NumPy-backed column access for swing/zone/breakout detection; vectorized causal closed-15M context mapping; periodic pruning of zones marked broken/consumed (not expired zones). No changed filter thresholds, entry/SL/TP calculations or portfolio gate rules are intended.
4. Offline sample parity tests compare every DataFrame output column and passed 7 synthetic scenarios (600–3,500 bars). Dynamic-strategy sandbox loading also passed. This does NOT prove parity on real 80K TradeLocker history or guarantee latency improvement there. A longer 10K run exceeded the available local execution window; no unsupported 80K speed claim is made.
5. **The supplied V6.4 source has no true `on_closed_candle` incremental state transition.** Enabling `LIVE_INCREMENTAL_ENABLED=true` alone will not make this strategy O(1) per candle. A production-grade refactor must retain V3.5 zones/setups/trade tracking, V4.31B trendline/HTF state, and V6.4 portfolio/pending position/rolling indicators and prove every-bar parity against the fixed 80K rolling-window runner. No such refactor is claimed here.

## Important existing code flags

- Keep `LIVE_INCREMENTAL_ENABLED=false` for V6.4 until a separately tested stateful V6.4 implementation exists. Never set DB `live_incremental_parity_verified=true` based solely on this patch.
- `LIVE_RUNNER_STALE_ORDER_GUARD_ENABLED=false` remains the default. Do NOT turn it on if you do not want that optional block. Other risk, position lock and idempotency checks remain unchanged.
- The V6.4 Python file describes itself as **RESEARCH_ONLY** with `live_approved=False` in diagnostics; this release does not change that.

## Validate exact dynamic source

From the project root, run:

```
cd AlgoAgentXAPI
python -m pytest -q tests/test_retained_strategy_state.py tests/test_incremental_parity_cli.py tests/test_live_strategy_history_profile.py tests/test_every_candle_latency_strategy.py tests/test_broker_candle_parity_guard.py
cd ..
python production_patch/v64/test_v64_parity.py
```

These tests use synthetic candles. Source must be imported through `app.services.dynamic_strategy_loader` before use. `production_patch/v64/test_v64_parity.py` also runs standalone with NumPy and Pandas.

For a **real broker** (no order placement) parity check, export complete chronological TradeLocker finalized OHLCV candles to CSV with headers `Date,Open,High,Low,Close,Volume`, then run:

```
python production_patch/v64/verify_broker_csv_parity.py --csv path/to/tradelocker_80000.csv --bars 80000 --report v64_real_parity.json
```

This runs baseline and optimized sources on identical 80K data and compares final signal, stop/target and reason **for every row**. It may take minutes and must be run OFFLINE, not inside the single live strategy worker during market hours. Also compare all source settings/DB parameters and runtime execution. Do not approve from synthetic tests alone.

## Controlled deployment process

1. Back up PostgreSQL (including Strategy.parameters.source_code), Compose, images and `.env.prod`. Do NOT modify a frozen V6.4 strategy record in place; clone/version it for testing.
2. Check code hash/parameters from read-only `app.tools.export_live_strategy_readonly`; the attached Python source might not exactly be the deployed version.
3. Verify real 80K TradeLocker parity, source settings, backtest signal bar/next-open behavior and order fills. Review runtime CPU/RAM with `docker stats --no-stream`.
4. Run optimized candidate only in an isolated DEMO deployment with **Auto Trade OFF**. Compare per-candle signals, strategy timings, gaps, and timestamps against the frozen baseline in a separate controlled evaluation. Do not run both eligible execution workers on the same live deployment.
5. Keep the original source as rollback; revert the cloned strategy to baseline and restore the previous worker image during a quiet period if any divergence occurs. Existing DB cursor and open positions must be verified before trading resumes.

## State machine / the remaining work

```
WAITING → closed candle committed → RUNNING_STRATEGY → evaluated signal
→ checkpoint processed-candle cursor → WAITING
```

The **waiting/scheduling loop** already exists. For V6.4, `RUNNING_STRATEGY` still calls a full `generate()` and can take longer than 300 seconds. The real per-candle speed fix requires extracting a versioned state machine from **both source strategies** and the portfolio gate, with state validity checks, restart recovery and execution parity. This is not solved by a Redis wake-up notification or a 2–3× full-replay micro-optimization.

## Technical validation and constraints

- Python compile passes; offline parity cases passed.
- Dynamic source loader accepted both baseline and optimized strategy source.
- Existing retained framework focused tests passed after updating one outdated test assertion to the **already-configured 200,000 history-bar cap**. Runtime cap unchanged.
- No Oracle, Docker, production DB, TradeLocker, live order submission or genuine 80K signal replay performed in this environment.
- `.env` files, credentials, runtime directories and uploaded historical private data excluded from the deliverable.
