import { apiDelete, apiGet, apiPatch, apiPost } from "../axios";
import apiClient from "../axios";
import type { AlertEvent, AlertHealth, AlertPayload, PriceAlert, TelegramChannel, WhatsAppChannel } from "@/types/alerts";

export const alertsApi = {
  list: (status?: string) => apiGet<PriceAlert[]>("/api/v1/alerts", { params: status ? { status } : undefined }),
  get: (id: string) => apiGet<PriceAlert>(`/api/v1/alerts/${id}`),
  create: (payload: AlertPayload) => apiPost<PriceAlert>("/api/v1/alerts", payload),
  update: (id: string, payload: Partial<AlertPayload>) => apiPatch<PriceAlert>(`/api/v1/alerts/${id}`, payload),
  remove: (id: string) => apiDelete(`/api/v1/alerts/${id}`),
  enable: (id: string) => apiPost<PriceAlert>(`/api/v1/alerts/${id}/enable`),
  disable: (id: string) => apiPost<PriceAlert>(`/api/v1/alerts/${id}/disable`),
  history: (limit = 200) => apiGet<AlertEvent[]>("/api/v1/alerts/history", { params: { limit } }),
  historyDetail: (id: string) => apiGet<AlertEvent>(`/api/v1/alerts/history/${id}`),
  health: () => apiGet<AlertHealth>("/api/v1/alerts/health"),
  telegramChannel: () => apiGet<TelegramChannel>("/api/v1/alerts/telegram-channel"),
  saveTelegramChannel: async (chatId: string) => {
    const response = await apiClient.put("/api/v1/alerts/telegram-channel", { chat_id: chatId, enabled: true });
    return response.data?.data as TelegramChannel;
  },
  testTelegram: (chatId?: string) => apiPost<{ status: string; telegram_api_accepted: boolean; message_id?: string }>("/api/v1/alerts/test-notification", { chat_id: chatId || null }),
  whatsappChannel: () => apiGet<WhatsAppChannel>("/api/v1/alerts/whatsapp-channel"),
  saveWhatsAppChannel: async (phoneNumber: string) => {
    const response = await apiClient.put("/api/v1/alerts/whatsapp-channel", { phone_number: phoneNumber, enabled: true });
    return response.data?.data as WhatsAppChannel;
  },
  testWhatsApp: (phoneNumber?: string) => apiPost<{ status: string; twilio_api_accepted: boolean; message_sid?: string }>("/api/v1/alerts/test-whatsapp", { phone_number: phoneNumber || null }),
};
