import type { RuntimeConfig } from "./runtimeSettingsTypes";

export const mapRuntimeSettingsToBacktestPayload = (config: RuntimeConfig) => ({ ...config });

export const mapRuntimeSettingsToLiveDeploymentPayload = (config: RuntimeConfig) => ({
  runtime_config: { ...config },
  capital: Number(config.risk?.initial_capital || 0),
  risk_per_trade: Number(config.risk?.risk_percent || 0),
  rr_ratio: Number(config.sl_tp?.rr_ratio || 0),
  price_risk_pct: Number(config.sl_tp?.fixed_price_risk_pct || 0),
  max_trades_per_day: config.execution?.max_trades_per_day == null ? null : Number(config.execution.max_trades_per_day),
  max_open_positions: Number(config.execution?.max_open_positions || 1),
  allow_short: Boolean(config.execution?.allow_short),
  mt5_demo_max_lot: config.risk?.max_lot_cap == null ? null : Number(config.risk.max_lot_cap),
  fixed_quantity: Number(config.risk?.fixed_quantity || 1),
  max_quantity: Number(config.risk?.max_quantity_cap || 1),
});
