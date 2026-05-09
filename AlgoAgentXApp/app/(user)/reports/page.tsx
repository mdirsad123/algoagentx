"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { GlassCard } from "@/components/ui/GlassCard";
import { PageHeader } from "@/components/ui/PageHeader";
import { PageShell } from "@/components/ui/PageShell";
import { ResponsiveTableWrapper } from "@/components/ui/ResponsiveTableWrapper";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { AlertTriangle, CalendarDays, CheckCircle, Download, FileSpreadsheet, TrendingUp } from "lucide-react";

export default function ReportsPage() {
  const performanceMetrics = [
    { period: "Today", pnl: 1250.5, trades: 12, winRate: 75.0, maxDrawdown: -245.8 },
    { period: "This Week", pnl: 8750.25, trades: 89, winRate: 68.5, maxDrawdown: -1250.4 },
    { period: "This Month", pnl: 32150.75, trades: 345, winRate: 71.2, maxDrawdown: -2850.2 },
    { period: "This Year", pnl: 156750.9, trades: 1423, winRate: 69.8, maxDrawdown: -12850.5 },
  ];

  const systemLogs = [
    { timestamp: "2024-01-07 14:30:25", level: "INFO", message: "Strategy EMA_Crossover executed successfully", details: "Entry: LONG NIFTY @ 23785.50" },
    { timestamp: "2024-01-07 14:25:18", level: "WARNING", message: "High volatility detected in BANKNIFTY", details: "Volatility index: 24.5%" },
    { timestamp: "2024-01-07 14:20:45", level: "ERROR", message: "Failed to connect to broker API", details: "Zerodha API timeout - retrying in 30s" },
    { timestamp: "2024-01-07 14:15:12", level: "INFO", message: "Daily backup completed", details: "Database backup successful" },
    { timestamp: "2024-01-07 14:10:33", level: "INFO", message: "AI signal generated", details: "BUY signal for RELIANCE with 85% confidence" },
  ];

  const strategyRows = [
    ["EMA Crossover", "+24.5%", "Trending market", "Active"],
    ["Mean Reversion", "+18.2%", "Range market", "Active"],
    ["Momentum", "-5.8%", "Volatile", "Review"],
    ["Support Resistance", "+31.7%", "Breakout", "Active"],
  ];

  const getLogIcon = (level: string) => {
    if (level === "ERROR") return <AlertTriangle className="h-4 w-4 text-rose-300" />;
    if (level === "WARNING") return <AlertTriangle className="h-4 w-4 text-amber-300" />;
    return <CheckCircle className="h-4 w-4 text-emerald-300" />;
  };

  const getLogBadge = (level: string) => {
    if (level === "ERROR") return <Badge className="border-rose-300/30 bg-rose-500/15 text-rose-100">ERROR</Badge>;
    if (level === "WARNING") return <Badge className="border-amber-300/30 bg-amber-500/15 text-amber-100">WARNING</Badge>;
    return <Badge className="border-emerald-300/30 bg-emerald-500/15 text-emerald-100">INFO</Badge>;
  };

  return (
    <PageShell>
      <PageHeader
        title="Reports"
        subtitle="Performance summaries, system logs, exports, and strategy insights in one clean workspace."
        actions={
          <>
            <Button variant="outline" className="gap-2 border-white/10 bg-white/5 text-white hover:bg-white/10">
              <FileSpreadsheet className="h-4 w-4" /> Excel
            </Button>
            <Button className="gap-2 rounded-xl bg-primary text-primary-foreground hover:bg-primary/90">
              <Download className="h-4 w-4" /> PDF Report
            </Button>
          </>
        }
      />

      <Tabs defaultValue="performance" className="space-y-6">
        <TabsList className="flex h-auto flex-wrap justify-start gap-2 rounded-2xl border border-white/10 bg-white/5 p-2 backdrop-blur-xl">
          <TabsTrigger value="performance" className="rounded-xl data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">Performance</TabsTrigger>
          <TabsTrigger value="logs" className="rounded-xl data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">System Logs</TabsTrigger>
          <TabsTrigger value="analytics" className="rounded-xl data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">Analytics</TabsTrigger>
        </TabsList>

        <TabsContent value="performance" className="space-y-6">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {performanceMetrics.map((metric) => (
              <GlassCard key={metric.period} className="p-5" hoverEffect={false}>
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-sm text-purple-100/70">{metric.period}</p>
                    <p className="mt-2 text-3xl font-black text-lime-300">₹{metric.pnl.toLocaleString()}</p>
                  </div>
                  <div className="rounded-2xl border border-white/10 bg-white/10 p-3 text-purple-100">
                    <CalendarDays className="h-5 w-5" />
                  </div>
                </div>
                <div className="mt-5 grid grid-cols-3 gap-2 text-xs text-purple-100/70">
                  <div className="rounded-xl bg-white/5 p-2"><span className="block text-white">{metric.trades}</span>Trades</div>
                  <div className="rounded-xl bg-white/5 p-2"><span className="block text-white">{metric.winRate}%</span>Win Rate</div>
                  <div className="rounded-xl bg-white/5 p-2"><span className="block text-rose-200">₹{Math.abs(metric.maxDrawdown).toLocaleString()}</span>Max DD</div>
                </div>
              </GlassCard>
            ))}
          </div>

          <GlassCard className="p-6" hoverEffect={false}>
            <div className="mb-5 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h2 className="workspace-section-title">Performance Summary</h2>
                <p className="workspace-muted-text">Export-ready yearly trading overview.</p>
              </div>
              <TrendingUp className="h-5 w-5 text-lime-300" />
            </div>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
              <div className="rounded-2xl border border-white/10 bg-white/5 p-5 text-center">
                <div className="text-3xl font-black text-lime-300">₹156,751</div>
                <div className="mt-1 text-sm text-purple-100/70">Total P&amp;L (YTD)</div>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/5 p-5 text-center">
                <div className="text-3xl font-black text-sky-200">69.8%</div>
                <div className="mt-1 text-sm text-purple-100/70">Average Win Rate</div>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/5 p-5 text-center">
                <div className="text-3xl font-black text-rose-200">₹12,851</div>
                <div className="mt-1 text-sm text-purple-100/70">Max Drawdown</div>
              </div>
            </div>
          </GlassCard>
        </TabsContent>

        <TabsContent value="logs" className="space-y-6">
          <GlassCard className="p-6" hoverEffect={false}>
            <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h2 className="workspace-section-title">System Logs</h2>
                <p className="workspace-muted-text">Readable event trail for trading and account activity.</p>
              </div>
              <div className="workspace-actions">
                {['All Logs', 'Errors', 'Warnings', 'Info', 'Last 24h'].map((label) => (
                  <Button key={label} variant="outline" size="sm" className="border-white/10 bg-white/5 text-purple-100 hover:bg-white/10">{label}</Button>
                ))}
              </div>
            </div>
            <div className="space-y-3">
              {systemLogs.map((log, index) => (
                <div key={index} className="flex flex-col gap-3 rounded-2xl border border-white/10 bg-white/5 p-4 sm:flex-row sm:items-start">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-white/10">{getLogIcon(log.level)}</div>
                  <div className="min-w-0 flex-1 space-y-1">
                    <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                      <span className="text-sm font-semibold text-white">{log.message}</span>
                      {getLogBadge(log.level)}
                    </div>
                    <p className="text-sm text-purple-100/70">{log.details}</p>
                    <p className="text-xs text-purple-100/45">{log.timestamp}</p>
                  </div>
                </div>
              ))}
            </div>
          </GlassCard>
        </TabsContent>

        <TabsContent value="analytics" className="space-y-6">
          <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
            <GlassCard className="p-6" hoverEffect={false}>
              <h2 className="workspace-section-title">Strategy Performance</h2>
              <p className="workspace-muted-text mb-4">Strategy contribution and current review status.</p>
              <ResponsiveTableWrapper>
                <table className="min-w-[640px]">
                  <thead><tr><th>Strategy</th><th>Return</th><th>Market</th><th>Status</th></tr></thead>
                  <tbody>
                    {strategyRows.map(([name, ret, market, status]) => (
                      <tr key={name}><td>{name}</td><td className={ret.startsWith("+") ? "text-lime-300" : "text-rose-300"}>{ret}</td><td>{market}</td><td><Badge className="bg-white/10 text-purple-100">{status}</Badge></td></tr>
                    ))}
                  </tbody>
                </table>
              </ResponsiveTableWrapper>
            </GlassCard>

            <GlassCard className="p-6" hoverEffect={false}>
              <h2 className="workspace-section-title">Risk Metrics</h2>
              <p className="workspace-muted-text mb-4">Core risk numbers for the current reporting window.</p>
              <div className="grid gap-3 sm:grid-cols-2">
                {[["Sharpe Ratio", "1.45"], ["Sortino Ratio", "1.78"], ["Calmar Ratio", "2.12"], ["Max Drawdown", "-12.2%"]].map(([label, value]) => (
                  <div key={label} className="rounded-2xl border border-white/10 bg-white/5 p-4">
                    <div className="text-sm text-purple-100/70">{label}</div>
                    <div className={value.startsWith("-") ? "mt-2 text-2xl font-black text-rose-200" : "mt-2 text-2xl font-black text-white"}>{value}</div>
                  </div>
                ))}
              </div>
            </GlassCard>
          </div>

          <GlassCard className="p-6" hoverEffect={false}>
            <h2 className="workspace-section-title">AI Insights</h2>
            <p className="workspace-muted-text mb-4">Actionable highlights without changing any trading logic.</p>
            <div className="grid gap-4 md:grid-cols-3">
              <div className="rounded-2xl border border-sky-300/20 bg-sky-400/10 p-4">
                <h4 className="font-semibold text-sky-100">Market Sentiment</h4>
                <p className="mt-2 text-sm text-sky-100/75">Current market sentiment is bullish with 68% positive signals across major indices.</p>
              </div>
              <div className="rounded-2xl border border-amber-300/20 bg-amber-400/10 p-4">
                <h4 className="font-semibold text-amber-100">Risk Alert</h4>
                <p className="mt-2 text-sm text-amber-100/75">High volatility expected in BANKNIFTY due to upcoming earnings reports.</p>
              </div>
              <div className="rounded-2xl border border-emerald-300/20 bg-emerald-400/10 p-4">
                <h4 className="font-semibold text-emerald-100">Performance Insight</h4>
                <p className="mt-2 text-sm text-emerald-100/75">EMA Crossover strategy is showing consistent performance in trending markets.</p>
              </div>
            </div>
          </GlassCard>
        </TabsContent>
      </Tabs>
    </PageShell>
  );
}
