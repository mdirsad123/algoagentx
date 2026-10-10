# AlgoAgentX: TradeLocker Broker Symbols + Partial Exit/Copy Fix (2026-10-10)

Deployment inspected: `0745e2d0-a8b8-4880-9917-3b83e40e1adc` (repository code only; no live DB/broker connection).

## Scope

**Four updated files** (relative to AlgoAgentX project root):

1. `AlgoAgentXApp/app/(user)/live-trading/[deploymentId]/settings/page.tsx`: TradeLocker dropdown fetches the entire connected-account instrument catalogue, displays exact TradeLocker names such as `BTCUSD.X`/`XAUUSD.X`, and saves the broker-native symbol separately from the Instrument Master symbol. An unrelated saved partial setting does not force a broker-symbol remap. The dropdown still respects RUNNING/FUNDED routing locks. Other broker dropdown behavior remains unchanged. Unavailable symbols and broker fetch errors are shown.
2. `AlgoAgentXAPI/app/services/live/live_position_manager_worker.py`: Adds a limited TradeLocker managed-position quote poller independent of active price alerts, including TradeLocker copy accounts; retains MT5/cTrader paths. Quotes publish into the existing Redis bus, validated bid/ask only, conservative 3-second poll interval. Caches adapter authorization per account and permits `MANUAL_REVIEW` states to reconcile.
3. `AlgoAgentXAPI/app/services/live/live_partial_exit_service.py`: For new TradeLocker-managed positions whose broker sync lacks an SL price, looks up the specific *positionId* via a matching entry's broker history. It uses original recorded entry SL only when linked to that exact position. Never guesses from the most recent same-symbol trade (hedging safety). Partial exits remain one state per position/account; uncertain outcomes become `MANUAL_REVIEW` without blind retransmission.
4. `AlgoAgentXAPI/app/services/brokers/tradelocker.py`: Distinguishes uncertain close-request results from definitive broker acknowledgments. The documented partial close endpoint itself was already correct, so it remains unchanged.

**Added test:** `AlgoAgentXAPI/tests/test_tradelocker_partial_exit_regressions.py`

**Included SQL:** `AlgoAgentX_TradeLocker_Partial_Exit_Audit_0745e2d0.sql` is read-only and works with the uploaded code's current model schema. It covers primary/copy positions, states, entry/partial orders, broker history events, and partial logs.

## Explicit limitations / safety

- **This is an offline patch, not a proven live broker fix.** No credentials, deployed DB, real orders, or execution were used. Broker health, quote and actual runner size must be confirmed against your server before claiming TradeLocker live partial close works.
- TradeLocker `/positions` provides `stopLossId` / `takeProfitId` order IDs. Those IDs are **not** SL/TP prices. A linked entry's original requested prices are not independent proof that stop/TP protection is still active at the broker.
- The broker-history lookup is restricted to the adapter's 48-hour query period; older open positions without a recoverable explicit positionId-to-entry mapping may remain `NO_STATE` (fail-closed). Avoid guessing or forcing a partial close for such cases.
- Do not overwrite the master record, create a new unsupported instrument, or deploy unvalidated sizing to live trading. Verify the exact instrument's `min_lot`, `lot_step`, `tick_size`, contract/tick value and broker limits.
- TradeLocker returns **placement/acceptance**, not a guaranteed fill. Status `AWAITING_RECONCILE` is not success. Status `DONE` means reconciled runner quantity but does not independently prove broker SL/TP orders remain protected.
- TradeLocker `MANUAL_REVIEW` intentionally blocks automatic resubmission after ambiguous broker errors; inspect actual broker positions and pending orders before deciding what to do.
- The new quote poller uses ~3 seconds when there are relevant positions. TradeLocker rate limits vary by account and endpoint; tune carefully in a DEMO-only rollout if needed.
- `LIVE_POSITION_MANAGER_DEMO_ONLY=true` in the uploaded `.env.prod`, so LIVE account partial closes remain blocked by design.
- Existing RUNNING settings permit some management edits, but changing primary broker/symbol requires stopping the strategy. Prefer deployment replacement after existing positions are closed, so partial management is not orphaned.

## Offline validation performed

- `python -m compileall` for three modified Python modules: passed.
- 41 relevant pytest cases across TradeLocker, partial exit, copy routing, MT5 and cTrader behavior: passed.
- TSX syntax/transpile check for modified settings page: passed; **not** a complete Next.js/TypeScript app build.
- No actual server/DB or broker integration test has been run.

## Apply

Backup your Git checkout and environment before changing any files. Extract the ZIP **at the project root** (`algoagentx/`), preserving file paths. The patch package **does not** contain `.env`, Docker volumes, broker credentials or your original ZIP's dependency directories.

On your Ubuntu deployment, after extracting the fixed files into the original project and after ensuring any open positions have completed safely:

```bash
cd ~/stock_market/algoagentx
# Only rebuild/restart affected services; leave Postgres, Redis and other workers intact.
docker compose --env-file .env.prod -f docker-compose.yml up -d --no-deps --build api live_position_manager_worker web

docker compose --env-file .env.prod -f docker-compose.yml ps api live_position_manager_worker web

docker logs --tail 100 algoagentx_live_position_manager_worker
```

For the read-only database audit, put the included `.sql` file into your project directory and run:

```bash
docker exec -i algoagentx_postgres_prod sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1' \
  < AlgoAgentX_TradeLocker_Partial_Exit_Audit_0745e2d0.sql \
  > tradelocker_partial_audit.txt
```

To check Redis worker heartbeat without changing state:

```bash
docker exec algoagentx_redis redis-cli --raw GET live:worker_health:live_position_manager_worker
```

To confirm TradeLocker quotes are published, read the Redis key for the **exact** account UUID and broker-native symbol, e.g.:

```bash
# Replace ACCOUNT_UUID with the broker_accounts.id from the read-only SQL report.
docker exec algoagentx_redis redis-cli --raw GET 'latest_price:TRADELOCKER:ACCOUNT_UUID:BTCUSD.X'
```

## What successful demo validation looks like

1. TradeLocker deployment Instrument selection lists `BTCUSD.X`, `XAUUSD.X`, and the other account instruments, not stale symbols from Instrument Master. Choosing one saves canonical `instrument` (when uniquely matchable) and exact `broker_symbol`.
2. Before the trigger, a managed primary/copy position has a state `PENDING`, exact broker position ID and an original recorded SL price.
3. At an executable quote crossing the trigger, `PARTIAL_EXIT_TRIGGERED` appears, followed by `PARTIAL_EXIT_CLOSE_REQUESTED`. `live_orders.action='PARTIAL_EXIT'` shows the requested broker-valid lot quantity.
4. Broker reconciliation confirms remaining lots and state changes to `DONE`. For example, a `0.06` lot position with 50% partial exits `0.03` and leaves `0.03` lots; a `0.01` lot position with min lot `0.01` skips partial (`SKIPPED_MIN_SIZE`).
5. Repeat with TradeLocker in **copy** mode and verify that primary and copy accounts have separate local positions, close orders, and state idempotency keys. Avoid any live-money rollout until you verify protections and real broker fills.
