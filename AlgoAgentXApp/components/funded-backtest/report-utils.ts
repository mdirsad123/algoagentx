import { currencySymbolForCode, formatCurrency } from "@/lib/formatters";
import { fundedStatusLabel } from "@/components/funded-backtest/funded-utils";
import { formatDateIST, formatDateTimeIST } from "@/lib/timezone";

export const safeNumber = (value: unknown): number | null => {
  if (value === null || value === undefined || value === "") return null;
  const n = Number(value); return Number.isFinite(n) ? n : null;
};
export const money = (value: unknown, currency = "USD") => {
  const n = safeNumber(value); return n === null ? "—" : formatCurrency(n, currencySymbolForCode(currency));
};
export const percent = (value: unknown, digits = 2) => {
  const n = safeNumber(value); return n === null ? "—" : `${(n * 100).toFixed(digits)}%`;
};
export const numberText = (value: unknown, digits = 2) => {
  const n = safeNumber(value); return n === null ? "—" : n.toLocaleString(undefined, { minimumFractionDigits: digits, maximumFractionDigits: digits });
};
export const dateText = (value: unknown, withTime = false) => {
  if (!value) return "—";
  return withTime ? formatDateTimeIST(String(value)) : formatDateIST(String(value));
};
export const statusLabel = (status?: string | null) => fundedStatusLabel(String(status || ""));
export const statusClass = (status?: string | null) => {
  const s=String(status||"").toUpperCase();
  if (s==="PASSED" || s==="PAYOUT_READY") return "border-emerald-400/30 bg-emerald-400/10 text-emerald-100";
  if (s.startsWith("FAILED")) return "border-red-400/30 bg-red-400/10 text-red-100";
  if (s==="INCOMPLETE" || s==="PAYOUT_ELIGIBLE") return "border-amber-400/30 bg-amber-400/10 text-amber-100";
  if (s.includes("ERROR")) return "border-orange-400/30 bg-orange-400/10 text-orange-100";
  return "border-blue-400/30 bg-blue-400/10 text-blue-100";
};
export const humanize = (value: unknown) => String(value ?? "—").replaceAll("_", " ").replace(/\b\w/g, c => c.toUpperCase());
export const downloadBlob = (filename: string, blob: Blob) => { const url=URL.createObjectURL(blob); const a=document.createElement("a"); a.href=url; a.download=filename; document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url); };
