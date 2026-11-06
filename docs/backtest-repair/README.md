# AlgoAgentX Backtest / Celery recovery (2026-11-06)

This package is a **source patch**, not a completed production deployment. The live
PostgreSQL, Redis and Docker hosts cannot be accessed from this workspace. Back up
production data before any migration. No market-data or strategy source was edited.

## Corrections in this package

- Prevent the dispatcher from repeatedly enqueueing a valid task just because it
  is waiting behind another multi-hour job. A task whose dispatch is already
  recorded is left in the queue. Orphaned RUNNING tasks are eligible for recovery
  only with a heartbeat older than 120 seconds and no active PG advisory lock.
- Record the initial task publish timestamp at the API submission point.
- Increase configurable worker memory allowance from 768 MiB to 1536 MiB;
  previous observation of ~1.4 GiB RSS made 768 MiB insufficient. Concurrency
  remains 1. This is NOT a cure for WSL host-wide memory exhaustion. With only
  ~3.77 GiB available to all containers, upgrading WSL RAM or reducing other
  workloads may be required before 400K-candle runs reliably complete.

Other partial Codex changes already present in your uploaded project are retained,
including the dedicated backtest worker, outbox, fencing and ordered equity
migration. These require production compatibility tests before adoption.

## Deployment sequence (PowerShell, in project directory)

1. Keep your own existing `.env.prod` and `.env.dev`; secrets are intentionally
   excluded from this distributable. DO NOT overwrite working environment files.
2. Back up PostgreSQL before changing the schema. Check available disk space.
3. `docker compose --env-file .env.prod config --quiet`
4. `docker compose --env-file .env.prod exec api alembic current`
5. `docker compose --env-file .env.prod exec api alembic heads`
6. Ensure no legacy backtest writer is executing before schema migration. Do not
   terminate live-trading workers. If needed, identify one exact Celery task and
   perform targeted cancellation/reconciliation; see diagnostics below.
7. `docker compose --env-file .env.prod --profile backtest build api backtest_worker backtest_dispatcher`
8. Apply the migration from the newly built image (not the stale running API):
   `docker compose --env-file .env.prod run --rm --no-deps api alembic upgrade head`
9. When deployment is safe for your live trading, deploy the three affected services:
   `docker compose --env-file .env.prod --profile backtest up -d --no-deps api backtest_worker backtest_dispatcher`
10. `docker compose --env-file .env.prod --profile backtest ps`
11. `docker logs --tail 100 algoagentx_backtest_worker`
12. `docker logs --tail 100 algoagentx_backtest_dispatcher`
13. Submit one small parity test before any full 400K-candle backtest.

IMPORTANT: This new queue is `backtest`. The old `celery` queue is shared; never
FLUSHDB, FLUSHALL, or purge that queue. Existing messages on the **legacy** default
queue need per-task reconciliation. If the old Celery worker is still running an
old backtest it can continue until gracefully cancelled or completed, even when
new workers are started. Confirm target task ownership before any revoke.

## Inspect old task and queue safely

```powershell
docker exec algoagentx_celery_worker celery -A app.celery_app.celery_app inspect active
docker exec algoagentx_celery_worker celery -A app.celery_app.celery_app inspect reserved
docker exec algoagentx_redis redis-cli LLEN celery
docker exec algoagentx_redis redis-cli LLEN backtest
```

`inspect active` and `reserved` report what the workers see, not necessarily the
whole queue. Revoke does not terminate an already active task. Do not use
`terminate=True` against a shared worker without checking the exact job and
potential unfinished database writes.

## Correct PostgreSQL login

Your production database role is not `postgres`. Compose defaults are
`algoagentx_user` and `algoagentx_db`; use the actual in-container environment:

```powershell
docker exec -it algoagentx_postgres_prod sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
```

View active and orphaned jobs with `AlgoAgentXAPI/scripts/backtest_ops/inspect_jobs.sql`.
Use `cancel_queued_job.sql` only after replacing its placeholder with the correct
job UUID. It cancels one **unstarted** durable job, not a running process or Redis
message. A confirmed active job requires coordinated worker cancellation.

## Important limitations

- Source-only testing cannot prove native replay parity, DB migration execution,
  Redis crash recovery or production memory usage.
- On this analysis machine, Celery is not installed and no PostgreSQL/Redis
  containers are reachable; tests that need those environments were not run.
- Full native engine optimization and frontend cancel/retry controls are not
  implemented in this targeted patch; the uploaded Codex changes are partial.
- Never mistake elapsed time for a dead job. Many 400K-candle tests take many
  minutes and heartbeat/ownership should be checked before cancellation.
