"use client";

import React, { useState, useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { Bell, User, ChevronDown, Globe, Settings, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/use-toast";
import { useNotifications } from "@/contexts/notification-context";
import { useUser } from "@/contexts/user-context";
import { NotificationResponse } from "@/types/notifications";
import { formatDistanceToNow } from "date-fns";
import { ModeToggle } from "@/components/mode-toggle";
import { withLocale } from "@/lib/route";

interface TopbarProps {
  pageTitle?: string;
}

export default function Topbar({ pageTitle }: TopbarProps) {
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
  const { user, isLoading: userLoading, clearUser } = useUser();
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [isUserDropdownOpen, setIsUserDropdownOpen] = useState(false);
  const [isLangDropdownOpen, setIsLangDropdownOpen] = useState(false);
  const [selectedLang, setSelectedLang] = useState("English");

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

  const languages = [
    "English",
    "Spanish",
    "French",
    "German"
  ];

  const handleProfileClick = () => {
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
      // Show toast for successful mark as read
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
    <header className="sticky top-0 z-50 border-b border-gray-200 bg-white/80 backdrop-blur-xl shadow-sm">
      <div className="flex items-center justify-between px-6 py-4">
        {/* Left side: Page title and breadcrumbs */}
        <div className="flex items-center gap-4">
          <h1 className="text-2xl font-bold text-gray-900 tracking-tight">
            {title}
          </h1>
          <div className="hidden md:flex items-center gap-2 text-sm text-gray-500">
            <span>Home</span>
            <span>›</span>
            <span className="text-gray-900">{title}</span>
          </div>
        </div>

        {/* Right side: Actions and user menu */}
        <div className="flex items-center gap-3">
          {/* Language Selector */}
          <div className="relative">
            <Button 
              variant="outline" 
              size="sm" 
              className="gap-2 border-gray-200 text-gray-700 hover:bg-gray-50 hover:border-gray-300"
              onClick={() => setIsLangDropdownOpen(!isLangDropdownOpen)}
            >
              <Globe className="w-4 h-4 text-gray-600" />
              <span className="hidden sm:inline text-gray-700">{selectedLang}</span>
              <ChevronDown className="w-4 h-4 text-gray-600" />
            </Button>
            
            {isLangDropdownOpen && (
              <div 
                className="absolute right-0 mt-2 w-40 bg-white border border-gray-200 rounded-lg shadow-lg z-50"
                onMouseDown={(e) => e.preventDefault()}
                onBlur={() => setIsLangDropdownOpen(false)}
              >
                {languages.map((lang) => (
                  <button
                    key={lang}
                    onClick={() => {
                      setSelectedLang(lang);
                      setIsLangDropdownOpen(false);
                    }}
                    className={`w-full text-left px-4 py-2 text-sm hover:bg-gray-50 transition-colors ${
                      selectedLang === lang ? "bg-blue-50 text-blue-600" : "text-gray-700"
                    }`}
                  >
                    {lang}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Theme Toggle */}
          <ModeToggle />

          {/* Notifications */}
          <div className="relative">
            <Button 
              variant="outline" 
              size="sm" 
              className="relative border-gray-200 text-gray-700 hover:bg-gray-50 hover:border-gray-300"
              onClick={() => setIsDropdownOpen(!isDropdownOpen)}
            >
              <Bell className="w-4 h-4 text-gray-600" />
              {unreadCount > 0 && (
                <span className="absolute -top-1 -right-1 h-5 w-5 bg-red-500 text-white text-xs rounded-full flex items-center justify-center">
                  {unreadCount > 99 ? '99+' : unreadCount}
                </span>
              )}
            </Button>

            {/* Notifications Dropdown */}
            {isDropdownOpen && (
              <div className="absolute right-0 mt-2 w-80 bg-white border border-gray-200 rounded-lg shadow-xl z-50 max-h-96 overflow-hidden">
                <div className="p-3 border-b border-gray-100 flex items-center justify-between">
                  <h3 className="font-semibold text-gray-900">Notifications</h3>
                  <button
                    onClick={() => setIsDropdownOpen(false)}
                    className="text-gray-500 hover:text-gray-700 transition-colors"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
                
                <div className="max-h-64 overflow-y-auto">
                  {isLoading ? (
                    <div className="p-4 text-center text-gray-500">
                      Loading notifications...
                    </div>
                  ) : notifications.length === 0 ? (
                    <div className="p-4 text-center text-gray-500">
                      No notifications
                    </div>
                  ) : (
                    notifications.map((notification) => (
                      <div
                        key={notification.id.toString()}
                        className={`p-3 border-b border-gray-100 hover:bg-gray-50 transition-colors ${
                          !notification.is_read ? 'bg-blue-50' : ''
                        }`}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div className="flex-1">
                            <h4 className="font-medium text-gray-900 text-sm">
                              {notification.title}
                            </h4>
                            <p className="text-xs text-gray-600 mt-1 line-clamp-2">
                              {notification.message}
                            </p>
                            <p className="text-xs text-gray-500 mt-2">
                              {formatDistanceToNow(new Date(notification.created_at), { addSuffix: true })}
                            </p>
                          </div>
                          {!notification.is_read && (
                            <button
                              onClick={() => handleMarkRead(notification.id.toString())}
                              className="text-xs text-blue-600 hover:text-blue-700 mt-1 font-medium"
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
                  <div className="p-2 border-t border-gray-100">
                    <button
                      onClick={handleMarkAllRead}
                      className="w-full text-xs text-blue-600 hover:text-blue-700 text-center py-2 font-medium"
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
              className="gap-2 text-gray-700 hover:bg-gray-50"
              onClick={() => setIsUserDropdownOpen(!isUserDropdownOpen)}
            >
              <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center">
                <User className="w-4 h-4 text-white" />
              </div>
              <span className="hidden md:inline text-gray-900 font-medium">{displayName}</span>
              <ChevronDown className="w-4 h-4 text-gray-500" />
            </Button>
            
            {/* Dropdown Menu */}
            {isUserDropdownOpen && (
              <div 
                className="absolute right-0 mt-2 w-56 bg-white border border-gray-200 rounded-lg shadow-xl z-50"
                onMouseDown={(e) => e.preventDefault()}
                onBlur={() => setIsUserDropdownOpen(false)}
              >
                <div className="p-3 border-b border-gray-100">
                  <p className="text-sm font-medium text-gray-900">{displayName}</p>
                  <p className="text-xs text-gray-600">{userEmail}</p>
                  <span className="inline-block mt-1 px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded-md font-medium">{userRole}</span>
                </div>
                <div className="p-2 space-y-1">
                  <button 
                    onClick={handleProfileClick}
                    className="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 hover:text-gray-900 rounded-md transition-colors"
                  >
                    My Profile
                  </button>
                  <button className="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 hover:text-gray-900 rounded-md transition-colors">
                    Change Password
                  </button>
                  <hr className="border-gray-100 my-1" />
                  <button 
                    onClick={handleLogout}
                    className="w-full text-left px-3 py-2 text-sm text-red-600 hover:bg-red-50 hover:text-red-700 rounded-md transition-colors"
                  >
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
}


