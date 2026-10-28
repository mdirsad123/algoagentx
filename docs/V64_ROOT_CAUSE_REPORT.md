# V6.4 collector root-cause report — 2026-10-28

Status: **PARTIALLY VERIFIED — collector deployed; end-to-end reliability not complete.**

## Phase 3 and follow-up findings (October 29 IST / October 28 UTC)

Final audit exception: `.env.prod` changed at 19:50:58.816 UTC outside this
task's edits. Changed keys are `LIVE_TRADELOCKER_EMPTY_RETRY_SECONDS` and
`LIVE_TRADELOCKER_FAST_EMPTY_RETRIES`. Further deployment/configuration work is
paused pending attribution. No environment restoration was attempted. The
validation report records hashes and the first successful follow-up-image cycle.

- The grace fix recovered actual TradeLocker ingestion. Six consecutive closes
  at 18:45–19:10 UTC have matching collector logs, PostgreSQL closed candles,
  and retained runner evaluations. See the validation report for measured times.
- A follow-up deployed at 19:46:43.600 UTC stops grace/inactive skips from
  renewing `last_poll_completed_at` or clearing a prior error. It exposes
  `last_poll_result_at`, `last_skip_reason`, and broker-response time separately.
  `already_stored` remains a successful DB freshness check, not a broker response.
- Empty-response retries now reset when the expected closed-candle bucket
  changes. The existing bounded retry count/delay remain unchanged. This fixes
  reopening detection after an idle probe without assuming session hours.
- Before this follow-up, new tests produced 3 failures / 24 passes. Afterwards
  the selected suite passed 91 tests. The cached-registry exception test passed
  without a production change: no registry starvation fix is claimed. Refresh
  still precedes polling and can impose its 20-second timeout.
- The five fixture/gate failures were Windows text-decoding differences. Explicit
  UTF-8 fixture reads fixed them; no strategy, authorized SHA, or gate was changed.
- Actual DB source SHA is
  `c50b77c72656ce76ec69b87cca07254520f88d181545a3ee4c60d161a25b2747`.

### Runner recovery diagnosis — not changed

The inspected runner setting `live_runner_sequential_catchup_enabled` is **false**.
In `D:\Stock_market\algoagentx\AlgoAgentXAPI\app\services\live\auto_runner_service.py`,
the initial query chooses the newest closed candle; selecting the earliest
pending candle occurs only inside `_sequential_monitor_enabled`. After a long
cold calculation, the completion path schedules the next boundary using current
UTC. A pending intermediate candle can therefore be skipped. The retained-state
validator correctly rejects a nonconsecutive next candle and cold-primes again.
This explains the observed 15:00 → 15:10 selection with stored 15:05 available;
it is not proof of a broken cache or permission to weaken continuity validation.

Enabling sequential replay changes evaluated strategy history and order
suppression behavior. It was not enabled, and no runner restart was requested.
Runner/collector/PostgreSQL start times independently changed around 17:07 UTC
during the interruption; cause is unverified. The follow-up collector deployment
preserved runner start `2026-10-28T17:07:48.761312649Z`.

Still open: inconsistent ≤60-second retained performance, 48-advance rolling
rebase parity, historical catch-up policy, missing long-gap API/test collection,
registry timeout impact, and the unverified 30-minute UI next-run anomaly.
Do not infer safe gap skipping from two later broker candles.

Evidence: `D:\Stock_market\algoagentx_backups\v64_phase3_20261028-203553` and
`D:\Stock_market\algoagentx_backups\v64_collector_followup_20261029-011418`.
Both contain private environment backups; never publish them.

## Historical Phase 2 record

The sections below preserve the original pre-deployment findings. Statements
about unperformed deployment/tests apply only to Phase 2; updates above supersede them.

## Confirmed primary cause

Call chain in `D:\Stock_market\algoagentx\AlgoAgentXAPI\app\services\live`:
`live_tradelocker_candle_worker._run` captures UTC time, awaits `_poll_one`, then
calls `candle_poll_schedule.next_poll_delay`; `next_candle_probe` deliberately
returns a future boundary. `_poll_one` originally used the pre-query snapshot
after its awaited deployment query. It returned an exact `retry_at`, but `_run`
ignored that field. A grace skip handled after +2 seconds therefore moved to the
next five-minute boundary. `expected=None` was missing `open` metadata in the
grace result, not evidence of an unregistered deployment.

