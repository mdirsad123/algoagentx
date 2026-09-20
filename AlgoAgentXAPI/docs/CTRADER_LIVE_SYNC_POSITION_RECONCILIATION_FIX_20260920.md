# cTrader live sync / position reconciliation fix — 2026-09-20

## Problems fixed

1. Broker SL/TP or manual closes were not immediately reflected in local `LivePosition` rows. This could leave a stale OPEN row and cause the next signal to be rejected.
2. `max_open_positions > 1` still behaved like one-position-only because the risk layer rejected every same-side signal with `Already in LONG/SHORT position`.
3. cTrader hedged accounts can have multiple positions with the same symbol and side. Reconciliation previously matched by symbol+side first, which can bind the wrong local row.
4. A race where cTrader closed a position between sync and close request surfaced as `cTrader position ... was not found` and incorrectly turned the strategy signal into an ERROR.
5. Some live-trading UI/messages still described broker-generic behavior as MT5-only.

## New behavior

- Broker-backed deployments automatically enable broker synchronization when started.
- Enabling Auto Runner also enables broker synchronization.
- Existing deployments with Auto Runner ON are treated as sync-enabled even if their old DB row still has `live_sync_enabled=false`.
- Default per-deployment sync interval remains 10 seconds (bounded by platform settings).
- Every DEMO/LIVE execution performs a fresh broker sync before risk checks.
- cTrader positions reconcile by `broker_position_id` first, then only fall back to symbol/side for legacy rows with no broker position id.
- Same-side entries are allowed until `max_open_positions` is reached. Opposite-side signals retain close-and-reverse behavior.
- If a cTrader position disappears at the broker between sync and close request, the close becomes an idempotent reconciliation (`RECONCILED`) instead of an execution error.
- cTrader summary refresh now runs the generic broker sync path as well.
- Live deployment UI polls summary every 10 seconds and shows broker auto-sync state, interval, and last sync time.

## Safety

Broker truth is authoritative for DEMO/LIVE positions. If a pre-trade broker refresh fails, new execution fails closed rather than placing a trade from stale local state.
