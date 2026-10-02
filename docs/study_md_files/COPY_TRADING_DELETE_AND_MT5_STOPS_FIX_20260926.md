# AlgoAgentX – Stale Deployment Delete + cTrader→MT5 Copy Invalid Stops Fix

Date: 26 Sep 2026

## Problems fixed

### 1. STOPPED deployment could not be deleted although the page showed 0 open positions

The Live Trading headline intentionally reports the PRIMARY account only. A copy-trading target can still have a local `live_positions.status='OPEN'` row that is not shown in that primary metric.

The old MT5 async flow made this worse: `PLACE_ORDER` returned `PLACED` as soon as the command was queued for the Windows MT5 Agent, and `_execute_demo_entry()` immediately created a local OPEN position. If MT5 later rejected the command (for example `Invalid stops`), the order became ERROR but that optimistic position row could remain OPEN. The delete endpoint correctly saw that row and blocked deletion.

Fix:

- MT5 `PLACED` now means **queued**, not filled.
- No local OPEN position is created until broker truth confirms it through reconciliation (or a synchronous FILLED result exists).
- Before deleting a DRAFT/STOPPED/ERROR deployment, the backend reconciles only broker accounts that still have local OPEN rows.
- If broker truth says there is no position, the stale local row becomes CLOSED and deletion can continue.
- If the broker really has an open position, or the broker cannot be verified, deletion remains blocked safely.

No force-delete bypass was added.

### 2. cTrader primary → MT5 copy returned `Invalid stops`

The MT5 Windows Agent previously used the source strategy/cTrader reference price as the MT5 MARKET request price and forwarded the source broker's absolute SL/TP unchanged.

For a cross-broker copy, cTrader and MT5 can differ by spread/quote offset by the time the MT5 command arrives. A protection level valid around cTrader's reference can then be invalid around MT5's current Bid/Ask.

Fix:

- Primary/copy strategy and risk calculation remain unchanged.
- The MT5 Agent uses the target terminal's current executable Bid/Ask for MARKET order price.
- For copy executions, it preserves the strategy's SL and TP **distances** by shifting both levels by the target-price offset.
- It normalizes protection to the MT5 symbol digits.
- It checks `trade_stops_level * point` before sending.
- It never silently widens the stop. If the strategy stop is genuinely too tight for that MT5 broker, only that copy target fails with a detailed local error.
- If MT5 still returns `TRADE_RETCODE_INVALID_STOPS`, the copy target refreshes the tick and retries exactly once. `INVALID_STOPS` is a rejection, so this retry cannot duplicate a filled trade.
- The exact symbol/volume/SL/TP actually sent to MT5 are written back to the local order result.

## Existing behavior preserved

- One strategy run / one signal.
- Original primary execution path remains the primary path.
- Copy targets remain isolated by account.
- Per-account balance/equity risk sizing remains unchanged.
- Per-account max-open-position and duplicate/idempotency protection remain unchanged.
- cTrader event-driven workers remain unchanged.
- MT5 ticket-based close logic remains unchanged.
- No frontend changes.
- No SQL migration.

## Changed files

```text
AlgoAgentXAPI/app/services/brokers/base.py
AlgoAgentXAPI/app/services/brokers/mt5_agent.py
AlgoAgentXAPI/app/services/live/execution_engine.py
AlgoAgentXAPI/app/api/v1/mt5_agent.py
AlgoAgentXAPI/app/api/v1/live_deployments.py
AlgoAgentXAPI/AlgoAgentXMT5Agent/mt5_client.py
AlgoAgentXAPI/storage/downloads/AlgoAgentXMT5Agent.zip
AlgoAgentXAPI/tests/test_mt5_copy_invalid_stops_fix.py
AlgoAgentXAPI/tests/test_mt5_async_position_and_delete_cleanup.py
```

## Validation

Focused regression suite:

```text
21 passed
```

Covered:

- existing copy symbol normalization
- primary regression protection
- account-scoped position isolation
- async ORM/copy regression
- generic idempotency
- existing MT5 ticket close + symbol resolution
- MT5 copy SL/TP rebasing
- MT5 minimum stop-level local rejection
- one copy-only retry after `Invalid stops`
- no optimistic local OPEN position while MT5 order is only queued

`python -m compileall -q app AlgoAgentXMT5Agent` also passes.

## Deployment

Backend services:

```bash
docker compose --env-file .env.prod up -d --build --force-recreate api live_market_worker live_strategy_worker live_reconcile_worker
```

Then restart the Windows MT5 Agent with the updated files/package so the new target-price SL/TP logic is active.

No PostgreSQL/Redis recreate is required.
