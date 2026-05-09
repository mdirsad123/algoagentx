import React from "react";
import { cn } from "@/lib/utils";

interface GlassCardProps {
  children: React.ReactNode;
  className?: string;
  hoverEffect?: boolean;
  depth?: 1 | 2 | 3 | 4 | 5;
  floating?: boolean;
}

export const GlassCard: React.FC<GlassCardProps> = ({
  children,
  className = "",
  hoverEffect = true,
  depth = 1,
  floating = false,
}) => {
  return (
    <div
      className={cn(
        "glass-card rounded-2xl border border-white/10 bg-white/[0.05] shadow-xl shadow-purple-950/20 backdrop-blur-xl",
        hoverEffect && "hover:-translate-y-0.5 hover:border-white/20 hover:bg-white/[0.07] hover:shadow-2xl",
        floating && "float-glass",
        `depth-${depth}`,
        className
      )}
    >
      {children}
    </div>
  );
};
