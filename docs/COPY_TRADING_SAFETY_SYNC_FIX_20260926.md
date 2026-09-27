# AlgoAgentX Copy Trading Safety + Broker Truth Fix

Date: 26 Sep 2026

## Goal

Keep the existing primary-account execution path intact and make copy trading safe across independent MT5/cTrader accounts.

## Root causes fixed

### 1. Copy orders inflated the primary order count
The deployment summary previously counted every `live_orders` row for a deployment. A single signal copied to Primary + Copy A + Copy B therefore appeared as 3 orders.

Fix:
- Primary `Orders Today`, total orders, recent orders, primary PnL and primary open positions are now filtered by the deployment's primary `broker_account_id`.
- Copy orders are returned separately as `copy_orders` and `copy_orders_today`.
- The Live Trading detail page has a new **Copy Trading Orders** table showing target account, broker, side, symbol, qty, prices, status, broker order id and errors.
- Dashboard/readiness/final-QA primary metrics no longer count copy replicas as primary trades.

### 2. Copy accounts could exceed max-open-position protection
The broker reconciliation query previously loaded every OPEN `LivePosition` for the deployment, regardless of broker account. A primary-account sync could therefore mark copy-account positions CLOSED because those positions were not present on the primary broker response.

Fix:
- `reconcile_positions()` is now scoped by both `deployment_id` and `broker_account_id`.
- `reconcile_orders()` is also account-scoped.
- Each copy target performs an independent broker-position refresh before risk/max-open-position checks.
- MT5 copy position refresh requires a fresh MT5 Agent heartbeat; stale state fails that copy target safely rather than risking duplicate exposure.
- cTrader position filtering accepts canonical/suffix aliases such as `XAUUSD` / `XAUUSDm`.

Result:
- `max_open_positions=1` is enforced independently using broker truth for Primary, Copy A, Copy B, etc.
- A position closed early on one broker does not incorrectly affect another broker's state.

### 3. cTrader primary -> MT5 copy sometimes returned `SL/TP missing or zero`
A reversal/close on MT5 was routed through the normal `PLACE_ORDER` path. Entry orders correctly require SL/TP, but a position close should not require new SL/TP. On MT5 hedging accounts, sending an opposite entry without a `position` ticket can also create a second position instead of closing the existing one.

Fix:
- Added a dedicated `CLOSE_POSITION` MT5 Agent command.
- Broker reconciliation stores the MT5 position ticket in `LivePosition.broker_position_id`.
- Backend queues close by ticket whenever possible.
- Windows MT5 Agent sends `TRADE_ACTION_DEAL` with the MT5 `position` ticket and opposite side.
- Close commands do not require SL/TP.
- A queued close remains `PLACED`; local position stays OPEN until the agent confirms the close. The engine will not open replacement risk while close confirmation is pending.

### 4. `No MT5 tick found for XAUUSD`
Some MT5 terminals can select a clean alias like `XAUUSD` even when only `XAUUSDm` has a live quote.

Fix:
- MT5 symbol resolver ranks canonical/alias candidates and requires a live tick before using a symbol.
- Example: requested `XAUUSD` -> skips no-tick `XAUUSD` -> selects live `XAUUSDm`.
- Existing suffix forms such as `XAUUSD.c` continue to work.

## Final safety model

```text
ONE strategy signal
        |
        v
Primary account
(existing execution path unchanged)
        |
        v
Copy router
        |
        +--> Copy A: refresh broker positions -> account risk/max-open -> execute
        +--> Copy B: refresh broker positions -> account risk/max-open -> execute
        +--> Copy C: refresh broker positions -> account risk/max-open -> execute
```

Do not globally block all copy targets only because Primary has a position. Broker accounts can legitimately diverge because of fills, slippage, SL/TP or manual closure. The correct guard is **independent broker-truth + max-open-position checks per target account**.

## Important Windows MT5 Agent update

MT5 Agent code changed. The updated downloadable agent ZIP is included at:

`AlgoAgentXAPI/storage/downloads/AlgoAgentXMT5Agent.zip`

If the Windows agent is run from Python files, replace/restart it. If an `.exe` is used, rebuild the EXE from this updated source before testing the cTrader -> MT5 copy/reversal path.

Agent code version default: `0.4.2-copy-close-symbols`.

## Database

No new SQL migration is required for this fix.

## Validation performed

- Python compile: passed for `app` and `AlgoAgentXMT5Agent`.
- Focused backend regression tests: 20 passed.
  - primary copy-trading regression
  - expired ORM regression
  - cross-broker symbol resolution
  - account-scoped position reconciliation
  - MT5 true position close + live-tick symbol selection
  - cTrader idempotency
  - generic order idempotency
  - Redis/order duplicate claim
  - latency trace
- Full pytest collection cannot complete in this sandbox because the environment lacks the `asyncpg` Python package required by unrelated DB-session tests.
- Updated TS/TSX files were syntax-parsed successfully with TypeScript 5.8.3. This sandbox does not contain the project's `node_modules`, so a full Next.js production build was not run here.

## Docker rebuild

Because backend, Web UI, broker sync and worker-imported code changed:

```bash
docker compose --env-file .env.prod up -d --build --force-recreate api web live_market_worker live_strategy_worker live_reconcile_worker
```

PostgreSQL and Redis do not need to be recreated.

## Suggested verification order

1. Primary only, Copy Trading OFF: verify original behavior.
2. Primary + one copy: verify one primary order plus one row in Copy Trading Orders.
3. Keep `max_open_positions=1`: next same-side signal should be rejected independently on every account that still has a live position.
4. Manually/SL-close one copy broker only: next signal should use that copy broker's current position truth, not Primary's state.
5. cTrader Primary + MT5 Copy: verify `XAUUSD` resolves to the terminal symbol such as `XAUUSDm`.
6. Trigger a reversal with an MT5 copy position: verify `CLOSE_POSITION` is used and no `SL/TP missing or zero` error appears.
