"use client";

import { useEffect, useRef, useState } from "react";
import { AlertTriangle, ArrowRight, RefreshCw, ShieldCheck } from "lucide-react";
import { GlassCard } from "@/components/ui/GlassCard";
import { Button } from "@/components/ui/button";
import { liveTradingApi } from "@/lib/api/live-trading";
import type { CopyTradingOrder, LiveOrder } from "@/types/live-trading";

type Status = Awaited<ReturnType<typeof liveTradingApi.getManualSignalStatus>>;

export function ManualSignalVerificationPanel({
  deploymentId, mode, latestClose, primaryOrders, copyOrders, onComplete,
}: {
  deploymentId: string;
  mode?: string | null;
  latestClose?: number | null;
  primaryOrders: LiveOrder[];
  copyOrders: CopyTradingOrder[];
  onComplete: () => Promise<void>;
}) {
  const [status, setStatus] = useState<Status | null>(null);
  const [statusError, setStatusError] = useState("");
  const [side, setSide] = useState<"BUY" | "SELL">("BUY");
  const [entry, setEntry] = useState("");
  const [stop, setStop] = useState("");
  const [target, setTarget] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [sending, setSending] = useState(false);
  const [result, setResult] = useState("");
  const [lastSignalId, setLastSignalId] = useState("");
  const [lastRequestId, setLastRequestId] = useState("");
  const [error, setError] = useState("");
  const entryModified = useRef(false);
  // The page passes an inline loadSummary callback. Keep its latest value
  // without resetting the 5-second polling timer on each parent rerender.
  const onCompleteRef = useRef(onComplete);
  useEffect(() => { onCompleteRef.current = onComplete; }, [onComplete]);
  useEffect(() => {
    if (!entryModified.current && latestClose && Number.isFinite(latestClose) && latestClose > 0) {
      setEntry(String(latestClose));
    }
  }, [latestClose]);
  useEffect(() => {
    let active = true;
    setStatus(null);
    liveTradingApi.getManualSignalStatus(deploymentId)
      .then((data) => { if (active) { setStatus(data); setStatusError(""); } })
      .catch((err: unknown) => { if (active) setStatusError(err instanceof Error ? err.message : "Cannot read manual execution status"); });
    return () => { active = false; };
  }, [deploymentId]);
  useEffect(() => {
    if (!lastRequestId) return;
    let closed = false;
    const startedAt = Date.now();
    const poll = async () => {
      if (closed) return;
      try {
        const latest = await liveTradingApi.getManualSignalRequest(deploymentId, lastRequestId);
        if (closed) return;
        setLastSignalId(latest.signal_id);
        const accountSummary = latest.copy_results.map((copy) =>
          `${copy.account_id.slice(0, 8)}: ${copy.status}${copy.error ? ` (${copy.error})` : ""}`).join(" · ");
        setResult(`Request ${lastRequestId} · ${latest.status}. Primary: ${latest.primary_order_status || "pending"}. Copies FILLED/RECONCILED: ${latest.copy_filled}/${latest.copy_expected}. ${accountSummary || "No selected copies"}. ${latest.rejection_reason || "Verify against broker terminals."}`);
        await onCompleteRef.current().catch(() => undefined);
        if (["REJECTED", "ERROR"].includes(latest.status) || Date.now() - startedAt > 210000) {
          clearInterval(timer);
        }
      } catch { /* transient status read: never resubmit order */ }
    };
    const timer = setInterval(() => { void poll(); }, 5000);
    void poll();
    return () => { closed = true; clearInterval(timer); };
  }, [deploymentId, lastRequestId]);
  const activeMode = (status?.mode || mode || "").toUpperCase();
  const phrase = activeMode === "LIVE" ? "PLACE LIVE ORDER" : "PLACE DEMO ORDER";
  const entryNum = Number(entry), stopNum = Number(stop), targetNum = Number(target);
  const validPrices = [entryNum, stopNum, targetNum].every((v) => Number.isFinite(v) && v > 0)
    && (side === "BUY" ? stopNum < entryNum && entryNum < targetNum : targetNum < entryNum && entryNum < stopNum);
  const canExecute = !!status?.enabled && status.running && status.auto_trade_enabled
    && ["DEMO", "LIVE"].includes(activeMode) && validPrices && confirmation === phrase && !sending;

  const submit = async () => {
    if (!canExecute) return;
    setSending(true); setResult(""); setError("");
    // One intent, one UUID. NEVER auto-repeat a timed-out order POST.
    // crypto.randomUUID() is unavailable on plain HTTP origins. The legacy
    // deployment UI is currently served over HTTP; getRandomValues is the
    // cryptographically secure browser primitive allowed on those origins.
    const random = new Uint8Array(16);
    crypto.getRandomValues(random);
    random[6] = (random[6] & 0x0f) | 0x40;
    random[8] = (random[8] & 0x3f) | 0x80;
    const hex = [...random].map((v) => v.toString(16).padStart(2, "0")).join("");
    const requestId = `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
    try {
      const result = await liveTradingApi.createDeploymentManualSignal(deploymentId, {
        signal_type: side, price: entryNum, stop_loss: stopNum, target: targetNum,
        request_id: requestId, confirmation: phrase,
        reason: "Manual primary and copy-trading broker order verification",
      });
      setLastSignalId(result.signal?.id || "");
      setLastRequestId(requestId);
      setResult(`Request ${requestId} · Signal ${result.status}. ${result.message || "Review recent primary and copy orders."}`);
      setConfirmation("");
      await onComplete().catch(() => undefined);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Manual broker execution request failed";
      setError(`Request ${requestId}: ${message}. Submission status is UNKNOWN; check broker orders and copy history BEFORE trying again.`);
      setConfirmation("");
      await onComplete().catch(() => undefined);
    } finally {
      setSending(false);
    }
  };

  const relatedPrimary = primaryOrders.filter((o) => lastSignalId && o.signal_id === lastSignalId && (o.action || "ENTRY") === "ENTRY");
  const relatedCopies = copyOrders.filter((o) => lastSignalId && o.signal_id === lastSignalId && (o.action || "ENTRY") === "ENTRY");
  const verifiedCount = relatedCopies.filter((o) => ["FILLED", "RECONCILED"].includes(o.status)).length;
  return (
    <GlassCard className="mb-6 p-6" hoverEffect={false}>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="flex items-center gap-2 text-xl font-bold text-white"><ShieldCheck className="h-5 w-5 text-cyan-300" /> Manual Signal — Real Broker Verification</h2>
          <p className="mt-1 text-sm text-purple-200">Uses the SAME signal → risk sizing → primary broker → selected copy accounts pipeline as the strategy. This submits actual broker orders, never a dry run.</p>
        </div>
        <div className="rounded-full border border-cyan-300/30 px-3 py-1 text-xs text-cyan-100">{activeMode || "UNKNOWN"} · {status?.copy_trading_enabled ? `${status.copy_account_count} selected copies` : "Copy trading off"}</div>
      </div>
      {!status?.enabled && <p role="alert" className="mt-4 rounded-lg border border-amber-400/40 bg-amber-400/10 p-3 text-sm text-amber-100">{statusError || "Server disabled manual broker execution. Set LIVE_MANUAL_ORDER_TEST_ENABLED=true for the API container, then recreate that container."}</p>}
      {status?.enabled && (!status.running || !status.auto_trade_enabled) && <p role="alert" className="mt-4 text-sm text-amber-100">Deployment must be RUNNING and Auto Trade must be ON; no manual order will be sent otherwise.</p>}
      <div className="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <label className="text-sm text-purple-100">Side
          <select value={side} disabled={sending} onChange={(e) => { setSide(e.target.value as "BUY" | "SELL"); setConfirmation(""); }} className="mt-1 w-full rounded-lg border border-white/20 bg-purple-950 p-3 text-white"><option value="BUY">BUY / LONG</option><option value="SELL">SELL / SHORT</option></select>
        </label>
        <label className="text-sm text-purple-100">Reference entry price
          <input type="number" step="any" min="0" value={entry} disabled={sending} onChange={(e) => { entryModified.current = true; setEntry(e.target.value); }} className="mt-1 w-full rounded-lg border border-white/20 bg-purple-950 p-3 text-white" />
        </label>
        <label className="text-sm text-purple-100">Stop loss (SL)
          <input type="number" step="any" min="0" value={stop} disabled={sending} onChange={(e) => setStop(e.target.value)} className="mt-1 w-full rounded-lg border border-white/20 bg-purple-950 p-3 text-white" />
        </label>
        <label className="text-sm text-purple-100">Take profit (TP)
          <input type="number" step="any" min="0" value={target} disabled={sending} onChange={(e) => setTarget(e.target.value)} className="mt-1 w-full rounded-lg border border-white/20 bg-purple-950 p-3 text-white" />
        </label>
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-purple-200">
        <span>Reference: latest stored close {latestClose || "not loaded"}; actual market fill may differ.</span>
        {validPrices && <span>Planned reward/risk: {(Math.abs(targetNum - entryNum) / Math.abs(entryNum - stopNum)).toFixed(2)}R</span>}
        {!validPrices && <span className="text-amber-100">Enter valid SL / entry / TP on the correct side.</span>}
      </div>
      <div className="mt-4 flex flex-col gap-3 rounded-xl border border-red-300/25 bg-red-500/5 p-4 lg:flex-row lg:items-end">
        <label className="min-w-[240px] flex-1 text-sm text-white"><span className="flex items-center gap-2"><AlertTriangle className="h-4 w-4 text-amber-300" /> Type <strong>{phrase}</strong> to confirm actual market orders</span>
          <input value={confirmation} onChange={(e) => setConfirmation(e.target.value)} disabled={sending} autoComplete="off" placeholder={phrase} className="mt-2 w-full rounded-lg border border-amber-300/30 bg-purple-950 p-3 text-white" />
        </label>
        <Button disabled={!canExecute} onClick={submit} className="gap-2 bg-amber-400 text-slate-950 hover:bg-amber-300">{sending ? <><RefreshCw className="h-4 w-4 animate-spin" /> Queueing order…</> : <>Submit {side} to broker <ArrowRight className="h-4 w-4" /></>}</Button>
      </div>
      <p className="mt-3 text-xs text-purple-200">The same platform risk limits, SL/TP checks, duplicate protection and copy-trading settings apply. Do not repeat a timed-out request without checking all broker accounts.</p>
      {error && <p role="alert" className="mt-3 rounded-lg border border-red-400/30 bg-red-500/10 p-3 text-sm text-red-100">{error}</p>}
      {result && <p role="status" className="mt-3 rounded-lg border border-cyan-300/30 bg-cyan-500/10 p-3 text-sm text-cyan-100">{result}</p>}
      {lastSignalId && (
        <div className="mt-4 rounded-xl border border-white/10 p-4 text-sm text-purple-100">
          <h3 className="font-semibold text-white">Latest manual signal — broker result verification</h3>
          <p className="mt-1 text-xs text-purple-200">Confirmed copy fills: {verifiedCount} / {status?.copy_trading_enabled ? status.copy_account_count : 0} selected. A PLACED or PENDING order is not a confirmed fill. Refresh updates this from stored broker reconciliation.</p>
          <div className="mt-2 space-y-1">
            {relatedPrimary.map((o) => <p key={o.id}>Primary: <strong>{o.status}</strong> · {o.broker_order_id || "broker ID pending"}{o.error_message ? ` · ${o.error_message}` : ""}</p>)}
            {relatedCopies.map((o) => <p key={o.id}>{o.broker_account_label || o.broker_login_id || "Copy account"}: <strong>{o.status}</strong> · {o.broker_order_id || "broker ID pending"}{o.error_message ? ` · ${o.error_message}` : ""}</p>)}
            {relatedPrimary.length === 0 && <p className="text-amber-100">No primary fill is confirmed in this snapshot yet. Check Recent Orders and TradeLocker terminal.</p>}
          </div>
        </div>
      )}
    </GlassCard>
  );
}
