import React from "react";
import { cn } from "@/lib/utils";

interface PageShellProps {
  children: React.ReactNode;
  className?: string;
  floating?: boolean;
}

export const PageShell: React.FC<PageShellProps> = ({ children, className = "", floating = false }) => {
  return (
    <div
      className={cn(
        "mx-auto w-full max-w-[1700px] min-w-0 space-y-4 px-0 py-0 sm:space-y-6 lg:space-y-7",
        floating && "float-glass",
        className
      )}
    >
      {children}
    </div>
  );
};
