"use client";

import { X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { RuntimeSettingsForm } from "./RuntimeSettingsForm";
import { RUNTIME_TABS } from "./runtimeSettingsDefaults";
import type { RuntimeConfig, RuntimeFieldSchema, RuntimeTab } from "./runtimeSettingsTypes";

type Props = {
  open: boolean;
  onClose: () => void;
  title?: string;
  subtitle?: string;
  badgeLabel?: string;
  activeTab: RuntimeTab;
  onTabChange: (tab: RuntimeTab) => void;
  config: RuntimeConfig;
  updateSection: (section: keyof RuntimeConfig, key: string, value: any) => void;
  strategySchema?: Record<string, RuntimeFieldSchema>;
  updateStrategyParam?: (key: string, value: any) => void;
  initialCapital?: string | number;
  onInitialCapitalChange?: (value: string) => void;
  currency?: string;
  quantityMode?: string;
  instrumentSymbol?: string;
  supportsIntradaySquareOff?: boolean;
  footerNote?: string;
  valid?: boolean;
  onReset?: () => void;
  onApply?: () => void;
};

export function RuntimeSettingsDrawer(props: Props) {
  if (!props.open) return null;
  return <div className="fixed inset-0 z-[120] flex items-stretch justify-end bg-black/55 backdrop-blur-sm">
    <button type="button" aria-label="Close strategy settings overlay" className="absolute inset-0 cursor-default" onClick={props.onClose} />
    <aside className="relative z-[121] flex h-full w-full max-w-3xl flex-col border-l border-border/60 bg-[#211042]/95 shadow-2xl backdrop-blur-xl">
      <div className="flex items-start justify-between gap-4 border-b border-border/50 px-5 py-4">
        <div><div className="flex flex-wrap items-center gap-2"><h2 className="text-xl font-semibold text-foreground">{props.title || "Strategy Runtime Settings"}</h2>{props.badgeLabel && <Badge className="border-primary/50 bg-primary/20 text-primary-foreground">{props.badgeLabel}</Badge>}</div><p className="mt-1 text-sm text-muted-foreground">{props.subtitle || "Configure risk, SL/TP, execution and dynamic strategy inputs."}</p></div>
        <Button type="button" variant="ghost" size="sm" className="rounded-xl" onClick={props.onClose}><X className="h-5 w-5" /></Button>
      </div>
      <div className="grid grid-cols-2 gap-3 border-b border-border/50 px-5 py-4 md:grid-cols-5">
        <div className="rounded-xl border border-border/50 bg-card/20 p-3 md:col-span-2"><p className="text-xs uppercase tracking-wide text-muted-foreground">Instrument</p><p className="mt-1 text-sm font-semibold text-foreground">{props.instrumentSymbol || "—"}</p></div>
        <div className="rounded-xl border border-border/50 bg-card/20 p-3"><p className="text-xs uppercase tracking-wide text-muted-foreground">Currency</p><p className="mt-1 text-sm font-semibold text-foreground">{props.currency || "—"}</p></div>
        <div className="rounded-xl border border-border/50 bg-card/20 p-3"><p className="text-xs uppercase tracking-wide text-muted-foreground">Qty Mode</p><p className="mt-1 text-sm font-semibold text-foreground">{props.quantityMode || "—"}</p></div>
        <div className="rounded-xl border border-border/50 bg-card/20 p-3"><p className="text-xs uppercase tracking-wide text-muted-foreground">RR / SL</p><p className="mt-1 text-sm font-semibold text-foreground">{props.config.sl_tp?.rr_ratio} · {props.config.sl_tp?.sl_mode}</p></div>
      </div>
      <div className="flex flex-wrap gap-2 border-b border-border/50 px-5 py-3">{RUNTIME_TABS.map((tab) => <button key={tab.value} type="button" onClick={() => props.onTabChange(tab.value)} className={`rounded-xl border px-3 py-2 text-xs font-medium transition ${props.activeTab === tab.value ? "border-primary/60 bg-primary/20 text-primary-foreground" : "border-border/60 bg-card/20 text-muted-foreground hover:bg-card/40 hover:text-foreground"}`}>{tab.label}</button>)}</div>
      <div className="flex-1 overflow-y-auto px-5 py-5"><RuntimeSettingsForm activeTab={props.activeTab} config={props.config} updateSection={props.updateSection} strategySchema={props.strategySchema} updateStrategyParam={props.updateStrategyParam} initialCapital={props.initialCapital} onInitialCapitalChange={props.onInitialCapitalChange} currency={props.currency} instrumentSymbol={props.instrumentSymbol} supportsIntradaySquareOff={props.supportsIntradaySquareOff} /></div>
      <div className="flex flex-col gap-3 border-t border-border/50 px-5 py-4 sm:flex-row sm:items-center sm:justify-between"><p className="text-xs text-muted-foreground">{props.footerNote || "Settings are sent with the next request only."}</p><div className="flex flex-wrap gap-2">{props.onReset && <Button type="button" variant="outline" onClick={props.onReset} className="rounded-xl border-border/60 bg-card/20 text-foreground hover:bg-card/40">Reset to Defaults</Button>}<Button type="button" disabled={props.valid === false} onClick={props.onApply || props.onClose} className="rounded-xl bg-primary text-primary-foreground hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-50">Apply Settings</Button></div></div>
    </aside>
  </div>;
}
