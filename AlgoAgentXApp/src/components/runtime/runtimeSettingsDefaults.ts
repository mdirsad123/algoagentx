import type { RuntimeConfig } from "./runtimeSettingsTypes";

export const RUNTIME_TABS = [
  { value: "risk", label: "Risk" },
  { value: "sl_tp", label: "SL / TP" },
  { value: "execution", label: "Execution" },
  { value: "trade_management", label: "Trade Mgmt" },
  { value: "strategy_params", label: "Strategy Params" },
] as const;

export const SYSTEM_RUNTIME_DEFAULTS: RuntimeConfig = {
  risk: { initial_capital: 100000, risk_percent: 0.01, position_size_mode: "RISK_BASED", fixed_lot: 0.01, fixed_quantity: 1, max_lot_cap: 0.02, max_quantity_cap: 1 },
  sl_tp: { rr_ratio: 2, sl_mode: "ATR", atr_period: 14, atr_multiplier: 2, swing_lookback: 10, fixed_price_risk_pct: 0.002 },
  execution: { entry_mode: "NEXT_CANDLE_OPEN", exit_on_opposite_signal: true, allow_long: true, allow_short: true, max_trades_per_day: 10, max_open_positions: 1, intraday_square_off: false, square_off_time: "15:15" },
  trade_management: { break_even_enabled: false, break_even_trigger_r: 1, trailing_enabled: false, trailing_mode: "ATR_TRAIL", trail_start_r: 1.5, trail_atr_multiplier: 1, partial_exit_enabled: false, partial_exit_at_r: 1, partial_exit_percent: 0.5 },
  strategy_params: {},
};
