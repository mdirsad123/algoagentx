"use client"
import Header from "@/components/shared/header";
import SideBar from "@/components/shared/sidebar";
import MobileMenu from "@/components/shared/mobile-menu"; // ⭐ ADDED
import PromoTicker from "@/components/shared/promo-ticker";
import { TooltipProvider } from "@/components/ui/tooltip";
import { ClientProvider } from "@/provider";
import { useConfig } from "@/hooks/use-config";
import React from "react";
import { NotificationProvider } from "@/contexts/notification-context";
import { Menu } from "lucide-react"; // ⭐ Hamburger icon

// Memoize components to prevent unnecessary re-renders
const MemoizedSideBar = React.memo(SideBar);
const MemoizedHeader = React.memo(Header);
const MemoizedMobileMenu = React.memo(MobileMenu);

export default function Layout({
  children,
  params: { locale },
}: Readonly<{
  children: React.ReactNode;
  params: { locale: string };
}>) {
  const [mounted, setMounted] = React.useState(false)
  const [config] = useConfig();
  const [openMenu, setOpenMenu] = React.useState(false); // ⭐ MOBILE SIDEBAR STATE

  const isRTL = locale === 'ar';
  const sidebarPosition = isRTL ? 'right' : 'left';

  // Use useMemo to cache computed values
  const sidebarLeft = React.useMemo(() => sidebarPosition === "left", [sidebarPosition]);
  const sidebarRight = React.useMemo(() => sidebarPosition === "right", [sidebarPosition]);

  React.useEffect(() => {
    setMounted(true)
  }, [])

  // Use useCallback for event handlers
  const handleOpenMenu = React.useCallback(() => {
    setOpenMenu(true);
  }, []);

  const handleCloseMenu = React.useCallback(() => {
    setOpenMenu(false);
  }, []);

  // Memoize the content container className
  const contentContainerClass = React.useMemo(() => (
    `overflow-y-auto hide-scrollbar bg-white mt-3 flex-1 ${
      sidebarLeft
        ? "mx-2 sm:mx-4 lg:ml-4 lg:mr-0"
        : "mx-2 sm:mx-4 lg:mr-4 lg:ml-0"
    }`
  ), [sidebarLeft]);

  // Memoize the mobile menu container className
  const mobileMenuContainerClass = React.useMemo(() => (
    `w-[260px] h-full bg-white shadow-xl ${
      isRTL ? "ml-auto" : ""
    }`
  ), [isRTL]);

 return (
  <NotificationProvider>
    <div className="flex h-screen overflow-hidden">
      <ClientProvider locale={locale}>
        <TooltipProvider>
          {/* Promo Ticker - Always visible at top */}
          <PromoTicker />

          {/* DESKTOP SIDEBAR - Memoized */}
          {mounted && sidebarLeft && (
            <div className="hidden lg:block">
              <MemoizedSideBar />
            </div>
          )}

          {/* PAGE CONTENT */}
          <main className="flex-1 w-full bg-background min-h-screen relative overflow-x-hidden">

            {/* HEADER with Hamburger - Memoized */}
            <div className="sticky top-0 z-50 bg-background flex items-center">

              {/* ⭐ MOBILE HAMBURGER BUTTON */}
              <button
                className="lg:hidden p-2"
                onClick={handleOpenMenu}
              >
                <Menu className="w-6 h-6" />
              </button>

              <MemoizedHeader />
            </div>

            {/* SCROLLABLE CONTENT - Memoized container */}
            <div className={contentContainerClass}>
              <div className="p-3 sm:p-4 md:p-6 dark:bg-gray-800 min-h-full">
                {/* Page transition wrapper */}
                <div className="animate-in fade-in-0 slide-in-from-right-1 duration-300">
                  {children}
                </div>
              </div>
            </div>

          </main>

          {/* DESKTOP RIGHT SIDEBAR (RTL) - Memoized */}
          {mounted && sidebarRight && (
            <div className="hidden lg:block">
              <MemoizedSideBar />
            </div>
          )}

          {/* ⭐ MOBILE SIDEBAR OVERLAY - Memoized */}
          {openMenu && (
            <div className="fixed inset-0 bg-black/40 z-50 lg:hidden">
              <div className={mobileMenuContainerClass}>
                <MemoizedMobileMenu setOpen={handleCloseMenu} />
              </div>
            </div>
          )}

        </TooltipProvider>
      </ClientProvider>
    </div>
  </NotificationProvider>
 );
}
