# AlgoAgentX Copy Trading — Revert + Safe ORM Fix (2026-09-25)

## Why this revision exists

The previous "pre-primary full ORM snapshot" revision changed the working route before the primary order and could fail while reading an expired `StrategyDeployment` attribute. The production traceback showed the failure at the snapshot comprehension (`column.key: getattr(deployment, column.key)`), which invoked SQLAlchemy's expired-attribute loader and raised `MissingGreenlet`.

## What is reverted

The primary broker execution is back to the last working symbol-routing implementation:

`signal -> original _execute_signal_for_account(db, deployment, signal)`

No clone or full ORM snapshot is created before the primary order.

## Narrow fix

Only the optional copy layer was changed:

1. Read copy-routing IDs/settings from the already-loaded ORM `__dict__` without invoking SQLAlchemy descriptors.
2. Execute the primary account through the unchanged original path.
3. After the primary result, rebuild copy deployment/signal scalar contexts using explicit awaited SQL row mappings (`StrategyDeployment.__table__` / `LiveSignal.__table__`) under `no_autoflush`.
4. Resolve the broker-neutral symbol from those plain scalar contexts.
5. Keep each copy target inside its existing SAVEPOINT.
6. Never walk the primary ORM object's columns after broker execution or after a copy SAVEPOINT rollback.
7. Copy failures cannot overwrite the primary signal result.

This retains the working MT5/cTrader order, symbol-normalization, compact idempotency, risk, SL/TP, duplicate-protection, and copy-account execution code.

## Regression coverage

Focused tests passed: 17/17.

A new regression test simulates an ORM deployment object whose attributes cannot be accessed after load. It verifies that:

- primary receives the exact original deployment object,
- copy routing does not touch expired primary ORM attributes,
- copy account execution still receives the selected target account,
- primary EXECUTED status is preserved.

## Deployment

No SQL migration and no frontend rebuild are required.

Rebuild local PROD backend services:

```bash
docker compose --env-file .env.prod up -d --build --force-recreate api live_strategy_worker
```

If your compose shares the API image/code with the other live workers and you prefer a clean restart:

```bash
docker compose --env-file .env.prod up -d --build --force-recreate api live_market_worker live_strategy_worker live_reconcile_worker
```
