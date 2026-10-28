# V6.4 stability implementation plan — 2026-10-28

## Current phase status — October 29 IST / October 28 UTC

**PARTIALLY VERIFIED.** Routine reversible phases proceeded under the approved
task-specific standing authorization. The historical checkpoint text below no
longer governs this task.

**Current operational checkpoint:** final audit found an unattributed `.env.prod`
change at 19:50:58.816 UTC to the two TradeLocker empty-retry settings. This task
did not change them. Pause additional deployment/configuration work until the
concurrent edit is reconciled; do not overwrite it or silently deploy it. One
post-follow-up live cycle completed (3.898-second ingestion, 53.732-second runner
dispatch), in addition to the six earlier Phase 3 cycles.

Completed Phase 3:
- Collector-only build/recreation, tested/deployed source-hash comparison and
  preservation of rollback image `algoagentx-v64-collector-rollback:20261028-phase3`.
- Read-only authorized DB-source/config audit; frozen source, 80K warmup,
  Auto Trade ON, 1% risk, max positions 1 and DEMO/XAUUSD.X/M5 preserved.
- Explicit UTF-8 fixture reads fixed five gate-test failures without changing pins.
- Actual 80K-source full/incremental comparison: historical output matched and
  three subsequent HOLD comparisons matched. No 48-step rebase/execution claim.
- Six consecutive actual closed-candle ingestion and retained-runner cycles
  correlated with PostgreSQL creation timestamps. Two exceeded 60 seconds.

Completed collector follow-up:
- Reproduced false healthy progress from grace/inactive skips and exhausted
  reopening retry budget; applied minimal collector fixes, 91 selected tests pass.
- Built/recreated collector only at 19:46:43.600 UTC, October 28 (01:16:43.600 IST,
  October 29). Source hashes verified; runner start unchanged by this deployment.
- Preserved the working Phase 3 image as
  `algoagentx-v64-collector-rollback:pre-followup`.

Remaining phases / acceptance gates:
1. Verify additional follow-up-image live closes, including actual grace/reopening
   if naturally encountered. Do not manufacture broker traffic or orders.
2. Profile retained execution without competing 80K parity subprocesses; maintain
   the frozen strategy and full warmup. The old parity/observer jobs are finished.
3. Add controlled runner-selection/recovery integration coverage before any
   behavior change. Effective sequential catch-up is false, explaining skipped
   pending bars and re-prime after a calculation crosses boundaries. Enabling it
   needs explicit trading-behavior approval and restart/state-loss justification.
4. Verify 48-advance rebase plus execution/sizing parity offline, without claiming
   the existing three HOLD checks establish it.
5. Resolve the incompatible long-gap test/spec without guessing absent candles,
   weakening SHA authorization, or hiding the collection failure.
6. Investigate registry timeout delay and UI next-run anomaly separately.

No runner, strategy, adapter, risk setting, auth, UI, migration or data changes
were made by these collector implementation phases. The unrelated dirty tree
is preserved. Current evidence and rollback instructions are in
`D:\Stock_market\algoagentx\docs\V64_VALIDATION_REPORT.md` and
`D:\Stock_market\algoagentx\docs\V64_DEPLOYMENT_ROLLBACK.md`.

## Historical plan (Phase 2)

The following pre-deployment checklist is retained for audit, not current status.

## Completed phase 2: minimal collector timing patch and offline regression

- Preserve pre-existing working-tree modifications; backup the two edited
  production files and `.env.prod` outside the repository.
- Prove old behavior before editing using fake UTC and monotonic clocks.
- Refresh readiness time after database lookup; honor exact grace retry deadline
  with minimum 100ms sleep; expose expected open and retry timing in logs.
- Test both boundary modes, delayed handling, UTC/IST, empty retry bounds,
  late response scheduling, registry 0-to-1 and refresh preservation, error
  isolation and recovery. Run existing retained-state and catch-up unit tests.
- Document existing failures rather than changing frozen strategy or source pins.

Only these production files changed:

1. `D:\Stock_market\algoagentx\AlgoAgentXAPI\app\services\live\candle_poll_schedule.py`
2. `D:\Stock_market\algoagentx\AlgoAgentXAPI\app\services\live\live_tradelocker_candle_worker.py`

New test:
`D:\Stock_market\algoagentx\AlgoAgentXAPI\tests\test_tradelocker_grace_retry.py`.

No configuration keys added, changed or removed. No sample-env changes needed.
No strategy, adapter, runner, broker adapter, auth, UI, schema or warmup changes.

## Subsequent phase — not executed

Project rules require a phase checkpoint despite the user's broader operational
authorization. Do not interpret this document as evidence of deployment.

Before targeted collector recreation:

1. Verify active deployment DB source SHA and parameters read-only, DEMO mode,
   80K requirement, effective container configuration and duplicate-key handling.
2. Compare source/image hashes and assess all pre-existing changes included by
   the shared Docker build context. Preserve current image for rollback.
3. Investigate existing gate fixture mismatch without changing frozen strategy.
4. Run isolated DB/Redis integration, closed-candle/idempotency/stale-order
   assertions and broker error handling. No production records used as fixtures.
5. Build and recreate collector only; do not restart runner or its retained state.
6. Observe 4–6 actual closed M5 cycles, record UTC/IST timestamps, ingest lag,
   runner mode/duration/cursor and signal safety. Do not count old stalled cycles.
7. Run authorized-source real-data full-versus-incremental rolling comparisons,
   including 48-advance rebase. Report all mismatches explicitly.

Heartbeat semantics, registry outage starvation, empty-streak reopening and the
UI next-run anomaly remain separate candidates requiring evidence and tests.
Rollback instructions are in
`D:\Stock_market\algoagentx\docs\V64_DEPLOYMENT_ROLLBACK.md`.