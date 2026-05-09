"use client";

import { clearAuthSession } from "@/lib/auth/session";
import { ChevronDown, LogOut, Menu, Settings, User as UserIcon } from "lucide-react";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import NotificationBell from "@/components/layout/NotificationBell";

interface TopbarProps {
  pageTitle?: string;
  onMenuClick?: () => void;
  showMenuButton?: boolean;
}

function getCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

export default function Topbar({ pageTitle, onMenuClick, showMenuButton = false }: TopbarProps) {
  const pathname = usePathname();
  const router = useRouter();
  const [isUserOpen, setIsUserOpen] = useState(false);
  const [profile, setProfile] = useState({
    name: "User",
    email: "",
    role: pathname.startsWith("/admin") ? "admin" : "user",
    authProvider: "local",
    avatarUrl: "",
  });
  const userRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const syncProfile = () => {
      const storedUser = typeof window !== "undefined" ? localStorage.getItem("currentUser") : null;
      let nextProfile: any = null;
      if (storedUser) {
        try {
          nextProfile = JSON.parse(storedUser);
        } catch {}
      }

      const email = nextProfile?.email || getCookie("loggedinuseremail") || getCookie("loggedinusername") || "";
      const name =
        nextProfile?.full_name ||
        nextProfile?.fullname ||
        getCookie("loggedinuserfullname") ||
        email?.split("@")[0] ||
        (pathname.startsWith("/admin") ? "Admin User" : "User");
      const role = String(nextProfile?.role || getCookie("loggedinuserroleid") || getCookie("loggedinuserrole") || (pathname.startsWith("/admin") ? "admin" : "user")).toLowerCase();
      const authProvider = String(nextProfile?.auth_provider || "local").toLowerCase();
      const avatarUrl = nextProfile?.avatar_url || "";
      setProfile({ name, email, role, authProvider, avatarUrl });
    };

    syncProfile();
    window.addEventListener("storage", syncProfile);
    const handleClickOutside = (event: MouseEvent) => {
      if (userRef.current && !userRef.current.contains(event.target as Node)) {
        setIsUserOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      window.removeEventListener("storage", syncProfile);
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [pathname]);

  const title = useMemo(() => {
    if (pageTitle) return pageTitle;
    const segment = pathname.split("/").filter(Boolean).pop() || "dashboard";
    return segment
      .split("-")
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(" ");
  }, [pageTitle, pathname]);

  const isAdmin = pathname.startsWith("/admin") || profile.role === "admin" || profile.role === "1";
  const profileHref = isAdmin ? "/admin/profile" : "/profile";
  const settingsHref = isAdmin ? "/admin/settings" : "/settings";
  const avatar = profile.name.charAt(0).toUpperCase();

  const handleLogout = () => {
    clearAuthSession();
    router.push("/auth/login");
  };
  return (
    <header className="sticky top-0 z-30 border-b border-white/10 bg-[#1f123f]/80 backdrop-blur-xl">
      <div className="flex min-w-0 items-center justify-between gap-2 px-3 py-2 sm:gap-3 sm:px-5 sm:py-3 lg:px-6">
        {showMenuButton && (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            aria-label="Open sidebar"
            onClick={onMenuClick}
            className="shrink-0 rounded-xl border border-white/10 bg-white/5 px-2 text-white hover:bg-white/10 hover:text-white lg:hidden"
          >
            <Menu className="h-5 w-5" />
          </Button>
        )}
        <div className="min-w-0 flex-1">
          <h1 className="max-w-[44vw] truncate text-base font-bold leading-tight text-white min-[390px]:max-w-[52vw] sm:max-w-[62vw] sm:text-xl lg:max-w-[70vw] lg:text-2xl xl:max-w-none">{title}</h1>
        </div>

        <div className="flex shrink-0 items-center gap-1.5 sm:gap-3">
          <NotificationBell />

          <div className="relative" ref={userRef}>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsUserOpen((v) => !v)}
              className="h-auto gap-1 rounded-2xl border border-white/10 bg-white/5 px-1.5 py-1.5 text-white hover:bg-white/10 hover:text-white sm:gap-3 sm:px-3 sm:py-2"
            >
              <div className="flex h-9 w-9 overflow-hidden items-center justify-center rounded-full bg-gradient-to-br from-fuchsia-500 to-blue-500 text-sm font-semibold text-white shadow-lg sm:h-10 sm:w-10 sm:text-base">
                {profile.avatarUrl ? <img src={profile.avatarUrl} alt="Profile" className="h-full w-full object-cover" /> : avatar}
              </div>
              <div className="hidden text-left md:block">
                <div className="max-w-[160px] truncate text-sm font-semibold text-white">{profile.name}</div>
                <div className="text-xs uppercase tracking-wide text-purple-100/70">{isAdmin ? "Admin" : "User"}</div>
              </div>
              <ChevronDown className="hidden h-4 w-4 text-purple-100/80 sm:block" />
            </Button>

            {isUserOpen && (
              <div className="absolute right-0 mt-3 w-[min(18rem,calc(100vw-92px))] overflow-hidden rounded-2xl border border-white/10 bg-[#08031f]/95 shadow-2xl shadow-purple-950/50 backdrop-blur-2xl sm:w-72">
                <div className="border-b border-white/10 p-4">
                  <div className="text-sm font-semibold text-white">{profile.name}</div>
                  <div className="truncate text-xs text-purple-100/70">{profile.email || "No email available"}</div>
                  <div className="mt-2 inline-flex rounded-full border border-white/10 bg-white/10 px-2 py-1 text-[11px] font-semibold text-purple-100">
                    {profile.authProvider.includes("google") ? "Google Account" : "Local Account"}
                  </div>
                </div>
                <div className="p-2">
                  <button onClick={() => { setIsUserOpen(false); router.push(profileHref); }} className="flex w-full items-center gap-3 rounded-xl px-3 py-2 text-sm text-white hover:bg-white/10">
                    <UserIcon className="h-4 w-4" /> Profile
                  </button>
                  <button onClick={() => { setIsUserOpen(false); router.push(settingsHref); }} className="flex w-full items-center gap-3 rounded-xl px-3 py-2 text-sm text-white hover:bg-white/10">
                    <Settings className="h-4 w-4" /> Settings
                  </button>
                  <button onClick={handleLogout} className="flex w-full items-center gap-3 rounded-xl px-3 py-2 text-sm text-rose-300 hover:bg-rose-500/10">
                    <LogOut className="h-4 w-4" /> Sign out
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
