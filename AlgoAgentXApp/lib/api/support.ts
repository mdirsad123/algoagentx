import axiosInstance from "../axios";
import { getApiBaseUrl } from "../api-base";

const API_BASE_URL = getApiBaseUrl();

const unwrap = <T>(payload: any): T => (payload?.success ? payload.data : payload);
const toArray = <T>(value: any): T[] => {
  if (Array.isArray(value)) return value as T[];
  if (Array.isArray(value?.items)) return value.items as T[];
  if (Array.isArray(value?.data?.items)) return value.data.items as T[];
  return [];
};

export type SupportCategory = "ask_ai" | "technical" | "billing" | "broker" | "live_trading" | "backtest" | "strategy" | "other";
export type SupportPriority = "low" | "medium" | "high" | "urgent";
export type SupportStatus = "open" | "in_progress" | "waiting_user" | "resolved" | "closed";
export type SupportSenderRole = "user" | "admin" | "system";

export interface SupportAttachment {
  id: string;
  ticket_id: string;
  message_id?: string | null;
  original_filename: string;
  stored_filename?: string;
  content_type?: string | null;
  size_bytes: number;
  created_at?: string | null;
  download_url?: string | null;
}

export interface SupportMessage {
  id: string;
  ticket_id: string;
  sender_id?: string | null;
  sender_role: SupportSenderRole;
  sender_name?: string | null;
  message: string;
  created_at: string;
  attachments?: SupportAttachment[];
}

export interface SupportReply extends SupportMessage {
  user_id?: string | null;
}

export interface SupportTicket {
  id: string;
  user_id: string;
  user_email?: string | null;
  user_name?: string | null;
  subject: string;
  title?: string;
  category: SupportCategory;
  priority: SupportPriority;
  status: SupportStatus;
  message: string;
  assigned_admin_id?: string | null;
  assigned_admin_name?: string | null;
  assigned_admin_email?: string | null;
  last_reply_by?: SupportSenderRole | string | null;
  last_reply_at?: string | null;
  created_at: string;
  updated_at: string;
  closed_at?: string | null;
  attachments?: SupportAttachment[];
  messages?: SupportMessage[];
  replies?: SupportReply[];
  unread_count?: number;
  unread?: boolean;
}

export interface SupportListResponse {
  items: SupportTicket[];
  total: number;
  skip?: number;
  limit?: number;
}

export interface CreateTicketPayload {
  subject: string;
  category: SupportCategory;
  priority: SupportPriority;
  message: string;
  attachments?: File[];
}

export interface AdminSupportListParams {
  skip?: number;
  limit?: number;
  status?: SupportStatus | "";
  category?: SupportCategory | "";
  priority?: SupportPriority | "";
  search?: string;
  user_id?: string;
}

export interface AdminSupportUpdatePayload {
  status?: SupportStatus;
  priority?: SupportPriority;
  category?: SupportCategory;
  assigned_admin_id?: string | null;
}

const withFiles = (payload: { [key: string]: any; attachments?: File[] }) => {
  const files = payload.attachments || [];
  if (!files.length) {
    const { attachments: _attachments, ...json } = payload;
    return { body: json, config: undefined as any };
  }

  const formData = new FormData();
  Object.entries(payload).forEach(([key, value]) => {
    if (key === "attachments") return;
    if (value !== undefined && value !== null) formData.append(key, String(value));
  });
  files.forEach((file) => formData.append("attachments", file));
  return {
    body: formData,
    config: { headers: { "Content-Type": "multipart/form-data" } },
  };
};

const normalizeTicket = (ticket: any): SupportTicket => ({
  ...ticket,
  subject: ticket?.subject || ticket?.title || "Untitled ticket",
  title: ticket?.title || ticket?.subject || "Untitled ticket",
  category: (ticket?.category || "other").toLowerCase() as SupportCategory,
  priority: (ticket?.priority || "medium").toLowerCase() as SupportPriority,
  status: (ticket?.status || "open").toLowerCase() as SupportStatus,
  messages: Array.isArray(ticket?.messages)
    ? ticket.messages
    : Array.isArray(ticket?.replies)
      ? ticket.replies
      : undefined,
});

const normalizeList = (data: SupportListResponse | SupportTicket[] | any): SupportListResponse => {
  const items = toArray<SupportTicket>(data).map(normalizeTicket);
  if (Array.isArray(data)) return { items, total: items.length };
  return {
    items,
    total: Number(data?.total ?? items.length),
    skip: data?.skip,
    limit: data?.limit,
  };
};

