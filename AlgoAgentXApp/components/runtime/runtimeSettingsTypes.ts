export type RuntimeTab = "risk" | "sl_tp" | "execution" | "trade_management" | "strategy_params";

export type RuntimeFieldSchema = {
  type?: "number" | "boolean" | "select" | "text" | "string";
  label?: string;
  default?: string | number | boolean | null;
  min?: number;
  max?: number;
  step?: number;
  options?: Array<string | { label?: string; value?: string | number | boolean }>;
};

export type RuntimeConfig = {
  risk: Record<string, any>;
  execution: Record<string, any>;
  sl_tp: Record<string, any>;
  trade_management: Record<string, any>;
  strategy_params: Record<string, any>;
};
