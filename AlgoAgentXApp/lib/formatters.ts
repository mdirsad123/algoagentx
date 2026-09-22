export const currencySymbolForCode = (currency?: string | null): string => {
  const code = String(currency || "").toUpperCase();
  if (code === "USD") return "$";
  if (code === "INR") return "₹";
  return currency || "₹";
};

export const formatNumber = (value: number | null | undefined, digits = 2): string => {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "—";
  return new Intl.NumberFormat("en-IN", { minimumFractionDigits: digits, maximumFractionDigits: digits }).format(Number(value));
};

export const formatCurrency = (value: number | null | undefined, currencySymbol = "₹", digits = 2): string => {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "—";
  const num = Number(value);
  const sign = num < 0 ? "-" : "";
  const symbol = currencySymbol || "₹";
  return `${sign}${symbol}${formatNumber(Math.abs(num), digits)}`;
};

export const formatTradeSize = (trade: { quantity_mode?: string | null; quantity?: number | null; lot_size?: number | null }, fallbackMode?: string | null): { label: string; value: string } => {
  const mode = String(trade.quantity_mode || fallbackMode || "").toUpperCase();
  if (mode === "LOTS") return { label: "Lot", value: formatNumber(trade.lot_size, 2) };
  if (mode === "UNITS") return { label: "Units", value: formatNumber(trade.quantity, 2) };
  if (mode === "CONTRACTS") return { label: "Contracts", value: formatNumber(trade.quantity, 0) };
  return { label: "Qty", value: formatNumber(trade.quantity, 0) };
};
