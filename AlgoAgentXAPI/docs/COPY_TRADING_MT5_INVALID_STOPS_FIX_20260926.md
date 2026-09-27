# AlgoAgentX – MT5 Copy Trading Invalid Stops Fix

Date: 26 Sep 2026

## Problem

When cTrader was the primary deployment and MT5 was a copy target, MT5 sometimes returned:

```text
Invalid stops
```

The same strategy SL/TP could work on cTrader while MT5 intermittently rejected it.

## Root cause

The Windows MT5 Agent was sending a MARKET order with the source strategy/candle price as `price`, even though the real MT5 executable price had already moved. It also forwarded the source broker's absolute SL/TP directly to MT5.

For cross-broker copying this can be unsafe because cTrader and MT5 may have a small quote offset and the order reaches MT5 after the source candle close. A stop that was valid around the cTrader reference price can therefore be on the wrong side of MT5 Bid/Ask or inside the MT5 broker's minimum stop distance.

## Fix

### Primary MT5 behavior

Primary MT5 orders keep the strategy's absolute SL/TP. The MARKET request now uses the current MT5 terminal Bid/Ask and validates protection against the live market before `order_send`.

### Cross-broker copy -> MT5

The copy router now sends two pieces of metadata to the MT5 Agent:

```text
is_copy_execution
source_broker_code
```

For a copy order whose source broker is not MT5, the Agent preserves the strategy's SL/TP distances by translating both levels by the target MT5 price offset:

```text
source reference price = 4280.00
MT5 live SELL price    = 4281.00
source SL              = 4282.00
source TP              = 4276.00

price offset = +1.00

MT5 SL = 4283.00
MT5 TP = 4277.00
```

This preserves the original stop distance and reward distance while aligning the protection with the target broker's current price.

### Broker stop-level validation

Before sending, the Agent reads MT5 `symbol_info()` values including:

```text
digits
point
trade_stops_level
```

Protection is normalized to broker digits and validated against the actual trigger side:

```text
BUY  -> SL/TP checked from Bid
SELL -> SL/TP checked from Ask
```

If the strategy distance is genuinely smaller than the target broker's allowed minimum, the Agent fails locally with a detailed message instead of sending an order that the broker will reject as `Invalid stops`.

### Preflight and race retry

If supported by the terminal, `order_check()` is run before `order_send()` specifically to catch invalid stops.

Gold can move between preflight and send. If a cross-broker copy still receives MT5 `TRADE_RETCODE_INVALID_STOPS`, the Agent refreshes the tick, rebuilds the translated protection once, and retries once. An invalid-stops response does not execute a trade, so this retry does not create a duplicate position.

### Result persistence

When MT5 confirms the order, AlgoAgentX updates the local `live_order` with the actual broker request symbol, volume, SL and TP so the UI reflects the protection that was really sent to MT5.

## Files changed

```text
AlgoAgentXAPI/app/services/brokers/base.py
AlgoAgentXAPI/app/services/brokers/mt5_agent.py
AlgoAgentXAPI/app/services/live/execution_engine.py
AlgoAgentXAPI/app/api/v1/mt5_agent.py
AlgoAgentXAPI/AlgoAgentXMT5Agent/mt5_client.py
AlgoAgentXAPI/tests/test_mt5_copy_close_and_symbol.py
```

The bundled API download package `storage/downloads/AlgoAgentXMT5Agent.zip` is also rebuilt from the updated Windows Agent.

## Database / frontend

No SQL migration is required.

No frontend change is required.

## Validation

Focused tests cover:

- primary MT5 absolute SL/TP preservation
- current MT5 market price usage
- cTrader -> MT5 copy SL/TP rebasing
- broker minimum stop-level local blocking
- one retry after a fast-market `Invalid stops`
- existing copy symbol / primary regression / position isolation / idempotency tests

