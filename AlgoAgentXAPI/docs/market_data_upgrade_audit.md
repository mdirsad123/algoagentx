# Phase MD-1 — Market Data Backend Audit + Schema Safety

Date: 2026-04-30
Scope: Backend audit + schema safety only. No broker fetch implementation, no CSV upload implementation, no auth changes, no live trading execution changes, and no backtest flow changes.

## 1. Existing tables found

### `market_data`
Found in:
- `app/db/models/market_data.py`
- PostgreSQL dump `algo_db_backup.dump`
- Alembic migration `alembic/versions/add_market_data_index.py`

Current model columns:
- `instrument_id` integer, foreign key to `instruments.id`, primary key
- `timeframe` string, primary key
- `timestamp` datetime, primary key
- `open` numeric
- `high` numeric
- `low` numeric
- `close` numeric
- `volume` numeric

Current dump structure confirms:
- `instrument_id integer NOT NULL`
- `timeframe text NOT NULL`
- `timestamp timestamp(3) without time zone NOT NULL`
- OHLCV numeric columns
- primary key: `(instrument_id, timeframe, timestamp)`
- foreign key to `instruments.id`

Schema status against required MD structure:

| Required field | Current status | Notes |
|---|---:|---|
| `id` optional | Not present | Acceptable because composite primary key is already used. |
| `instrument_id` | Present | FK to `instruments.id`. |
| `timeframe` | Present | Used by admin datasets and backtest fetch. |
| `timestamp` / `candle_time` | Present as `timestamp` | Backtest service expects `MarketData.timestamp`. Keep as-is for stability. |
| `open` | Present | Numeric. |
| `high` | Present | Numeric. |
| `low` | Present | Numeric. |
| `close` | Present | Numeric. |
| `volume` | Present | Numeric. |
| `source` / `provider` optional | Missing | Should be added in a later phase only if needed for import lineage. Do not add in MD-1. |
| `created_at` | Missing | Should be added in a later phase only if needed. Do not add in MD-1. |
| `updated_at` | Missing | Should be added in a later phase only if needed. Do not add in MD-1. |

Uniqueness requirement:
- Required unique key: `instrument_id + timeframe + timestamp`.
- Current model and dump already satisfy this using the composite primary key `market_data_pkey`.
- Existing Alembic adds a non-unique helper index `idx_market_data_instrument_tf_ts`; the dump did not clearly show this helper index, but the primary key still provides uniqueness.

### `instruments`
Found in:
- `app/db/models/instruments.py`
- PostgreSQL dump `algo_db_backup.dump`
- `/api/v1/instruments` endpoint

Current model columns:
- `id` integer primary key
- `symbol` string not null
- `exchange` string not null
- `market` string not null
- `instrument_type` string
- `tick_size` numeric
- `lot_size` integer

Dump also shows `created_at timestamp(3) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL`, but the SQLAlchemy model does not currently include `created_at`. This is not breaking the current market-data/backtest flow and should not be changed in MD-1.

### `job_status`
Found in:
- `app/db/models/job_status.py`
- PostgreSQL dump `algo_db_backup.dump`
- admin market-data hook enqueue logic

Current model columns include:
- `id`
- `user_id`
- `job_type`
- `status`
- `progress`
- `message`
- `retry_count`
- `max_retries`
- `created_at`
- `updated_at`
- `started_at`
- `completed_at`
- `job_data`
- `result_data`
- `debit_txn_id`

Market-data job types currently used:
- `market_data_import`
- `market_data_upload`
- `market_data_refresh`

### `live_market_candles`
Found in:
- `app/db/models/live_trading.py`
- `app/services/live/broker_candle_service.py`

This table is for live deployment candle snapshots, not the canonical backtest `market_data` table. It already has source/provider-style columns:
- `source`
- `is_closed`
- `raw_payload`
- `created_at`
- `updated_at`

Do not merge or rewrite this table in MD-1.

### Broker-related tables found
Found in `app/db/models/live_trading.py`:
- `broker_providers`
- `broker_oauth_states`
- `broker_accounts`
- `broker_instruments`

These support MT5/Upstox connection and broker metadata. They should be reused later for broker-backed market-data fetch, but not changed in MD-1.

## 2. Existing endpoints found

### Public/user market-data endpoints
Mounted in `app/api/v1/router.py` with prefix `/api/v1/market-data`:
- `GET /api/v1/market-data/timeframes`
- `GET /api/v1/market-data/range`

