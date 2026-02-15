import { UUID } from "crypto";

export interface NotificationBase {
  type: string;
  title: string;
  message: string;
  metadata?: Record<string, any>;
}

export interface NotificationCreate extends NotificationBase {
  // Additional fields for creation if needed
}

export interface NotificationUpdate {
  is_read: boolean;
}

export interface NotificationResponse extends NotificationBase {
  id: UUID;
  user_id: string;
  is_read: boolean;
  created_at: string; // ISO date string
}

export interface MarkReadRequest {
  notification_ids: UUID[];
}

export interface MarkAllReadRequest {
  // Empty interface for mark all read
}

export interface UnreadCountResponse {
  unread_count: number;
}