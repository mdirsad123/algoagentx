# AlgoAgentX — TradeLocker rate-limit / stale-position / duplicate-order safety patch

**Base:** user-provided `algoagentx(10).zip` with the preceding TradeLocker candle-history pagination patch retained.

## Issue visible in user screenshots
- First BTCUSD order filled and broker SL reportedly closed it.
- Following BUY signals showed `TradeLocker API rate limit reached`, `Broker state refresh failed safely before execution`, and some local order ERROR statuses.
- Screenshots alone cannot determine what the broker actually held at those moments; a 429 is not evidence of an open position or proof an order was never accepted.
- This change treats **fresh broker positions** as the gate and keeps ambiguous order ACKs blocked until verified, rather than guessing that 0 open positions means 0 unresolved orders.

## Changes

1. `AlgoAgentXAPI/app/services/brokers/tradelocker.py`
   - Per-process, credential/account-scoped JWT, `/trade/config` and instrument cache to avoid repeated authentication and schema calls from new adapter instances. Config/instrument TTL 120 seconds; JWT valid only until its reported expiry. No cross-account data sharing.
   - Respect 429 `Retry-After` via a bounded in-process cooldown; never silently treat a 429 as an empty position list or blindly retry order POST/DELETE.
   - Reject malformed `/positions` or `/orders` payloads instead of interpreting missing lists as zero positions.
   - Ambiguous market-order transport/response failure is `UNCERTAIN` (never assume failed/duplicate-submit). 429 HTTP rejection remains a definitive `ERROR`.
   - Retains previous cursor-paginated TradeLocker history warmup and UTC/OHLC validation.
2. `AlgoAgentXAPI/app/services/live/broker_sync_service.py`
   - New `sync_tradelocker_pretrade_positions()` shared by primary and copy targets. Always retrieves **all currently open positions** of the respective broker account before risk checks. Fails closed if broker positions cannot be fetched.
   - If there are prior unconfirmed entry orders, asks the broker for active/order history, reconciles confirmed statuses, and otherwise retains the pending guard. Does not assume a pending ACK is a fill.
   - Preserves a recent (<=120 seconds) verified broker-balance snapshot for risk sizing; refreshes balance if older or missing. A missing valid broker balance blocks entries instead of falling back to potentially stale sizing.
   - Moves TradeLocker full-background sync positions ahead of order history so throttled order-history lookups cannot keep locally closed SL/TP positions marked OPEN.
   - Background REST sync interval for TradeLocker only becomes >=60s, reducing routine request volume. MT5/cTrader intervals are unchanged; entries continue to request fresh broker positions.
3. `AlgoAgentXAPI/app/services/live/execution_engine.py`
   - Uses the dedicated fresh TradeLocker pre-trade path instead of an expensive full account/order/history sync on every signal.
   - Keeps unknown order POST outcomes in local `PENDING`, ensuring the existing account-specific pending-entry gate prevents a duplicate order. Manual broker verification is required when no broker order ID exists.
   - MT5/cTrader paths and execution/SL/TP/partial-close logic are unchanged.
4. `AlgoAgentXAPI/tests/test_tradelocker_rate_limit_position_guards.py`
   - Offline tests for positions-first, no false zero on 429/malformed payload, pending-order verification, cross-account JWT isolation, and no retry of ambiguous POST.

## What this DOES and DOES NOT fix
- Can correct a stale local `OPEN` position after broker SL **when `/positions` succeeds**. It cannot make TradeLocker respond to a rate-limited API.
- Reduces preventable request volume; it **cannot guarantee** zero 429 errors if other API consumers or the broker rate limits globally, or if concurrent worker processes still request too often.
- Copy accounts are account-scoped. An active broker position or unconfirmed order for one copy account blocks only that account; unrelated accounts use their own snapshots.
- Existing cTrader/MT5 signal, execution, risk and partial-exit behavior deliberately untouched. This is NOT proof of live broker parity.
- The current partial-exit quote worker polls TradeLocker for managed positions every ~3 seconds. If 429s continue, measure the actual broker request budget and separately tune polling **without blindly delaying partial exits**.

## Tests performed in offline container
- `pytest` focused TradeLocker, candle history, MT5, cTrader, copy trading: **60 passed**.
- `python -m compileall` on changed Python modules: passed.
- One legacy end-to-end test could not be imported: environment missing `asyncpg`. No real TradeLocker credentials, API responses, live DB or orders were available. **Do not equate offline tests with proven production safety.**

## Database changes
No migration / UPDATE / DELETE necessary. Audit SQL under `diagnostics/tradelocker_btcusd_order_audit.sql` is read-only.

## Safe deployment
Pause new DEMO orders and wait for existing open/pending positions to finish or confirm they can still be managed through the broker. Back up existing project and database. Use patch ZIP and apply on staging/DEMO first.

```bash
cd ~/stock_market/algoagentx
mkdir -p ~/algoagentx_patch_backup
cp AlgoAgentXAPI/app/services/brokers/tradelocker.py ~/algoagentx_patch_backup/tradelocker.py
cp AlgoAgentXAPI/app/services/live/broker_sync_service.py ~/algoagentx_patch_backup/broker_sync_service.py
cp AlgoAgentXAPI/app/services/live/execution_engine.py ~/algoagentx_patch_backup/execution_engine.py
unzip -o AlgoAgentX_TradeLocker_Order_RateLimit_Fix_Patch.zip -d .
# Rebuild only Python services importing affected modules; do not restart PostgreSQL/Redis/web.
docker compose --env-file .env.prod -f docker-compose.yml up -d --no-deps --build api live_strategy_worker live_reconcile_worker live_position_manager_worker live_history_worker
docker compose --env-file .env.prod -f docker-compose.yml ps api live_strategy_worker live_reconcile_worker live_position_manager_worker live_history_worker
```

If API is actively running legacy TradeLocker auto-runner, rebuilding API restarts that loop. Do not deploy while an order is in-flight.

## Verification (DEMO first)
1. Verify `/trade/positions` returns an authenticated list and `BTCUSD.X` symbols are mapped correctly; do not rely solely on UI position count.
2. Test after broker-confirmed SL close: fresh snapshot yields zero open, no unresolved locally PENDING order, then next *new valid candle* gets one execution attempt.
3. Verify same candle never duplicates on primary or copies, and account A does not inherit account B's pending orders.
4. Trigger mock 429: safety fails closed, reports warning; never sends an order on incomplete account truth.
5. Verify fills/SL/TP and partial-close watcher on primary and copies; compare broker IDs with local rows.
6. If 429 continues, inspect `live_trade_logs` and lower other TradeLocker quote/REST polling in a separate measured release.

## Rollback
If regression occurs, pause new execution, restore the three `.py` files from `~/algoagentx_patch_backup`, then run the same selective Docker rebuild. No database rollback necessary (no schema change).
