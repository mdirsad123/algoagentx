# AlgoAgentX V6.4 — Optional Hybrid DEMO Runner (28 Oct 2026)

**Classification: RESEARCH MONITOR INTEGRATION / NOT PRODUCTION PARITY APPROVED.**

## What changed

- `AlgoAgentXAPI/strategies/v64_hybrid_incremental.py`: preserves the combined V6.4 `generate()` behavior and offers V3.5 retained-state / trendline+portfolio replay. This is the previously measured **experimental hybrid**, NOT a fully per-candle V4.31B or V6.4 gate implementation.
- `AlgoAgentXAPI/app/services/live/v64_hybrid_gate.py`: fail-closed selector. Uses experimental class ONLY for DEMO XAUUSD(.X) M5, exact 80K history, exact pinned frozen DB source SHA, and explicitly authorized runtime switches. **No Strategy database mutation.**
- `AlgoAgentXAPI/app/services/live/strategy_runner.py`: optional runtime selector and normal retained cache; detailed selection/latency logs. `MONITOR_ONLY=true` additionally suppresses DEMO broker order submission in the legacy runner even if the hybrid source gate fails and falls back to FULL_HISTORY, or Dashboard Auto Trade is accidentally ON. Rebuilds exact rolling 80K history after configurable 48 incremental advances, to bound history growth.
- `AlgoAgentXAPI/app/core/config.py`: four new optional flags (all OFF by default except rebase interval), plus source hash authorization.
- `AlgoAgentXAPI/tests/test_v64_hybrid_gate_20261028.py`: activation-denial/authorization checks.
- `production_patch/v64/verify_hybrid_80k_replay.py`: offline full-history + rolling-bar parity CLI (no order writes, no broker API).
- `WATCH_V64_HYBRID.ps1`: read-only log viewer.

**What did not change:** saved PostgreSQL Strategy code/params, 1% risk, historical candle DB, TradeLocker candle collector, broker order safety checks, standalone V3.5 research baseline, or Docker volumes. No changes to `.env.prod` have been bundled.

## Offline checks on the supplied (not broker-verified) XAUUSD CSV

- Frozen source SHA256: `7122bb951cd867f3cd57f66d2fef6b6307e708c7c4a5547d42aaab79a2bbb5cb`.
- Cold 80K full historical comparison: 488 signals on each source, matching Position, SL, TP and reason for every one of the 80K historical rows. Original ~108.65s; candidate ~40.61s (this machine).
- One 80K rolling candle: frozen full 116.36s; candidate hybrid incremental 11.50s; HOLD matches including reason/SL/TP (this machine).
- Second independent 80K window ending at **2026-10-16 11:20 UTC**: rolling original 102.06s; hybrid 10.86s; both HOLD matched. **Important:** that same timestamp gave a BUY in a different 3,000-candle input window; signals therefore depend on history length. This is exactly why the live 80K requirement is retained. This test is NOT an 80K rolling BUY match.
- Prior tests from this context included a BUY and four following candles at 3K, matching `Position`, `SL`, `TP`, and `reason`.
- Automated Python: 13 tests passed, 8 synthetic strict rolling-bar comparisons passed, 600-bar full historical + 3 rolling comparisons passed.
- These are **offline local-machine results, not Docker live-order or actual TradeLocker 80K data tests**. They do NOT demonstrate continued parity through tens of thousands of sliding candles, high trading activity, restart, 15M boundaries, or live fills. The periodic cold rebase is a containment measure, not proof of parity. **Only use monitor-only until exact live-broker parity is independently established.**

## Windows PowerShell — safe deployment and monitoring

1. From `D:\Stock_market\algoagentx`, make a backup of the existing repo, and verify that the `live_legacy_runner_worker` is not currently submitting an order. In the Dashboard, set **Auto Trade OFF**. Keep broker reconciliation and position management services running if positions are open.
2. Extract this ZIP to a *temporary sibling folder*. Copy its source tree **over your existing repo**; do NOT replace your `.env.prod`, PostgreSQL or Redis volumes. If you use Git, inspect `git diff` before rebuild. Do not extract a second `.env.prod` over your own.
3. First rebuild only the strategy runner while flags are OFF:

```powershell
cd D:\Stock_market\algoagentx
docker compose --env-file .env.prod config --quiet
docker compose --env-file .env.prod up -d --no-deps --build live_legacy_runner_worker
```

**Full-history mode remains the original baseline until you deliberately opt in.**

4. Export the exact active database strategy SHA read-only (replace deployment UUID with your current one; create a unique filename each time):

```powershell
docker compose --env-file .env.prod exec -T api python -m app.tools.export_live_strategy_readonly `
  --deployment-id YOUR_CURRENT_DEPLOYMENT_UUID --out /tmp/v64_active_20261028.py
