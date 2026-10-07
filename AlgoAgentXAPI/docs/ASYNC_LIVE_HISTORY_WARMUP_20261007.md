# Async Live History Warm-up Fix — 07 Oct 2026

## Goal
Keep AlgoAgentX responsive while a strategy needs large broker history (for example Trend-Following V1.37 needs ~20,000 XAUUSD M5 bars for daily/4H context).

## Final architecture
- Fast live bootstrap remains `LIVE_MARKET_BOOTSTRAP_CANDLES=2000`.
- Platform default strategy history is `2000` bars.
- Trend-Following V1.37 declares/inferes `20000` bars because its source uses completed daily HTF features.
- Resistance Rejection V3.5 uses `2000` bars.
- Heavy warm-up never runs inside FastAPI, Compatibility, Dry Test, or the live strategy event worker.
- A dedicated Celery worker consumes queue `live_history` with concurrency 1.
- cTrader warm-up is fetched backwards in 1000-bar pages. Each page is committed immediately so progress becomes visible and a restart resumes from the oldest stored candle.
- Compatibility and strategy execution remain HOLD/FAIL-safe until enough history exists; they enqueue/deduplicate warm-up instead of blocking the browser.

## Production ENV
```env
LIVE_MARKET_BOOTSTRAP_CANDLES=2000
LIVE_STRATEGY_HISTORY_DEFAULT_BARS=2000
LIVE_STRATEGY_HISTORY_PAGE_SIZE=1000
LIVE_STRATEGY_HISTORY_MAX_BARS=100000
```

## Build/start the dedicated worker
From project root:

```bash
docker compose --env-file .env.prod -f docker-compose.yml up -d --build live_history_worker
```

If API/live workers also changed, rebuild these together:

```bash
docker compose --env-file .env.prod -f docker-compose.yml up -d --build \
  api live_history_worker live_market_worker live_strategy_worker live_reconcile_worker live_position_manager_worker web
```

## Observe warm-up
```bash
docker compose --env-file .env.prod -f docker-compose.yml logs -f live_history_worker
```

The deployment candle count should progress roughly:

`1999/20000 -> 2999/20000 -> 3999/20000 -> ... -> 20000/20000`

The UI/API should remain responsive during this process.

## Validation performed
- Python compile checks passed for all modified backend/strategy files.
- 44 targeted regression tests passed covering dynamic registry, history profile, deleted-deployment traces, copy isolation, symbol resolution, partial exit, runtime config, and MT5 cleanup paths.
- Actual strategy profile check: dynamic V1.37 source resolves to 20,000 bars; V3.5 resolves to 2,000 bars.
