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
  User,
  CreditCard,
} from "lucide-react";

import React from "react";
import { AlgoAgentXLogo } from "@/components/branding/AlgoAgentXLogo";
import { Button } from "@/components/ui/button";

// Define menu items with proper locale-aware URLs
const menuItems = [
  { icon: Home, label: "Dashboard", href: "/dashboard" },
  { icon: Layers, label: "Brokers", href: "/brokers" },
  { icon: BarChart3, label: "Strategies", href: "/strategies" },
  { icon: PlayCircle, label: "Backtest", href: "/backtest" },
  { icon: History, label: "Backtest History", href: "/backtest-history" },
  { icon: FileText, label: "Reports", href: "/reports" },
  { icon: CreditCard, label: "Pricing", href: "/pricing" },
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
      className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200 group
        ${
          isActive
            ? "bg-blue-600/20 border-l-2 border-blue-400 text-white"
            : "text-gray-300 hover:bg-gray-800 hover:text-white hover:border-l-2 hover:border-gray-600"
        }
      `}
    >
      <Icon className={`w-5 h-5 transition-colors duration-200
        ${isActive ? "text-blue-400" : "text-gray-400 group-hover:text-blue-400"}`}
      />
      <span className="text-sm font-medium tracking-wide">{label}</span>
    </Link>
  );
});

SidebarItem.displayName = "SidebarItem";

export default React.memo(function Sidebar() {
  const pathname = usePathname();

  // Determine active menu item based on current pathname
  const getIsActive = React.useCallback((href: string) => {
    // Remove locale prefix from pathname for comparison
    const pathWithoutLocale = pathname.replace(/^\/[a-z]{2}/, '') || '/';
    return pathWithoutLocale === href || pathWithoutLocale.startsWith(href + '/');
  }, [pathname]);

  // Memoize the sidebar content to prevent unnecessary re-renders
  const sidebarContent = React.useMemo(() => (
    <aside className="w-[260px] min-h-screen border-r border-gray-800 bg-gray-950/80 backdrop-blur-xl flex flex-col">
      {/* LOGO HEADER */}
      <div className="h-[80px] flex items-center justify-center border-b border-gray-800">
        <AlgoAgentXLogo variant="full" size="md" />
      </div>

      {/* MENU NAVIGATION */}
      <nav className="flex-1 px-3 py-6 space-y-1">
        {menuItems.map((item) => (
          <SidebarItem
            key={item.href}
            icon={item.icon}
            label={item.label}
            href={item.href}
            isActive={getIsActive(item.href)}
          />
        ))}
      </nav>

      {/* USER SECTION */}
      <div className="p-4 border-t border-gray-800 space-y-3">
        <Link
          href="/profile"
          prefetch={true}
          className="w-full flex items-center gap-3 px-3 py-3 rounded-lg text-gray-300 hover:bg-gray-800 hover:text-white transition-all duration-200"
        >
          <User className="w-5 h-5 text-gray-400 group-hover:text-blue-400" />
          <span className="text-sm font-medium tracking-wide">Profile</span>
        </Link>
        <Link
          href="/settings"
          prefetch={true}
          className="w-full flex items-center gap-3 px-3 py-3 rounded-lg text-gray-300 hover:bg-gray-800 hover:text-white transition-all duration-200"
        >
          <Settings className="w-5 h-5 text-gray-400 group-hover:text-blue-400" />
          <span className="text-sm font-medium tracking-wide">Settings</span>
        </Link>
      </div>
    </aside>
  ), [getIsActive]);

  return sidebarContent;
});