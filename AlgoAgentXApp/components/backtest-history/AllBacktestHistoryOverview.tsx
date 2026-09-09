"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Eye, Loader2, Play, RefreshCcw, ShieldCheck } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { backtestsApi, type BacktestHistoryItem } from "@/lib/api/backtests";
import { fundedReportingApi, type FundedHistoryItem } from "@/lib/api/funded-backtests";
import { parseApiError } from "@/lib/api/error";
import { formatDateTimeIST } from "@/lib/timezone";
import { dateText, statusClass, statusLabel } from "@/components/funded-backtest/report-utils";

const standardStatusClass = (status?: string | null) => {
  const normalized = String(status || "").toLowerCase();
  if (normalized === "completed") return "border-emerald-500/40 bg-emerald-500/10 text-emerald-200";
  if (normalized === "running") return "border-sky-500/40 bg-sky-500/10 text-sky-200";
  if (normalized === "pending") return "border-amber-500/40 bg-amber-500/10 text-amber-200";
  if (normalized === "failed") return "border-rose-500/40 bg-rose-500/10 text-rose-200";
  return "border-border/50 bg-card/40 text-muted-foreground";
};

const humanize = (value?: string | null) => String(value || "Unknown").replaceAll("_", " ").replace(/\b\w/g, (m) => m.toUpperCase());

