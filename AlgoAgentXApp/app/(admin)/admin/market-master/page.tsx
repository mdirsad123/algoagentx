"use client";

import { useEffect, useMemo, useState } from "react";
import { Database, Edit, Loader2, Plus, RefreshCcw, Save, Search, X } from "lucide-react";
import { toast } from "sonner";

import { adminApi, MarketMasterAssetClass, MarketMasterInstrument, MarketMasterInstrumentPayload } from "@/lib/api/admin";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { GlassCard } from "@/components/ui/GlassCard";
import { PageHeader } from "@/components/ui/PageHeader";

const fieldClass =
  "w-full rounded-xl border border-border/60 bg-card/25 px-3 py-2 text-sm text-foreground outline-none transition-colors placeholder:text-muted-foreground focus:border-primary/50 focus:ring-2 focus:ring-primary/35";

const quantityModes = ["SHARES", "LOTS", "UNITS", "CONTRACTS"];
const exchangeOptions = ["GLOBAL", "MT5", "BINANCE", "NSE", "BSE", "UPSTOX", "ZERODHA", "ANGEL", "DHAN", "GROWW", "BYBIT", "OKX"];
const assetClassOptions = ["FOREX", "METAL", "CRYPTO", "INDIAN_EQUITY", "INDIAN_INDEX", "FUTURES", "COMMODITY"];
const currencyOptions = ["USD", "INR", "EUR", "GBP", "JPY", "USDT"];
const currencySymbols: Record<string, string> = { USD: "$", INR: "₹", EUR: "€", GBP: "£", JPY: "¥", USDT: "$" };

