# Live runner +5s schedule and broker sync fix

## Runner timing
For M5:
- 11:55 candle closes at 12:00:00
- first strategy attempt is 12:00:05
- if the closed candle is missing, retry at 12:00:10, :15, :20 ... up to 10 broker refresh attempts
- once the candle is processed, the next scheduled run is the next exact timeframe close +5 seconds
- `next_run_at` is persisted and kept in the future
- duplicate orders remain protected by the per-deployment PostgreSQL advisory transaction lock plus existing candle/signal idempotency

## UI
- Last Run shows seconds
- Next Scheduled Run shows seconds
- Last Processed Candle stays minute-level because it identifies the broker candle

## Broker sync production error
The Docker log showed a cTrader websocket timeout followed by SQLAlchemy MissingGreenlet.
The rollback expired the ORM deployment object, and the exception path accessed `deployment.id`
again, causing an implicit async DB load outside the greenlet context.

The sync path now caches UUIDs before broker calls/rollback, treats broker timeouts as transient,
keeps auto-sync enabled, and retries on the next sync cycle without the MissingGreenlet cascade.

## Docker
Dockerfile.prod now uses Poetry 2.1.2, matching the checked-in poetry.lock generator.
