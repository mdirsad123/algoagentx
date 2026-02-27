"use client";
import React, { useState, useEffect } from "react";
import { Bell, ChevronDown, Globe, X } from "lucide-react";
import Cookies from "js-cookie";
import Link from "next/link";
import { useRouter, usePathname } from "next/navigation";
import axiosInstance from "@/lib/axios";
import { useNotifications } from "@/contexts/notification-context";
import { useUser } from "@/contexts/user-context";
import { NotificationResponse } from "@/types/notifications";
import { ThemeToggle } from "@/components/theme-toggle";
import { withLocale } from "@/lib/route";

export default function MinimalHeader() {
  const [showLangDropdown, setShowLangDropdown] = useState(false);
  const [showUserDropdown, setShowUserDropdown] = useState(false);
  const [showNotificationDropdown, setShowNotificationDropdown] = useState(false);
  const [selectedLang, setSelectedLang] = useState("Eng (US)");

  // Use notifications from context
  const { unreadCount, notifications, markAllRead, fetchNotifications } = useNotifications();
  
  // Use user from context
  const { user, isLoading: userLoading, clearUser } = useUser();
  const router = useRouter();
  const pathname = usePathname();

  // Calculate display values from user context
  const displayName = user?.displayName || user?.fullname || user?.username || user?.email || "User";
  const userEmail = user?.email || "";
  const userRole = user?.role || "User";
  const avatarLetter = displayName.charAt(0).toUpperCase();

  const languages = [
    "Eng (US)",
    "Eng (UK)", 
    "Spanish",
    "French",
    "German"
  ];

  return (
    <div className="w-full bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700">
      <div className="flex items-center justify-end h-14 px-6 gap-6">
        
        {/* Language Selector */}
        <div className="relative" onBlur={() => setShowLangDropdown(false)}>
          <button
            onClick={() => setShowLangDropdown(!showLangDropdown)}
            className="flex items-center gap-2 text-sm text-gray-700 hover:text-gray-900 transition-colors"
          >
            <Globe className="w-4 h-4" />
            <span>{selectedLang}</span>
            <ChevronDown className="w-4 h-4" />
          </button>
          
          {showLangDropdown && (
            <div 
              className="absolute right-0 mt-2 w-40 bg-white border border-gray-200 rounded-lg shadow-lg z-50"
              onMouseDown={(e) => e.preventDefault()}
            >
              {languages.map((lang) => (
                <button
                  key={lang}
                  onClick={() => {
                    setSelectedLang(lang);
                    setShowLangDropdown(false);
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
        <ThemeToggle />

        {/* Notification Bell */}
        <div className="relative" onBlur={() => setShowNotificationDropdown(false)}>
          <button
            onClick={() => setShowNotificationDropdown(!showNotificationDropdown)}
            className="relative p-2 hover:bg-gray-50 rounded-full transition-colors"
          >
            <Bell className="w-5 h-5 text-gray-600" />
            {unreadCount > 0 && (
              <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full"></span>
            )}
          </button>

          {showNotificationDropdown && (
            <div 
              className="absolute right-0 mt-2 w-80 bg-white border border-gray-200 rounded-lg shadow-lg z-50 max-h-96 overflow-hidden"
              onMouseDown={(e) => e.preventDefault()}
            >
              <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
                <h3 className="text-sm font-semibold text-gray-900">Notifications</h3>
                <div className="flex items-center gap-2">
                  {unreadCount > 0 && (
                    <button
                      onClick={async (e) => {
                        e.stopPropagation();
                        await markAllRead();
                        await fetchNotifications();
                      }}
                      className="text-xs text-blue-600 hover:text-blue-800 transition-colors"
                    >
                      Mark all as read
                    </button>
                  )}
                  <button
                    onClick={() => setShowNotificationDropdown(false)}
                    className="p-1 hover:bg-gray-100 rounded-full transition-colors"
                  >
                    <X className="w-4 h-4 text-gray-500" />
                  </button>
                </div>
              </div>
              
              <div className="max-h-64 overflow-y-auto">
                {notifications.length === 0 ? (
                  <div className="px-4 py-6 text-center text-gray-500 text-sm">
                    No notifications
                  </div>
                ) : (
                  notifications.slice(0, 5).map((notification: NotificationResponse) => (
                    <div
                      key={notification.id}
                      className={`px-4 py-3 border-b border-gray-50 last:border-b-0 hover:bg-gray-50 transition-colors ${
                        !notification.is_read ? 'bg-blue-50' : ''
                      }`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex-1 min-w-0">
                          <h4 className="text-sm font-medium text-gray-900 truncate">
                            {notification.title}
                          </h4>
                          <p className="text-xs text-gray-600 mt-1 line-clamp-2">
                            {notification.message}
                          </p>
                        </div>
                        {!notification.is_read && (
                          <div className="w-2 h-2 bg-blue-500 rounded-full mt-2 flex-shrink-0"></div>
                        )}
                      </div>
                      <p className="text-xs text-gray-500 mt-2">
                        {new Date(notification.created_at).toLocaleString()}
                      </p>
                    </div>
                  ))
                )}
              </div>

              {notifications.length > 5 && (
                <div className="px-4 py-2 border-t border-gray-100 bg-gray-50">
              <Link
                href={withLocale(pathname, "/notifications")}
                onClick={() => setShowNotificationDropdown(false)}
                className="text-xs text-blue-600 hover:text-blue-800 transition-colors block text-center"
              >
                View all notifications
              </Link>
                </div>
              )}
            </div>
          )}
        </div>

        {/* User Profile */}
        <div className="relative" onBlur={() => setShowUserDropdown(false)}>
          <button
            onClick={() => setShowUserDropdown(!showUserDropdown)}
            className="flex items-center gap-3 hover:bg-gray-50 rounded-lg px-2 py-1 transition-colors"
          >
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-400 to-blue-600 flex items-center justify-center">
              <span className="text-white font-bold text-sm">{avatarLetter}</span>
            </div>
            <div className="flex flex-col items-start">
              <span className="text-sm font-medium text-gray-900">{displayName}</span>
              <span className="text-xs text-gray-500">{userRole}</span>
            </div>
            <ChevronDown className="w-4 h-4 text-gray-600" />
          </button>

          {showUserDropdown && (
            <div 
              className="absolute right-0 mt-2 w-48 bg-white border border-gray-200 rounded-lg shadow-lg z-50"
              onMouseDown={(e) => e.preventDefault()}
            >
              <div className="px-4 py-3 border-b border-gray-100">
                <p className="text-sm font-medium text-gray-900">{displayName}</p>
                <p className="text-xs text-gray-500">{userEmail}</p>
              </div>
              <Link
                href={withLocale(pathname, "/myprofile")}
                onClick={() => setShowUserDropdown(false)}
                className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 transition-colors block"
              >
                My Profile
              </Link>
              <Link
                href={withLocale(pathname, "/changepassword")}
                onClick={() => setShowUserDropdown(false)}
                className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 transition-colors block"
              >
                Change Password
              </Link>
              <div className="border-t border-gray-100">
                <button 
                  onClick={handleLogout}
                  className="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-red-50 transition-colors"
                >
                  Logout
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );

  function handleLogout() {
    // Clear user from context (this also clears localStorage)
    clearUser();
    
    // Remove all authentication cookies
    Cookies.remove("accessToken");
    Cookies.remove("loggedinuserid");
    Cookies.remove("loggedinusername");
    Cookies.remove("loggedinuserfullname");
    Cookies.remove("loggedinuserroleid");
    Cookies.remove("loggedinuseremail");
    Cookies.remove("loggedinuserrole");

    // Remove localStorage token if present (correct key name)
    if (typeof window !== 'undefined') {
      localStorage.removeItem('access_token');
    }

    // Use router for proper navigation with locale support
    router.push('/auth/login');
  }
}