export default function AllBacktestHistoryOverview() {
  const [standard, setStandard] = useState<BacktestHistoryItem[]>([]);
  const [funded, setFunded] = useState<FundedHistoryItem[]>([]);
  const [standardTotal, setStandardTotal] = useState(0);
  const [fundedTotal, setFundedTotal] = useState(0);
  const [fundedCounts, setFundedCounts] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const [standardResult, fundedResult] = await Promise.all([
        backtestsApi.getHistory({ page: 1, page_size: 5 }),
        fundedReportingApi.listRuns({ page: 1, page_size: 5 }),
      ]);
      setStandard(standardResult.backtests || []);
      setStandardTotal(standardResult.pagination?.total_count || 0);
      setFunded(fundedResult.items || []);
      setFundedTotal(fundedResult.total || 0);
      setFundedCounts(fundedResult.status_counts || {});
    } catch (err) {
      setError(parseApiError(err).message || "Unable to load combined backtest history.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const fundedPassed = fundedCounts.PASSED || 0;
  const totalRuns = standardTotal + fundedTotal;
  const recentCount = standard.length + funded.length;
  const latestCreated = useMemo(() => {
    const dates = [
      ...standard.map((item) => item.created_at),
      ...funded.map((item) => item.created_at),
    ].filter(Boolean) as string[];
    if (!dates.length) return "—";
    return formatDateTimeIST(dates.sort((a, b) => new Date(b).getTime() - new Date(a).getTime())[0]);
  }, [standard, funded]);

  if (loading) {
    return (
      <Card className="rounded-xl border border-border/50 bg-card/30 shadow-xl backdrop-blur-xl">
        <CardContent className="flex min-h-[260px] items-center justify-center gap-2 text-muted-foreground">
          <Loader2 className="h-5 w-5 animate-spin" /> Loading Standard and Funded history…
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="rounded-xl border border-rose-500/30 bg-rose-500/10">
        <CardContent className="flex flex-wrap items-center justify-between gap-3 p-5 text-rose-100">
          <span>{error}</span>
          <Button variant="outline" onClick={() => void load()}>
            <RefreshCcw className="mr-2 h-4 w-4" /> Retry
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-5">
        {[
          ["Total Runs", totalRuns, "Standard + Funded"],
          ["Standard Runs", standardTotal, "Normal backtests"],
          ["Funded Runs", fundedTotal, "Prop-rule simulations"],
          ["Funded Passed", fundedPassed, "Provider-rule pass states"],
          ["Recent Loaded", recentCount, latestCreated === "—" ? "No runs yet" : `Latest ${latestCreated}`],
        ].map(([label, value, note]) => (
          <Card key={String(label)} className="h-full rounded-xl border border-border/50 bg-card/30 shadow-xl backdrop-blur-xl">
            <CardHeader className="pb-2">
              <CardDescription>{label}</CardDescription>
              <CardTitle className="text-2xl text-foreground">{value}</CardTitle>
            </CardHeader>
            <CardContent className="pt-0 text-xs text-muted-foreground">{note}</CardContent>
          </Card>
        ))}
      </section>

      <div className="grid gap-6 2xl:grid-cols-2">
        <Card className="min-w-0 rounded-xl border border-border/50 bg-card/30 shadow-xl backdrop-blur-xl">
          <CardHeader>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <CardTitle className="flex items-center gap-2"><Play className="h-5 w-5" />Recent Standard Backtests</CardTitle>
                <CardDescription>Common overview only. Open Standard for full PnL, win-rate, drawdown and filter analytics.</CardDescription>
              </div>
              <Button variant="outline" size="sm" asChild><Link href="/backtest-history?type=standard">Open Standard</Link></Button>
            </div>
          </CardHeader>
          <CardContent>
            {standard.length === 0 ? (
              <div className="rounded-xl border border-dashed border-white/10 p-8 text-center text-sm text-muted-foreground">
                No Standard backtests yet.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <Table className="min-w-[650px]">
                  <TableHeader><TableRow><TableHead>Strategy</TableHead><TableHead>Market</TableHead><TableHead>Status</TableHead><TableHead>Created</TableHead><TableHead /></TableRow></TableHeader>
                  <TableBody>
                    {standard.map((item) => (
                      <TableRow key={item.id}>
                        <TableCell className="max-w-[220px] truncate font-medium">{item.strategy_name || "—"}</TableCell>
                        <TableCell>{item.instrument_symbol || "—"} · {item.timeframe || "—"}</TableCell>
                        <TableCell><span className={`inline-flex rounded-full border px-2 py-1 text-xs ${standardStatusClass(item.status)}`}>{humanize(item.status)}</span></TableCell>
                        <TableCell className="whitespace-nowrap text-xs text-muted-foreground">{formatDateTimeIST(item.created_at)}</TableCell>
                        <TableCell><Button variant="outline" size="sm" asChild><Link href={`/backtest-report/${item.id}`}><Eye className="mr-1 h-4 w-4" />View</Link></Button></TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="min-w-0 rounded-xl border border-border/50 bg-card/30 shadow-xl backdrop-blur-xl">
          <CardHeader>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <CardTitle className="flex items-center gap-2"><ShieldCheck className="h-5 w-5" />Recent Funded Backtests</CardTitle>
                <CardDescription>Common overview only. Open Funded for phase, drawdown, risk and payout analytics.</CardDescription>
              </div>
              <Button variant="outline" size="sm" asChild><Link href="/backtest-history?type=funded">Open Funded</Link></Button>
            </div>
          </CardHeader>
          <CardContent>
            {funded.length === 0 ? (
              <div className="rounded-xl border border-dashed border-white/10 p-8 text-center text-sm text-muted-foreground">
                No Funded backtests yet.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <Table className="min-w-[680px]">
                  <TableHeader><TableRow><TableHead>Strategy</TableHead><TableHead>Market</TableHead><TableHead>Status</TableHead><TableHead>Created</TableHead><TableHead /></TableRow></TableHeader>
                  <TableBody>
                    {funded.map((item) => (
                      <TableRow key={item.id}>
                        <TableCell className="max-w-[220px] truncate font-medium">{item.strategy_name || item.strategy_id || "—"}</TableCell>
                        <TableCell>{item.instrument_symbol || item.instrument_id || "—"} · {item.timeframe || "—"}</TableCell>
                        <TableCell><span className={`inline-flex rounded-full border px-2 py-1 text-xs font-semibold ${statusClass(item.status)}`}>{statusLabel(item.status)}</span></TableCell>
                        <TableCell className="whitespace-nowrap text-xs text-muted-foreground">{dateText(item.created_at)}</TableCell>
                        <TableCell><Button variant="outline" size="sm" asChild><Link href={`/funded-backtest-report/${item.id}`}><Eye className="mr-1 h-4 w-4" />View</Link></Button></TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
