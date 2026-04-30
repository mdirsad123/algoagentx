# AlgoAgentX Admin Market Data Guide

This guide covers the final Admin Market Data upgrade flow for importing, validating, refreshing, and using candles in backtests.

## 1. Admin page overview

Open the admin page:

```text
/admin/market-data
```

The page contains:

- KPI cards for dataset count, record count, fresh/warning datasets, and stale/no-data datasets.
- Dataset filters for symbol, exchange, market, timeframe, freshness status, and stale threshold.
- Fetch from Broker tab for MT5, Upstox, and MOCK/dev provider imports.
- Upload CSV tab for manual fallback imports.
- Dataset Coverage & Freshness table.
- Import Failures & Invalid Datasets / jobs table.
- Refresh Missing action per dataset row.

Only admin users should access this page and the related `/api/v1/admin/market-data/*` endpoints.

## 2. Importing data from MT5

MT5 import is designed for forex/demo historical candles and uses the MetaTrader 5 terminal installed on the same machine where FastAPI is running.

Before importing:

1. Install MetaTrader 5 desktop terminal.
2. Open MT5 and login:

```text
MT5 Terminal -> File -> Login to Trade Account
```

3. Enter MT5 login ID, password, and server in the MT5 terminal.
4. Keep MT5 running.
5. Open Market Watch, right-click, and choose Show All.
6. Open the symbol chart once if MT5 has not loaded history yet.
7. Start the FastAPI server.

Admin UI flow:

1. Go to `/admin/market-data`.
2. Select **Fetch from Broker**.
3. Provider: `MT5`.
4. Select the instrument.
5. Confirm or enter the broker symbol, for example `XAUUSD`, `EURUSD`, or the broker-specific symbol suffix.
6. Select timeframe: `5m`, `15m`, `1h`, or `1d`.
7. Select start and end date.
8. Use **Preview Fetch** first.
9. If the preview is valid, use **Fetch & Save Candles**.

Supported MT5 timeframes currently include:

```text
1m, 5m, 15m, 30m, 1h, 4h, 1d
```

Common MT5 errors:

| Error | Fix |
|---|---|
| MT5 package not installed | Install the `MetaTrader5` Python package in the API virtual environment. |
| MT5 terminal not found / initialize failed | Start MT5 terminal on the same machine and login. |
| Symbol not found | Use Market Watch -> Show All or enter the exact broker symbol suffix. |
| No candles returned | Open the chart once in MT5 and check broker history/date range. |

The market-data import flow does not place live orders.

## 3. Importing data from Upstox

Upstox import is designed for Indian market historical data.

Before importing:

1. Connect or test the Upstox account from the existing Broker/Admin broker flow.
2. Ensure a valid Upstox access token exists.
3. Use a valid Upstox `instrument_key`.

Example keys:

```text
NSE_INDEX|Nifty 50
NSE_INDEX|Nifty Bank
NSE_EQ|INE002A01018
```

Admin UI flow:

1. Go to `/admin/market-data`.
2. Select **Fetch from Broker**.
3. Provider: `UPSTOX`.
4. Select instrument.
5. Enter symbol/trading name if needed.
6. Enter `instrument_key`.
7. Select timeframe and date range.
8. Use **Preview Fetch** first.
9. Use **Fetch & Save Candles** after preview confirms valid rows.

Supported Upstox timeframes currently include:

```text
1m, 5m, 15m, 30m, 1h, 1d
```

Common Upstox errors:

| Error | Fix |
|---|---|
| Access token missing/expired | Reconnect/test Upstox broker account. |
| Invalid instrument key | Use exact Upstox instrument key, not only symbol. |
| Unsupported timeframe | Choose one of the supported intervals. |
| Rate limit | Wait and retry after some time. |
| No candles returned | Check date range, holiday/session, instrument key, and Upstox permissions. |

The market-data import flow does not place live orders.

## 4. Uploading CSV fallback data

CSV upload is the fallback option when broker fetch is not available or broker data is incomplete.

Admin UI flow:

1. Go to `/admin/market-data`.
2. Select **Upload CSV**.
3. Select instrument.
4. Select timeframe.
5. Keep source as `CSV` or enter a descriptive source such as `MANUAL_CSV`.
6. Choose a CSV file.
7. Use **Validate CSV** first. This sends `dry_run=true` and does not save candles.
8. Use **Upload & Save Candles** to persist valid candles.

Accepted CSV examples:

```csv
Date,Open,High,Low,Close,Volume
2026-04-01 09:15:00,100,105,99,103,12000
```

