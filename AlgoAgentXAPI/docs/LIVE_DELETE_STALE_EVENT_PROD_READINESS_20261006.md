# AlgoAgentX Live Delete / Stale Event Production Readiness Fix

## Root cause fixed
A stopped deployment could be deleted from `strategy_deployments` while one or more candle events for that deployment were still pending in the Redis live-candle stream. The strategy worker correctly resolved the deployment as missing, but the latency tracer then tried to insert `live_execution_traces.deployment_id` for the deleted row. PostgreSQL rejected the trace FK; the stream entry remained pending; XAUTOCLAIM reclaimed it repeatedly; the worker became DEGRADED and could waste CPU/DB resources.

## Fix
- `live_strategy_worker.py`
  - Treats a missing deployment as a terminal stale event.
  - ACKs it.
  - Publishes completion status.
  - Does **not** persist a relational execution trace for an already-deleted deployment.
- `live_latency_trace_service.py`
  - Adds a second defensive FK guard.
  - If a trace's deployment no longer exists, persistence returns `deployment_missing=True` instead of executing an invalid INSERT.
- Added regression test `tests/test_live_trace_deleted_deployment.py`.

No database migration is required.

## Important resource finding
The supplied log's repeated failure is a stale-event retry loop, not an OOM error. That loop can itself increase CPU and PostgreSQL load.

The universal 20,000-candle live warm-up remains enabled. On the supplied strategy code, local synthetic timing showed approximately:
- Trend-Following V1.37 / 20k rows: ~0.44s on this test host.
- Resistance Rejection V3.5 / 20k rows: ~37s on this test host.

Those numbers are not Oracle performance guarantees; they show why V3.5 may cause temporary CPU spikes with a universal 20k history. Keep concurrent live deployments modest on small machines.

## Recommended environment
For a small production/demo stack running API + web + PostgreSQL + Redis + market worker + strategy worker + reconcile worker + position manager + Celery:
- Prefer >= 2 vCPU and >= 4 GB RAM.
- 8 GB RAM is more comfortable when building Docker images and running several strategies.
- For constrained local Docker, use `LIVE_WORKER_CONCURRENCY=2` while testing.
- Production can generally use 4; increase only after observing CPU/latency.

## Required worker flags for this project
Because this project uses copy trading, broker reconciliation, and live partial exits, production `.env.prod` should have:

```env
LIVE_EVENT_PIPELINE_ENABLED=true
LIVE_MARKET_WORKER_ENABLED=true
LIVE_STRATEGY_STREAM_ENABLED=true
LIVE_RECONCILE_WORKER_ENABLED=true
LIVE_POSITION_MANAGER_WORKER_ENABLED=true
LIVE_POSITION_MANAGER_BROKER_SEND_ENABLED=true
CTRADER_PERSISTENT_CONNECTION_ENABLED=true
LIVE_COPY_TRADING_ENABLED=true
LIVE_LATENCY_TRACE_ENABLED=true
```

For demo validation keep:

```env
LIVE_POSITION_MANAGER_DEMO_ONLY=true
```

## Production deploy
Do not overwrite a working Oracle `.env.prod` with a local `.env.prod`; keep your server URLs, OAuth callback URLs, secrets, and broker credentials.

```bash
docker compose --env-file .env.prod -f docker-compose.yml up -d --build
```

Then:

```bash
docker compose --env-file .env.prod -f docker-compose.yml ps
```

Expected live services:
- api: running/healthy
- web: running
- postgres_prod: healthy
- redis: healthy
- live_market_worker: healthy
- live_strategy_worker: healthy
- live_reconcile_worker: healthy
- live_position_manager_worker: healthy (when enabled)
- celery_worker: running if background jobs are used

Check live-worker logs:

```bash
docker compose --env-file .env.prod -f docker-compose.yml logs --tail=150 live_market_worker live_strategy_worker live_reconcile_worker live_position_manager_worker
```

After deployment, old deleted-deployment Redis events may be seen briefly, but the fixed strategy worker should ACK/drop them instead of generating FK errors. Within a worker health TTL the Strategy Worker should return HEALTHY after successful processing.

## First production validation
1. Use DEMO broker mode first.
2. Create one fresh deployment.
3. Confirm Market Worker HEALTHY.
4. Confirm Strategy Worker HEALTHY.
5. Confirm Reconcile Worker HEALTHY.
6. Confirm Position Manager HEALTHY if partial exit is enabled.
7. Refresh candles and run Full Dry Test.
8. Confirm exact strategy class/source hash.
9. Enable Auto Runner.
10. Observe one complete candle -> signal -> order lifecycle before adding the second strategy/copy accounts.
