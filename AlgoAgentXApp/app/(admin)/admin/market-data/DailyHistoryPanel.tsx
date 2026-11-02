"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { formatDateTimeIST } from "@/lib/timezone";
import { marketHistoryApi, MarketHistoryAccount, MarketHistoryConfig, MarketHistoryRun, MarketHistoryVerification, AdminMarketDataCatalog } from "@/lib/api/admin";
import { liveTradingApi } from "@/lib/api/live-trading";
import { HistorySelect } from "./HistorySelect";
import { BrokerSymbolPicker } from "./BrokerSymbolPicker";

const field = "rounded-xl border border-border/60 bg-card/25 px-3 py-2 text-sm text-foreground w-full";
const errorText = (e: any) => e?.response?.data?.detail || e?.message || "Operation failed";

export function DailyHistoryPanel({ catalog, view }: { catalog: AdminMarketDataCatalog; view: "daily" | "connect" }) {
  const [overview, setOverview] = useState<Awaited<ReturnType<typeof marketHistoryApi.overview>> | null>(null);
  const [accounts, setAccounts] = useState<MarketHistoryAccount[]>([]);
  const [accountPage, setAccountPage] = useState(1);
  const [accountTotal, setAccountTotal] = useState(0);
  const [search, setSearch] = useState("");
  const [configs, setConfigs] = useState<MarketHistoryConfig[]>([]);
  const [configPage, setConfigPage] = useState(1);
  const [configTotal, setConfigTotal] = useState(0);
  const [runs, setRuns] = useState<MarketHistoryRun[]>([]);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [accountId, setAccountId] = useState("");
  const [subId, setSubId] = useState("");
  const [instrumentId, setInstrumentId] = useState("");
  const [symbol, setSymbol] = useState("");
  const [editingConfig, setEditingConfig] = useState<MarketHistoryConfig | null>(null);
  const [fixedSymbol, setFixedSymbol] = useState("");
  const [verification, setVerification] = useState<MarketHistoryVerification | null>(null);
  const [verifyingId, setVerifyingId] = useState("");
  const [tf, setTf] = useState("5m");
  const [initialStart, setInitialStart] = useState("");
  const [manualFeedId, setManualFeedId] = useState("");
  const [manualFrom, setManualFrom] = useState("");
  const [manualTo, setManualTo] = useState("");
  const [connectClient, setConnectClient] = useState("");
  const [connectSecret, setConnectSecret] = useState("");
  const [connectLabel, setConnectLabel] = useState("cTrader Open API");
  const [redirectUri, setRedirectUri] = useState("");
  const [myAccountId, setMyAccountId] = useState("");
  const [myAccounts, setMyAccounts] = useState<any[]>([]);
  const [ctraderAccounts, setCtraderAccounts] = useState<any[]>([]);

  const [restored, setRestored] = useState(false);
  useEffect(() => {
    try {
      const stored = JSON.parse(sessionStorage.getItem("algoagentx-daily-history-selection") || "{}");
      setAccountId(stored.accountId || ""); setSubId(stored.subId || "");
      setInstrumentId(stored.instrumentId || ""); setSymbol(stored.symbol || "");
      setTf(stored.tf || "5m"); setInitialStart(stored.initialStart || "");
    } catch { /* Invalid browser selection is safely ignored. */ }
    setRestored(true);
  }, []);
  useEffect(() => {
    if (!restored) return;
    sessionStorage.setItem("algoagentx-daily-history-selection", JSON.stringify({accountId, subId, instrumentId, symbol, tf, initialStart}));
  }, [restored, accountId, subId, instrumentId, symbol, tf, initialStart]);
  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [meta, acct, cfg, history] = await Promise.all([
        marketHistoryApi.overview(), marketHistoryApi.accounts(accountPage, search),
        marketHistoryApi.configs(configPage), marketHistoryApi.runs(1),
      ]);
      setOverview(meta); setAccounts(acct.items); setAccountTotal(acct.total);
      setConfigs(cfg.items); setConfigTotal(cfg.total); setRuns(history.items);
    } catch (e) {
      toast.error(String(errorText(e)));
    } finally { setLoading(false); }
  }, [accountPage, configPage, search]);

  useEffect(() => { void load(); }, [load]);
  useEffect(() => {
    if (view !== "connect") return;
    void liveTradingApi.getBrokerRedirectUri("ctrader").then(x => setRedirectUri(x.redirect_uri)).catch(() => {});
    void liveTradingApi.listBrokerAccounts().then(x => setMyAccounts(x.filter(a => ["CTRADER", "CTRADER_API"].includes(String(a.broker_code || a.broker_name).toUpperCase())))).catch(() => {});
  }, [view]);

  const selected = useMemo(() => accounts.find(x => x.id === accountId), [accounts, accountId]);
  const choices = selected?.subaccounts || [];
  const verifyData = async (feedId: string) => {
    setVerifyingId(feedId); setVerification(null);
    try {
      const result = await marketHistoryApi.verify(feedId);
      setVerification(result);
      if (!result.source.count) toast.info("This broker feed has no saved candles yet.");
    } catch (e) { toast.error(String(errorText(e))); }
    finally { setVerifyingId(""); }
  };
  const doPublish = async (config: MarketHistoryConfig) => {
    if (!config.is_primary) { toast.error("Select Primary first"); return; }
    setBusy(true);
    try {
      const info = await marketHistoryApi.publishPreview(config.id);
      if (!info.source_rows) { toast.error("No stored source candles. Fetch & Save history first."); return; }
      const ok = window.confirm(`Publish ${info.missing_rows.toLocaleString()} missing ${config.broker_symbol} ${config.timeframe} candles to the BACKTEST market_data table?\n\n${info.overlapping_rows.toLocaleString()} timestamps already exist and will NOT be overwritten. ${info.different_ohlc_overlaps_preserved.toLocaleString()} overlapping OHLCV differences will be preserved as the original legacy values.\n\nThis makes a MIXED MT5 + ${config.provider} candle series. Provenance is audited. Continue?`);
      if (!ok) return;
      const result = await marketHistoryApi.publishMissing(config.id);
      toast.success(`Insert-missing-only publication queued (${result.run_id.slice(0,8)}). Refresh Coverage after the job finishes.`);
      await load();
    } catch (e) {toast.error(String(errorText(e)));}
    finally {setBusy(false);}
  };
  const doAction = async (action: () => Promise<unknown>, message: string) => {
    setBusy(true);
    try { await action(); toast.success(message); await load(); }
    catch (e) { toast.error(String(errorText(e))); }
    finally { setBusy(false); }
  };

  if (view === "connect") return (
    <div className="space-y-5">
      <div className="rounded-xl border border-primary/30 bg-primary/5 p-4 text-sm">
        <h3 className="font-semibold">Connect cTrader Open API — priority</h3>
        <p className="mt-1 text-xs text-muted-foreground">Connect your own cTrader account here using the existing secure OAuth flow. Other users must authorize their own connections; this admin page can configure their existing connected accounts, but cannot impersonate them.</p>
      </div>
      <div className="grid gap-3 md:grid-cols-2">
        <label className="text-xs text-muted-foreground">Account label<input className={`${field} mt-1`} value={connectLabel} onChange={e => setConnectLabel(e.target.value)} /></label>
        <label className="text-xs text-muted-foreground">Client ID<input className={`${field} mt-1`} value={connectClient} onChange={e => setConnectClient(e.target.value)} autoComplete="off" /></label>
        <label className="text-xs text-muted-foreground">Client secret<input type="password" className={`${field} mt-1`} value={connectSecret} onChange={e => setConnectSecret(e.target.value)} autoComplete="new-password" /></label>
        <label className="text-xs text-muted-foreground">Required callback URL (add to your cTrader developer app)<input className={`${field} mt-1`} value={redirectUri} readOnly /></label>
      </div>
      <Button disabled={busy || !connectClient.trim() || !connectSecret.trim() || !redirectUri} onClick={() => void doAction(async () => {
        const result = await liveTradingApi.connectCtraderOAuth({account_label: connectLabel, client_id: connectClient,
          client_secret: connectSecret, redirect_uri: redirectUri, redirect_after: "/admin/market-data?tab=connect"});
        setConnectSecret("");
        window.location.assign(result.auth_url);
      }, "Opening cTrader authorization")}>Connect with cTrader OAuth</Button>
      <div className="border-t border-border/60 pt-4">
        <p className="mb-3 text-sm font-semibold">Sync/select my cTrader trading account</p>
        <div className="flex flex-wrap gap-2">
          <div className="w-full max-w-sm"><HistorySelect value={myAccountId} onChange={v => {setMyAccountId(v); setCtraderAccounts([]);}} placeholder="Choose my connected cTrader account" options={myAccounts.map(a => ({value:a.id,label:`${a.account_label} • ${String(a.id).slice(-6)}`}))} /></div>
          <Button variant="outline" disabled={!myAccountId || busy} onClick={() => void doAction(async () => {
            const result = await liveTradingApi.getCtraderAccounts(myAccountId);
            setCtraderAccounts(result.accounts || []);
          }, "cTrader account list refreshed")}>Discover trading accounts</Button>
        </div>
        {ctraderAccounts.length > 0 && <div className="mt-3 flex flex-wrap gap-2">
          {ctraderAccounts.map((x, i) => {
            const id = String(x.ctrader_account_id || x.account_number || "");
            return <Button key={`${id}-${i}`} variant="outline" disabled={busy || !id} onClick={() => void doAction(async () => {
              await liveTradingApi.selectCtraderAccount(myAccountId, id);
            }, `Selected cTrader •••${id.slice(-4)}`)}>Select •••{id.slice(-4)} ({x.account_type || (x.is_live ? "LIVE" : "DEMO")})</Button>;
          })}
        </div>}
      </div>
      <div className="text-xs text-muted-foreground">MT5, TradeLocker and other account connection forms remain available under the existing Brokers page. Use that page to connect them, then choose their accounts in Automatic Daily Sync here. The current connection flow and credentials remain unchanged.</div>
      <a href="/brokers" className="inline-block text-sm text-primary underline">Open full Broker Connections</a>
    </div>
  );

  return <div className="space-y-5">
    <div className="flex flex-wrap items-center justify-between gap-2">
      <div><h3 className="text-base font-semibold">Automatic Daily Sync</h3>
        <p className="text-xs text-muted-foreground">One batch at 03:00 IST, cTrader first. Source-isolated historical candles; no live trading worker changes.</p></div>
      <Button variant="outline" onClick={() => void load()} disabled={loading}>{loading ? "Loading…" : "Refresh Status"}</Button>
    </div>
    <div className="grid gap-3 md:grid-cols-3 text-sm">
      <div className="rounded-xl border border-border/60 p-3"><p className="text-xs text-muted-foreground">Global schedule</p><b>{overview?.feature_enabled ? "Enabled" : "OFF — env flag"}</b></div>
      <div className="rounded-xl border border-border/60 p-3"><p className="text-xs text-muted-foreground">Next scheduled</p><b>{overview?.next_scheduled_at ? formatDateTimeIST(overview.next_scheduled_at) : "—"}</b></div>
      <div className="rounded-xl border border-border/60 p-3"><p className="text-xs text-muted-foreground">Enabled feeds</p><b>{overview?.enabled_count || 0} / {overview?.config_count || 0}</b></div>
    </div>
    {!overview?.feature_enabled && <p className="rounded-lg border border-amber-500/30 p-3 text-xs text-amber-200">Automatic 03:00 scheduling is OFF. Set MARKET_DATA_DAILY_SYNC_ENABLED=true on the dedicated scheduler/worker after applying SQL. Explicit Run Now remains available.</p>}
    <form onSubmit={e => {e.preventDefault(); void doAction(async () => {
      if (!accountId || !subId || !instrumentId || !symbol.trim()) throw new Error("Account, trading subaccount, instrument and verified broker symbol are required");
      const data = await marketHistoryApi.create({ broker_account_id: accountId, subaccount_id: subId,
        instrument_id: Number(instrumentId), broker_symbol: symbol.trim(), timeframe: tf,
        initial_start: initialStart ? `${initialStart}T00:00:00Z` : null, enabled: false });
      setInitialStart("");
      return data;
    }, "Isolated feed created (OFF by default). Enable when ready."); }} className="rounded-xl border border-border/60 p-4 space-y-3">
      <h4 className="text-sm font-semibold">Add broker feed configuration</h4>
      <p className="text-xs text-muted-foreground">For long backfills, choose an initial UTC date. If blank, Run Now downloads the latest 7 days on an empty feed, then future runs fetch incrementally from the last stored closed candle. Account must already be connected and authorized.</p>
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3 items-start">
        <label className="min-w-0 space-y-1 text-xs text-violet-200">Connected broker account
          <HistorySelect value={accountId} onChange={v => {setAccountId(v);setSubId("");setSymbol("");}} placeholder="Choose connected account" options={accounts.map(a => ({value:a.id,label:`${a.provider} • ${a.label} • user ${a.user} • ${a.status}`}))} />
        </label>
        <label className="min-w-0 space-y-1 text-xs text-violet-200">Trading subaccount
          <HistorySelect value={subId} onChange={v => {setSubId(v);setSymbol("");}} disabled={!accountId || choices.length === 0} placeholder={!accountId ? "Choose a broker account first" : choices.length ? "Choose trading subaccount" : "No linked trading subaccounts"} options={choices.map(a => ({value:a.id,label:`${a.label} • ${a.environment}`}))} />
        </label>
        <label className="min-w-0 space-y-1 text-xs text-violet-200">Market Master instrument
          <HistorySelect value={instrumentId} onChange={v => {setInstrumentId(v);setSymbol("");}} placeholder="Select instrument" options={catalog.instruments.map(x => ({value:String(x.id),label:`${x.symbol} • ${x.exchange}`}))} />
        </label>
        <div className="min-w-0 space-y-1 text-xs text-violet-200"><span>Exact broker symbol</span>
          <BrokerSymbolPicker accountId={accountId} subId={subId} provider={selected?.provider || ""}
            canonicalSymbol={catalog.instruments.find(x => String(x.id) === instrumentId)?.symbol || ""} value={symbol} onChange={setSymbol} />
        </div>
        <label className="min-w-0 self-start space-y-1 text-xs text-violet-200">Timeframe
          <HistorySelect className="!h-10 !min-h-10" value={tf} onChange={setTf} placeholder="Timeframe" options={(selected?.provider === "TRADELOCKER" ? ["1m", "5m", "15m", "30m", "1h", "4h", "1d"] : ["1m", "2m", "3m", "4m", "5m", "10m", "15m", "30m", "1h", "4h", "12h", "1d"]).map(x => ({value:x,label:x}))} />
        </label>
        <label className="text-xs text-muted-foreground">Initial history start (UTC, optional)<input type="date" className={`${field} mt-1`} value={initialStart} onChange={e => setInitialStart(e.target.value)} /></label>
      </div>
      {selected && <p className="text-xs text-muted-foreground">{selected.provider}: {selected.capability}. {selected.history_supported ? "Historical API available" : "Daily history unsupported; connect a cTrader/TradeLocker account"}</p>}
      <Button disabled={busy || !selected?.history_supported || selected?.status !== "CONNECTED"} type="submit">Add Feed (disabled by default)</Button>
    </form>
    <form className="space-y-3 rounded-xl border border-border/60 p-4" onSubmit={e => {e.preventDefault();
      const start = new Date(`${manualFrom}T00:00:00Z`);
      const endExclusive = new Date(new Date(`${manualTo}T00:00:00Z`).getTime() + 86400000);
      if (!manualFeedId || !manualFrom || !manualTo || Number.isNaN(start.getTime()) || Number.isNaN(endExclusive.getTime())) { toast.error("Select feed and start/end dates"); return; }
      void doAction(() => marketHistoryApi.manual(manualFeedId, start.toISOString(), endExclusive.toISOString(), false), "Manual date-range historical fetch queued");
    }}>
      <h4 className="text-sm font-semibold">Manual cTrader / TradeLocker date-range fetch</h4>
      <p className="text-xs text-muted-foreground">Preserves the existing MT5 manual tab. For cloud brokers, historical candles are fetched into their isolated feed through the same low-priority history worker (up to 120 days per job). For older years, run additional date ranges.</p>
      <div className="grid gap-3 md:grid-cols-3">
        <HistorySelect value={manualFeedId} onChange={setManualFeedId} placeholder="Select configured feed" options={configs.map(c => ({value:c.id,label:`${c.provider} / ${c.broker_symbol} / ${c.timeframe} / •••${c.subaccount_id.slice(-4)}`}))} />
        <label className="text-xs text-muted-foreground">From (UTC)<input type="date" required className={`${field} mt-1`} value={manualFrom} onChange={e => setManualFrom(e.target.value)} /></label>
        <label className="text-xs text-muted-foreground">To (inclusive, UTC)<input type="date" required className={`${field} mt-1`} value={manualTo} onChange={e => setManualTo(e.target.value)} /></label>
      </div>
      <div className="flex flex-wrap gap-2"><Button type="button" disabled={busy || !manualFeedId || !manualFrom || !manualTo} variant="outline" onClick={() => {
        const start = new Date(`${manualFrom}T00:00:00Z`), end = new Date(new Date(`${manualTo}T00:00:00Z`).getTime() + 86400000);
        if (end <= start) { toast.error("End date must not precede start date"); return; }
        void doAction(() => marketHistoryApi.manual(manualFeedId, start.toISOString(), end.toISOString(), true), "Preview queued. No data will be saved.");
      }}>Preview / Dry Run</Button>
      <Button type="submit" disabled={busy || !manualFeedId || !manualFrom || !manualTo}>Fetch & Save Range</Button></div>
    </form>
    <p className="rounded-lg border border-border/60 bg-background/20 p-3 text-xs text-muted-foreground"><b className="text-foreground">Primary</b> chooses the ONE broker source allowed to fill absent backtest timestamps. On an existing MT5 dataset, click <b>Publish Missing</b> and explicitly approve mixing the sources. Existing MT5 prices are NEVER overwritten. Previously imported source candles and future daily imports can then fill missing canonical timestamps; all new published timestamps are audited.</p>
    <div className="overflow-x-auto rounded-xl border border-border/60">
      <table className="w-full min-w-[1540px] text-left text-xs">
        <thead className="border-b border-border/60 bg-background/20"><tr>{["Broker / Account", "Instrument / Symbol", "Timeframe", "Stored candles", "Last source candle / UTC grid target", "Result", "Primary", "Auto Fetch", "Actions"].map(x => <th className="p-3" key={x}>{x}</th>)}</tr></thead>
        <tbody>{configs.map(c => <tr className="border-b border-border/40" key={c.id}>
          <td className="p-3">{c.provider}<div className="text-muted-foreground">•••{c.subaccount_id.slice(-4)}</div></td>
          <td className="p-3">{catalog.instruments.find(x => x.id === c.instrument_id)?.symbol || c.instrument_id}<div className="text-muted-foreground">{c.broker_symbol}</div></td>
          <td className="p-3">{c.timeframe}</td>
          <td className="p-3"><b>{Number(c.source_count ?? 0).toLocaleString()}</b><div className="text-muted-foreground">{c.source_first ? `Since ${formatDateTimeIST(c.source_first)}` : "No saved source candles"}</div></td>
          <td className="p-3">{c.last_candle ? formatDateTimeIST(c.last_candle) : "NEEDS_INITIAL_IMPORT"}<div className="text-muted-foreground">Target*: {formatDateTimeIST(c.expected_last_closed_utc)}</div></td>
          <td className="p-3">{c.last_status}<div className="max-w-44 text-muted-foreground">{c.last_error}</div></td>
          <td className="p-3">{c.is_primary ? (c.publish_approved ? "Primary • gap-fill ON" : "Primary • awaiting approval") : "Secondary"}</td>
          <td className="p-3"><input aria-label={`Auto fetch ${c.broker_symbol}`} type="checkbox" disabled={busy} checked={c.enabled} onChange={e => void doAction(() => marketHistoryApi.edit(c.id, {enabled: e.target.checked}), e.target.checked ? "Feed enabled" : "Feed disabled")} /></td>
          <td className="p-3"><div className="flex gap-2">
            <Button size="sm" variant="outline" disabled={verifyingId === c.id} title="Read the saved candle count and OHLCV samples directly from PostgreSQL" onClick={() => void verifyData(c.id)}>{verifyingId === c.id ? "Checking…" : "Verify Stored Data"}</Button>
            <Button size="sm" variant="outline" title={c.last_candle || c.initial_start ? "Fetch missing closed candles since last stored candle or configured initial date" : "No history yet: bootstrap the latest 7 days, then sync incrementally"} disabled={busy || ["QUEUED", "RUNNING"].includes(c.last_status)} onClick={() => void doAction(() => marketHistoryApi.run(c.id), c.last_candle || c.initial_start ? "Incremental history sync queued" : "Last 7 days bootstrap queued (new source)")}>Run Now</Button>
            {c.is_primary && <Button size="sm" variant="outline" disabled={busy || Number(c.source_count || 0) === 0} title="Explicitly fill missing canonical backtest timestamps, preserve existing MT5 OHLCV" onClick={() => void doPublish(c)}>Publish Missing</Button>}
            <Button size="sm" variant="outline" disabled={busy || ["QUEUED", "RUNNING"].includes(c.last_status)} title="Correct an incorrect broker symbol before candles have been stored" onClick={() => {setEditingConfig(c);setFixedSymbol("");}}>Fix Symbol</Button>
            {!c.is_primary && <Button size="sm" variant="outline" title="Choose one primary broker source for backtest gap filling. Overlap is never overwritten and existing MT5 rows stay unchanged." disabled={busy} onClick={() => {
              if (window.confirm("Set this feed as Primary? Existing MT5/backtest candle prices remain unchanged. Use Publish Missing to explicitly approve adding absent timestamps from this broker."))
                void doAction(async () => { const r = await marketHistoryApi.primary(c.id); toast.info(r.note); }, "Primary selected");
            }}>Primary</Button>}
            <Button size="sm" variant="ghost" disabled={busy} onClick={() => {if (window.confirm("Disable automatic fetching? The feed remains listed, with candles and history retained.")) void doAction(() => marketHistoryApi.disable(c.id), "Feed disabled");}}>Disable</Button>
            <Button size="sm" variant="outline" disabled={busy} title="Remove this row from schedule and active list, but keep historical candles and run audit" onClick={() => {if (window.confirm(`DELETE ${c.provider} ${c.broker_symbol} ${c.timeframe} from scheduled configurations?\n\nStored candles and all audit records will be preserved. This cannot run while a job is queued or running.`)) void doAction(() => marketHistoryApi.archive(c.id), "Schedule configuration deleted; stored candles preserved");}}>Delete</Button>
          </div></td>
        </tr>)}</tbody>
      </table>
      {configs.length === 0 && <p className="p-5 text-xs text-muted-foreground">No configured feeds yet. Select an account, trading subaccount, instrument and timeframe above.</p>}
    </div>
    {verification && <section aria-label="Saved broker candle verification" className="space-y-3 rounded-xl border border-emerald-400/35 bg-[#241444]/55 p-4 text-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div><h4 className="font-semibold">Verified PostgreSQL storage • {verification.provider} {verification.broker_symbol} {verification.timeframe}</h4>
          <p className="mt-1 text-xs text-violet-200">Read-only inspection. Primary/secondary settings do not automatically copy candles into the legacy backtest table.</p></div>
        <Button type="button" variant="outline" size="sm" onClick={() => setVerification(null)}>Close</Button>
      </div>
      <div className="grid gap-3 md:grid-cols-2">
        <div className="rounded-lg border border-emerald-400/30 bg-emerald-900/15 p-3">
          <p className="text-xs text-emerald-200">Broker source candles • market_data_feed_candles</p>
          <p className="mt-1 text-2xl font-semibold text-white">{verification.source.count.toLocaleString()}</p>
          <p className="mt-1 text-xs text-violet-100">First: {verification.source.first ? formatDateTimeIST(verification.source.first) : "—"}</p>
          <p className="text-xs text-violet-100">Last: {verification.source.last ? formatDateTimeIST(verification.source.last) : "—"}</p>
        </div>
        <div className="rounded-lg border border-violet-400/30 bg-violet-900/15 p-3">
          <p className="text-xs text-violet-200">Legacy backtest candles • market_data</p>
          <p className="mt-1 text-2xl font-semibold text-white">{verification.canonical.count.toLocaleString()}</p>
          <p className="mt-1 text-xs text-violet-100">First: {verification.canonical.first ? formatDateTimeIST(verification.canonical.first) : "—"}</p>
          <p className="text-xs text-violet-100">Last: {verification.canonical.last ? formatDateTimeIST(verification.canonical.last) : "—"}</p>
        </div>
      </div>
      {verification.source.count > 0 ? <p className="text-xs text-emerald-200">Confirmed: OHLCV rows are saved in PostgreSQL for this exact broker feed.</p>
        : <p className="text-xs text-amber-200">No saved broker candle rows yet. Preview/dry run does not store candles; check the latest completed run.</p>}
      {verification.last_run_dry_run && <p className="text-xs text-amber-200">The most recent job was a preview (dry run), which intentionally does not insert candles.</p>}
      <div className="overflow-x-auto rounded-lg border border-violet-400/20">
        <table className="w-full min-w-[540px] text-left text-xs"><thead className="bg-violet-900/30"><tr>{["UTC candle / IST display", "Open", "High", "Low", "Close", "Volume"].map(h => <th className="p-2" key={h}>{h}</th>)}</tr></thead>
          <tbody>{verification.latest_candles.map(c => <tr key={c.timestamp} className="border-t border-violet-400/15"><td className="p-2">{formatDateTimeIST(c.timestamp)}</td><td className="p-2">{c.open}</td><td className="p-2">{c.high}</td><td className="p-2">{c.low}</td><td className="p-2">{c.close}</td><td className="p-2">{c.volume}</td></tr>)}</tbody>
        </table>
      </div>
    </section>}
    {editingConfig && <div className="rounded-xl border border-violet-400/40 bg-[#241444]/45 p-4 space-y-3">
      <h4 className="text-sm font-semibold">Fix broker symbol • {editingConfig.provider} / •••{editingConfig.subaccount_id.slice(-4)}</h4>
      <p className="text-xs text-violet-200">Saved: {editingConfig.broker_symbol}. Choose the exact symbol from this account. Existing candles cannot be relabeled or mixed with another broker source.</p>
      <BrokerSymbolPicker accountId={editingConfig.broker_account_id} subId={editingConfig.subaccount_id} provider={editingConfig.provider}
        canonicalSymbol={catalog.instruments.find(x => x.id === editingConfig.instrument_id)?.symbol || ""} value={fixedSymbol} onChange={setFixedSymbol} />
      <div className="flex gap-2"><Button disabled={busy || !fixedSymbol || fixedSymbol.toUpperCase() === editingConfig.broker_symbol.toUpperCase()} onClick={() => void doAction(async () => {
        await marketHistoryApi.edit(editingConfig.id, {broker_symbol:fixedSymbol}); setEditingConfig(null);setFixedSymbol("");
      }, "Broker symbol corrected; run the feed again")}>Save exact symbol</Button>
      <Button variant="outline" type="button" onClick={() => setEditingConfig(null)}>Cancel</Button></div>
    </div>}
    <div className="flex gap-3 text-xs"><Button variant="outline" disabled={configPage <= 1} onClick={() => setConfigPage(x => x-1)}>Previous</Button><span className="self-center">{configPage} / {Math.max(1, Math.ceil(configTotal / 30))}</span><Button variant="outline" disabled={configPage*30 >= configTotal} onClick={() => setConfigPage(x => x+1)}>Next</Button></div>
    <div className="space-y-3"><h4 className="text-sm font-semibold">All users' connected accounts (masked)</h4><input value={search} onChange={e => {setSearch(e.target.value); setAccountPage(1);}} className={field} placeholder="Filter account label" />
      <div className="overflow-x-auto rounded-xl border border-border/60"><table className="w-full min-w-[700px] text-left text-xs"><thead><tr>{["Owner", "Provider", "Account", "Mode", "Connection", "History", "Subaccounts"].map(x => <th className="p-3" key={x}>{x}</th>)}</tr></thead>
      <tbody>{accounts.map(a => <tr key={a.id} className="border-t border-border/40"><td className="p-3">{a.user}</td><td className="p-3">{a.provider}</td><td className="p-3">{a.label}</td><td className="p-3">{a.mode}</td><td className="p-3">{a.status}</td><td className="p-3">{a.capability}</td><td className="p-3">{a.subaccounts.map(s => s.label).join(", ") || "Select in Brokers"}</td></tr>)}</tbody></table></div>
      <div className="flex gap-3 text-xs"><Button variant="outline" disabled={accountPage <= 1} onClick={() => setAccountPage(x => x-1)}>Previous</Button><span className="self-center">{accountPage} / {Math.max(1, Math.ceil(accountTotal / 30))}</span><Button variant="outline" disabled={accountPage*30 >= accountTotal} onClick={() => setAccountPage(x => x+1)}>Next</Button></div>
    </div>
    <div className="space-y-2"><h4 className="text-sm font-semibold">Recent daily/manual sync runs</h4>
      <div className="overflow-x-auto rounded-xl border border-border/60"><table className="w-full min-w-[650px] text-left text-xs"><thead><tr>{["Started", "Status", "Fetched", "Inserted", "Published from new sync", "Invalid", "Last after"].map(x => <th className="p-3" key={x}>{x}</th>)}</tr></thead><tbody>{runs.map(r => <tr className="border-t border-border/40" key={r.id}><td className="p-3">{formatDateTimeIST(r.started_at)}</td><td className="p-3">{r.status} {r.error || ""}</td><td className="p-3">{r.fetched}</td><td className="p-3">{r.inserted}</td><td className="p-3">{r.updated ?? 0}</td><td className="p-3">{r.invalid}</td><td className="p-3">{formatDateTimeIST(r.last_after)}</td></tr>)}</tbody></table></div>
    </div>
    <p className="text-xs text-muted-foreground">*The UTC grid target is not a market-hours calendar. Primary + Publish Missing allows explicitly approved insert-only mixing of historical broker sources; existing canonical OHLCV never changes on overlap. To repair gaps missing from the source feed itself, use the manual cTrader/TradeLocker date-range fetch, then republish. Delete archives a configuration and retains source candles/audit.</p>
  </div>;
}
