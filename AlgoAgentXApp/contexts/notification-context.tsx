import React, { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { notificationApi } from "@/lib/api/notifications";
import { NotificationResponse, UnreadCountResponse } from "@/types/notifications";
import { toast } from "@/components/ui/use-toast";
import { parseApiError, formatErrorMessage } from "@/lib/api/error";

interface NotificationContextType {
  notifications: NotificationResponse[];
  unreadCount: number;
  isLoading: boolean;
  error: string | null;
  fetchNotifications: () => Promise<void>;
  fetchUnreadCount: () => Promise<void>;
  markRead: (notificationIds: string[]) => Promise<void>;
  markAllRead: () => Promise<void>;
  markAsRead: (notificationId: string) => void; // Optimistic update
}

const NotificationContext = createContext<NotificationContextType | undefined>(undefined);

export const useNotifications = () => {
  const context = useContext(NotificationContext);
  if (context === undefined) {
    throw new Error('useNotifications must be used within a NotificationProvider');
  }
  return context;
};

interface NotificationProviderProps {
  children: ReactNode;
}

export const NotificationProvider: React.FC<NotificationProviderProps> = ({ children }) => {
  const [notifications, setNotifications] = useState<NotificationResponse[]>([]);
  const [unreadCount, setUnreadCount] = useState<number>(0);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUnreadCount, setLastUnreadCount] = useState<number>(0);

  const fetchNotifications = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const data = await notificationApi.getNotifications(0, 10, false);
      setNotifications(data);
    } catch (err) {
      const errorInfo = parseApiError(err);
      setError(errorInfo.message);
      console.error('Error fetching notifications:', errorInfo);
    } finally {
      setIsLoading(false);
    }
  };

  const fetchUnreadCount = async () => {
    try {
      const data = await notificationApi.getUnreadCount();
      setUnreadCount(data.unread_count);
    } catch (err) {
      console.error('Error fetching unread count:', err);
    }
  };

  const markRead = async (notificationIds: string[]) => {
    try {
      await notificationApi.markRead(notificationIds);
      // Update local state optimistically
      setNotifications(prev => 
        prev.map(notification => 
          notificationIds.includes(notification.id.toString()) 
            ? { ...notification, is_read: true }
            : notification
        )
      );
      setUnreadCount(prev => Math.max(0, prev - notificationIds.length));
    } catch (err) {
      const errorInfo = parseApiError(err);
      setError(errorInfo.message);
      console.error('Error marking notifications as read:', errorInfo);
    }
  };

  const markAllRead = async () => {
    try {
      await notificationApi.markAllRead();
      // Update local state optimistically
      setNotifications(prev => 
        prev.map(notification => ({ ...notification, is_read: true }))
      );
      setUnreadCount(0);
    } catch (err) {
      const errorInfo = parseApiError(err);
      setError(errorInfo.message);
      console.error('Error marking all notifications as read:', errorInfo);
    }
  };

  const markAsRead = (notificationId: string) => {
    // Optimistic update for immediate UI feedback
    setNotifications(prev => 
      prev.map(notification => 
        notification.id.toString() === notificationId 
          ? { ...notification, is_read: true }
          : notification
      )
    );
    setUnreadCount(prev => Math.max(0, prev - 1));
  };

  // Initial fetch
  useEffect(() => {
    fetchNotifications();
    fetchUnreadCount();
  }, []);

  // Poll for new notifications every 30 seconds
  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const data = await notificationApi.getUnreadCount();
        const newUnreadCount = data.unread_count;
        
        // Check if there are new notifications
        if (newUnreadCount > lastUnreadCount && lastUnreadCount > 0) {
          // Fetch new notifications
          const newNotifications = await notificationApi.getNotifications(0, 10, false);
          setNotifications(newNotifications);
          
          // Show toast for new notifications with professional styling
          const newCount = newUnreadCount - lastUnreadCount;
          toast({
            title: "New Notifications",
            description: `You have ${newCount} new ${newCount === 1 ? 'notification' : 'notifications'}`,
            duration: 3000,
            variant: "default"
          });
        }
        
        setUnreadCount(newUnreadCount);
        setLastUnreadCount(newUnreadCount);
      } catch (err) {
        console.error('Error polling notifications:', err);
      }
    }, 30000);

    return () => clearInterval(interval);
  }, [lastUnreadCount]);

  const value: NotificationContextType = {
    notifications,
    unreadCount,
    isLoading,
    error,
    fetchNotifications,
    fetchUnreadCount,
    markRead,
    markAllRead,
    markAsRead,
  };

  return (
    <NotificationContext.Provider value={value}>
      {children}
    </NotificationContext.Provider>
  );
};


