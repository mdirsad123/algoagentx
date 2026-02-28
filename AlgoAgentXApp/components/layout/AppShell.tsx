"use client"

import React from "react";
import { usePathname } from "next/navigation";
import { NotificationProvider } from "@/contexts/notification-context";
import { Toaster } from "@/components/ui/toaster";
import Sidebar from "./Sidebar";
import Topbar from "./Topbar";

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
      <div className="flex h-screen overflow-hidden bg-gray-50 dark:bg-dark-background">
        {/* Sidebar - Fixed Position */}
        <Sidebar />
        
        {/* Main Content Area - Offset for fixed sidebar */}
        <div className="flex-1 flex flex-col ml-16 lg:ml-64 transition-all duration-300 ease-in-out">
          {/* Topbar */}
          <Topbar pageTitle={pageTitle} />
          
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


