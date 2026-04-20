import React from "react";

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
  const baseClasses = `
    glass-card
    ${hoverEffect ? 'hover:shadow-2xl hover:border-border/70' : ''}
    ${floating ? 'float-glass' : ''}
    depth-${depth}
  `;
  
  return (
    <div className={`${baseClasses} ${className}`}>
      {children}
    </div>
  );
};
