-- AlgoAgentX Live Trading Foundation - Phase 1
-- Run this once in DBeaver/PostgreSQL before using the live trading API endpoints.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS broker_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    broker_name VARCHAR(50) NOT NULL DEFAULT 'MT5',
    account_label VARCHAR(255) NOT NULL,
    mode VARCHAR(20) NOT NULL DEFAULT 'DEMO' CHECK (mode IN ('PAPER', 'DEMO', 'LIVE')),
    status VARCHAR(30) NOT NULL DEFAULT 'DISCONNECTED' CHECK (status IN ('CONNECTED', 'DISCONNECTED', 'EXPIRED', 'ERROR')),
    server_name VARCHAR(255),
    login_id VARCHAR(255),
    encrypted_password TEXT,
    encrypted_token TEXT,
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    last_connected_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS strategy_deployments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    strategy_id VARCHAR(64) NOT NULL REFERENCES strategies(id) ON DELETE RESTRICT,
    broker_account_id UUID REFERENCES broker_accounts(id) ON DELETE SET NULL,
    name VARCHAR(255) NOT NULL,
    instrument VARCHAR(100) NOT NULL,
    timeframe VARCHAR(50) NOT NULL,
    mode VARCHAR(20) NOT NULL DEFAULT 'PAPER' CHECK (mode IN ('PAPER', 'DEMO', 'LIVE')),
    status VARCHAR(30) NOT NULL DEFAULT 'DRAFT' CHECK (status IN ('DRAFT', 'RUNNING', 'PAUSED', 'STOPPED', 'ERROR')),
    capital NUMERIC(18,4) NOT NULL DEFAULT 100000,
    risk_per_trade NUMERIC(10,6) NOT NULL DEFAULT 0.01,
    rr_ratio NUMERIC(10,4) NOT NULL DEFAULT 2,
    price_risk_pct NUMERIC(10,6) NOT NULL DEFAULT 0.002,
    max_daily_loss NUMERIC(18,4) NOT NULL DEFAULT 5000,
    max_trades_per_day INTEGER NOT NULL DEFAULT 10,
    max_open_positions INTEGER NOT NULL DEFAULT 1,
    allow_short BOOLEAN NOT NULL DEFAULT TRUE,
    auto_trade_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    tradingview_secret VARCHAR(255),
    last_signal_at TIMESTAMPTZ,
    last_heartbeat_at TIMESTAMPTZ,
    started_at TIMESTAMPTZ,
    stopped_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS live_signals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    deployment_id UUID NOT NULL REFERENCES strategy_deployments(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    strategy_id VARCHAR(64) NOT NULL REFERENCES strategies(id) ON DELETE RESTRICT,
    source VARCHAR(30) NOT NULL DEFAULT 'MANUAL' CHECK (source IN ('TRADINGVIEW', 'ENGINE', 'MANUAL')),
    symbol VARCHAR(100) NOT NULL,
    timeframe VARCHAR(50) NOT NULL,
    signal_type VARCHAR(20) NOT NULL CHECK (signal_type IN ('BUY', 'SELL', 'EXIT', 'HOLD')),
    side VARCHAR(20) CHECK (side IS NULL OR side IN ('LONG', 'SHORT')),
    price NUMERIC(18,8),
    candle_time TIMESTAMPTZ,
    confidence NUMERIC(10,6),
    reason TEXT,
    raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    status VARCHAR(30) NOT NULL DEFAULT 'RECEIVED' CHECK (status IN ('RECEIVED', 'ACCEPTED', 'REJECTED', 'EXECUTED', 'ERROR')),
    rejection_reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS live_orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    deployment_id UUID NOT NULL REFERENCES strategy_deployments(id) ON DELETE CASCADE,
    signal_id UUID REFERENCES live_signals(id) ON DELETE SET NULL,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    broker_account_id UUID REFERENCES broker_accounts(id) ON DELETE SET NULL,
    broker_order_id VARCHAR(255),
    symbol VARCHAR(100) NOT NULL,
    side VARCHAR(20) NOT NULL CHECK (side IN ('BUY', 'SELL')),
    order_type VARCHAR(30) NOT NULL DEFAULT 'MARKET' CHECK (order_type IN ('MARKET', 'LIMIT', 'SL', 'TARGET')),
    qty NUMERIC(18,8) NOT NULL,
    entry_price NUMERIC(18,8),
    executed_price NUMERIC(18,8),
    stop_loss NUMERIC(18,8),
    target NUMERIC(18,8),
    status VARCHAR(30) NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'PLACED', 'FILLED', 'REJECTED', 'CANCELLED', 'ERROR')),
    error_message TEXT,
    raw_response JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS live_positions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    deployment_id UUID NOT NULL REFERENCES strategy_deployments(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    broker_account_id UUID REFERENCES broker_accounts(id) ON DELETE SET NULL,
    symbol VARCHAR(100) NOT NULL,
    side VARCHAR(20) NOT NULL CHECK (side IN ('LONG', 'SHORT')),
    qty NUMERIC(18,8) NOT NULL,
    avg_entry_price NUMERIC(18,8) NOT NULL,
    current_price NUMERIC(18,8),
    stop_loss NUMERIC(18,8),
    target NUMERIC(18,8),
    unrealized_pnl NUMERIC(18,4) NOT NULL DEFAULT 0,
    realized_pnl NUMERIC(18,4) NOT NULL DEFAULT 0,
    status VARCHAR(30) NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN', 'CLOSED', 'ERROR')),
    opened_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    closed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS live_trade_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    deployment_id UUID NOT NULL REFERENCES strategy_deployments(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    event_type VARCHAR(80) NOT NULL,
    level VARCHAR(20) NOT NULL DEFAULT 'INFO' CHECK (level IN ('INFO', 'WARNING', 'ERROR')),
    message TEXT NOT NULL,
    metadata_json JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS live_equity_points (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    deployment_id UUID NOT NULL REFERENCES strategy_deployments(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    timestamp TIMESTAMPTZ NOT NULL,
    equity NUMERIC(18,4) NOT NULL,
    balance NUMERIC(18,4),
    unrealized_pnl NUMERIC(18,4),
    realized_pnl NUMERIC(18,4),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_broker_accounts_user_status ON broker_accounts(user_id, status);
CREATE INDEX IF NOT EXISTS idx_broker_accounts_user_mode ON broker_accounts(user_id, mode);
CREATE INDEX IF NOT EXISTS idx_strategy_deployments_user_status ON strategy_deployments(user_id, status);
CREATE INDEX IF NOT EXISTS idx_strategy_deployments_strategy ON strategy_deployments(strategy_id);
CREATE INDEX IF NOT EXISTS idx_strategy_deployments_broker ON strategy_deployments(broker_account_id);
CREATE INDEX IF NOT EXISTS idx_live_signals_deployment_created ON live_signals(deployment_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_live_signals_user_created ON live_signals(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_live_signals_status ON live_signals(status);
CREATE INDEX IF NOT EXISTS idx_live_orders_deployment_created ON live_orders(deployment_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_live_orders_user_status ON live_orders(user_id, status);
CREATE INDEX IF NOT EXISTS idx_live_orders_signal ON live_orders(signal_id);
CREATE INDEX IF NOT EXISTS idx_live_positions_deployment_status ON live_positions(deployment_id, status);
CREATE INDEX IF NOT EXISTS idx_live_positions_user_status ON live_positions(user_id, status);
CREATE INDEX IF NOT EXISTS idx_live_positions_symbol ON live_positions(symbol);
CREATE INDEX IF NOT EXISTS idx_live_trade_logs_deployment_created ON live_trade_logs(deployment_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_live_trade_logs_user_created ON live_trade_logs(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_live_trade_logs_level ON live_trade_logs(level);
CREATE INDEX IF NOT EXISTS idx_live_equity_points_deployment_timestamp ON live_equity_points(deployment_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_live_equity_points_user_timestamp ON live_equity_points(user_id, timestamp DESC);
