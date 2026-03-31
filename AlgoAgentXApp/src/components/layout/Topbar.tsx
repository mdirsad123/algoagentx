"use client";

import { Bell, ChevronDown, LogOut, Settings, User as UserIcon } from "lucide-react";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import { Button } from "@/components/ui/button";

interface TopbarProps {
  pageTitle?: string;
}

function getCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

export default function Topbar({ pageTitle }: TopbarProps) {
  const pathname = usePathname();
  const router = useRouter();
  const [isUserOpen, setIsUserOpen] = useState(false);
  const [profile, setProfile] = useState({
    name: "User",
    email: "",
    role: pathname.startsWith("/admin") ? "admin" : "user",
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
      setProfile({ name, email, role });
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
    [
      "accessToken",
      "loggedinuserid",
      "loggedinusername",
      "loggedinuserfullname",
      "loggedinuserroleid",
      "loggedinuseremail",
      "loggedinuserrole",
    ].forEach((cookieName) => {
      document.cookie = `${cookieName}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/; samesite=strict`;
    });
    localStorage.removeItem("access_token");
    localStorage.removeItem("currentUser");
    router.push("/auth/login");
  };

  return (
    <header className="sticky top-0 z-30 border-b border-white/10 bg-[#1f123f]/80 backdrop-blur-xl">
      <div className="flex items-center justify-between px-6 py-5">
        <div>
          <h1 className="text-3xl font-bold text-white">{title}</h1>
          <p className="mt-1 text-sm text-purple-100/80">
            {isAdmin ? "System management and business controls" : "Manage your trading workspace"}
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" className="relative rounded-2xl border border-white/10 bg-white/5 text-white hover:bg-white/10 hover:text-white">
            <Bell className="h-5 w-5" />
            <span className="absolute right-2 top-2 h-2.5 w-2.5 rounded-full bg-fuchsia-400" />
          </Button>

          <div className="relative" ref={userRef}>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsUserOpen((v) => !v)}
              className="h-auto gap-3 rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-white hover:bg-white/10 hover:text-white"
            >
              <div className="flex h-11 w-11 items-center justify-center rounded-full bg-gradient-to-br from-fuchsia-500 to-blue-500 font-semibold text-white shadow-lg">
                {avatar}
              </div>
              <div className="hidden text-left md:block">
                <div className="max-w-[160px] truncate text-sm font-semibold text-white">{profile.name}</div>
                <div className="text-xs uppercase tracking-wide text-purple-100/70">{isAdmin ? "Admin" : "User"}</div>
              </div>
              <ChevronDown className="h-4 w-4 text-purple-100/80" />
            </Button>

            {isUserOpen && (
              <div className="absolute right-0 mt-3 w-72 overflow-hidden rounded-2xl border border-white/10 bg-[#08031f]/95 shadow-2xl shadow-purple-950/50 backdrop-blur-2xl">
                <div className="border-b border-white/10 p-4">
                  <div className="text-sm font-semibold text-white">{profile.name}</div>
                  <div className="truncate text-xs text-purple-100/70">{profile.email || "No email available"}</div>
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
