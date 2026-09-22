import { apiDelete, apiGet, apiPatch, apiPost } from "../axios";
import { NotificationResponse, UnreadCountResponse } from "@/types/notifications";

export const notificationApi = {
  getNotifications: async (
    offset: number = 0,
    limit: number = 20,
    unread_only: boolean = false
  ): Promise<NotificationResponse[]> => {
    return apiGet<NotificationResponse[]>("/api/v1/notifications", {
      params: { offset, limit, unread_only },
    });
  },

  getUnreadCount: async (): Promise<UnreadCountResponse> => {
    return apiGet<UnreadCountResponse>("/api/v1/notifications/unread-count");
  },

  markOneRead: async (notificationId: string): Promise<NotificationResponse> => {
    return apiPatch<NotificationResponse>(`/api/v1/notifications/${notificationId}/read`);
  },

  markRead: async (notificationIds: string[]): Promise<void> => {
    await apiPost("/api/v1/notifications/mark-read", { notification_ids: notificationIds });
  },

  markAllRead: async (): Promise<void> => {
    await apiPatch("/api/v1/notifications/read-all");
  },

  deleteNotification: async (notificationId: string): Promise<void> => {
    await apiDelete(`/api/v1/notifications/${notificationId}`);
  },
};
