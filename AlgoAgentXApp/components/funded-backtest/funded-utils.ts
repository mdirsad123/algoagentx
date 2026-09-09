export const decimalToPercent = (value?: number | string | null): number => {
  if (value === null || value === undefined || value === "") return 0;
  return Number(value) * 100;
};

export const percentToDecimal = (value?: number | string | null): number => {
  if (value === null || value === undefined || value === "") return 0;
  return Number(value) / 100;
};

export const formatPercent = (value?: number | string | null, digits = 2): string => `${decimalToPercent(value).toFixed(digits)}%`;

export const terminalFundedStatuses = new Set([
  "PASSED", "FAILED_DAILY_DD", "FAILED_MAX_DD", "FAILED_OTHER_RULE", "INCOMPLETE",
  "PAYOUT_ELIGIBLE", "PAYOUT_READY", "SIMULATION_ERROR", "ERROR",
]);

export const isFundedRunTerminal = (status?: string | null) => terminalFundedStatuses.has(String(status || "").toUpperCase());
export const isFundedRunFailure = (status?: string | null) => ["FAILED_DAILY_DD", "FAILED_MAX_DD", "FAILED_OTHER_RULE"].includes(String(status || "").toUpperCase());
export const isFundedRunSuccess = (status?: string | null) => ["PASSED", "PAYOUT_ELIGIBLE", "PAYOUT_READY"].includes(String(status || "").toUpperCase());

export const fundedStatusLabel = (status?: string | null): string => ({
  PENDING: "Pending",
  RUNNING: "Running",
  PHASE_PASSED: "Phase Passed",
  PASSED: "Challenge Passed",
  FAILED_DAILY_DD: "Failed — Daily Drawdown",
  FAILED_MAX_DD: "Failed — Maximum Drawdown",
  FAILED_OTHER_RULE: "Failed — Rule Violation",
  INCOMPLETE: "Simulation Incomplete",
  PAYOUT_ELIGIBLE: "Payout Eligible",
  PAYOUT_READY: "Payout Ready",
  SIMULATION_ERROR: "Simulation Error",
  ERROR: "Simulation Error",
}[String(status || "").toUpperCase()] || String(status || "Unknown").replaceAll("_", " "));

export const stableFingerprint = (value: unknown): string => {
  const sortObject = (input: any): any => {
    if (Array.isArray(input)) return input.map(sortObject);
    if (input && typeof input === "object") return Object.keys(input).sort().reduce((acc, key) => { acc[key] = sortObject(input[key]); return acc; }, {} as Record<string, any>);
    return input;
  };
  return JSON.stringify(sortObject(value));
};


export const validateRiskTiers = (tiers: Array<{ min_account_return_pct?: number | null; max_account_return_pct?: number | null; risk_percent: number; is_active?: boolean }>): string | null => {
  const active = tiers.filter((t) => t.is_active !== false);
  if (active.length > 0 && active[0].min_account_return_pct != null) return "The first active risk tier must be open-ended below (Below).";
  if (active.length > 0 && active[active.length - 1].max_account_return_pct != null) return "The last active risk tier must be open-ended above (Above).";
  for (let i = 0; i < active.length; i += 1) {
    const tier = active[i];
    if (!(Number(tier.risk_percent) > 0)) return `Risk tier ${i + 1} must have risk greater than 0%.`;
    if (tier.min_account_return_pct != null && tier.max_account_return_pct != null && Number(tier.min_account_return_pct) >= Number(tier.max_account_return_pct)) return `Risk tier ${i + 1} minimum return must be below maximum return.`;
    if (i > 0) {
      const prev = active[i - 1];
      if (prev.max_account_return_pct == null) return `Risk tier ${i} cannot have an open upper bound before the final tier.`;
      if (tier.min_account_return_pct == null) return `Risk tier ${i + 1} must define a lower bound.`;
      if (Number(tier.min_account_return_pct) < Number(prev.max_account_return_pct)) return `Risk tiers ${i} and ${i + 1} overlap.`;
      if (Number(tier.min_account_return_pct) > Number(prev.max_account_return_pct)) return `Risk tiers ${i} and ${i + 1} leave a gap.`;
    }
  }
  return null;
};
