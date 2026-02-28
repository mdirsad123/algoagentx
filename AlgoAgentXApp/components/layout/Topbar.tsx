"use client";

import React, { useState, useEffect, useRef } from "react";
import { usePathname, useRouter } from "next/navigation";
import { Bell, User, ChevronDown, Settings, X, Users, Database, Shield, DollarSign, TrendingUp } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/use-toast";
import { useNotifications } from "@/contexts/notification-context";
import { useUser } from "@/contexts/user-context";
import { formatDistanceToNow } from "date-fns";
import { ModeToggle } from "@/components/mode-toggle";
import { withLocale } from "@/lib/route";

interface TopbarProps {
  pageTitle?: string;
}

export default React.memo(function Topbar({ pageTitle }: TopbarProps) {
  const pathname = usePathname();
  const router = useRouter();
  const { toast } = useToast();
  const { 
    unreadCount, 
    notifications, 
    isLoading, 
    markRead, 
    markAllRead 
  } = useNotifications();
  const { user, clearUser } = useUser();
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
  const displayName = user?.displayName || user?.fullname || user?.username || user?.email || "User";
  const userEmail = user?.email || "";
  const userRole = user?.role || "User";
  const avatarLetter = displayName.charAt(0).toUpperCase();

  const handleProfileClick = () => {
    setIsUserOpen(false);
    router.push(withLocale(pathname, "/myprofile"));
  };

  const handleLogout = () => {
    // Clear user from context (this also clears localStorage)
    clearUser();
    
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

  const handleMarkRead = async (notificationId: string) => {
    try {
      await markRead([notificationId]);
      toast({
        title: "Notification marked as read",
        description: "The notification has been marked as read.",
      });
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Error",
        description: "Failed to mark notification as read. Please try again.",
      });
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await markAllRead();
      toast({
        title: "All notifications marked as read",
        description: "All notifications have been marked as read.",
      });
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Error",
        description: "Failed to mark all notifications as read. Please try again.",
      });
    }
  };

  return (
    <header className="sticky top-0 z-50 border-b border-gray-100 dark:border-dark-border bg-white/80 dark:bg-gradient-to-r dark:from-blue-900/20 dark:to-cyan-900/20 backdrop-blur-xl shadow-sm">
      <div className="flex items-center justify-between px-6 py-4">
        {/* Left side: Page title */}
        <div className="flex items-center gap-4">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-dark-text-primary tracking-tight">
            {title}
          </h1>
        </div>

        {/* Right side: Actions and user menu */}
        <div className="flex items-center gap-3">
          {/* Theme Toggle */}
          <ModeToggle />

          {/* Notifications */}
          <div className="relative">
            <Button 
              variant="outline" 
              size="sm" 
              onClick={() => setIsNotificationOpen(!isNotificationOpen)}
              className="relative border-gray-200 dark:border-dark-border text-gray-700 dark:text-dark-text-secondary hover:bg-gray-50 dark:hover:bg-dark-surface-2 hover:border-gray-300 dark:hover:border-dark-border"
            >
              <Bell className="w-4 h-4 text-gray-600 dark:text-dark-text-secondary" />
              {unreadCount > 0 && (
                <span className="absolute -top-1 -right-1 h-5 w-5 bg-red-500 text-white text-xs rounded-full flex items-center justify-center">
                  {unreadCount > 99 ? '99+' : unreadCount}
                </span>
              )}
            </Button>

            {isNotificationOpen && (
              <div className="absolute right-0 mt-2 w-80 bg-white dark:bg-gradient-to-br dark:from-blue-900/90 dark:to-cyan-900/90 border border-gray-200 dark:border-blue-500/30 rounded-lg shadow-lg z-50">
                <div className="p-3 border-b border-gray-100 dark:border-blue-500/30 flex items-center justify-between">
                  <h3 className="font-semibold text-gray-900 dark:text-white">Notifications</h3>
                  <button
                    onClick={() => setIsNotificationOpen(false)}
                    className="text-gray-500 dark:text-blue-200 hover:text-gray-700 dark:hover:text-white transition-colors"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
                
                <div className="max-h-64 overflow-y-auto">
                  {isLoading ? (
                    <div className="p-4 text-center text-gray-500 dark:text-blue-200">
                      Loading notifications...
                    </div>
                  ) : notifications.length === 0 ? (
                    <div className="p-4 text-center text-gray-500 dark:text-blue-200">
                      No notifications
                    </div>
                  ) : (
                    notifications.map((notification) => (
                      <div
                        key={notification.id.toString()}
                        className={`p-3 border-b border-gray-100 dark:border-blue-500/20 hover:bg-gray-50 dark:hover:bg-blue-500/10 transition-colors ${
                          !notification.is_read ? 'bg-blue-50 dark:bg-blue-500/15' : ''
                        }`}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div className="flex-1">
                            <h4 className="font-medium text-gray-900 dark:text-white text-sm">
                              {notification.title}
                            </h4>
                            <p className="text-xs text-gray-600 dark:text-blue-100 mt-1 line-clamp-2">
                              {notification.message}
                            </p>
                            <p className="text-xs text-gray-500 dark:text-blue-300 mt-2">
                              {formatDistanceToNow(new Date(notification.created_at), { addSuffix: true })}
                            </p>
                          </div>
                          {!notification.is_read && (
                            <button
                              onClick={() => handleMarkRead(notification.id.toString())}
                              className="text-xs text-blue-600 dark:text-blue-300 hover:text-blue-700 dark:hover:text-blue-200 mt-1 font-medium"
                            >
                              Mark read
                            </button>
                          )}
                        </div>
                      </div>
                    ))
                  )}
                </div>

                {notifications.length > 0 && (
                  <div className="p-2 border-t border-gray-100 dark:border-blue-500/30">
                    <button
                      onClick={handleMarkAllRead}
                      className="w-full text-xs text-blue-600 dark:text-blue-300 hover:text-blue-700 dark:hover:text-blue-200 text-center py-2 font-medium"
                    >
                      Mark all as read
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* User Menu */}
          <div className="relative">
            <Button 
              variant="ghost" 
              size="sm" 
              onClick={() => setIsUserOpen(!isUserOpen)}
              className="gap-3 text-gray-700 dark:text-dark-text-secondary hover:bg-gray-50 dark:hover:bg-dark-surface-2"
            >
              <div className="w-9 h-9 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-full flex items-center justify-center shadow-lg">
                <span className="text-white font-semibold text-sm">{avatarLetter}</span>
              </div>
              <div className="hidden md:block text-left">
                <div className="text-gray-900 dark:text-dark-text-primary font-medium text-sm">{displayName}</div>
                <div className="text-xs text-gray-500 dark:text-dark-text-secondary">{userRole}</div>
              </div>
              <ChevronDown className="w-4 h-4 text-gray-500 dark:text-dark-text-secondary" />
            </Button>

            {isUserOpen && (
              <div className="absolute right-0 mt-2 w-64 bg-white dark:bg-gradient-to-br dark:from-blue-900/90 dark:to-cyan-900/90 border border-gray-200 dark:border-blue-500/30 rounded-lg shadow-lg z-50">
                <div className="p-4 border-b border-gray-100 dark:border-blue-500/30">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-full flex items-center justify-center">
                      <span className="text-white font-semibold">{avatarLetter}</span>
                    </div>
                    <div>
                      <p className="font-semibold text-gray-900 dark:text-white text-sm">{displayName}</p>
                      <p className="text-xs text-gray-600 dark:text-blue-100">{userEmail}</p>
                      <span className="inline-block mt-1 px-2 py-1 bg-blue-100 dark:bg-blue-500/20 text-blue-800 dark:text-blue-200 text-xs rounded-md font-medium">{userRole}</span>
                    </div>
                  </div>
                </div>
                <div className="p-2 space-y-1">
                  <button 
                    onClick={handleProfileClick}
                    className="w-full text-left px-3 py-2 text-sm text-gray-700 dark:text-blue-100 hover:bg-gray-50 dark:hover:bg-blue-500/10 hover:text-gray-900 dark:hover:text-white rounded-md transition-colors flex items-center gap-2"
                  >
                    <User className="w-4 h-4" />
                    My Profile
                  </button>
                  {user?.role?.toLowerCase() === 'admin' && (
                    <>
                      <button 
                        onClick={() => {
                          setIsUserOpen(false);
                          router.push('/admin/users');
                        }}
                        className="w-full text-left px-3 py-2 text-sm text-gray-700 dark:text-blue-100 hover:bg-gray-50 dark:hover:bg-blue-500/10 hover:text-gray-900 dark:hover:text-white rounded-md transition-colors flex items-center gap-2"
                      >
                        <Users className="w-4 h-4" />
                        User Management
                      </button>
                      <button 
                        onClick={() => {
                          setIsUserOpen(false);
                          router.push('/admin/database');
                        }}
                        className="w-full text-left px-3 py-2 text-sm text-gray-700 dark:text-blue-100 hover:bg-gray-50 dark:hover:bg-blue-500/10 hover:text-gray-900 dark:hover:text-white rounded-md transition-colors flex items-center gap-2"
                      >
                        <Database className="w-4 h-4" />
                        Database
                      </button>
                      <button 
                        onClick={() => {
                          setIsUserOpen(false);
                          router.push('/admin/analytics');
                        }}
                        className="w-full text-left px-3 py-2 text-sm text-gray-700 dark:text-blue-100 hover:bg-gray-50 dark:hover:bg-blue-500/10 hover:text-gray-900 dark:hover:text-white rounded-md transition-colors flex items-center gap-2"
                      >
                        <TrendingUp className="w-4 h-4" />
                        Analytics
                      </button>
                      <button 
                        onClick={() => {
                          setIsUserOpen(false);
                          router.push('/admin/billing');
                        }}
                        className="w-full text-left px-3 py-2 text-sm text-gray-700 dark:text-blue-100 hover:bg-gray-50 dark:hover:bg-blue-500/10 hover:text-gray-900 dark:hover:text-white rounded-md transition-colors flex items-center gap-2"
                      >
                        <DollarSign className="w-4 h-4" />
                        Billing
                      </button>
                      <button 
                        onClick={() => {
                          setIsUserOpen(false);
                          router.push('/admin/settings');
                        }}
                        className="w-full text-left px-3 py-2 text-sm text-gray-700 dark:text-blue-100 hover:bg-gray-50 dark:hover:bg-blue-500/10 hover:text-gray-900 dark:hover:text-white rounded-md transition-colors flex items-center gap-2"
                      >
                        <Shield className="w-4 h-4" />
                        Admin Settings
                      </button>
                    </>
                  )}
                  <button className="w-full text-left px-3 py-2 text-sm text-gray-700 dark:text-blue-100 hover:bg-gray-50 dark:hover:bg-blue-500/10 hover:text-gray-900 dark:hover:text-white rounded-md transition-colors flex items-center gap-2">
                    <Settings className="w-4 h-4" />
                    Settings
                  </button>
                  <hr className="border-gray-100 dark:border-blue-500/30 my-1" />
                  <button 
                    onClick={handleLogout}
                    className="w-full text-left px-3 py-2 text-sm text-red-600 dark:text-red-300 hover:bg-red-50 dark:hover:bg-red-500/10 hover:text-red-700 dark:hover:text-red-200 rounded-md transition-colors flex items-center gap-2"
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
