-- Idempotent registration. Run against algoagentx_prod after backing up the database.
-- Starts disabled: administrator explicitly enables after reviewing integration.
INSERT INTO broker_providers (
  id, code, name, display_name, market_type, broker_category, auth_type,
  supports_paper, supports_demo, supports_live, supports_market_data,
  supports_orders, supports_websocket, is_enabled, is_live_enabled,
  setup_mode, description, admin_notes
)
VALUES (
  gen_random_uuid(), 'TRADELOCKER', 'TradeLocker', 'TradeLocker REST API', 'FOREX_CFD',
  'Cloud Broker', 'EMAIL_PASSWORD', false, true, true, true, true, false, false, false,
  'REST_API',
  'TradeLocker account and instrument integration; order execution gated pending demo validation.',
  'Demo validation required: order fill, reconciliation, partial exit, SL/TP, and rate limits. Disable at any time.'
)
ON CONFLICT (code) DO NOTHING;
