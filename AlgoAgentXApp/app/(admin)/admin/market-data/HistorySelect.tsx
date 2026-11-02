"use client";

import * as React from "react";
import * as Primitive from "@radix-ui/react-select";
import { Check, ChevronDown, X } from "lucide-react";
import { cn } from "@/lib/utils";

/** Admin market-data picker. Radix portal avoids the browser's OS-black native menus. */
export type HistoryOption = { value: string; label: string; disabled?: boolean };
export function HistorySelect({ value, onChange, options, placeholder = "Choose an option", disabled, className, clearable = false }:
  { value: string; onChange: (value: string) => void; options: HistoryOption[]; placeholder?: string; disabled?: boolean; className?: string; clearable?: boolean }) {
  const selected = options.find((option) => option.value === value);
  const available = options.filter((option) => option.value !== "");
  const hasStaleValue = !!value && !selected;
  return <div className="flex min-w-0 items-start gap-1"><Primitive.Root value={value} onValueChange={onChange} disabled={disabled}>
    <Primitive.Trigger aria-label={selected?.label || placeholder} className={cn(
      "flex h-10 min-h-10 min-w-0 flex-1 items-center justify-between gap-2 self-start rounded-xl border border-violet-400/25 bg-[#321c60]/90 px-3 py-2 text-left text-sm text-violet-50 shadow-sm outline-none transition-colors hover:border-violet-300/45 focus:ring-2 focus:ring-fuchsia-400/45 disabled:opacity-50",
      className,
    )}>
      {/* Keep the visible label OUTSIDE Radix Value: controlled Value can render blank
          when the associated item is reloaded/unmounted during account updates. */}
      <span aria-hidden="true" className={cn("block min-w-0 flex-1 truncate", !value && "text-violet-200/75", hasStaleValue && "text-amber-200")}>
        {selected?.label ?? (hasStaleValue ? "Selection unavailable — choose again" : placeholder)}
      </span>
      <Primitive.Icon><ChevronDown className="h-4 w-4 shrink-0 text-violet-200" /></Primitive.Icon>
    </Primitive.Trigger>
    <Primitive.Portal>
      <Primitive.Content position="popper" sideOffset={5} className="z-[200] max-h-[min(20rem,var(--radix-select-content-available-height))] min-w-[var(--radix-select-trigger-width)] overflow-hidden rounded-xl border border-violet-400/45 bg-[#251446] text-violet-50 shadow-2xl shadow-black/45">
        <Primitive.Viewport className="max-h-[19rem] overflow-y-auto p-1.5">
          {available.map(option =>
            <Primitive.Item key={option.value} value={option.value} disabled={option.disabled}
              className="relative flex cursor-pointer select-none items-center rounded-lg py-2.5 pl-3 pr-8 text-sm text-violet-50 outline-none data-[highlighted]:bg-fuchsia-600/45 data-[state=checked]:bg-violet-700/75 data-[disabled]:opacity-45">
              <Primitive.ItemText>{option.label}</Primitive.ItemText>
              <Primitive.ItemIndicator className="absolute right-2"><Check className="h-4 w-4" /></Primitive.ItemIndicator>
            </Primitive.Item>
          )}
          {available.length === 0 && <div className="px-3 py-2 text-xs text-violet-200">No options loaded for this selection</div>}
        </Primitive.Viewport>
      </Primitive.Content>
    </Primitive.Portal>
  </Primitive.Root>
  {clearable && !!value && <button type="button" onClick={() => onChange("")} aria-label={`Clear ${placeholder}`} title={`Clear ${placeholder}`}
    className="rounded-xl border border-violet-400/25 bg-[#321c60]/90 px-2 text-violet-100 hover:bg-fuchsia-500/20"><X className="h-4 w-4" /></button>}
  </div>;
}
