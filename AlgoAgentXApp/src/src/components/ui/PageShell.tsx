import React from "react";

interface PageShellProps {
  children: React.ReactNode;
  className?: string;
  floating?: boolean;
}

export const PageShell: React.FC<PageShellProps> = ({ children, className = "", floating = false }) => {
  return (
    <div className={`min-h-screen app-gradient-bg ${floating ? 'float-glass' : ''} ${className}`}>
      <div className="container mx-auto px-4 py-8">
        {children}
      </div>
    </div>
  );
};
