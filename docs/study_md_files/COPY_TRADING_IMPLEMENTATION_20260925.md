# AlgoAgentX Copy Trading — 2026-09-25

## Scope implemented

Copy trading is an execution fan-out layer. The deployment's existing primary broker account remains the candle/strategy source. The strategy is evaluated once; after a valid signal reaches the execution engine, the same trade intent can be routed to selected connected accounts.

The primary account behavior remains unchanged when Copy Trading is OFF (the default). Copy targets must belong to the same user, be CONNECTED, and use the same DEMO/LIVE environment as the primary account. Cross-provider routing is supported for compatible execution adapters, including cTrader and MT5. The primary account cannot be duplicated in the target list.

For each target, existing order preview/risk sizing, position limits, broker adapter/gateway and order persistence are reused. Position checks, daily trade/loss checks and duplicate-order checks are now scoped by broker account. Client order IDs also include broker account identity so one account's idempotency claim cannot suppress sibling copy accounts. A target failure is logged and does not roll back successful sibling accounts.

## Safety limitation

FUNDED deployment copy trading is intentionally blocked in this release. Existing funded state is deployment-scoped, so sharing it across several funded accounts would incorrectly combine drawdown/rule state. A later funded-copy phase should bind an independent funded profile/state to each target account before enabling this.

## Database

Run `sql/20260925_add_copy_trading.sql` once on an existing database, or use the included Alembic migration `20260925_copy_trading_fanout.py` if Alembic is your normal deployment path. Do not run both for the same migration unless your migration process accounts for the already-existing columns.

New fields on `strategy_deployments`:

- `copy_trading_enabled BOOLEAN NOT NULL DEFAULT FALSE`
- `copy_broker_account_ids JSONB NOT NULL DEFAULT []`

## UI

Open Live Trading -> deployment -> Settings. A new Copy Trading card appears above the existing runtime toggles. Turn it on and select one or more eligible connected accounts, then Save Settings.

## Rollback

Turn Copy Trading OFF for the deployment. This immediately returns execution to the original primary-account-only behavior without changing strategy, candle, runner, broker or deployment identity.
