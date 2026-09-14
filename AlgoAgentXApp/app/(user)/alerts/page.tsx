"use client";

import { useEffect, useMemo, useState } from "react";
import { BellRing, Check, CheckCircle2, ChevronsUpDown, CircleAlert, Edit3, Loader2, Pause, Play, RefreshCw, Send, Trash2, WifiOff } from "lucide-react";
import { PageShell } from "@/components/ui/PageShell";
import { PageHeader } from "@/components/ui/PageHeader";
import { GlassCard } from "@/components/ui/GlassCard";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from "@/components/ui/command";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { alertsApi } from "@/lib/api/alerts";
import { liveTradingApi } from "@/lib/api/live-trading";
import { formatDateTimeIST } from "@/lib/timezone";
import { useToast } from "@/components/shared/toast";
import type { AlertEvent, AlertHealth, AlertPayload, AlertType, PriceAlert, TelegramChannel, WhatsAppChannel } from "@/types/alerts";
import type { BrokerAccount, BrokerSymbol, MarketInstrument } from "@/types/live-trading";

const alertSelectTriggerClass = "mt-2 border-white/20 bg-[#241044]/95 text-white shadow-sm hover:bg-[#2d1554] focus:ring-violet-400/60";
const alertSelectContentClass = "z-[150] border-white/20 bg-[#241044] text-white shadow-2xl";
const alertSelectItemClass = "text-white focus:bg-violet-600/40 focus:text-white";


const normalizeSymbolKey = (value: unknown) => String(value || "").trim().toUpperCase().replace(/[^A-Z0-9]/g, "");

const matchesCanonicalSymbol = (brokerSymbol: string, canonicalSymbol: string) => {
  const broker = normalizeSymbolKey(brokerSymbol);
  const canonical = normalizeSymbolKey(canonicalSymbol);
  return Boolean(broker && canonical && (broker === canonical || broker.startsWith(canonical) || canonical.startsWith(broker)));
};

const conditions: Array<{ value: AlertType; label: string }> = [
  { value: "CROSSING_UP", label: "Crossing Up" },
  { value: "CROSSING_DOWN", label: "Crossing Down" },
  { value: "ENTERING_ZONE", label: "Entering Zone" },
  { value: "LEAVING_ZONE", label: "Leaving Zone" },
];

const numberText = (value: unknown, digits = 2) => {
  const n = Number(value);
  return Number.isFinite(n) ? n.toLocaleString("en-US", { maximumFractionDigits: digits }) : "—";
};

const conditionLabel = (value: string) => {
  if (value === "APPROACHING_TARGET") return "Approaching Target";
  if (value === "APPROACHING_ZONE") return "Approaching Zone";
  return conditions.find((x) => x.value === value)?.label || value.replaceAll("_", " ");
};

const eventTargetLabel = (event: AlertEvent) => {
  const snapshot = (event.payload?.alert_snapshot || {}) as Record<string, unknown>;
  const sourceType = String(snapshot.alert_type || event.condition_type || "");
  if (sourceType === "ENTERING_ZONE" || sourceType === "LEAVING_ZONE" || event.condition_type === "APPROACHING_ZONE") {
    return `${numberText(snapshot.zone_low)} – ${numberText(snapshot.zone_high)}`;
  }
  return numberText(snapshot.target_price);
};

const toIstInputValue = (value?: string | null) => {
  if (!value) return "";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "";
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Kolkata",
    year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit",
    hour12: false,
  }).formatToParts(parsed);
  const part = (type: string) => parts.find((x) => x.type === type)?.value || "";
  return `${part("year")}-${part("month")}-${part("day")}T${part("hour")}:${part("minute")}`;
};

const istInputToUtcIso = (value: string) => value ? new Date(`${value}:00+05:30`).toISOString() : null;

const blankForm = (): AlertPayload => ({
  symbol: "",
  provider: "MT5",
  broker_account_id: null,
  alert_type: "CROSSING_UP",
  target_price: null,
  zone_low: null,
  zone_high: null,
  trigger_mode: "ONCE",
  cooldown_seconds: 60,
  rearm_distance: 0,
  rearm_type: "DISTANCE_AND_COOLDOWN",
  expires_at: null,
  telegram_enabled: true,
  browser_enabled: false,
  whatsapp_enabled: false,
  approach_enabled: false,
  approach_distance: null,
});

function statusClass(value: string) {
  const v = String(value || "").toUpperCase();
  if (["ACTIVE", "ARMED", "CONNECTED", "HEALTHY", "SENT", "CONFIGURED", "WAITING"].includes(v)) return "border-emerald-400/30 bg-emerald-400/15 text-emerald-100";
  if (["COOLDOWN", "REARM_WAIT", "DEGRADED", "RETRYING", "SENDING", "APPROACH_SENT"].includes(v)) return "border-amber-400/30 bg-amber-400/15 text-amber-100";
  if (["DISABLED", "COMPLETED", "IDLE"].includes(v)) return "border-slate-400/30 bg-slate-400/15 text-slate-100";
  return "border-red-400/30 bg-red-400/15 text-red-100";
}

