# AlgoAgentX — Gold V9.32 source-pinned hybrid incremental deployment

**Status: EXPERIMENTAL / DEMO MONITOR ONLY. HARD-BLOCKED for broker orders and LIVE accounts due to a confirmed right-edge signal mismatch in the frozen V9.32 source.**

## 1. What changed

The original V9.32 DB/source code was **not edited**. The identical source is saved at
`AlgoAgentXAPI/strategies/v932_original_db_source.py`, and its SHA256 *after
stripping exterior whitespace* is:

`a63659f9b6a4d0302165b94e9889b5da35e6fd2f4020d5893516ba4def9ad512`

This matches the normalized V9.32 SHA in the user's PostgreSQL screenshot.
The source file with its trailing newline has a different raw SHA. Do **not**
substitute that raw hash for the normalized DB hash shown above.

- `app/services/live/v932_hybrid_gate.py` — DEMO-only, exact source hash, exact 80K
  history, instrument M5 and parity authorization gate.
- `app/services/live/incremental_adapter_registry.py` — V9.32 adapter selection,
  legacy V6.4 preserved, per-instrument fail-closed helper.
- `strategies/v932_pinned_strategy.py` — frozen V9.32 implementation with a
  *checked precomputed horizontal signal history* injection point. With no
  cache, it executes the same original source semantics as V9.32.
- `strategies/v932_incremental.py` — retains the V3.5 horizontal state controller;
  replays V4.31B, portfolio arbitration, all V8/V9 added entries, vetoes and
  completed HTF aggregation on each new closed candle. State is separated by
  deployment ID by the unchanged generic cache.
- `app/core/config.py` — optional
  `LIVE_INCREMENTAL_REQUIRE_ADAPTER_INSTRUMENTS` setting.
- `app/services/live/strategy_runner.py` — fail closed for selected DEMO
  instruments without an adapter; use generic log name for periodic rebase;
  keeps V6.4-only legacy log marker exclusive to V6.4.
- `tests/test_v932_incremental_adapter.py` — source, gate and small-window
  real-candle parity smoke tests.
- `app/tools/verify_v932_incremental_parity.py` — exact-source offline
  full-history vs hybrid output and wall-time verifier.

**Important performance limitation:** This is **hybrid retained-state**, not
fully O(1) incremental. The base V3.5 subsystem advances by one candle, but
V4.31B and every V9 calculation still replay full retained history. Cold
warmup and periodic rebase still run original full-history calculations.
Do not claim V9.32 is under 60 seconds per 80K candle without measurement.

## 2. Preserve and redeploy V9.32

Before changing files, back up the existing project, `.env.prod`, database,
config and Docker definitions and confirm broker positions and copy orders are
reconciled. Keep old V6.4 strategy record intact for rollback. Disable Auto
Trade and stop or undeploy the V6.4 deployment after open orders are safely
managed. Do NOT delete a deployment holding active orders.

Extract the delivered ZIP to a **separate** staging folder first, then merge
its changed source files into `D:\Stock_market\algoagentx`. Do NOT blindly
replace production secrets with the included snapshot `.env.prod`.

**Recommended safe install on Windows:** Extract this ZIP into a separate
staging folder, open PowerShell in that staging folder and run:

```powershell
powershell -ExecutionPolicy Bypass -File .\INSTALL_V932_SAFE.ps1 -TargetRoot D:\Stock_market\algoagentx -ApplyMonitorEnv
```

The installer backs up replaced source files and `.env.prod` outside the
project directory, copies only the 10 new/changed backend files, and sets
monitor-only environment values. It does **not** restart Docker, change the
DB, place orders, or clear data. Omit `-ApplyMonitorEnv` if you prefer to
merge the environment values manually. `INSTALL_V932_SAFE.ps1` has not been
executed on your Windows/Docker host and should be reviewed before use.

The V9.32 strategy already exists in PostgreSQL. Confirm (read-only):

```sql
SELECT id,name,
       parameters->>'source_code_sha256' AS source_sha,
       parameters->>'live_history_bars' AS history_override
FROM strategies
WHERE name ILIKE '%V9.32%';
```

