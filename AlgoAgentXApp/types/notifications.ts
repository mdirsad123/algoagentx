export interface NotificationBase {
  type: string;
  title: string;
  message: string;
  severity?: "info" | "success" | "warning" | "error" | string;
  entity_type?: string | null;
  entity_id?: string | null;
  action_url?: string | null;
  metadata?: Record<string, any>;
}

export interface NotificationResponse extends NotificationBase {
  id: string;
  user_id: string;
  is_read: boolean;
  created_at: string;
  read_at?: string | null;
}

export interface UnreadCountResponse {
  unread_count: number;
}

export interface MarkReadRequest {
  notification_ids: string[];
}
