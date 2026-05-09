"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  ArrowRight,
  BarChart3,
  Bot,
  Brain,
  Check,
  ChevronRight,
  CreditCard,
  Database,
  FileBarChart,
  Gauge,
  GitBranch,
  LineChart,
  Lock,
  MessageCircle,
  RadioTower,
  Rocket,
  Shield,
  Sparkles,
  WalletCards,
  Zap,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { landingApi, type LandingStats } from "@/lib/api/landing";
import type { SubscriptionPlan, SubscriptionPlansGrouped } from "@/lib/api/subscriptions";
import { cn } from "@/lib/utils";
import CouponAnnouncementBar from "@/components/common/CouponAnnouncementBar";

const EMPTY_STATS: LandingStats = {
  total_users: 0,
  total_backtests: 0,
  total_strategies: 0,
  connected_brokers: 0,
  live_deployments: 0,
};

const navItems = [
  { label: "Features", href: "#features" },
  { label: "Pricing", href: "#pricing" },
  { label: "Brokers", href: "#brokers" },
  { label: "Backtesting", href: "#backtesting" },
  { label: "Contact", href: "#contact" },
];

const trustBadges = ["Backtesting Engine", "Broker Integration", "Live Trading Control", "Strategy Deployment"];

const features = [
  { icon: Brain, title: "AI Strategy Builder", description: "Create, validate, and manage strategy logic with a SaaS-ready workflow for templates and custom requests." },
  { icon: BarChart3, title: "Backtest Engine", description: "Run historical tests with risk, reward, drawdown, trade history, and report-ready performance metrics." },
  { icon: WalletCards, title: "Broker Integration", description: "Connect broker accounts safely and keep each user account isolated for live or demo execution." },
  { icon: RadioTower, title: "Live Strategy Deployment", description: "Deploy strategies with approval gates, sync controls, execution logs, and broker-specific settings." },
  { icon: Shield, title: "Risk Management", description: "Configure capital risk, stop-loss, reward:risk, max trades, and live trading guardrails before execution." },
  { icon: FileBarChart, title: "Reports & Analytics", description: "Track backtests, trades, equity curves, strategy returns, and performance summaries in one platform." },
  { icon: Lock, title: "Admin SaaS Controls", description: "Manage users, strategies, pricing, subscriptions, credits, broker providers, and live approvals." },
  { icon: CreditCard, title: "Payment/Credits System", description: "Monetize backtests and premium access with credit top-ups, subscriptions, and billing history." },
];

const steps = [
  { title: "Create or choose strategy", description: "Start from an admin-approved template or request a custom strategy workflow." },
  { title: "Backtest historical data", description: "Validate entries, exits, risk rules, and performance before risking capital." },
  { title: "Connect broker", description: "Attach MT5 or Upstox credentials per user account with secure SaaS separation." },
  { title: "Deploy with control", description: "Use live approvals, pause/start controls, and sync toggles before broker execution." },
  { title: "Monitor performance", description: "Review logs, signals, orders, reports, P&L, and strategy health from dashboards." },
];

const brokers = [
  { name: "MT5", status: "Supported", description: "Demo/live account connection and execution foundation." },
  { name: "Upstox", status: "Supported", description: "OAuth-style account setup and live data integration foundation." },
  { name: "TradingView Webhook", status: "Supported", description: "Alert payloads can trigger platform-side live signal flows." },
  { name: "Paper Trading", status: "Supported", description: "Test deployments before turning on broker execution." },
  { name: "More Brokers", status: "Coming soon", description: "Extend provider controls as the SaaS broker layer grows." },
];

const faqs = [
  { q: "Can I backtest before live trading?", a: "Yes. The platform is designed to test strategy logic with historical data before deployment." },
  { q: "Does AlgoAgentX place live orders automatically?", a: "Live execution should be enabled only after broker connection, deployment setup, approvals, and risk controls are configured." },
  { q: "Can each user connect their own broker account?", a: "Yes. The SaaS flow supports user-specific broker accounts so one user does not share another user’s credentials." },
  { q: "How do credits and subscriptions work?", a: "Backtests and premium actions can be controlled by subscription credits and top-up credits based on your billing configuration." },
  { q: "Can admins manage strategies?", a: "Admins can manage strategy templates, review requests, validate code, run sandbox checks, and publish stable strategies." },
  { q: "Is risk control included?", a: "Yes. Risk settings such as capital, position sizing, stop-loss, max trades, and live approval gates can be configured." },
];

