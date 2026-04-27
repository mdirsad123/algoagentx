CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS live_market_candles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    deployment_id UUID NULL REFERENCES strategy_deployments(id) ON DELETE CASCADE,
    broker_account_id UUID NULL REFERENCES broker_accounts(id) ON DELETE SET NULL,
    symbol VARCHAR(100) NOT NULL,
    timeframe VARCHAR(50) NOT NULL,
    candle_time TIMESTAMPTZ NOT NULL,
    open NUMERIC(18, 8) NOT NULL,
    high NUMERIC(18, 8) NOT NULL,
    low NUMERIC(18, 8) NOT NULL,
    close NUMERIC(18, 8) NOT NULL,
    volume NUMERIC(18, 8) NULL,
    source VARCHAR(30) NOT NULL DEFAULT 'MT5',
    is_closed BOOLEAN NOT NULL DEFAULT TRUE,
    raw_payload JSONB NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_live_market_candles_dep_symbol_tf_time UNIQUE (deployment_id, symbol, timeframe, candle_time)
);

CREATE INDEX IF NOT EXISTS idx_live_market_candles_deployment_time
    ON live_market_candles (deployment_id, candle_time DESC);

CREATE INDEX IF NOT EXISTS idx_live_market_candles_symbol_tf_time
    ON live_market_candles (symbol, timeframe, candle_time DESC);

CREATE INDEX IF NOT EXISTS idx_live_market_candles_broker_time
    ON live_market_candles (broker_account_id, candle_time DESC);

CREATE OR REPLACE FUNCTION set_live_market_candles_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_live_market_candles_updated_at ON live_market_candles;
CREATE TRIGGER trg_live_market_candles_updated_at
BEFORE UPDATE ON live_market_candles
FOR EACH ROW
EXECUTE FUNCTION set_live_market_candles_updated_at();
