# AlgoAgentX TradeLocker — No-new-candle retry fix (M5, any selected symbol)

## Root cause in the user's Nov 8 2026 logs

TradeLocker REST returned `HTTP 200` with an empty list of candles during the Gold market break. `broker_candle_service.refresh_deployment_candles` converted the empty list to `HTTPException(400)`. This made `live_tradelocker_candle_worker` execute its generic exception handler and retry every 5 seconds, *bypassing* the existing boundary-aware no-data backoff. The 80,000-candle warmup had already succeeded (80,005 stored).

## This patch changes **only the TradeLocker candle-ingestion workflow**

- Adds an optional `allow_empty=False` argument to the existing refresh function. Only the independent TradeLocker live candle worker opts in with `allow_empty=True`.
- An empty successful broker response is returned as `no_new_candle=True`, logged at INFO instead of raising HTTP 400. It **does not prove market closed**; empty results may also occur with delayed feeds / symbol problems.
- Existing schedule then runs 2 short retries at 8-second intervals following the first missing candle. On prolonged absence, it polls **once per new selected-timeframe close** (+10s idle grace on M5), rather than retrying every 5 seconds.
- On a genuine new candle it stores the bar and resumes the normal runner notification path. No fake candles are generated.
- Broker 429, 401, API failure and network errors still surface as errors. The default behavior of other refresh callers is unchanged.
- No V9.32 strategy, SHA, `.env.prod`, DB, orders or warmup code was modified.

## Install on Windows PowerShell

1. Extract this ZIP to `D:\Stock_market\candle_fix` (keeping the folders).
2. Ensure no broker order is being submitted while you rebuild the service. Your strategy workers and broker credentials are not modified by the patch.
3. Run:

```powershell
powershell -ExecutionPolicy Bypass -File "D:\Stock_market\candle_fix\APPLY_TRADELOCKER_NO_CANDLE_FIX.ps1" -TargetRoot "D:\Stock_market\algoagentx"
cd D:\Stock_market\algoagentx
docker compose --env-file .env.prod config --quiet
docker compose --env-file .env.prod up -d --build --no-deps --force-recreate live_tradelocker_candle_worker
```

No change to `LIVE_INCREMENTAL_AUTHORIZED_SOURCE_SHA256` or `LIVE_INCREMENTAL_REQUIRE_ADAPTER_INSTRUMENTS` is necessary for **this** issue.

For expected no-data behavior, the existing setting `LIVE_TRADELOCKER_BOUNDARY_POLL_ENABLED=true` should remain enabled. It defaults to true in this supplied project; only set it if your `.env.prod` explicitly disables it.

## Verify

```powershell
docker logs --since 20m algoagentx_live_tradelocker_candle_worker 2>&1 |
  Select-String -Pattern "TRADELOCKER_NO_NEW_CANDLE_BACKOFF|TradeLocker candle fetch|TradeLocker candle fetch failed"

docker logs --since 20m algoagentx_live_legacy_runner_worker 2>&1 |
  Select-String -Pattern "RUNNER_NO_NEW_CANDLE_IDLE|RUNNER_GENERATE_COMPLETE|RETAINED_INCREMENTAL|RUNNER_CANDLE_BACKFILL_WAIT"
```

Expected when no market data: INFO `TradeLocker candle fetch ... ready=False`, then INFO `TRADELOCKER_NO_NEW_CANDLE_BACKOFF` after the short retry budget. After that, once per M5 close (plus 10 seconds) rather than 5-second exception spam.

When broker data resumes: `TradeLocker candle fetch ... ready=True`. The actual V9.32 runner behavior still depends on whether its incremental adapter is installed, signal parity, and deployment configuration. This patch **does not** resolve V9.32's historical-vs-live right-edge signal mismatch; automated order approval remains blocked in the previously supplied experimental V9.32 build.

If market reopened but zero bars continue, verify symbol/route mapping and broker feed separately. A session/weekend gap may still trigger `RUNNER_CANDLE_BACKFILL_WAIT` because historical-gap verification is a separate feature.

## Offline validation done here

- Python syntax compilation of both patched modules and modified/new tests: passed.
- Isolated async service tests: empty opt-in response, unchanged default HTTP400, unchanged broker exception handling: passed.
- Time-aligned scheduling sanity tests: initial +8s retries; subsequent M5-boundary schedule; normal schedule after successful candle: passed.
- Full project test suite and connected TradeLocker/live execution: **not run**, as neither broker connection nor a complete Python service environment is available in the offline runtime. Added regression tests under `AlgoAgentXAPI/tests` for use in your project environment.