These endpoints read from the canonical `market_data` table.

### Admin market-data endpoints — newer module
Mounted in `app/api/v1/router.py` with prefix `/api/v1/admin/market-data` from `app/api/v1/admin_market_data.py`:
- `GET /api/v1/admin/market-data/catalog`
- `GET /api/v1/admin/market-data/datasets`
- `GET /api/v1/admin/market-data/jobs`
- `POST /api/v1/admin/market-data/hooks/import`
- `POST /api/v1/admin/market-data/hooks/upload`
- `POST /api/v1/admin/market-data/hooks/refresh`

These are admin-only via `get_admin_user`.

### Admin market-data endpoints — legacy module
Mounted under `app/api/v1/admin.py` with prefix `/api/v1/admin`:
- `GET /api/v1/admin/market-data/supported`
- `GET /api/v1/admin/market-data/coverage`
- `GET /api/v1/admin/market-data/freshness`
- `POST /api/v1/admin/market-data/refresh`
- `POST /api/v1/admin/market-data/upload`

These existing endpoints were left untouched to avoid breaking the current admin page.

### Broker/live candle endpoints related to market data
Found in live services and routers:
- Broker account connection/test endpoints are handled through broker account routes.
- Live deployment candle snapshot/refresh flow uses `app/services/live/broker_candle_service.py` and `LiveMarketCandle`, not canonical `market_data`.

## 3. Existing models/services found

### Models
- `app/db/models/market_data.py` — canonical backtest market data.
- `app/db/models/instruments.py` — symbols/instruments.
- `app/db/models/job_status.py` — job tracking for market data hooks and other async jobs.
- `app/db/models/live_trading.py` — broker providers/accounts/instruments and live candle snapshots.

### Services
- `app/services/backtest_service.py` — fetches canonical market data and passes normalized DataFrame to the backtest engine.
- `app/services/admin_market_data_service.py` — catalog, dataset coverage/freshness, job listing, and placeholder enqueue hooks.
- `app/services/brokers/base.py` — broker adapter contract, including `get_rates()`.
- `app/services/brokers/factory.py` — broker adapter factory.
- `app/services/brokers/mt5.py` — MT5 implementation including `get_rates()`.
- `app/services/brokers/upstox.py` — Upstox implementation including `get_rates()`.
- `app/services/live/broker_candle_service.py` — refreshes live deployment candles into `live_market_candles`.

## 4. Current backtest data flow

Current flow in `app/services/backtest_service.py`:

1. Backtest request passes `strategy_id`, `instrument_id`, `timeframe`, `start_date`, `end_date`, and capital.
2. `_fetch_market_data()` queries `MarketData` where:
   - `instrument_id == requested instrument_id`
   - `timeframe == requested timeframe`
   - `timestamp >= start_date 00:00:00`
   - `timestamp <= end_date 23:59:59`
3. Results are ordered by `MarketData.timestamp ASC`.
4. Rows are converted into a DataFrame with exact engine-friendly columns:
   - `Date`
   - `Open`
   - `High`
   - `Low`
   - `Close`
   - `Volume`
5. Strategy is resolved from the database/registry.
6. `BacktestParams` are inferred from instrument market/symbol and timeframe.
7. `run_backtest_engine()` runs with the normalized market data.

Important stability note:
- Existing backtest depends on `market_data.timestamp` and exact OHLCV conversion. Do not rename `timestamp` to `candle_time` in MD-1.

## 5. Missing pieces for real broker import

The backend has enough foundation to support future broker/import features, but these pieces are not implemented yet for canonical `market_data`:

1. Broker fetch worker for admin market data:
   - No worker currently consumes `market_data_import` / `market_data_refresh` jobs and writes to `market_data`.
   - Existing broker adapters have `get_rates()`, but the result currently feeds live candle snapshots, not canonical backtest candles.

2. Canonical candle upsert service:
   - Need a safe service to normalize broker/CSV rows to `market_data` columns.
   - Need upsert on `(instrument_id, timeframe, timestamp)`.
   - Need duplicate handling and validation.

3. CSV upload parser:
   - Hook endpoint exists, but no parser/import worker is wired in MD-1.
   - Later CSV parser should support common columns: Date/Datetime/Timestamp, Open, High, Low, Close, Volume.

