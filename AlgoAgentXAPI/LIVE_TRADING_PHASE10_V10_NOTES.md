# AlgoAgentX Live Trading Phase 10 V10

Implemented Strategy Runner on latest closed MT5 candles.

## Added

- `app/services/live/strategy_runner.py`
- `POST /api/v1/live/deployments/{deployment_id}/run-strategy-once`
- `POST /api/v1/admin/live/deployments/{deployment_id}/run-strategy-once`

## Behavior

- DEMO mode refreshes MT5 candles first.
- Runner uses `live_market_candles`, not backtest `market_data`.
- Strategy registry maps deployed strategy to a safe engine class.
- Latest closed candle generates BUY/SELL/HOLD/EXIT.
- Duplicate ENGINE signal is skipped for same candle/time/signal.
- `execute=false` performs dry run and saves signal only.
- `execute=true` routes to existing PAPER/DEMO execution engine when auto trade is enabled.
- LIVE mode remains blocked.

## Migration

No new SQL migration is required for Phase 10.
