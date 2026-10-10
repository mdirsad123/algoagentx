# AlgoAgentX cTrader + MT5 Candle Parity Patch — 11 October 2026

**Source baseline:** user's `algoagentx(10).zip` plus previous TradeLocker historical pagination, position-refresh, rate-limit and pending-order safety patch. This package **does not change any existing TradeLocker, copy, partial-exit, signal/strategy or order-execution code**.

## Evidence and verified bug

- From the user's exported cTrader `xauusd_live_candles.csv`, 551 `CTRADER_LIVE_TRENDBAR` candles stored `Close = Low` while their `raw_payload` had no `deltaClose` (all 551). An actual deltaClose of zero is valid, but an **absent** field is not zero.
- `live_market_worker._decode_trendbar` previously used `bar.get('deltaClose') or 0`. The live spot event is provisional and may lack a completed candle close.
- cTrader adapter history decoding also permitted missing deltas, and the separate legacy MT5-specific candle snapshot writer saved current forming bars with `is_closed=True`.
- **MT5's generic `broker_candle_service.refresh_deployment_candles` already filters forming bars.** The patch addresses the other MT5-specific route.

## Changed files

1. `AlgoAgentXAPI/app/services/live/live_market_worker.py`: cTrader decoder keeps missing close as None in *provisional* spot messages and rejects absent close in completed/history data. Spot bar rollover now triggers one small historical candle verification per shared broker subscription; its verified close is fanned out to deployments under `CTRADER_LIVE_VERIFIED`. If history is not ready, no guessed candle is published; existing +3s/+8s watchdog tries historical recovery. Source OHLC and raw payload are preserved. No execution methods changed.
2. `AlgoAgentXAPI/app/services/brokers/ctrader.py`: reject historical bars without required deltas, invalid timestamps or impossible prices; preserve valid `deltaClose=0` bars. No order or position methods changed.
3. `AlgoAgentXAPI/app/services/live/mt5_candle_service.py`: never store forming MT5 candles as closed in the older MT5-specific snapshot path. Correct numeric milliseconds-versus-seconds date interpretation. No MT5 agent, trade, or position code changed.
4. `AlgoAgentXAPI/tests/test_live_market_transition.py`: verified historical close on rollover, missing `deltaClose` guard, fallback/watchdog tests.
5. `AlgoAgentXAPI/tests/test_broker_candle_parity_guard.py`: historical decoder and MT5 forming-bar test.
6. `diagnostics/ctrader_mt5_candle_parity_audit.sql`: read-only audit only.

## Not changed / important boundaries

- Existing TradeLocker fixes preserved. No `tradelocker.py`, `execution_engine.py`, `broker_sync_service.py`, copy-trading, SL/TP or partial-close modification in this **new** patch.
- cTrader source now waits for authoritative historical OHLC before signal emission; this can add a small delay (one history request; watchdog at +3/+8 seconds). Correctness takes priority over a guessed price.
- This fixes a **demonstrated cTrader decoder defect**, not all sources of live-versus-backtest discrepancy. MT5/cTrader/TradeLocker broker candle feeds differ legitimately. Exact signal parity requires using the same complete feed, warmup, strategy hash, runtime settings, time alignment and state.
- No DB schema migration. The existing **551 suspect historical cTrader rows** cannot be reconstructed from `raw_payload`: missing `deltaClose` means the real close is unknown. Audit and re-fetch broker candles in controlled staging; do not auto-delete candles or historical trades.
- **Offline-only tests**. We did not contact your production database, cTrader/MT5 accounts, or place/close any orders. Validate on DEMO before using real money.

## Deployment safety

**Do not rebuild/restart production with a real BTCUSD position open or an unsettled/uncertain order.** Pause fresh deployments, preserve broker-side SL/TP, back up code and database, apply to staging or DEMO, and test candle/time/close parity first. Patch ZIP only changes the 3 Python files plus tests and read-only audit (no TradeLocker files). Full source ZIP contains previous TradeLocker patches plus the latest cTrader/MT5 candle changes; it excludes credentials, private keys, .env and generated assets.

```bash
cd ~/stock_market/algoagentx
mkdir -p ~/algoagentx_ctrader_mt5_backup
cp AlgoAgentXAPI/app/services/live/live_market_worker.py ~/algoagentx_ctrader_mt5_backup/
cp AlgoAgentXAPI/app/services/live/mt5_candle_service.py ~/algoagentx_ctrader_mt5_backup/
cp AlgoAgentXAPI/app/services/brokers/ctrader.py ~/algoagentx_ctrader_mt5_backup/
unzip -o AlgoAgentX_cTrader_MT5_Candle_Parity_Patch.zip -d .

# Stage/DEMO: rebuild services that import the three changed modules.
docker compose --env-file .env.prod -f docker-compose.yml up -d --no-deps --build api live_market_worker live_history_worker

docker compose --env-file .env.prod -f docker-compose.yml ps api live_market_worker live_history_worker
```

`live_strategy_worker` is unchanged and does not need a rebuild for this patch, but check its health after restarting market worker. PostgreSQL, Redis, TradeLocker execution workers and frontend need no restart. If an MT5-only deployment uses the legacy `/mt5` candle refresh endpoint, that API process needs the rebuild above.

### DEMO validation

1. On cTrader DEMO, observe 20+ completed M5 bars. New stored sources should say `CTRADER_LIVE_VERIFIED` or `CTRADER_RECOVERY_BACKFILL`, **not unverified** `CTRADER_LIVE_TRENDBAR`. For every verified `raw_payload`, check `deltaClose` exists and `close=(low+deltaClose)/100000`.
2. Verify max one processing/signal per candle per deployment; check data gaps are recovered by watchdog when historical fetch is unavailable at turnover.
3. On MT5 DEMO, the current forming candle is not in the `is_closed=true` stored snapshots; next closed candle appears after its actual close plus 2s grace.
4. Run V1.37/V3.5 offline replay with the *identical cTrader or MT5 broker feed* and enough historical warmup; compare raw signals, then executions separately.
5. Confirm existing TradeLocker DEMO orders, copy positions and partial exit still behave exactly as before; no new code for those areas was changed.

### Rollback
Restore the three Python files from `~/algoagentx_ctrader_mt5_backup/`, rebuild the same three services and recheck DEMO. No migration reversal necessary.
