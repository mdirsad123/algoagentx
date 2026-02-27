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
} from "lucide-react";
import React from "react";
import { withLocale, normalizePath } from "@/lib/route";

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

  // Determine active menu item based on current pathname
  const getIsActive = React.useCallback((href: string) => {
    const normalizedPath = normalizePath(pathname);
    const normalizedHref = normalizePath(href);
    
    // Active when:
    // 1. currentPath === href
    // 2. OR currentPath startsWith(href + "/")
    return normalizedPath === normalizedHref || normalizedPath.startsWith(normalizedHref + '/');
  }, [pathname]);

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
  ), [getIsActive]);

  return sidebarContent;
});
