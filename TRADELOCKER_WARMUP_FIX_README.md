# AlgoAgentX TradeLocker historical-candle warm-up fix (19 October 2026)

## Scope
This is a **targeted source patch**, not a new strategy or a replacement for the complete project. No trading strategy, broker order placement, or risk-guard logic is modified.

**Problem found:** The general backfill calls `TradeLockerAdapter.get_rates_history(count=40005)`, but that adapter caps each call at 30,000. When a subsequent request is queued, it fetches recent history instead of resuming from the oldest stored bar. Rate limiting and duplicate Celery retry handling amplify the problem.

## Modified files
- `AlgoAgentXAPI/app/services/live/broker_candle_service.py`: TradeLocker cursor pages of up to 1,500 bars, save/commit each successful page, resume from oldest saved candle; wait 3 seconds between requests; broker HTTP 429 propagates to task retry without replaying all successful pages.
- `AlgoAgentXAPI/app/tasks.py`: One retry path, longer exponential backoff, preserve `queued` Redis marker across retries; release only the running lock; clear marker on success or final failure.
- `AlgoAgentXAPI/app/services/live/history_warmup_queue.py`: Lengthen queue marker TTL to 2 hours to cover delayed retries.
- `docker-compose.yml`: change history worker `--max-tasks-per-child=1` to `50` to reduce repeat authentication/instrument requests; concurrency remains 1.
- `AlgoAgentXAPI/tests/test_tradelocker_candle_history_parity.py`: add offline backward-cursor resume regression.

## Apply
1. Back up the project and database. Disable Auto Trade or use a demo account for the first deployment test. Do not delete stored candles or reset Redis globally.
2. Copy the modified files from this ZIP into the matching relative paths of your project. Do not replace or disclose your environment or secrets files.
3. From the directory containing `docker-compose.yml`, run:

```bash
docker compose up -d --build api live_history_worker
docker compose logs -f --tail=100 live_history_worker
```

4. Confirm historical count progresses beyond 30,000 toward 40,000 and `STRATEGY_HISTORY_READY` is logged. Re-run the read-only compatibility/full dry test *after* history reaches the required count; never use order execution as a history test.
5. Check UI readiness and ensure no repeated 429 storms. Validate current closed-candle timestamps, broker status, and risk guards before re-enabling trading.

## SQL check (read-only)
```sql
SELECT deployment_id, source, timeframe,
       COUNT(*) AS closed_candles,
       MIN(candle_time) AS oldest_utc,
       MAX(candle_time) AS newest_utc
FROM live_market_candles
WHERE deployment_id = '67053cdc-60f4-454d-8868-2e84d760ab23'
  AND is_closed = TRUE
GROUP BY deployment_id, source, timeframe;
```

## Important additional check
Bundled `AlgoAgentXAPI/strategies/xauusd_5m_resistance_rejection_v3_5.py` declares `LIVE_HISTORY_BARS = 2000`; your screenshot requires 40,000. Inspect the **published DB strategy** `live_history_bars` / `required_history_bars` and the global `LIVE_STRATEGY_HISTORY_OVERRIDE_BARS` before changing anything. Do not reduce warm-up for an unrelated trend-following strategy without validating identical historical signals.

## Verification limitations
Offline adapter test suite: 11 passed. Python syntax compilation: passed. Integration with live TradeLocker API, your production Redis/Celery, and database was **not executed** in this isolated environment. The broker's actual historical retention and rate limits are not verified; if TradeLocker does not expose 40k M5 candles, an incomplete history state remains correct and automatic trading must stay blocked.
