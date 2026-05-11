-- BROKER-PRO-5 MT5 Agent Architecture safe migration
-- Run in DBeaver before starting the updated API.
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS mt5_agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    broker_account_id UUID NOT NULL REFERENCES broker_accounts(id) ON DELETE CASCADE,
    agent_token_hash VARCHAR(128) NOT NULL UNIQUE,
    status VARCHAR(30) NOT NULL DEFAULT 'DISCONNECTED',
    last_heartbeat_at TIMESTAMPTZ NULL,
    terminal_status VARCHAR(50) NULL,
    mt5_account_login VARCHAR(255) NULL,
    server_name VARCHAR(255) NULL,
    trading_mode VARCHAR(20) NOT NULL DEFAULT 'DEMO',
    balance NUMERIC(18,4) NULL,
    equity NUMERIC(18,4) NULL,
    currency VARCHAR(20) NULL,
    algo_trading_enabled BOOLEAN NULL,
    agent_version VARCHAR(80) NULL,
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_mt5_agents_user_account ON mt5_agents(user_id, broker_account_id);
CREATE INDEX IF NOT EXISTS idx_mt5_agents_status_heartbeat ON mt5_agents(status, last_heartbeat_at);

CREATE TABLE IF NOT EXISTS mt5_agent_commands (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL REFERENCES mt5_agents(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    broker_account_id UUID NOT NULL REFERENCES broker_accounts(id) ON DELETE CASCADE,
    command_type VARCHAR(50) NOT NULL DEFAULT 'PLACE_ORDER',
    status VARCHAR(30) NOT NULL DEFAULT 'PENDING',
    request_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    result_payload JSONB NULL,
    error_message TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    picked_up_at TIMESTAMPTZ NULL,
    completed_at TIMESTAMPTZ NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_mt5_agent_commands_agent_status ON mt5_agent_commands(agent_id, status);
CREATE INDEX IF NOT EXISTS idx_mt5_agent_commands_account_status ON mt5_agent_commands(broker_account_id, status);

-- Make existing MT5 accounts production-safe. They remain usable, but execution waits for an Agent heartbeat.
UPDATE broker_accounts
SET metadata_json = COALESCE(metadata_json, '{}'::jsonb) || jsonb_build_object(
    'mt5_agent', COALESCE(metadata_json->'mt5_agent', jsonb_build_object('status','AGENT_REQUIRED','message','Install AlgoAgentX MT5 Agent on your Windows PC or VPS where MetaTrader 5 is running.'))
)
WHERE UPPER(COALESCE(broker_code, broker_name, '')) = 'MT5';
