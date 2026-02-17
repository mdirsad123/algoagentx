"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Home,
  BarChart3,
  Layers,
  PlayCircle,
  History,
  FileText,
  Settings,
  Sparkles,
  CreditCard,
  Badge,
  Coins,
} from "lucide-react";
import React from "react";
import { withLocale, normalizePath } from "@/lib/route";
import { useCreditsSummary } from "@/hooks/useCreditsSummary";
import { LoadingSkeleton } from "@/components/ui/loading-skeleton";
import EmptyState from "@/components/shared/empty-state";

// Define menu items with proper locale-aware URLs
const menuItems = [
  { icon: Home, label: "Dashboard", href: "/dashboard" },
  { icon: Layers, label: "Brokers", href: "/brokers" },
  { icon: BarChart3, label: "Strategies", href: "/strategies" },
  { icon: Sparkles, label: "AI Screener", href: "/ai-screener" },
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
}: {
  icon: any;
  label: string;
  href: string;
  isActive: boolean;
}) {
  return (
    <Link
      href={href}
      prefetch={true}
      className={`flex items-center gap-3 px-3 py-2 rounded-md transition-colors duration-200
        ${
          isActive
            ? "bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 border-r-2 border-blue-600 dark:border-blue-500"
            : "text-gray-700 dark:text-gray-300 hover:bg-blue-50 dark:hover:bg-gray-800 hover:text-blue-600 dark:hover:text-blue-400"
        }
      `}
    >
      <Icon className="w-5 h-5" />
      <span className="text-sm font-medium">{label}</span>
    </Link>
  );
});

SidebarItem.displayName = "SidebarItem";

export default React.memo(function Sidebar() {
  const pathname = usePathname();
  const { creditsSummary, loading, error } = useCreditsSummary();

  // Determine active menu item based on current pathname
  const getIsActive = React.useCallback((href: string) => {
    const normalizedPath = normalizePath(pathname);
    const normalizedHref = normalizePath(href);
    
    // Active when:
    // 1. currentPath === href
    // 2. OR currentPath startsWith(href + "/")
    return normalizedPath === normalizedHref || normalizedPath.startsWith(normalizedHref + '/');
  }, [pathname]);

  // Get plan display name and credits display
  const getPlanDisplay = (planName: string) => {
    switch (planName?.toUpperCase()) {
      case 'PRO':
        return 'Pro';
      case 'PREMIUM':
        return 'Premium';
      case 'TRIAL':
        return 'Trial';
      default:
        return 'Free';
    }
  };

  const getCreditsDisplay = (planName: string, balance: number) => {
    const plan = planName?.toUpperCase();
    if (plan === 'PRO' || plan === 'PREMIUM') {
      return 'Unlimited';
    }
    return Math.floor(balance).toString();
  };

  // Memoize the sidebar content to prevent unnecessary re-renders
  const sidebarContent = React.useMemo(() => (
    <aside className="w-[260px] min-h-screen border-r border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 flex flex-col">
      {/* LOGO */}
      <div className="h-[90px] flex items-center justify-center border-b border-gray-200 dark:border-gray-700">
        <img
          src="/product.svg"
          alt="AlgoAgentX"
          className="h-[60px] object-contain"
        />
      </div>

      {/* CREDITS BADGE */}
      <div className="px-3 py-3 border-b border-gray-200 dark:border-gray-700">
        {loading ? (
          <LoadingSkeleton className="h-20 w-full rounded-lg" />
        ) : error ? (
          <EmptyState
            title="Unable to load credits"
            description="Please try again later"
            variant="error"
          />
        ) : creditsSummary ? (
          <div className="bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-gray-800 dark:to-gray-900 rounded-lg p-3 border border-blue-100 dark:border-gray-700">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium text-gray-600 dark:text-gray-400">Plan</span>
              <Badge 
                variant="secondary" 
                className="text-xs px-2 py-1"
              >
                {getPlanDisplay(creditsSummary.plan_name)}
              </Badge>
            </div>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Coins className="w-4 h-4 text-yellow-600" />
                <span className="text-xs font-medium text-gray-600 dark:text-gray-400">Credits</span>
              </div>
              <span className="text-sm font-bold text-gray-900 dark:text-white">
                {getCreditsDisplay(creditsSummary.plan_name, creditsSummary.credit_balance)}
              </span>
            </div>
            {creditsSummary.plan_name?.toUpperCase() !== 'PRO' && creditsSummary.plan_name?.toUpperCase() !== 'PREMIUM' && (
              <div className="mt-2 pt-2 border-t border-gray-200 dark:border-gray-700">
                <Link
                  href={withLocale(pathname, "/pricing")}
                  prefetch={true}
                  className="w-full flex items-center justify-center px-3 py-1.5 rounded-md bg-blue-500 hover:bg-blue-600 text-white text-xs font-medium transition-colors duration-200"
                >
                  Upgrade Plan
                </Link>
              </div>
            )}
          </div>
        ) : null}
      </div>

      {/* MENU */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {menuItems.map((item) => (
          <SidebarItem
            key={item.href}
            icon={item.icon}
            label={item.label}
            href={withLocale(pathname, item.href)}
            isActive={getIsActive(item.href)}
          />
        ))}
      </nav>

      {/* FOOTER */}
      <div className="p-4 border-t border-gray-200 dark:border-gray-700 space-y-2">
        <Link
          href={withLocale(pathname, "/pricing")}
          prefetch={true}
          className="w-full flex items-center gap-3 px-3 py-2 rounded-md bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 border border-blue-200 dark:border-blue-800 hover:bg-blue-100 dark:hover:bg-blue-900/30 transition-colors duration-200"
        >
          <CreditCard className="w-5 h-5" />
          <span className="text-sm font-medium">Upgrade</span>
        </Link>
        <Link
          href={withLocale(pathname, "/myprofile")}
          prefetch={true}
          className="w-full flex items-center gap-3 px-3 py-2 rounded-md text-gray-600 dark:text-gray-300 hover:bg-blue-50 dark:hover:bg-gray-800 hover:text-blue-600 dark:hover:text-blue-400 transition-colors duration-200"
        >
          <Settings className="w-5 h-5" />
          <span className="text-sm font-medium">My Profile</span>
        </Link>
      </div>
    </aside>
  ), [getIsActive, creditsSummary, loading, error, pathname]);

  return sidebarContent;
});
