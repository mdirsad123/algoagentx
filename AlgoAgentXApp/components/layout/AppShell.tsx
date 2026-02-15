"use client"

import React from "react";
import { usePathname } from "next/navigation";
import { NotificationProvider } from "@/contexts/notification-context";
import { Toaster } from "@/components/ui/toaster";

interface AppShellProps {
  children: React.ReactNode;
  pageTitle?: string;
}

export default function AppShell({ children, pageTitle }: AppShellProps) {
  const pathname = usePathname();
  const isAuthPage = pathname.startsWith('/auth');

  // Don't show layout on auth pages
  if (isAuthPage) {
    return <>{children}</>;
  }

  return (
    <NotificationProvider>
      <div className="flex h-screen overflow-hidden bg-gray-50">
        {/* Main Content Area - Full width without sidebar or topbar */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Scrollable Content */}
          <main className="flex-1 overflow-y-auto hide-scrollbar">
            <div className="p-6">
              {children}
            </div>
          </main>
        </div>
      </div>
      <Toaster />
    </NotificationProvider>
  );
}