docker cp algoagentx_api:/tmp/v64_active_20261028.py .\v64_active_20261028.py
(Get-FileHash .\v64_active_20261028.py -Algorithm SHA256).Hash.ToLower()
```

The project-candidate frozen source was SHA `7122bb...` above. If the DB source differs, the gate will log `db_source_sha_not_frozen_reference` and keep normal FULL_HISTORY mode. **Do not force-match a different source or use flags to pretend parity.**

5. For **monitor-only** testing, if the active DB SHA matches the frozen file, edit **your local existing** `.env.prod` (do not upload it or reveal tokens) to contain exactly one of each:

```ini
LIVE_INCREMENTAL_ENABLED=true
LIVE_V64_HYBRID_ENABLED=true
LIVE_V64_HYBRID_MONITOR_ONLY=true
LIVE_V64_HYBRID_PARITY_APPROVED=false
LIVE_V64_HYBRID_MAX_ADVANCES=48
LIVE_V64_HYBRID_AUTHORIZED_SOURCE_SHA256=PASTE_EXACT_ACTIVE_DATABASE_SOURCE_SHA256
LIVE_RUNNER_STALE_ORDER_GUARD_ENABLED=false
```

Then recreate only `live_legacy_runner_worker` **after it is idle**. It will perform a cold 80K baseline-compatible initialization, then next consecutive M5 candle(s) should run `RETAINED_INCREMENTAL`. **MONITOR_ONLY always suppresses DEMO broker order submission from this runner, including FULL_HISTORY fallback.** Other services are not disabled by this switch; Dashboard Auto Trade should stay OFF.

```powershell
docker compose --env-file .env.prod up -d --no-deps --force-recreate live_legacy_runner_worker
.\WATCH_V64_HYBRID.ps1
```

6. For offline verification against a **genuine completed TradeLocker UTC 80K+ candle CSV**, use an exported DB strategy file plus an exact non-secret parameters JSON:

```powershell
cd D:\Stock_market\algoagentx
python production_patch\v64\verify_hybrid_80k_replay.py `
  --csv tradelocker_m5_utc.csv `
  --baseline v64_active_20261028.py `
  --candidate production_patch\v64\V64_HYBRID_INCREMENTAL_EXPERIMENT.py `
  --params-file safe_strategy_params.json `
  --bars 80000 --checks 3 --report v64_hybrid_broker_parity.json
```

`--params-file` is optional only when there are no custom active strategy parameters; if your deployment has parameters, include them. The script does not make network calls or orders. Also validate rolling cases containing BUY/SELL, 15M boundaries, repeated candles, and history expiration. One HOLD comparison is NOT an approval.

## Expected worker log markers

- `RUNNER_V64_HYBRID_SELECTED ... monitor_only=True`: exact SHA/source/runtime gate matched.
- `RUNNER_INCREMENTAL_PRIMED ... bars=80000`: retained warmup initialized.
- `RUNNER_STAGE_DONE ... stage=strategy_incremental_update wall_s=...`: incremental timing.
- `RUNNER_GENERATE_COMPLETE ... mode=RETAINED_INCREMENTAL`: fast path actually used.
- `RUNNER_V64_HYBRID_MONITOR_ORDER_SUPPRESSED`: signal emitted but intentionally no broker order.
- `RUNNER_V64_HYBRID_REBASE`: periodic fresh rolling 80K cold rewarm (expect slow cycle).
- `RUNNER_V64_HYBRID_NOT_SELECTED ...`: flag/source/mode/history mismatch; unchanged full-history fallback.
- `RUNNER_INCREMENTAL_INVALIDATED`, `RUNNER_CANDLE_GAP`, `RUNNER_INCREMENTAL_RETRY_COLD`: gaps and recovery. Record these; don't assume execution parity.

**Important:** If source SHA differs, no improvement occurs. If you leave `MONITOR_ONLY=true` no automatic orders are submitted by this runner. If you later wish to enable DEMO order submissions, do so only after comprehensive active-broker parity and explicit review: set `MONITOR_ONLY=false`, `PARITY_APPROVED=true`, confirm active source SHA and broker positions, and operate with safeguards. This has **NOT** been approved in this package.

## Quick rollback

1. In `.env.prod`, set `LIVE_V64_HYBRID_ENABLED=false` and `LIVE_INCREMENTAL_ENABLED=false`; leave your saved Strategy DB source unchanged.
2. After verifying no order is in-flight, recreate only the runner:

```powershell
docker compose --env-file .env.prod up -d --no-deps --force-recreate live_legacy_runner_worker
```

The original `FULL_HISTORY` code path resumes; no database rollback needed. Avoid `docker compose down -v`, Redis `FLUSHALL`, volume pruning, resetting history or restarting broker position managers blindly.
