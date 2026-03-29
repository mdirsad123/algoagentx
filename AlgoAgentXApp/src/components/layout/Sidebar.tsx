"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";

// Lazy load icons to reduce bundle size
const Home = React.lazy(() => import("lucide-react").then(mod => ({ default: mod.Home })));
const BarChart3 = React.lazy(() => import("lucide-react").then(mod => ({ default: mod.BarChart3 })));
const Layers = React.lazy(() => import("lucide-react").then(mod => ({ default: mod.Layers })));
const PlayCircle = React.lazy(() => import("lucide-react").then(mod => ({ default: mod.PlayCircle })));
const History = React.lazy(() => import("lucide-react").then(mod => ({ default: mod.History })));
const FileText = React.lazy(() => import("lucide-react").then(mod => ({ default: mod.FileText })));
const Settings = React.lazy(() => import("lucide-react").then(mod => ({ default: mod.Settings })));
const User = React.lazy(() => import("lucide-react").then(mod => ({ default: mod.User })));
const CreditCard = React.lazy(() => import("lucide-react").then(mod => ({ default: mod.CreditCard })));
const ChevronRight = React.lazy(() => import("lucide-react").then(mod => ({ default: mod.ChevronRight })));
const ChevronLeft = React.lazy(() => import("lucide-react").then(mod => ({ default: mod.ChevronLeft })));
const Users = React.lazy(() => import("lucide-react").then(mod => ({ default: mod.Users })));
const Database = React.lazy(() => import("lucide-react").then(mod => ({ default: mod.Database })));
const Shield = React.lazy(() => import("lucide-react").then(mod => ({ default: mod.Shield })));
const DollarSign = React.lazy(() => import("lucide-react").then(mod => ({ default: mod.DollarSign })));
const TrendingUp = React.lazy(() => import("lucide-react").then(mod => ({ default: mod.TrendingUp })));

// Define menu items with proper locale-aware URLs
const userMenuItems = [
  { icon: Home, label: "Dashboard", href: "/dashboard" },
  { icon: Layers, label: "Brokers", href: "/brokers" },
  { icon: BarChart3, label: "Strategies", href: "/strategies" },
  { icon: PlayCircle, label: "Backtest", href: "/backtest" },
  { icon: History, label: "Backtest History", href: "/backtest-history" },
  { icon: FileText, label: "Reports", href: "/reports" },
  { icon: CreditCard, label: "Pricing", href: "/pricing" },
  { icon: DollarSign, label: "Credits", href: "/credits" },
  { icon: User, label: "My Profile", href: "/myprofile" },
  { icon: Settings, label: "Settings", href: "/settings" },
];

const adminMenuItems = [
  { icon: Home, label: "Dashboard", href: "/admin/dashboard" },
  { icon: Users, label: "Users", href: "/admin/users" },
  { icon: CreditCard, label: "Subscriptions", href: "/admin/subscriptions" },
  { icon: DollarSign, label: "Payments", href: "/admin/payments" },
  { icon: Database, label: "Credits", href: "/admin/credits" },
  { icon: FileText, label: "Orders", href: "/admin/orders" },
  { icon: TrendingUp, label: "Backtests", href: "/admin/backtests" },
  { icon: Shield, label: "Support Tickets", href: "/admin/support-tickets" },
  { icon: Layers, label: "Strategy Requests", href: "/admin/strategy-requests" },
  { icon: BarChart3, label: "AI Jobs", href: "/admin/ai-jobs" },
];

// Memoize SidebarItem to prevent unnecessary re-renders
const SidebarItem = React.memo(function SidebarItem({
  icon: Icon,
  label,
  href,
  isActive,
  isCollapsed,
}: {
  icon: any;
  label: string;
  href: string;
  isActive: boolean;
  isCollapsed: boolean;
}) {
  return (
    <Link
      href={href}
      prefetch={true}
      className={`flex items-center gap-3 px-3 py-2 rounded-xl transition-all duration-300 ease-in-out group
        ${isActive 
          ? "bg-primary/10 border-l-3 border-primary text-primary" 
          : "text-foreground hover:bg-primary/10 hover:border-l-3 hover:border-primary hover:text-primary"
        }
        ${isCollapsed ? "justify-center" : ""}
      `}
    >
      <div className={`p-2 rounded-lg transition-all duration-300 ease-in-out
        ${isActive 
          ? "bg-gradient-to-r from-blue-500 to-cyan-500 text-white shadow-lg shadow-blue-500/30" 
          : "bg-muted text-muted-foreground group-hover:bg-gradient-to-r group-hover:from-blue-500 group-hover:to-cyan-500 group-hover:text-white group-hover:shadow-lg group-hover:shadow-blue-500/20"
        }`}>
        <Icon className={`w-5 h-5 ${isCollapsed ? "mx-auto" : ""} transition-colors duration-200`} />
      </div>
      {!isCollapsed && (
        <span className="text-sm font-medium tracking-wide transition-colors duration-200">{label}</span>
      )}
    </Link>
  );
});

SidebarItem.displayName = "SidebarItem";

