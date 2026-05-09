"use client";

import React, { useEffect, useMemo, useState } from "react";
import { usePathname } from "next/navigation";
import { NotificationProvider } from "@/contexts/notification-context";
import { Toaster } from "@/components/ui/toaster";
import CouponAnnouncementBar from "@/components/common/CouponAnnouncementBar";
import Sidebar from "./Sidebar";
import Topbar from "./Topbar";

const SIDEBAR_WIDTH_EXPANDED = 256;
const SIDEBAR_WIDTH_COLLAPSED = 96;
const DESKTOP_BREAKPOINT = 1024;

interface AppShellProps {
  children: React.ReactNode;
  pageTitle?: string;
  showCouponBar?: boolean;
}

export default function AppShell({ children, pageTitle, showCouponBar = false }: AppShellProps) {
  const pathname = usePathname();
  const isAuthPage = pathname.startsWith("/auth") || pathname === "/login" || pathname === "/register";
  const isAdminPage = pathname.startsWith("/admin");
  const [isCompactViewport, setIsCompactViewport] = useState(false);
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [isMobileOpen, setIsMobileOpen] = useState(false);

  useEffect(() => {
    const syncSidebarMode = () => {
      const compact = window.innerWidth < DESKTOP_BREAKPOINT;
      setIsCompactViewport(compact);
      if (compact) {
        setIsMobileOpen(false);
      }
    };

    syncSidebarMode();
    window.addEventListener("resize", syncSidebarMode);
    return () => window.removeEventListener("resize", syncSidebarMode);
  }, []);

  useEffect(() => {
    setIsMobileOpen(false);
  }, [pathname]);

  useEffect(() => {
    if (!isMobileOpen) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setIsMobileOpen(false);
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [isMobileOpen]);

  const sidebarOffset = useMemo(() => {
    if (isCompactViewport) return 0;
    return isCollapsed ? SIDEBAR_WIDTH_COLLAPSED : SIDEBAR_WIDTH_EXPANDED;
  }, [isCollapsed, isCompactViewport]);

  if (isAuthPage) {
    return <>{children}</>;
  }

  return (
    <NotificationProvider>
      <div className="h-[100dvh] overflow-hidden bg-gradient-to-br from-[#120826] via-[#4a178f] to-[#1a2448] text-white">
        {isCompactViewport && isMobileOpen && (
          <button
            type="button"
            aria-label="Close sidebar overlay"
            className="fixed inset-0 z-40 bg-black/55 backdrop-blur-sm lg:hidden"
            onClick={() => setIsMobileOpen(false)}
          />
        )}

        <Sidebar
          isCollapsed={isCollapsed}
          setIsCollapsed={setIsCollapsed}
          isCompactViewport={isCompactViewport}
          isMobileOpen={isMobileOpen}
          onMobileClose={() => setIsMobileOpen(false)}
        />

        <div
          className={`user-shell-content ${isAdminPage ? "admin-shell-content" : ""} flex h-full min-w-0 flex-1 flex-col transition-[margin-left] duration-300 ease-in-out`}
          style={{ marginLeft: sidebarOffset }}
        >
          {showCouponBar && <CouponAnnouncementBar />}
          <Topbar pageTitle={pageTitle} onMenuClick={() => setIsMobileOpen(true)} showMenuButton={isCompactViewport} />

          <main
            className={
              isAdminPage
                ? "admin-main flex-1 overflow-y-auto overflow-x-hidden hide-scrollbar"
                : "flex-1 overflow-y-auto overflow-x-hidden hide-scrollbar"
            }
          >
            <div
              className={
                isAdminPage
                  ? "mx-auto w-full max-w-[1700px] min-w-0 px-4 py-4 sm:px-6 sm:py-5 lg:px-8 lg:py-7"
                  : "mx-auto w-full max-w-[1700px] min-w-0 px-4 py-4 sm:px-6 sm:py-5 lg:px-8 lg:py-7"
              }
            >
              {children}
            </div>
          </main>
        </div>
      </div>
      <Toaster />
    </NotificationProvider>
  );
}
