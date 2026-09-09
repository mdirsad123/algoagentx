# AlgoAgentX Phase 1 Alerting — Fix 1

## PostgreSQL `FOR UPDATE` outer-join fix

The alert worker uses row locks so multiple workers cannot claim the same alert or Telegram delivery. The alert ORM models use joined relationships, so a plain `FOR UPDATE` query could be expanded into `LEFT OUTER JOIN` clauses. PostgreSQL rejects locking the nullable side of an outer join with:

`FOR UPDATE cannot be applied to the nullable side of an outer join`

The Phase 1 fix now:

- suppresses relationship eager loading for row-lock queries using `noload("*")`, and
- scopes row locks to the base table with `FOR UPDATE OF <base_table> SKIP LOCKED`.

The fix is applied to both Telegram delivery claims and price-alert evaluation locks.

## Development Redis

If the API and alert worker are run directly on Windows, Redis must be reachable from that Windows process. A separate dev Redis can be mapped to host port `6380`.

Use in the API `.env` used by the local Python process:

```env
REDIS_URL=redis://127.0.0.1:6380/0
REDIS_HOST=127.0.0.1
REDIS_PORT=6380
REDIS_DB=0
```

Then start the alert worker from the API project directory:

```bash
python -m app.services.alerts.worker
```

## Production worker

Production Docker Compose should include a dedicated service that runs:

```bash
python -m app.services.alerts.worker
```

using the same API image, PostgreSQL database, Redis service, and Telegram environment variables as the API.
