import React from "react";
import { cn } from "@/lib/utils";

interface PageHeaderProps {
  title: string;
  subtitle?: string;
  description?: string;
  actions?: React.ReactNode;
  className?: string;
  floating?: boolean;
}

export const PageHeader: React.FC<PageHeaderProps> = ({
  title,
  subtitle,
  description,
  actions,
  className = "",
  floating = false,
}) => {
  const helperText = subtitle || description;

  return (
    <div
      className={cn(
        "rounded-3xl border border-white/10 bg-white/[0.035] px-4 py-4 shadow-xl shadow-purple-950/20 backdrop-blur-xl sm:px-5 sm:py-5",
        floating && "float-glass",
        className
      )}
    >
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="min-w-0 space-y-1.5">
          <h1 className="truncate bg-gradient-to-r from-white via-purple-100 to-fuchsia-200 bg-clip-text text-2xl font-black tracking-tight text-transparent sm:text-3xl">
            {title}
          </h1>
          {helperText && (
            <p className="max-w-3xl text-sm leading-6 text-purple-100/75 sm:text-base">
              {helperText}
            </p>
          )}
        </div>
        {actions && (
          <div className="flex shrink-0 flex-wrap items-center gap-2 sm:gap-3">
            {actions}
          </div>
        )}
      </div>
    </div>
  );
};