```csv
Date,Close,High,Low,Open,Volume
2026-04-01 09:15:00,103,105,99,100,12000
```

```csv
timestamp,open,high,low,close,volume
2026-04-01T09:15:00,100,105,99,103,12000
```

```csv
time,open,high,low,close,tick_volume
2026-04-01 09:15:00,100,105,99,103,12000
```

Validation rules:

- Timestamp is required.
- Open, high, low, and close are required and numeric.
- High must be greater than or equal to open, close, and low.
- Low must be less than or equal to open, close, and high.
- Volume defaults to `0` when missing.
- Duplicate timestamps inside the import are removed.
- Rows are sorted ascending before upsert.
- Invalid rows are counted and returned in the summary.
- If all rows are invalid, the import is blocked.

## 5. Freshness and coverage logic

The dataset table calculates freshness per instrument/timeframe using the latest candle available in `market_data`.

Statuses:

| Status | Meaning |
|---|---|
| `FRESH` | Dataset is up to date based on timeframe and market rule. |
| `WARNING` | Dataset is delayed but not critically stale. |
| `STALE` | Dataset needs refresh. |
| `NO_DATA` | No candles exist for that dataset. |

Freshness thresholds:

| Timeframe | Fresh | Warning |
|---|---:|---:|
| `5m` | latest candle within 30 minutes | within 24 hours |
| `15m` | latest candle within 1 hour | within 24 hours |
| `1h` | latest candle within 3 hours | within 48 hours |
| `1d` | latest expected trading day | within 7 days |

Market/session rules:

- `CRYPTO`: 24x7.
- `FOREX`: 24x5, weekends use last weekday expectation.
- `INDIAN_EQUITY` / NSE: weekdays only, with simple NSE session expectation.

## 6. Refresh Missing flow

Use **Refresh Missing** on a dataset row when data exists but latest candles are missing.

Backend behavior:

1. Finds latest candle for selected instrument/timeframe.
2. Starts from latest candle timestamp minus a small overlap buffer.
3. Fetches to selected end date/current date.
4. Upserts using `instrument_id + timeframe + timestamp`.
5. Existing rows are updated; missing rows are inserted.
6. Duplicate rows are not created.

If a dataset has no candles, use **Fetch & Save Candles** first.

## 7. How backtest uses imported data

Backtests should use the imported `market_data` rows for the selected instrument, timeframe, and date range.

The backtest data guard checks availability before running:

- If no data exists, backtest is blocked with a friendly error.
- If the requested date range does not overlap available data, backtest is blocked.
- If data is partial, backtest is blocked for now to avoid confusing results.
- Credits should not be consumed when backtest is blocked due to missing data.
- Strategy behavior and backtest engine logic are unchanged.

Verification:

1. Import data from MT5, Upstox, or CSV.
2. Go to the user/admin backtest page.
3. Select the same instrument, timeframe, start date, and end date.
4. Run backtest.
5. Confirm result completes.
6. Try a missing date range.
7. Confirm clean data-unavailable error and no credit debit.

## 8. Database safety

The `market_data` table uses a composite uniqueness key through its primary key:

```text
instrument_id + timeframe + timestamp
```

The upsert service uses that key to avoid duplicate candles.

Expected columns:

```text
instrument_id
timeframe
timestamp
open
high
low
close
volume
```

No final MD-10 SQL migration is required if this table already exists with the composite key.

## 9. Provider status

| Provider | Status | Notes |
|---|---|---|
| MT5 | Working for historical fetch/import when local MT5 terminal is installed and logged in | Forex/demo data, no live orders. |
| Upstox | Implemented, requires existing valid Upstox broker/token configuration | Indian market historical data, no live orders. |
| CSV | Working fallback import path | Supports validation, dry run, and safe upsert. |
| MOCK | Dev/test only | Keep for smoke testing; do not rely on it for production market data. |

## 10. Production checklist

Before production use:

- Confirm admin-only auth for all `/api/v1/admin/market-data/*` endpoints.
- Confirm normal user cannot upload/import/refresh market data.
- Confirm broker credentials/tokens are never returned to frontend.
- Confirm API responses return clean messages, not stack traces.
- Confirm duplicate imports update rows instead of creating duplicates.
- Confirm CSV dry run does not insert rows.
- Confirm broker preview does not insert rows.
- Confirm backtest missing-data guard blocks before credit debit.
- Confirm market-data refresh does not place live orders.
- Confirm MT5 terminal and Upstox token operational processes are documented for admin operators.
