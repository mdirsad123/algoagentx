"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, useEffect } from "react";
import {
  Home,
  BarChart3,
  Layers,
  PlayCircle,
  History,
  FileText,
  Settings,
  User,
  CreditCard,
  ChevronRight,
  ChevronLeft,
  Users,
  Database,
  Shield,
  DollarSign,
  TrendingUp,
} from "lucide-react";

import React from "react";
import { AlgoAgentXLogo } from "@/components/branding/AlgoAgentXLogo";
import { Button } from "@/components/ui/button";
import { useUser } from "@/contexts/user-context";

// Define menu items with proper locale-aware URLs
const userMenuItems = [
  { icon: Home, label: "Dashboard", href: "/dashboard" },
  { icon: Layers, label: "Brokers", href: "/brokers" },
  { icon: BarChart3, label: "Strategies", href: "/strategies" },
  { icon: PlayCircle, label: "Backtest", href: "/backtest" },
  { icon: History, label: "Backtest History", href: "/backtest-history" },
  { icon: FileText, label: "Reports", href: "/reports" },
  { icon: CreditCard, label: "Pricing", href: "/pricing" },
];

const adminMenuItems = [
  { icon: Home, label: "Dashboard", href: "/dashboard" },
  { icon: Users, label: "User Management", href: "/admin/users" },
  { icon: Database, label: "Database", href: "/admin/database" },
  { icon: Shield, label: "Admin Settings", href: "/admin/settings" },
  { icon: DollarSign, label: "Billing", href: "/admin/billing" },
  { icon: TrendingUp, label: "Analytics", href: "/admin/analytics" },
  { icon: Layers, label: "Brokers", href: "/brokers" },
  { icon: BarChart3, label: "Strategies", href: "/strategies" },
  { icon: PlayCircle, label: "Backtest", href: "/backtest" },
  { icon: History, label: "Backtest History", href: "/backtest-history" },
  { icon: FileText, label: "Reports", href: "/reports" },
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
          ? "bg-blue-50 dark:bg-blue-900/20 border-l-3 border-blue-400 text-blue-600 dark:text-blue-300" 
          : "text-gray-600 dark:text-dark-text-secondary hover:bg-blue-50 dark:hover:bg-blue-900/20 hover:border-l-3 hover:border-blue-300 hover:text-blue-500"
        }
        ${isCollapsed ? "justify-center" : ""}
      `}
    >
      <div className={`p-2 rounded-lg transition-all duration-300 ease-in-out
        ${isActive 
          ? "bg-gradient-to-r from-blue-500 to-cyan-500 text-white shadow-lg shadow-blue-500/30" 
          : "bg-gray-100 dark:bg-dark-surface-2 text-gray-600 dark:text-dark-text-secondary group-hover:bg-gradient-to-r group-hover:from-blue-500 group-hover:to-cyan-500 group-hover:text-white group-hover:shadow-lg group-hover:shadow-blue-500/20"
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
  const { user } = useUser();

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
    const userRole = user?.role?.toLowerCase() || 'user';
    if (userRole === 'admin') {
      return adminMenuItems;
    }
    return userMenuItems;
  }, [user?.role]);

  // Memoize the sidebar content to prevent unnecessary re-renders
  const sidebarContent = React.useMemo(() => {
    const menuItems = getMenuItems();
    return (
      <aside 
        className={`min-h-screen border-r border-gray-200 dark:border-dark-border bg-white/50 dark:bg-dark-surface backdrop-blur-xl transition-all duration-300 ease-in-out
          ${isCollapsed ? "w-16" : "w-64"}
          fixed left-0 top-0 z-40 shadow-lg
        `}
      >
        {/* LOGO HEADER */}
        <div className={`flex items-center justify-between h-16 px-4 border-b border-gray-200 dark:border-dark-border ${isCollapsed ? "justify-center" : ""}`}>
          {!isCollapsed ? (
            <div className="flex items-center gap-4">
              {/* Logo Container */}
              <div className="relative">
                <div className="p-3 rounded-xl">
                  <img 
                    src="/algoagentx_icon.jpeg" 
                    alt="AlgoAgentX Logo" 
                    className="w-8 h-8 object-contain"
                  />
                </div>
              </div>

              <div className="flex flex-col">
                <span className="text-lg font-bold bg-gradient-to-r from-blue-600 via-blue-700 to-cyan-600 bg-clip-text text-transparent">
                  AlgoAgentX
                </span>
                <span className="text-xs font-medium text-gray-600 dark:text-gray-300 tracking-wider">
                  AI TRADING
                </span>
              </div>
            </div>
          ) : (
            <div className="relative">
              <div className="p-2.5 rounded-lg">
                <img 
                  src="/algoagentx_icon.jpeg" 
                  alt="AlgoAgentX Logo" 
                  className="w-8 h-8 object-contain"
                />
              </div>
            </div>
          )}
          <Button
            variant="ghost"
            size="sm"
            className="ml-2 p-2 hover:bg-gray-200 dark:hover:bg-dark-surface-2 transition-colors"
            onClick={() => setIsCollapsed(!isCollapsed)}
            aria-label={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {isCollapsed ? (
              <ChevronRight className="w-4 h-4 text-gray-600 dark:text-dark-text-secondary" />
            ) : (
              <ChevronLeft className="w-4 h-4 text-gray-600 dark:text-dark-text-secondary" />
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
        <div className="p-4 border-t border-gray-200 dark:border-dark-border space-y-2">
          <Link
            href="/profile"
            prefetch={true}
            className={`flex items-center gap-3 px-3 py-2 rounded-xl transition-all duration-200 group
              ${isCollapsed ? "justify-center" : ""}
              text-gray-600 dark:text-dark-text-secondary hover:bg-gray-50 dark:hover:bg-dark-surface-2 hover:text-gray-900 dark:hover:text-dark-text-primary
            `}
          >
            <div className="p-2 rounded-lg bg-gray-100 dark:bg-dark-surface-2 text-gray-600 dark:text-dark-text-secondary group-hover:bg-blue-100 dark:group-hover:bg-dark-surface-2 group-hover:text-blue-600 dark:group-hover:text-dark-text-primary transition-colors">
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
              text-gray-600 dark:text-dark-text-secondary hover:bg-gray-50 dark:hover:bg-dark-surface-2 hover:text-gray-900 dark:hover:text-dark-text-primary
            `}
          >
            <div className="p-2 rounded-lg bg-gray-100 dark:bg-dark-surface-2 text-gray-600 dark:text-dark-text-secondary group-hover:bg-blue-100 dark:group-hover:bg-dark-surface-2 group-hover:text-blue-600 dark:group-hover:text-dark-text-primary transition-colors">
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
