# AlgoAgentX Live Trading Foundation V1

## Added files

- `app/db/models/live_trading.py`
- `app/schemas/live_trading.py`
- `app/api/v1/live_common.py`
- `app/api/v1/broker_accounts.py`
- `app/api/v1/live_deployments.py`
- `app/api/v1/live_signals.py`
- `app/api/v1/live_orders.py`
- `app/api/v1/live_positions.py`
- `app/api/v1/live_logs.py`
- `database/migrations/live_trading_foundation.sql`

## Modified files

- `app/db/models/__init__.py`
- `app/api/v1/router.py`

## Phase 1 behavior

- Adds broker accounts, strategy deployments, live signals, live orders, live positions, live logs, and live equity points.
- Blocks LIVE mode in this phase. PAPER and DEMO are allowed.
- Only PUBLIC/published strategies can be deployed.
- Users can access only their own live trading objects.
- Admin users can list all live trading objects.
- PAPER deployments can start without broker account.
- DEMO deployments require a broker account when starting.
- MT5 is only prepared as broker account metadata. No real MT5 connection is made in this phase.

## Manual migration

Run this SQL in DBeaver:

`database/migrations/live_trading_foundation.sql`

## Main verification endpoints

- `GET /api/v1/broker-accounts`
- `POST /api/v1/broker-accounts`
- `GET /api/v1/live/deployments`
- `POST /api/v1/live/deployments`
- `POST /api/v1/live/deployments/{id}/start`
- `POST /api/v1/live/deployments/{id}/pause`
- `POST /api/v1/live/deployments/{id}/stop`
- `POST /api/v1/live/signals/manual`
- `GET /api/v1/live/orders?deployment_id={id}`
- `GET /api/v1/live/positions?deployment_id={id}`
- `GET /api/v1/live/positions/open`
- `GET /api/v1/live/logs?deployment_id={id}`
