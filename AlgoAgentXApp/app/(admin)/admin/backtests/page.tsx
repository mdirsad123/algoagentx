"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Eye, RefreshCcw, Search, Code2 } from "lucide-react";
import { toast } from "sonner";

import { adminApi, type AdminBacktest } from "@/lib/api/admin";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { PageHeader } from "@/components/ui/PageHeader";

const fieldClass =
  "w-full rounded-xl border border-border/60 bg-card/25 px-4 py-3 text-sm text-foreground outline-none transition-colors placeholder:text-muted-foreground focus:border-primary/50 focus:ring-2 focus:ring-primary/35";

const formatCurrency = (value: number | null | undefined) =>
  new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 2 }).format(Number(value || 0));

const formatPercent = (value: number | null | undefined) => `${Number(value || 0).toFixed(2)}%`;

export default function AdminBacktestsPage() {
  const [items, setItems] = useState<AdminBacktest[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [total, setTotal] = useState(0);
  const [filters, setFilters] = useState({ search: "", from_date: "", to_date: "", status: "" });

  const load = async () => {
    setLoading(true);
    try {
      const res = await adminApi.getBacktests({ page, page_size: pageSize, ...filters, status: filters.status || undefined });
      setItems(res.items || []);
      setTotal(res.total || 0);
    } catch (error: any) {
      toast.error(error?.message || "Failed to load backtests");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void load(); }, [page]);

  const totals = useMemo(() => {
    const totalPnl = items.reduce((sum, row) => sum + Number(row.net_profit || 0), 0);
    const avgReturn = items.length ? items.reduce((sum, row) => sum + Number(row.total_return || 0), 0) / items.length : 0;
    const avgDrawdown = items.length ? items.reduce((sum, row) => sum + Number(row.max_drawdown || 0), 0) / items.length : 0;
    return { totalPnl, avgReturn, avgDrawdown, profitable: items.filter((r) => Number(r.net_profit || 0) > 0).length };
  }, [items]);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Backtests Management"
        subtitle="Review all system backtests, monitor results, and jump into detailed reports."
        actions={<div className="flex gap-2"><Button variant="outline" className="rounded-xl" asChild><Link href="/admin/backtest-engine"><Code2 className="mr-2 h-4 w-4" />Engine Workspace</Link></Button><Button variant="outline" onClick={() => void load()} className="rounded-xl"><RefreshCcw className="mr-2 h-4 w-4" />Refresh</Button></div>}
      />

      <section className="grid grid-cols-1 gap-4 md:grid-cols-4">
        {[
          ["Total Runs", String(total)],
          ["Profitable Runs", String(totals.profitable)],
          ["Avg Return", formatPercent(totals.avgReturn)],
          ["Total PnL", formatCurrency(totals.totalPnl)],
        ].map(([label, value]) => (
          <Card key={label} className="rounded-xl border border-border/50 bg-card/30 shadow-xl backdrop-blur-xl">
            <CardHeader className="pb-2"><CardDescription>{label}</CardDescription><CardTitle className="text-2xl">{value}</CardTitle></CardHeader>
          </Card>
        ))}
      </section>

      <Card className="rounded-xl border border-border/50 bg-card/30 shadow-xl backdrop-blur-xl">
        <CardHeader><CardTitle>Filters</CardTitle></CardHeader>
        <CardContent className="grid grid-cols-1 gap-4 lg:grid-cols-4">
          <div className="relative lg:col-span-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <input className={`${fieldClass} pl-10`} value={filters.search} onChange={(e)=>setFilters((p)=>({...p,search:e.target.value}))} placeholder="Search by strategy, user, or ID" />
          </div>
          <input className={fieldClass} type="date" value={filters.from_date} onChange={(e)=>setFilters((p)=>({...p,from_date:e.target.value}))} />
          <input className={fieldClass} type="date" value={filters.to_date} onChange={(e)=>setFilters((p)=>({...p,to_date:e.target.value}))} />
          <div className="flex gap-2">
            <select className={fieldClass} value={filters.status} onChange={(e)=>setFilters((p)=>({...p,status:e.target.value}))}>
              <option value="">All statuses</option><option value="completed">Completed</option><option value="failed">Failed</option>
            </select>
            <Button className="rounded-xl bg-primary text-primary-foreground" onClick={() => { setPage(1); void load(); }}>Apply</Button>
          </div>
        </CardContent>
      </Card>

      <Card className="rounded-xl border border-border/50 bg-card/30 shadow-xl backdrop-blur-xl">
        <CardHeader><CardTitle>Backtest Results</CardTitle></CardHeader>
        <CardContent>
          {loading ? <div className="h-40 animate-pulse rounded-xl bg-card/20" /> : items.length === 0 ? (
            <div className="flex h-40 items-center justify-center text-muted-foreground">No backtests found</div>
          ) : (
            <div className="admin-table-scroll overflow-x-auto">
              <table className="admin-data-table min-w-full text-sm">
                <thead>
                  <tr className="border-b border-border/40 text-left text-muted-foreground">
                    {['Strategy','User','Instrument','TF','PnL','Return','Win Rate','Trades','Created','Actions'].map((h)=><th key={h} className="px-3 py-3 font-medium">{h}</th>)}
                  </tr>
                </thead>
                <tbody>
                  {items.map((row) => (
                    <tr key={row.id} className="border-b border-border/20">
                      <td className="px-3 py-3">{row.strategy_name || row.strategy_id || '—'}</td>
                      <td className="px-3 py-3">{row.user_email || row.user_name || '—'}</td>
                      <td className="px-3 py-3">{row.instrument_symbol || '—'}</td>
                      <td className="px-3 py-3">{row.timeframe || '—'}</td>
                      <td className="px-3 py-3">{formatCurrency(row.net_profit)}</td>
                      <td className="px-3 py-3">{formatPercent(row.total_return)}</td>
                      <td className="px-3 py-3">{formatPercent(row.win_rate)}</td>
                      <td className="px-3 py-3">{row.total_trades || 0}</td>
                      <td className="px-3 py-3">{row.created_at ? new Date(row.created_at).toLocaleString() : '—'}</td>
                      <td className="px-3 py-3">
                        <Button size="sm" variant="outline" className="rounded-xl" asChild>
                          <Link href={`/admin/backtest-report/${row.id}`}><Eye className="mr-2 h-4 w-4" />View</Link>
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
