"use client"
import { TooltipProvider } from "@/components/ui/tooltip";
import { ClientProvider } from "@/provider";
import React from "react";
import { NotificationProvider } from "@/contexts/notification-context";

export default function RootLayout({
  children,
  params: { locale },
}: Readonly<{
  children: React.ReactNode;
  params: { locale: string };
}>) {

 return (
  <NotificationProvider>
    <ClientProvider locale={locale}>
      <TooltipProvider>
        {/* Simple container for non-authenticated pages */}
        <div className="min-h-screen bg-background">
          {children}
        </div>
      </TooltipProvider>
    </ClientProvider>
  </NotificationProvider>
 );
}