export const buildAttachmentUrl = (downloadUrl?: string | null) => {
  if (!downloadUrl) return "#";
  if (/^https?:\/\//i.test(downloadUrl)) return downloadUrl;
  return `${API_BASE_URL}${downloadUrl.startsWith("/") ? downloadUrl : `/${downloadUrl}`}`;
};


const getAttachmentDownloadPath = (attachment: SupportAttachment) => {
  const url = attachment.download_url;
  if (url) {
    if (/^https?:\/\//i.test(url)) {
      try {
        const parsed = new URL(url);
        return `${parsed.pathname}${parsed.search}`;
      } catch {
        return url;
      }
    }
    return url.startsWith("/") ? url : `/${url}`;
  }

  if (!attachment.ticket_id || !attachment.id) {
    throw new Error("Attachment download URL is missing.");
  }
  return `/api/v1/support-tickets/${attachment.ticket_id}/attachments/${attachment.id}`;
};

const getFilenameFromDisposition = (disposition?: string | null) => {
  if (!disposition) return null;
  const utf8 = disposition.match(/filename\*=UTF-8''([^;]+)/i)?.[1];
  if (utf8) return decodeURIComponent(utf8.replace(/["']/g, ""));
  const plain = disposition.match(/filename="?([^";]+)"?/i)?.[1];
  return plain || null;
};

export const supportApi = {
  list: async (): Promise<SupportTicket[]> => {
    const data = unwrap<SupportListResponse | SupportTicket[]>((await axiosInstance.get("/api/v1/support-tickets")).data);
    return normalizeList(data).items;
  },

  listWithMeta: async (params?: { skip?: number; limit?: number; status?: SupportStatus }): Promise<SupportListResponse> => {
    const data = unwrap<SupportListResponse | SupportTicket[]>((await axiosInstance.get("/api/v1/support-tickets", { params })).data);
    return normalizeList(data);
  },

  get: async (ticketId: string): Promise<SupportTicket> => {
    return normalizeTicket(unwrap<SupportTicket>((await axiosInstance.get(`/api/v1/support-tickets/${ticketId}`)).data));
  },

  create: async (payload: CreateTicketPayload): Promise<SupportTicket> => {
    const { body, config } = withFiles(payload);
    return normalizeTicket(unwrap<SupportTicket>((await axiosInstance.post("/api/v1/support-tickets", body, config)).data));
  },

  reply: async (ticketId: string, message: string, attachments: File[] = []): Promise<SupportMessage> => {
    const { body, config } = withFiles({ message, attachments });
    return unwrap<SupportMessage>((await axiosInstance.post(`/api/v1/support-tickets/${ticketId}/messages`, body, config)).data);
  },

  close: async (ticketId: string): Promise<{ id: string; status: SupportStatus }> => {
    return unwrap<{ id: string; status: SupportStatus }>((await axiosInstance.patch(`/api/v1/support-tickets/${ticketId}/close`)).data);
  },



  downloadAttachment: async (attachment: SupportAttachment): Promise<void> => {
    const path = getAttachmentDownloadPath(attachment);
    const response = await axiosInstance.get(path, { responseType: "blob" });
    const blob = response.data as Blob;
    const filename =
      getFilenameFromDisposition(response.headers?.["content-disposition"]) ||
      attachment.original_filename ||
      "support-attachment";

    const objectUrl = window.URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = objectUrl;
    anchor.download = filename;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    window.URL.revokeObjectURL(objectUrl);
  },
  adminList: async (params?: AdminSupportListParams): Promise<SupportListResponse> => {
    const cleaned = Object.fromEntries(
      Object.entries(params || {}).filter(([, value]) => value !== undefined && value !== null && value !== "")
    );
    const data = unwrap<SupportListResponse | SupportTicket[]>((await axiosInstance.get("/api/v1/admin/support-tickets", { params: cleaned })).data);
    return normalizeList(data);
  },

  adminGet: async (ticketId: string): Promise<SupportTicket> => {
    return normalizeTicket(unwrap<SupportTicket>((await axiosInstance.get(`/api/v1/admin/support-tickets/${ticketId}`)).data));
  },

  adminReply: async (ticketId: string, message: string, attachments: File[] = [], status: SupportStatus = "waiting_user"): Promise<SupportMessage> => {
    const { body, config } = withFiles({ message, attachments, status });
    return unwrap<SupportMessage>((await axiosInstance.post(`/api/v1/admin/support-tickets/${ticketId}/messages`, body, config)).data);
  },

  adminUpdate: async (ticketId: string, payload: AdminSupportUpdatePayload): Promise<SupportTicket> => {
    return normalizeTicket(unwrap<SupportTicket>((await axiosInstance.patch(`/api/v1/admin/support-tickets/${ticketId}`, payload)).data));
  },

  adminAssign: async (ticketId: string, adminId?: string | null): Promise<{ id: string; assigned_admin_id: string; status: SupportStatus }> => {
    const payload = adminId ? { admin_id: adminId } : {};
    return unwrap<{ id: string; assigned_admin_id: string; status: SupportStatus }>((await axiosInstance.post(`/api/v1/admin/support-tickets/${ticketId}/assign`, payload)).data);
  },
};