const instrumentPresets: Array<{ label: string; payload: MarketMasterInstrumentPayload }> = [
  { label: "XAUUSD · Gold vs US Dollar · MT5 suffix m", payload: { symbol: "XAUUSD", name: "Gold vs US Dollar", exchange: "MT5", market: "METAL", instrument_type: "METAL", asset_class: "METAL", base_currency: "XAU", quote_currency: "USD", account_currency: "USD", currency_symbol: "$", price_unit_name: "points", quantity_mode: "LOTS", contract_size: 100, tick_size: 0.01, tick_value_per_lot: 1, pip_size: 0.01, min_lot: 0.01, lot_step: 0.01, price_precision: 2, quantity_precision: 2, broker_symbol: "XAUUSDm", is_active: true, is_tradeable_backtest: true, is_tradeable_live: true } },
  { label: "XAGUSD · Silver vs US Dollar · MT5 suffix m", payload: { symbol: "XAGUSD", name: "Silver vs US Dollar", exchange: "MT5", market: "METAL", instrument_type: "METAL", asset_class: "METAL", base_currency: "XAG", quote_currency: "USD", account_currency: "USD", currency_symbol: "$", price_unit_name: "points", quantity_mode: "LOTS", contract_size: 5000, tick_size: 0.001, tick_value_per_lot: 5, pip_size: 0.001, min_lot: 0.01, lot_step: 0.01, price_precision: 3, quantity_precision: 2, broker_symbol: "XAGUSDm", is_active: true, is_tradeable_backtest: true, is_tradeable_live: true } },
  { label: "BTCUSD · Bitcoin vs US Dollar · MT5 suffix m", payload: { symbol: "BTCUSD", name: "Bitcoin vs US Dollar", exchange: "MT5", market: "CRYPTO", instrument_type: "CRYPTO", asset_class: "CRYPTO", base_currency: "BTC", quote_currency: "USD", account_currency: "USD", currency_symbol: "$", price_unit_name: "points", quantity_mode: "LOTS", contract_size: 1, tick_size: 0.01, tick_value_per_lot: 0.01, pip_size: 0.01, min_lot: 0.01, lot_step: 0.01, price_precision: 2, quantity_precision: 2, broker_symbol: "BTCUSDm", is_active: true, is_tradeable_backtest: true, is_tradeable_live: true } },
  { label: "GBPUSD · Pound vs US Dollar · MT5 suffix m", payload: { symbol: "GBPUSD", name: "Great Britain Pound vs US Dollar", exchange: "MT5", market: "FOREX", instrument_type: "FOREX", asset_class: "FOREX", base_currency: "GBP", quote_currency: "USD", account_currency: "USD", currency_symbol: "$", price_unit_name: "pips", quantity_mode: "LOTS", contract_size: 100000, tick_size: 0.00001, tick_value_per_lot: 1, pip_size: 0.0001, min_lot: 0.01, lot_step: 0.01, price_precision: 5, quantity_precision: 2, broker_symbol: "GBPUSDm", is_active: true, is_tradeable_backtest: true, is_tradeable_live: true } },
  { label: "GBPJPY · Pound vs Japanese Yen · MT5 suffix m", payload: { symbol: "GBPJPY", name: "Great Britain Pound vs Japanese Yen", exchange: "MT5", market: "FOREX", instrument_type: "FOREX", asset_class: "FOREX", base_currency: "GBP", quote_currency: "JPY", account_currency: "USD", currency_symbol: "$", price_unit_name: "pips", quantity_mode: "LOTS", contract_size: 100000, tick_size: 0.001, tick_value_per_lot: 1, pip_size: 0.01, min_lot: 0.01, lot_step: 0.01, price_precision: 3, quantity_precision: 2, broker_symbol: "GBPJPYm", is_active: true, is_tradeable_backtest: true, is_tradeable_live: true } },
  { label: "USDJPY · US Dollar vs Japanese Yen · MT5 suffix m", payload: { symbol: "USDJPY", name: "US Dollar vs Japanese Yen", exchange: "MT5", market: "FOREX", instrument_type: "FOREX", asset_class: "FOREX", base_currency: "USD", quote_currency: "JPY", account_currency: "USD", currency_symbol: "$", price_unit_name: "pips", quantity_mode: "LOTS", contract_size: 100000, tick_size: 0.001, tick_value_per_lot: 1, pip_size: 0.01, min_lot: 0.01, lot_step: 0.01, price_precision: 3, quantity_precision: 2, broker_symbol: "USDJPYm", is_active: true, is_tradeable_backtest: true, is_tradeable_live: true } },
  { label: "EURUSD · Euro vs US Dollar · MT5 suffix m", payload: { symbol: "EURUSD", name: "Euro vs US Dollar", exchange: "MT5", market: "FOREX", instrument_type: "FOREX", asset_class: "FOREX", base_currency: "EUR", quote_currency: "USD", account_currency: "USD", currency_symbol: "$", price_unit_name: "pips", quantity_mode: "LOTS", contract_size: 100000, tick_size: 0.00001, tick_value_per_lot: 1, pip_size: 0.0001, min_lot: 0.01, lot_step: 0.01, price_precision: 5, quantity_precision: 2, broker_symbol: "EURUSDm", is_active: true, is_tradeable_backtest: true, is_tradeable_live: true } },
  { label: "EURCAD · Euro vs Canadian Dollar · MT5 suffix m", payload: { symbol: "EURCAD", name: "Euro vs Canadian Dollar", exchange: "MT5", market: "FOREX", instrument_type: "FOREX", asset_class: "FOREX", base_currency: "EUR", quote_currency: "CAD", account_currency: "USD", currency_symbol: "$", price_unit_name: "pips", quantity_mode: "LOTS", contract_size: 100000, tick_size: 0.00001, tick_value_per_lot: 1, pip_size: 0.0001, min_lot: 0.01, lot_step: 0.01, price_precision: 5, quantity_precision: 2, broker_symbol: "EURCADm", is_active: true, is_tradeable_backtest: true, is_tradeable_live: true } },
];

