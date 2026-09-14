export type AlertType = "CROSSING_UP" | "CROSSING_DOWN" | "ENTERING_ZONE" | "LEAVING_ZONE";
export type AlertTriggerMode = "ONCE" | "RECURRING";
export type AlertEventType = AlertType | "APPROACHING_TARGET" | "APPROACHING_ZONE";

export interface PriceAlert {
  id: string;
  user_id: string;
  broker_account_id?: string | null;
  symbol: string;
  provider: string;
  alert_type: AlertType;
  target_price?: string | number | null;
  zone_low?: string | number | null;
  zone_high?: string | number | null;
  status: string;
  runtime_state: string;
  trigger_mode: AlertTriggerMode;
  cooldown_seconds: number;
  rearm_distance: string | number;
  rearm_type: string;
  expires_at?: string | null;
  telegram_enabled: boolean;
  browser_enabled: boolean;
  whatsapp_enabled: boolean;
  approach_enabled: boolean;
  approach_distance?: string | number | null;
  approach_state: string;
  last_approach_triggered_at?: string | null;
  approach_trigger_count: number;
  last_price?: string | number | null;
  last_market_timestamp?: string | null;
  last_triggered_at?: string | null;
  rearm_eligible_at?: string | null;
  trigger_count: number;
  metadata?: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface AlertEvent {
  id: string;
  alert_id: string;
  user_id: string;
  symbol: string;
  provider: string;
  condition_type: AlertEventType;
  trigger_price: string | number;
  previous_price?: string | number | null;
  market_timestamp?: string | null;
  server_received_at: string;
  condition_detected_at: string;
  notification_queued_at?: string | null;
  notification_sent_at?: string | null;
  notification_response_at?: string | null;
  telegram_status: string;
  browser_status: string;
  whatsapp_status: string;
  feed_to_server_latency_ms?: number | null;
  evaluation_latency_ms?: number | null;
  notification_api_latency_ms?: number | null;
  total_internal_latency_ms?: number | null;
  payload?: Record<string, unknown> | null;
  created_at: string;
}

export interface AlertHealth {
  worker: string;
  worker_heartbeat?: string | null;
  redis: string;
  database: string;
  market_feed: string;
  active_alert_count?: number;
  last_tick?: string | null;
  telegram: string;
  whatsapp: string;
  feeds: Array<{
    provider: string;
    broker_account_id?: string | null;
    status: string;
    last_tick_at?: string | null;
    last_heartbeat_at?: string | null;
    connection_error?: string | null;
  }>;
}

export interface TelegramChannel {
  configured: boolean;
  chat_id?: string | null;
  enabled: boolean;
  verified: boolean;
  using_global_fallback: boolean;
}

export interface WhatsAppChannel {
  configured: boolean;
  phone_number?: string | null;
  enabled: boolean;
  verified: boolean;
  using_global_fallback: boolean;
  content_template_configured: boolean;
  approaching_template_configured?: boolean;
  triggered_template_configured?: boolean;
}

export interface AlertPayload {
  symbol: string;
  provider: string;
  broker_account_id?: string | null;
  alert_type: AlertType;
  target_price?: number | null;
  zone_low?: number | null;
  zone_high?: number | null;
  trigger_mode: AlertTriggerMode;
  cooldown_seconds: number;
  rearm_distance: number;
  rearm_type: string;
  expires_at?: string | null;
  telegram_enabled: boolean;
  browser_enabled: false;
  whatsapp_enabled: boolean;
  approach_enabled: boolean;
  approach_distance?: number | null;
}
