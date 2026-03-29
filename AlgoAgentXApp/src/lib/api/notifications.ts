import axiosInstance from "../axios";
import { 
  NotificationResponse, 
  UnreadCountResponse as UnreadCountResponseType,
  MarkReadRequest as MarkReadRequestType 
} from "@/types/notifications";

export interface NotificationCreate {
  type: string;
  title: string;
  message: string;
  metadata?: Record<string, any>;
}

export interface MarkReadRequest {
  notification_ids: string[];
}

export const notificationApi = {
  // Get notifications with pagination
  getNotifications: async (
    skip: number = 0,
    limit: number = 10,
    unread_only: boolean = false
  ): Promise<NotificationResponse[]> => {
    const response = await axiosInstance.get("/api/v1/notifications", {
      params: { skip, limit, unread_only }
    });
    return response.data;
  },

  // Get unread count
  getUnreadCount: async (): Promise<UnreadCountResponseType> => {
    const response = await axiosInstance.get("/api/v1/notifications/unread-count");
    return response.data;
  },

  // Mark specific notifications as read
  markRead: async (notificationIds: string[]): Promise<void> => {
    await axiosInstance.post("/api/v1/notifications/mark-read", {
      notification_ids: notificationIds
    });
  },

  // Mark all notifications as read
  markAllRead: async (): Promise<void> => {
    await axiosInstance.post("/api/v1/notifications/mark-all-read");
  }
};