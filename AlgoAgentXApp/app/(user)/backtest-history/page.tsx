"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Layers3, Play, ShieldCheck } from "lucide-react";

import AllBacktestHistoryOverview from "@/components/backtest-history/AllBacktestHistoryOverview";
import FundedBacktestHistoryWorkspace from "@/components/backtest-history/FundedBacktestHistoryWorkspace";
import StandardBacktestHistoryWorkspace from "@/components/backtest-history/StandardBacktestHistoryWorkspace";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/ui/PageHeader";

type HistoryType = "all" | "standard" | "funded";

const tabs: Array<{ value: HistoryType; label: string }> = [
  { value: "all", label: "All" },
  { value: "standard", label: "Standard" },
  { value: "funded", label: "Funded" },
];

export default function BacktestHistoryPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const requested = searchParams.get("type");
  const selectedType: HistoryType = requested === "standard" || requested === "funded" ? requested : "all";

  const newRunTarget = selectedType === "funded" ? "/backtest?type=funded" : "/backtest?type=standard";
  const actionLabel = selectedType === "funded" ? "Run Funded Backtest" : "New Backtest";

  return (
    <div className="space-y-6">
      <PageHeader
        title="Backtest History"
        subtitle="One archive for Standard and Funded simulations, with specialized analytics preserved inside each history type."
        actions={
          <Button
            onClick={() => router.push(newRunTarget)}
            className="rounded-xl bg-primary text-primary-foreground hover:bg-primary/90"
          >
            {selectedType === "funded" ? <ShieldCheck className="mr-2 h-4 w-4" /> : <Play className="mr-2 h-4 w-4" />}
            {actionLabel}
          </Button>
        }
      />

      <section className="rounded-2xl border border-white/10 bg-white/[0.035] p-2 shadow-xl backdrop-blur-xl">
        <div className="flex flex-wrap gap-2" role="tablist" aria-label="Backtest history type">
          {tabs.map((tab) => {
            const active = selectedType === tab.value;
            return (
              <button
                key={tab.value}
                type="button"
                role="tab"
                aria-selected={active}
                onClick={() => router.push(`/backtest-history?type=${tab.value}`)}
                className={[
                  "inline-flex min-w-[110px] items-center justify-center gap-2 rounded-xl border px-4 py-2.5 text-sm font-semibold transition",
                  active
                    ? "border-lime-300/50 bg-lime-300/10 text-lime-100 shadow-sm"
                    : "border-transparent bg-transparent text-muted-foreground hover:border-white/10 hover:bg-white/5 hover:text-foreground",
                ].join(" ")}
              >
                {tab.value === "all" && <Layers3 className="h-4 w-4" />}
                {tab.value === "funded" && <ShieldCheck className="h-4 w-4" />}
                {tab.value === "standard" && <Play className="h-4 w-4" />}
                {tab.label}
              </button>
            );
          })}
        </div>
      </section>

      {selectedType === "standard" ? (
        <StandardBacktestHistoryWorkspace />
      ) : selectedType === "funded" ? (
        <FundedBacktestHistoryWorkspace />
      ) : (
        <AllBacktestHistoryOverview />
      )}
    </div>
  );
}
