# AlgoAgentX Copy Trading — Cross-Broker Symbol Routing Final Fix

Date: 25 Sep 2026

## Root causes fixed

1. `NameError: resolved_broker_symbol is not defined` in `_execute_demo_entry`.
   - The previous symbol-normalization patch wrote `resolved_broker_symbol` into the MT5 `LiveOrder` before assigning it.
   - The broker call could already be queued/sent, then local execution crashed before the order record/position state was completed.

2. Persistent cTrader worker only performed exact symbol-name matching.
   - A primary MT5 deployment can carry `XAUUSDm` while cTrader exposes `XAUUSD`.
   - The fallback cTrader adapter already supported alias/root matching, but the persistent event/order worker did not, so the fast cTrader path could reject `XAUUSDm` as not found.

## Corrected routing

Signal/strategy symbol -> canonical copy symbol -> target broker exact symbol

Examples:
- MT5 primary `XAUUSDm` -> canonical `XAUUSD` -> cTrader copy `XAUUSD`
- cTrader primary `XAUUSD` -> canonical `XAUUSD` -> MT5 copy -> Windows MT5 Agent resolves `XAUUSDm`, `XAUUSD.c`, etc.

## Code changes

- `app/services/live/execution_engine.py`
  - defines the resolved broker symbol immediately after broker result is returned;
  - persists/open-positions using the exact resolved symbol when available;
  - no use-before-assignment path remains.

- `app/services/brokers/symbol_utils.py`
  - new dependency-free shared symbol matcher;
  - exact matches win;
  - common FX/metals/crypto broker suffixes are matched by six-letter pair root.

- `app/services/brokers/ctrader.py`
  - cTrader adapter now delegates to the shared matcher.

- `app/services/live/live_market_worker.py`
  - persistent cTrader market/order worker now uses the same shared matcher;
  - both cached metadata and fresh Open API symbol lists support alias resolution;
  - gateway response returns requested symbol + exact resolved cTrader symbol.

## Database

No SQL migration is required for this fix.

## Validation

- Python compileall: passed.
- Focused regression suite: 16 tests passed.
- Tests cover MT5 suffix -> cTrader clean symbol, exact-match priority, MT5 terminal suffix resolution, primary-path regression, idempotency, Redis dedupe, and latency tracing.

The broader worker test set could not be collected in this sandbox because the environment does not have the `asyncpg` package installed; this is an environment dependency limitation, not a project test failure.
