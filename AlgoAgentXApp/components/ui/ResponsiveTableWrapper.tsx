import React from "react";
import { cn } from "@/lib/utils";

interface ResponsiveTableWrapperProps {
  children: React.ReactNode;
  className?: string;
  maxHeight?: string;
}

export function ResponsiveTableWrapper({ children, className, maxHeight }: ResponsiveTableWrapperProps) {
  return (
    <div
      className={cn(
        "responsive-table-wrapper overflow-x-auto rounded-2xl border border-white/10 bg-black/10 shadow-inner shadow-black/10",
        maxHeight && "overflow-y-auto",
        className
      )}
      style={maxHeight ? { maxHeight } : undefined}
    >
      {children}
    </div>
  );
}
