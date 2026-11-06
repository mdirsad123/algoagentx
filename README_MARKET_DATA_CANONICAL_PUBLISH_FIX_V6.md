# AlgoAgentX Market Data V6 — Canonical candle publication repair

This patch is based on the **V5 ZIP** previously provided in this conversation, not a fresh export of your local Windows working tree. It is an offline source-code fix, **not** a deployment to your Docker database. It does not touch live V6.4 strategy/runner logic or order placement.

## Confirmed cause of the repeated error

In `AlgoAgentXAPI/app/api/v1/admin_market_data_sync.py`, V5's `/publish-preview` endpoint called `preview_publication` without importing it. Its `/publish-missing` endpoint called `process_market_canonical_publish` without importing it. The generic frontend error was therefore possible even though cTrader candles had been fetched and stored in `market_data_feed_candles`.

- **Source `UP_TO_DATE`, inserted 0** only describes the isolated broker feed. A successful re-fetch of overlapping candles naturally inserts zero new source rows.
- **Legacy Coverage and Backtest** use the separate `market_data` table. Source rows must first be explicitly approved and published; they do not appear in Backtest just because a source import succeeded.
- Screenshot of PostgreSQL schema shows `market_data.timestamp` as **timestamp(3)** without time zone. The source feed uses `TIMESTAMPTZ`. PostgreSQL transaction timezone now explicitly uses UTC during preview and publication to avoid shifts at conversion/joins.
- The screenshot's OHLC values are `NUMERIC(65,30)`, which explains 30-digit zero padding in DBeaver. This patch does **not** silently change the type or round historical candles. Newly published OHLC use 5 significant post-decimal positions; source-verification UI formats to exactly 5dp. Existing DBeaver table view can still pad zeros to 30 digits because the column's fixed scale remains 30.

## Changed files

- `AlgoAgentXAPI/app/api/v1/admin_market_data_sync.py` — missing imports for two real endpoints.
- `AlgoAgentXAPI/app/services/market_data/feed_publish.py` — UTC-safe insert-only publishing, exact provenance and run-audit timestamp conversion, bounded pages, round *new canonical* OHLC to 5 decimals, no overwrites, clearer page audit.
- `AlgoAgentXAPI/app/services/market_data/daily_tasks.py` — persist final publish status and counts; sanitized exception class/SQLSTATE diagnostics.
- `AlgoAgentXAPI/app/services/market_data/daily_sync.py` — distinguish missing migration/schema SQL errors from broker connection failures.
- `AlgoAgentXAPI/app/services/market_data/feed_inspection.py` — read-only 5dp OHLC display for samples.
- `AlgoAgentXApp/app/(admin)/admin/market-data/HistorySelect.tsx` — remove redundant Radix value that could duplicate selection text.
- `AlgoAgentXAPI/tests/test_market_data_publish_runtime_v6.py` plus adjusted existing tests.
- `VERIFY_MARKET_DATA_CANONICAL_V6.sql` — read-only database proof for source/canonical coverage and OHLC display.
- `OPTIONAL_ONCE_ONLY_BTCUSD_CANONICAL_REPAIR_V6.sql` — **manual-only, opt-in**, approved BTCUSD cTrader source -> canonical insert-only recovery if required. No SQL is executed automatically.

## Database changes

**No new migration is required for V6.** The existing **V5** migration must already be applied: `market_data_sync_configs.is_archived` and `market_data_canonical_provenance` table. If `SELECT to_regclass('public.market_data_canonical_provenance');` returns NULL, apply V5 SQL **once**; do not rerun the full old migration stack blindly.

**Do not ALTER `market_data` from NUMERIC(65,30) to NUMERIC(65,5) automatically.** That would recast existing backtest prices and may change V6.4 research results. To view 5 decimals in PostgreSQL, use `round(open,5)::numeric(65,5)` (examples in the verification SQL).

## Deploy on Windows (PowerShell)

1. Back up local PROD PostgreSQL and your project source; keep `.env.prod` unchanged.
2. Unzip the V6 project into your source tree (or copy only the patched files). Run from the directory containing `docker-compose.yml`.
3. Rebuild **only** the API, web UI, and dedicated history worker:

```powershell
docker compose --env-file .env.prod up -d --no-deps --build --force-recreate api web market_data_history_worker
```

Leave `market_data_history_scheduler` and **all live trading workers** unchanged.

4. Refresh your admin browser with Ctrl+Shift+R. Under `Market Data > Automatic Daily Sync`, select the **correct cTrader BTCUSD 5m feed** (broker symbol `BTCUSD`, not an old `BTCUSDm` config). It must be **Primary**. Click **Publish Missing**. Preview the source count, missing canonical rows, and price mismatches. Confirm the explicit **INSERT MISSING ONLY** merge.
5. Check **Recent daily/manual sync runs** until the **canonical-publish** run status becomes `UP_TO_DATE`. The publish job's **Inserted** count means newly added canonical backtest rows; the ordinary source-fetch job's **Inserted** count means newly added source rows. These are different counters.
6. Click **Refresh Coverage**. Your BTCUSD M5 `market_data` latest candle should reach the latest **saved, verified closed** source candle, unless that source has a gap. Check Backtest preview afterward.
7. For future new candles, leave `Primary • gap-fill ON`. Manual Fetch & Save and daily Run Now then copy new source timestamps to canonical automatically; they **never overwrite existing candles**. Only the initially stored source history needs one-time Publish Missing approval.

## Verify against the real database

Run **read-only** `VERIFY_MARKET_DATA_CANONICAL_V6.sql` in DBeaver against `algoagentx_postgres_prod`, or:

```powershell
Get-Content .\VERIFY_MARKET_DATA_CANONICAL_V6.sql | docker exec -i algoagentx_postgres_prod sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1'
```

Check `source_latest_utc`, `canonical_latest_utc`, `source_rows_not_yet_in_backtest`, and the last 10 canonical bars. Source count can remain unchanged while canonical row count increases.

If the UI job still fails, get **sanitized** errors from the API and dedicated worker (do not paste OAuth credentials):

```powershell
docker logs --since 15m algoagentx_api 2>&1 | Select-String 'publish-preview|publish-missing|NameError|Traceback|500'
docker logs --since 15m algoagentx_market_data_history_worker 2>&1 | Select-String 'Canonical missing-candle publish|DB_SCHEMA|code=|exception_class|ERROR'
```

If you're unable to use the API UI after the patch, the optional one-time SQL is a **separate fallback**. It refuses to operate until you replace the placeholder UUID with the exact **Primary + approved BTCUSD cTrader feed**. Do not execute it for any other instrument blindly. It never updates old OHLCV and records provenance in the same transaction.

## Scope and verification limitations

- Focused history suite: **33 passed, 2 skipped**. A separate six-test backtest warmup suite passed. The API route smoke test executes actual Preview and Publish Missing functions using stubbed optional imports, a fake database and queue; it passed. V6 Python code compiles and the modified TypeScript file parses. SQLAlchemy generated INSERT-only SQL, including UTC transaction settings and five-decimal rounding.
- Two production-import-dependent endpoint tests are skipped because `python-jose`, Celery and asyncpg are not installed in the lean offline runner; run them in your API Docker container.
- A real end-to-end PostgreSQL database commit, live cTrader API fetch, Next.js full build and browser refresh **cannot be claimed verified here**. The user must run the verification commands locally. This ZIP does not modify your database by itself.
