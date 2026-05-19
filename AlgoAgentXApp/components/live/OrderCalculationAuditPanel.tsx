"use client";

import { useState } from "react";
import { CheckCircle2, ShieldAlert } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { GlassCard } from "@/components/ui/GlassCard";

type AuditLike = Record<string, any> | null | undefined;

const pick = (...values: any[]) => values.find((value) => value !== undefined && value !== null && value !== "");
const asRecord = (value: any): Record<string, any> => (value && typeof value === "object" && !Array.isArray(value) ? value : {});

function num(value: any, digits = 4) {
  if (value === undefined || value === null || value === "") return "—";
  const n = Number(value);
  if (!Number.isFinite(n)) return String(value);
  return n.toLocaleString(undefined, { maximumFractionDigits: digits });
}

function money(value: any, currency?: string | null) {
  if (value === undefined || value === null || value === "") return "—";
  const amount = Number(value);
  if (!Number.isFinite(amount)) return String(value);
  const code = currency?.toUpperCase();
  if (code === "USD" || code === "INR" || code === "EUR" || code === "GBP") {
    return new Intl.NumberFormat(undefined, { style: "currency", currency: code, maximumFractionDigits: 2 }).format(amount);
  }
  return code ? `${amount.toLocaleString(undefined, { maximumFractionDigits: 2 })} ${code}` : amount.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

function redactSensitive(value: any): any {
  if (Array.isArray(value)) return value.map(redactSensitive);
  if (!value || typeof value !== "object") return value;
  return Object.fromEntries(Object.entries(value).map(([key, item]) => {
    const sensitive = /(password|secret|token|access_token|refresh_token|authorization|encrypted|client_secret)/i.test(key);
    return [key, sensitive ? "[REDACTED]" : redactSensitive(item)];
  }));
}

function sourceLabel(value: any) {
  const raw = String(value || "—").replaceAll("_", " ").toUpperCase();
  if (raw.includes("STRATEGY")) return "Strategy";
  if (raw.includes("BROKER EQUITY")) return "Broker Equity";
  if (raw.includes("BROKER BALANCE")) return "Broker Balance";
  if (raw.includes("FIXED")) return "Fixed %";
  if (raw.includes("ATR")) return "ATR";
  if (raw.includes("FALLBACK")) return "Fallback";
  return raw === "—" ? "—" : raw;
}

function Metric({ label, value, highlight = false }: { label: string; value: string; highlight?: boolean }) {
  return (
    <div className={`rounded-xl border p-4 ${highlight ? "border-lime-400/20 bg-lime-400/10" : "border-white/10 bg-white/5"}`}>
      <p className="text-xs font-medium uppercase tracking-wide text-purple-300">{label}</p>
      <p className="mt-2 break-words text-lg font-bold text-white">{value}</p>
    </div>
  );
}

export function OrderCalculationAuditPanel({
  preview,
  latestOrder,
  latestSignal,
  currency,
  title = "Last Order Calculation",
  subtitle = "Compact view of the latest signal, SL/TP, risk, lot/qty, and validation result.",
  showPayload = false,
  defaultExpanded = false,
}: {
  preview?: AuditLike;
  latestOrder?: AuditLike;
  latestSignal?: AuditLike;
  currency?: string | null;
  title?: string;
  subtitle?: string;
  showPayload?: boolean;
  defaultExpanded?: boolean;
}) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const order = asRecord(latestOrder);
  const raw = asRecord(order.raw_response);
  const rawSizing = asRecord(raw.sizing);
  const rawAuditPreview = asRecord(raw.audit_preview);
  const directPreview = asRecord(preview);
  const audit = Object.keys(directPreview).length
    ? directPreview
    : Object.keys(rawAuditPreview).length
      ? rawAuditPreview
      : Object.keys(rawSizing).length
        ? rawSizing
        : raw;
  const entryPlan = asRecord(pick(audit.entry_plan, rawSizing.entry_plan));
  const risk = asRecord(pick(audit.risk_metadata, audit.risk_engine, rawSizing.risk_metadata, rawSizing));
  const signal = asRecord(latestSignal);

  const hasAudit = Object.keys(audit).length > 0 || Object.keys(order).length > 0 || Object.keys(signal).length > 0;
  if (!hasAudit) {
    return (
      <GlassCard className="mb-6 p-6" hoverEffect={false}>
        <div className="flex items-start gap-3">
          <ShieldAlert className="mt-1 h-5 w-5 text-purple-200" />
          <div>
            <h2 className="text-xl font-bold text-white">{title}</h2>
            <p className="mt-1 text-sm text-purple-200">Run a dry test, strategy tick, manual signal, or broker order to see calculation details here.</p>
          </div>
        </div>
      </GlassCard>
    );
  }

  const validationStatus = String(pick(audit.validation_status, audit.status, order.status, "—"));
  const rejectedReason = pick(audit.rejected_reason, audit.reason, order.error_message, rawSizing.rejected_reason);
  const finalLot = pick(audit.final_lot_size, audit.final_lot, risk.final_lot, risk.final_lot_size, order.qty);
  const rawLot = pick(risk.raw_lot, audit.raw_lot, risk.requested_lot, audit.requested_lot);
  const maxLotCap = pick(risk.max_lot_cap, audit.max_lot_cap);
  const finalQty = pick(audit.final_quantity, audit.final_qty, risk.final_quantity, risk.final_qty, order.qty);
  const rawQty = pick(risk.raw_quantity, risk.requested_quantity, audit.raw_quantity, audit.requested_quantity);
  const explicitCap = pick(risk.cap_applied, audit.cap_applied, undefined);
  const inferredCap = (Number.isFinite(Number(rawLot)) && Number.isFinite(Number(finalLot)) && Number(rawLot) > Number(finalLot)) ||
    (Number.isFinite(Number(rawQty)) && Number.isFinite(Number(finalQty)) && Number(rawQty) > Number(finalQty));
  const capApplied = explicitCap === undefined ? inferredCap : Boolean(explicitCap);
  const brokerPayload = asRecord(pick(audit.broker_payload_preview, audit.broker_order_payload_preview, raw.broker_payload_preview, raw.request, rawSizing.broker_payload_preview));
  const safePayload = redactSensitive(brokerPayload);
  const effectiveCurrency = currency || pick(audit.account_currency, risk.account_currency, raw.currency, order.currency);

  const metrics = [
    { label: "Signal", value: String(pick(audit.side, signal.signal_type, order.side, "—")), highlight: true },
    { label: "Entry Price", value: num(pick(audit.entry_price, audit.latest_price, entryPlan.entry_price, order.entry_price, order.executed_price)) },
    { label: "Strategy SL", value: num(pick(audit.strategy_stop_loss, risk.strategy_stop_loss)) },
    { label: "Strategy TP", value: num(pick(audit.strategy_target, risk.strategy_target)) },
    { label: "Final SL Used", value: num(pick(audit.stop_loss, audit.preview_stop_loss, entryPlan.stop_loss, risk.preview_stop_loss, order.stop_loss)), highlight: true },
    { label: "Final TP Used", value: num(pick(audit.target, audit.preview_target, entryPlan.target, risk.preview_target, order.target)), highlight: true },
    { label: "SL Source", value: sourceLabel(pick(entryPlan.stop_loss_source, risk.stop_loss_source)) },
    { label: "Target Source", value: sourceLabel(pick(entryPlan.target_source, risk.target_source)) },
    { label: "Risk Points", value: num(pick(entryPlan.risk_points, risk.risk_points, audit.risk_points)) },
    { label: "Reward Points", value: num(pick(entryPlan.reward_points, risk.reward_points, audit.reward_points)) },
    { label: "RR Ratio", value: num(pick(entryPlan.rr_ratio, risk.rr_ratio)) },
    { label: "Capital Source", value: sourceLabel(pick(risk.effective_capital_source, audit.effective_capital_source)) },
    { label: "Broker Equity/Balance", value: money(pick(risk.broker_equity, audit.equity, risk.equity, risk.effective_capital, audit.effective_capital), effectiveCurrency) },
    { label: "Risk %", value: pick(risk.risk_percent, audit.risk_percent) !== undefined ? `${num(Number(pick(risk.risk_percent, audit.risk_percent)) * 100, 3)}%` : "—" },
    { label: "Risk Amount", value: money(pick(risk.risk_amount, audit.risk_amount, audit.actual_risk_amount), effectiveCurrency) },
    { label: "Position Size Mode", value: String(pick(risk.position_size_mode, audit.position_size_mode, audit.quantity_mode, "—")) },
    { label: "Raw Lot/Qty", value: num(pick(rawLot, rawQty)) },
    { label: "Final Lot/Qty", value: num(pick(finalLot, finalQty)), highlight: true },
    { label: "Max Lot Cap", value: num(maxLotCap) },
  ];

  const compactLabels = new Set(["Signal", "Entry Price", "SL Source", "Final SL Used", "Final TP Used", "Capital Source", "Risk %", "Final Lot/Qty"]);
  const compactMetrics = metrics.filter((item) => compactLabels.has(item.label));

  return (
    <GlassCard className="mb-6 overflow-hidden p-0" hoverEffect={false}>
      <div className="border-b border-white/10 bg-gradient-to-r from-cyan-500/10 via-purple-500/10 to-lime-500/10 p-6">
        <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-start">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <CheckCircle2 className="h-5 w-5 text-lime-300" />
              <h2 className="text-xl font-bold text-white">{title}</h2>
            </div>
            <p className="mt-1 text-sm text-purple-200">{subtitle}</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Badge className={validationStatus === "OK" || validationStatus === "FILLED" || validationStatus === "PLACED" ? "border-lime-400/30 bg-lime-400/20 text-lime-100" : "border-yellow-400/30 bg-yellow-400/20 text-yellow-100"}>Validation: {validationStatus}</Badge>
            <Badge className="border-cyan-400/30 bg-cyan-400/20 text-cyan-100">Cap Applied: {capApplied ? "Yes" : "No"}</Badge>
            <Badge className="border-fuchsia-400/30 bg-fuchsia-400/20 text-fuchsia-100">SL: {sourceLabel(pick(entryPlan.stop_loss_source, risk.stop_loss_source))}</Badge>
            <Badge className="border-lime-400/30 bg-lime-400/20 text-lime-100">Capital: {sourceLabel(pick(risk.effective_capital_source, audit.effective_capital_source))}</Badge>
          </div>
        </div>
        {rejectedReason && <div className="mt-4 rounded-xl border border-red-400/30 bg-red-500/10 p-4 text-sm text-red-100">Rejected / warning reason: {String(rejectedReason)}</div>}
      </div>

      <div className="p-6">
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
          {compactMetrics.map((item) => <Metric key={item.label} label={item.label} value={item.value} highlight={item.highlight} />)}
        </div>
        <div className="mt-4 flex justify-end">
          <button
            type="button"
            onClick={() => setExpanded((value) => !value)}
            className="rounded-lg border border-white/10 bg-white/5 px-4 py-2 text-sm font-semibold text-white transition hover:bg-white/10"
          >
            {expanded ? "Hide Calculation Details" : "Show Calculation Details"}
          </button>
        </div>
        {expanded && (
          <div className="mt-5 space-y-5">
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
              {metrics.map((item) => <Metric key={item.label} label={item.label} value={item.value} highlight={item.highlight} />)}
            </div>
            {showPayload && (
              <div className="rounded-2xl border border-white/10 bg-slate-950/40 p-4">
                <div className="mb-2 flex items-center justify-between gap-2">
                  <h3 className="font-semibold text-white">Developer Payload</h3>
                  <span className="text-xs text-purple-300">Sensitive credentials are redacted.</span>
                </div>
                {Object.keys(safePayload).length === 0 ? (
                  <p className="text-sm text-purple-200">No developer payload available yet.</p>
                ) : (
                  <pre className="max-h-[320px] overflow-auto whitespace-pre-wrap rounded-xl border border-white/10 bg-black/30 p-4 text-xs text-purple-100">{JSON.stringify(safePayload, null, 2)}</pre>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </GlassCard>
  );
}
