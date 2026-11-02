"use client";

import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { marketHistoryApi, MarketHistoryAccount, MarketHistoryConfig, MarketHistoryRun, AdminMarketDataCatalog } from "@/lib/api/admin";
import { formatDateTimeIST } from "@/lib/timezone";
import { HistorySelect } from "./HistorySelect";
import { BrokerSymbolPicker } from "./BrokerSymbolPicker";

const field = "w-full rounded-xl border border-border/60 bg-card/30 px-3 py-2.5 text-sm text-foreground";
const errMessage = (e: any): string => String(e?.response?.data?.detail || e?.message || "History operation failed");
const validDates = (from: string, to: string): boolean => !!from && !!to && from <= to &&
  !Number.isNaN(Date.parse(`${from}T00:00:00Z`)) && !Number.isNaN(Date.parse(`${to}T00:00:00Z`));

/** Direct manual cTrader/TradeLocker history import; never modifies legacy MT5 import. */
export function CloudManualFetch({ provider, catalog }: { provider: "CTRADER" | "TRADELOCKER"; catalog: AdminMarketDataCatalog }) {
  const [accounts, setAccounts] = useState<MarketHistoryAccount[]>([]);
  const [accountPage, setAccountPage] = useState(1);
  const [accountTotal, setAccountTotal] = useState(0);
  const [accountId, setAccountId] = useState("");
  const [subId, setSubId] = useState("");
  const [instrumentId, setInstrumentId] = useState("");
  const [symbol, setSymbol] = useState("");
  const [timeframe, setTimeframe] = useState("5m");
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");
  const [busy, setBusy] = useState(false);
  const [recent, setRecent] = useState<MarketHistoryRun[]>([]);
  const [lastJob, setLastJob] = useState("");

  const [restored, setRestored] = useState(false);
  useEffect(() => {
    try {
      const stored = JSON.parse(sessionStorage.getItem(`algoagentx-cloud-manual-${provider}`) || "{}");
      setAccountId(stored.accountId || ""); setSubId(stored.subId || "");
      setInstrumentId(stored.instrumentId || ""); setSymbol(stored.symbol || "");
      setTimeframe(stored.timeframe || "5m"); setFromDate(stored.fromDate || ""); setToDate(stored.toDate || "");
    } catch { /* A stale browser selection is not required. */ }
    setRestored(true);
  }, [provider]);
  useEffect(() => {
    if (!restored) return;
    sessionStorage.setItem(`algoagentx-cloud-manual-${provider}`, JSON.stringify({accountId, subId, instrumentId, symbol, timeframe, fromDate, toDate}));
  }, [provider, restored, accountId, subId, instrumentId, symbol, timeframe, fromDate, toDate]);
  useEffect(() => {
    let active = true;
    void marketHistoryApi.accounts(accountPage, "", 100).then((res) => {
      if (!active) return;
      setAccounts(res.items.filter((a) => a.provider === provider && a.status === "CONNECTED" && a.history_supported));
      setAccountTotal(res.total);
    }).catch((e) => { if (active) toast.error(errMessage(e)); });
    return () => { active = false; };
  }, [provider, accountPage]);


  const selected = useMemo(() => accounts.find((a) => a.id === accountId), [accounts, accountId]);
  const timeframes = provider === "TRADELOCKER" ? ["1m", "5m", "15m", "30m", "1h", "4h", "1d"] :
    ["1m", "2m", "3m", "4m", "5m", "10m", "15m", "30m", "1h", "4h", "12h", "1d"];

  const reloadRuns = async () => {
    const result = await marketHistoryApi.runs(1);
    setRecent(result.items.filter((r) => r.id === lastJob || !lastJob).slice(0, 5));
  };

  const submit = async (preview: boolean) => {
    if (!accountId || !subId || !instrumentId || !symbol.trim()) {
      toast.error("Choose connected account, subaccount, instrument and exact broker symbol"); return;
    }
    if (!validDates(fromDate, toDate)) { toast.error("Choose valid From and To dates"); return; }
    const start = new Date(`${fromDate}T00:00:00Z`);
    const end = new Date(Date.parse(`${toDate}T00:00:00Z`) + 86400000);
    if (end.getTime() - start.getTime() > 120 * 86400000) {
      toast.error("Maximum 120 days per historical import. Split older data into separate ranges."); return;
    }
    setBusy(true);
    try {
      // Reuse an exact source configuration if it exists. Otherwise create one OFF
      // by default so a manual import cannot opt itself into scheduled fetching.
      let matched: MarketHistoryConfig | undefined;
      for (let page = 1; page <= 10; page++) {
        const res = await marketHistoryApi.configs(page);
        matched = res.items.find((c) => c.broker_account_id === accountId && c.subaccount_id === subId &&
          c.instrument_id === Number(instrumentId) && c.provider === provider &&
          c.broker_symbol === symbol.trim() && c.timeframe === timeframe);
        if (matched || page * 30 >= res.total) break;
      }
      if (!matched) {
        matched = await marketHistoryApi.create({broker_account_id: accountId, subaccount_id: subId,
          instrument_id: Number(instrumentId), broker_symbol: symbol.trim(), timeframe, enabled: false});
      }
      const job = await marketHistoryApi.manual(matched.id, start.toISOString(), end.toISOString(), preview);
      setLastJob(job.run_id);
      toast.success(`${preview ? "Preview" : "Fetch & Save"} queued for ${provider}. Open Automatic Daily Sync to review results.`);
      const res = await marketHistoryApi.runs(1);
      setRecent(res.items.filter((r) => r.id === job.run_id));
    } catch (e) {toast.error(errMessage(e));}
    finally {setBusy(false);}
  };

  return <div className="space-y-4 rounded-xl border border-border/60 bg-background/10 p-4">
    <div>
      <h3 className="text-sm font-semibold">{provider === "CTRADER" ? "cTrader Open API" : "TradeLocker"} • Fetch historical candles</h3>
      <p className="mt-1 text-xs text-muted-foreground">Choose an authorized connected account. Dates are UTC and inclusive. Results are written into source-isolated candles, never silently replacing existing backtests. Fetching runs on the separate history worker.</p>
    </div>
    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
      <label className="text-xs text-muted-foreground">Connected broker account
        <div className="mt-1"><HistorySelect value={accountId} onChange={v => {setAccountId(v);setSubId("");setSymbol("");}} placeholder={`Choose ${provider} account`} options={accounts.map(a => ({value:a.id,label:`${a.label} • user ${a.user} • ${a.mode}`}))} /></div>
      </label>
      <label className="text-xs text-muted-foreground">Trading subaccount
        <div className="mt-1"><HistorySelect value={subId} onChange={v => {setSubId(v);setSymbol("");}} placeholder="Choose trading account" options={(selected?.subaccounts || []).map(s => ({value:s.id,label:`${s.label} • ${s.environment}`}))} /></div>
      </label>
      <label className="text-xs text-muted-foreground">Market Master instrument
        <div className="mt-1"><HistorySelect value={instrumentId} onChange={v => {setInstrumentId(v);setSymbol("");}} placeholder="Select instrument" options={catalog.instruments.map(x => ({value:String(x.id),label:`${x.symbol} • ${x.exchange}`}))} /></div>
      </label>
      <label className="text-xs text-muted-foreground">Exact {provider} symbol
        <div className="mt-1"><BrokerSymbolPicker accountId={accountId} subId={subId} provider={provider}
          canonicalSymbol={catalog.instruments.find(x => String(x.id) === instrumentId)?.symbol || ""} value={symbol} onChange={setSymbol} /></div>
      </label>
      <label className="text-xs text-muted-foreground">Timeframe
        <div className="mt-1"><HistorySelect value={timeframe} onChange={setTimeframe} placeholder="Timeframe" options={timeframes.map(x => ({value:x,label:x}))} /></div>
      </label>
      <label className="text-xs text-muted-foreground">From (UTC)
        <input type="date" className={`${field} mt-1`} value={fromDate} onChange={(e) => setFromDate(e.target.value)} />
      </label>
      <label className="text-xs text-muted-foreground">To (UTC, inclusive)
        <input type="date" className={`${field} mt-1`} value={toDate} onChange={(e) => setToDate(e.target.value)} />
      </label>
      <div className="flex items-end gap-3">
        <Button variant="outline" disabled={busy || !subId || !validDates(fromDate, toDate)} onClick={() => void submit(true)}>Preview</Button>
        <Button disabled={busy || !subId || !validDates(fromDate, toDate)} onClick={() => void submit(false)}>{busy ? "Queuing…" : "Fetch & Save"}</Button>
      </div>
    </div>
    {accountTotal > 100 && <div className="flex gap-2 text-xs items-center">
      <Button variant="outline" size="sm" disabled={accountPage <= 1} onClick={() => setAccountPage((n) => n - 1)}>Previous accounts</Button>
      <span>Page {accountPage}</span>
      <Button variant="outline" size="sm" disabled={accountPage * 100 >= accountTotal} onClick={() => setAccountPage((n) => n + 1)}>Next accounts</Button>
    </div>}
    <div className="flex items-center gap-3 text-xs text-muted-foreground">
      <span>Manual cloud imports are opt-in and do not automatically enable the daily scheduler.</span>
      <Button size="sm" variant="outline" onClick={() => void reloadRuns().catch((e) => toast.error(errMessage(e)))}>Refresh job result</Button>
    </div>
    {lastJob && <p className="text-xs text-muted-foreground">Queued job ID: <code className="text-foreground">{lastJob}</code></p>}
    {recent.map((r) => <p key={r.id} className="rounded-lg border border-border/50 p-3 text-xs">
      <b>{r.status}</b> • Fetched {r.fetched}, inserted {r.inserted}, invalid {r.invalid}
      {r.last_after ? ` • Last candle ${formatDateTimeIST(r.last_after)}` : ""}
      {r.error ? <span className="block text-amber-300">{r.error}</span> : null}
    </p>)}
  </div>;
}
