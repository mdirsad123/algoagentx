# V6.4 validation — 2026-10-28

**PARTIALLY VERIFIED — deployed to DEMO; NOT COMPLETE.**

## Phase 3 / collector follow-up — October 29 IST / October 28 UTC

### Final preservation exception — further deployment paused

At 19:52:02 UTC the final audit detected `.env.prod` had changed since the
successful preservation check. File modification time is 19:50:58.816 UTC.
Changed key names only: `LIVE_TRADELOCKER_EMPTY_RETRY_SECONDS` and
`LIVE_TRADELOCKER_FAST_EMPTY_RETRIES`. This task did not edit that file; actor
and intent are unknown. No restoration or subsequent deployment was performed.
Current file SHA is
`df825149898710f145e743ef41025e9694e8088211379364971a5c037f1bd315`;
backup SHA is
`a66a1b6c80bfbab55eea96adc04a53cee06035110686ad49900e581b27fa0ec3`.
Thus earlier byte-equality results below describe their check time, not final
preservation. Resolve the concurrent configuration change before another deploy.
Current collector image/start and runner start still match deployment evidence.

First real follow-up-image cycle: October 28 19:50 UTC close (October 29 01:20
IST), collector attempt 19:50:01.988, fetch start 19:50:02.190, HTTP history 200,
ingestion lag 3.898 seconds. Runner completed RETAINED_INCREMENTAL at
19:51:00.558, generate 53.471 seconds, dispatch 53.732 seconds, HOLD_IGNORED.
Incremental update alone measured wall 52.420 / CPU 52.358 seconds. This is
evidence of substantial computation, not proof that external contention caused
earlier overruns. Heartbeat at 19:51:34.968 was HEALTHY with broker-response time.
Only one post-follow-up cycle is verified here; do not count the earlier six as
six cycles of this newer image. Close-to-completion was 60.558 seconds, so even
this cycle does not meet a strict 60-second end-to-end latency threshold.

### Executed checks

| Check | Result |
|---|---|
| Original deployed grace fix selected suite | 87 passed |
| Follow-up regressions before changes | 3 failed, 24 passed |
| Follow-up selected suite, including broker-history async cases | 91 passed, 2 existing deprecation warnings, 11.62s |
| Existing long-gap test collection, repeated | Still fails: absent `observed_broker_gap_eligible` |
| Python AST checks of 2 production modules and 3 edited test files | Passed |
| `git diff --check` | Passed; existing CRLF conversion warnings only |
| `.env.prod` byte comparison against Phase 3 and follow-up backups | Unchanged |
| Collector source/image hash check and Compose config validation | Passed |
| Runner restart caused by follow-up deployment | None; start time unchanged |

Async broker-history tests were executed through an external pytest plugin using
stdlib `asyncio.run`, not by installing dependencies. Reproduction command:

```powershell
& D:\Stock_market\algoagentx\AlgoAgentXAPI\.venv\Scripts\python.exe D:\Stock_market\algoagentx_backups\phase3_test_checks.py
```

The full repository suite is **not** passing/claimed: the long-gap collection
error is intentionally visible. Four new worker cases cover skipped health
progress (two cases), registry failure with cached deployments, and renewing
bounded retries at a new expected candle. Registry failure already passed before
the follow-up, so no registry fix is attributed to it.

### Six consecutive actual cycles

UTC closes below are October 28, 2026; IST closes are October 29, 2026.
Each has one logged dispatch, `RETAINED_INCREMENTAL`, `HOLD_IGNORED`, a closed
PostgreSQL `TRADELOCKER` candle and matching collector fetch. These are evidence
for the Phase 3 grace fix, **before** the 19:46 follow-up deployment.

| Close UTC | Close IST | DB ingest lag (s) | Generate (s) | Dispatch duration (s) |
|---|---|---:|---:|---:|
| 18:45 | 00:15 | 5.467 | 42.487 | 42.576 |
| 18:50 | 00:20 | 3.416 | 39.456 | 39.520 |
| 18:55 | 00:25 | 3.729 | 42.790 | 42.867 |
| 19:00 | 00:30 | 3.572 | 42.235 | 42.301 |
| 19:05 | 00:35 | 4.789 | 67.374 | 67.591 |
| 19:10 | 00:40 | 4.236 | 66.716 | 66.982 |