4. Import audit metadata:
   - `market_data` does not store `source`, `created_at`, or `updated_at`.
   - For production import lineage, add metadata either to `market_data` or to an import batch table in a later phase.

5. Instrument mapping:
   - Canonical `instruments` and broker instruments are separate.
   - Future broker fetch needs a clear mapping from canonical `instrument_id` to broker `instrument_key` / broker symbol.

6. Date/time normalization:
   - Dump uses `timestamp without time zone`, while the SQLAlchemy model uses timezone-aware `DateTime(timezone=True)`.
   - Current code works by stripping timezone when passing data to pandas.
   - Later import code must normalize incoming timestamps consistently before upsert.

## 6. Recommended next phases

### Phase MD-2 — Canonical Market Data Upsert Service
- Add a backend service that validates and upserts candles into `market_data`.
- Use `(instrument_id, timeframe, timestamp)` conflict target.
- Add row-level validation for OHLCV and timestamp.
- Return imported/skipped/invalid counts.
- Keep backtest read path unchanged.

### Phase MD-3 — Admin Fetch from Broker Backend
- Implement admin fetch endpoint/job worker for broker candles.
- Reuse existing broker accounts/adapters and `get_rates()`.
- Map broker symbols/instrument keys to canonical `instrument_id`.
- Store data in canonical `market_data` using MD-2 upsert service.

### Phase MD-4 — Admin CSV Upload Backend
- Implement file upload endpoint/parser.
- Validate CSV headers and rows.
- Use the MD-2 upsert service.
- Store invalid-row report in job result.

### Phase MD-5 — Admin UI Integration
- Wire admin page tabs:
  - Tab 1: Fetch from Broker
  - Tab 2: Upload CSV
- Show import jobs, row counts, invalid rows, and freshness.

### Phase MD-6 — Backtest Data Health Guardrails
- Add pre-backtest warnings when data is missing, stale, or has large candle gaps.
- Do not block existing backtest unless the requested dataset has no rows.

## 7. Exact SQL needed if schema/index is missing

A safe manual SQL file has been added:

- `scripts/market_data_schema_safety.sql`

Current audit result:
- The uploaded PostgreSQL dump already has the required uniqueness through `market_data_pkey` on `(instrument_id, timeframe, timestamp)`.
- The SQL file is still included as a safety/verification script. It does not change columns and does not rewrite data.
- Run it only if you want to verify the schema and create the non-unique helper index if missing.

Manual DBeaver SQL:

```sql
-- See scripts/market_data_schema_safety.sql
```

## 8. Risk notes

1. Do not rename `market_data.timestamp` in this project right now. Backtest fetch logic and admin coverage currently rely on it.
2. Do not merge `live_market_candles` with `market_data` in MD-1. Live execution snapshots and historical backtest candles have different responsibilities.
3. Do not add broker fetch or CSV ingestion directly inside FastAPI request handlers in later phases for large imports. Use a job/worker path or bounded sync flow.
4. Be careful with timezone normalization. Existing dump is `timestamp without time zone`; incoming broker/CSV data may be timezone-aware.
5. Before adding `source`, `created_at`, or `updated_at` columns to `market_data`, confirm all ORM inserts/upserts and DB migrations are coordinated.
6. The current admin market-data hooks enqueue jobs but do not process/import data yet. This is expected for MD-1.
7. Backtest stability depends on enough rows existing in `market_data` for the selected `instrument_id`, `timeframe`, and date range.

## MD-1 changes made

Changed files:
- Added `docs/market_data_upgrade_audit.md`
- Added `scripts/market_data_schema_safety.sql`

No app files changed.
No broker fetch implementation added.
No CSV upload implementation added.
No auth/live trading/backtest logic changed.

---

## Phase MD-2 Addendum — Candle Normalization + Safe Upsert Core

Added backend-only ingestion utilities under `app/services/market_data/`:

- `types.py` — canonical `NormalizedCandle`, `ValidationErrorSample`, and `CandleImportSummary` dataclasses.
- `normalizer.py` — accepts provider/CSV variants like `Date`, `Datetime`, `timestamp`, `time`, `candle_time`, mixed OHLC case, and `Volume`/`tick_volume`.
- `validator.py` — enforces required timestamp/OHLC, numeric values, price shape checks, duplicate timestamp removal, ascending sort, and non-fatal invalid-row samples.
- `upsert_service.py` — async PostgreSQL upsert by `instrument_id + timeframe + timestamp`; supports `dry_run` and returns full import summary.

