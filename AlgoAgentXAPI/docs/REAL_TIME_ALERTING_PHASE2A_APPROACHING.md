# AlgoAgentX Real-Time Alerting — Phase 2A Approaching Level / Zone

## What Phase 2A adds

Phase 2A adds one optional pre-warning before the existing Phase 1 trigger:

- Crossing Up: warn at `target - approach_distance`.
- Crossing Down: warn at `target + approach_distance`.
- Entering Zone from below: warn at `zone_low - approach_distance`.
- Entering Zone from above: warn at `zone_high + approach_distance`.

The Entering Zone logic is deliberately **two-way and automatic**. You do not need separate Support/Resistance alert types.

Example resistance:

```text
Current 4390
Zone 4400-4402
Approach distance 3

4397 -> approaching-zone Telegram
4400.x -> existing entering-zone Telegram
```

Example support:

```text
Current 4400
Zone 4380-4382
Approach distance 3

4385 -> approaching-zone Telegram
4382.x -> existing entering-zone Telegram
```

The support example uses the upper zone boundary because price is approaching from above: `4382 + 3 = 4385`. If you instead define a single support target at `4380` with Crossing Down, the approach threshold is `4380 + 3 = 4383`.

## Architecture

No new service is added:

```text
MT5 + AlgoAgentXMT5Agent
        -> FastAPI quote endpoint
        -> Redis quote bus
        -> existing alert-worker
        -> approach evaluator + main evaluator
        -> PostgreSQL alert_events
        -> existing Telegram delivery/retry
```

Phase 2A uses the same per-tick alert-row fetch/lock already used by Phase 1 and adds no additional PostgreSQL query per tick.

## Database migration

Preferred:

```bash
alembic upgrade head
```

New revision:

```text
20260910_alert_approach_phase2a
```

Manual fallback, only if your deployment process requires it:

```text
ALERTING_PHASE2A_MANUAL_MIGRATION_20260910.sql
```

Existing Phase 1 rows default to `approach_enabled = false`.

## New price_alerts fields

```text
approach_enabled
approach_distance
approach_state
last_approach_triggered_at
approach_trigger_count
```

## State / duplicate prevention

Approach state is separate from the Phase 1 main alert state.

```text
WAITING -> APPROACH_SENT
```

For recurring alerts, the approach warning can return to `WAITING` only after:

1. the configured cooldown has elapsed, and
2. price has moved sufficiently away using the existing `rearm_distance`.

This prevents repeated Telegram messages while price oscillates inside the approach band.

For `Trigger Once`, no approach rearm occurs after the main alert completes.

## Telegram

Approach events reuse the existing Telegram delivery queue, retry behavior, and audit timestamps.

Example:

```text
🟡 AlgoAgentX Approaching Zone

XAUUSDm is approaching your configured zone from below

Zone: 4400.00 - 4402.00
Current: 4397.25
Distance to Zone: 2.75
...
```

The actual Phase 1 zone-entry notification remains a separate event.

## Alert History

New event types:

```text
APPROACHING_TARGET
APPROACHING_ZONE
```

Both approach and main events are retained independently with the existing latency fields.

## Feed health polish

When the user has zero active alerts, the health endpoint now returns:

```text
market_feed = idle
```

instead of warning that the market feed is disconnected simply because there are no symbols to stream.

When at least one active alert exists, a stale/no-tick feed is still reported as degraded/disconnected.

## Local testing

### Resistance zone from below

```text
Zone: 4400-4402
Approach: 3
Price path: 4395 -> 4396.9 -> 4397.1 -> 4399 -> 4400.2
```

Expected:

```text
~4397 -> APPROACHING_ZONE
4400.2 -> ENTERING_ZONE
```

### Support zone from above

```text
Zone: 4380-4382
Approach: 3
Price path: 4390 -> 4386 -> 4385.1 -> 4384.9 -> 4382.0
```

Expected:

```text
~4385 -> APPROACHING_ZONE
4382.0 -> ENTERING_ZONE
```

### Single support level with Crossing Down

```text
Target: 4380
Approach: 3
```

Expected approach threshold:

```text
4383
```

## Production Docker deployment

No new Compose service is needed. Continue using the existing Phase 1 services:

```text
postgres_prod
redis
api
alert_worker
web
```

After replacing APP/API source:

```bash
docker compose --env-file .env.prod -f docker-compose.yml down
docker compose --env-file .env.prod -f docker-compose.yml up -d --build postgres_prod redis api
docker compose --env-file .env.prod -f docker-compose.yml exec api alembic upgrade head
docker compose --env-file .env.prod -f docker-compose.yml up -d --build alert_worker web
```

Do not use `down -v` for a normal deployment.

## Rollback

Recommended application rollback:

1. Disable any newly created approach alerts or set `approach_enabled=false`.
2. Redeploy the prior Phase 1 APP/API images/source.
3. It is safe to leave the additive Phase 2A columns in PostgreSQL.

Only run `alembic downgrade` if you explicitly need schema rollback and have confirmed no newer migration depends on Phase 2A.

## Known limits

- One approach distance per alert.
- Absolute price distance only.
- No approach behavior for Leaving Zone in Phase 2A.
- No sessions, indicators, strategy confirmation, WhatsApp, or browser push.
- Telegram API acceptance is recorded; handset delivery confirmation is not available.