Thus continuity is demonstrated in this window; the ≤60-second target is not
consistently met. Initial recovery ingestion at 15:09:04.923 for the 15:00 open
was 244.923 seconds late. The 15:10 and 15:15 closes ingested in 4.656 and 7.057
seconds respectively. Actual boundary-crossing lookup at 15:15:01.965 now fetched
at 15:15:02.391 instead of deferring five minutes.

Archived runner logs plus current logs through 19:45 contain 45 retained and
3 full-history evaluations; this is not one uninterrupted process lifetime.
Runner/collector/PostgreSQL start times changed around 17:07 UTC during an
interruption, cause unverified. No restart by this follow-up; current runner start
is `2026-10-28T17:07:48.761312649Z`.

Read-only snapshot at 19:49:23.813 UTC: cursor 19:40, next run 19:50:02,
Auto Trade true, stale guard true, duplicate candle timestamps empty in the
queried range since 15:00. The last completed event reports HOLD, executed false.
No 30-minute scheduler jump was seen in this snapshot. Earlier runner output
reported `HOLD_STALE_CANDLE`; the snapshot query found no separately named
`RUNNER_STALE_ORDER_SUPPRESSED` events. Do not claim BUY/SELL stale suppression
integration coverage or broker execution parity from HOLDs.

### Actual-source 80K parity

Read-only DB source hash:
`c50b77c72656ce76ec69b87cca07254520f88d181545a3ee4c60d161a25b2747`.
Adapter candidate hash:
`26699c47e24c99f12c66d3fdba2fd05b6da940fc329c78e8e28354cd56ac2106`.
Input: 80,003 exported actual stored TradeLocker candles and resolved deployment
parameters, with 80,000-bar warmup. Initial compared historical signal rows match
(428 baseline BUY/SELL rows). Three subsequent comparisons at 14:55, 15:00 and
15:05 UTC match position/SL/TP/reason; all three latest positions are HOLD/0.
Incremental durations were 67.195, 75.869 and 72.032 seconds. Initial baseline
was 711.853 seconds, hybrid 184.987 seconds. Host workload may affect timing;
resource contention is a possibility, not a proven cause.

The JSON contains a generic external-CSV caveat. Export provenance establishes
this CSV came from the deployment DB, but there is no claim it remains identical
after subsequent broker revisions. Three steps do **not** cover 48-advance
rebase, execution, risk/sizing, or all future signals. Both parity and bounded
observer jobs completed; no duplicate jobs were launched during resumption.

### Follow-up deployment and remaining gates

Collector started `2026-10-28T19:46:43.599797745Z`; installed image
`sha256:8462eed7153b3fbc6aac8ab2550156f050663a3bfb01027305b7650e2de4c744`.
At 19:46:49 it reported `already_stored` for 19:40; heartbeat at 19:47:19 was
HEALTHY. That is startup/DB-freshness evidence, not six follow-up broker cycles.

Open gates: consistent ≤60 seconds, 48-step parity, historical catch-up/re-prime
policy, long-gap test/spec, registry timeout impact, natural reopening/grace
health validation, and the UI anomaly. No strategy or trading behavior changed.

Evidence directories:
- `D:\Stock_market\algoagentx_backups\v64_phase3_20261028-203553`
- `D:\Stock_market\algoagentx_backups\v64_collector_followup_20261029-011418`

Key files: `cycles.json`, `deployment.json`, `before.txt`, `after.txt`,
`actual-db-parity.json`, `parity-process.log`, `health-observations.jsonl`,
timestamped read-only snapshots, captured logs, build/recreate logs. Evidence
directories contain private environment copies: do not publish/commit them.

## Historical Phase 2 results (superseded where noted above)

The rest of this document records pre-deployment tests; its "not executed"
statements are historical, not the current status.

## Actual executed checks

Commands ran from `D:\Stock_market\algoagentx\AlgoAgentXAPI` with
`D:\Stock_market\algoagentx\AlgoAgentXAPI\.venv\Scripts\python.exe`.
Existing pytest 8.4.2 was found; no packages installed.

