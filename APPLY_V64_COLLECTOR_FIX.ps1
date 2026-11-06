param([string]$EnvPath = '.env.prod')
$ErrorActionPreference = 'Stop'
$full = (Resolve-Path -LiteralPath $EnvPath).Path
$content = [System.IO.File]::ReadAllText($full)
if ($content.Contains('REPLACE_WITH_EXISTING_LOCAL_VALUE')) {
  throw 'Invalid placeholder in .env.prod. Restore real typed values from your private working backup; do not overwrite with the ZIP template.'
}
$backup = "$full.backup.$(Get-Date -Format yyyyMMdd-HHmmss)"
Copy-Item -LiteralPath $full -Destination $backup
# Does not modify credentials, broker accounts, source SHA, auto-trade, or strategy parameters.
$changes = [ordered]@{
  LIVE_INCREMENTAL_ENABLED='true'
  LIVE_INCREMENTAL_ADAPTER_ENABLED='true'
  LIVE_INCREMENTAL_MONITOR_ONLY='false'
  LIVE_TRADELOCKER_BOUNDARY_POLL_ENABLED='true'
  LIVE_TRADELOCKER_GAP_BACKFILL_ENABLED='false'
  LIVE_RUNNER_SEQUENTIAL_CATCHUP_ENABLED='false'
  LIVE_TRADELOCKER_SESSION_GAP_RESUME_ENABLED='false'
  LIVE_RUNNER_DEMO_OBSERVED_GAP_RESUME_ENABLED='false'
  LIVE_RUNNER_DEDICATED_CANDLE_IDLE_ENABLED='true'
  LIVE_TRADELOCKER_REGISTRY_REFRESH_SECONDS='15'
  LIVE_TRADELOCKER_FAST_EMPTY_RETRIES='2'
  LIVE_TRADELOCKER_EMPTY_RETRY_SECONDS='8'
  LIVE_TRADELOCKER_IDLE_BOUNDARY_GRACE_SECONDS='10'
  LIVE_RUNNER_STALE_ORDER_GUARD_ENABLED='true'
  LIVE_RUNNER_MAX_ORDER_AGE_AFTER_CLOSE_SECONDS='120'
}
$lines = New-Object 'System.Collections.Generic.List[string]'
$seen = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
foreach ($line in [regex]::Split($content, "`r?`n")) {
  if ($line -match '^\s*([A-Z][A-Z0-9_]*)\s*=') {
    $key = $Matches[1]
    if ($changes.Contains($key)) {
      if ($seen.Add($key)) { $lines.Add("$key=$($changes[$key])") }
      continue
    }
  }
  $lines.Add($line)
}
foreach ($key in $changes.Keys) { if ($seen.Add($key)) { $lines.Add("$key=$($changes[$key])") } }
[System.IO.File]::WriteAllText($full, ($lines -join "`r`n"), [System.Text.UTF8Encoding]::new($false))
Write-Host "Existing environment backed up: $backup"
Write-Host "Updated only the $($changes.Count) collector/recovery settings. Credentials and strategy SHA preserved."
