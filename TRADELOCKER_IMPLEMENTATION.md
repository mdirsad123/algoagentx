# AlgoAgentX TradeLocker integration – October 2026

## What this ZIP contains
- A separate REST-based `TradeLockerAdapter`; no changes to cTrader/MT5 adapter behavior.
- Backend broker factory provider registration; encrypted account fields use existing credential storage.
- Admin provider enable/disable via the existing catalog. Seed SQL at `AlgoAgentXAPI/scripts/tradelocker_provider_seed.sql`, **disabled by default**.
- User Brokers form for environment, email, password and server; Fetch Accounts lists available IDs and accNum values and lets users select a verified pair. Test and Sync Instruments actions remain available.
- Adapter methods for account information, quotes, symbols, rates, orders, positions, market order requests and position close requests. Account state is mapped using TradeLocker /trade/config -> accountDetailsConfig column IDs instead of treating an array as a dictionary. Missing values stay unknown rather than being fabricated.

## Hard limits / deployment gate
This is a **staged integration**, not certified as production-trading ready. No TradeLocker credentials or sandbox account were provided to this runtime, so live account-state response shapes, broker fills, reconciliation, partial exits and copy-trading behaviors have NOT been end-to-end validated. The shared live execution worker and dashboard may need additional reconciliation work before enabling this provider as a primary or copy account. Do not turn on production orders based on source-level tests.

TradeLocker REST success means an order/close REQUEST was accepted, **not necessarily filled**. Broker order ID and position ID differ. Before live enablement, map `/trade/config` columns accurately, reconcile ordersHistory to positions by ID and verify copy-position watchers/partial exits. Account mode in AlgoAgentX remains DEMO while the TradeLocker environment is separately stored as demo/live; do not interpret local `DEMO` as proof that the remote account is simulated. Authentication secrets currently use the project's legacy XOR-derived credential wrapper; migrate to authenticated encryption/KMS before production credentials. Enable TLS/HTTPS on the server before entering secrets.

## Setup
1. Back up the DB. Seed the provider with the SQL file; admin enables it in Admin > Brokers after code review.
2. Rebuild API and web with the dependencies in `pyproject.toml` / `requirements.txt`.
3. Go to user Brokers > Connect Broker > TradeLocker. Enter email, password, exact server and environment, click Fetch Accounts and select the account. The ID and accNum are populated automatically. On Edit, Fetch Accounts can use saved credentials if password is left blank.
4. Click Test then Sync Instruments. Verify XAUUSD and other instruments in the `GET /api/v1/broker-accounts/{id}/symbols` endpoint.
5. Keep `TRADELOCKER_ORDER_EXECUTION_ENABLED=false` and `TRADELOCKER_LIVE_EXECUTION_ENABLED=false` (defaults) until demo end-to-end validations pass. Never enable the latter with real money until copy fan-out, idempotency, reconciliation, SL/TP, partial close and rate-limit checks succeed.
6. For many accounts, request a `tl-developer-api-key` from the official Developer Program; provide it as `TRADELOCKER_DEVELOPER_API_KEY` to the API container.

## Validation matrix (uncompleted until a demo account is supplied)
- [ ] Account auth and token refresh; wrong credentials error safely redacted
- [ ] Account identification, accNum, instrument name/TRADE and INFO routes
- [ ] Price and historic bars parity; per-instrument minimum size and lot step
- [ ] One small demo market buy/sell and accurate fill status
- [ ] Broker SL/TP updates and partial close of a valid position ID
- [ ] Copy trading fanout MT5/cTrader/TradeLocker, account-level limits and deduplication
- [ ] Worker reconnects, rate limits, latency, alarms, idempotency, unmatched position recovery
- [ ] Multi-tenant provider disable blocks placement in all paths; rollback plan

Official docs: https://public-api.tradelocker.com/docs/getting-started

## Delta: simplified account connection
- New server route: `POST /api/v1/broker-accounts/tradelocker/discover` — authenticates ephemerally and returns `[{id, accNum, name}]`, without storing passwords or returning tokens.
- New route: `GET /api/v1/broker-accounts/{uuid}/tradelocker/accounts` — discovers accounts with saved encrypted credentials; user-scoped authorization.
- Account selection is mandatory from the freshly fetched account list; manual guessing is no longer required.
- `/trade/config` accountDetailsConfig maps `/trade/accounts/{id}/state` values to field names, then exposes `balance` and `equity` in the existing connection-result UI. If field names differ or the array size changes, this fails closed instead of mislabeling financial values.
- In multi-account TradeLocker logins, saving an additional account can use the same credentials with a different selected account; this does not create another external TradeLocker login.
- Market quote, alert-worker, execution-worker and live order end-to-end validation have NOT been completed. Do not enable the order safety gates on this source alone.

## Local checks
- Python module syntax check run successfully (`py_compile`).
- Static UI wiring inspected for account discovery, selected ID/accNum and balance/equity rendering.
- Full Next.js build unavailable because `node_modules` are not in the extracted archive; no authenticated external broker session was possible.
