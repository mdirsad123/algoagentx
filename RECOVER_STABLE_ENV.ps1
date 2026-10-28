# Restores config using YOUR OWN trusted local backup. Never prints secret values.
param([string]$ReferenceEnv = '', [string]$ReferenceZip = '')
$ErrorActionPreference = 'Stop'
$dest = Join-Path $PSScriptRoot '.env.prod'
if (!(Test-Path -LiteralPath $dest)) { throw 'Missing .env.prod. Restore the ORIGINAL local production environment file first.' }
function Read-EnvContent([string]$path) {
    return [System.IO.File]::ReadAllText($path, [System.Text.Encoding]::UTF8)
}
function Read-ZipEnv([string]$path) {
    Add-Type -AssemblyName System.IO.Compression
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $zip=[System.IO.Compression.ZipFile]::OpenRead($path)
    try {
        $entry=$zip.Entries | Where-Object { $_.FullName -eq '.env.prod' -or $_.FullName -match '(^|/)\.env\.prod$' } | Select-Object -First 1
        if (!$entry) { throw 'Reference ZIP has no .env.prod' }
        $reader=[System.IO.StreamReader]::new($entry.Open(),[System.Text.Encoding]::UTF8)
        try { return $reader.ReadToEnd() } finally { $reader.Dispose() }
    } finally { $zip.Dispose() }
}
function EnvMap([string]$content) {
    $result=@{}
    foreach ($line in ($content -split "`r?`n")) {
        if ($line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$') { $result[$matches[1]]=$matches[2].Trim() }
    }
    return $result
}
$original=Read-EnvContent $dest
$existing=EnvMap $original
$ph='REPLACE_WITH_EXISTING_LOCAL_VALUE'
$missing=@($existing.Keys | Where-Object { $existing[$_] -eq $ph })
$reference=@{}
if ($missing.Count -gt 0) {
    $candidates=[System.Collections.Generic.List[object]]::new()
    if ($ReferenceEnv) { $candidates.Add(@('env',$ReferenceEnv)) }
    if ($ReferenceZip) { $candidates.Add(@('zip',$ReferenceZip)) }
    $backupCandidates=Get-ChildItem -LiteralPath $PSScriptRoot -File | Where-Object { $_.Name -match '^\.env\.prod\.(backup|bak)(\.|$)' } | Sort-Object LastWriteTime -Descending
    foreach ($candidate in $backupCandidates) { $candidates.Add(@('env',$candidate.FullName)) }
    foreach ($path in @((Join-Path $PSScriptRoot 'algoagentx(4).zip'), (Join-Path $env:USERPROFILE 'Downloads\algoagentx(4).zip'))) {
        if (Test-Path -LiteralPath $path) { $candidates.Add(@('zip',$path)) }
    }
    foreach ($candidate in $candidates) {
        try {
            if (!(Test-Path -LiteralPath $candidate[1])) { continue }
            $src= if ($candidate[0] -eq 'zip') { Read-ZipEnv $candidate[1] } else { Read-EnvContent $candidate[1] }
            $values=EnvMap $src
            foreach ($key in $missing) {
                if ($values.ContainsKey($key) -and $values[$key] -ne $ph -and $values[$key] -ne '') { $reference[$key]=$values[$key] }
            }
        } catch { Write-Warning "Ignoring invalid reference backup: $($candidate[1])" }
    }
    $unresolved=@($missing | Where-Object { !$reference.ContainsKey($_) })
    if ($unresolved.Count -gt 0) {
        throw "$($unresolved.Count) placeholders cannot be restored. Pass -ReferenceZip 'PATH_TO_YOUR_OLD_algoagentx(4).zip' or -ReferenceEnv 'PATH_TO_ORIGINAL_.env.prod'. No file was changed."
    }
}
$changes=[ordered]@{
 'LIVE_STRATEGY_HISTORY_DEFAULT_BARS'='80000'
 'LIVE_STRATEGY_HISTORY_OVERRIDE_BARS'='80000'
 'LIVE_STRATEGY_HISTORY_MAX_BARS'='200000'
 'LIVE_INCREMENTAL_ENABLED'='true'
 'LIVE_INCREMENTAL_ADAPTER_ENABLED'='true'
 'LIVE_INCREMENTAL_MONITOR_ONLY'='false'
 'LIVE_RUNNER_SEQUENTIAL_CATCHUP_ENABLED'='false'
 'LIVE_TRADELOCKER_GAP_BACKFILL_ENABLED'='false'
 'LIVE_TRADELOCKER_SESSION_GAP_RESUME_ENABLED'='false'
 'LIVE_RUNNER_DEMO_OBSERVED_GAP_RESUME_ENABLED'='false'
 'LIVE_TRADELOCKER_BOUNDARY_POLL_ENABLED'='true'
 'LIVE_TRADELOCKER_IDLE_BOUNDARY_GRACE_SECONDS'='10'
 'LIVE_RUNNER_DEDICATED_CANDLE_IDLE_ENABLED'='true'
 'LIVE_RUNNER_DEDICATED_CANDLE_PROBE_SECONDS'='5'
 'LIVE_RUNNER_DEDICATED_CANDLE_FAST_PROBES'='3'
 'LIVE_RUNNER_DEDICATED_CANDLE_MAX_IDLE_PROBE_SECONDS'='30'
 'LIVE_RUNNER_STALE_ORDER_GUARD_ENABLED'='true'
 'LIVE_RUNNER_MAX_ORDER_AGE_AFTER_CLOSE_SECONDS'='120'
}
foreach ($key in $reference.Keys) { $existing[$key]=$reference[$key] }
foreach ($key in $changes.Keys) { $existing[$key]=$changes[$key] }
# Keep all original secrets and user approval SHA; collapse duplicate keys, last value wins.
$seen=@{}; $newLines=[System.Collections.Generic.List[string]]::new()
foreach ($line in ($original -split "`r?`n")) {
    if ($line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=') {
        $key=$matches[1]
        if ($seen.ContainsKey($key)) { continue }
        $newLines.Add("$key=$($existing[$key])")
        $seen[$key]=$true
    } else { $newLines.Add($line) }
}
foreach ($key in $changes.Keys) { if (!$seen.ContainsKey($key)) { $newLines.Add("$key=$($existing[$key])") } }
# Keep validation BEFORE writing. No typed Pydantic placeholders permitted.
$text=$newLines -join "`n"
if ($text.Contains($ph)) { throw 'Unsafe placeholder remains. Aborting before writing.' }
$typed=[ordered]@{
 'ACCESS_TOKEN_EXPIRE_MINUTES'='int'; 'SMTP_PORT'='int'; 'SMTP_TIMEOUT_SECONDS'='int'; 'TWILIO_TIMEOUT_SECONDS'='int';
 'SMTP_ENABLED'='bool'; 'SMTP_USE_TLS'='bool'; 'SMTP_USE_SSL'='bool'
}
foreach ($key in $typed.Keys) {
    $value=$existing[$key]
    if (!$value) { continue }
    if ($typed[$key] -eq 'int' -and $value -notmatch '^\d+$') { throw "Invalid integer environment field: $key" }
    if ($typed[$key] -eq 'bool' -and $value -notmatch '^(true|false|1|0|yes|no)$') { throw "Invalid boolean environment field: $key" }
}
$backup="$dest.pre_stability_fix.$(Get-Date -Format 'yyyyMMdd_HHmmss')"
Copy-Item -LiteralPath $dest -Destination $backup -ErrorAction Stop
[System.IO.File]::WriteAllText($dest,($text+"`n"),[System.Text.UTF8Encoding]::new($false))
Write-Host "Local env repaired; placeholder values restored: $($missing.Count). Backup created." -ForegroundColor Green
Write-Host 'Original broker credentials, deployment SHA, and dashboard Auto Trade setting have not been changed.'
Write-Host 'Next: docker compose --env-file .env.prod config --quiet'
