# AlgoAgentX Live-Trading Parity Hardening — 06 Oct 2026

## Scope

This patch hardens live strategy execution after the 300-candle warm-up and dynamic-strategy source-mismatch investigation.

## Confirmed findings from deployment 685dd1c6-7662-4e56-8942-639141ec15c0

- The deployed executable source is the correct `XAUUSD5MTrendBreakoutV137` Dynamic DB strategy.
- The old export was evaluated on only ~300 M5 candles. Important V1.37 higher-timeframe fields were `null`, including 4H momentum, daily momentum, and 1H ATR-ratio diagnostics.
- Its runtime snapshot had Exit On Opposite Signal enabled, while the V1.37 research/live contract requires it disabled.
- The supplied generic `market_data` candles are not identical to the cTrader live trendbars, so exact backtest/live parity must use the same broker candle source.

## Implemented

### Strategy-specific history requirement

- `XAUUSD5MTrendBreakoutV137`: 20,000 closed M5 broker candles.
- `XAUUSD5MSupplyDemandRejectionV35CandidateA`: 1,000 closed M5 broker candles.
- Unknown/future strategy default: 5,000 closed candles.
- Per-strategy override: set `live_history_bars` or `required_history_bars` in strategy parameters.
- Hard platform cap: 100,000 bars (configurable with `LIVE_STRATEGY_HISTORY_MAX_BARS`).
- Strategy classes can also declare `LIVE_HISTORY_BARS` / `REQUIRED_HISTORY_BARS`.

### Broker-safe large history

Large warm-up is paginated rather than asking a broker for 100,000 bars in one call:

- cTrader: backwards trendbar pagination (2,000-bar pages).
- MT5 Agent: `start_pos` pagination via the desktop agent.
- Local MT5 adapter: `copy_rates_from_pos` pagination.

History is written in batched PostgreSQL upserts and de-duplicated by deployment/candle timestamp.

### Hard execution gate

DEMO/LIVE strategy execution now refuses to trade if:

- exact strategy source/class cannot resolve;
- required closed-candle history is not present;
- the strategy's live runtime contract is violated.

No signal/order is sent while any of these conditions are unresolved.

### V1.37 runtime contract

The live runner validates:

- Entry Mode = Next Candle Open
- Exit On Opposite Signal = OFF
- Max Open Positions = 1
- SL Mode = Strategy Suggested
- RR = 2.0
- Break Even = OFF
- Trailing = OFF
- Partial Exit = ON
- Partial Exit At = 1.70R
- Partial Exit Percent = 90%

Admin Save/Create/Duplicate flows now re-apply known/code-declared live runtime contracts to the strategy default runtime config and its default runtime preset so a stale default preset cannot silently re-enable incompatible behavior.

### Visibility / audit

Readiness and compatibility now expose/fail on:

- resolved strategy class;
- required history bars;
- stored history bars;
- runtime-contract violations.

New engine signal payloads include:

- `required_history_bars`
- `loaded_history_bars`
- `history_ready`

## Deployment procedure

1. Stop old Trend V1.37 and V3.5 deployments before replacing production code.
2. Replace project files.
3. Rebuild production:

```bash
docker compose --env-file .env.prod -f docker-compose.yml up -d --build
```

4. In Admin open Trend-Following Breakout V1.37 and click Save once. Then Verify Code -> Sandbox -> Publish. This synchronizes the V1.37 runtime preset to its live contract.
5. For V3.5 do Save -> Verify -> Sandbox -> Publish after confirming its correct source is present.
6. Create fresh live deployments. Fresh deployment IDs are recommended because the old V3.5 deployment contains invalid historical signals from the prior duplicated V1.37 source.
7. Run Compatibility / Readiness before enabling Auto Trade.
8. Trend V1.37 should report `stored_history_bars >= 20000`; V3.5 should report `>= 1000`.
9. Confirm the first new signal payload has the correct `resolved_strategy_class`, source hash, and history fields.

## Validation completed in this patch

- Python compile checks passed for every modified backend/MT5-agent module.
- 33 combined targeted regression tests passed, including 4 strategy-history/runtime-profile tests, plus dynamic strategy registry, copy-trading isolation, symbol resolution, partial-exit config, and partial-exit management coverage.
- Exact V1.37 class was smoke-tested on 20,000 synthetic M5 bars successfully.
- Exact V3.5 class was smoke-tested on 1,000 synthetic M5 bars successfully.

## Important parity note

The supplied October historical `market_data` and cTrader live trendbars are not price-identical. For the 37 old V1.37 live signal timestamps, the historical close and cTrader source-row close differed on every timestamp (mean absolute difference about 2.25 XAUUSD points; max about 20.48). This is a data-feed difference, not cross-deployment signal leakage. For exact signal-by-signal validation, replay the same cTrader-derived candle history that live execution used.
