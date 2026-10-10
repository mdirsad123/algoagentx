# AlgoAgentX TradeLocker candle and warmup safety patch

## Scope (11 Oct 2026)

Patch **TradeLocker-only broker history**. It does not edit MT5 or cTrader adapters, broker orders, signal rules, copy trading, position reconciliation, or partial exits.

### Root cause addressed

- The previous TradeLocker `get_rates()` was a one-shot history request using a limited time window and a 6,000-bar lookback bound, even when the history-worker wanted 20,000 candles. As a result, long-warmup strategies could remain missing history. This does **not** prove live TradeLocker candle corruption.
- `/trade/history` returns independent **UTC millisecond** timestamps and native `o/h/l/c/v`. The TradeLocker adapter now preserves the original REST OHLC in `raw_payload` when writing refreshed candles, so corrupted data can be diagnosed from PostgreSQL.
- For **background worker calls only**, `get_rates_history()` makes bounded historical date-range pages, walks backwards with a strict cursor, sorts and de-duplicates timestamps, and stops safely when no more candles are available. Every window is bounded below the broker's 20,000-bars-per-request API limit.
- The short `get_rates()` call used by the current live scheduler remains **one broker request**. No new real-time streaming/polling worker is installed or enabled.
- Incomplete, NaN or impossible OHLC candles are discarded. A legitimate `Close == Low` is still accepted.
- No schema/DB migration is necessary.

### Why this is NOT yet proof that live and backtest match

1. Your previous confirmed Close=Low corruption came from `CTRADER_LIVE_TRENDBAR`, not TradeLocker. We deliberately did not alter the cTrader worker in this patch.
2. MT5 and TradeLocker may use different liquidity/quote sources. For near-exact replay compare **TradeLocker broker candles with TradeLocker live candles**, not TradeLocker against MT5 and expecting identical prices.
3. Strategy code, settings, state/warmup, position management, actual bid/ask fill, and spread can still affect result parity. This patch does not claim to solve them all.
4. No live API credentials/TradeLocker account/environment/Oracle DB were available. Tests are offline mocks; real broker integration and profitability are NOT verified.

## Tests

From `AlgoAgentXAPI`:

```bash
PYTHONPATH=. python -m pytest -q tests/test_tradelocker_candle_history_parity.py tests/test_tradelocker_reconciliation_safety.py tests/test_tradelocker_partial_exit_regressions.py tests/test_live_strategy_history_profile.py tests/test_copy_trading_primary_regression.py tests/test_mt5_copy_close_and_symbol.py tests/test_ctrader_fill_replay.py
```

## Deployment procedure (recommended staging or DEMO first)

1. Record source SHA/revision, export DB snapshot, and wait until existing real positions are safely managed. **Do not replace running live execution blindly.**
2. Extract **patch-only ZIP** at `~/stock_market/algoagentx` (or copy patched file and new diagnostic/test files). The full source ZIP deliberately excludes `.env`, private keys and local secrets. Keep your current server `.env.prod` and existing Docker volumes.
3. Run tests in a staging/dev checkout. Do NOT run historical warmup in the API route. Current warmup is already queued through the dedicated `live_history_worker`.
4. Restart only the services that actively call the changed TradeLocker candle adapter:

```bash
cd ~/stock_market/algoagentx
docker compose --env-file .env.prod -f docker-compose.yml up -d --no-deps --build api live_history_worker
docker compose --env-file .env.prod -f docker-compose.yml ps api live_history_worker
# If needed (do not paste secrets):
docker logs --tail 70 algoagentx_api
docker logs --tail 70 algoagentx_live_history_worker
```

**Do not** rebuild PostgreSQL, Redis, MT5 agent, cTrader market worker, TradeLocker position manager, or other workers for this patch. Do not enable or disable existing TradeLocker execution flags.

5. In DEMO only, refresh 12 candles and verify newest closed candle exactly matches TradeLocker `/trade/history`. Then queue an ordinary strategy warmup through existing UI/readiness flow and confirm `stored >= required` without errors. If TradeLocker cannot supply required historical bars, strategy must stay HOLD rather than trading with incomplete filters.
6. Inspect read-only `diagnostics/tradelocker_candle_audit.sql` and export new TradeLocker candles. Use the included CSV comparator for MT5-vs-TradeLocker *diagnostics only*. Test strategy parity using identical TradeLocker inputs.
7. Rollback: restore just the original `AlgoAgentXAPI/app/services/brokers/tradelocker.py` from your backup and rebuild the two services. Do not rollback DB volumes or delete trade rows.

### Database SQL

**No schema migration or UPDATE is required.** `diagnostics/tradelocker_candle_audit.sql` is read-only. It will not rewrite previously executed orders or old candle records.

### Known limitations

- API historical availability and rate limits depend on the specific TradeLocker broker/account/instrument. A client with unavailable 20k candle history will not become magically ready.
- Same-symbol MT5 and TradeLocker XAUUSD candle prices cannot be assumed identical. Validating same-source parity is still required before assessing trading returns.
- This is a **targeted safety repair**, not a guarantee of all strategies, copy orders, partial exits, or real fills against a live server.
