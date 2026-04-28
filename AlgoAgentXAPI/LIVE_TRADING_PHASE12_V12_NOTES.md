# AlgoAgentX Live Trading Phase 12 v12

## Scope
- Runs selected deployment strategy once on latest closed candles.
- DEMO mode refreshes MT5 candles first, then executes only on MT5 demo account when `auto_trade_enabled=true`.
- PAPER mode remains supported.
- LIVE mode remains blocked at route, runner, safety, and platform-settings levels.

## Main endpoint
`POST /api/v1/live/deployments/{deployment_id}/run-strategy-once`

Payload:
```json
{ "execute": true }
```

Use `{ "execute": false }` for dry run.

## Important files changed
- `app/services/live/strategy_runner.py`
- `app/services/live/execution_engine.py`
- `app/services/brokers/mt5.py`
- `app/schemas/live_trading.py`
- `app/api/v1/live_deployments.py`
- `src/types/live-trading.ts`
- `src/app/(user)/live-trading/[deploymentId]/page.tsx`
- `src/app/(admin)/admin/live-trading/[deploymentId]/page.tsx`
- `database/migrations/phase12_mt5_demo_strategy_execution.sql`

## Manual SQL
Run `database/migrations/phase12_mt5_demo_strategy_execution.sql` in DBeaver before verification.
