# TradeLocker live data hotfix — 10 October 2026

## Verified from user-provided logs
- TradeLocker authentication responds HTTP 201 and selected account instruments HTTP 200.
- `live_history_worker` repeatedly fails with `Unsupported candle broker provider: TRADELOCKER` at `broker_candle_service.py:122`.
- `auto-runner/enable` separately timed out acquiring PostgreSQL/asyncpg connection.
- `live_market_worker` is built around cTrader's persistent event stream; it does not automatically subscribe to TradeLocker candles.

## Changes in this source ZIP
1. Register `TRADELOCKER` as an allowed source in `broker_candle_service.py` so the existing refresh/warm-up routines can use the broker adapter.
2. Return the broker adapter's historical bars as UTC-aware `candle_time` (TradeLocker `t` is in milliseconds), with symbol, OHLCV, and minimal raw payload. Sort chronological before selecting the latest bars.
3. Harden generic candle timestamp parsing for millisecond UNIX timestamps.
4. Show TradeLocker REST rather than a misleading cTrader connection status in the frontend's latency panel. For REST brokers, do not apply cTrader's persistent-connection feature flag to the flag summary, and do not advertise cTrader event-pipeline readiness.

## Not yet solved / not guaranteed
- This is **not** a full TradeLocker streaming service. The existing live-market worker remains cTrader-specific. Legacy polling/refresh must be configured and independently validated for TradeLocker.
- Verify history API supports the configured route, account and requested M5 bars; a real account API call was not possible in this environment.
- Separate PostgreSQL timeout and Redis AOF disk-latency warnings still need operational investigation.
- Position reconciliation, end-to-end live execution, partial closes and alert-to-order routing have **not** been demonstrated. Keep `TRADELOCKER_ORDER_EXECUTION_ENABLED=false` and `TRADELOCKER_LIVE_EXECUTION_ENABLED=false`.
- Equity is nullable where the broker does not return an identifiable equity column. Do not replace it with balance artificially.

## Verification steps (DEMO only)
1. Back up the DB and apply ZIP only to a dev/staging copy. Rebuild API, web, live_history_worker, and workers that import these modules.
2. Open broker connection Test; verify credentials, account ID and accNum, and symbol `XAUUSD.X`.
3. Invoke the deployment's Refresh Candles and watch `live_history_worker` log. Check the API response for strictly increasing UTC `candle_time`, OHLC > 0, and positive `stored_count`.
4. Check warm-up against the strategy-required 1000 *closed* M5 candles. Prevent live activation while the requirement fails.
5. Observe at least two complete M5 closes. Confirm automatic ingestion occurs without pressing Refresh (if not, REST polling is still missing).
6. Diagnose asyncpg pool timeout and Redis AOF disk stalls separately; confirm DB and Redis health.
7. Only after the data feed and preflight are stable, validate broker-side orders and reconciliation using controlled DEMO orders with the safety gate explicitly enabled for that test.

No existing production deployment should be overwritten solely on the basis of this hotfix.
