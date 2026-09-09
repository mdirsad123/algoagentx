"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { ChevronLeft, ChevronRight, Eye, Loader2, RefreshCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { fundedBacktestsApi, fundedReportingApi, type FundedHistoryItem, type FundedAccountProfile } from "@/lib/api/funded-backtests";
import { backtestsApi, type StrategyOption, type InstrumentOption } from "@/lib/api/backtests";
import { dateText, money, percent, statusClass, statusLabel } from "@/components/funded-backtest/report-utils";
import { parseApiError } from "@/lib/api/error";

const PAGE_SIZE = 20;
const statuses = ["ALL", "PASSED", "FAILED_DAILY_DD", "FAILED_MAX_DD", "FAILED_OTHER_RULE", "INCOMPLETE", "PAYOUT_ELIGIBLE", "PAYOUT_READY", "SIMULATION_ERROR"];

export default function FundedBacktestHistoryWorkspace() {
  const [items, setItems] = useState<FundedHistoryItem[]>([]);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [counts, setCounts] = useState<Record<string, number>>({});
  const [status, setStatus] = useState("ALL");
  const [profileId, setProfileId] = useState("ALL"); const [strategyId, setStrategyId] = useState("ALL"); const [instrumentId, setInstrumentId] = useState("ALL");
  const [profiles, setProfiles] = useState<FundedAccountProfile[]>([]); const [strategies, setStrategies] = useState<StrategyOption[]>([]); const [instruments, setInstruments] = useState<InstrumentOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true); setError("");
    try {
      const data = await fundedReportingApi.listRuns({ page, page_size: PAGE_SIZE, status: status === "ALL" ? undefined : status, profile_id: profileId === "ALL" ? undefined : profileId, strategy_id: strategyId === "ALL" ? undefined : strategyId, instrument_id: instrumentId === "ALL" ? undefined : Number(instrumentId) });
      setItems(data.items || []); setTotal(data.total || 0); setCounts(data.status_counts || {});
    } catch (err) { setError(parseApiError(err).message); }
    finally { setLoading(false); }
  }, [page, status, profileId, strategyId, instrumentId]);
  useEffect(() => { void load(); }, [load]);
  useEffect(() => { Promise.all([fundedBacktestsApi.listProfiles(), backtestsApi.getStrategiesCatalog(), backtestsApi.getInstruments()]).then(([p,s,i])=>{setProfiles(p);setStrategies(s);setInstruments(i)}).catch(()=>{}); }, []);
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const failed = useMemo(() => Object.entries(counts).filter(([k]) => k.startsWith("FAILED")).reduce((a,[,v])=>a+v,0), [counts]);

  return <div className="mx-auto w-full max-w-[1600px] space-y-6">
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">{[
      ["Total Runs", total], ["Passed", counts.PASSED || 0], ["Failed", failed], ["Incomplete", counts.INCOMPLETE || 0], ["Payout Ready", counts.PAYOUT_READY || 0],
    ].map(([k,v]) => <Card key={String(k)}><CardContent className="p-4"><p className="text-xs uppercase tracking-wide text-muted-foreground">{k}</p><p className="mt-2 text-2xl font-bold">{v}</p></CardContent></Card>)}</div>
    <Card><CardHeader><div className="flex flex-wrap items-center justify-between gap-3"><CardTitle>Simulation History</CardTitle><div className="flex flex-wrap gap-2"><Select value={status} onValueChange={(v)=>{setStatus(v);setPage(1)}}><SelectTrigger className="w-[190px]"><SelectValue/></SelectTrigger><SelectContent className="border-white/20 bg-[#241044] text-white">{statuses.map(s=><SelectItem key={s} value={s}>{s === "ALL" ? "All statuses" : statusLabel(s)}</SelectItem>)}</SelectContent></Select><Select value={profileId} onValueChange={(v)=>{setProfileId(v);setPage(1)}}><SelectTrigger className="w-[180px]"><SelectValue placeholder="All accounts"/></SelectTrigger><SelectContent className="bg-[#241044] text-white"><SelectItem value="ALL">All accounts</SelectItem>{profiles.map(p=><SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>)}</SelectContent></Select><Select value={strategyId} onValueChange={(v)=>{setStrategyId(v);setPage(1)}}><SelectTrigger className="w-[200px]"><SelectValue placeholder="All strategies"/></SelectTrigger><SelectContent className="bg-[#241044] text-white"><SelectItem value="ALL">All strategies</SelectItem>{strategies.map(x=><SelectItem key={x.id} value={String(x.id)}>{x.name}</SelectItem>)}</SelectContent></Select><Select value={instrumentId} onValueChange={(v)=>{setInstrumentId(v);setPage(1)}}><SelectTrigger className="w-[180px]"><SelectValue placeholder="All markets"/></SelectTrigger><SelectContent className="bg-[#241044] text-white"><SelectItem value="ALL">All markets</SelectItem>{instruments.map(x=><SelectItem key={x.id} value={String(x.id)}>{x.symbol}</SelectItem>)}</SelectContent></Select><Button variant="outline" size="icon" onClick={()=>void load()}><RefreshCcw className="h-4 w-4"/></Button></div></div></CardHeader><CardContent>
      {loading ? <div className="flex min-h-48 items-center justify-center gap-2 text-muted-foreground"><Loader2 className="h-5 w-5 animate-spin"/>Loading funded history…</div> : error ? <div className="rounded-xl border border-red-400/20 bg-red-400/10 p-5 text-red-100">{error}</div> : items.length === 0 ? <div className="rounded-xl border border-dashed border-white/15 p-10 text-center"><p className="font-semibold">No funded backtests yet.</p><p className="mt-2 text-sm text-muted-foreground">Run your first funded simulation to see challenge results and risk analytics here.</p><Button className="mt-4" asChild><Link href="/backtest?type=funded">Run Funded Backtest</Link></Button></div> : <div className="overflow-x-auto"><Table className="min-w-[1250px]"><TableHeader><TableRow><TableHead>Created</TableHead><TableHead>Account</TableHead><TableHead>Type</TableHead><TableHead>Strategy</TableHead><TableHead>Market</TableHead><TableHead>Range</TableHead><TableHead>Risk</TableHead><TableHead>Status</TableHead><TableHead>Final Balance</TableHead><TableHead>Return</TableHead><TableHead>Max DD</TableHead><TableHead>Days</TableHead><TableHead/></TableRow></TableHeader><TableBody>{items.map(item=><TableRow key={item.id}><TableCell>{dateText(item.created_at)}</TableCell><TableCell><p className="font-medium">{item.account_name || "Funded Account"}</p><p className="text-xs text-muted-foreground">{item.provider_name || "—"}</p></TableCell><TableCell>{item.challenge_type || "—"}</TableCell><TableCell className="max-w-[230px] truncate">{item.strategy_name || item.strategy_id || "—"}</TableCell><TableCell>{item.instrument_symbol || item.instrument_id || "—"} · {item.timeframe || "—"}</TableCell><TableCell>{dateText(item.start_date)} → {dateText(item.end_date)}</TableCell><TableCell>{item.risk_mode || "—"}</TableCell><TableCell><span className={`inline-flex rounded-full border px-2 py-1 text-xs font-semibold ${statusClass(item.status)}`}>{statusLabel(item.status)}</span></TableCell><TableCell>{money(item.final_balance, item.account_currency || "USD")}</TableCell><TableCell>{percent(item.return_pct)}</TableCell><TableCell>{percent(item.max_drawdown_pct)}</TableCell><TableCell>{item.calendar_days ?? "—"}</TableCell><TableCell><Button variant="outline" size="sm" asChild><Link href={`/funded-backtest-report/${item.id}`}><Eye className="mr-1 h-4 w-4"/>View</Link></Button></TableCell></TableRow>)}</TableBody></Table></div>}
      <div className="mt-4 flex items-center justify-between text-sm text-muted-foreground"><span>{total ? `${(page-1)*PAGE_SIZE+1}–${Math.min(page*PAGE_SIZE,total)} of ${total}` : "0 runs"}</span><div className="flex items-center gap-2"><Button variant="outline" size="sm" disabled={page<=1} onClick={()=>setPage(p=>p-1)}><ChevronLeft className="h-4 w-4"/></Button><span>Page {page} / {pages}</span><Button variant="outline" size="sm" disabled={page>=pages} onClick={()=>setPage(p=>p+1)}><ChevronRight className="h-4 w-4"/></Button></div></div>
    </CardContent></Card>
  </div>;
}
