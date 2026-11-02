# AlgoAgentX Market Data V4 — Stable dropdowns + PostgreSQL candle verification

Based on the previous **V3** broker-symbol/theme archive. This patch changes only admin Market Data UI and read-only admin history verification endpoints. It does **not** change live trading, MT5 terminal integrations, broker session logic, scheduler, strategy logic, backtest execution, or database schema.

## Changes

1. **Empty dropdown text fixed** in `HistorySelect.tsx`. Radix was supplied `value={value || undefined}`, which toggles between controlled and uncontrolled state for blank selections and can leave the selected label empty after lists reload. It now always has a controlled `value={value}`, explicit placeholder/selected text, and a visible "Selection unavailable — choose again" indicator when the option has disappeared.
2. **Field labels in Automatic Daily Sync**: Connected broker account, Trading subaccount, Market Master instrument, Exact broker symbol, Timeframe. When an account has no linked trading subaccount, the field now says so rather than showing an unlabeled blank.
3. **Stored-candle totals in the feed table**: `Stored candles` shows the actual number of rows and first timestamp in `market_data_feed_candles`, not merely a job status.
4. **Verify Stored Data** button for each feed. The new admin-protected **read-only** API endpoint `GET /api/v1/admin/market-data/auto-sync/configs/{config_id}/verification` returns actual source-feed count, min/max timestamp, five latest OHLCV candles, and separate legacy backtest dataset count/min/max. It does not expose tokens, change account settings or fetch new candles.
5. **Legacy panel clearly labelled** `Legacy Backtest Dataset Coverage & Freshness`, with an explanation that cTrader/TradeLocker source feeds are shown under Automatic Daily Sync.
6. Database verification SQL `VERIFY_ALGOAGENTX_BTCUSD_CTRADER_V4.sql` contains four SELECT-only queries for cTrader BTCUSD configs, saved source candles, latest run audit and legacy backtest records.

## Why your BTCUSD import does not show in the old dataset table

- `market_data_feed_candles` stores candles per connected broker, subaccount, instrument and timeframe.
- `market_data` is the pre-existing canonical dataset read by legacy backtests.
- Your earlier screenshot showed BTCUSD **4,140 inserted** and **UP_TO_DATE**. That supports the import being successful, but the authoritative proof is a non-zero row count in `market_data_feed_candles` from SQL or the V4 Verify Stored Data button.
- Pressing **Primary** alone does not overwrite existing canonical candles and does not merge feeds from different brokers. Do not `INSERT INTO market_data SELECT ...` without a separate audited source-adoption procedure.

## Deployment (PowerShell in Windows project directory)

1. Keep a backup of your current project and `.env.prod` before replacing the project files from the V4 ZIP.
2. Run from `D:\Stock_market\algoagentx`:

```powershell
docker compose --env-file .env.prod up -d --no-deps --build --force-recreate api web
```

The **history worker and scheduler do not need rebuilding** because the new API is read-only and its background tasks are unchanged. Do not recreate live trading workers for a UI/verification patch.

3. Hard refresh the browser: `Ctrl+Shift+R`.
4. Open **Admin → Market Data → Automatic Daily Sync**. Select the configured `CTRADER / BTCUSD / 5m` row and click **Verify Stored Data**. Expect `Broker source candles` greater than zero if your prior import committed.
5. The verification box shows the total count, first/last candle (displayed in IST) and five latest OHLCV rows, plus the separate legacy backtest count.
6. For independent SQL verification, run the included SQL file against your actual **prod PostgreSQL DB**, **not** the `algoagentx_postgres_dev` container. From PowerShell in the directory containing the SQL file:

```powershell
Get-Content .\VERIFY_ALGOAGENTX_BTCUSD_CTRADER_V4.sql | docker exec -i algoagentx_postgres_prod sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1'
```

The PostgreSQL Docker container must expose `POSTGRES_USER` and `POSTGRES_DB` environment variables (as the standard official image normally does). Alternatively open the file in pgAdmin connected to the production database on port **5432** and execute there. All four queries are **SELECT only**.

### Troubleshooting

If `Stored candles` is 0 after a successful-looking run, check the *exact* feed ID and `dry_run` flag: a **PREVIEW** run does not insert anything. A wrong broker subaccount can produce an apparently similar BTCUSD feed with a different feed ID.

If the Trading subaccount menu has no options, that connected broker account has no selected/authorized subaccount as exposed by its broker metadata; choose a different connected account or sync/select the trading account under **Connect Broker**. No option should silently remain invisible.

If the verification endpoint returns 404, ensure the browser/API rebuilt from V4 and that the selected config exists in the same production database.

## Changed project files

- `AlgoAgentXApp/app/(admin)/admin/market-data/HistorySelect.tsx`
- `AlgoAgentXApp/app/(admin)/admin/market-data/DailyHistoryPanel.tsx`
- `AlgoAgentXApp/app/(admin)/admin/market-data/page.tsx`
- `AlgoAgentXApp/lib/api/admin.ts`
- `AlgoAgentXAPI/app/api/v1/admin_market_data_sync.py`
- `AlgoAgentXAPI/app/services/market_data/feed_inspection.py` (new)
- `AlgoAgentXAPI/tests/test_market_history_storage_verification_v4.py` (new)

**No new tables/columns/ALTER migration required.** This patch is compatible with the V3 historical feed tables.

## Validation

- 20 focused offline Python tests passed, including 4 new storage/selector regression tests.
- Python compilation of both backend files succeeded.
- TypeScript parser reported zero syntax errors in four touched TS/TSX files.
- Docker PostgreSQL, cTrader authenticated integration and full Next.js build were not available in this workspace. Verify them after local deployment.
