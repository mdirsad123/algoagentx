# Run inside D:\Stock_market\algoagentx; does not change any live state.
$patterns = @(
  'RUNNER_V64_HYBRID_', 'RUNNER_INCREMENTAL_', 'RETAINED_INCREMENTAL',
  'RUNNER_GENERATE_COMPLETE', 'stage=strategy_generate',
  'stage=strategy_incremental_update', 'RUNNER_CANDLE_GAP',
  'RUNNER_DISPATCH_FINISHED', 'RUNNER_LOCK_SKIPPED',
  'RUNNER_CANDLE_CATCHUP', 'RUNNER_CANDLE_BACKFILL_WAIT',
  'TRADELOCKER_GAP_BACKFILLED', 'TRADELOCKER_GAP_UNRESOLVED',
  'TRADELOCKER_GAP_BACKFILL_ERROR', 'TRADELOCKER_GAP_BEYOND_LOOKBACK'
)
Write-Host 'AlgoAgentX V6.4 runner timing + safety markers (last 90 minutes)'
docker compose --env-file .env.prod logs --since=90m --tail=10000 live_legacy_runner_worker live_tradelocker_candle_worker |
  Select-String -Pattern $patterns
