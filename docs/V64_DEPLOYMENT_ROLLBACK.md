# V6.4 collector deployment / rollback — 2026-10-28

Status: **DEPLOYED, PARTIALLY VERIFIED**. The grace patch and collector follow-up
were built and recreated independently. No runner restart is required. Do not
recreate DB, Redis, history or unrelated workers. Do not restore `.env.prod`:
no environment changes were made.

## Current deployment — October 28 UTC / October 29 IST

**Do not run another deployment/rollback blindly:** at final audit `.env.prod`
differed from the verified deployment backup. Its modification time is
19:50:58.816 UTC; changed names are `LIVE_TRADELOCKER_EMPTY_RETRY_SECONDS` and
`LIVE_TRADELOCKER_FAST_EMPTY_RETRIES`. This task did not edit them. Reconcile
intent before using the commands below, since Compose would read the changed
file. Do not restore the private backup over another actor's edits automatically.

Follow-up start: `2026-10-28T19:46:43.599797745Z` (01:16:43.600 IST October 29).
Image: `sha256:8462eed7153b3fbc6aac8ab2550156f050663a3bfb01027305b7650e2de4c744`.
Verified installed hashes:
- Scheduler: `276d05f49c378798e1979de021523dd0d11743212c7b690f6d8028f3d163ffa4`
- Collector: `ef6a531558cc57e8ba84a647ab779bf152da5d4ac6b7b60df50c0b78af458a60`

Executed by `D:\Stock_market\algoagentx_backups\deploy_followup.py`:
Compose config validation, preserve old image, collector-only build, compare
source hashes in an isolated no-network image container, collector-only recreate,
compare installed hashes, assert runner start unchanged. Effective commands:

```powershell
Set-Location D:\Stock_market\algoagentx
docker compose --env-file D:\Stock_market\algoagentx\.env.prod config --quiet
docker compose --env-file D:\Stock_market\algoagentx\.env.prod build live_tradelocker_candle_worker
docker compose --env-file D:\Stock_market\algoagentx\.env.prod up -d --no-deps --no-build --force-recreate live_tradelocker_candle_worker
```

Runner start before/after follow-up remained `2026-10-28T17:07:48.761312649Z`.
The earlier change from 13:45 to 17:07 coincided with collector/PostgreSQL start
changes during interruption; cause is not established. Do not claim continuous
runner uptime across that event.

### Preferred rollback: follow-up only (NOT executed)

Preserved image `algoagentx-v64-collector-rollback:pre-followup` resolves to
`sha256:1fea7f3fbe110ddc55add7f8421172aa9f635f3afadbb6f42677193b3596f810`.
It retains the original grace fix, but loses the follow-up health/reopening fixes.
Verify tag and service mapping first; stop on any error:

```powershell
Set-Location D:\Stock_market\algoagentx
docker image inspect algoagentx-v64-collector-rollback:pre-followup --format '{{.Id}}'
if ($LASTEXITCODE -ne 0) { throw 'Rollback image missing' }
docker image tag algoagentx-v64-collector-rollback:pre-followup algoagentx-live_tradelocker_candle_worker:latest
if ($LASTEXITCODE -ne 0) { throw 'Tag failed; do not recreate' }
docker compose --env-file D:\Stock_market\algoagentx\.env.prod up -d --no-deps --no-build --force-recreate live_tradelocker_candle_worker
if ($LASTEXITCODE -ne 0) { throw 'Collector rollback failed' }
```

Then verify runner start unchanged, heartbeat and subsequent real closed-candle
ingestion. Rollback only changes the image; review source separately before any
later rebuild. Source backups and actual deployment logs:
`D:\Stock_market\algoagentx_backups\v64_collector_followup_20261029-011418`.
The earlier full pre-grace rollback tag is
`algoagentx-v64-collector-rollback:20261028-phase3`; it reintroduces the known stall.
Neither rollback has been performed. Never restore the entire dirty tree.

## Historical Phase 2 procedure (not current rollback instructions)

The remaining sections retain the original pre-deployment plan. In particular,
the historical `20261028-phase2` tag below is not the verified current rollback
tag. Use the verified follow-up rollback above instead.

## Backup and checkpoint

Verified local file backups and original Git diff:
`D:\Stock_market\algoagentx_backups\v64_phase2_20261028-202014`.
The directory contains credentials in its `.env.prod` backup: keep local/private,
never commit, upload or paste it. No backup is stored in the Docker build context.

## Preflight and targeted deployment (not executed)

First finish effective-config/DB SHA checks and review unrelated working-tree
changes: the shared Dockerfile copies the whole backend, not just this patch.
Then use PowerShell:

```powershell
Set-Location D:\Stock_market\algoagentx
docker compose --env-file D:\Stock_market\algoagentx\.env.prod config --quiet
if ($LASTEXITCODE -ne 0) { throw 'Compose validation failed' }
$oldImage = docker inspect algoagentx_live_tradelocker_candle_worker --format '{{.Image}}'
if ($LASTEXITCODE -ne 0) { throw 'Collector inspection failed' }
docker image tag $oldImage algoagentx-v64-collector-rollback:20261028-phase2
if ($LASTEXITCODE -ne 0) { throw 'Rollback image preservation failed' }
docker compose --env-file D:\Stock_market\algoagentx\.env.prod build live_tradelocker_candle_worker
if ($LASTEXITCODE -ne 0) { throw 'Build failed; do not recreate' }
docker compose --env-file D:\Stock_market\algoagentx\.env.prod up -d --no-deps --no-build --force-recreate live_tradelocker_candle_worker
if ($LASTEXITCODE -ne 0) { throw 'Collector recreation failed' }
docker compose --env-file D:\Stock_market\algoagentx\.env.prod logs --since=10m --tail=200 live_tradelocker_candle_worker live_legacy_runner_worker
```

Verify exact installed source, settings import, registry membership, DB closed
candles and processed cursor. Observe 4–6 real M5 closes; require same-cycle
grace retry, actual fetch, DB ingestion, runner evaluation and retained mode.
Never submit artificial broker orders for verification. Preserve Auto Trade.

## Source rollback (available now; not executed)

Review any edits made AFTER this phase before restoring, to avoid overwriting
newer work. Restore only these two production files, not the entire Git tree:

```powershell
$backup = 'D:\Stock_market\algoagentx_backups\v64_phase2_20261028-202014'
Copy-Item "$backup\AlgoAgentXAPI\app\services\live\candle_poll_schedule.py" 'D:\Stock_market\algoagentx\AlgoAgentXAPI\app\services\live\candle_poll_schedule.py' -Force
Copy-Item "$backup\AlgoAgentXAPI\app\services\live\live_tradelocker_candle_worker.py" 'D:\Stock_market\algoagentx\AlgoAgentXAPI\app\services\live\live_tradelocker_candle_worker.py' -Force
```

## Image rollback after future deployment (not executed)

The preservation tag must have been created successfully before the build.
Current Compose-generated collector image name was observed in phase 1; verify
that mapping remains unchanged before using this command:

```powershell
Set-Location D:\Stock_market\algoagentx
docker image tag algoagentx-v64-collector-rollback:20261028-phase2 algoagentx-live_tradelocker_candle_worker:latest
if ($LASTEXITCODE -ne 0) { throw 'Rollback image missing; do not recreate' }
docker compose --env-file D:\Stock_market\algoagentx\.env.prod up -d --no-deps --no-build --force-recreate live_tradelocker_candle_worker
```

Rollback returns the known grace-stall behavior; it is not a reliability fix.
Do not use `git reset`, volume deletion, database resets or broad Docker cleanup.