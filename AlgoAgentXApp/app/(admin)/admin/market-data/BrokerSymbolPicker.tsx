"use client";

import { useEffect, useMemo, useState } from "react";
import { Loader2, RotateCw } from "lucide-react";
import { marketHistoryApi, type MarketHistoryBrokerSymbol } from "@/lib/api/admin";
import { HistorySelect } from "./HistorySelect";

function normalized(symbol: string) {
  return symbol.toUpperCase().replace(/[^A-Z0-9]/g, "");
}

/** Choose the exact symbol FROM the chosen trading subaccount. Never copy MT5's broker_symbol. */
export function BrokerSymbolPicker({ accountId, subId, canonicalSymbol, provider, value, onChange }: {
  accountId: string; subId: string; canonicalSymbol: string; provider: string;
  value: string; onChange: (value: string) => void;
}) {
  const [symbols, setSymbols] = useState<MarketHistoryBrokerSymbol[]>([]);
  const [loadedFor, setLoadedFor] = useState("");
  const key = `${accountId}:${subId}`;
  const availableSymbols = useMemo(() => loadedFor === key ? symbols : [], [loadedFor, key, symbols]);
  const [search, setSearch] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [refresh, setRefresh] = useState(0);
  useEffect(() => {
    let cancelled = false;
    setSymbols([]); setLoadedFor(""); setError(""); setSearch("");
    if (!accountId || !subId) return;
    setBusy(true);
    marketHistoryApi.symbols(accountId, subId).then(result => {
      if (!cancelled) { setSymbols(result.items); setLoadedFor(`${accountId}:${subId}`); }
    }).catch((err: any) => {
      if (!cancelled) setError(String(err?.response?.data?.detail || err?.message || "Broker symbol discovery failed"));
    }).finally(() => { if (!cancelled) setBusy(false); });
    return () => { cancelled = true; };
  }, [accountId, subId, refresh]);

  // An exact match wins. A unique account-provided suffix variant (e.g. XAUUSD.x)
  // is allowed; never guess when multiple variants exist.
  useEffect(() => {
    if (!canonicalSymbol || availableSymbols.length === 0 || value) return;
    const target = canonicalSymbol.toUpperCase();
    const exact = availableSymbols.find(item => item.symbol.toUpperCase() === target);
    const alternatives = availableSymbols.filter(item => {
      const name = normalized(item.symbol), base = normalized(target);
      return name === base || (base.length >= 6 && name.startsWith(base) && name.length <= base.length + 2);
    });
    if (exact) onChange(exact.symbol);
    else if (alternatives.length === 1) onChange(alternatives[0].symbol);
  }, [canonicalSymbol, availableSymbols, value, onChange]);

  const filtered = useMemo(() => {
    const needle = search.trim().toUpperCase();
    const matching = availableSymbols.filter(item => !needle || item.symbol.toUpperCase().includes(needle) || (item.description || "").toUpperCase().includes(needle));
    return matching.slice(0, 80);
  }, [availableSymbols, search]);
  const options = filtered.map(item => ({value: item.symbol, label: item.description && item.description !== item.symbol ? `${item.symbol} — ${item.description}` : item.symbol}));
  if (value && !options.some(o => o.value === value)) options.unshift({value, label: value});
  const verified = availableSymbols.some(item => item.symbol.toUpperCase() === value.toUpperCase());
  return <div className="min-w-0 space-y-1.5">
    <div className="flex gap-2">
      <input value={search} onChange={e => setSearch(e.target.value)} aria-label="Filter broker symbols" placeholder="Search symbols (XAUUSD, BTCUSD...)"
        className="min-w-0 flex-1 rounded-xl border border-violet-400/25 bg-[#321c60]/90 px-3 py-2 text-sm text-violet-50 outline-none placeholder:text-violet-200/65 focus:ring-2 focus:ring-fuchsia-400/45" />
      <button type="button" onClick={() => setRefresh(x => x + 1)} disabled={!accountId || !subId || busy} title="Reload exact broker symbols" aria-label="Reload broker symbols" className="rounded-xl border border-violet-400/30 px-3 text-violet-50 hover:bg-fuchsia-500/15 disabled:opacity-50">
        {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <RotateCw className="h-4 w-4" />}
      </button>
    </div>
    <HistorySelect value={value} onChange={onChange} options={options} disabled={!accountId || !subId || busy || !!error || availableSymbols.length === 0} placeholder={busy ? "Loading symbols from broker…" : `Choose exact ${provider || "broker"} symbol`} />
    {error ? <p role="alert" className="text-xs text-amber-200">{error} — confirm the account is connected and use reload.</p> :
      <p className="text-[11px] text-violet-200/80">{value ? (verified ? `Verified on this account: ${value}` : `Not verified on this account: ${value}. Select a listed symbol.`) : (availableSymbols.length ? `${availableSymbols.length} broker symbols loaded. Choose the exact account symbol.` : "Choose an account and trading subaccount first.")}</p>}
  </div>;
}
