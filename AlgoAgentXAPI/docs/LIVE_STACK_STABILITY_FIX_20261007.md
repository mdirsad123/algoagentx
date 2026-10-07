# AlgoAgentX Live Stack Stability Fix — 07 Oct 2026

## What the logs proved

The dedicated history worker was successful. Trend V1.37 reached 20,002/20,000 bars and Resistance Rejection V3.5 reached 2,001/2,000 bars. The later outage was not a missing-history problem.

The live stack then suffered host/container resource pressure: Gunicorn workers were repeatedly SIGKILLed, Redis/PostgreSQL service-name DNS lookups intermittently failed, Redis operations timed out, cTrader persistent sessions disconnected/retried, and Redis heartbeat keys expired. This made the UI show workers OFFLINE even when some container processes were still alive.

The `missed heartbeat from celery@...` messages in `live_history_worker` were about the old general Celery worker, not the dedicated `live_history@...` worker.

## Changes in this build

- API defaults to one Gunicorn worker (`WEB_CONCURRENCY=1`) and recycles workers after a bounded request count.
- Live event concurrency reduced from 8 to 2 for the default low-resource profile.
- SQLAlchemy pools bounded to 3 + 2 overflow per process; DB connect/pool timeouts reduced so a transient Docker DNS problem fails fast instead of hanging browser requests for ~60-90 seconds.
- API Redis manager now reconnects automatically if API startup happened during a transient Redis/DNS outage.
- Market/Strategy/Reconcile/Position heartbeat loops survive transient Redis errors instead of dying permanently.
- Strategy worker retrieves background task exceptions so Redis failures do not produce `Task exception was never retrieved` noise.
- Reconcile worker survives one failed DB/network cycle and retries on the next interval.
- Position Manager survives transient Redis pub/sub errors and clears stale DEGRADED state after a successful recovery cycle.
- Docker worker healthchecks are process-liveness checks instead of Redis heartbeat / Celery inspect checks. Redis/app readiness remains visible in Pipeline Health.
- Dedicated history worker: concurrency 1, no gossip/mingle, one task per child so memory is returned to the OS after a large warm-up.
- History warm-up uses 5,000-bar broker-session chunks while cTrader still requests 1,000 trendbars per wire page. This reduces 20k warm-up connection churn from about 20 broker sessions to about 4.
- Summary polling no longer refreshes the broker by default.
- Live deployment page no longer automatically opens a cTrader broker refresh when mounted.
- Runtime UI polling reduced from 5 seconds to 10 seconds; live execution remains event-driven and unaffected.
- V1.37 still requires 20,000 M5 history bars. Resistance Rejection V3.5 still requires 2,000.

## One-time local cleanup before rebuild

If testing PROD only, stop the old optional Celery worker and DEV database/Redis to release RAM:

```powershell
docker stop algoagentx_celery_worker algoagentx_redis_dev algoagentx_postgres_dev
```

Do not delete the DEV database volume if you need its data later.

## Rebuild

```powershell
docker compose --env-file .env.prod -f docker-compose.yml down

docker compose --env-file .env.prod -f docker-compose.yml up -d --build
```

Check status:

```powershell
docker compose --env-file .env.prod -f docker-compose.yml ps
```

Check resource use:

```powershell
docker stats --no-stream
```

Core logs:

```powershell
docker compose --env-file .env.prod -f docker-compose.yml logs --tail=200 api live_market_worker live_strategy_worker live_reconcile_worker live_position_manager_worker live_history_worker redis postgres_prod
```

## Expected stable state

- API / Web / PostgreSQL / Redis: healthy.
- Worker containers: healthy by process liveness.
- Pipeline Health: Market, Strategy, Reconcile, Position Manager become HEALTHY after Redis heartbeats recover.
- History worker may be idle after warm-up; that is normal.
- No repeated `SIGKILL! Perhaps out of memory?` messages.
- No persistent `Temporary failure in name resolution` for `redis` / `postgres_prod`.
- No repeated `Task exception was never retrieved` from the live strategy worker.

## Resource note

The code is now conservative, but the complete PROD stack still needs real RAM. For local Docker Desktop/WSL, allocate at least 6 GB to Docker/WSL if possible. For Oracle, 4 GB is a practical minimum and 8 GB is preferable when API, PostgreSQL, Redis, web, history, market, strategy, reconcile, position-manager and background jobs all run on one VM.
