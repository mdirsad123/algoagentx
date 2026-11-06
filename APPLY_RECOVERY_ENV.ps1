# Updates only known recovery knobs in EXISTING local .env.prod; never copies the packaged redacted template.
$ErrorActionPreference = 'Stop'
$dest = Join-Path $PSScriptRoot '.env.prod'
if (-not (Test-Path $dest)) { throw 'No local .env.prod found. Preserve your original configured production file.' }
$content = Get-Content -LiteralPath $dest -Encoding UTF8
if ($content -match 'REPLACE_WITH_EXISTING_LOCAL_VALUE') { throw 'Found sanitized placeholder values in .env.prod. Restore real local .env.prod before proceeding.' }
$updates = [ordered]@{
  'LIVE_RUNNER_SEQUENTIAL_CATCHUP_ENABLED' = 'true'
  'LIVE_RUNNER_DEMO_OBSERVED_GAP_RESUME_ENABLED' = 'true'
  'LIVE_RUNNER_DEMO_OBSERVED_GAP_MIN_MISSING_BARS' = '6'
  'LIVE_TRADELOCKER_GAP_BACKFILL_ENABLED' = 'false'
  'LIVE_TRADELOCKER_SESSION_GAP_RESUME_ENABLED' = 'false'
  'LIVE_TRADELOCKER_BOUNDARY_POLL_ENABLED' = 'true'
  'LIVE_TRADELOCKER_IDLE_BOUNDARY_GRACE_SECONDS' = '10'
  'LIVE_RUNNER_DEDICATED_CANDLE_IDLE_ENABLED' = 'true'
  'LIVE_RUNNER_DEDICATED_CANDLE_PROBE_SECONDS' = '5'
  'LIVE_RUNNER_DEDICATED_CANDLE_FAST_PROBES' = '3'
  'LIVE_RUNNER_DEDICATED_CANDLE_MAX_IDLE_PROBE_SECONDS' = '30'
  'LIVE_RUNNER_STALE_ORDER_GUARD_ENABLED' = 'true'
  'LIVE_RUNNER_MAX_ORDER_AGE_AFTER_CLOSE_SECONDS' = '120'
}
$backup = "$dest.backup.$(Get-Date -Format 'yyyyMMdd_HHmmss')"
Copy-Item -LiteralPath $dest -Destination $backup -ErrorAction Stop
$result = [System.Collections.Generic.List[string]]::new()
$seen = @{}
foreach ($line in $content) {
  if ($line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=') {
    $key = $Matches[1]
    if ($updates.Contains($key)) {
      if ($seen.ContainsKey($key)) { continue } # collapse duplicates
      $result.Add("$key=$($updates[$key])")
      $seen[$key] = $true
      continue
    }
  }
  $result.Add($line)
}
foreach ($key in $updates.Keys) {
  if (-not $seen.ContainsKey($key)) { $result.Add("$key=$($updates[$key])") }
}
[System.IO.File]::WriteAllLines($dest, [string[]]$result, [System.Text.UTF8Encoding]::new($false))
Write-Host "Updated recovery flags in existing .env.prod. Backup: $backup" -ForegroundColor Green
Write-Host 'Auto Trade, broker credentials and original incremental/SHA settings were not changed.'
