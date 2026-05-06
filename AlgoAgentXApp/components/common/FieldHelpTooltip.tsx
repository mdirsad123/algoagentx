"use client";

import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { HelpCircle } from "lucide-react";

export type FieldHelpTooltipProps = {
  content: string;
  label?: string;
  className?: string;
};

type TooltipPosition = {
  left: number;
  top: number;
  transform: string;
};

const TOOLTIP_WIDTH = 320;
const VIEWPORT_PADDING = 16;

export function FieldHelpTooltip({ content, label = "Field help", className = "" }: FieldHelpTooltipProps) {
  const [open, setOpen] = useState(false);
  const [mounted, setMounted] = useState(false);
  const [position, setPosition] = useState<TooltipPosition>({
    left: 0,
    top: 0,
    transform: "translateX(-50%)",
  });
  const buttonRef = useRef<HTMLButtonElement | null>(null);

  const updatePosition = () => {
    const button = buttonRef.current;
    if (!button || typeof window === "undefined") return;

    const rect = button.getBoundingClientRect();
    const viewportWidth = window.innerWidth || document.documentElement.clientWidth;
    const viewportHeight = window.innerHeight || document.documentElement.clientHeight;
    const estimatedHeight = 96;
    const preferredTop = rect.bottom + 10;
    const showAbove = preferredTop + estimatedHeight > viewportHeight - VIEWPORT_PADDING;
    const top = showAbove ? Math.max(VIEWPORT_PADDING, rect.top - estimatedHeight - 10) : preferredTop;
    const rawLeft = rect.left + rect.width / 2;
    const minLeft = VIEWPORT_PADDING + TOOLTIP_WIDTH / 2;
    const maxLeft = Math.max(minLeft, viewportWidth - VIEWPORT_PADDING - TOOLTIP_WIDTH / 2);
    const left = Math.min(Math.max(rawLeft, minLeft), maxLeft);

    setPosition({ left, top, transform: "translateX(-50%)" });
  };

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!open) return;
    updatePosition();

    const handleOutsideClick = (event: MouseEvent | TouchEvent) => {
      if (buttonRef.current && event.target instanceof Node && buttonRef.current.contains(event.target)) {
        return;
      }
      setOpen(false);
    };

    window.addEventListener("resize", updatePosition);
    window.addEventListener("scroll", updatePosition, true);
    document.addEventListener("mousedown", handleOutsideClick);
    document.addEventListener("touchstart", handleOutsideClick);

    return () => {
      window.removeEventListener("resize", updatePosition);
      window.removeEventListener("scroll", updatePosition, true);
      document.removeEventListener("mousedown", handleOutsideClick);
      document.removeEventListener("touchstart", handleOutsideClick);
    };
  }, [open]);

  const tooltipId = `field-help-${label.replace(/[^a-zA-Z0-9]+/g, "-").toLowerCase()}`;

  const tooltip = mounted && open
    ? createPortal(
        <div
          id={tooltipId}
          role="tooltip"
          className="fixed z-[9999] w-[min(320px,calc(100vw-32px))] rounded-xl border border-primary/50 bg-[#27104d]/98 px-3.5 py-2.5 text-left text-xs font-medium leading-relaxed text-white shadow-2xl shadow-black/50 backdrop-blur-xl"
          style={{ left: position.left, top: position.top, transform: position.transform }}
        >
          {content}
        </div>,
        document.body,
      )
    : null;

  return (
    <span className={`inline-flex items-center ${className}`}>
      <button
        ref={buttonRef}
        type="button"
        aria-label={label}
        aria-describedby={open ? tooltipId : undefined}
        aria-expanded={open}
        onMouseEnter={() => {
          setOpen(true);
          requestAnimationFrame(updatePosition);
        }}
        onMouseLeave={() => setOpen(false)}
        onFocus={() => {
          setOpen(true);
          requestAnimationFrame(updatePosition);
        }}
        onBlur={() => setOpen(false)}
        onClick={(event) => {
          event.preventDefault();
          event.stopPropagation();
          setOpen((current) => !current);
          requestAnimationFrame(updatePosition);
        }}
        className="inline-flex h-5 w-5 items-center justify-center rounded-full border border-primary/50 bg-primary/25 text-primary-foreground shadow-sm shadow-primary/20 transition hover:border-primary hover:bg-primary/40 focus:outline-none focus:ring-2 focus:ring-primary/60"
      >
        <HelpCircle className="h-3.5 w-3.5" aria-hidden="true" />
      </button>
      {tooltip}
    </span>
  );
}

export default FieldHelpTooltip;
