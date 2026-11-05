# TradeLocker copy reliability review — November 5, 2026

## Disposition

Offline repair checks pass within the tested scope. **Not production-validated and not deployed.**
No orders, credential changes, migrations, service restarts, database recovery, or strategy changes were performed in this review.

## Evidence and attribution

- Retained audit: 14,664 successful `/trade/quotes` requests and three quote HTTP 429 responses in the alert-worker sample. Separate services also authenticated repeatedly. The audit records multiple selected accounts with the same credential fingerprint. This supports shared request-pressure attribution; it does not identify every historical reconciliation endpoint that returned 429.
- The unrestricted regression collection blocker is `observed_broker_gap_eligible`, imported by `test_demo_observed_long_gap_20261028.py` but missing from `app/services/live/candle_catchup.py`. Both conditions were verified at Git HEAD: this repair did not introduce it. No replacement trading/recovery behavior was invented to make that test pass.
- Deployment-page TypeScript callback used `.bind` at HEAD. Replacing it with a typed closure removes that diagnostic. Eight diagnostics remain in admin/user live-approval, backtest-report and reports pages; those pages were not edited by this repair.
- Existing user changes in `d:\Stock_market\algoagentx\docs\get_gold_data_database.md` were left untouched.

## Additional fixes completed during resumed review

- Bounded shared-cache local-lock waiting, Redis I/O and loaders under the same 15-second/caller deadline. Lease cleanup is bounded to 100 ms and otherwise relies on lease expiry.
- Validate the shared session encryption key before performing authentication when Redis is active.
- Reject a loader result if it has lost its Redis lease; compare ownership before publishing or deleting leases.
- A rejected old local token cannot evict a newer cached token.
- Missing position/link identifiers, invalid sides/quantities, nonfinite numbers and partially filled protection evidence do not prove full broker protection.
- Malformed persisted protection-event payloads return Unverified rather than breaking summary serialization.
- Added 16 offline cases covering these boundaries. Total acceptance cases: 30.

## Validation

