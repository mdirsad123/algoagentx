# AlgoAgentX Real-Time Alerting — Phase 1

Phase 1 adds independent live-price alert processing with Telegram delivery.

## Services

Run the normal API plus a separate alert worker from the same API image/codebase:

```bash
python -m app.services.alerts.worker
```

Production Docker Compose service example:

```yaml
alert-worker:
  build:
    context: ./api
    dockerfile: Dockerfile.prod
  command: ["python", "-m", "app.services.alerts.worker"]
  env_file: .env.prod
  restart: unless-stopped
  depends_on:
    - postgres
    - redis
```

The worker is independent from FastAPI request handling and consumes live quote events from Redis.

## MT5 live-tick path

For MT5 accounts using the existing AlgoAgentX MT5 Agent:

1. Create an alert and select the relevant MT5 broker account.
2. The Windows/VPS agent asks the API which symbols have active alerts.
3. The agent reads MT5 `symbol_info_tick` about every 250ms while active alerts exist.
4. It pushes quote batches to `/api/v1/mt5-agent/quotes`.
5. API writes latest quote to Redis and publishes `alerts:quotes`.
6. The separate alert worker evaluates state transitions immediately.

This path does **not** wait for 1m/5m candle close, strategy evaluation, backtests, or frontend refresh. For always-on protection, run the MT5 Agent + terminal on an always-on Windows VPS rather than relying on a personal desktop.

## Telegram

Set in API/worker environment:

```env
TELEGRAM_BOT_TOKEN=...
TELEGRAM_DEFAULT_CHAT_ID=
```

A user can save their own chat ID from the Alerts page. `TELEGRAM_DEFAULT_CHAT_ID` is only an optional admin/owner fallback.

The UI's Test Telegram button verifies that the Bot API accepts a message. Telegram does not provide true phone-handset delivery confirmation, so history records API request/response timing only.

## Database

Preferred:

```bash
alembic upgrade head
```

Manual deployments can use:

```text
ALERTING_PHASE1_MANUAL_MIGRATION_20260909.sql
```

## Health

Authenticated endpoint:

```text
GET /api/v1/alerts/health
```

Reports worker, Redis, database, feed health/last tick, and whether Telegram token is configured.
