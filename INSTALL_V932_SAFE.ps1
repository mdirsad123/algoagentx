# Source-only V9.32 monitor patch installer. No Docker/DB/broker calls.
# Usage:
# powershell -ExecutionPolicy Bypass -File .\INSTALL_V932_SAFE.ps1 -TargetRoot D:\Stock_market\algoagentx -ApplyMonitorEnv
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$TargetRoot,
    [switch]$ApplyMonitorEnv
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$srcRoot = $PSScriptRoot
$target = (Resolve-Path -LiteralPath $TargetRoot).Path
if (-not (Test-Path -LiteralPath (Join-Path $target 'AlgoAgentXAPI'))) {
    throw 'TargetRoot must be the existing AlgoAgentX project root (AlgoAgentXAPI missing).'
}
$files = @(
    'AlgoAgentXAPI\app\core\config.py',
    'AlgoAgentXAPI\app\services\live\incremental_adapter_registry.py',
    'AlgoAgentXAPI\app\services\live\strategy_runner.py',
    'AlgoAgentXAPI\app\services\live\v932_hybrid_gate.py',
    'AlgoAgentXAPI\strategies\v932_original_db_source.py',
    'AlgoAgentXAPI\strategies\v932_pinned_strategy.py',
    'AlgoAgentXAPI\strategies\v932_incremental.py',
    'AlgoAgentXAPI\tests\test_v932_incremental_adapter.py',
    'AlgoAgentXAPI\app\tools\verify_v932_incremental_parity.py',
    'AlgoAgentXAPI\app\tools\audit_v932_right_edge.py'
)
$backup = Join-Path (Split-Path -Parent $target) ('algoagentx_v932_backup_' + (Get-Date -Format 'yyyyMMdd_HHmmss'))
New-Item -ItemType Directory -Path $backup -Force | Out-Null
foreach ($relative in $files) {
    $from = Join-Path $srcRoot $relative
    $to = Join-Path $target $relative
    if (-not (Test-Path -LiteralPath $from)) { throw "Package missing file: $relative" }
    $toDir = Split-Path -Parent $to
    if (-not (Test-Path -LiteralPath $toDir)) {
        New-Item -ItemType Directory -Path $toDir -Force | Out-Null
    }
    if (Test-Path -LiteralPath $to) {
        $save = Join-Path $backup $relative
        $saveDir = Split-Path -Parent $save
        New-Item -ItemType Directory -Path $saveDir -Force | Out-Null
        Copy-Item -LiteralPath $to -Destination $save -Force
    }
    Copy-Item -LiteralPath $from -Destination $to -Force
    Write-Host "Copied $relative"
}
if ($ApplyMonitorEnv) {
    $envPath = Join-Path $target '.env.prod'
    if (-not (Test-Path -LiteralPath $envPath)) { throw 'Target .env.prod is missing; merge V932_DEMO_INCREMENTAL_ENV.txt manually.' }
    Copy-Item -LiteralPath $envPath -Destination (Join-Path $backup '.env.prod') -Force
    $content = [System.IO.File]::ReadAllText($envPath)
    $values = [ordered]@{
        'LIVE_INCREMENTAL_ENABLED'='true'
        'LIVE_INCREMENTAL_ADAPTER_ENABLED'='true'
        'LIVE_INCREMENTAL_MONITOR_ONLY'='true'
        'LIVE_INCREMENTAL_PARITY_APPROVED'='false'
        'LIVE_INCREMENTAL_AUTHORIZED_SOURCE_SHA256'='a63659f9b6a4d0302165b94e9889b5da35e6fd2f4020d5893516ba4def9ad512'
        'LIVE_INCREMENTAL_MAX_ADVANCES'='48'
        'LIVE_INCREMENTAL_REQUIRE_ADAPTER_INSTRUMENTS'='XAUUSD,XAUUSD.X'
        'LIVE_STRATEGY_HISTORY_DEFAULT_BARS'='80000'
        'LIVE_STRATEGY_HISTORY_MAX_BARS'='200000'
        'LIVE_STRATEGY_HISTORY_OVERRIDE_BARS'='80000'
    }
    $lines = [System.Collections.Generic.List[string]]::new()
    foreach ($line in ($content -split '\r?\n')) { $lines.Add($line) }
    foreach ($key in $values.Keys) {
        $matching = @($lines | Where-Object { $_ -match ('^\s*' + [regex]::Escape($key) + '\s*=') })
        if ($matching.Count -gt 1) { throw "Duplicate setting: $key. Restore .env.prod from backup and fix duplicates manually." }
        $entry = "${key}=$($values[$key])"
        if ($matching.Count -eq 1) {
            for ($i=0; $i -lt $lines.Count; $i++) {
                if ($lines[$i] -match ('^\s*' + [regex]::Escape($key) + '\s*=')) { $lines[$i]=$entry; break }
            }
        } else { $lines.Add($entry) }
    }
    [System.IO.File]::WriteAllText($envPath, (($lines -join "`r`n").TrimEnd() + "`r`n"), [System.Text.UTF8Encoding]::new($false))
    Write-Host 'Updated .env.prod ONLY for V9.32 DEMO MONITOR (no broker orders).'
}
Write-Host ''
Write-Host "Backup folder: $backup"
Write-Host 'No Docker containers were restarted; no database records or broker orders were touched.'
Write-Host 'Next: review README_V932_INCREMENTAL_DEMO.md and rebuild only the idle strategy runners.'
Write-Warning 'V9.32 order mode is HARD-BLOCKED due to the demonstrated right-edge historical-vs-live signal discrepancy.'