No frontend route, broker fetch, CSV endpoint, auth flow, backtest engine, or live execution logic was changed in MD-2.

### MD-2 SQL

No new SQL is required for MD-2 because the existing `market_data` table already uses the correct composite key/upsert target:

```text
instrument_id + timeframe + timestamp
```

### MD-2 Smoke Test

Run from the API root:

```bash
python scripts/test_market_data_upsert_smoke.py --dry-run-only
python scripts/test_market_data_upsert_smoke.py --instrument-id 1 --timeframe 5m
```

Run the second command twice or use the built-in two-pass script output. The second upsert should report `inserted_rows=0` and updates for existing candles, confirming duplicate imports do not create duplicate rows.

---

# Phase MD-3 — Admin CSV Upload Import Engine

Date: 2026-04-30
Scope: Backend-only admin CSV upload endpoint. No frontend work, no broker fetch implementation, and no backtest engine changes.

## Implemented endpoint

- `POST /api/v1/admin/market-data/upload-csv`
- Auth: existing `get_admin_user` dependency, so normal users are blocked.
- Request type: `multipart/form-data`
- Fields:
  - `instrument_id` integer, required
  - `timeframe` string, required
  - `source` string, optional, defaults to `CSV`
  - `dry_run` boolean, optional, defaults to `false`
  - `file` CSV upload, required

## Supported CSV shapes

The endpoint uses the MD-2 normalizer/upsert service, so it supports header-based mapping for these formats:

- `Date,Open,High,Low,Close,Volume`
- `Date,Close,High,Low,Open,Volume`
- `timestamp,open,high,low,close,volume`
- `Datetime,Open,High,Low,Close,Volume`
- `time,open,high,low,close,tick_volume`

Header names are normalized case-insensitively by the MD-2 service. The `Date,Close,High,Low,Open,Volume` variant is safe because values are mapped by header name, not by column order.

## Validation and import behavior

The endpoint:

1. Confirms admin-only access.
2. Confirms `instrument_id` exists in `instruments`.
3. Confirms timeframe is in the existing admin market-data supported timeframe list.
4. Reads CSV safely using Python's standard CSV parser.
5. Sends rows into `upsert_market_data_candles` from MD-2.
6. Supports `dry_run=true` without inserting into `market_data`.
7. Uses the existing composite key/upsert target: `instrument_id + timeframe + timestamp`.
8. Returns the MD-2 import summary including valid/invalid/duplicate/insert/update counts.
9. Creates a `job_status` record with `job_type = CSV_UPLOAD` when possible.

## Job tracking

Existing `job_status` table is reused. No new schema was added.

Stored job fields:

- `job_type = CSV_UPLOAD`
- `status = completed` or `failed`
- `job_data` includes `instrument_id`, `timeframe`, `source`, `dataset_uri`, `dry_run`
- `result_data` includes the import summary, inserted/updated/invalid/duplicate counts, and error details if failed

The admin market-data jobs endpoint now also includes `CSV_UPLOAD` in its allowed job filter and service-side job-type list.

## SQL required

No SQL migration is required for MD-3.

## Verification

1. Start API.
2. Open `/docs`.
3. Use `POST /api/v1/admin/market-data/upload-csv` with an admin token.
4. Test first with `dry_run=true`.
5. Test with `dry_run=false`.
6. Query `market_data` for the selected `instrument_id` and `timeframe`.
7. Re-upload the same CSV and confirm row count does not duplicate because upsert updates existing candles.
8. Run existing backtest using the same instrument/timeframe to confirm current backtest flow still works.

## Risk notes

- The `market_data` table does not currently persist `source/provider`, so source is saved in `job_status` only. Adding source/provider columns should be a separate future schema phase if needed.
- CSV import is intentionally a fallback path. Broker fetch should be implemented in a later phase and should call the same MD-2 normalization/upsert service.

---

## Phase MD-4 update — Broker Provider Adapter Foundation

Implemented a provider adapter foundation for historical candle fetch without enabling any real broker fetch yet.

### New provider files

- `app/services/market_data/providers/base.py`
  - Defines `MarketDataProvider.fetch_candles(...)` async interface.
