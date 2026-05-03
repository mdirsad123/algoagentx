"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { GlassCard } from "@/components/ui/GlassCard";
import { PageHeader } from "@/components/ui/PageHeader";
import { PageShell } from "@/components/ui/PageShell";
import { useToast } from "@/components/shared/toast";
import { liveTradingApi } from "@/lib/api/live-trading";
import type { BrokerAccount, BrokerSymbol, LiveOrderPreview } from "@/types/live-trading";

const TIMEFRAME_OPTIONS = ["M1", "M5", "M15", "M30", "H1", "H4", "D1"];
const UPSTOX_TIMEFRAME_OPTIONS = ["1m", "5m", "15m", "30m", "1h", "1d"];

const FALLBACK_SYMBOL_OPTIONS = [
  "XAUUSD",
  "XAUUSDm",
  "BTCUSD",
  "BTCUSDm",
  "EURUSD",
  "GBPUSD",
  "USDJPY",
  "US30",
  "NAS100",
];


export default function LiveDeploymentSettingsPage() {
  const { deploymentId } = useParams<{ deploymentId: string }>();
  const router = useRouter();
  const { showToast } = useToast();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [brokers, setBrokers] = useState<BrokerAccount[]>([]);
  const [symbolOptions, setSymbolOptions] = useState<BrokerSymbol[]>([]);
  const [loadingSymbols, setLoadingSymbols] = useState(false);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewEntryPrice, setPreviewEntryPrice] = useState(4630);
  const [previewStopLoss, setPreviewStopLoss] = useState(4625);
  const [riskPreview, setRiskPreview] = useState<LiveOrderPreview | null>(null);
  const [form, setForm] = useState({
    name: "",
    instrument: "",
    timeframe: "",
    mode: "PAPER" as "PAPER" | "DEMO",
    broker_account_id: "" as string,
    capital: 100000,
    risk_per_trade: 0.01,
    rr_ratio: 2,
    price_risk_pct: 0.002,
    max_daily_loss: 5000,
    max_trades_per_day: 10,
    max_open_positions: 1,
    allow_short: true,
    auto_trade_enabled: false,
    mt5_demo_max_lot: 0.02,
    broker_symbol: "",
    instrument_key: "",
    exchange: "NSE_EQ",
    segment: "EQ",
    product_type: "MIS",
    order_variety: "REGULAR",
    quantity_mode: "FIXED_QTY",
    fixed_quantity: 1,
    max_quantity: 1,
    max_order_value: 5000,
    square_off_time: "15:15",
    upstox_order_confirmed: false,
  });

  const connectedDemoBrokers = useMemo(() => brokers.filter((broker) => broker.mode === "DEMO" && broker.status === "CONNECTED"), [brokers]);
  const selectedBroker = useMemo(() => brokers.find((broker) => broker.id === form.broker_account_id), [brokers, form.broker_account_id]);
  const isUpstox = (selectedBroker?.broker_name || selectedBroker?.broker_code || "").toUpperCase() === "UPSTOX";

  useEffect(() => {
    const loadSymbols = async () => {
      if (form.mode !== "DEMO" || !form.broker_account_id) {
        setSymbolOptions([]);
        return;
      }
      try {
        setLoadingSymbols(true);
        const query = form.instrument ? form.instrument.replace(/m$/i, "").slice(0, 6) : "";
        const rows = await liveTradingApi.listBrokerSymbols(form.broker_account_id, query, 200);
        setSymbolOptions(rows.filter((row) => row?.symbol && row.success !== false));
      } catch {
        setSymbolOptions([]);
      } finally {
        setLoadingSymbols(false);
      }
    };
    loadSymbols();
  }, [form.mode, form.broker_account_id]);

  useEffect(() => {
    const load = async () => {
      try {
        const [row, brokerRows] = await Promise.all([
          liveTradingApi.getDeployment(deploymentId),
          liveTradingApi.listBrokerAccounts(),
        ]);
        setBrokers(brokerRows);
        setForm({
          name: row.name,
          instrument: row.instrument,
          timeframe: row.timeframe,
          mode: (row.mode === "DEMO" ? "DEMO" : "PAPER") as "PAPER" | "DEMO",
          broker_account_id: row.broker_account_id || "",
          capital: Number(row.capital),
          risk_per_trade: Number(row.risk_per_trade),
          rr_ratio: Number(row.rr_ratio),
          price_risk_pct: Number(row.price_risk_pct),
          max_daily_loss: Number(row.max_daily_loss),
          max_trades_per_day: Number(row.max_trades_per_day),
          max_open_positions: Number(row.max_open_positions),
          allow_short: Boolean(row.allow_short),
          auto_trade_enabled: Boolean(row.auto_trade_enabled),
          mt5_demo_max_lot: Number(row.mt5_demo_max_lot ?? 0.02),
          broker_symbol: row.broker_symbol || "",
          instrument_key: row.instrument_key || "",
          exchange: row.exchange || "NSE_EQ",
          segment: row.segment || "EQ",
          product_type: row.product_type || "MIS",
          order_variety: row.order_variety || "REGULAR",
          quantity_mode: row.quantity_mode || "FIXED_QTY",
          fixed_quantity: Number(row.fixed_quantity ?? 1),
          max_quantity: Number(row.max_quantity ?? 1),
          max_order_value: Number(row.max_order_value ?? 5000),
          square_off_time: row.square_off_time || "15:15",
          upstox_order_confirmed: Boolean(row.upstox_order_confirmed),
        });
      } catch (error: any) { showToast(error.message || "Failed to load settings", "error"); }
      finally { setLoading(false); }
    };
    if (deploymentId) load();
  }, [deploymentId]);

  const runRiskPreview = async () => {
    if (!form.instrument) {
      showToast("Select instrument before preview", "error");
      return;
    }
    try {
      setPreviewLoading(true);
      const result = await liveTradingApi.previewLiveOrder({
        deployment_id: deploymentId,
        symbol: form.instrument,
        side: "BUY",
        entry_price: Number(previewEntryPrice),
        stop_loss: Number(previewStopLoss),
        runtime_config: {
          risk: {
            initial_capital: Number(form.capital),
            risk_percent: Number(form.risk_per_trade),
            max_lot_cap: form.mt5_demo_max_lot ? Number(form.mt5_demo_max_lot) : null,
            max_quantity_cap: form.max_quantity ? Number(form.max_quantity) : null,
          },
          sl_tp: {
            rr_ratio: Number(form.rr_ratio),
            fixed_price_risk_pct: Number(form.price_risk_pct),
          },
          execution: {
            max_trades_per_day: Number(form.max_trades_per_day),
            max_open_positions: Number(form.max_open_positions),
            allow_short: Boolean(form.allow_short),
          },
        },
      });
      setRiskPreview(result as LiveOrderPreview);
    } catch (error: any) {
      showToast(error?.message || "Risk preview failed", "error");
    } finally {
      setPreviewLoading(false);
    }
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (form.mode === "DEMO" && !form.broker_account_id) {
      showToast("DEMO mode requires a connected broker", "error");
      return;
    }
    try {
      setSaving(true);
      await liveTradingApi.updateDeployment(deploymentId, { ...form, broker_account_id: form.broker_account_id || null, broker_symbol: form.broker_symbol || null, instrument_key: form.instrument_key || null });
      showToast("Deployment settings updated", "success");
      router.push(`/live-trading/${deploymentId}`);
    } catch (error: any) { showToast(error.message || "Failed to update settings", "error"); }
    finally { setSaving(false); }
  };

  return (
    <PageShell>
      <PageHeader title="Deployment Settings" subtitle="Edit broker, mode, risk, and deployment configuration." actions={<Link href={`/live-trading/${deploymentId}`}><Button variant="outline" className="gap-2 border-white/10 bg-white/5 text-white hover:bg-white/10"><ArrowLeft className="h-4 w-4" />Back</Button></Link>} />
      <GlassCard className="p-6" hoverEffect={false}>
        {loading ? <p className="text-purple-100">Loading settings...</p> : (
          <form onSubmit={submit} className="space-y-6">
            <div className="rounded-xl border border-lime-300/20 bg-lime-300/10 p-4 text-sm text-lime-100">
              PAPER can run without broker. DEMO requires a connected broker. Demo is recommended before live execution. Upstox orders may place real trades in your broker account; use small quantity first. Order sizing uses instrument master and risk engine.
            </div>
            <div className="rounded-2xl border border-cyan-300/20 bg-cyan-300/10 p-5 text-sm text-cyan-50">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
                <div>
                  <h3 className="text-base font-black text-white">Risk Engine Order Preview</h3>
                  <p className="mt-1 text-xs text-amber-100">Preview final lot/quantity before enabling deployment. Demo recommended for all live execution testing.</p>
                  <p className="mt-1 text-xs text-cyan-100">Order sizing uses Instrument Master + the same shared risk engine as backtest. DEMO/LIVE will reject if instrument spec is missing.</p>
                </div>
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                  <label className="space-y-1 text-xs text-cyan-100">Preview Entry
                    <input type="number" step="0.01" className="w-full rounded-xl border border-white/10 bg-slate-950/60 px-3 py-2 text-white outline-none" value={previewEntryPrice} onChange={(e) => setPreviewEntryPrice(Number(e.target.value))} />
                  </label>
                  <label className="space-y-1 text-xs text-cyan-100">Preview SL
                    <input type="number" step="0.01" className="w-full rounded-xl border border-white/10 bg-slate-950/60 px-3 py-2 text-white outline-none" value={previewStopLoss} onChange={(e) => setPreviewStopLoss(Number(e.target.value))} />
                  </label>
                  <Button type="button" disabled={previewLoading} onClick={runRiskPreview} className="mt-5 border-0 bg-cyan-400 text-slate-950 hover:bg-cyan-300">{previewLoading ? "Previewing..." : "Preview Sizing"}</Button>
                </div>
              </div>
              {riskPreview && (
                <div className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-4 xl:grid-cols-7">
                  <div className="rounded-xl border border-white/10 bg-white/5 p-3"><p className="text-[10px] uppercase text-cyan-200">Status</p><p className={riskPreview.validation_status === "OK" ? "font-bold text-lime-200" : "font-bold text-rose-200"}>{riskPreview.validation_status || "—"}</p></div>
                  <div className="rounded-xl border border-white/10 bg-white/5 p-3"><p className="text-[10px] uppercase text-cyan-200">Currency</p><p className="font-bold text-white">{riskPreview.account_currency || "—"}</p></div>
                  <div className="rounded-xl border border-white/10 bg-white/5 p-3"><p className="text-[10px] uppercase text-cyan-200">Qty Mode</p><p className="font-bold text-white">{riskPreview.quantity_mode || "—"}</p></div>
                  <div className="rounded-xl border border-white/10 bg-white/5 p-3"><p className="text-[10px] uppercase text-cyan-200">Lot / Qty</p><p className="font-bold text-white">{riskPreview.quantity_mode === "LOTS" ? (riskPreview.final_lot_size ?? "—") : (riskPreview.final_quantity ?? "—")}</p></div>
                  <div className="rounded-xl border border-white/10 bg-white/5 p-3"><p className="text-[10px] uppercase text-cyan-200">Actual Risk</p><p className="font-bold text-white">{riskPreview.currency_symbol || ""}{riskPreview.actual_risk_amount ?? "—"}</p></div>
                  <div className="rounded-xl border border-white/10 bg-white/5 p-3"><p className="text-[10px] uppercase text-cyan-200">SL / TP</p><p className="font-bold text-white">{riskPreview.stop_loss ?? "—"} / {riskPreview.target ?? "—"}</p></div>
                  <div className="rounded-xl border border-white/10 bg-white/5 p-3"><p className="text-[10px] uppercase text-cyan-200">Broker Payload</p><p className="truncate font-bold text-white">{riskPreview.quantity_mode === "LOTS" ? `volume=${(riskPreview.broker_order_payload_preview as any)?.volume ?? "—"}` : `qty=${(riskPreview.broker_order_payload_preview as any)?.quantity ?? "—"}`}</p></div>
                </div>
              )}
              {riskPreview?.validation_status === "REJECTED" && <p className="mt-3 rounded-xl border border-rose-300/20 bg-rose-500/10 p-3 text-rose-100">{riskPreview.rejected_reason || "Risk engine rejected this order."}</p>}
            </div>
            <div className="grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-3">
              <label className="space-y-2 text-sm text-purple-100">Name<input className="w-full rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-white outline-none" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></label>
              <label className="space-y-2 text-sm text-purple-100">Mode<select className="w-full rounded-xl border border-white/10 bg-slate-950 px-3 py-2 text-white outline-none" value={form.mode} onChange={(e) => setForm({ ...form, mode: e.target.value as "PAPER" | "DEMO", broker_account_id: e.target.value === "PAPER" ? "" : form.broker_account_id })}><option value="PAPER">PAPER</option><option value="DEMO">DEMO / Broker</option></select></label>
              <label className="space-y-2 text-sm text-purple-100">Broker Account<select disabled={form.mode !== "DEMO"} className="w-full rounded-xl border border-white/10 bg-slate-950 px-3 py-2 text-white outline-none disabled:opacity-50" value={form.broker_account_id} onChange={(e) => setForm({ ...form, broker_account_id: e.target.value })}><option value="">Select connected broker</option>{connectedDemoBrokers.map((broker) => <option key={broker.id} value={broker.id}>{broker.account_label} • {broker.login_id || broker.broker_name} • {broker.server_name || broker.broker_code || broker.broker_name}</option>)}</select></label>
              <label className="space-y-2 text-sm text-purple-100">Instrument
                {form.mode === "DEMO" && form.broker_account_id ? (
                  <select disabled={isUpstox} className="w-full rounded-xl border border-white/10 bg-slate-950 px-3 py-2 text-white outline-none disabled:opacity-50" value={form.instrument} onChange={(e) => setForm({ ...form, instrument: e.target.value.toUpperCase() })}>
                    <option value={form.instrument}>{form.instrument || (loadingSymbols ? "Loading MT5 symbols..." : "Select symbol")}</option>
                    {[...new Set([...symbolOptions.map((item) => item.symbol), ...FALLBACK_SYMBOL_OPTIONS])].filter(Boolean).map((symbol) => (
                      <option key={symbol} value={symbol}>{symbol}</option>
                    ))}
                  </select>
                ) : (
                  <input className="w-full rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-white outline-none" value={form.instrument} onChange={(e) => setForm({ ...form, instrument: e.target.value.toUpperCase() })} />
                )}
              </label>
              <label className="space-y-2 text-sm text-purple-100">Timeframe
                <select className="w-full rounded-xl border border-white/10 bg-slate-950 px-3 py-2 text-white outline-none" value={form.timeframe} onChange={(e) => setForm({ ...form, timeframe: isUpstox ? e.target.value : e.target.value.toUpperCase() })}>
                  {[...new Set([form.timeframe, ...(isUpstox ? UPSTOX_TIMEFRAME_OPTIONS : TIMEFRAME_OPTIONS)])].filter(Boolean).map((tf) => <option key={tf} value={tf}>{tf}</option>)}
                </select>
              </label>
              <label className="space-y-2 text-sm text-purple-100">MT5 DEMO max lot<input type="number" step="0.01" min="0.01" className="w-full rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-white outline-none" value={form.mt5_demo_max_lot} onChange={(e) => setForm({ ...form, mt5_demo_max_lot: Number(e.target.value) })} /></label>
              {isUpstox && <>
              <label className="space-y-2 text-sm text-purple-100">Upstox Instrument Key<input className="w-full rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-white outline-none" value={form.instrument_key} onChange={(e) => setForm({ ...form, instrument_key: e.target.value, broker_symbol: e.target.value })} placeholder="NSE_EQ|INE040A01034" /></label>
              <label className="space-y-2 text-sm text-purple-100">Exchange<input className="w-full rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-white outline-none" value={form.exchange} onChange={(e) => setForm({ ...form, exchange: e.target.value.toUpperCase() })} /></label>
              <label className="space-y-2 text-sm text-purple-100">Segment<input className="w-full rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-white outline-none" value={form.segment} onChange={(e) => setForm({ ...form, segment: e.target.value.toUpperCase() })} /></label>
              <label className="space-y-2 text-sm text-purple-100">Product Type<select className="w-full rounded-xl border border-white/10 bg-slate-950 px-3 py-2 text-white outline-none" value={form.product_type} onChange={(e) => setForm({ ...form, product_type: e.target.value })}><option value="MIS">MIS / Intraday</option><option value="CNC">CNC / Delivery</option></select></label>
              <label className="space-y-2 text-sm text-purple-100">Quantity Mode<select className="w-full rounded-xl border border-white/10 bg-slate-950 px-3 py-2 text-white outline-none" value={form.quantity_mode} onChange={(e) => setForm({ ...form, quantity_mode: e.target.value })}><option value="FIXED_QTY">Fixed Quantity</option><option value="RISK_BASED">Risk Based</option></select></label>
              <label className="space-y-2 text-sm text-purple-100">Fixed Qty<input type="number" step="1" min="1" className="w-full rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-white outline-none" value={form.fixed_quantity} onChange={(e) => setForm({ ...form, fixed_quantity: Number(e.target.value) })} /></label>
              <label className="space-y-2 text-sm text-purple-100">Max Qty<input type="number" step="1" min="1" className="w-full rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-white outline-none" value={form.max_quantity} onChange={(e) => setForm({ ...form, max_quantity: Number(e.target.value) })} /></label>
              <label className="space-y-2 text-sm text-purple-100">Max Order Value<input type="number" step="1" min="1" className="w-full rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-white outline-none" value={form.max_order_value} onChange={(e) => setForm({ ...form, max_order_value: Number(e.target.value) })} /></label>
              <label className="space-y-2 text-sm text-purple-100">Square-off Time<input className="w-full rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-white outline-none" value={form.square_off_time} onChange={(e) => setForm({ ...form, square_off_time: e.target.value })} /></label>
              </>}
              <label className="space-y-2 text-sm text-purple-100">Capital<input type="number" className="w-full rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-white outline-none" value={form.capital} onChange={(e) => setForm({ ...form, capital: Number(e.target.value) })} /></label>
              <label className="space-y-2 text-sm text-purple-100">Risk per trade<input type="number" step="0.001" className="w-full rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-white outline-none" value={form.risk_per_trade} onChange={(e) => setForm({ ...form, risk_per_trade: Number(e.target.value) })} /></label>
              <label className="space-y-2 text-sm text-purple-100">RR ratio<input type="number" step="0.1" className="w-full rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-white outline-none" value={form.rr_ratio} onChange={(e) => setForm({ ...form, rr_ratio: Number(e.target.value) })} /></label>
              <label className="space-y-2 text-sm text-purple-100">Price risk %<input type="number" step="0.0001" className="w-full rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-white outline-none" value={form.price_risk_pct} onChange={(e) => setForm({ ...form, price_risk_pct: Number(e.target.value) })} /></label>
              <label className="space-y-2 text-sm text-purple-100">Max daily loss<input type="number" className="w-full rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-white outline-none" value={form.max_daily_loss} onChange={(e) => setForm({ ...form, max_daily_loss: Number(e.target.value) })} /></label>
              <label className="space-y-2 text-sm text-purple-100">Max trades per day<input type="number" className="w-full rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-white outline-none" value={form.max_trades_per_day} onChange={(e) => setForm({ ...form, max_trades_per_day: Number(e.target.value) })} /></label>
              <label className="space-y-2 text-sm text-purple-100">Max open positions<input type="number" className="w-full rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-white outline-none" value={form.max_open_positions} onChange={(e) => setForm({ ...form, max_open_positions: Number(e.target.value) })} /></label>
            </div>
            <div className="flex flex-wrap gap-4 rounded-xl border border-white/10 bg-white/5 p-4"><label className="flex items-center gap-2 text-sm text-purple-100"><input type="checkbox" checked={form.allow_short} onChange={(e) => setForm({ ...form, allow_short: e.target.checked })} />Allow short</label><label className="flex items-center gap-2 text-sm text-purple-100"><input type="checkbox" checked={form.auto_trade_enabled} onChange={(e) => setForm({ ...form, auto_trade_enabled: e.target.checked })} />Auto trade enabled</label>{isUpstox && <label className="flex items-center gap-2 text-sm text-yellow-100"><input type="checkbox" checked={form.upstox_order_confirmed} onChange={(e) => setForm({ ...form, upstox_order_confirmed: e.target.checked })} />I understand Upstox orders may place real trades</label>}</div>
            <Button disabled={saving} className="border-0 bg-gradient-to-r from-lime-400 to-emerald-500 text-slate-950 hover:from-lime-300 hover:to-emerald-400">{saving ? "Saving..." : "Save Settings"}</Button>
          </form>
        )}
      </GlassCard>
    </PageShell>
  );
}
