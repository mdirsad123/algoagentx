"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import {
  BarChart3,
  ChevronLeft,
  ChevronRight,
  CreditCard,
  FileText,
  Headset,
  History,
  Home,
  Layers,
  PlayCircle,
  Settings,
  Shield,
  TrendingUp,
  User,
  Users,
  Wallet,
} from "lucide-react";
import { Button } from "@/components/ui/button";

const userMenuItems = [
  { icon: Home, label: "Dashboard", href: "/dashboard" },
  { icon: Layers, label: "Brokers", href: "/brokers" },
  { icon: BarChart3, label: "Strategies", href: "/strategies" },
  { icon: PlayCircle, label: "Backtest", href: "/backtest" },
  { icon: History, label: "Backtest History", href: "/backtest-history" },
  { icon: FileText, label: "Reports", href: "/reports" },
  { icon: CreditCard, label: "Pricing", href: "/pricing" },
  { icon: Wallet, label: "Credits", href: "/credits" },
  { icon: Headset, label: "Support Tickets", href: "/support-tickets" },
  // { icon: User, label: "My Profile", href: "/profile" },
  // { icon: Settings, label: "Settings", href: "/settings" },
];

const adminMenuItems = [
  { icon: Home, label: "Dashboard", href: "/admin/dashboard" },
  { icon: Users, label: "Users", href: "/admin/users" },
  { icon: CreditCard, label: "Subscriptions", href: "/admin/subscriptions" },
  { icon: Wallet, label: "Payments", href: "/admin/payments" },
  { icon: FileText, label: "Orders", href: "/admin/orders" },
  { icon: BarChart3, label: "Credits", href: "/admin/credits" },
  { icon: Layers, label: "Strategies", href: "/admin/strategy-requests" },
  { icon: TrendingUp, label: "Backtests", href: "/admin/backtests" },
  { icon: Shield, label: "Support Tickets", href: "/admin/support-tickets" },
];

function getCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

function SidebarItem({
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
      className={[
        "group flex items-center gap-3 rounded-2xl px-3 py-3 text-sm font-medium transition-all duration-200",
        isCollapsed ? "justify-center" : "justify-start",
        isActive
          ? "bg-white/16 text-white shadow-lg shadow-purple-900/30 ring-1 ring-white/10"
          : "text-purple-100/90 hover:bg-white/8 hover:text-white",
      ].join(" ")}
    >
      <span
        className={[
          "flex h-10 w-10 items-center justify-center rounded-xl border transition-all duration-200",
          isActive
            ? "border-white/10 bg-gradient-to-br from-fuchsia-500 to-violet-500 text-white shadow-lg"
            : "border-white/5 bg-white/5 text-purple-100 group-hover:border-white/10 group-hover:bg-white/10",
        ].join(" ")}
      >
        <Icon className="h-5 w-5" />
      </span>
      {!isCollapsed && <span className="truncate">{label}</span>}
    </Link>
  );
}

export default function Sidebar() {
  const pathname = usePathname();
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [role, setRole] = useState<string>("");

  useEffect(() => {
    const syncRole = () => {
      const cookieRole = getCookie("loggedinuserroleid") || getCookie("loggedinuserrole") || "";
      const storedUser = typeof window !== "undefined" ? localStorage.getItem("currentUser") : null;
      let nextRole = cookieRole;
      if (!nextRole && storedUser) {
        try {
          nextRole = JSON.parse(storedUser)?.role || "";
        } catch {}
      }
      setRole(String(nextRole || "").toLowerCase());
    };

    syncRole();
    const onResize = () => setIsCollapsed(window.innerWidth < 1280);
    onResize();
    window.addEventListener("resize", onResize);
    window.addEventListener("storage", syncRole);
    return () => {
      window.removeEventListener("resize", onResize);
      window.removeEventListener("storage", syncRole);
    };
  }, []);

  const isAdminSection = pathname.startsWith("/admin");
  const isAdminUser = role === "admin" || role === "1";
  const menuItems = isAdminSection || isAdminUser ? adminMenuItems : userMenuItems;
  const brandSubtitle = isAdminSection || isAdminUser ? "Admin Console" : "Trading Workspace";

  const getIsActive = (href: string) => pathname === href || pathname.startsWith(`${href}/`);

  const footerLinks = useMemo(() => {
    if (isAdminSection || isAdminUser) {
      return [
        { icon: User, label: "Profile", href: "/admin/profile" },
        { icon: Settings, label: "Settings", href: "/admin/settings" },
      ];
    }
    return [
      { icon: User, label: "Profile", href: "/profile" },
      { icon: Settings, label: "Settings", href: "/settings" },
    ];
  }, [isAdminSection, isAdminUser]);

  return (
    <aside
      className={[
        "fixed left-0 top-0 z-40 flex h-screen flex-col border-r border-white/10 bg-gradient-to-b from-[#4f1d95] via-[#341672] to-[#1f2647] text-white shadow-2xl shadow-purple-950/35 backdrop-blur-2xl transition-all duration-300",
        isCollapsed ? "w-[88px]" : "w-64",
      ].join(" ")}
    >
      <div className={[
        "flex h-20 items-center border-b border-white/10 px-4",
        isCollapsed ? "justify-center" : "justify-between",
      ].join(" ") }>
        {!isCollapsed && (
          <div className="flex items-center gap-3 overflow-hidden">
            <img src="/images/algoagentx_icon.jpeg" alt="AlgoAgentX" className="h-10 w-10 rounded-xl object-cover ring-1 ring-white/10" />
            <div className="min-w-0">
              <div className="truncate text-xl font-bold text-white">AlgoAgentX</div>
              <div className="truncate text-sm text-purple-100/80">{brandSubtitle}</div>
            </div>
          </div>
        )}
        {isCollapsed && <img src="/images/algoagentx_icon.jpeg" alt="AlgoAgentX" className="h-10 w-10 rounded-xl object-cover ring-1 ring-white/10" />}
        <Button
          variant="ghost"
          size="sm"
          className="rounded-xl border border-white/10 bg-white/5 text-white hover:bg-white/10 hover:text-white"
          onClick={() => setIsCollapsed((v) => !v)}
        >
          {isCollapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
        </Button>
      </div>

      <nav className="flex-1 space-y-2 overflow-y-auto px-3 py-5">
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

      <div className="space-y-2 border-t border-white/10 px-3 py-4">
        {footerLinks.map((item) => (
          <SidebarItem
            key={item.href}
            icon={item.icon}
            label={item.label}
            href={item.href}
            isActive={getIsActive(item.href)}
            isCollapsed={isCollapsed}
          />
        ))}
      </div>
    </aside>
  );
}
