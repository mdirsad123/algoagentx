# AlgoAgentX — Market Data V5: dropdowns, canonical backtest gap filling, archive

**Base:** previous V4 ZIP (`algoagentx_market_data_dropdown_storage_verify_v4_20261031.zip`). This is a source patch, **not a deployment to your local Docker**. It has not been run against your actual cTrader account or PostgreSQL database.

## Why the coverage was stale

V4 source-specific cTrader candles are saved in `market_data_feed_candles`. The legacy coverage and backtest engine read `market_data`. The old Coverage “Refresh Missing” endpoint chooses the manual-import provider, which does not know CTRADER. Therefore a successful source import did not automatically advance backtest coverage.

“Fetched 6,266, inserted 4” means 6,266 upstream bars were processed and only four new rows were added to **the source feed**, due to overlapping/deduplicated timestamps. This does not measure canonical publication.

## V5 changes

1. `HistorySelect` renders its selected label outside Radix Select's dynamic Value and constrains trigger height, preventing visually blank/dropdown oversized fields. Manual fetch and daily feed selections persist across tab switches in browser session storage; no tokens are stored.
2. Explicit **Primary → Publish Missing** for an existing BTCUSD/XAUUSD 5m backtest dataset. A preview shows source rows, missing canonical timestamps, overlap and differing OHLC values. Confirmation is required to approve a **MIXED SOURCE** dataset.
3. The dedicated market-history worker publishes missing timestamps from **all already stored source rows** in bounded, resumable/idempotent chunks, then audits added timestamps in `market_data_canonical_provenance`. `market_data` rows that already exist are never updated or deleted (`ON CONFLICT DO NOTHING`). This is an INSERT-only merge, not averaging/deduplication by price.
4. Future daily/manual source syncs publish verified closed candles **if** their feed is Primary and the explicit approval is ON; the original isolated feed remains intact. `Updated` in history run now tracks newly published canonical candles (while `Inserted` for an ordinary fetch tracks source insertions).
5. The canonical Coverage **Fill Gaps / Refresh** action resolves the selected Primary broker source and queues publication of saved source rows, followed by a separate incremental broker fetch. It no longer sends `CTRADER` to the legacy supported-provider registry. Use **Refresh Coverage** after the worker finishes. Coverage dataset count may stay 4; `total_records` and `last_candle_at` should advance.
6. **Delete** archives a feed configuration (removes it from schedule and active UI). It **does not destroy candles or audit history**. It cannot run during an active sync. Recreating the exact feed unarchives it with auto-fetch OFF.
7. Same MT5 legacy manual fetch, other backtests and V6.4 live strategy are untouched.

### Important limitation

Publishing fills canonical timestamps **that already exist in the selected broker feed**. If your cTrader source itself has an internal history gap or you need dates older than its first stored candle, fetch the missing dates using **Manual cTrader / TradeLocker date-range fetch** and republish; daily automatic sync fetches forward from the latest saved broker candle and does not invent missing historical candles or treat session breaks as gaps. Broker trading calendars and prices can differ. Backtests spanning the boundary between MT5 and cTrader data may change: revalidate your research before comparing results.

## Deploy to local PROD (PowerShell)

1. Backup your current local PROD PostgreSQL database and project. Keep your `.env.prod` unchanged.
2. **Apply exactly one migration method:**

**A — manual SQL, especially if you created the prior sync tables manually:**

```powershell
Get-Content .\SQL_MANUAL_MARKET_DATA_GAP_PUBLISH_V5.sql | docker exec -i algoagentx_postgres_prod sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1'
```

**B — Alembic:** if your Alembic revision history already includes `20261031_market_data_auto_sync` and all earlier revisions are applied, run the new revision via your normal Alembic upgrade workflow. **Do not run both SQL and Alembic upgrade.** Alembic's old legacy chain includes an offline-incompatible schema introspection revision, so `alembic upgrade head --sql` for the entire chain cannot be used as validation here. The V5 target migration was individually SQL-compiled successfully.

3. Copy the updated project files in place, then rebuild only history-related components and the admin API/web:

```powershell
docker compose --env-file .env.prod up -d --no-deps --build --force-recreate api web market_data_history_worker market_data_history_scheduler
```

4. Hard refresh `http://localhost:3000/admin/market-data` (Ctrl+Shift+R). Ensure the history worker is online.

5. For **BTCUSD** (already reported as Primary): choose Automatic Daily Sync → BTCUSD cTrader → **Publish Missing** → review exact overlap/mismatch counts → confirm. The worker publishes the already stored BTCUSD source candles. To fetch further candles, click **Run Now**. To verify canonical data, click **Refresh Coverage**.

6. For **XAUUSD**, choose its correct cTrader feed (exact broker symbol `XAUUSD`) → **Primary** → **Publish Missing** → confirm → **Run Now**. Do not change Market Master's MT5 symbol `XAUUSDm`; its instrument identity remains the same, while the cTrader feed's broker symbol is account-specific. Existing MT5 candles win at overlaps.

7. **Check PostgreSQL:**

```powershell
Get-Content .\VERIFY_MARKET_DATA_CANONICAL_V5.sql | docker exec -i algoagentx_postgres_prod sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1'
```

`market_data_canonical_provenance` records the source of **new V5-published** candles. Legacy rows (and any before V5 publishing) have no provenance record; this does not mean they are missing. An additional new `is_archived` column is created on `market_data_sync_configs`.

### Debugging after deployment

```powershell
docker logs --since 20m algoagentx_market_data_history_worker 2>&1 | Select-String "Canonical missing-candle publish|Market history run failed|market_data_daily.publish_missing|FAILED"
docker logs --since 20m algoagentx_api
```

Do not dump broker tokens or full `.env.prod` in shared logs.

## Verification performed in build environment

- 27 focused pytest tests: passed (older history coverage tests + V5 publishing regression tests).
- Python compilation: passed.
- Five changed TypeScript files: syntax transpilation passed (not a full Next.js typecheck/build; `node_modules` is absent from the uploaded archive).
- Standalone V5 Alembic upgrade SQL: generated successfully; full legacy migration chain's offline SQL generation is not supported by an unrelated earlier migration.
- ZIP integrity: checked when packaged.

**Not verified:** live PostgreSQL changes, actual broker connectivity, real-candle values, Docker container deployment and a complete frontend build. These steps require your local environment.
