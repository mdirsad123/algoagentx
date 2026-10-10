# AlgoAgentX TradeLocker position-limit and copy-synchronization safety patch

**Source base:** AlgoAgentX_TradeLocker_Live_Candle_Hotfix_20261010.zip, previously provided in this conversation. The user may have made local edits since that archive; merge the three changed backend files instead of overwriting newer production code without comparison.

## User-reported issue
- GFT TradeLocker showed 2 broker positions while the AlgoAgentX deployment showed 0.
- `max_open_positions=1` was not reliably enforced.
- TradeLocker copy-account positions and copy order status did not reconcile; copy execution appeared to fail.

## Confirmed implementation defects and fixes
1. **Wrong position parser:** `broker_sync_service.py` dispatched TradeLocker positions to the Upstox parser, which expects `quantity`, `instrument_token`, `average_price`. TradeLocker exposes `id`, `tradableInstrumentId`, `side`, `qty`, `avgPrice`, `openDate`, and `unrealizedPl` via the columns in `/trade/config`. The new TradeLocker normalizer requires ID/side/symbol/valid quantity and preserves independent hedge positions by broker position ID.
2. **Position instrument naming:** `tradelocker.py` now maps `tradableInstrumentId` to the broker instrument name and adds `broker_position_id`. Unknown instrument IDs remain visible as distinct identifiers rather than being silently omitted; missing IDs/invalid table shapes raise a blocking error instead of reporting false zero positions.
3. **Copy account checks:** `sync_copy_target_positions()` now fetches every open TradeLocker position **for the selected copy account**, rather than filtering to one instrument. Copy target symbol resolution checks that `XAUUSD` resolves uniquely to `XAUUSD.X` (or other exact broker symbol); ambiguity prevents a copy order.
4. **Pending entry gate:** TradeLocker market-order acknowledgments are not fills. `execution_engine.py` now blocks another entry while a previous local TradeLocker entry has status `PLACED`, `SUBMITTED`, or `PENDING` for that deployment and account. Combined with corrected broker position reconciliation, this protects `max_open_positions=1` during the fill-confirmation gap.
5. **Final order reconciliation:** `/orders` contains non-final orders. Open locally-acknowledged orders are checked against matching `orderId`s in `/ordersHistory`, selectively rather than refetching all historical orders each polling cycle. The same check is added for TradeLocker copy targets.
6. **Financial sync:** TradeLocker `get_account_info()` now returns standard `connected`, balance, equity, margin and currency fields for use by the existing generic broker-sync service.

## Unchanged
- cTrader and MT5 adapters, cTrader persistent event stream, signal strategy, risk algorithm, funded logic, MT5 symbol handling, and frontend files were not changed by this patch.
- Automatic candle feed/legacy scheduler is not modified.
- TradeLocker live-account execution safety flags and broker restrictions remain in place.

## Testing actually performed
- 8 offline tests in `AlgoAgentXAPI/tests/test_tradelocker_reconciliation_safety.py` **passed**.
- Changed Python modules pass compileall.
- No TradeLocker network access, current production DB snapshot or broker credentials were supplied for testing. No actual broker orders, closes, copy fills, or partial exits were placed. Production behavior is therefore NOT certified.

## Recommended safe rollout (development/staging first)
1. **Before installing:** TURN OFF Auto Trade and copy execution on this TradeLocker deployment. Do not delete the existing two GFT positions automatically; inspect and manage them using TradeLocker according to your plan.
2. Take a DB backup and back up your current source. Merge these three files with your latest local edits:
    - `AlgoAgentXAPI/app/services/brokers/tradelocker.py`
    - `AlgoAgentXAPI/app/services/live/broker_sync_service.py`
    - `AlgoAgentXAPI/app/services/live/execution_engine.py`
   New test file: `AlgoAgentXAPI/tests/test_tradelocker_reconciliation_safety.py`.
3. Rebuild/recreate services that import the modified modules (run from the AlgoAgentX compose project root):
   ```powershell
   docker compose --env-file .env.prod -f docker-compose.yml up -d --build --force-recreate --no-deps api live_strategy_worker live_reconcile_worker live_position_manager_worker
   ```
   No web, market, or history worker rebuild is needed for **this** patch.
4. On deployment, click **Sync Broker** while Auto Trade remains OFF. Compare actual TradeLocker open positions and broker position IDs to AlgoAgentX primary and copy open-position lists. If TradeLocker shows two and AlgoAgentX still shows zero, STOP: collect sanitized reconcile-worker and API logs.
5. For the reported primary account, expect AlgoAgentX to show **two** OPEN rows (if TradeLocker still has two). With `max_open_positions=1`, every NEW entry must be blocked. Verify the `MAX_OPEN_POSITIONS_REACHED` event. Neither account nor system should add another position in this state.
6. Check the selected copy-account identity and environment; confirm positions come from **its own account**, not the primary. Existing broker positions need to sync before copy-entry risk evaluation.
7. Only on a **free TradeLocker demo account**, validate one minimum-size BUY/SELL order, order ACK, matching final order history, broker position ID/quantity/side, SL/TP, manual full close, partial close if configured, then the copy path. An evaluation account named DEMO can still incur real challenge loss and is not an appropriate debugging account.
8. Keep unattended Auto Trade OFF until all safety checks complete. Do not assume 8 mocked tests prove broker fill or close semantics.

## If copy order still does not appear
Inspect API/worker logs or `live_trade_logs` for `COPY_TARGET_SKIPPED`, `COPY_ACCOUNT_ERROR`, `COPY_ACCOUNT_RESULT`, `PRE_TRADE_BROKER_SYNC_FAILED` and `MAX_OPEN_POSITIONS_REACHED`. In particular verify `LIVE_COPY_TRADING_ENABLED`, the deployment's `copy_trading_enabled`, `copy_broker_account_ids`, the copy account's `CONNECTED` status, and that primary/copy environment modes match.

## Operational caution
TradeLocker rate limits and latency depend on `/trade/config`. If broker `positions` or account schema is missing/malformed, new entries should fail closed; never replace a failed broker API snapshot with an empty list and assume there are zero positions. The pending-entry guard is deployment-scoped; multiple concurrently running deployments sharing a single broker account require further account-level locking and deduplication validation.
