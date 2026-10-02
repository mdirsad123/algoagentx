# AlgoAgentX live execution fix — 25 Sep 2026

## Root cause confirmed from Docker logs

The failing `live_orders` insert used a 149-character copy-trading order identity as both `client_order_id` and `idempotency_key` while `live_orders.idempotency_key` is `VARCHAR(128)`. PostgreSQL therefore raised `StringDataRightTruncationError` during `await db.flush()` after strategy/risk processing and before the order transaction could commit.

The follow-up `This Session's transaction has been rolled back...` message was secondary: the MT5/legacy auto-runner error handler attempted to use the same failed SQLAlchemy session without calling `rollback()` first.

## Fixes

1. Generic MT5/Upstox order identity is now deterministic, account-scoped, retry-stable and ~47 characters.
2. Same candle + same account + same strategy/action produces the same id across retries, even if a failed signal row is recreated.
3. Different copy accounts produce different ids, preserving multi-account idempotency.
4. Strategy runner now always rolls back a failed SQLAlchemy transaction before writing `RUNNER_ERROR` or retrying.
5. Primary account DB exceptions are no longer swallowed inside the copy router; they propagate to the runner rollback boundary.
6. Each copy target runs inside its own SQLAlchemy SAVEPOINT and uses a scalar copy of the signal, so one copy failure cannot poison primary/sibling execution state.
7. MT5 Agent payload now keeps `client_order_id` and `idempotency_key` semantically separate.
8. An MT5 agent command queued successfully is stored as `PLACED` rather than falsely marked `FILLED`; the agent callback can later update it to `FILLED`.

## Database

No schema migration is required for this fix. Keeping `idempotency_key VARCHAR(128)` is intentional; IDs are now bounded in code instead of enlarging broker-facing identity fields indefinitely.

## Focused validation

- Python compileall: passed.
- 7 focused tests passed covering compact/retry-stable account-scoped identities, copy-disabled primary regression, cTrader identity, Redis order claim and latency tracing.
- A broader local test requiring `asyncpg` could not be collected in the artifact environment because that optional runtime dependency is not installed there; the Docker runtime already contains it.

## Rebuild

From the project root:

```bash
docker compose --env-file .env.prod up -d --build --force-recreate api live_market_worker live_strategy_worker live_reconcile_worker
```

Then inspect:

```bash
docker compose --env-file .env.prod logs -f api live_strategy_worker
```

First validate with Copy Trading OFF. Wait for an automatic M5 candle; do not press Run Once. Expected: signal -> order preview/risk -> `live_orders` insert -> MT5 Agent command -> `PLACED`, then broker callback/sync -> `FILLED`.
