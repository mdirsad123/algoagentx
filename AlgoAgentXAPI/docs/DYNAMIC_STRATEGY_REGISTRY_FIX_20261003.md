# AlgoAgentX Dynamic Strategy Registry Fix — 03 Oct 2026

## Problem fixed

Admin-created/versioned strategies could contain the latest `source_code` in PostgreSQL, but live strategy resolution could still fall through a broad static name match. In particular, any name containing `Resistance Rejection` could resolve to the old static `XAUUSD 5M Resistance Rejection V1` class when `engine_mode=DYNAMIC_DB` was missing from an older Strategy row.

That allowed a deployment selected as V3.5 to execute V1 instead of failing.

## Final architecture

Admin/DB source code is now authoritative:

1. Strategy `source_code` exists in `Strategy.parameters` -> execute that exact source through the Dynamic DB loader.
2. `source_code` exists but cannot load -> hard error. No static fallback.
3. `engine_mode=DYNAMIC_DB` but source code is missing -> hard error.
4. Static registry is used only when there is no DB source code.
5. Versioned static strategies resolve only by exact registered name; an unknown future V3.6 cannot silently become V1.

This means future Admin-created versions do **not** require manual edits to `strategy_registry.py`.

## Admin Save / Duplicate / Rollback behavior

- Any saved non-empty `source_code` automatically gets:
  - `engine_mode = DYNAMIC_DB`
  - `source_code_sha256 = <sha256>`
- This works whether source code arrives as the top-level Admin field or inside `parameters`.
- Duplicate preserves the dynamic source/runtime metadata but clears old Verify/Sandbox evidence.
- Rollback restores the old source, marks it Dynamic DB, and returns the strategy to Private/Under Development for re-verification.
- Saving unchanged code no longer clears Verify/Sandbox evidence.
- Changing executable code/config on a Published strategy automatically moves it to Private so the changed version cannot remain published under stale verification. Run Verify Code + Sandbox + Publish again.

## Current exact static fallbacks added

These are safety fallbacks only when DB `source_code` is absent:

- `XAUUSD 5M Resistance Rejection V3.5`
  - `XAUUSD5MSupplyDemandRejectionV35CandidateA`
- `Trend-Following Breakout V1.37`
  - `XAUUSD5MTrendBreakoutV137`

When Admin DB source exists, DB source always wins over these static fallbacks.

## Live audit fields added

Every newly persisted live signal now records:

- `strategy_name`
- `canonical_strategy`
- `resolved_strategy_class`
- `engine_mode`
- `source_code_sha256`

This makes a future strategy-version mismatch visible immediately in exported `live_signals`.

## Dynamic loader cache

Dynamic strategy classes are cached by exact source text (max 64 entries). Unchanged code is not recompiled on every live candle. Editing/saving code creates a new cache key automatically, so the next run loads the new version.

## Safe deployment steps

1. Stop the existing V3.5 live deployment before replacing/restarting backend code. Do not change the strategy engine underneath an open live position.
2. Replace the project with this updated package.
3. Rebuild relevant services:

```bash
docker compose --env-file .env.prod up -d --build api live_strategy_worker celery_worker web
```

4. Open V3.5 in Admin Strategy Workspace and press **Save Strategy** once. If the older row was Published without Dynamic DB metadata, it may move to Private intentionally.
5. Run **Verify Code**.
6. Run **Sandbox Backtest**.
7. Publish the strategy again.
8. Create a fresh live deployment.
9. On the first BUY/SELL live signal, export/check `raw_payload`. Expected V3.5 values:

```text
strategy_name          = XAUUSD 5M Resistance Rejection V3.5
canonical_strategy     = XAUUSD 5M Resistance Rejection V3.5
resolved_strategy_class= XAUUSD5MSupplyDemandRejectionV35CandidateA
engine_mode            = DYNAMIC_DB
source_code_sha256     = <non-empty hash>
```

For Trend-Following V1.37, expected class:

```text
XAUUSD5MTrendBreakoutV137
```

## Future version flow

For V3.6 / V3.7 / V4 etc.:

```text
Duplicate/Create -> edit Source Code -> Save -> Verify -> Sandbox -> Publish -> Deploy
```

No manual Python registry edit is required. If source is missing/broken, deployment resolution fails instead of running an older strategy.

## Validation performed

- Python compile checks passed for all changed backend files and both new strategy modules.
- Dynamic strategy registry test suite: 8 passed.
- Both uploaded strategy sources passed the Dynamic DB security/loader validation.
- Both uploaded strategies were instantiated and executed successfully on synthetic 5-minute OHLCV data through the Dynamic DB loader.
- Both exact static fallback entries were also instantiated/executed successfully.

Full API/live integration test collection was not runnable in this sandbox because the host Python environment does not have all project runtime packages (`python-jose`, `redis`). Those packages are already project/Docker dependencies; this was an execution-environment limitation, not a code syntax failure.