const editableFields: Array<{ key: keyof MarketMasterInstrumentPayload; label: string; type?: "text" | "number" | "checkbox" | "select"; options?: string[] }> = [
  { key: "exchange", label: "Exchange / Data Source", type: "select", options: exchangeOptions },
  { key: "asset_class", label: "Asset Class", type: "select", options: assetClassOptions },
  { key: "market", label: "Market", type: "select", options: assetClassOptions },
  { key: "instrument_type", label: "Instrument Type", type: "select", options: assetClassOptions },
  { key: "base_currency", label: "Base Currency" },
  { key: "quote_currency", label: "Quote Currency" },
  { key: "broker_symbol", label: "Broker Symbol" },
  { key: "account_currency", label: "Account Currency", type: "select", options: currencyOptions },
  { key: "currency_symbol", label: "Currency Symbol", type: "select", options: ["$", "₹", "€", "£", "¥"] },
  { key: "price_unit_name", label: "Price Unit", type: "select", options: ["points", "pips", "rupees", "ticks"] },
  { key: "quantity_mode", label: "Quantity Mode", type: "select", options: quantityModes },
  { key: "contract_size", label: "Contract Size", type: "number" },
  { key: "tick_size", label: "Tick Size", type: "number" },
  { key: "tick_value_per_lot", label: "Tick Value / Lot", type: "number" },
  { key: "pip_size", label: "Pip Size", type: "number" },
  { key: "min_lot", label: "Min Lot", type: "number" },
  { key: "max_lot", label: "Max Lot", type: "number" },
  { key: "lot_step", label: "Lot Step", type: "number" },
  { key: "min_quantity", label: "Min Quantity", type: "number" },
  { key: "quantity_step", label: "Quantity Step", type: "number" },
  { key: "price_precision", label: "Price Precision", type: "number" },
  { key: "quantity_precision", label: "Quantity Precision", type: "number" },
  { key: "is_active", label: "Active", type: "checkbox" },
  { key: "is_tradeable_backtest", label: "Backtest Tradeable", type: "checkbox" },
  { key: "is_tradeable_live", label: "Live Tradeable", type: "checkbox" },
];

function getErrorMessage(error: any, fallback: string) {
  return error?.response?.data?.detail || error?.response?.data?.message || error?.message || fallback;
}

function formatValue(value: any) {
  if (value === null || value === undefined || value === "") return "—";
  return String(value);
}

function normalizePatch(values: MarketMasterInstrumentPayload): MarketMasterInstrumentPayload {
  const next: MarketMasterInstrumentPayload = { ...values };
  for (const key of Object.keys(next) as Array<keyof MarketMasterInstrumentPayload>) {
    const value = next[key];
    if (value === "") (next as any)[key] = null;
  }
  return next;
}

