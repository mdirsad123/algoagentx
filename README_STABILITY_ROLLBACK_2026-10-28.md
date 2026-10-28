# AlgoAgentX V6.4 — Stability rollback (28 Oct 2026)

## Root cause
The supplied `algoagentx(5).zip` / previous packaged `.env.prod` contains 62 `REPLACE_WITH_EXISTING_LOCAL_VALUE` entries, including seven INT/BOOL values. Pydantic crashes before either worker starts. The UI screenshots of a previous successful run cannot prove the current workers are running.

## Changed vs latest broken archive
- Restored known-running *pre-session-gap* `auto_runner_service.py`, `live_tradelocker_candle_worker.py`, `broker_candle_service.py`, and `candle_catchup.py` from user-provided `algoagentx(4).zip`.
- Kept generic V6.4 incremental adapter + the original DB `source_code` and source SHA matching, `80,000` warmup, history max `200,000`, and existing project frontend/backend.
- Kept adaptive polling after no-data, including M5-close +10s after sustained idle.
- Set default operational flags for non-blocking latest-candle runner: sequential catch-up OFF, session gap resume OFF, gap backfill OFF. This is a **stability rollback** rather than an exact historical gap replay; `RUNNER_CANDLE_GAP` may still be logged and missing signals cannot be ruled out.
- Added `RECOVER_STABLE_ENV.ps1` to restore only placeholder values **from a private original backup** (your local old `algoagentx(4).zip` or `.env.prod.backup.*`) and apply safe flags; it does **not** change broker credentials, source SHA or UI Auto Trade setting.
- Excluded real `.env.prod` and sensitive files from distributable. **Do not copy the redacted `.env.prod` from the prior broken ZIP.** This package has no live credentials.

## Deployment — Windows PowerShell
1. Back up your project and save the current `.env.prod` in a private folder. Extract release ZIP to another folder, then merge its project code into `D:\Stock_market\algoagentx`, keeping the **existing local** `.env.prod`, database, `.env` secrets and Docker volumes. If you have a working earlier `algoagentx(4).zip`, keep it on your machine.
2. From the project root execute:

```powershell
cd D:\Stock_market\algoagentx
powershell -ExecutionPolicy Bypass -File .\RECOVER_STABLE_ENV.ps1 -ReferenceZip 'D:\Downloads\algoagentx(4).zip'
docker compose --env-file .env.prod config --quiet
```

If you have a valid `.env.prod` backup instead, use `-ReferenceEnv 'D:\path\to\original.env.prod'`. If nothing needs restoring, call script without either argument.

3. Import-test the real container settings **before starting workers** (after source merge):

```powershell
docker compose --env-file .env.prod run --rm --no-deps --entrypoint python live_legacy_runner_worker -c "from app.core.config import settings as s; print('CONFIG_OK',s.live_incremental_enabled,s.live_incremental_adapter_enabled,s.live_runner_sequential_catchup_enabled,s.live_tradelocker_gap_backfill_enabled)"
```

Expected: `CONFIG_OK True True False False`. The command does not place an order.

4. Once any current order evaluation has completed, recreate **only these two workers**:

```powershell
docker compose --env-file .env.prod up -d --no-deps --build --force-recreate live_tradelocker_candle_worker live_legacy_runner_worker
docker compose --env-file .env.prod ps live_tradelocker_candle_worker live_legacy_runner_worker
docker compose --env-file .env.prod logs -f --tail=80 live_tradelocker_candle_worker live_legacy_runner_worker
```

## Monitoring criteria
- `TradeLocker candle fetch ... ready=True` with new closed M5 timestamps. Normal ingestion should typically be seconds after broker publishes a candle; no strict 5-second guarantee.
- First V6.4 cold restart: `RUNNER_INCREMENTAL_PRIMED bars=80000` with `mode=FULL_HISTORY`, then `RUNNER_INCREMENTAL_DONE` and `mode=RETAINED_INCREMENTAL` for subsequent consecutive bars.
- During extended no-data: `TRADELOCKER_NO_NEW_CANDLE_BACKOFF`, without excessive REST request loops.
- Verify **at least four consecutive** M5 candle opens, no repeated startup exception, no unintentional broker orders, and no growing backlog.
- A post-restart `RUNNER_CANDLE_GAP` warning/error documents unconfirmed intermediate evaluations; it is not resolved by this stability rollback. TradeLocker history, strategy state and backtest signal parity need a separate systematic replay study.

## Rollback
Preserve the existing project before merging. Restore that backup and the private `.env.prod` backup saved by `RECOVER_STABLE_ENV.ps1` (filename `.env.prod.pre_stability_fix.*`). Restart the two workers via the commands above.

## Important
No broker, Docker or database was available to the offline tests. A source ZIP cannot guarantee live fills, parity or 54% future win rate. Experimental V6.4 hybrid execution remains different from certified full-history parity. This package does not switch off DEMO Auto Trade, but enables the previously supported stale-order age guard to avoid placing old signals at new prices.
