# AlgoAgentX — Market Data broker-symbol and dropdown V3 patch

This patch is based on `algoagentx_market_data_ctrader_history_fix_20261031_v2.zip` and changes **only** the admin market-data frontend and the account-scoped history API/service. It does not change the live-trading, V6.4 strategy, backtest, data schema, scheduling, or existing MT5 import logic.

## What changed

1. **Exact broker/subaccount symbol discovery**: `GET /api/v1/admin/market-data/auto-sync/accounts/{broker_account_id}/symbols?subaccount_id=<id>` (admin authentication required). Gets actual supported symbols from the connected *specific* cTrader or TradeLocker trading account, masks sensitive data, and returns names/IDs only. No copied MT5 suffix.
2. **Strict symbol validation on feed creation**: a submitted symbol must match the account's discovered list. It rejects an unrecognized `XAUUSDm` for cTrader instead of creating a feed destined to fail.
3. **Fix Symbol for previously failed feeds**: new option on Automatic Daily Sync configuration rows. It can change a feed symbol only when the feed has **zero stored candles** and no active job. Failed audit history remains intact. Feeds with candles must not be relabeled; create a new feed instead.
4. **History-worker preview fallback**: if an adapter's fuzzy/cached cTrader symbol resolution does not exactly match the configured symbol, the worker looks up the exact symbol on the selected subaccount before rejecting it. No live adapter method was changed.
5. **Purple dropdown menus**: native `select` menus on the admin Market Data page are replaced with a scoped, portal-rendered violet Radix dropdown, including manual-fetch filters, connected accounts, trading subaccounts, timeframes and feed selectors.
6. **Removed redundant panel**: the bottom `Import Failures & Invalid Datasets` panel is gone. The existing import health summary and daily sync job history remain.
7. **Windows-readable diagnostics**: newly generated sanitized history stage errors use ASCII hyphens instead of the garbled Windows PowerShell em dash.

## Broker mapping — do not hardcode globally

| Context | Example symbol | Where to get it |
|---|---|---|
| MT5 / Exness | `XAUUSDm` | MT5 Market Watch / Market Master broker symbol |
| cTrader | `XAUUSD` | Selected cTrader Open API trading account's actual symbol list |
| TradeLocker | `XAUUSD.x` | Selected TradeLocker trading account's instrument list |

These are examples from your reported accounts, not universal broker naming guarantees. The new picker checks the **actual connected account**; if one account supports a different suffix, select its returned symbol. For BTCUSD, select exactly what the corresponding cTrader subaccount returns; don't copy `BTCUSDm` from MT5.

## Deploy on local Windows Docker

1. Back up the working project and `.env.prod`, and replace project code with files from this ZIP. Keep the existing production environment secrets unchanged.
2. From `D:\Stock_market\algoagentx`, with the existing running database and broker connections:

```powershell
docker compose --env-file .env.prod up -d --no-deps --build --force-recreate api web market_data_history_worker
```

3. Refresh `http://localhost:3000/admin/market-data` (hard refresh Ctrl+Shift+R if stale).
4. **For existing FAILED BTCUSDm cTrader feed**: Automatic Daily Sync → find that feed → **Fix Symbol** → choose the same cTrader subaccount → select the API-verified `BTCUSD` (or the exact offered symbol) → **Save exact symbol** → **Run Now**.
5. For a new feed or manual import, choose a connected broker account and trading subaccount, select the Market Master instrument, then choose the *broker-provided* symbol. The picker may select an exact/unique account-provided match; check the verification caption.
6. Existing successful XAUUSD cTrader candles do not require re-import. The `market_data` canonical backtest series and existing feed candles are not changed by deployment.

### No SQL changes

**No migration or manual ALTER/UPDATE query is required.** Previously failed configurations can be fixed through the UI, subject to the no-existing-candles guard. Do not mass-UPDATE all `broker_symbol` fields; they are source-specific.

### Diagnostics, if an account can't load symbols

```powershell
docker logs --since 15m algoagentx_api 2>&1 | Select-String "symbol|history|ctrader|tradelocker"
docker logs --since 15m algoagentx_market_data_history_worker 2>&1 | Select-String "Market history run failed|BROKER_|resolve-symbol|fetch-candles"
```

An unavailable or expired broker OAuth connection must be reauthorized in the broker connection flow. This patch does **not** create or validate a live broker token on your host.

## Validation on the patch source

- 16 history-focused Python tests passed (including 3 new broker symbol tests).
- Python compilation of modified backend modules passed.
- TypeScript parser accepted all six changed/new frontend TypeScript/TSX files.
- Full Next.js build: not run (this runtime does not have the frontend node_modules).
- Real cTrader / TradeLocker account and PostgreSQL integration: not available in this environment, so requires local verification.
- No database tables, columns, migrations, scheduler, live trading services, strategies or backtest engines were changed.

## File list

- `AlgoAgentXAPI/app/api/v1/admin_market_data_sync.py`
- `AlgoAgentXAPI/app/services/market_data/daily_sync.py`
- `AlgoAgentXAPI/tests/test_market_history_broker_symbols_v3.py`
- `AlgoAgentXAPI/tests/test_market_history_oct31_fixes.py` (assertion for ASCII diagnostic)
- `AlgoAgentXApp/app/(admin)/admin/market-data/BrokerSymbolPicker.tsx` (new)
- `AlgoAgentXApp/app/(admin)/admin/market-data/HistorySelect.tsx` (new)
- `AlgoAgentXApp/app/(admin)/admin/market-data/CloudManualFetch.tsx`
- `AlgoAgentXApp/app/(admin)/admin/market-data/DailyHistoryPanel.tsx`
- `AlgoAgentXApp/app/(admin)/admin/market-data/page.tsx`
- `AlgoAgentXApp/lib/api/admin.ts`
