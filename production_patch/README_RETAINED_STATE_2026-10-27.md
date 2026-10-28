# AlgoAgentX universal retained-state execution framework (2026-10-27)

## What this release does

A deployment-specific, in-process strategy instance can be retained between candles **only** when the strategy itself has an explicit, parity-verified incremental implementation. The system uses the normal full-history path for all other strategies, including today's DB-stored V6.4 unless its exact implementation is upgraded and verified. This release DOES NOT claim a 4–7 minute V6.4 `generate()` speedup.

The generic framework covers all strategies' **scheduling, candle pinning, contract checks, state invalidation, risk and order pipeline**. Strategy-specific incremental calculations cannot be invented generically: trendlines, zones, historical anchors and multi-timeframe context may depend on arbitrarily old data.

## Strategy interface v1

In the exact versioned strategy class, implement:

```python
LIVE_INCREMENTAL_VERSION = 1

def start_live_incremental(self, generated: pd.DataFrame) -> bool:
    """Called ONCE after the normal full-history generate().
    Prepare retained indexes/rolling indicators/zones from the exact full state.
    Return True only if fully initialized. Never place orders here.
    """
    ...

def on_closed_candle(self, candle: dict) -> pd.DataFrame:
    """Called once for the next CONSECUTIVE, finalized candle.
    Input: {'Date': timezone-aware UTC, 'Open', 'High', 'Low', 'Close', 'Volume'}.
    Update all mathematical dependencies of the original algorithm.
    Return a nonempty DataFrame whose last row has the identical original
    signal/SL/TP/risk/reason fields and Date == candle['Date'].
    Never place orders here: the platform's execution engine owns them.
    """
    ...
```

Do NOT just append the new row and call `generate()` again: that repeats the full cost. Calculate only the affected features/conditions, but prove same outputs on matching history.

## Activation (never enable for an unverified V6.4)

1. Save exact dynamic strategy code with the v1 methods; no changes to risk/order logic.
2. Run `python -m app.tools.check_live_incremental_parity --source <exact source.py> --csv <historical OHLCV.csv> --history-bars 80000 --checks 20 --report parity.json`. Choose datasets representing different regimes, gap/restart cases and actual broker symbols. This checker compares final signal/SL/TP-related payloads on selected candles, **not** full trading parity.
3. Independently reconcile entry/exit, signal bar, SL, TP, costs and backtest/live execution decisions for sufficient historical sequences and demo candles.
4. In a DEMO-only controlled rollout, set `LIVE_INCREMENTAL_ENABLED=true` in `.env.prod`, and on only the verified strategy's database `parameters` set `"live_incremental_enabled": true` and `"live_incremental_parity_verified": true`. The system also requires the strategy class methods and `LIVE_INCREMENTAL_VERSION=1`. These flags MUST NOT be enabled by default or for unrelated strategies.
5. One `live_legacy_runner_worker` instance must own the deployment. Do not scale multiple workers or enable simultaneous API auto-schedulers.
6. Restart/rebuild **only** after recording the last processed candle and making sure no live trade is in-flight. Process restarts intentionally discard memory state and perform a full cold warmup. There is no Redis pickle or persistence of executable Python strategy objects.

## Running / recovery behavior

- Initial eligible closed candle: normal 80K full `generate()`, then `start_live_incremental()` creates in-memory state.
- Next consecutive closed candle: read **one** compact OHLCV row; call `on_closed_candle()` without full replay. Validated output travels through the existing signal/risk/order pipeline.
- Parameters/source/runtime/timeframe/instrument change, cursor mismatch, skipped bar, previous finalized candle revision, process restart, invalid output, exception: state invalidated and full-history behavior is restored. A failing incremental update returns a retry request; it never invents a HOLD/BUY/SELL.
- Existing latest-only scheduler can report candle gaps. Exact in-order historical reconciliation is a separate project; no stale broker orders should be synthesized from historical gaps.
- V6.4's DB-stored `source_code` is NOT present in the attached source ZIP. Its internal `generate()` cannot be automatically transformed safely in this package. Do not claim this release meets real-time M5 execution until its actual incremental implementation is validated.

## Deployment and rollback

1. Back up the running Compose file, deployed application images/source, database and Redis persistent data; keep `.env.prod` and credentials in place. Do not ship environment files with diagnostic ZIPs.
2. Compare application diff. Keep `LIVE_INCREMENTAL_ENABLED=false` through ordinary initial rollout. This exercises the unchanged full-history path.
3. Run `python -m compileall -q AlgoAgentXAPI/app` and `cd AlgoAgentXAPI && pytest -q tests/test_retained_strategy_state.py tests/test_live_strategy_history_profile.py tests/test_every_candle_latency_strategy.py tests/test_broker_candle_parity_guard.py`.
4. Validate `docker compose --env-file .env.prod config --quiet` and build `live_legacy_runner_worker`; do not recreate API/DB/Redis unnecessarily.
5. Only after controlled demo review, deploy a verified incremental strategy and enable flags specifically for that strategy.
6. To roll back: disable `LIVE_INCREMENTAL_ENABLED`, restore the previous runner image during a safe window, then verify cursor, signals and open orders. No database schema changes are required.

## Existing safeguards

`LIVE_RUNNER_STALE_ORDER_GUARD_ENABLED` remains **false** by default. This release does not activate it. Other existing broker/idempotency/risk checks remain in the shared execution pipeline.

## Known limitations

- No fully generic automatic incremental rewrite exists for arbitrary Python trading algorithms. The previous OHLCV candle is re-read for revision detection; older historical amendments require separate reconciliation.
- This is in-memory retention only (restart triggers cold replay). A versioned JSON state checkpoint interface could be developed separately after proving parity and transactional recovery.
- No live broker, Oracle VM, real DB-deployed V6.4 or funded-account order integration has been tested here.

## Read-only exact source export (for V6.4)

From the built API container, run:

```bash
docker compose --env-file .env.prod exec -T api python -m app.tools.export_live_strategy_readonly --deployment-id <deployment-uuid> --out /tmp/active_strategy.py
docker cp algoagentx_api:/tmp/active_strategy.py ./active_strategy.py
```

This only reads the Strategy row. Review `active_strategy.py` for private data before sharing; the source ZIP alone cannot prove the exact live V6.4 algorithm or its parameters.