- `app/services/market_data/providers/errors.py`
  - Defines provider-layer exceptions for safe API handling.
- `app/services/market_data/providers/registry.py`
  - Registers provider names: `MOCK`, `MT5`, `UPSTOX`, `CSV`.
  - Only `MOCK` is implemented in MD-4.
  - `MT5`, `UPSTOX`, and `CSV` are reserved placeholders for future phases.
- `app/services/market_data/providers/mock_provider.py`
  - Deterministic dev/test-only candle generator.
  - Does not call any broker.
  - Intended only for `/fetch-preview` and `/fetch-import` smoke testing.

### New admin endpoints

- `POST /api/v1/admin/market-data/fetch-preview`
  - Admin only.
  - Resolves provider from registry.
  - Validates instrument and timeframe.
  - Fetches candles from provider.
  - Runs MD-2 normalization/validation via dry-run upsert.
  - Does not save candles.

- `POST /api/v1/admin/market-data/fetch-import`
  - Admin only.
  - MD-4 allows `MOCK` provider only.
  - Fetches deterministic candles and saves through MD-2 safe upsert service.
  - Uses existing unique key: `instrument_id + timeframe + timestamp`.

### Risk notes

- No real MT5 or Upstox code was added in this phase.
- No frontend code was changed.
- Existing CSV upload endpoint remains unchanged.
- Existing backtest and live-trading logic were not modified.
- MOCK provider data is not real market data and should only be used for smoke testing.

### MD-4 verification payload

```json
{
  "provider": "MOCK",
  "symbol": "TEST",
  "instrument_id": 1,
  "timeframe": "15m",
  "start_date": "2025-01-01",
  "end_date": "2025-01-02"
}
```

Expected behavior:

1. `/fetch-preview` returns a summary with `saved = false`.
2. `/fetch-import` inserts/updates MOCK candles.
3. Re-running `/fetch-import` updates existing candles instead of creating duplicates.

---

## Phase MD-5 update — MT5 Historical Candle Fetch + Import

Implemented a real MT5 historical candle provider for Admin Market Data without changing live execution or the existing MT5 broker connection page.

### New provider file

- `app/services/market_data/providers/mt5_provider.py`
  - Provider name: `MT5`.
  - Uses the local MetaTrader5 Python package and an already logged-in MT5 terminal session.
  - Fetches historical rates with `copy_rates_range`.
  - Converts MT5 rates into MD-2 normalized candle-compatible rows:
    - `timestamp`
    - `open`
    - `high`
    - `low`
    - `close`
    - `volume` using `real_volume`, then `tick_volume`, then `volume` fallback.
  - Selects the symbol with `symbol_select` and tries broker suffix candidates such as `XAUUSDm` when available in Market Watch.
  - Does not send orders and does not call any live execution logic.

### Provider registry update

- `MT5` now resolves to `MT5MarketDataProvider`.
- `MOCK` remains available for smoke testing.
- `UPSTOX` and `CSV` remain reserved placeholders for later phases.

### Admin endpoint updates

- `POST /api/v1/admin/market-data/fetch-preview`
  - Now supports `provider = MT5`.
  - Fetches MT5 candles and validates through MD-2 dry-run upsert.
  - Does not save rows.

- `POST /api/v1/admin/market-data/fetch-import`
  - Now supports `provider = MT5` and `provider = MOCK`.
  - Saves MT5 candles into `market_data` through MD-2 safe upsert.
  - Supports optional `dry_run` in the request body.

### Supported MT5 timeframes

- `1m`
- `5m`
- `15m`
- `30m`
- `1h`
- `4h`
- `1d`

### Clean error messages added

- MT5 package not installed / terminal not available.
- MT5 initialize failed.
- Symbol not found or not selectable.
- No candles returned.
- Unsupported timeframe.
- MT5 historical fetch failure.

### MD-5 verification payload

```json
{
  "provider": "MT5",
  "instrument_id": 10,
  "symbol": "XAUUSD",
  "timeframe": "15m",
  "start_date": "2024-01-01",
  "end_date": "2024-02-01",
  "dry_run": false
}
```

### MD-5 verification steps

