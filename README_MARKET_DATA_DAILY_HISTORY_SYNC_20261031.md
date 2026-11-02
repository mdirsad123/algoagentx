# AlgoAgentX: cTrader-first Daily Market History Sync (2026-10-31)

## What was changed

- `Market Data` admin page has **Manual Fetch**, **Automatic Daily Sync**, and **Connect Broker** tabs. The manual MT5 date-range import, datasets, freshness and import jobs remain intact. The CSV upload was removed from the page only; the existing CSV API route remains.
- The `Connect Broker` tab reuses the *existing authenticated cTrader OAuth* and trading-account discovery flow. To connect TradeLocker or other providers, use the existing Brokers page, then configure them on Market Data. Only the logged-in admin can connect their own cTrader credentials; this tab does not impersonate other users.
- Admin account discovery shows connected broker accounts for all users with masked IDs and status. Only previously connected, supported, authorized account/subaccount IDs can be configured.
- Dedicated, read-only history adapters reuse existing cTrader Open API and TradeLocker historical rate methods. Broker-native timeframe mapping, closed-candle checks, small backward overlap, idempotent source-specific inserts, per-run bounded 2-day windows, manual cloud-broker date-range backfill, and dry-run are included.
- Daily schedule uses a **dedicated Celery Beat app at 03:00 Asia/Kolkata** plus a low-concurrency history worker/queue. It is opt-in, feature-flagged OFF by default, and separate from live candle and trading workers. Per-day and per-config durable unique keys prevent duplicate scheduled jobs.
- Four new PostgreSQL tables isolate per-account historical candles, feed configuration, batch dispatch and audit runs. Original `market_data` and `live_market_candles` are NOT changed. Existing backtest series will not be overwritten or mixed with another broker's OHLCV. Primary publishing is insert-only and available only when the legacy series is empty.

## Implementation paths

- API routes: `AlgoAgentXAPI/app/api/v1/admin_market_data_sync.py`, included via `app/api/v1/router.py`.
- Broker/history sync: `AlgoAgentXAPI/app/services/market_data/daily_sync.py`.
- Dedicated scheduler/worker tasks: `AlgoAgentXAPI/app/services/market_data/daily_tasks.py`.
- ORM tables: `AlgoAgentXAPI/app/db/models/market_data_sync.py`.
- Alembic revision: `AlgoAgentXAPI/alembic/versions/20261031_market_data_auto_sync.py`.
- Admin page: `AlgoAgentXApp/app/(admin)/admin/market-data/page.tsx` and `DailyHistoryPanel.tsx`.
- Frontend API client: `AlgoAgentXApp/lib/api/admin.ts`.
- Tests: `AlgoAgentXAPI/tests/test_daily_market_history.py`.
- Manual SQL: `SQL_MANUAL_MARKET_DATA_SYNC_20261031.sql`.

## Deploy carefully

1. **Back up your PostgreSQL production database before updating.** Deploy the new project files without copying the supplied `.env.prod` over your own environment configuration. The new feature is OFF by default.
2. Run **EITHER** Alembic **OR** the manual SQL (not both):

   **Recommended Alembic** (run from project root where Docker Compose lives):

   ```bash
   docker compose --env-file .env.prod run --rm --no-deps api alembic upgrade head
   ```

   **Manual PostgreSQL option** (run from project root after Postgres is running):

   ```bash
   docker compose --env-file .env.prod exec -T postgres_prod sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1' < SQL_MANUAL_MARKET_DATA_SYNC_20261031.sql
   ```

   Once verified and only if the previous Alembic revision was applied, mark this SQL revision in Alembic without rerunning it:

   ```bash
   docker compose --env-file .env.prod run --rm --no-deps api alembic stamp 20261031_market_data_auto_sync
   ```

3. Start only the new history services and API/UI as appropriate; do not restart the live collector/runner:

   ```bash
   docker compose --env-file .env.prod up -d --build --no-deps api market_data_history_worker market_data_history_scheduler web
   ```

   **Note:** In the supplied Compose, the Next.js service is named `web` (verify with `docker compose config --services`). If the web service name differs in your deployment, substitute its actual name. Existing Postgres and Redis must already be running.

4. Connect cTrader with OAuth in **Admin → Market Data → Connect Broker** (or reuse an existing linked cTrader account); discover the available trading subaccounts.
5. In **Automatic Daily Sync**, choose account/subaccount, Market Master instrument, *exact broker symbol*, timeframe (e.g., `5m`) and optional initial UTC date, then add a source-specific feed. Configurations are **OFF by default**. For large missing history, use the dedicated manual date-range fetch to backfill deliberately.
6. Test **Preview / Dry Run** and **Run Now**, examine saved feed candles and recent runs. Enable individual feeds when happy with the source data.
7. To enable the daily 03:00 IST dispatcher, add this line to your own `.env.prod` and recreate ONLY the history scheduler and worker:

   ```env
   MARKET_DATA_DAILY_SYNC_ENABLED=true
   ```

   ```bash
   docker compose --env-file .env.prod up -d --no-deps --force-recreate market_data_history_worker market_data_history_scheduler
   ```

## PostgreSQL inspection queries (read-only)

```sql
SELECT id, provider, subaccount_id, broker_symbol, timeframe, enabled, is_primary,
       publish_approved, last_status, checkpoint
FROM market_data_sync_configs ORDER BY created_at DESC;

SELECT feed_id, COUNT(*) AS candles, MIN(timestamp) AS first_open_utc,
       MAX(timestamp) AS last_open_utc
FROM market_data_feed_candles GROUP BY feed_id;

SELECT feed_id, status, scheduled_date, fetched, inserted, invalid, skipped,
       last_before, last_after, started_at, finished_at
FROM market_data_sync_runs ORDER BY created_at DESC LIMIT 30;

SELECT scheduled_date, dispatched_at
FROM market_data_sync_batches ORDER BY scheduled_date DESC LIMIT 10;
```

## Important limitations and verification status

- **Working cTrader and TradeLocker read-only historical methods are integrated**, but no live broker API requests or live PostgreSQL integration test were possible in the provided offline container. Your credentials, account permissions, symbol mapping and actual data quality must be verified on your deployment before enabling automated daily jobs.
- MT5, Upstox, Binance and other accounts appear in the all-users discovery, but automated account-scoped history has **NOT** been enabled for those providers in this patch. Existing manual provider importing remains. The cloud history worker does **not** depend on the Windows MT5 terminal.
- The scheduled sync catches up from the latest saved *source feed* candle; it does not silently fill earlier internal holes. A bounded manual date-range fetch can backfill specific known gaps. UTC-grid last-expected calculation is a best-effort target and not a complete broker session/holiday calendar; session gaps can be flagged PARTIAL.
- A legacy backtest series with unknown existing broker provenance stays untouched. Setting a primary broker when that series is nonempty does **not** publish its candles into legacy `market_data` until an independently reviewed source-adoption/migration workflow is performed. History remains available in source-isolated tables.
- The history worker verifies the **exact symbol name** before saving source data, refusing the execution adapters' optional fuzzy/suffix match. Check symbol suffixes in the broker's Market Watch/list when configuring a feed.
- Offline verification: **9/9 new backend unit tests passed**; additional existing cTrader/TradeLocker test collection was blocked by a missing `redis` Python module in this offline environment; Python source compilation passed; Alembic single head and offline migration SQL generation passed; Docker Compose YAML structure parsed; changed TypeScript file syntax parsed without errors. **Full `next build`, Docker integration, Celery runtime, migrations against a real DB, and real cTrader/TradeLocker history remain unverified** because dependencies/Docker/broker credentials were unavailable in the test environment.