export default function AdminMarketMasterPage() {
  const [items, setItems] = useState<MarketMasterInstrument[]>([]);
  const [assetClasses, setAssetClasses] = useState<MarketMasterAssetClass[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [editing, setEditing] = useState<MarketMasterInstrument | null>(null);
  const [form, setForm] = useState<MarketMasterInstrumentPayload>({});

  const activeCount = useMemo(() => items.filter((item) => item.is_active).length, [items]);
  const lotCount = useMemo(() => items.filter((item) => item.quantity_mode === "LOTS").length, [items]);

  const loadData = async (nextSearch = search) => {
    setLoading(true);
    try {
      const [instrumentRows, classRows] = await Promise.all([
        adminApi.getMarketMasterInstruments(nextSearch.trim() || undefined),
        adminApi.getMarketMasterAssetClasses(),
      ]);
      setItems(instrumentRows || []);
      setAssetClasses(classRows || []);
    } catch (error) {
      toast.error(getErrorMessage(error, "Failed to load market master data"));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData("");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const openEditor = (item: MarketMasterInstrument) => {
    setEditing(item);
    setForm({
      exchange: item.exchange || "GLOBAL",
      market: item.market || item.asset_class || "",
      instrument_type: item.instrument_type || item.asset_class || "",
      asset_class: item.asset_class || "",
      base_currency: item.base_currency || "",
      quote_currency: item.quote_currency || "",
      broker_symbol: item.broker_symbol || "",
      account_currency: item.account_currency || "",
      currency_symbol: item.currency_symbol || "",
      price_unit_name: item.price_unit_name || "",
      quantity_mode: item.quantity_mode || "",
      contract_size: item.contract_size ?? undefined,
      tick_size: item.tick_size ?? undefined,
      tick_value_per_lot: item.tick_value_per_lot ?? undefined,
      pip_size: item.pip_size ?? undefined,
      min_lot: item.min_lot ?? undefined,
      max_lot: item.max_lot ?? undefined,
      lot_step: item.lot_step ?? undefined,
      min_quantity: item.min_quantity ?? undefined,
      quantity_step: item.quantity_step ?? undefined,
      price_precision: item.price_precision ?? undefined,
      quantity_precision: item.quantity_precision ?? undefined,
      is_active: item.is_active,
      is_tradeable_backtest: item.is_tradeable_backtest,
      is_tradeable_live: item.is_tradeable_live,
    });
  };

  const openCreate = () => {
    setEditing({
      id: 0,
      symbol: "",
      name: "",
      is_active: true,
      is_tradeable_backtest: true,
      is_tradeable_live: false,
    });
    setForm({
      ...instrumentPresets[0].payload,
    });
  };

  const saveInstrument = async () => {
    if (!editing) return;
    setSaving(true);
    try {
      if (editing.id === 0) {
        if (!form.symbol?.trim()) {
          toast.error("Symbol is required");
          return;
        }
        await adminApi.createMarketMasterInstrument(normalizePatch(form));
        toast.success("Instrument created");
      } else {
        await adminApi.updateMarketMasterInstrument(editing.id, normalizePatch(form));
        toast.success("Instrument updated");
      }
      setEditing(null);
      await loadData();
    } catch (error) {
      toast.error(getErrorMessage(error, "Failed to save instrument"));
    } finally {
      setSaving(false);
    }
  };

  const updateField = (key: keyof MarketMasterInstrumentPayload, value: any) => {
    setForm((prev) => {
      const next = { ...prev, [key]: value };
      if (key === "account_currency" && typeof value === "string" && currencySymbols[value]) {
        next.currency_symbol = currencySymbols[value];
      }
      if (key === "asset_class" && typeof value === "string") {
        next.market = next.market || value;
        next.instrument_type = next.instrument_type || value;
      }
      return next;
    });
  };

  const applyPreset = (indexValue: string) => {
    const index = Number(indexValue);
    const preset = Number.isFinite(index) ? instrumentPresets[index] : null;
    if (!preset) return;
    setForm((prev) => ({ ...prev, ...preset.payload }));
    toast.success(`${preset.payload.symbol} preset applied`);
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Market Master"
        subtitle="Manage instrument metadata, quantity modes, currencies, lot settings, ticks, and backtest/live tradeability."
        actions={
          <div className="flex flex-wrap gap-2">
            <Button className="rounded-xl" variant="outline" onClick={() => loadData()} disabled={loading}>
              <RefreshCcw className="mr-2 h-4 w-4" /> Refresh
            </Button>
            <Button className="rounded-xl bg-gradient-to-r from-fuchsia-600 to-violet-600 text-white" onClick={openCreate}>
              <Plus className="mr-2 h-4 w-4" /> Add Instrument
            </Button>
          </div>
        }
      />

      <div className="grid gap-4 md:grid-cols-3">
        <GlassCard className="p-5" depth={2}>
          <p className="text-sm text-purple-100/75">Total Instruments</p>
          <p className="mt-2 text-3xl font-bold text-white">{items.length}</p>
        </GlassCard>
        <GlassCard className="p-5" depth={2}>
          <p className="text-sm text-purple-100/75">Active Instruments</p>
          <p className="mt-2 text-3xl font-bold text-white">{activeCount}</p>
        </GlassCard>
        <GlassCard className="p-5" depth={2}>
          <p className="text-sm text-purple-100/75">Lot Based</p>
          <p className="mt-2 text-3xl font-bold text-white">{lotCount}</p>
        </GlassCard>
      </div>

      <GlassCard className="p-5" depth={3}>
        <div className="mb-5 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-white/10 bg-white/10 text-purple-100">
              <Database className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-white">Instrument Master</h2>
              <p className="text-sm text-purple-100/70">Indian stocks, indices, forex, metals, crypto and future markets.</p>
            </div>
          </div>
          <form
            className="flex gap-2"
            onSubmit={(event) => {
              event.preventDefault();
              loadData(search);
            }}
          >
            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-purple-100/60" />
              <input className={`${fieldClass} pl-9`} placeholder="Search symbol / asset..." value={search} onChange={(event) => setSearch(event.target.value)} />
            </div>
            <Button type="submit" className="rounded-xl" variant="outline" disabled={loading}>Search</Button>
          </form>
        </div>

        <div className="admin-table-scroll overflow-x-auto rounded-2xl border border-white/10">
          <table className="admin-data-table w-full min-w-[980px] text-left text-sm">
            <thead className="bg-white/10 text-xs uppercase tracking-wide text-purple-100/75">
              <tr>
                <th className="px-4 py-3">Symbol</th>
                <th className="px-4 py-3">Name</th>
                <th className="px-4 py-3">Asset Class</th>
                <th className="px-4 py-3">Currency</th>
                <th className="px-4 py-3">Qty Mode</th>
                <th className="px-4 py-3">Tick Size</th>
                <th className="px-4 py-3">Lot Step</th>
                <th className="px-4 py-3">Min Lot</th>
                <th className="px-4 py-3">Active</th>
                <th className="px-4 py-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/10">
              {loading ? (
                <tr>
                  <td colSpan={10} className="px-4 py-10 text-center text-purple-100/80">
                    <Loader2 className="mx-auto mb-2 h-6 w-6 animate-spin" /> Loading market master...
                  </td>
                </tr>
              ) : items.length === 0 ? (
                <tr>
                  <td colSpan={10} className="px-4 py-10 text-center text-purple-100/80">No instruments found. Run Phase 2A SQL migration first.</td>
                </tr>
              ) : (
                items.map((item) => (
                  <tr key={item.id} className="text-purple-50 transition-colors hover:bg-white/5">
                    <td className="px-4 py-3 font-semibold text-white">{item.symbol}</td>
                    <td className="px-4 py-3">{formatValue(item.name)}</td>
                    <td className="px-4 py-3">{formatValue(item.asset_class)}</td>
                    <td className="px-4 py-3">{formatValue(item.account_currency)}</td>
                    <td className="px-4 py-3"><Badge className="border-violet-400/30 bg-violet-500/10 text-violet-100">{formatValue(item.quantity_mode)}</Badge></td>
                    <td className="px-4 py-3">{formatValue(item.tick_size)}</td>
                    <td className="px-4 py-3">{formatValue(item.lot_step)}</td>
                    <td className="px-4 py-3">{formatValue(item.min_lot)}</td>
                    <td className="px-4 py-3">
                      <Badge className={item.is_active ? "border-emerald-400/30 bg-emerald-500/10 text-emerald-100" : "border-rose-400/30 bg-rose-500/10 text-rose-100"}>
                        {item.is_active ? "Active" : "Inactive"}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <Button size="sm" className="rounded-xl" variant="outline" onClick={() => openEditor(item)}>
                        <Edit className="mr-2 h-4 w-4" /> Edit
                      </Button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </GlassCard>

      <Dialog open={Boolean(editing)} onOpenChange={(open) => !open && setEditing(null)}>
        <DialogContent className="max-h-[92vh] max-w-4xl overflow-y-auto border-white/10 bg-[#170b2f] text-white shadow-2xl">
          <DialogHeader>
            <DialogTitle className="flex items-center justify-between text-white">
              <span>{editing?.id === 0 ? "Add Instrument" : `Edit ${editing?.symbol}`}</span>
              <Button variant="ghost" size="sm" className="rounded-xl text-white hover:bg-white/10" onClick={() => setEditing(null)}>
                <X className="h-4 w-4" />
              </Button>
            </DialogTitle>
          </DialogHeader>

          <div className="rounded-2xl border border-violet-400/20 bg-violet-500/10 p-4">
            <label className="space-y-2 text-sm text-purple-100">
              <span>Quick Instrument Preset</span>
              <select className={fieldClass} onChange={(event) => applyPreset(event.target.value)} defaultValue="">
                <option value="">Choose preset to auto-fill symbol, broker symbol, lot, tick, pip, currency</option>
                {instrumentPresets.map((preset, index) => (
                  <option key={preset.label} value={index}>{preset.label}</option>
                ))}
              </select>
            </label>
            <p className="mt-2 text-xs text-purple-100/70">For MT5 suffix brokers, keep internal Symbol clean, for example XAUUSD, and set Broker Symbol as XAUUSDm.</p>
          </div>

          {editing?.id === 0 ? (
            <div className="grid gap-4 md:grid-cols-2">
              <label className="space-y-2 text-sm text-purple-100">
                <span>Symbol *</span>
                <input className={fieldClass} value={form.symbol || ""} onChange={(event) => updateField("symbol", event.target.value.toUpperCase())} />
              </label>
              <label className="space-y-2 text-sm text-purple-100">
                <span>Name</span>
                <input className={fieldClass} value={form.name || ""} onChange={(event) => updateField("name", event.target.value)} />
              </label>
            </div>
          ) : null}

          <div className="grid gap-4 md:grid-cols-3">
            {editableFields.map((field) => {
              const value = (form as any)[field.key];
              if (field.type === "checkbox") {
                return (
                  <label key={field.key} className="flex items-center justify-between gap-3 rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-purple-100">
                    <span>{field.label}</span>
                    <input type="checkbox" checked={Boolean(value)} onChange={(event) => updateField(field.key, event.target.checked)} className="h-5 w-5 accent-violet-500" />
                  </label>
                );
              }
              if (field.type === "select") {
                const options = field.options || assetClasses.map((item) => item.code);
                return (
                  <label key={field.key} className="space-y-2 text-sm text-purple-100">
                    <span>{field.label}</span>
                    <select className={fieldClass} value={(value as string) || ""} onChange={(event) => updateField(field.key, event.target.value)}>
                      <option value="">Select</option>
                      {options.map((option) => <option key={option} value={option}>{option}</option>)}
                    </select>
                  </label>
                );
              }
              return (
                <label key={field.key} className="space-y-2 text-sm text-purple-100">
                  <span>{field.label}</span>
                  <input
                    className={fieldClass}
                    type={field.type || "text"}
                    step={field.type === "number" ? "any" : undefined}
                    value={value ?? ""}
                    onChange={(event) => updateField(field.key, field.type === "number" ? (event.target.value === "" ? "" : Number(event.target.value)) : event.target.value)}
                  />
                </label>
              );
            })}
          </div>

          <div className="flex justify-end gap-3 border-t border-white/10 pt-4">
            <Button variant="outline" className="rounded-xl" onClick={() => setEditing(null)} disabled={saving}>Cancel</Button>
            <Button className="rounded-xl bg-gradient-to-r from-fuchsia-600 to-violet-600 text-white" onClick={saveInstrument} disabled={saving}>
              {saving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Save className="mr-2 h-4 w-4" />}
              Save
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
