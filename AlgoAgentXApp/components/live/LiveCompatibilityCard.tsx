"use client";

import { ShieldCheck } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { GlassCard } from "@/components/ui/GlassCard";
import type { LiveCompatibilityResult } from "@/types/live-trading";

function badgeClass(status?: string) {
  const value = String(status || "FAIL").toUpperCase();
  if (value === "PASS") return "border-lime-400/30 bg-lime-400/20 text-lime-100";
  if (value === "WARNING") return "border-yellow-400/30 bg-yellow-400/20 text-yellow-100";
  return "border-red-400/30 bg-red-400/20 text-red-100";
}

function titleFor(status?: string) {
  const value = String(status || "FAIL").toUpperCase();
  if (value === "PASS") return "Live compatible";
  if (value === "WARNING") return "Compatible with warnings";
  return "Compatibility failed";
}

export function LiveCompatibilityCard({
  result,
  loading,
  onRun,
  compact = false,
  title = "Live Compatibility",
}: {
  result?: LiveCompatibilityResult | null;
  loading?: boolean;
  onRun?: () => void;
  compact?: boolean;
  title?: string;
}) {
  const checks = result?.checks || [];
  const failing = checks.filter((item) => String(item.status).toUpperCase() === "FAIL").length;
  const warnings = checks.filter((item) => String(item.status).toUpperCase() === "WARNING").length;
  return (
    <GlassCard className={`${compact ? "p-4" : "mb-6 p-6"}`} hoverEffect={false}>
      <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-start">
        <div>
          <div className="flex items-center gap-2">
            <ShieldCheck className="h-5 w-5 text-lime-300" />
            <h2 className={`${compact ? "text-lg" : "text-2xl"} font-bold text-white`}>{title}</h2>
          </div>
          <p className="mt-1 text-sm text-purple-200">Validates strategy output, STRATEGY_SUGGESTED SL, instrument spec, runtime config, and broker capital before auto trading.</p>
          {result?.summary && <p className="mt-2 text-sm text-purple-100">{result.summary}</p>}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Badge className={badgeClass(result?.status)}>{titleFor(result?.status)}</Badge>
          <Badge className="border-white/10 bg-white/10 text-purple-100">{failing} fail</Badge>
          <Badge className="border-white/10 bg-white/10 text-purple-100">{warnings} warning</Badge>
          {onRun && <Button disabled={loading} onClick={onRun} variant="outline" className="border-white/10 bg-white/5 text-white hover:bg-white/10">{loading ? "Checking..." : "Run Check"}</Button>}
        </div>
      </div>
      {checks.length > 0 ? (
        <div className="mt-5 grid grid-cols-1 gap-3 lg:grid-cols-2">
          {checks.map((check, index) => (
            <div key={`${check.name}-${index}`} className="rounded-xl border border-white/10 bg-white/5 p-4">
              <div className="flex flex-wrap items-center gap-2">
                <p className="font-semibold text-white">{check.name}</p>
                <Badge className={badgeClass(check.status)}>{check.status}</Badge>
              </div>
              <p className="mt-1 text-sm text-purple-200">{check.message}</p>
            </div>
          ))}
        </div>
      ) : (
        <div className="mt-5 rounded-xl border border-white/10 bg-white/5 p-4 text-sm text-purple-200">Run compatibility check to validate this deployment before enabling Auto Trade.</div>
      )}
    </GlassCard>
  );
}