| Check | Actual result |
|---|---|
| Existing boundary + collector health baseline | 24 passed |
| Initial new regression tests BEFORE patch | 11 failed, 7 passed, 2 warnings |
| Initial new regressions + existing boundary/health AFTER patch | 42 passed, 2 warnings |
| Final focused suite below (including 23 new cases) | 62 passed, 2 warnings, 3.99s |
| Broader suite adding registry/gate tests | 71 passed, 5 failed, 2 warnings, 3.83s |
| Original backed-up scheduler + new regressions + gates | 21 passed, 16 failed: same 11 regression and 5 gate failures |
| Existing long-gap test collection | Error: missing `observed_broker_gap_eligible` |
| Four synchronous broker normalization tests | 4 passed, 7 unknown-asyncio-marker warnings |
| Python syntax compile and AST checks of two patched modules + final new test | Passed after all test additions |
| Final diff whitespace check and environment preservation | `git diff --check` passed; `.env.prod` SHA unchanged |
| `docker compose --env-file .env.prod config --quiet` | Passed |
| Build / recreate / post-patch live M5 observations | Not executed |

Final focused command (PowerShell):

```powershell
Set-Location D:\Stock_market\algoagentx\AlgoAgentXAPI
& D:\Stock_market\algoagentx\AlgoAgentXAPI\.venv\Scripts\python.exe -m pytest tests/test_tradelocker_grace_retry.py tests/test_candle_boundary_idle_20261028.py tests/test_tradelocker_collector_health_recovery.py tests/test_candle_catchup_20261028.py tests/test_retained_strategy_state.py -o addopts= -q --tb=short
```

Broader suite additionally includes
`D:\Stock_market\algoagentx\AlgoAgentXAPI\tests\test_incremental_adapter_registry_20261028.py`
and `D:\Stock_market\algoagentx\AlgoAgentXAPI\tests\test_v64_hybrid_gate_20261028.py`.
The five failures are fixture/source-pin mismatches, reproduced with original
scheduler modules. No pin or strategy logic was weakened to pass them.

Warnings in focused tests are existing Pydantic validator and SQLAlchemy
declarative-base deprecations. Async broker-history tests were not executed:
pytest-asyncio is absent. New async worker tests run via standard `asyncio.run`,
so they require no additional plugin. Full repository suite was not run.

## Configuration and preservation

Backup: `D:\Stock_market\algoagentx_backups\v64_phase2_20261028-202014`.
Environment SHA-256 before edits:
`a66a1b6c80bfbab55eea96adc04a53cee06035110686ad49900e581b27fa0ec3`.
Specified `REPLACE_WITH_EXISTING_LOCAL_VALUE` placeholder was absent.
Duplicate names: `NEXT_PUBLIC_API_TIMEOUT_MS`,
`NEXT_PUBLIC_HEAVY_API_TIMEOUT_MS`, `NEXT_PUBLIC_POLLING_API_TIMEOUT_MS`.
Values not printed or changed. Runtime-effective values have not been audited.

Collector image observed before deployment:
`sha256:f7abf2c7942aa30c7cab4be2d9a1bd551d62f47de88f5dda05cdbaed5f5034e4`.
Runner start observed: `2026-10-28T13:45:49.799679434Z`. No restart performed.

## Scope limitations

Tests use isolated I/O doubles; no real broker candles, DB writes, Redis or order
execution. Error tests exercise scheduler recovery from raised exceptions, not
real HTTP 429/503 retry headers or DNS resolution. Reopening tests exercise
scheduling after success, not an actual broker session calendar.

No actual 80K parity run; no active DB-source SHA verification; no measured
post-patch FULL_HISTORY-to-RETAINED_INCREMENTAL transition. Existing retained
cache tests passing does not prove V6.4 signal, SL/TP, portfolio or sizing parity.
No post-patch actual M5 cycles observed. Pre-patch stalled-cycle times are listed
in `D:\Stock_market\algoagentx\docs\V64_ROOT_CAUSE_REPORT.md`.

Raw output files in the backup directory: `regression-before.txt`,
`regression-after.txt`, `offline-suite.txt`, `offline-suite-selected.txt`,
`original-comparison.txt`, `focused-final.txt`, `collector-before-deployment.log`,
`runner-before-deployment.log`. Some shell commands used `type` after pytest to
show captured output; use pytest's recorded summary, not the wrapper exit code.