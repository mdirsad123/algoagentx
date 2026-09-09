# AlgoAgentX Phase 1 — End-to-End Alert Test Guide

## Important architecture

For MT5 Phase 1 the required runtime path is:

`MT5 Terminal -> AlgoAgentXMT5Agent -> API quote endpoint -> Redis -> alert-worker -> Telegram`

The web page can be closed. The API and alert-worker do not read MT5 prices directly from a Windows terminal; the Agent is the bridge.

## What "Broker Connected" means

A connected broker/Agent heartbeat proves that AlgoAgentX can see the MT5 Agent and terminal/account. It does not by itself prove that an alert quote has reached Redis. The alert health card is now driven by recent ticks.

## Test order

1. Start Redis/Postgres/API.
2. Start `python -m app.services.alerts.worker` for local dev.
3. Start MetaTrader 5 and login to the intended broker account.
4. Run the updated Agent `0.4.1-alerts-symbols` with the Agent Token generated for the same AlgoAgentX broker account selected in the alert.
5. On Alerts, choose that MT5 broker account.
6. Wait for broker symbols to load and select the exact broker symbol, for example `XAUUSD.x`.
7. Create an ACTIVE alert.
8. Confirm the Agent console shows:
   - `Active alert symbols: [...]`
   - `Alert quotes sent | accepted=...`
9. Confirm the Alerts table `Last Price` changes from `0/—` to the live price and Market Feed becomes `Connected`.
10. For Crossing Up, the alert requires a real transition `previous < target <= current`. If price was already above the target when the alert was armed, it will not immediately fire.
11. After the crossing, confirm Telegram and Alert History.

## Diagnostics

### Ask the API which alert symbols this Agent should stream

```bat
curl.exe -H "Authorization: Bearer YOUR_AGENT_TOKEN" http://localhost:8000/api/v1/mt5-agent/alert-symbols
```

Expected: the active alert symbol is returned. If the list is empty, check that the alert is ACTIVE and uses the same broker account that the Agent Token belongs to.

### Check that quotes reached Redis

Development container example:

```bat
docker exec algoagentx_redis_dev redis-cli --scan --pattern "latest_price:MT5:*"
```

Production container example:

```bat
docker exec algoagentx_redis redis-cli --scan --pattern "latest_price:MT5:*"
```

At least one key should exist after the Agent starts streaming an active alert symbol.

## Crossing test example

If live XAUUSD.x is around `4414.80`, create:

- Symbol: `XAUUSD.x`
- Condition: Crossing Up
- Target: `4415.00`
- Frequency: Trigger Once
- Telegram: enabled

It triggers only when the incoming tick sequence actually moves from below 4415 to 4415 or above.
