"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { CheckCircle2, PlayCircle, ShieldCheck } from "lucide-react";

import StandardBacktestWorkspace from "@/components/backtest-workspace/StandardBacktestWorkspace";
import FundedBacktestWorkspace from "@/components/backtest-workspace/FundedBacktestWorkspace";

const options = [
  {
    value: "standard" as const,
    title: "Standard Backtest",
    description: "Run the existing strategy backtest with normal capital, runtime settings, filters, credits and reports.",
    icon: PlayCircle,
  },
  {
    value: "funded" as const,
    title: "Funded / Prop Backtest",
    description: "Test the same strategy against funded profiles, phases, drawdown rules, risk ladders and payout requirements.",
    icon: ShieldCheck,
  },
];

export default function BacktestPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const selectedType = searchParams.get("type") === "funded" ? "funded" : "standard";

  const selectType = (next: "standard" | "funded") => {
    if (next === selectedType) return;
    // Intentionally start each workspace with its own isolated form state.
    // This prevents Standard-only query state from leaking into Funded and vice versa.
    router.push(`/backtest?type=${next}`);
  };

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-white/10 bg-white/[0.035] p-4 shadow-xl backdrop-blur-xl sm:p-5">
        <div className="mb-4">
          <p className="text-sm font-semibold text-foreground">Backtest Type</p>
          <p className="mt-1 text-xs text-muted-foreground">
            Standard and Funded share one workspace, while each keeps its existing specialized execution engine and state.
          </p>
        </div>
        <div className="grid gap-3 lg:grid-cols-2">
          {options.map((option) => {
            const selected = selectedType === option.value;
            const Icon = option.icon;
            return (
              <button
                key={option.value}
                type="button"
                aria-pressed={selected}
                onClick={() => selectType(option.value)}
                className={[
                  "group relative flex min-h-[96px] w-full items-start gap-3 rounded-2xl border p-4 text-left transition-all",
                  selected
                    ? "border-lime-300/70 bg-white/10 shadow-lg shadow-purple-950/20 ring-1 ring-lime-300/20"
                    : "border-white/10 bg-black/5 hover:border-white/20 hover:bg-white/[0.055]",
                ].join(" ")}
              >
                <span className={[
                  "mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border",
                  selected ? "border-lime-300/40 bg-lime-300/10 text-lime-200" : "border-white/10 bg-white/5 text-purple-100",
                ].join(" ")}>
                  <Icon className="h-5 w-5" />
                </span>
                <span className="min-w-0 flex-1">
                  <span className="flex flex-wrap items-center gap-2">
                    <span className="font-semibold text-foreground">{option.title}</span>
                    {selected && (
                      <span className="inline-flex items-center gap-1 rounded-full border border-lime-300/30 bg-lime-300/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-lime-200">
                        <CheckCircle2 className="h-3 w-3" /> Selected
                      </span>
                    )}
                  </span>
                  <span className="mt-1.5 block text-xs leading-relaxed text-muted-foreground">{option.description}</span>
                </span>
              </button>
            );
          })}
        </div>
      </section>

      {selectedType === "funded" ? <FundedBacktestWorkspace /> : <StandardBacktestWorkspace />}
    </div>
  );
}