Artifacts are under `d:\Stock_market\algoagentx\artifacts\`.

| Check | Result |
| --- | --- |
| `copy_acceptance_final.txt` | 30 passed, 2 warnings, exit 0 |
| `copy_focused_final.txt` | 46 passed, 2 warnings, exit 0; explicit four-file focused selection |
| `copy_targeted_final.txt` | 289 passed, 2 warnings, exit 0 |
| `copy_remaining_final.txt` | 447 passed, 14 warnings, exit 0; excludes local_debug and the named collection-blocked file |
| `copy_regression_final.txt` | Collection error for missing baseline import, exit 2 |
| `copy_typescript_final.txt` | Eight remaining diagnostics, exit 2; none on repaired deployment page |
| `copy_source_review_final.txt` | 23 changed/untracked Python files compile; baseline blocker attribution recorded |
| `git diff --check` | Passed; Git emits existing LF/CRLF conversion warnings |
| Docker Compose `config --services` | Passed; no containers modified |

These suites overlap; do not sum their counts. The older `copy_focused.txt` contains 56 passing progress markers but no explicit count or exit footer; the new focused artifact uses the explicit four-file selection in the launcher. Deprecation warnings remain, plus an unawaited test AsyncMock warning in the market-data publish test. No real Redis/PostgreSQL/broker integration test or browser rendering test was performed.

Reproduce the checks using the existing installed interpreter (no dependency install):

```bat
d:\Stock_market\algoagentx\AlgoAgentXAPI\.venv\Scripts\python.exe d:\Stock_market\algoagentx\artifacts\start_copy_checks.py launch acceptance focused targeted remaining regression typescript
d:\Stock_market\algoagentx\AlgoAgentXAPI\.venv\Scripts\python.exe d:\Stock_market\algoagentx\artifacts\verify_copy_review.py
git -C d:\Stock_market\algoagentx diff --check
```

The launcher writes each process's exit code to its artifact; launch success alone is not test success. Python suites use `d:\Stock_market\algoagentx\AlgoAgentXAPI\scripts\run_copy_reliability_tests.py`, which blocks outbound socket connection calls while permitting the Windows stdlib asyncio wakeup socketpair.

## Frozen behavior and safety review

- No changes to strategy/incremental implementations, warmup algorithms, sizing formulas or risk-setting files were found in the diff. Shared broker I/O necessarily changes scheduling, not strategy calculations.
- Execution-engine changes are deployment-ID telemetry and durable deferred-copy expiry anchoring. Existing concurrent dispatch, account-scoped reservation/idempotency and primary-position gates remain in place.
- Uncertain entry acknowledgements remain PENDING and reconcile against exact broker order/strategy IDs. Partial-close uncertainty requires manual review; writes are not replayed automatically.
- Deselected copy accounts with persisted open positions or pending orders remain eligible for reconciliation. Disconnected accounts and mode mismatches remain blocked.
- Financial refresh remains enabled by default on pretrade paths; background copy reconciliation and position-management refresh disable it. Trading state is not placed in the shared metadata/session cache.

## Schema review

Reviewed the official TradeLocker pages named **Get configuration**, **Get non-final orders**, and **Difference between order(id) and position(id)**, including their markdown OpenAPI definitions. Saved config example: `d:\Stock_market\algoagentx\artifacts\tradelocker_schema.txt`.

- `ordersConfig`/`positionsConfig` determine positional column mapping. `stopLossId`/`takeProfitId` are identifiers, not prices. An order acknowledgement is not a filled position.
- Config describes quota fields `rateLimitType`, `measure`, `intervalNum`, `limit`, with SECONDS/MINUTES units. Route names in the adapter match documented examples; the docs do not provide a closed enum for every broker deployment.
- The OpenAPI definition describes rateLimits as an object while its example is a list. The implementation expects the example's list shape; confirm actual selected-account responses before rollout.
- Documentation does not fully specify broker-specific status vocabulary, remaining protective quantity after partial fills, or every protection linkage convention. Unknown/partial evidence stays Unverified. `isOpen` is not treated as sufficient evidence of an active protective order.

## Operational requirements and unresolved limits

1. **Redis is mandatory operationally for the multi-worker guarantee.** All affected workers must use the same Redis database and existing server-side `ALGOAGENTX_CREDENTIAL_SECRET` (preferred) or `SECRET_KEY`. Do not use a frontend/public key. No secret values were inspected or changed. If the Redis manager returns no client, code retains process-local fallback; cross-process deduplication/rate limiting is then not guaranteed. Redis command errors fail requests instead of silently bypassing coordination.
2. Default global spacing remains 300 ms (`TRADELOCKER_SHARED_REQUEST_SPACING_MS`); setting zero disables global pacing. Do not change execution gates or quota knobs for rollout without review.
3. Priority/cooldown/Redis failure can defer background exposure reads. Close writes are not automatically replayed or exempted from broker cooldown. A context-free close that needs authentication can still be deferred by entry priority. Continuous entry traffic, cold-cache three-copy execution budgets, and protection/close latency need DEMO verification; no claim of starvation-free priority scheduling is made.
4. Position snapshots and active orders are separate broker requests, not an atomic snapshot. Evidence older than 120 seconds is Unverified. Existing persisted sync events retain the first 25 positions; positions outside that sample cannot be verified by this enrichment. Primary UI protection was not redesigned.
5. Actual multi-process Redis lease contention, broker quota scope, encrypted-key consistency, worker INFO logging and sustained request reduction remain unproven at runtime.
6. Historical missing-table reports were not repaired or independently reproduced in this offline pass. No migration is introduced by these changes. Compare existing migrations with the intended database using approved read-only checks before any deployment; do not run Alembic upgrade blindly.
7. Fix remaining TypeScript diagnostics before claiming a clean web build. A next/build production build was not run.

## Affected services and build-only commands

Validated names from `d:\Stock_market\algoagentx\docker-compose.yml`: `api`, `web`, `alert_worker`, `live_market_worker`, `live_strategy_worker`, `live_reconcile_worker`, `live_position_manager_worker`, `live_legacy_runner_worker`, `live_tradelocker_candle_worker`, `live_history_worker`, `live_dry_test_worker`. `celery_worker` is profile-gated; rebuild if that profile is actually used for broker work. Market-data daily services are not part of this repair's rollout.

These commands are **not executed** and only build images; they do not update running containers:

```bat
docker compose --project-directory d:\Stock_market\algoagentx --env-file d:\Stock_market\algoagentx\.env.prod -f d:\Stock_market\algoagentx\docker-compose.yml build api alert_worker live_market_worker live_strategy_worker live_reconcile_worker live_position_manager_worker live_legacy_runner_worker live_tradelocker_candle_worker live_history_worker live_dry_test_worker
docker compose --project-directory d:\Stock_market\algoagentx --env-file d:\Stock_market\algoagentx\.env.prod -f d:\Stock_market\algoagentx\docker-compose.yml build web
```

Do not use whole-stack `up --build`, `down`, or a blanket restart. Collector-only deployment cannot install the execution-engine fix into a running runner. Any later runner replacement needs an explicit, justified maintenance plan that accounts for exposure, pending acknowledgements and in-flight work. No deployment was attempted in this review.

## Primary plus three-copy DEMO checklist — not performed

1. Obtain explicit authorization for any artificial broker order; confirm all four selected accounts are DEMO, matching mode and selected account identifiers. Keep LIVE gates unchanged.
2. Verify existing database tables, Redis/key consistency, deployed code versions and INFO-level request logs without printing credentials.
3. Observe cold and warm session/config requests from all relevant workers: one login-scoped session load, separate selected-account metadata, no cached financial/position truth.
4. Use an authorized DEMO event to confirm primary gates and three independent account-scoped copies. Compare sizing and risk decisions to frozen expectations; confirm one failing copy does not cancel siblings and each account has at most one entry for the signal.
5. Confirm broker positions, active SL/TP IDs, side/type/price and covering quantity independently in TradeLocker. Verify missing/stale/partial evidence displays Unverified, not requested or zero prices.
6. Confirm copies remain managed after the primary is flat and after a copy is deselected. Validate partial-close/full-close acknowledgement handling without retrying an uncertain write.
7. Exercise 429, timeout and expired-token scenarios in an isolated transport harness, not by deliberately flooding the broker. Verify cooldown, bounded expiry, no renewed deferred-copy window, no duplicate sends and healthy cTrader restoration.
8. Observe request counts, HTTP 429s, quote freshness and close latency under representative load before declaring the repair successful. Stop rollout on new errors or stale exposure truth; do not weaken safeguards to pass the checklist.