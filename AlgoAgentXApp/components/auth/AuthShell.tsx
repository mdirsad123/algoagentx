import React from "react";

interface AuthShellProps {
  children: React.ReactNode;
  title?: string;
  subtitle?: string;
  icon?: React.ReactNode;
}

export default function AuthShell({ children, title, subtitle, icon }: AuthShellProps) {
  return (
    <div className="min-h-[100dvh] w-full overflow-x-hidden bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      {title && (
        <div className="absolute top-8 left-8 text-white">
          <div className="flex items-center gap-3">
            {icon}
            <div>
              <h1 className="text-2xl font-bold">{title}</h1>
              {subtitle && <p className="text-purple-300 text-sm">{subtitle}</p>}
            </div>
          </div>
        </div>
      )}
      {children}
    </div>
  );
}
