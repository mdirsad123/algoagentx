# AlgoAgentX Copy Trading — Revert to Stable Safety-Sync Build + cTrader DNS Hardening

Date: 26 Sep 2026

## Why this build exists

The immediately previous MT5 `Invalid stops` experiment changed the MT5 order-protection path. This package intentionally reverts those changes and returns the project to the last copy-trading build where the user confirmed the primary/copy flow and independent open-position protection were working.

Preserved from the stable build:

- Primary execution path unchanged.
- Copy Trading ON/OFF routing.
- Primary-only `Orders Today` / primary Recent Orders UI.
- Separate Copy Trading Orders table.
- Per-account `max_open_positions` protection.
- Account-scoped position reconciliation.
- Account-scoped duplicate/idempotency protection.
- Cross-broker symbol routing (`XAUUSD` / `XAUUSDm`).
- MT5 ticket-based `CLOSE_POSITION` safety fix.
- Existing cTrader persistent event pipeline / market / strategy / reconcile workers.

Reverted:

- MT5 live-price SL/TP rebasing/translation experiment.
- MT5 `order_check()` invalid-stop preflight/retry experiment.
- Extra copy metadata added only for that invalid-stop experiment.

## New narrow fix in this package

The supplied runtime log did not show a strategy-runner code exception. It showed:

`socket.gaierror: [Errno -3] Temporary failure in name resolution`

while a short-lived API request was opening the cTrader Open API WebSocket to load symbols.

The persistent cTrader worker already has reconnect/backoff logic. This package leaves that worker unchanged and only hardens the short-lived cTrader API adapter:

1. Retry transient DNS resolution failure up to three attempts.
2. If symbol loading still hits a transient DNS error, use the last broker-synced `ctrader_symbols_preview` from broker metadata when available.
3. No risk, execution, strategy, worker, Redis, or PostgreSQL flow is changed by this retry.

## Important timing note from the supplied log

The deployment was started at approximately 14:46:10 and the provided log ends around 14:46:36. For an M5 deployment, the next normal candle close would be around 14:50, so the pasted log ends before the next expected candle-close event. The pasted log alone therefore does not prove that the live worker/strategy worker stopped.

## Validation

- Python `compileall`: PASS.
- Focused copy-trading/cTrader/MT5/idempotency/latency regression tests: 25 PASS.
- Dedicated simulated cTrader DNS retry test: PASS (two temporary DNS failures, success on third attempt).

## Deployment

Replace API and restart the Windows MT5 Agent with the reverted package, then rebuild live backend services:

```bash
docker compose --env-file .env.prod up -d --build --force-recreate api live_market_worker live_strategy_worker live_reconcile_worker
```

Check:

```bash
docker compose --env-file .env.prod ps

docker compose --env-file .env.prod logs -f api live_market_worker live_strategy_worker live_reconcile_worker
```

No SQL migration is required.
