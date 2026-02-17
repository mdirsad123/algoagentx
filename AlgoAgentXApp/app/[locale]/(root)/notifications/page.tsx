'use client';

import React, { useState } from 'react';
import { Eye, Trash2, CheckSquare } from 'lucide-react';
import { useNotifications } from '@/contexts/notification-context';
import { NotificationResponse } from '@/types/notifications';
import Toast from "@/components/shared/toast";
import { MdMessage } from "react-icons/md";
import { PageHeader } from "@/components/ui/page-header";
import EmptyState from "@/components/shared/empty-state";

export default function FullNotificationsPage() {
  const [activeTab, setActiveTab] = useState('All');
  const [selectedNotification, setSelectedNotification] = useState<NotificationResponse | null>(null);
  const [isUpdating, setIsUpdating] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState<string | null>(null);
  const [isMarkingAll, setIsMarkingAll] = useState(false);

  // Use notifications from context
  const { notifications, unreadCount, markRead, markAllRead, fetchNotifications } = useNotifications();

  // Calculate counts from context notifications
  const totalCount = notifications.length;
  const readCount = notifications.filter((n) => n.is_read).length;

  // Tabs array with badge counts
  const tabs = [
    { label: `All (${totalCount})`, value: 'All' },
    { label: `Unread (${unreadCount})`, value: 'Unread' },
    { label: `Read (${readCount})`, value: 'Read' }
  ];

  // Filter notifications based on active tab
  const filteredNotifications = notifications.filter((n) => {
    if (activeTab === 'All') return true;
    if (activeTab === 'Unread') return !n.is_read;
    if (activeTab === 'Read') return n.is_read;
    return n.type === activeTab;
  });

  // ✅ New function to mark all as read using context
  const handleMarkAllAsRead = async () => {
    setIsMarkingAll(true);
    try {
      await markAllRead();
      await fetchNotifications();
      Toast.fire({
        icon: "success",
        title: "All notifications marked as read!",
      });
    } catch (err) {
      console.error('Error marking all read:', err);
      Toast.fire({
        icon: "error",
        title: "Failed to mark all as read",
      });
    } finally {
      setIsMarkingAll(false);
    }
  };

  // Fixed handleViewClick function using context
  const handleViewClick = async (notification: NotificationResponse) => {
    setSelectedNotification(notification);

    if (!notification.is_read) {
      setIsUpdating(notification.id.toString());
      
      try {
        await markRead([notification.id]);
        await fetchNotifications();
        
        Toast.fire({
          icon: "success",
          title: "Notification marked as read!",
        });
      } catch (error) {
        console.error('Error marking notification as read:', error);
        
        Toast.fire({
          icon: "error",
          title: "Failed to mark notification as read",
          text: error instanceof Error ? error.message : 'Unknown error'
        });
      } finally {
        setIsUpdating(null);
      }
    }
  };

  // Note: Delete functionality is not available in the context
  // If needed, this would require adding a delete method to the notification context
  const handleDeleteClick = async (notification: NotificationResponse) => {
    // Delete functionality not implemented in context
    // This would need to be added to the notification context if required
    Toast.fire({
      icon: "warning",
      title: "Delete functionality not available",
      text: "Please contact support if you need to delete notifications"
    });
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-3 sm:p-6 transition-colors duration-300">
      <PageHeader 
        title="Notifications"
        subtitle="Manage your notifications and alerts"
      />

      {/* Tabs */}
      <div className="border-b mb-4 overflow-x-auto">
  <div className="flex items-center">
    {/* Tabs */}
    <nav className="flex min-w-max sm:min-w-0">
      {tabs.map((tab) => (
        <button
          key={tab.value}
          onClick={() => setActiveTab(tab.value)}
          className={`px-4 sm:px-6 py-2 sm:py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
            activeTab === tab.value
              ? "border-amber-500 text-amber-600 bg-amber-50"
              : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
          }`}
        >
          {tab.label}
        </button>
      ))}
    </nav>

    {/* Mark All as Read button on the right */}
    <div className="ml-auto">
      <button
        onClick={handleMarkAllAsRead}
        disabled={isMarkingAll || unreadCount === 0}
        className={`flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-md shadow-sm transition-colors
          ${unreadCount === 0
            ? 'bg-gray-200 text-gray-400 cursor-not-allowed'
            : 'bg-blue-500 text-white hover:bg-blue-600'
          }`}
      >
        {isMarkingAll ? (
          <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
        ) : (
          <CheckSquare className="w-4 h-4" />
        )}
        {isMarkingAll ? 'Marking...' : 'Mark All as Read'}
      </button>
    </div>
  </div>
</div>


  {/* Notifications List */}
  <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border dark:border-gray-700 divide-y divide-gray-100 dark:divide-gray-700">
    {filteredNotifications.length === 0 ? (
      <EmptyState
        title="No Notifications"
        description="You don't have any notifications at the moment"
        icon={<Eye className="w-12 h-12 text-gray-400" />}
        actionLabel="Refresh"
        onAction={fetchNotifications}
      />
    ) : (
      filteredNotifications.map((notification: NotificationResponse) => {
        return (
          <div
            key={notification.id}
            className="p-4 sm:p-6 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
          >
            <div className="flex items-start justify-between">
              <div className="flex items-start space-x-3 sm:space-x-4">
                <div className="w-10 h-10 sm:w-12 sm:h-12 rounded-full bg-gray-100 dark:bg-gray-700 flex items-center justify-center flex-shrink-0">
                  <MdMessage className="text-lg sm:text-xl text-blue-500" />
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex flex-wrap items-center gap-2 mb-2">
                  <h3
                      className={`font-semibold text-sm sm:text-base ${
                        notification.is_read
                        ? "text-gray-600 dark:text-gray-400"
                        : "text-gray-900 dark:text-gray-100"
                      }`}
                    >
                      {notification.title || "Untitled"}
                    </h3>
                    {notification.type === "Action" && (
                      <span className="px-2 py-0.5 text-xs font-medium rounded-full border bg-red-100 text-red-600 border-red-200">
                        Action Required
                      </span>
                    )}
                    {!notification.is_read && (
                      <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-blue-100 text-blue-600">
                        New
                      </span>
                    )}
                  </div>

                  {/* Render HTML-rich message */}
                  <div
                    className={`mb-3 text-sm break-words ${
                      notification.is_read ? "text-gray-500 dark:text-gray-400" : "text-gray-600 dark:text-gray-300"
                    }`}
                    dangerouslySetInnerHTML={{ __html: notification.message }}
                  />

                  <div className="flex flex-wrap items-center gap-3 text-xs sm:text-sm text-gray-500 dark:text-gray-400">
                    <span>{new Date(notification.created_at).toLocaleString()}</span>
                    {notification.is_read && (
                      <span className="text-green-500">✓ Read</span>
                    )}
                    <div
                      className={`w-2.5 h-2.5 rounded-full ${
                        notification.is_read ? "bg-gray-300" : "bg-blue-500"
                      }`}
                    />
                  </div>
                </div>
              </div>

              {/* Actions */}
              <div className="flex items-center space-x-1 sm:space-x-2 ml-2">
                {/* View */}
                  <button
                  className={`p-1.5 sm:p-2 rounded transition-colors ${
                    isUpdating === notification.id.toString()
                      ? "text-blue-500 cursor-not-allowed"
                      : "text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300"
                  }`}
                  onClick={() => handleViewClick(notification)}
                  disabled={isUpdating === notification.id.toString()}
                >
                  {isUpdating === notification.id.toString() ? (
                    <div className="w-4 h-4 sm:w-5 sm:h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
                  ) : (
                    <Eye className="w-4 h-4 sm:w-5 sm:h-5" />
                  )}
                </button>

                {/* Delete */}
                <button
                  className={`p-1.5 sm:p-2 rounded transition-colors ${
                    isDeleting === notification.id.toString()
                      ? "text-red-500 cursor-not-allowed"
                      : "text-gray-400 dark:text-gray-500 hover:text-red-500 dark:hover:text-red-400"
                  }`}
                  onClick={() => handleDeleteClick(notification)}
                  disabled={isDeleting === notification.id.toString()}
                >
                  {isDeleting === notification.id.toString() ? (
                    <div className="w-4 h-4 sm:w-5 sm:h-5 border-2 border-red-500 border-t-transparent rounded-full animate-spin"></div>
                  ) : (
                    <Trash2 className="w-4 h-4 sm:w-5 sm:h-5" />
                  )}
                </button>
              </div>
            </div>
          </div>
        );
      })
    )}
  </div>

  {/* Popup Modal */}
  {selectedNotification && (
    <div className="fixed inset-0 flex items-center justify-center bg-black bg-opacity-50 dark:bg-opacity-70 z-50 p-3">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg w-full max-w-lg max-h-[85vh] overflow-y-auto p-4 sm:p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg sm:text-xl font-bold break-words dark:text-gray-100">
            {selectedNotification.title}
          </h2>
          {selectedNotification.is_read ? (
            <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-green-100 text-green-600">
              Read
            </span>
          ) : (
            <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-blue-100 text-blue-600">
              New
            </span>
          )}
        </div>

        <div
          className="text-sm sm:text-base text-gray-700 dark:text-gray-300 mb-4 max-h-60 overflow-y-auto break-words"
          dangerouslySetInnerHTML={{
            __html: selectedNotification.message,
          }}
        />

        <div className="text-xs sm:text-sm text-gray-500 dark:text-gray-400 mb-4">
          Created At:{" "}
          {new Date(selectedNotification.created_at).toLocaleString()}
        </div>

        <div className="flex justify-end">
          <button
            onClick={() => setSelectedNotification(null)}
            className="px-3 sm:px-4 py-2 bg-gray-200 dark:bg-gray-700 rounded hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors text-sm sm:text-base dark:text-gray-100"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )}
</div>

  );
}