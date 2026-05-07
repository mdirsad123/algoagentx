"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Check, Sparkles, Tag } from "lucide-react";
import { couponBarApi, CouponBarConfig } from "@/lib/api/coupon-bar";

function copyTextFallback(text: string) {
  if (typeof document === "undefined") return false;
  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.setAttribute("readonly", "");
  textarea.style.position = "fixed";
  textarea.style.left = "-9999px";
  textarea.style.top = "0";
  document.body.appendChild(textarea);
  textarea.select();
  let copied = false;
  try {
    copied = document.execCommand("copy");
  } catch {
    copied = false;
  } finally {
    document.body.removeChild(textarea);
  }
  return copied;
}

export default function CouponAnnouncementBar() {
  const [config, setConfig] = useState<CouponBarConfig | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    let alive = true;
    couponBarApi
      .getPublic()
      .then((data) => {
        if (alive) setConfig(data);
      })
      .catch(() => {
        if (alive) setConfig(null);
      });
    return () => {
      alive = false;
    };
  }, []);

  useEffect(() => {
    if (!copied) return;
    const timer = window.setTimeout(() => setCopied(false), 1400);
    return () => window.clearTimeout(timer);
  }, [copied]);

  const message = useMemo(() => config?.message?.trim() || "", [config?.message]);
  const code = useMemo(() => config?.code?.trim() || "", [config?.code]);
  const shouldShow = Boolean(config?.enabled && message);

  const handleCopyCode = useCallback(async () => {
    if (!code) return;
    let ok = false;
    try {
      if (navigator?.clipboard?.writeText) {
        await navigator.clipboard.writeText(code);
        ok = true;
      }
    } catch {
      ok = false;
    }
    if (!ok) ok = copyTextFallback(code);
    if (ok) setCopied(true);
  }, [code]);

  const renderItem = useCallback(
    (index: number) => (
      <span
        key={`coupon-marquee-item-${index}`}
        className="mx-8 inline-flex items-center gap-3 whitespace-nowrap text-sm font-semibold text-white md:text-[15px]"
      >
        <Sparkles className="h-4 w-4 shrink-0 text-fuchsia-100" />
        <span>{message}</span>
        {code ? (
          <button
            type="button"
            title="Copy coupon code"
            aria-label={`Copy coupon code ${code}`}
            onClick={handleCopyCode}
            className="inline-flex shrink-0 items-center gap-1.5 rounded-full border border-white/30 bg-white/20 px-3 py-1 text-xs font-bold uppercase tracking-[0.18em] text-white shadow-lg shadow-fuchsia-950/20 backdrop-blur transition hover:border-white/45 hover:bg-white/30 focus:outline-none focus:ring-2 focus:ring-white/70 focus:ring-offset-2 focus:ring-offset-indigo-700"
          >
            {copied ? <Check className="h-3.5 w-3.5" /> : <Tag className="h-3.5 w-3.5" />}
            {copied ? "Copied" : code}
          </button>
        ) : null}
      </span>
    ),
    [code, copied, handleCopyCode, message],
  );

  if (!shouldShow) return null;

  return (
    <div className="relative z-30 h-10 w-full overflow-hidden border-b border-white/10 bg-gradient-to-r from-fuchsia-600 via-indigo-600 to-blue-600 shadow-lg shadow-fuchsia-950/20">
      <div className="coupon-marquee flex h-full min-w-max items-center hover:[animation-play-state:paused]">
        {[0, 1, 2, 3].map(renderItem)}
      </div>
    </div>
  );
}
