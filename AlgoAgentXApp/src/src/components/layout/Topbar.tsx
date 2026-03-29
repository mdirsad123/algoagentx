"use client";

import React, { useState, useEffect, useRef } from "react";
import { usePathname, useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";

// Import icons directly from lucide-react
import { 
  Bell, 
  User, 
  ChevronDown, 
  Settings, 
  X, 
  Users, 
  Database, 
  Shield, 
  DollarSign, 
  TrendingUp 
} from "lucide-react";

interface TopbarProps {
  pageTitle?: string;
}

export default React.memo(function Topbar({ pageTitle }: TopbarProps) {
  const pathname = usePathname();
  const router = useRouter();
  const [isNotificationOpen, setIsNotificationOpen] = useState(false);
  const [isUserOpen, setIsUserOpen] = useState(false);
  
  // Refs for dropdowns to handle outside clicks
  const notificationRef = useRef<HTMLDivElement>(null);
  const userRef = useRef<HTMLDivElement>(null);

  // Handle outside clicks to close dropdowns
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (notificationRef.current && !notificationRef.current.contains(event.target as Node)) {
        setIsNotificationOpen(false);
      }
      if (userRef.current && !userRef.current.contains(event.target as Node)) {
        setIsUserOpen(false);
      }
    }

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Extract page title from pathname if not provided
  const getPageTitle = () => {
    if (pageTitle) return pageTitle;
    
    const pathSegments = pathname.split('/').filter(Boolean);
    const lastSegment = pathSegments[pathSegments.length - 1];
    
    if (!lastSegment) return "Dashboard";
    
    return lastSegment
      .split('-')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  const title = getPageTitle();

  // Calculate display values from user context
  const displayName = "User";
  const userEmail = "";
  const userRole = "User";
  const avatarLetter = displayName.charAt(0).toUpperCase();

  const handleProfileClick = () => {
    setIsUserOpen(false);
    router.push("/profile");
  };

  const handleLogout = () => {
    // Remove all authentication cookies
    document.cookie = 'accessToken=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/; samesite=strict';
    document.cookie = 'loggedinuserid=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/; samesite=strict';
    document.cookie = 'loggedinusername=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/; samesite=strict';
    document.cookie = 'loggedinuserfullname=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/; samesite=strict';
    document.cookie = 'loggedinuserroleid=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/; samesite=strict';
    document.cookie = 'loggedinuseremail=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/; samesite=strict';
    document.cookie = 'loggedinuserrole=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/; samesite=strict';

    // Remove localStorage token
    localStorage.removeItem('access_token');
    localStorage.removeItem('currentUser');

    // Navigate to login
    router.push('/auth/login');
  };

  return (
    <header className="sticky top-0 z-50 border-b border-border/60 bg-card/40 backdrop-blur-xl shadow-lg shadow-purple-500/20">
      <div className="flex items-center justify-between px-6 py-4">
        {/* Left side: Page title */}
        <div className="flex items-center gap-6">
          <h1 className="text-2xl font-bold text-foreground tracking-tight">
            {title}
          </h1>
        </div>

        {/* Right side: Actions and user menu */}
        <div className="flex items-center gap-4">
          {/* Notifications */}
          <div className="relative">
            <Button 
              variant="outline" 
              size="sm" 
              onClick={() => setIsNotificationOpen(!isNotificationOpen)}
              className="relative border-border/60 text-foreground hover:bg-card/60 hover:border-border/80 transition-all duration-200"
            >
              <Bell className="w-5 h-5 text-foreground" />
              <span className="absolute -top-1 -right-1 h-6 w-6 bg-red-500 text-white text-xs rounded-full flex items-center justify-center font-medium shadow-lg">
                0
              </span>
            </Button>

            {isNotificationOpen && (
              <div className="absolute right-0 mt-2 w-80 bg-card/80 backdrop-blur-xl border border-border/60 rounded-lg shadow-xl z-50">
                <div className="p-3 border-b border-border/60 flex items-center justify-between">
                  <h3 className="font-semibold text-foreground">Notifications</h3>
                  <button
                    onClick={() => setIsNotificationOpen(false)}
                    className="text-muted-foreground hover:text-foreground transition-colors"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
                
                <div className="max-h-64 overflow-y-auto">
                  <div className="p-4 text-center text-muted-foreground">
                    No notifications
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* User Menu */}
          <div className="relative">
            <Button 
              variant="ghost" 
              size="sm" 
              onClick={() => setIsUserOpen(!isUserOpen)}
              className="gap-3 text-foreground hover:bg-card/60 transition-all duration-200"
            >
              <div className="w-10 h-10 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-full flex items-center justify-center shadow-lg border-2 border-white/20">
                <span className="text-white font-semibold text-sm">{avatarLetter}</span>
              </div>
              <div className="hidden md:block text-left">
                <div className="text-foreground font-medium text-sm">{displayName}</div>
                <div className="text-xs text-muted-foreground">{userRole}</div>
              </div>
              <ChevronDown className="w-4 h-4 text-muted-foreground" />
            </Button>

            {isUserOpen && (
              <div className="absolute right-0 mt-2 w-64 bg-card/80 backdrop-blur-xl border border-border/60 rounded-lg shadow-xl z-50">
                <div className="p-4 border-b border-border/60">
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-full flex items-center justify-center shadow-lg border-2 border-white/20">
                      <span className="text-white font-semibold text-base">{avatarLetter}</span>
                    </div>
                    <div>
                      <p className="font-semibold text-foreground text-sm">{displayName}</p>
                      <p className="text-xs text-muted-foreground">{userEmail}</p>
                      <span className="inline-block mt-1 px-2 py-1 bg-primary/10 text-primary text-xs rounded-md font-medium">{userRole}</span>
                    </div>
                  </div>
                </div>
                <div className="p-2 space-y-1">
                  <button 
                    onClick={handleProfileClick}
                    className="w-full text-left px-3 py-2 text-sm text-foreground hover:bg-primary/10 hover:text-foreground rounded-md transition-colors flex items-center gap-2"
                  >
                    <User className="w-4 h-4" />
                    My Profile
                  </button>
                  <button className="w-full text-left px-3 py-2 text-sm text-foreground hover:bg-primary/10 hover:text-foreground rounded-md transition-colors flex items-center gap-2">
                    <Settings className="w-4 h-4" />
                    Settings
                  </button>
                  <hr className="border-border/60 my-1" />
                  <button 
                    onClick={handleLogout}
                    className="w-full text-left px-3 py-2 text-sm text-destructive hover:bg-destructive/10 hover:text-destructive rounded-md transition-colors flex items-center gap-2"
                  >
                    <span className="w-4 h-4" />
                    Sign Out
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
});