export default function AlertsPage() {
  const { showToast } = useToast();
  const [alerts, setAlerts] = useState<PriceAlert[]>([]);
  const [history, setHistory] = useState<AlertEvent[]>([]);
  const [health, setHealth] = useState<AlertHealth | null>(null);
  const [telegram, setTelegram] = useState<TelegramChannel | null>(null);
  const [whatsapp, setWhatsApp] = useState<WhatsAppChannel | null>(null);
  const [accounts, setAccounts] = useState<BrokerAccount[]>([]);
  const [brokerSymbols, setBrokerSymbols] = useState<BrokerSymbol[]>([]);
  const [marketInstruments, setMarketInstruments] = useState<MarketInstrument[]>([]);
  const [symbolsLoading, setSymbolsLoading] = useState(false);
  const [symbolLoadError, setSymbolLoadError] = useState<string | null>(null);
  const [symbolPickerOpen, setSymbolPickerOpen] = useState(false);
  const [chatId, setChatId] = useState("");
  const [whatsAppNumber, setWhatsAppNumber] = useState("");
  const [form, setForm] = useState<AlertPayload>(blankForm());
  const [editingId, setEditingId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [detail, setDetail] = useState<AlertEvent | null>(null);

  const mt5Accounts = useMemo(() => accounts.filter((a) => String(a.broker_code || a.broker_name || "").toUpperCase() === "MT5"), [accounts]);
  const activeMarketInstruments = useMemo(() => {
    const active = marketInstruments.filter((item) => item.is_active !== false);
    return active.length ? active : marketInstruments;
  }, [marketInstruments]);
  const symbolOptions = useMemo(() => {
    const seen = new Set<string>();
    const rows: Array<{ value: string; label: string; source: "broker" | "master" }> = [];
    for (const item of brokerSymbols) {
      if (!item?.symbol || item.success === false) continue;
      const value = String(item.symbol).trim();
      const key = value.toUpperCase();
      if (!value || seen.has(key)) continue;
      seen.add(key);
      const master = activeMarketInstruments.find((candidate) =>
        matchesCanonicalSymbol(value, String(candidate.broker_symbol || candidate.symbol || "")) ||
        matchesCanonicalSymbol(value, String(candidate.symbol || ""))
      );
      const canonical = master?.symbol && String(master.symbol).toUpperCase() !== value.toUpperCase() ? ` · ${master.symbol}` : "";
      const description = String(item.description || master?.name || "").trim();
      rows.push({ value, label: `${value}${canonical}${description ? ` · ${description}` : ""}`, source: "broker" });
    }
    if (!rows.length) {
      for (const item of activeMarketInstruments) {
        const value = String(item.broker_symbol || item.symbol || "").trim();
        const key = value.toUpperCase();
        if (!value || seen.has(key)) continue;
        seen.add(key);
        const canonical = item.symbol && String(item.symbol).toUpperCase() !== value.toUpperCase() ? ` · ${item.symbol}` : "";
        const description = String(item.name || item.instrument_type || "").trim();
        rows.push({ value, label: `${value}${canonical}${description ? ` · ${description}` : ""} · Market Master`, source: "master" });
      }
    }
    if (form.symbol && !seen.has(String(form.symbol).toUpperCase())) {
      rows.unshift({ value: form.symbol, label: `${form.symbol} · Current alert symbol`, source: "master" });
    }
    return rows;
  }, [brokerSymbols, activeMarketInstruments, form.symbol]);
  const selectedSymbolOption = useMemo(
    () => symbolOptions.find((option) => option.value === form.symbol) || null,
    [symbolOptions, form.symbol],
  );
  const isZone = form.alert_type === "ENTERING_ZONE" || form.alert_type === "LEAVING_ZONE";
  const approachSupported = form.alert_type !== "LEAVING_ZONE";
  const activeAlertCount = health?.active_alert_count ?? alerts.filter((row) => row.status === "ACTIVE").length;
  const feedReady = activeAlertCount === 0
    ? health?.market_feed === "idle" || health?.market_feed === "connected"
    : health?.market_feed === "connected";
  const protectionHealthy = health?.worker === "healthy" && health?.redis === "healthy" && health?.database === "healthy" && Boolean(feedReady);

  const approachPreview = useMemo(() => {
    if (!form.approach_enabled || !form.approach_distance || Number(form.approach_distance) <= 0) return null;
    const distance = Number(form.approach_distance);
    if (form.alert_type === "CROSSING_UP" && form.target_price != null) {
      return `Warn near ${numberText(Number(form.target_price) - distance)} before crossing up ${numberText(form.target_price)}.`;
    }
    if (form.alert_type === "CROSSING_DOWN" && form.target_price != null) {
      return `Warn near ${numberText(Number(form.target_price) + distance)} before crossing down ${numberText(form.target_price)}.`;
    }
    if (form.alert_type === "ENTERING_ZONE" && form.zone_low != null && form.zone_high != null) {
      return `Two-way zone: from below warn near ${numberText(Number(form.zone_low) - distance)}; from above warn near ${numberText(Number(form.zone_high) + distance)}.`;
    }
    return null;
  }, [form.approach_enabled, form.approach_distance, form.alert_type, form.target_price, form.zone_low, form.zone_high]);

  const load = async (silent = false) => {
    try {
      if (!silent) setLoading(true);
      const [a, h, healthData, tg, wa, brokerRows] = await Promise.all([
        alertsApi.list(),
        alertsApi.history(100),
        alertsApi.health().catch(() => null),
        alertsApi.telegramChannel().catch(() => null),
        alertsApi.whatsappChannel().catch(() => null),
        liveTradingApi.listBrokerAccounts().catch(() => []),
      ]);
      setAlerts(a || []);
      setHistory(h || []);
      if (healthData) setHealth(healthData);
      if (tg) {
        setTelegram(tg);
        if (tg.chat_id) setChatId(tg.chat_id);
      }
      if (wa) {
        setWhatsApp(wa);
        if (wa.phone_number) setWhatsAppNumber(wa.phone_number);
      }
      setAccounts(brokerRows || []);
    } catch (error: any) {
      showToast(error?.message || "Unable to load alerts", "error");
    } finally {
      if (!silent) setLoading(false);
    }
  };

  useEffect(() => {
    void load();
    const timer = window.setInterval(() => void load(true), 5000);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    let cancelled = false;
    void liveTradingApi.listMarketInstruments().then((rows) => {
      if (!cancelled) setMarketInstruments(rows || []);
    }).catch(() => {
      if (!cancelled) setMarketInstruments([]);
    });
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    const accountId = form.broker_account_id;
    if (!accountId || form.provider !== "MT5") {
      setBrokerSymbols([]);
      setSymbolLoadError(null);
      setSymbolsLoading(false);
      return;
    }
    let cancelled = false;
    setSymbolsLoading(true);
    setSymbolLoadError(null);
    void liveTradingApi.listBrokerSymbols(accountId, "", 500).then((rows) => {
      if (cancelled) return;
      const usable = (rows || []).filter((row) => row?.symbol && row.success !== false);
      setBrokerSymbols(usable);
      const errorRow = (rows || []).find((row) => row?.success === false);
      if (errorRow && !usable.length) setSymbolLoadError(String(errorRow.message || "Unable to load MT5 broker symbols."));
      if (form.symbol && usable.length && !usable.some((row) => String(row.symbol).toUpperCase() === String(form.symbol).toUpperCase())) {
        const mapped = usable.find((row) => matchesCanonicalSymbol(String(row.symbol), form.symbol));
        if (mapped?.symbol) setForm((current) => current.broker_account_id === accountId ? { ...current, symbol: String(mapped.symbol) } : current);
      }
    }).catch((error: any) => {
      if (!cancelled) {
        setBrokerSymbols([]);
        setSymbolLoadError(error?.message || "Unable to load symbols from the MT5 Agent. Make sure the updated agent is running.");
      }
    }).finally(() => {
      if (!cancelled) setSymbolsLoading(false);
    });
    return () => { cancelled = true; };
  }, [form.broker_account_id, form.provider]);

  const resetForm = () => {
    setEditingId(null);
    setForm(blankForm());
  };

  const saveAlert = async () => {
    if (!form.symbol.trim()) return showToast("Symbol is required", "error");
    if (!form.broker_account_id && form.provider === "MT5") return showToast("Select the MT5 broker account that supplies live ticks", "error");
    if (!isZone && (!form.target_price || Number(form.target_price) <= 0)) return showToast("Enter a valid target price", "error");
    if (isZone && (!(Number(form.zone_low) < Number(form.zone_high)))) return showToast("Zone Low must be below Zone High", "error");
    if (form.approach_enabled && (!approachSupported || !form.approach_distance || Number(form.approach_distance) <= 0)) {
      return showToast(approachSupported ? "Approach Distance must be greater than 0" : "Approach Alert is not supported for Leaving Zone in Phase 2A", "error");
    }
    if (!form.telegram_enabled && !form.whatsapp_enabled) return showToast("Enable Telegram or WhatsApp for this alert", "error");
    if (form.whatsapp_enabled && health?.whatsapp !== "configured") return showToast("Configure Twilio WhatsApp credentials on the API/worker first", "error");
    if (form.whatsapp_enabled && !whatsapp?.configured) return showToast("Save and test your WhatsApp destination number first", "error");
    try {
      setBusy(true);
      const payload: AlertPayload = {
        ...form,
        symbol: form.symbol.trim(),
        target_price: isZone ? null : Number(form.target_price),
        zone_low: isZone ? Number(form.zone_low) : null,
        zone_high: isZone ? Number(form.zone_high) : null,
        cooldown_seconds: Number(form.cooldown_seconds || 0),
        rearm_distance: Number(form.rearm_distance || 0),
        approach_enabled: Boolean(form.approach_enabled && approachSupported),
        approach_distance: form.approach_enabled && approachSupported ? Number(form.approach_distance) : null,
      };
      if (editingId) await alertsApi.update(editingId, payload);
      else await alertsApi.create(payload);
      showToast(editingId ? "Alert updated" : "Alert created and armed", "success");
      resetForm();
      await load(true);
    } catch (error: any) {
      showToast(error?.message || "Unable to save alert", "error");
    } finally {
      setBusy(false);
    }
  };

  const editAlert = (row: PriceAlert) => {
    setEditingId(row.id);
    setForm({
      symbol: row.symbol,
      provider: row.provider,
      broker_account_id: row.broker_account_id || null,
      alert_type: row.alert_type,
      target_price: row.target_price == null ? null : Number(row.target_price),
      zone_low: row.zone_low == null ? null : Number(row.zone_low),
      zone_high: row.zone_high == null ? null : Number(row.zone_high),
      trigger_mode: row.trigger_mode,
      cooldown_seconds: row.cooldown_seconds,
      rearm_distance: Number(row.rearm_distance || 0),
      rearm_type: row.rearm_type,
      expires_at: row.expires_at || null,
      telegram_enabled: row.telegram_enabled,
      browser_enabled: false,
      whatsapp_enabled: row.whatsapp_enabled,
      approach_enabled: Boolean(row.approach_enabled),
      approach_distance: row.approach_distance == null ? null : Number(row.approach_distance),
    });
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const runAction = async (action: "enable" | "disable" | "delete", row: PriceAlert) => {
    try {
      setBusy(true);
      if (action === "enable") await alertsApi.enable(row.id);
      if (action === "disable") await alertsApi.disable(row.id);
      if (action === "delete") await alertsApi.remove(row.id);
      showToast(action === "delete" ? "Alert deleted" : `Alert ${action}d`, "success");
      await load(true);
    } catch (error: any) {
      showToast(error?.message || "Alert action failed", "error");
    } finally {
      setBusy(false);
    }
  };

  const saveTelegram = async () => {
    if (!chatId.trim()) return showToast("Enter your Telegram chat ID", "error");
    try {
      setBusy(true);
      const saved = await alertsApi.saveTelegramChannel(chatId.trim());
      setTelegram(saved);
      showToast("Telegram chat saved", "success");
    } catch (error: any) {
      showToast(error?.message || "Unable to save Telegram chat", "error");
    } finally { setBusy(false); }
  };

  const testTelegram = async () => {
    try {
      setBusy(true);
      if (chatId.trim() && chatId.trim() !== telegram?.chat_id) await alertsApi.saveTelegramChannel(chatId.trim());
      await alertsApi.testTelegram(chatId.trim() || undefined);
      showToast("Telegram API accepted the test notification", "success");
      await load(true);
    } catch (error: any) {
      showToast(error?.message || "Telegram test failed", "error");
    } finally { setBusy(false); }
  };

  const saveWhatsApp = async () => {
    if (!whatsAppNumber.trim()) return showToast("Enter your WhatsApp number in E.164 format, e.g. +919876543210", "error");
    try {
      setBusy(true);
      const saved = await alertsApi.saveWhatsAppChannel(whatsAppNumber.trim());
      setWhatsApp(saved);
      showToast("WhatsApp number saved", "success");
    } catch (error: any) {
      showToast(error?.message || "Unable to save WhatsApp number", "error");
    } finally { setBusy(false); }
  };

  const testWhatsApp = async () => {
    try {
      setBusy(true);
      if (whatsAppNumber.trim() && whatsAppNumber.trim() !== whatsapp?.phone_number) {
        await alertsApi.saveWhatsAppChannel(whatsAppNumber.trim());
      }
      await alertsApi.testWhatsApp(whatsAppNumber.trim() || undefined);
      showToast("Twilio API accepted the WhatsApp test notification", "success");
      await load(true);
    } catch (error: any) {
      showToast(error?.message || "WhatsApp test failed", "error");
    } finally { setBusy(false); }
  };

  if (loading) return <PageShell><div className="flex min-h-[50vh] items-center justify-center gap-2 text-muted-foreground"><Loader2 className="h-5 w-5 animate-spin" />Loading alert engine…</div></PageShell>;

  return (
    <PageShell>
      <PageHeader title="Real-Time Alerts" description="Live tick/quote monitoring independent of candle close, backtests, strategy evaluation and browser refresh." />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-6">
        {[
          ["Alert Worker", health?.worker || "unknown", health?.worker === "healthy"],
          ["Redis", health?.redis || "unknown", health?.redis === "healthy"],
          ["Database", health?.database || "unknown", health?.database === "healthy"],
          ["Market Feed", health?.market_feed || "unknown", health?.market_feed === "connected" || health?.market_feed === "idle"],
          ["Telegram", health?.telegram || "unknown", health?.telegram === "configured"],
          ["WhatsApp", health?.whatsapp || "unknown", health?.whatsapp === "configured"],
        ].map(([label, value, good]) => (
          <GlassCard key={String(label)} className="p-4">
            <div className="flex items-center justify-between gap-3">
              <div><p className="text-xs uppercase tracking-wider text-muted-foreground">{String(label)}</p><p className="mt-1 font-semibold capitalize">{String(value).replaceAll("_", " ")}</p></div>
              {good ? <CheckCircle2 className="h-5 w-5 text-emerald-300" /> : <CircleAlert className="h-5 w-5 text-amber-300" />}
            </div>
          </GlassCard>
        ))}
      </div>

      {!protectionHealthy && (
        <div className="mt-4 flex gap-3 rounded-2xl border border-amber-400/25 bg-amber-400/10 p-4 text-sm text-amber-100">
          <WifiOff className="mt-0.5 h-5 w-5 shrink-0" />
          <div><strong>Real-time alert protection is not fully healthy.</strong> Alerts remain stored, but active protection requires the alert worker, Redis, database and a recent live market tick. Start/verify the updated MT5 Agent on the same broker account used by the alert. {health?.last_tick ? `Last alert tick: ${formatDateTimeIST(health.last_tick, { seconds: true })}.` : "No alert quote tick has reached AlgoAgentX yet."}</div>
        </div>
      )}

      <div className="mt-6 grid gap-6 2xl:grid-cols-[1.25fr_.75fr]">
        <GlassCard className="p-5">
          <div className="mb-5 flex items-center justify-between"><div><h2 className="text-xl font-bold">{editingId ? "Edit Alert" : "Create Alert"}</h2><p className="text-sm text-muted-foreground">Phase 2A adds one pre-warning before the existing real-time target/zone alert.</p></div>{editingId && <Button variant="outline" onClick={resetForm}>Cancel Edit</Button>}</div>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            <div>
              <Label>Symbol / Instrument</Label>
              <Popover open={symbolPickerOpen} onOpenChange={setSymbolPickerOpen}>
                <PopoverTrigger asChild>
                  <Button
                    type="button"
                    variant="outline"
                    role="combobox"
                    aria-expanded={symbolPickerOpen}
                    disabled={!form.broker_account_id || symbolsLoading}
                    className={`${alertSelectTriggerClass} h-10 w-full justify-between px-3 font-normal`}
                  >
                    <span className="min-w-0 flex-1 truncate text-left">
                      {symbolsLoading
                        ? "Loading broker symbols…"
                        : selectedSymbolOption?.label || form.symbol || (form.broker_account_id ? "Search or select broker instrument" : "Select broker account first")}
                    </span>
                    {symbolsLoading ? <Loader2 className="ml-2 h-4 w-4 shrink-0 animate-spin opacity-70" /> : <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-70" />}
                  </Button>
                </PopoverTrigger>
                <PopoverContent
                  align="start"
                  className="z-[150] w-[var(--radix-popover-trigger-width)] min-w-[320px] border-white/20 bg-[#241044] p-0 text-white shadow-2xl"
                >
                  <Command className="bg-[#241044] text-white">
                    <CommandInput
                      placeholder="Search symbol, e.g. XAUUSDm, BTCUSDm…"
                      className="text-white placeholder:text-white/45"
                    />
                    <CommandList className="max-h-[360px]">
                      <CommandEmpty className="py-6 text-center text-sm text-white/65">No matching broker instrument found.</CommandEmpty>
                      <CommandGroup>
                        {symbolOptions.map((option) => (
                          <CommandItem
                            key={`${option.source}-${option.value}`}
                            value={`${option.value} ${option.label}`}
                            onSelect={() => {
                              setForm((current) => ({ ...current, symbol: option.value }));
                              setSymbolPickerOpen(false);
                            }}
                            className="cursor-pointer text-white aria-selected:bg-violet-600/40 aria-selected:text-white"
                          >
                            <Check className={`mr-2 h-4 w-4 shrink-0 ${form.symbol === option.value ? "opacity-100" : "opacity-0"}`} />
                            <span className="truncate">{option.label}</span>
                          </CommandItem>
                        ))}
                      </CommandGroup>
                    </CommandList>
                  </Command>
                </PopoverContent>
              </Popover>
              <p className={`mt-1 text-xs ${symbolLoadError ? "text-amber-200" : "text-muted-foreground"}`}>{symbolLoadError || (brokerSymbols.length ? "Exact symbols are loaded from this MT5 broker account and preserved exactly, including broker suffixes such as XAUUSDm, XAUUSD.x or XAUUSD.a." : form.broker_account_id ? "Using Market Master as fallback until broker symbols are available." : "Select the same MT5 account whose Agent token is running.")}</p>
            </div>
            <div><Label>Feed / Provider</Label><Select value={form.provider} onValueChange={(v) => setForm({ ...form, provider: v })}><SelectTrigger className={alertSelectTriggerClass}><SelectValue /></SelectTrigger><SelectContent className={alertSelectContentClass}><SelectItem className={alertSelectItemClass} value="MT5">MT5 Agent — Live Ticks</SelectItem></SelectContent></Select></div>
            <div><Label>MT5 Broker Account</Label><Select value={form.broker_account_id || ""} onValueChange={(v) => setForm((current) => ({ ...current, broker_account_id: v || null, symbol: current.broker_account_id === v ? current.symbol : "" }))}><SelectTrigger className={alertSelectTriggerClass}><SelectValue placeholder="Select account" /></SelectTrigger><SelectContent className={alertSelectContentClass}>{mt5Accounts.map((a) => <SelectItem className={alertSelectItemClass} key={a.id} value={a.id}>{a.account_label} · {a.status}</SelectItem>)}</SelectContent></Select></div>
            <div><Label>Condition</Label><Select value={form.alert_type} onValueChange={(v) => setForm((current) => ({ ...current, alert_type: v as AlertType, ...(v === "LEAVING_ZONE" ? { approach_enabled: false, approach_distance: null } : {}) }))}><SelectTrigger className={alertSelectTriggerClass}><SelectValue /></SelectTrigger><SelectContent className={alertSelectContentClass}>{conditions.map((x) => <SelectItem className={alertSelectItemClass} key={x.value} value={x.value}>{x.label}</SelectItem>)}</SelectContent></Select></div>
            {!isZone ? <div><Label>Target Price</Label><Input className="mt-2" type="number" step="any" value={form.target_price ?? ""} onChange={(e) => setForm({ ...form, target_price: e.target.value === "" ? null : Number(e.target.value) })} /></div> : <><div><Label>Zone Low</Label><Input className="mt-2" type="number" step="any" value={form.zone_low ?? ""} onChange={(e) => setForm({ ...form, zone_low: e.target.value === "" ? null : Number(e.target.value) })} /></div><div><Label>Zone High</Label><Input className="mt-2" type="number" step="any" value={form.zone_high ?? ""} onChange={(e) => setForm({ ...form, zone_high: e.target.value === "" ? null : Number(e.target.value) })} /></div></>}
            <div><Label>Frequency</Label><Select value={form.trigger_mode} onValueChange={(v) => setForm({ ...form, trigger_mode: v as "ONCE" | "RECURRING" })}><SelectTrigger className={alertSelectTriggerClass}><SelectValue /></SelectTrigger><SelectContent className={alertSelectContentClass}><SelectItem className={alertSelectItemClass} value="ONCE">Trigger Once</SelectItem><SelectItem className={alertSelectItemClass} value="RECURRING">Recurring / Rearm</SelectItem></SelectContent></Select></div>
            <div><Label>Cooldown (seconds)</Label><Input className="mt-2" type="number" min={0} value={form.cooldown_seconds} disabled={form.trigger_mode === "ONCE"} onChange={(e) => setForm({ ...form, cooldown_seconds: Number(e.target.value) })} /></div>
            <div><Label>Rearm Distance</Label><Input className="mt-2" type="number" min={0} step="any" value={form.rearm_distance} disabled={form.trigger_mode === "ONCE" || isZone} onChange={(e) => setForm({ ...form, rearm_distance: Number(e.target.value) })} /><p className="mt-1 text-xs text-muted-foreground">Crossing alerts must move this far away after cooldown before rearming.</p></div>
            <div><Label>Expiration (optional, IST)</Label><Input className="mt-2" type="datetime-local" value={toIstInputValue(form.expires_at)} onChange={(e) => setForm({ ...form, expires_at: istInputToUtcIso(e.target.value) })} /></div>
          </div>

          <div className={`mt-5 rounded-2xl border p-4 ${form.approach_enabled ? "border-amber-300/30 bg-amber-300/10" : "border-white/10 bg-white/5"}`}>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="font-semibold">Approach Alert <span className="text-xs font-normal text-amber-200">Phase 2A</span></p>
                <p className="mt-1 text-xs text-muted-foreground">Send one pre-warning through the notification channels enabled on this alert before price reaches the target or enters the zone.</p>
              </div>
              <Button
                type="button"
                variant={form.approach_enabled ? "default" : "outline"}
                disabled={!approachSupported}
                onClick={() => setForm((current) => ({
                  ...current,
                  approach_enabled: !current.approach_enabled,
                  approach_distance: current.approach_enabled ? null : (current.approach_distance || 2),
                }))}
              >
                {form.approach_enabled ? "Approach ON" : "Enable Approach"}
              </Button>
            </div>
            {!approachSupported && <p className="mt-3 text-xs text-amber-200">Approach proximity is intentionally limited to Crossing Up, Crossing Down, and Entering Zone in Phase 2A.</p>}
            {form.approach_enabled && approachSupported && (
              <div className="mt-4 grid gap-4 md:grid-cols-[220px_1fr]">
                <div>
                  <Label>Approach Distance</Label>
                  <Input
                    className="mt-2"
                    type="number"
                    min="0.0000000001"
                    step="any"
                    value={form.approach_distance ?? ""}
                    onChange={(e) => setForm({ ...form, approach_distance: e.target.value === "" ? null : Number(e.target.value) })}
                  />
                  <p className="mt-1 text-xs text-muted-foreground">Absolute price distance. For Gold, 3 means $3 away.</p>
                </div>
                <div className="rounded-xl border border-white/10 bg-black/10 p-3 text-sm">
                  <p className="font-medium">How it works</p>
                  <p className="mt-1 text-muted-foreground">
                    For an Entering Zone alert, AlgoAgentX automatically handles both directions: price rising from below toward resistance, or price falling from above toward support.
                  </p>
                  {approachPreview && <p className="mt-2 font-medium text-amber-100">{approachPreview}</p>}
                </div>
              </div>
            )}
          </div>

          <div className="mt-5 grid gap-3 md:grid-cols-3">
            <button type="button" onClick={() => setForm((current) => ({ ...current, telegram_enabled: !current.telegram_enabled }))} className={`rounded-xl border p-3 text-left transition ${form.telegram_enabled ? "border-emerald-400/30 bg-emerald-400/10" : "border-white/10 bg-white/5 opacity-70"}`}>
              <p className="font-semibold">Telegram {form.telegram_enabled ? "ON" : "OFF"}</p><p className="text-xs text-muted-foreground">Primary notification channel</p>
            </button>
            <button type="button" onClick={() => setForm((current) => ({ ...current, whatsapp_enabled: !current.whatsapp_enabled }))} className={`rounded-xl border p-3 text-left transition ${form.whatsapp_enabled ? "border-emerald-400/30 bg-emerald-400/10" : "border-white/10 bg-white/5 opacity-70"}`}>
              <p className="font-semibold">WhatsApp {form.whatsapp_enabled ? "ON" : "OFF"}</p><p className="text-xs text-muted-foreground">Twilio WhatsApp delivery</p>
            </button>
            <div className="rounded-xl border border-white/10 bg-white/5 p-3 opacity-60"><p className="font-semibold">Browser Push</p><p className="text-xs text-muted-foreground">Not enabled</p></div>
          </div>
          <Button className="mt-5" disabled={busy} onClick={() => void saveAlert()}><BellRing className="mr-2 h-4 w-4" />{editingId ? "Save Changes" : "Create & Arm Alert"}</Button>
        </GlassCard>

        <div className="space-y-6">
          <GlassCard className="p-5">
            <h2 className="text-xl font-bold">Telegram Setup</h2>
            <p className="mt-1 text-sm text-muted-foreground">Create the bot with BotFather, start a chat with it, then save the Telegram chat ID here.</p>
            <div className="mt-4"><Label>Telegram Chat ID</Label><Input className="mt-2" value={chatId} onChange={(e) => setChatId(e.target.value)} placeholder="e.g. 123456789" /></div>
            <div className="mt-4 flex flex-wrap gap-2"><Button variant="outline" disabled={busy} onClick={() => void saveTelegram()}>Save Chat ID</Button><Button disabled={busy} onClick={() => void testTelegram()}><Send className="mr-2 h-4 w-4" />Test Telegram</Button></div>
            <div className="mt-4 rounded-xl border border-white/10 bg-white/5 p-3 text-sm"><p>Bot token: <strong>{health?.telegram === "configured" ? "Configured" : "Not configured on API/worker"}</strong></p><p>Chat: <strong>{telegram?.configured ? (telegram.verified ? "Verified by test" : "Configured") : "Not configured"}</strong></p>{telegram?.using_global_fallback && <p className="mt-1 text-amber-200">Using global admin fallback chat ID.</p>}</div>
            <p className="mt-3 text-xs text-muted-foreground">A successful test means Telegram Bot API accepted the message. It is not a handset-delivery receipt.</p>
          </GlassCard>

          <GlassCard className="p-5">
            <h2 className="text-xl font-bold">WhatsApp Setup</h2>
            <p className="mt-1 text-sm text-muted-foreground">Uses your Twilio WhatsApp sender configured on the API/alert worker.</p>
            <div className="mt-4"><Label>Destination WhatsApp Number</Label><Input className="mt-2" value={whatsAppNumber} onChange={(e) => setWhatsAppNumber(e.target.value)} placeholder="+919876543210" /></div>
            <div className="mt-4 flex flex-wrap gap-2"><Button variant="outline" disabled={busy} onClick={() => void saveWhatsApp()}>Save Number</Button><Button disabled={busy || health?.whatsapp !== "configured"} onClick={() => void testWhatsApp()}><Send className="mr-2 h-4 w-4" />Test WhatsApp</Button></div>
            <div className="mt-4 rounded-xl border border-white/10 bg-white/5 p-3 text-sm"><p>Twilio: <strong>{health?.whatsapp === "configured" ? "Configured" : "Not configured on API/worker"}</strong></p><p>Number: <strong>{whatsapp?.configured ? (whatsapp.verified ? "Verified by test" : "Configured") : "Not configured"}</strong></p><p>Mode: <strong>{whatsapp?.content_template_configured ? "Twilio Content Templates" : "Body / active WhatsApp session"}</strong></p>{whatsapp?.content_template_configured && <><p>Approaching template: <strong>{whatsapp?.approaching_template_configured ? "Configured" : "Legacy fallback"}</strong></p><p>Triggered template: <strong>{whatsapp?.triggered_template_configured ? "Configured" : "Legacy fallback"}</strong></p></>}{whatsapp?.using_global_fallback && <p className="mt-1 text-amber-200">Using global fallback destination from environment.</p>}</div>
            <p className="mt-3 text-xs text-muted-foreground">Recommended: configure TWILIO_CONTENT_SID_APPROACHING and TWILIO_CONTENT_SID_TRIGGERED on the API/alert worker. The old TWILIO_CONTENT_SID remains only as a fallback.</p>
          </GlassCard>
        </div>
      </div>

      <GlassCard className="mt-6 p-5">
        <div className="mb-4 flex items-center justify-between"><div><h2 className="text-xl font-bold">Active Alerts</h2><p className="text-sm text-muted-foreground">Persistent state survives frontend closure and worker restart.</p></div><Button size="sm" variant="outline" onClick={() => void load(true)}><RefreshCw className="mr-2 h-4 w-4" />Refresh</Button></div>
        <div className="overflow-x-auto"><Table className="min-w-[1200px]"><TableHeader><TableRow><TableHead>Symbol</TableHead><TableHead>Condition</TableHead><TableHead>Target / Zone</TableHead><TableHead>Feed</TableHead><TableHead>Status</TableHead><TableHead>Last Price</TableHead><TableHead>Distance</TableHead><TableHead>Last Triggered</TableHead><TableHead>Count</TableHead><TableHead>Approach</TableHead><TableHead>Channel</TableHead><TableHead>Actions</TableHead></TableRow></TableHeader><TableBody>
          {alerts.length === 0 ? <TableRow><TableCell colSpan={12} className="py-10 text-center text-muted-foreground">No alerts created yet.</TableCell></TableRow> : alerts.map((row) => {
            const last = Number(row.last_price);
            let distance: number | null = null;
            if (Number.isFinite(last)) {
              if (row.target_price != null) {
                distance = Math.abs(Number(row.target_price) - last);
              } else if (row.zone_low != null && row.zone_high != null) {
                const low = Number(row.zone_low);
                const high = Number(row.zone_high);
                if (Number.isFinite(low) && Number.isFinite(high)) {
                  distance = last < low ? low - last : (last > high ? last - high : 0);
                }
              }
            }
            const channels = [row.telegram_enabled ? "Telegram" : null, row.whatsapp_enabled ? "WhatsApp" : null].filter(Boolean).join(" + ") || "None";
            return <TableRow key={row.id}><TableCell className="font-semibold">{row.symbol}</TableCell><TableCell>{conditionLabel(row.alert_type)}</TableCell><TableCell>{row.target_price != null ? numberText(row.target_price) : `${numberText(row.zone_low)} – ${numberText(row.zone_high)}`}</TableCell><TableCell>{row.provider}</TableCell><TableCell><div className="flex gap-1"><Badge className={statusClass(row.status)}>{row.status}</Badge><Badge className={statusClass(row.runtime_state)}>{row.runtime_state}</Badge></div></TableCell><TableCell>{numberText(row.last_price)}</TableCell><TableCell>{distance == null ? "—" : numberText(distance, 4)}</TableCell><TableCell>{formatDateTimeIST(row.last_triggered_at, { seconds: true })}</TableCell><TableCell>{row.trigger_count}</TableCell><TableCell>{row.approach_enabled ? <div className="flex flex-col gap-1"><span>{numberText(row.approach_distance)}</span><Badge className={statusClass(row.approach_state)}>{row.approach_state}</Badge></div> : "Off"}</TableCell><TableCell>{channels}</TableCell><TableCell><div className="flex gap-1"><Button title="Edit" size="icon" variant="ghost" onClick={() => editAlert(row)}><Edit3 className="h-4 w-4" /></Button>{row.status === "ACTIVE" ? <Button title="Disable" size="icon" variant="ghost" onClick={() => void runAction("disable", row)}><Pause className="h-4 w-4" /></Button> : <Button title="Enable" size="icon" variant="ghost" onClick={() => void runAction("enable", row)}><Play className="h-4 w-4" /></Button>}<Button title="Delete" size="icon" variant="ghost" onClick={() => void runAction("delete", row)}><Trash2 className="h-4 w-4" /></Button></div></TableCell></TableRow>;
          })}
        </TableBody></Table></div>
      </GlassCard>

      <GlassCard className="mt-6 p-5">
        <h2 className="text-xl font-bold">Alert History</h2><p className="mb-4 text-sm text-muted-foreground">Detailed timestamps and real measured API/internal latency.</p>
        <div className="overflow-x-auto"><Table className="min-w-[1050px]"><TableHeader><TableRow><TableHead>Symbol</TableHead><TableHead>Alert</TableHead><TableHead>Target / Zone</TableHead><TableHead>Trigger Price</TableHead><TableHead>Triggered At</TableHead><TableHead>Channel</TableHead><TableHead>Delivery</TableHead><TableHead>Feed→Server</TableHead><TableHead>Evaluation</TableHead><TableHead>Notify API</TableHead><TableHead>Total</TableHead></TableRow></TableHeader><TableBody>
          {history.length === 0 ? <TableRow><TableCell colSpan={11} className="py-10 text-center text-muted-foreground">No alert events yet.</TableCell></TableRow> : history.map((row) => <TableRow key={row.id} className="cursor-pointer" onClick={() => setDetail(row)}><TableCell className="font-semibold">{row.symbol}</TableCell><TableCell>{conditionLabel(row.condition_type)}</TableCell><TableCell>{eventTargetLabel(row)}</TableCell><TableCell>{numberText(row.trigger_price)}</TableCell><TableCell>{formatDateTimeIST(row.condition_detected_at, { seconds: true })}</TableCell><TableCell>{[row.telegram_status !== "DISABLED" ? "Telegram" : null, row.whatsapp_status !== "DISABLED" ? "WhatsApp" : null].filter(Boolean).join(" + ") || "None"}</TableCell><TableCell><div className="flex flex-wrap gap-1">{row.telegram_status !== "DISABLED" && <Badge className={statusClass(row.telegram_status)}>TG {row.telegram_status}</Badge>}{row.whatsapp_status !== "DISABLED" && <Badge className={statusClass(row.whatsapp_status)}>WA {row.whatsapp_status}</Badge>}</div></TableCell><TableCell>{row.feed_to_server_latency_ms ?? "—"} ms</TableCell><TableCell>{row.evaluation_latency_ms ?? "—"} ms</TableCell><TableCell>{row.notification_api_latency_ms ?? "—"} ms</TableCell><TableCell>{row.total_internal_latency_ms ?? "—"} ms</TableCell></TableRow>)}
        </TableBody></Table></div>
      </GlassCard>

      <Dialog open={!!detail} onOpenChange={(open) => !open && setDetail(null)}><DialogContent className="max-w-2xl"><DialogHeader><DialogTitle>Alert Event Timing</DialogTitle></DialogHeader>{detail && <div className="grid gap-3 text-sm md:grid-cols-2">{[
        ["Event", detail.id], ["Alert", detail.alert_id], ["Symbol", detail.symbol], ["Condition", conditionLabel(detail.condition_type)], ["Target / Zone", eventTargetLabel(detail)], ["Previous Price", numberText(detail.previous_price)], ["Trigger Price", numberText(detail.trigger_price)], ["Market Timestamp", formatDateTimeIST(detail.market_timestamp, { seconds: true })], ["Server Received", formatDateTimeIST(detail.server_received_at, { seconds: true })], ["Condition Detected", formatDateTimeIST(detail.condition_detected_at, { seconds: true })], ["Notification Queued", formatDateTimeIST(detail.notification_queued_at, { seconds: true })], ["Notification API Requested", formatDateTimeIST(detail.notification_sent_at, { seconds: true })], ["Notification API Response", formatDateTimeIST(detail.notification_response_at, { seconds: true })], ["Telegram Status", detail.telegram_status], ["WhatsApp Status", detail.whatsapp_status],
      ].map(([label, value]) => <div key={String(label)} className="rounded-lg border border-white/10 bg-white/5 p-3"><p className="text-xs text-muted-foreground">{String(label)}</p><p className="mt-1 break-all">{String(value)}</p></div>)}</div>}</DialogContent></Dialog>
    </PageShell>
  );
}
