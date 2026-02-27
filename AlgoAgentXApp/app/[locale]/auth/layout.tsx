"use client";

import React from 'react'
import { TooltipProvider } from "@/components/ui/tooltip";
import { ClientProvider } from "@/provider";
import { NotificationProvider } from "@/contexts/notification-context";

interface AuthLayoutProps {
  children: React.ReactNode;
  params: { locale: string };
}

export default function AuthLayout({ 
  children, 
  params: { locale } 
}: AuthLayoutProps) {
  return (
    <NotificationProvider>
      <ClientProvider locale={locale}>
        <TooltipProvider>
          {/* Clean auth layout - NO sidebar, NO header */}
          <div className="min-h-screen bg-background">
            {children}
          </div>
        </TooltipProvider>
      </ClientProvider>
    </NotificationProvider>
  )
}