Actual pre-deployment container logs on October 28, UTC (IST = UTC +05:30):

| Boundary UTC / IST | Attempt UTC | Grace skip UTC |
|---|---|---|
| 14:25 / 19:55 | 14:25:01.965 | 14:25:02.872 |
| 14:30 / 20:00 | 14:30:01.978 | 14:30:02.122 |
| 14:35 / 20:05 | 14:35:01.991 | 14:35:02.159 |
| 14:40 / 20:10 | 14:40:01.990 | 14:40:02.189 |
| 14:45 / 20:15 | 14:45:01.985 | 14:45:02.106 |
| 14:50 / 20:20 | 14:50:01.974 | 14:50:02.251 |

These are FAILED pre-patch cycles, not successful broker ingestion observations.
Registry scans continued with one deployment; matching runner logs show
`RUNNER_NO_NEW_CANDLE_IDLE`. Registry scans are eligibility queries, not fetches.

## Executed reproduction

New deterministic tests run actual scheduler functions with isolated I/O doubles.
Before patch, handler at 12:45:02.100 produced 299.9 seconds instead of 0.1.
Actual `_run` fake-clock reproduction retried at 12:50:02. A deployment lookup
completing at 12:45:02.100 still skipped using the original 12:45:01.980 snapshot.
These tests pass after the patch; no real candles or orders were generated.

## Patch

- `_poll_one`: refresh UTC time after the awaited deployment query; include
  expected candle open in grace metadata.
- `_run`: consume exact `retry_at` in a separate grace branch, also with boundary
  polling disabled; emit `TRADELOCKER_GRACE_RETRY`.
- `next_poll_delay`: optional explicit deadline; an expired deadline yields a
  100ms minimum delay. Fallback uses the current boundary, never next boundary.
- Empty-response retry counts, registry refresh policy, history and order paths
  remain unchanged.

## Related findings, not fixed or claimed verified

1. High confidence: `_run` records `last_poll_completed_at` for grace skips, and
   `candle_worker_health.collector_status` treats that timestamp as progress.
   Thus repeated skips can look healthy without broker responses. Ownership and
   fallback changes need separate concurrency tests before deployment.
2. High confidence: broader existing gate tests use a research-source fixture
   with hash `916f1ad9b922b4349fb9167567392bda8a06766f358210f86714676aa364b503`,
   while the tested baseline constant is
   `7122bb951cd867f3cd57f66d2fef6b6307e708c7c4a5547d42aaab79a2bbb5cb`.
   Five gate tests fail unchanged with backed-up pre-patch scheduler modules too.
   Neither is a measurement of the active DB source; do not alter authorization
   or frozen strategy to make tests pass.
3. High confidence: the existing long-gap test imports absent
   `observed_broker_gap_eligible`; collection fails. No gap bypass added.
4. Runner source explicitly rebases at configured maximum advances; retained
   state is process-local. A runner restart loses it. Runner was not restarted.
   Retained state unit tests are not actual V6.4 signal parity evidence.
5. Extended empty streaks retain the existing one-poll-per-boundary policy;
   reopening later than the idle probe can still defer detection. Per-cycle
   retry-budget redesign is outside this minimal grace patch.
6. Registry exceptions can delay polling because refresh precedes dispatch.
   Successful refresh preservation is tested; full outage scheduling is not.
7. UI next-run assignments were located, but the reported 30-minute jump has
   not been reproduced or explained from actual DB scheduler state.

## Evidence location

`D:\Stock_market\algoagentx_backups\v64_phase2_20261028-202014`
contains verified backups, preflight hashes, original Git diff/status,
before/after test output and collector/runner pre-deployment logs.

No database writes, broker calls, orders, credential changes or restarts were
performed by this phase. Active DB SHA, real closed-candle persistence, full
80K rolling parity, stale-order integration and live recovery remain unverified.