Expected normalized source SHA:
`a63659f9b6a4d0302165b94e9889b5da35e6fd2f4020d5893516ba4def9ad512`

Use a NEW XAUUSD M5 TradeLocker DEMO deployment for V9.32, leaving V6.4
unchanged as archived rollback. Only the source pinned to that exact hash
is eligible for this adapter.

## 3. `.env.prod` for initial DEMO MONITOR ONLY

Use the provided `V932_DEMO_INCREMENTAL_ENV.txt`. Verify there is only one
value of each key. Required:

```ini
LIVE_INCREMENTAL_ENABLED=true
LIVE_INCREMENTAL_ADAPTER_ENABLED=true
LIVE_INCREMENTAL_MONITOR_ONLY=true
LIVE_INCREMENTAL_PARITY_APPROVED=false
LIVE_INCREMENTAL_AUTHORIZED_SOURCE_SHA256=a63659f9b6a4d0302165b94e9889b5da35e6fd2f4020d5893516ba4def9ad512
LIVE_INCREMENTAL_MAX_ADVANCES=48
LIVE_INCREMENTAL_REQUIRE_ADAPTER_INSTRUMENTS=XAUUSD,XAUUSD.X
LIVE_STRATEGY_HISTORY_OVERRIDE_BARS=80000
LIVE_STRATEGY_HISTORY_DEFAULT_BARS=80000
LIVE_STRATEGY_HISTORY_MAX_BARS=200000
```

`LIVE_INCREMENTAL_MONITOR_ONLY=true` is a **global** DEMO order suppressor
for registered adapter monitoring. If you have other DEMO deployments still
running, coordinate this change with them: their order submission may also
be blocked. The `REQUIRE_ADAPTER_INSTRUMENTS` guard itself applies only to
Gold (`XAUUSD`, `XAUUSD.X`). These settings do not authorize LIVE accounts.

**Why OVERRIDE_BARS=80000?** V9.32 inherits `LIVE_HISTORY_BARS=24000`
from its base class, while its tested Gold configuration and this exact
adapter gate use **80,000 bars**. The screenshot shows its DB
`live_history_bars` unset. Setting `OVERRIDE_BARS=0` without first storing
an explicit 80K per-strategy profile would select 24K and reject this adapter.

## 4. Rebuild and inspect

From PowerShell `D:\Stock_market\algoagentx`:

```powershell
docker compose --env-file .env.prod config --quiet
docker compose --env-file .env.prod up -d --build --no-deps --force-recreate live_strategy_worker live_legacy_runner_worker
docker compose --env-file .env.prod exec -T live_legacy_runner_worker python -c "from app.core.config import settings as s; print(s.live_incremental_enabled,s.live_incremental_adapter_enabled,s.live_incremental_monitor_only,s.live_incremental_parity_approved,s.live_incremental_authorized_source_sha256,s.live_strategy_history_override_bars,s.live_incremental_require_adapter_instruments)"
docker logs --since 30m algoagentx_live_legacy_runner_worker 2>&1 | Select-String -Pattern "RUNNER_INCREMENTAL_ADAPTER_SELECTED|v932_hybrid_v1|RUNNER_INCREMENTAL_PRIMED|RETAINED_INCREMENTAL|RUNNER_INCREMENTAL_ADAPTER_FALLBACK|HOLD_INCREMENTAL_ADAPTER_REQUIRED|RUNNER_GENERATE_COMPLETE"
```

Restart each worker actually running the strategy (check `docker ps` and
service logs first). For a startup/candle simulation, the first calculation
will be FULL_HISTORY; the next consecutive M5 candle should show
`RETAINED_INCREMENTAL` only after `RUNNER_INCREMENTAL_PRIMED bars=80000`.
If the adapter is unavailable, the Gold DEMO **holds** with
`HOLD_INCREMENTAL_ADAPTER_REQUIRED` rather than silently placing an order
from FULL_HISTORY. Weekend gaps/worker restarts trigger a cold rebuild.

## 5. Offline tests — required before any approval