export default React.memo(function Sidebar() {
  const pathname = usePathname();
  const [isCollapsed, setIsCollapsed] = useState(false);

  // Check screen size on mount and resize to set initial collapsed state
  useEffect(() => {
    const checkScreenSize = () => {
      setIsCollapsed(window.innerWidth < 1024);
    };
    checkScreenSize();
    window.addEventListener('resize', checkScreenSize);
    return () => window.removeEventListener('resize', checkScreenSize);
  }, []);

  // Determine active menu item based on current pathname
  const getIsActive = React.useCallback((href: string) => {
    // Remove locale prefix from pathname for comparison
    const pathWithoutLocale = pathname.replace(/^\/[a-z]{2}/, '') || '/';
    const normalizedHref = href.startsWith('/') ? href : '/' + href;
    return pathWithoutLocale === normalizedHref || pathWithoutLocale.startsWith(normalizedHref + '/');
  }, [pathname]);

  // Get menu items based on user role
  const getMenuItems = React.useCallback(() => {
    // For now, always show user menu items
    // In the future, this can be enhanced with user context
    return userMenuItems;
  }, []);

  // Memoize the sidebar content to prevent unnecessary re-renders
  const sidebarContent = React.useMemo(() => {
    const menuItems = getMenuItems();
    return (
      <aside 
        className={`min-h-screen border-r border-white/20 bg-gradient-to-b from-purple-900/50 to-indigo-900/50 backdrop-blur-xl transition-all duration-300 ease-in-out
          ${isCollapsed ? "w-16" : "w-64"}
          fixed left-0 top-0 z-40 shadow-lg shadow-purple-500/20
        `}
      >
        {/* LOGO HEADER */}
        <div className={`flex items-center justify-between h-16 px-4 border-b border-border ${isCollapsed ? "justify-center" : ""}`}>
          {!isCollapsed ? (
            <div className="flex items-center gap-4">
              {/* Logo Container */}
              <div className="relative">
                <div className="p-3 rounded-xl">
                  <img 
                    src="/images/algoagentx_icon.jpeg" 
                    alt="AlgoAgentX Logo"
                    className="w-8 h-8 object-contain"
                  />
                </div>
              </div>

              <div className="flex flex-col">
                <span className="text-lg font-bold bg-gradient-to-r from-blue-600 via-blue-700 to-cyan-600 bg-clip-text text-transparent">
                  AlgoAgentX
                </span>
                <span className="text-xs font-medium text-foreground tracking-wider">
                  AI TRADING
                </span>
              </div>
            </div>
          ) : (
            <div className="relative">
              <div className="p-2.5 rounded-lg">
                <img 
                  src="/images/algoagentx_icon.jpeg" 
                  alt="AlgoAgentX Logo"
                  className="w-8 h-8 object-contain"
                />
              </div>
            </div>
          )}
          <Button
            variant="ghost"
            size="sm"
            className="ml-2 p-2 hover:bg-accent transition-colors"
            onClick={() => setIsCollapsed(!isCollapsed)}
            aria-label={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {isCollapsed ? (
              <ChevronRight className="w-4 h-4 text-foreground" />
            ) : (
              <ChevronLeft className="w-4 h-4 text-foreground" />
            )}
          </Button>
        </div>

        {/* MENU NAVIGATION */}
        <nav className="flex-1 px-2 py-4 space-y-1">
          {menuItems.map((item) => (
            <SidebarItem
              key={item.href}
              icon={item.icon}
              label={item.label}
              href={item.href}
              isActive={getIsActive(item.href)}
              isCollapsed={isCollapsed}
            />
          ))}
        </nav>

        {/* USER SECTION */}
        <div className="p-4 border-t border-border space-y-2">
          <Link
            href="/profile"
            prefetch={true}
            className={`flex items-center gap-3 px-3 py-2 rounded-xl transition-all duration-200 group
              ${isCollapsed ? "justify-center" : ""}
              text-foreground hover:bg-accent hover:text-foreground
            `}
          >
            <div className="p-2 rounded-lg bg-muted text-muted-foreground group-hover:bg-gradient-to-r group-hover:from-blue-500 group-hover:to-cyan-500 group-hover:text-white group-hover:shadow-lg group-hover:shadow-blue-500/20 transition-colors">
              <User className="w-5 h-5" />
            </div>
            {!isCollapsed && (
              <span className="text-sm font-medium tracking-wide">Profile</span>
            )}
          </Link>
          <Link
            href="/settings"
            prefetch={true}
            className={`flex items-center gap-3 px-3 py-2 rounded-xl transition-all duration-200 group
              ${isCollapsed ? "justify-center" : ""}
              text-foreground hover:bg-accent hover:text-foreground
            `}
          >
            <div className="p-2 rounded-lg bg-muted text-muted-foreground group-hover:bg-gradient-to-r group-hover:from-blue-500 group-hover:to-cyan-500 group-hover:text-white group-hover:shadow-lg group-hover:shadow-blue-500/20 transition-colors">
              <Settings className="w-5 h-5" />
            </div>
            {!isCollapsed && (
              <span className="text-sm font-medium tracking-wide">Settings</span>
            )}
          </Link>
        </div>
      </aside>
    );
  }, [getIsActive, isCollapsed, getMenuItems]);

  return sidebarContent;
});
