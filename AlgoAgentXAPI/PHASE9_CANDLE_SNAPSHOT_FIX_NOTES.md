# Phase 9 Candle Snapshot Fix

This fix keeps Phase 9 scope unchanged: no chart UI, no TradingView candle fetch, no old backtest market_data mixing.

Fixes included:

- MT5 candle refresh now tries multiple MT5 history methods:
  - copy_rates_from_pos with latest closed candle first
  - copy_rates_from with current UTC time
  - copy_rates_range fallback
- MT5 symbol fallback support:
  - tries exact deployment symbol first
  - searches MT5 symbols such as XAUUSD*, *XAUUSD*, and broker suffix variants like XAUUSDm
- Better error message when MT5 terminal is connected but history is unavailable.
- Stored candle rows use the resolved MT5 symbol if broker uses a suffix.
- Frontend Market Data Snapshot shows Deployment Symbol and MT5 Symbol separately.
- Default candle refresh count reduced to 100 from frontend to avoid excessive terminal history request failures.

If MT5 still returns no data, open MT5 terminal → Market Watch → right click Show All → open the symbol/timeframe chart once, then retry Refresh Candles.