1. Start MetaTrader 5 terminal on the same machine where the API runs.
2. Login to the demo account.
3. In MT5 Market Watch, right-click and choose Show All.
4. Open the target symbol chart once, for example `XAUUSD` or broker suffix symbol such as `XAUUSDm`.
5. Start API.
6. Open `/docs`.
7. Test `/api/v1/admin/market-data/fetch-preview` with `provider = MT5`.
8. Test `/api/v1/admin/market-data/fetch-import` with `provider = MT5`.
9. Query `market_data` for the selected `instrument_id`, `timeframe`, and date range.
10. Re-run the same import and confirm candles are updated, not duplicated.
11. Run existing user backtest for the same instrument/timeframe/date range.
12. Confirm no live order is placed. This phase only imports historical candles.

### Risk notes

- MT5 historical import depends on the MT5 terminal and broker history availability.
- If MT5 returns no rows, open the exact symbol chart in the terminal and retry.
- Broker-specific suffixes may be required, for example `XAUUSDm` instead of `XAUUSD`.
- No SQL change was required.

## Phase MD-6 update — Upstox Historical Candle Fetch + Import

### Files added/changed

- Added `app/services/market_data/providers/upstox_provider.py`.
- Updated `app/services/market_data/providers/registry.py` so `UPSTOX` resolves to the real Upstox historical provider.
- Updated `app/api/v1/admin_market_data.py` fetch request payload to accept optional `instrument_key` and `broker_account_id`, and to pass provider context safely into adapters.

### Upstox provider behavior

- Uses the existing `UpstoxAdapter` and existing encrypted broker account token flow.
- Loads a connected `UPSTOX` broker account from `broker_accounts`, or uses `broker_account_id` if supplied.
- Does not place orders and does not touch live execution logic.
- Fetches historical candles from the existing Upstox v3 historical candle endpoint constants.
- Normalizes Upstox candle rows into the MD-2 ingestion shape:
  - `timestamp`
  - `open`
  - `high`
  - `low`
  - `close`
  - `volume`

### Supported timeframes

- `1m`
- `5m`
- `15m`
- `30m`
- `1h`
- `1d`

### Endpoint payload example

```json
{
  "provider": "UPSTOX",
  "instrument_id": 5,
  "symbol": "NIFTY",
  "instrument_key": "NSE_INDEX|Nifty 50",
  "timeframe": "15m",
  "start_date": "2024-01-01",
  "end_date": "2024-02-01",
  "dry_run": false
}
```

### Error handling added

- Missing connected Upstox account/token.
- Expired/unauthorized token.
- Rate limit response.
- Unsupported timeframe.
- Missing/invalid `instrument_key`.
- No candles returned.

### SQL

No SQL is required for MD-6. The endpoint accepts `instrument_key` directly in the request, so this phase does not need to alter the `instruments` table.

### Verification steps

1. Confirm Upstox account is connected and tested from the broker page.
2. Start API.
3. Open `/docs`.
4. Run `POST /api/v1/admin/market-data/fetch-preview` with `provider = UPSTOX` and `instrument_key = NSE_INDEX|Nifty 50`.
5. Run `POST /api/v1/admin/market-data/fetch-import` with the same payload and `dry_run = false`.
6. Query `market_data` for the selected `instrument_id`, `timeframe`, and date range.
7. Re-run the same import and confirm duplicate candles are updated, not duplicated.
8. Run existing user backtest for that instrument/timeframe/date range.
9. Confirm no live order is placed.

## Phase MD-8 — Freshness, Coverage, Refresh Missing Candles

Implemented safe market-data freshness improvements and a missing-candle refresh flow.

Backend additions:
- Dataset freshness now returns market-aware fields: `instrument`, `exchange`, `market`, `timeframe`, `record_count`, `first_candle_at`, `latest_candle_at`, `expected_freshness_status`, `missing_from_date`, `freshness_age_hours`, and uppercase `status`.
- Freshness rules cover 5m, 15m, 1h, and 1d with simple CRYPTO 24x7, FOREX 24x5, and INDIAN_EQUITY/NSE weekday handling.
- Added `POST /api/v1/admin/market-data/refresh-missing`.
- Refresh Missing finds latest stored candle, subtracts a small overlap buffer, fetches from MT5/UPSTOX/MOCK providers, and upserts with existing MD-2 safety.

Frontend additions:
- Dataset coverage table now shows missing-from date and market rule.
- Added per-dataset Refresh Missing action. It uses the selected broker provider and current dry-run/end-date controls.

No SQL required.
No live trading/order execution logic changed.
No backtest engine logic changed.
