# Docker worker startup/healthcheck fix — 07 Oct 2026

## Root causes

1. `Dockerfile.prod` defines an HTTP `GET /health` HEALTHCHECK for the API image. Worker services use the same image but do not run an HTTP server. Without a Compose override, Docker therefore reports `alert_worker`, `celery_worker`, and `live_history_worker` as unhealthy even while their worker process is alive.
2. `live_reconcile_worker` used `depends_on: live_market_worker: condition: service_healthy`. During a slow market-worker startup, Compose could abort the whole `up` command with `dependency failed to start`, even though `live_market_worker` later became healthy.
3. The market-worker Redis-heartbeat healthcheck had a short startup grace period for broker-feed initialization.

## Changes

- `alert_worker`: disable inherited API HTTP healthcheck.
- `live_history_worker`: replace HTTP check with Celery node ping.
- `celery_worker`: replace HTTP check with Celery node ping.
- `live_market_worker`: startup grace 120 seconds, 10 retries.
- strategy/reconcile/position workers: larger startup grace.
- `live_reconcile_worker`: market dependency changed from `service_healthy` to `service_started`. It has its own Redis-heartbeat healthcheck and can safely start while market feeds are initializing.

## Recommended rebuild

Normal production live stack:

```bash
docker compose --env-file .env.prod -f docker-compose.yml up -d --build
```

If the optional general Celery worker is also used:

```bash
docker compose --env-file .env.prod -f docker-compose.yml --profile worker up -d --build
```

Then inspect:

```bash
docker compose --env-file .env.prod -f docker-compose.yml ps
```

The dedicated `live_history_worker` is not optional and is started without a profile.

If an old `algoagentx_celery_worker` container remains from a previous build while the `worker` profile is not enabled, either rebuild it with `--profile worker` or stop/remove it to avoid a misleading stale unhealthy status and unnecessary RAM usage.
