# AlgoAgentX Copy Trading — Cross-Broker Symbol Resolution Fix (2026-09-25)

## Problem
A primary MT5 deployment can use an exact broker symbol such as `XAUUSDm`, while the selected cTrader copy account exposes `XAUUSD`. The copy router previously propagated the primary broker alias into the copy account, causing cTrader to reject the order with `cTrader symbol XAUUSDm was not found`.

The reverse direction has the same risk: a cTrader primary can emit `XAUUSD`, while an MT5 copy terminal may require `XAUUSDm`, `XAUUSDc`, `XAUUSD.pro`, etc.

## Correct architecture
Strategy generation remains single-source. The primary account keeps its existing exact deployment symbol. Copy targets receive a broker-neutral canonical instrument, then each target adapter resolves that canonical instrument to the exact symbol exposed by that account.

```
Strategy signal once
    -> primary account: preserve deployment's exact broker symbol
    -> copy account A: canonical symbol -> target broker resolver -> exact symbol
    -> copy account B: canonical symbol -> target broker resolver -> exact symbol
```

### MT5 primary -> cTrader copy
`XAUUSDm` -> canonical `XAUUSD` -> cTrader `XAUUSD`

### cTrader primary -> MT5 copy
`XAUUSD` -> canonical `XAUUSD` -> MT5 terminal resolver -> `XAUUSDm` (or another broker-specific suffix)

## Changes
- Added Market Master-first canonical copy-symbol resolution in `execution_engine.py`.
- Copy targets no longer inherit the primary account's `broker_symbol`, even when both targets are the same provider.
- cTrader symbol lookup now supports safe alias matching (`XAUUSDm` -> `XAUUSD`) while preferring exact matches.
- cTrader order result records the actual resolved symbol and preserves the requested symbol separately.
- MT5 Windows Agent resolves canonical symbols against the actual terminal symbol list at the last mile with no additional API request before order submission.
- MT5 Agent candle/quote paths also use the same resolver where appropriate.
- Primary account execution path is unchanged.
- No database migration is required.

## Validation
Focused regression tests cover:
- canonical `XAUUSDm` -> `XAUUSD`
- cTrader alias resolution and exact-match priority
- MT5 `XAUUSD` -> `XAUUSDm`
- alternate MT5 suffix `XAUUSD.c`
- copy-trading primary-path regression
- generic/cTrader idempotency
- order dedupe and latency tracing

12 focused tests pass.

## Deployment
Replace `AlgoAgentXAPI` with the updated API package and rebuild API/live workers. Because the MT5 Windows Agent code changed, restart the Python agent. If using a packaged EXE, rebuild/redeploy the EXE before testing cTrader-primary -> MT5-copy routing.
