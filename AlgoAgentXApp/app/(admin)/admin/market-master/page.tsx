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

const editableFields: Array<{ key: keyof MarketMasterInstrumentPayload; label: string; type?: "text" | "number" | "checkbox" | "select"; options?: string[] }> = [
  { key: "asset_class", label: "Asset Class", type: "select" },
  { key: "broker_symbol", label: "Broker Symbol" },
  { key: "account_currency", label: "Account Currency" },
  { key: "currency_symbol", label: "Currency Symbol" },
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
      asset_class: item.asset_class || "",
      broker_symbol: item.broker_symbol || "",
      account_currency: item.account_currency || "",
      currency_symbol: item.currency_symbol || "",
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
      symbol: "",
      name: "",
      exchange: "GLOBAL",
      asset_class: "INDIAN_EQUITY",
      account_currency: "INR",
      currency_symbol: "₹",
      price_unit_name: "points",
      quantity_mode: "SHARES",
      tick_size: 0.05,
      min_quantity: 1,
      quantity_step: 1,
      price_precision: 2,
      quantity_precision: 0,
      is_active: true,
      is_tradeable_backtest: true,
      is_tradeable_live: false,
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
    setForm((prev) => ({ ...prev, [key]: value }));
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
