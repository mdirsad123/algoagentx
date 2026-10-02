# AlgoAgentX Copy Trading Execution Regression Fix — 2026-09-25

## Root cause
The first copy-trading router wrapped the PRIMARY broker execution in a lightweight `SimpleNamespace` deployment context even when copy trading was disabled. That changed the proven single-account execution path and could surface async SQLAlchemy/ORM state problems before order preview/risk sizing, including `MissingGreenlet` failures.

## Fix
1. Copy Trading OFF (or no copy targets) bypasses the router completely and calls the original primary execution path with the real `StrategyDeployment` ORM object.
2. Copy Trading ON executes the PRIMARY account first with the real ORM deployment, then runs only additional copy accounts through isolated copy contexts.
3. Duplicate-order safety is now broker-account scoped so the primary account's order does not block a selected copy account for the same signal/candle.
4. Copy-account signal status changes no longer overwrite the PRIMARY signal result.
5. Strategy-runner exceptions now emit a full Python traceback to Docker logs (`logger.exception`) while keeping the existing UI-safe error message.

## No database migration
No SQL change is required for this fix if the earlier copy-trading migration has already been applied.

## Validation performed
- Python `compileall` passed for the API package.
- Focused tests passed: copy-router primary-path regression, live order-dedupe claim, and live latency trace (5 tests total).

## Important architecture note
The current `live_market_worker` event-driven candle pipeline registers cTrader deployments only. MT5 deployments currently use the existing auto-runner/MT5 agent path. This is why MT5 technical logs contain `AUTO_RUNNER_*` events even when the cTrader event pipeline is enabled globally.