function formatStat(value: number | undefined, loading: boolean) {
  if (loading) return "--";
  const safe = Number.isFinite(Number(value)) ? Number(value) : 0;
  return new Intl.NumberFormat("en-IN").format(safe);
}

function priceText(plan: SubscriptionPlan) {
  const price = Number(plan.price_inr || 0);
  if (price <= 0) return "Free";
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(price);
}

function periodText(plan: SubscriptionPlan) {
  const period = String(plan.billing_period || "").toUpperCase();
  if (period === "YEARLY") return "/year";
  if (period === "MONTHLY") return "/month";
  return "";
}

function sectionLabel(text: string) {
  return <Badge className="border-purple-300/20 bg-purple-400/10 text-purple-100 hover:bg-purple-400/10">{text}</Badge>;
}

export default function LandingPage() {
  const [stats, setStats] = useState<LandingStats>(EMPTY_STATS);
  const [statsLoading, setStatsLoading] = useState(true);
  const [plans, setPlans] = useState<SubscriptionPlansGrouped | null>(null);
  const [plansLoading, setPlansLoading] = useState(true);
  const [plansError, setPlansError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    landingApi
      .getStats()
      .then((data) => {
        if (!cancelled) setStats({ ...EMPTY_STATS, ...(data || {}) });
      })
      .catch(() => {
        if (!cancelled) setStats(EMPTY_STATS);
      })
      .finally(() => {
        if (!cancelled) setStatsLoading(false);
      });

    landingApi
      .getPlans()
      .then((data) => {
        if (!cancelled) {
          setPlans(data || { free: [], monthly: [], yearly: [] });
          setPlansError(null);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setPlans({ free: [], monthly: [], yearly: [] });
          setPlansError("Pricing plans are not available right now.");
        }
      })
      .finally(() => {
        if (!cancelled) setPlansLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const displayedPlans = useMemo(() => {
    const all = [...(plans?.free || []), ...(plans?.monthly || [])];
    return all.slice(0, 4);
  }, [plans]);

  const statCards = [
    { label: "Total Users", value: stats.total_users, icon: Bot },
    { label: "Total Backtests", value: stats.total_backtests, icon: Database },
    { label: "Total Strategies", value: stats.total_strategies, icon: GitBranch },
    { label: "Connected Brokers", value: stats.connected_brokers, icon: Activity },
    { label: "Live Deployments", value: stats.live_deployments, icon: RadioTower },
  ];

  return (
    <main className="min-h-screen overflow-hidden bg-[radial-gradient(circle_at_15%_10%,rgba(168,85,247,0.34),transparent_32%),radial-gradient(circle_at_85%_18%,rgba(16,185,129,0.22),transparent_30%),radial-gradient(circle_at_50%_95%,rgba(236,72,153,0.22),transparent_35%),linear-gradient(135deg,#17112b_0%,#161b2f_42%,#10251f_100%)] text-white">
      <div className="pointer-events-none fixed inset-0 -z-10">
        <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.055)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.055)_1px,transparent_1px)] bg-[size:72px_72px] opacity-45 [mask-image:radial-gradient(circle_at_top,black,transparent_78%)]" />
        <div className="absolute left-[8%] top-[8%] h-[360px] w-[360px] rounded-full bg-purple-400/25 blur-3xl" />
        <div className="absolute right-[8%] top-[14%] h-[360px] w-[360px] rounded-full bg-emerald-400/20 blur-3xl" />
        <div className="absolute bottom-[8%] left-[35%] h-[420px] w-[420px] rounded-full bg-fuchsia-400/18 blur-3xl" />
        <div className="absolute inset-0 bg-white/[0.025]" />
      </div>

      <header className="fixed inset-x-0 top-0 z-50 border-b border-white/15 bg-[#17112b]/55 shadow-lg shadow-purple-950/10 backdrop-blur-2xl">
        <CouponAnnouncementBar />
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
          <Link href="/" className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-gradient-to-br from-purple-500 via-fuchsia-500 to-pink-500 shadow-lg shadow-purple-500/30">
              <Rocket className="h-5 w-5" />
            </div>
            <div>
              <p className="text-lg font-bold leading-none">AlgoAgentX</p>
              <p className="text-[11px] text-purple-100/70">AI Trading SaaS</p>
            </div>
          </Link>

          <nav className="hidden items-center gap-7 text-sm text-slate-200/80 lg:flex">
            {navItems.map((item) => (
              <a key={item.href} href={item.href} className="transition hover:text-white">
                {item.label}
              </a>
            ))}
          </nav>

          <div className="flex items-center gap-2">
            <Button asChild variant="ghost" className="text-white hover:bg-white/10 hover:text-white">
              <Link href="/login">Sign In</Link>
            </Button>
            <Button asChild className="bg-gradient-to-r from-purple-500 to-fuchsia-500 text-white hover:opacity-95">
              <Link href="/register">Get Started</Link>
            </Button>
          </div>
        </div>
      </header>

      <section className="relative mx-auto grid max-w-7xl gap-12 px-4 pb-16 pt-32 sm:px-6 lg:grid-cols-[1.08fr_0.92fr] lg:px-8 lg:pb-24 lg:pt-40">
        <div className="flex flex-col justify-center">
          {sectionLabel("Production-grade algo trading platform")}
          <h1 className="mt-6 text-4xl font-black tracking-tight sm:text-6xl lg:text-7xl">
            Backtest, deploy, and control your <span className="bg-gradient-to-r from-purple-300 via-fuchsia-300 to-pink-300 bg-clip-text text-transparent">AI trading systems</span>.
          </h1>
          <p className="mt-6 max-w-2xl text-lg leading-8 text-slate-300">
            AlgoAgentX helps traders backtest strategies, connect brokers, deploy live strategies, monitor signals, and manage risk from one SaaS workspace.
          </p>
          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <Button asChild size="lg" className="h-12 rounded-full bg-gradient-to-r from-purple-500 via-fuchsia-500 to-pink-500 px-7 text-white shadow-2xl shadow-purple-500/25 hover:opacity-95">
              <Link href="/register">Start Free <ArrowRight className="ml-2 h-4 w-4" /></Link>
            </Button>
            <Button asChild size="lg" variant="outline" className="h-12 rounded-full border-white/20 bg-white/5 px-7 text-white hover:bg-white/10 hover:text-white">
              <Link href="/login">Sign In</Link>
            </Button>
            <Button asChild size="lg" variant="ghost" className="h-12 rounded-full px-7 text-purple-100 hover:bg-white/10 hover:text-white">
              <a href="#pricing">View Pricing</a>
            </Button>
          </div>
          <div className="mt-8 flex flex-wrap gap-2">
            {trustBadges.map((badge) => (
              <span key={badge} className="rounded-full border border-white/10 bg-white/[0.06] px-4 py-2 text-sm text-slate-200 backdrop-blur">
                <Check className="mr-2 inline h-4 w-4 text-emerald-300" />{badge}
              </span>
            ))}
          </div>
        </div>

        <div className="relative min-h-[500px]">
          <Card className="absolute right-0 top-4 w-full max-w-[520px] border-white/10 bg-white/[0.07] shadow-2xl shadow-purple-950/40 backdrop-blur-2xl">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-white">Live Control Center</CardTitle>
                  <p className="mt-2 text-sm text-slate-300">Strategy sync, broker status, and risk controls.</p>
                </div>
                <Badge className="bg-emerald-400/15 text-emerald-200 hover:bg-emerald-400/15">System Ready</Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {["EMA 9/20 Scalper", "RSI Reversal", "Breakout Swing"].map((name, index) => (
                <div key={name} className="rounded-2xl border border-white/10 bg-white/[0.08] p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-semibold text-white">{name}</p>
                      <p className="text-sm text-slate-400">Risk {index + 1}% • RR 1:{index + 2}</p>
                    </div>
                    <Badge className={cn(index === 0 ? "bg-emerald-400/15 text-emerald-200" : "bg-purple-400/15 text-purple-100", "hover:bg-white/10")}>{index === 0 ? "Running" : "Ready"}</Badge>
                  </div>
                  <div className="mt-4 h-2 rounded-full bg-white/10">
                    <div className="h-2 rounded-full bg-gradient-to-r from-purple-400 to-fuchsia-400" style={{ width: `${68 + index * 8}%` }} />
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
          <div className="absolute bottom-8 left-0 w-[280px] rounded-3xl border border-white/10 bg-white/[0.08] p-5 shadow-2xl shadow-fuchsia-950/40 backdrop-blur-2xl">
            <div className="mb-4 flex items-center gap-3">
              <div className="rounded-2xl bg-purple-400/15 p-3"><LineChart className="h-5 w-5 text-purple-200" /></div>
              <div>
                <p className="font-semibold">Backtest Snapshot</p>
                <p className="text-sm text-slate-400">Equity curve + trade report</p>
              </div>
            </div>
            <div className="flex h-24 items-end gap-2">
              {[32, 50, 42, 70, 61, 88, 78, 96].map((h, i) => <div key={i} className="flex-1 rounded-t-lg bg-gradient-to-t from-purple-500/50 to-fuchsia-300/90" style={{ height: `${h}%` }} />)}
            </div>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
          {statCards.map((stat) => {
            const Icon = stat.icon;
            return (
              <Card key={stat.label} className="border-white/10 bg-white/[0.06] backdrop-blur-xl">
                <CardContent className="p-5">
                  <Icon className="mb-4 h-5 w-5 text-purple-200" />
                  <p className="text-3xl font-black text-white">{formatStat(stat.value, statsLoading)}</p>
                  <p className="mt-1 text-sm text-slate-400">{stat.label}</p>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </section>

      <section id="features" className="mx-auto max-w-7xl px-4 py-20 sm:px-6 lg:px-8">
        <div className="max-w-3xl">{sectionLabel("Features")}<h2 className="mt-4 text-3xl font-bold sm:text-5xl">Everything required for a serious trading SaaS.</h2></div>
        <div className="mt-12 grid gap-5 md:grid-cols-2 lg:grid-cols-4">
          {features.map((feature) => {
            const Icon = feature.icon;
            return (
              <Card key={feature.title} className="group border-white/10 bg-white/[0.055] transition hover:-translate-y-1 hover:bg-white/[0.08] hover:shadow-2xl hover:shadow-purple-950/30">
                <CardContent className="p-6">
                  <div className="mb-5 inline-flex rounded-2xl bg-purple-400/15 p-3 text-purple-100"><Icon className="h-6 w-6" /></div>
                  <h3 className="text-lg font-bold text-white">{feature.title}</h3>
                  <p className="mt-3 text-sm leading-6 text-slate-400">{feature.description}</p>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </section>

      <section id="backtesting" className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
        <div className="rounded-[2rem] border border-white/10 bg-gradient-to-br from-white/[0.09] to-white/[0.035] p-6 backdrop-blur-2xl lg:p-10">
          <div className="grid gap-10 lg:grid-cols-[0.9fr_1.1fr]">
            <div>{sectionLabel("How it works")}<h2 className="mt-4 text-3xl font-bold sm:text-5xl">Move from idea to controlled deployment.</h2><p className="mt-5 text-slate-300">Keep research, broker connection, live approvals, and reporting inside one production workflow.</p></div>
            <div className="space-y-4">
              {steps.map((step, index) => (
                <div key={step.title} className="flex gap-4 rounded-2xl border border-white/10 bg-white/[0.08] p-4">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-purple-500 to-fuchsia-500 font-bold">{index + 1}</div>
                  <div><p className="font-semibold text-white">{step.title}</p><p className="mt-1 text-sm text-slate-400">{step.description}</p></div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section id="brokers" className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
        <div className="text-center">{sectionLabel("Brokers & integrations")}<h2 className="mt-4 text-3xl font-bold sm:text-5xl">Connect what is supported. Label what is coming.</h2></div>
        <div className="mt-10 grid gap-4 md:grid-cols-2 lg:grid-cols-5">
          {brokers.map((broker) => (
            <Card key={broker.name} className="border-white/10 bg-white/[0.055]">
              <CardContent className="p-5">
                <Badge className={broker.status === "Supported" ? "bg-emerald-400/15 text-emerald-200 hover:bg-emerald-400/15" : "bg-amber-400/15 text-amber-200 hover:bg-amber-400/15"}>{broker.status}</Badge>
                <h3 className="mt-4 text-lg font-bold">{broker.name}</h3>
                <p className="mt-2 text-sm leading-6 text-slate-400">{broker.description}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>

      <section id="pricing" className="mx-auto max-w-7xl px-4 py-20 sm:px-6 lg:px-8">
        <div className="flex flex-col justify-between gap-4 md:flex-row md:items-end">
          <div>{sectionLabel("Pricing preview")}<h2 className="mt-4 text-3xl font-bold sm:text-5xl">Start free. Scale with credits and subscriptions.</h2></div>
          <Button asChild variant="outline" className="border-white/15 bg-white/5 text-white hover:bg-white/10 hover:text-white"><Link href="/pricing">Open Pricing <ChevronRight className="ml-2 h-4 w-4" /></Link></Button>
        </div>
        <div className="mt-10 grid gap-5 md:grid-cols-2 lg:grid-cols-4">
          {plansLoading ? [0, 1, 2, 3].map((i) => <Card key={i} className="h-64 animate-pulse border-white/10 bg-white/[0.05]"><span className="sr-only">Loading plan</span></Card>) : displayedPlans.length > 0 ? displayedPlans.map((plan) => (
            <Card key={plan.plan_key || plan.id} className="border-white/10 bg-white/[0.065]">
              <CardContent className="p-6">
                <Badge className="bg-purple-400/15 text-purple-100 hover:bg-purple-400/15">{plan.code}</Badge>
                <div className="mt-5 flex items-end gap-1"><span className="text-3xl font-black">{priceText(plan)}</span><span className="pb-1 text-sm text-slate-400">{periodText(plan)}</span></div>
                <p className="mt-3 text-sm text-slate-400">{Number(plan.included_credits || 0).toLocaleString("en-IN")} included credits</p>
                <Button asChild className="mt-6 w-full bg-gradient-to-r from-purple-500 to-fuchsia-500 text-white hover:opacity-95"><Link href="/register">Choose Plan</Link></Button>
              </CardContent>
            </Card>
          )) : (
            <Card className="border-white/10 bg-white/[0.055] md:col-span-2 lg:col-span-4"><CardContent className="p-8 text-center"><p className="text-slate-300">{plansError || "No active pricing plans found."}</p><Button asChild className="mt-5 bg-gradient-to-r from-purple-500 to-fuchsia-500 text-white"><Link href="/pricing">Go to Pricing Page</Link></Button></CardContent></Card>
          )}
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
        <Card className="border-amber-300/20 bg-amber-300/10"><CardContent className="flex gap-4 p-6 text-amber-50"><Shield className="h-6 w-6 shrink-0" /><p className="text-sm leading-6">AlgoAgentX is a trading technology platform. Trading involves risk. Users are responsible for their own trading decisions, broker connections, strategy settings, and live execution controls.</p></CardContent></Card>
      </section>

      <section id="contact" className="mx-auto max-w-7xl px-4 py-20 sm:px-6 lg:px-8">
        <div className="grid gap-10 lg:grid-cols-[0.8fr_1.2fr]">
          <div>{sectionLabel("FAQ & support")}<h2 className="mt-4 text-3xl font-bold sm:text-5xl">Common questions before going live.</h2><p className="mt-5 text-slate-300">Need help? Sign in and use support tickets from your dashboard.</p><Button asChild className="mt-6 bg-gradient-to-r from-purple-500 to-fuchsia-500 text-white"><Link href="/support-tickets"><MessageCircle className="mr-2 h-4 w-4" /> Support</Link></Button></div>
          <div className="grid gap-4 md:grid-cols-2">
            {faqs.map((faq) => <Card key={faq.q} className="border-white/10 bg-white/[0.055]"><CardContent className="p-5"><h3 className="font-bold text-white">{faq.q}</h3><p className="mt-2 text-sm leading-6 text-slate-400">{faq.a}</p></CardContent></Card>)}
          </div>
        </div>
      </section>

      <footer className="border-t border-white/10 bg-white/[0.08]">
        <div className="mx-auto grid max-w-7xl gap-8 px-4 py-10 sm:px-6 md:grid-cols-4 lg:px-8">
          <div><div className="flex items-center gap-3"><Rocket className="h-6 w-6 text-purple-200" /><span className="font-bold">AlgoAgentX</span></div><p className="mt-4 text-sm text-slate-400">Professional AI algo trading, backtesting, broker deployment, and SaaS controls.</p></div>
          <div><p className="font-semibold">Product</p><div className="mt-3 space-y-2 text-sm text-slate-400"><a className="block hover:text-white" href="#features">Features</a><a className="block hover:text-white" href="#pricing">Pricing</a><a className="block hover:text-white" href="#brokers">Brokers</a></div></div>
          <div><p className="font-semibold">Company</p><div className="mt-3 space-y-2 text-sm text-slate-400"><a className="block hover:text-white" href="#contact">Support</a><Link className="block hover:text-white" href="/login">Sign In</Link><Link className="block hover:text-white" href="/register">Register</Link></div></div>
          <div><p className="font-semibold">Legal</p><div className="mt-3 space-y-2 text-sm text-slate-400"><span className="block">Terms placeholder</span><span className="block">Privacy placeholder</span><span className="block">Risk disclosure placeholder</span></div></div>
        </div>
        <div className="border-t border-white/10 py-5 text-center text-sm text-slate-500">© {new Date().getFullYear()} AlgoAgentX. All rights reserved.</div>
      </footer>
    </main>
  );
}
