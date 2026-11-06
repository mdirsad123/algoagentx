# AlgoAgentX Market Data UI + cTrader History Fix — 2026-10-31 (V2)

This package is a corrective patch on top of the earlier **cTrader-priority daily-history** project. Preserve your existing production `.env.prod`, database, live deployments, warmup parameters and live V6.4 strategy. No migration or new table/column is required for this V2 patch, provided the preceding daily-history migration was already installed (you already have configurations shown in the screenshots).

## Fixes

1. Browser dropdown options have explicit dark backgrounds, white text and dark native widget scheme in Market Data (including cTrader accounts and timeframes).
2. cTrader history worker now has a **read-only exact UTC range** method. It chunks trendbar requests into a max 12 hours for short timeframes (2 days for higher timeframes), converts cTrader's low + relative OHLC deltas using 1e5, preserves Decimal prices, uses account authentication and checks the broker symbol. The existing live strategy `get_rates_history` function was not rewritten.
3. Switching historical subaccounts no longer reuses a cached symbol preview belonging to the original connected account. This avoids wrong symbol IDs.
4. History failures now persist **sanitized stage/error codes** (e.g. `resolve-symbol: BROKER_SYMBOL`, `fetch-candles: BROKER_TIMEOUT`, `BROKER_DNS`, `BROKER_AUTH`) instead of only `FAILED History fetch failed`. The Docker history worker emits run/feed/provider/exception class and safe code, but never upstream OAuth text or credentials.
5. `Run Now` is usable with a new empty feed and no initial date: it bootstraps **the last 7 days** of history (max 120-day optional API lookback), up to the latest *closed* candle. If candles exist, it resumes from the last saved candle with bounded overlap. If `initial_start` is configured, that date is respected instead. Scheduled daily jobs remain opt-in and still do not auto-download unbounded history on a newly configured feed.
6. Fetch from Broker tab offers MT5, cTrader and TradeLocker (plus existing Binance and Upstox). cTrader/TradeLocker manual imports require the exact connected account, trading subaccount, market master instrument, exact broker symbol and UTC date range. Preview / Fetch & Save enqueue the separate low-priority history worker and create a DISABLED source feed if required. Existing manual MT5 endpoint remains unchanged.
7. Primary selection now has an explanation/tooltip: a primary feed can populate **an empty** canonical series only; existing MT5 `market_data` is not overwritten by cTrader. A successful new cloud-broker run will be visible in `market_data_feed_candles` and the Automatic Daily Sync history table, **not necessarily** in the old Dataset Coverage table.

## Deploy only the affected containers (PowerShell)

From `D:\\Stock_market\\algoagentx` with your **existing** `.env.prod` and running PostgreSQL/Redis:

```powershell
# Preserve your current .env.prod; don't replace it with defaults.
docker compose --env-file .env.prod up -d --no-deps --build --force-recreate api web market_data_history_worker
# No need to restart market_data_history_scheduler: its schedule is unchanged.
docker compose --env-file .env.prod ps api web market_data_history_worker market_data_history_scheduler
```

If you also changed a scheduler setting in `.env.prod` while applying this patch, recreate **only** `market_data_history_scheduler` separately; otherwise keep it running.

## Test the new cTrader feed

1. Open `http://localhost:3000/admin/market-data` → **Fetch from Broker** → choose **cTrader Open API**.
2. Select the existing connected cTrader account and the **exact** trading subaccount (DEMO/LIVE), then Market Master XAUUSD, broker's exact `XAUUSDm` if available, and `5m`.
3. Test a short historical window (e.g. two market-open days in the past), **Preview** first, then **Fetch & Save**.
4. Click **Refresh job result**. You can also see all runs in **Automatic Daily Sync** → Recent daily/manual sync runs.
5. If the feed has no history, **Run Now** now fetches a default recent **7-day** bootstrap. With candles already in the feed, it fetches missing closed candles since the last stored candle. More history is obtained with additional manual date-range requests (up to 120 days per job) or an explicit `initial_start` on a new configuration.
6. Once runs succeed and candle timestamps are correct, enable the individual feed's **Auto Fetch** toggle; it runs at the existing single **03:00 IST** global schedule.

**Weekend note:** Saturday 2026-10-31 is not a market-open day for XAUUSD on most forex/metal brokers. The latest valid cTrader gold candle may be on Friday 2026-10-30; absence of Saturday gold M5 candles is normal. Crypto sources can have weekend candles.

## If a cTrader run still fails

The screenshots only show the generic error, not the original Python exception. The patch removes that diagnostic blocker, but a real auth, symbol, DNS or WebSocket error must still be checked in your Docker deployment.

```powershell
docker logs --since 20m algoagentx_market_data_history_worker 2>&1 | Select-String "Market history run failed|BROKER_|resolve-symbol|fetch-candles|Traceback"
docker logs --since 20m algoagentx_api 2>&1 | Select-String "market-data|auto-sync|error|Traceback"
```

Read the **new** run's `error` text from the admin dashboard. Older failures retain their old generic error. If the new error is `BROKER_AUTH`, reconnect/refresh cTrader OAuth; if `BROKER_SYMBOL`, discover that trading account's exact symbol; if `BROKER_DNS`/`BROKER_TIMEOUT`/`BROKER_CONNECTION`, verify the **history worker** has outgoing network/DNS access to the selected cTrader demo/live Open API endpoint. Do **not** share raw tokens, credentials or unredacted environment files.

For database verification, use included `VERIFY_MARKET_DATA_HISTORY_FEEDS_20261031.sql` in your local PostgreSQL query console. It reads only from existing source-feed/config/run tables. There is **no new manual CREATE TABLE/ALTER TABLE query** needed for this V2 patch.

## Validation scope

- Python compilation: passed.
- Offline pytest: 20 tests passed across existing daily-history / cTrader connectivity / new cTrader range regression suite.
- TS/TSX syntactic parser checks: passed.
- Real cTrader auth/history against your local account, Docker services, PostgreSQL schema and full Next.js build: **not run in this environment**. They must be verified after you deploy; your screenshots show that services were healthy before the patch, not that cTrader history was functioning.