```powershell
# From the repository root, after building the backend image:
cd AlgoAgentXAPI
python -m pytest -q tests/test_v932_incremental_adapter.py tests/test_incremental_adapter_registry_20261028.py
cd ..

# From AlgoAgentXAPI on a local Python environment with project dependencies:
python -m app.tools.verify_v932_incremental_parity --csv ../artifacts/backtest_private/xauusd.csv --history 80000 --steps 4 --output ../V932_PARITY_80000.json
```

The CSV packed with the snapshot ends **2026-11-04 18:25 UTC**, not at the
current broker candle. For a true live-parity audit, export *the same exact
80K closed TradeLocker candles* used by your active deployment and compare
at least many consecutive closes and every non-HOLD signal, SL, TP and
reason. Include realistic gap/restart/cold-rebase cases. Measure cold and
incremental wall times and end-to-end candle close→broker decision latency.

The recorded 5K real-candle local smoke result is stored as
`V932_PARITY_5000.json`; it is **not** 80K certification. Verify at
least 80K and multiple BUY/SELL decisions before changing these switches.

## 6. Critical strategy-level right-edge discrepancy (BLOCKER)

Reproduced using the original uploaded V9.32 source and genuine XAUUSD M5 data:

- On **2026-11-04 17:30 UTC**, a replay with 11 later candles produces
  `V432A_COMPRESS_LONG|V62_COMPRESSION_BREAK_LONG` (BUY) with SL
  4062.5889285714284 and TP 4081.312142857143.
- Re-running that same source with **17:30 as the newest available closed
  candle** returns HOLD, no SL, no TP.

This is recorded in `V932_RIGHT_EDGE_AUDIT.json` and is reproducible with
`python -m app.tools.audit_v932_right_edge --csv ../artifacts/backtest_private/xauusd.csv --lookback 10000 --target 2026-11-04T17:30:00Z --output ../V932_RIGHT_EDGE_AUDIT.json`.
Several original V9.x families use `np.r_[... , False]` and next-bar
checks, and some V6.x arrays intentionally exclude the final bar. The
result is that historically seen entries need not appear at the live
right edge. **The incremental adapter faithfully preserves the source's
actual current-bar semantics; changing its output to force these entries
would change the strategy and require a new backtest/source hash.**

Because this discrepancy is now established, the V9.32 adapter rejects
`MONITOR_ONLY=false` even when `PARITY_APPROVED=true`. Gold DEMO remains
HOLD via the instrument-specific strict guard. To permit automated broker
orders, produce a **new causally corrected research strategy** (new SHA),
replay full native backtests, and validate its revised incremental adapter.
Do not silently patch V9.32 logic under the old approved SHA.

## 7. Release criteria and safety

Do not set `LIVE_INCREMENTAL_MONITOR_ONLY=false` with
`LIVE_INCREMENTAL_PARITY_APPROVED=true`: the code rejects V9.32 order mode
until a new strategy version fixes the proven right-edge discrepancy.
Additional 80K parity, real TradeLocker candles, next-open execution,
copy trading, restarts and measured timing remain required for the revised
version. This bundle intentionally ships **unapproved**. The source calls several parts `RESEARCH_ONLY`.

For this V9.32 hybrid the runner also enforces a **maximum 60-second stale
order window** even when the global stale-order guard is off, to avoid
submitting delayed orders after a slow cold/rebase calculation. If the
calculation runs late, that candle is held, not traded.

The `LIVE_INCREMENTAL_AUTHORIZED_SOURCE_SHA256` flag authorizes **one** pinned
source. V9.33 or other future revisions need a newly reviewed adapter or a
strategy-native implementation, new fingerprint and repeat parity evidence.
The registry is extensible; changing SHA alone cannot convert code.

## 8. Rollback

Do not edit V6.4 DB source. Revert `.env.prod` from your backup, restore
unchanged V6.4 DEMO deployment after ensuring no conflicting primary/copy
positions and rebuild the workers. Setting
`LIVE_INCREMENTAL_ADAPTER_ENABLED=false` turns off experimental adapters,
but with `LIVE_INCREMENTAL_REQUIRE_ADAPTER_INSTRUMENTS` still set,
Gold DEMO **remains HOLD**. To intentionally use FULL_HISTORY after a
reviewed rollback, remove the Gold instrument names from the strict guard.
Keep Auto Trade OFF during rollback and validate source, history, account
and SL/TP before enabling.
