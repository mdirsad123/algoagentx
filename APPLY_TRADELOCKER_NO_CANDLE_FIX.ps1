param(
    [Parameter(Mandatory = $true)]
    [string]$TargetRoot
)

$ErrorActionPreference = 'Stop'
$TargetRoot = (Resolve-Path -LiteralPath $TargetRoot).Path
$updateRoot = $PSScriptRoot
$files = @(
    'AlgoAgentXAPI\app\services\live\broker_candle_service.py',
    'AlgoAgentXAPI\app\services\live\live_tradelocker_candle_worker.py'
)

foreach ($relative in $files) {
    if (-not (Test-Path -LiteralPath (Join-Path $TargetRoot $relative))) {
        throw "Target file not found: $relative (check TargetRoot)"
    }
    if (-not (Test-Path -LiteralPath (Join-Path $updateRoot $relative))) {
        throw "Update file not found: $relative (extract the full ZIP first)"
    }
}

$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$backupRoot = Join-Path $TargetRoot "backup_tradelocker_no_candle_$stamp"
foreach ($relative in $files) {
    $oldFile = Join-Path $TargetRoot $relative
    $newFile = Join-Path $updateRoot $relative
    $backupFile = Join-Path $backupRoot $relative
    New-Item -ItemType Directory -Path (Split-Path $backupFile -Parent) -Force | Out-Null
    Copy-Item -LiteralPath $oldFile -Destination $backupFile -Force
    Copy-Item -LiteralPath $newFile -Destination $oldFile -Force
    Write-Host "UPDATED: $relative"
}
Write-Host "Backup: $backupRoot"
Write-Host 'No .env.prod, strategy, SHA, deployment, database or broker-order setting was changed.'
Write-Host 'Next: rebuild ONLY the live_tradelocker_candle_worker Docker service when it is idle.'
