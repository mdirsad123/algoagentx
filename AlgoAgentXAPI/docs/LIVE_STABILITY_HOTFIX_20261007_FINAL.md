# AlgoAgentX Live Stability Hotfix — 07 Oct 2026

This build keeps the dynamic strategy registry, copy-trading, partial-exit and event-driven cTrader architecture intact. It changes only live infrastructure/runtime behavior that was causing CPU/DB pressure.

## Root causes fixed

1. `LiveMarketCandle` ORM queries were hydrating joined deployment/user/strategy/broker relationships for every candle. A 1k/2k/20k history read therefore became a large multi-table query. Runner/history reads now select only compact candle columns.
2. The live page readiness flow was executing the dynamic pandas strategy inside API requests. This could hold an API DB session for a long time and starve the SQLAlchemy pool. Readiness is now observer-only; deep strategy execution remains in explicit Compatibility / Full Dry Test actions.
3. A recreated Redis strategy consumer group started from `0-0`, which could replay old stream history. New groups now start at `$`, while pending entries still provide crash recovery.
4. Reclaimed/stale candle events could re-run expensive strategy code even when `last_processed_candle_time` already proved the candle had completed. They are now ACKed immediately as `ALREADY_PROCESSED`.
5. Market bootstrap wrote candles one INSERT at a time. It now uses 250-row idempotent bulk upserts.
6. The API legacy scheduler was still enabled in `.env.prod`. This local stability profile disables it while the cTrader Redis event pipeline owns strategy execution.

## Temporary low-history stability profile

`.env.prod` intentionally contains:

```env
LIVE_LEGACY_RUNNER_ENABLED=false
LIVE_WORKER_CONCURRENCY=1
LIVE_MARKET_DEPLOYMENT_SCAN_SECONDS=30
LIVE_MARKET_BOOTSTRAP_CANDLES=300
LIVE_STRATEGY_HISTORY_DEFAULT_BARS=1000
LIVE_STRATEGY_HISTORY_OVERRIDE_BARS=1000
LIVE_STRATEGY_HISTORY_PAGE_SIZE=500
```

`LIVE_STRATEGY_HISTORY_OVERRIDE_BARS=1000` is a temporary operational override. It does not modify strategy source code, but it DOES change the history supplied to the live strategy and therefore should not be used to judge final V1.37/V3.5 parity/performance.

After the stack is stable, restore authored strategy requirements with:

```env
LIVE_STRATEGY_HISTORY_OVERRIDE_BARS=0
LIVE_STRATEGY_HISTORY_DEFAULT_BARS=2000
```

With override `0`, the existing strategy contracts become active again:

- Resistance Rejection V3.5: 2,000 bars
- Trend-Following V1.37: 20,000 bars

`LIVE_MARKET_BOOTSTRAP_CANDLES=300` can remain small because large historical warm-up belongs to `live_history_worker`; market bootstrap is only startup recovery.

## Deployment

From the project root:

```powershell
docker compose --env-file .env.prod -f docker-compose.yml down
docker compose --env-file .env.prod -f docker-compose.yml up -d --build

docker compose --env-file .env.prod -f docker-compose.yml ps
docker stats --no-stream
```

Do not use `down -v`.

## First validation

For the first 10-15 minutes, run one cTrader DEMO deployment (prefer V3.5) and verify:

```powershell
docker stats --no-stream
```

The strategy worker should be mostly idle between M5 closes instead of staying near 100% CPU continuously.

Check recent logs:

```powershell
docker compose --env-file .env.prod -f docker-compose.yml logs --tail=250 api live_market_worker live_strategy_worker postgres_prod redis
```

There should be no repeated `QueuePool limit ... timed out` loop, no multi-minute `/readiness` request, and no continuous strategy recomputation between candle closes.

If old pending Redis messages exist, the strategy worker will safely ACK already-processed candles using the deployment cursor. Do not delete Redis/DB volumes.

## Validation performed on this package

- Python compile check: all `app` and `strategies` modules compile.
- Focused tests: `test_live_strategy_history_profile.py` and `test_strategy_registry_dynamic_live.py` pass (13 tests).
- Query-shape check confirms compact candle history SELECT contains no ORM JOIN.
- A broader local test requiring the Python `redis` package could not be collected in the artifact environment because that dependency is not installed there; the production Docker image installs project requirements.
