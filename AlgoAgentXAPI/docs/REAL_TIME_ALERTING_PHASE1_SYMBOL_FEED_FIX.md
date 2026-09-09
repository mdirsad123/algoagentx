# AlgoAgentX Phase 1 — Symbol/Feed Diagnostic Update

This update fixes the common state where MT5 Agent heartbeat is online but alert rules still show `Last Price = 0` and no Telegram alert is generated.

## Changes

- Alert feed health is now based on recent live ticks, not heartbeat alone.
- MT5 Agent supports `FETCH_SYMBOLS` and returns the exact broker symbol names visible to MetaTrader 5.
- Broker account `/symbols` now works for MT5 Agent accounts.
- Alerts UI uses a broker-aware symbol dropdown and falls back to Market Master when broker symbols cannot be loaded.
- MT5 Agent logs active alert symbols and a throttled live quote confirmation line.
- Agent version: `0.4.1-alerts-symbols`.

## Required runtime chain

`MT5 Terminal -> AlgoAgentXMT5Agent -> POST /api/v1/mt5-agent/quotes -> Redis -> alert-worker -> Telegram`

The frontend and the Broker CONNECTED badge do not themselves supply live alert prices.
