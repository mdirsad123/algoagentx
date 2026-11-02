-- AlgoAgentX: manual PostgreSQL schema for cTrader/TradeLocker daily history sync

-- Apply ONCE to the same PostgreSQL DB used by AlgoAgentXAPI (psql -v ON_ERROR_STOP=1).

-- Does NOT modify legacy market_data, live_market_candles, strategies or orders.

-- If you apply this manually, DO NOT also run the Alembic migration for the same revision:

-- either upgrade via Alembic OR run this SQL, then mark the revision via Alembic stamp after verifying all DDL.

BEGIN;

CREATE TABLE IF NOT EXISTS market_data_sync_configs (
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	broker_account_id UUID NOT NULL, 
	instrument_id INTEGER NOT NULL, 
	provider VARCHAR(50) NOT NULL, 
	subaccount_id VARCHAR(120) NOT NULL, 
	broker_symbol VARCHAR(120) NOT NULL, 
	timeframe VARCHAR(20) NOT NULL, 
	enabled BOOLEAN DEFAULT false NOT NULL, 
	is_primary BOOLEAN DEFAULT false NOT NULL, 
	publish_approved BOOLEAN DEFAULT false NOT NULL, 
	initial_start TIMESTAMP WITH TIME ZONE, 
	checkpoint TIMESTAMP WITH TIME ZONE, 
	last_status VARCHAR(32) DEFAULT 'NEEDS_INITIAL_IMPORT' NOT NULL, 
	last_error VARCHAR(300), 
	last_synced_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_market_sync_source UNIQUE (broker_account_id, subaccount_id, instrument_id, timeframe, broker_symbol), 
	FOREIGN KEY(broker_account_id) REFERENCES broker_accounts (id) ON DELETE CASCADE, 
	FOREIGN KEY(instrument_id) REFERENCES instruments (id)
);

CREATE TABLE IF NOT EXISTS market_data_feed_candles (
	feed_id UUID NOT NULL, 
	timestamp TIMESTAMP WITH TIME ZONE NOT NULL, 
	open NUMERIC NOT NULL, 
	high NUMERIC NOT NULL, 
	low NUMERIC NOT NULL, 
	close NUMERIC NOT NULL, 
	volume NUMERIC DEFAULT '0' NOT NULL, 
	stored_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (feed_id, timestamp), 
	FOREIGN KEY(feed_id) REFERENCES market_data_sync_configs (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS market_data_sync_batches (
	scheduled_date DATE NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	dispatched_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (scheduled_date)
);

CREATE TABLE IF NOT EXISTS market_data_sync_runs (
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	feed_id UUID NOT NULL, 
	run_key VARCHAR(180) NOT NULL, 
	scheduled_date DATE, 
	requested_start TIMESTAMP WITH TIME ZONE, 
	requested_end TIMESTAMP WITH TIME ZONE, 
	dry_run BOOLEAN DEFAULT false NOT NULL, 
	status VARCHAR(32) DEFAULT 'QUEUED' NOT NULL, 
	started_at TIMESTAMP WITH TIME ZONE, 
	finished_at TIMESTAMP WITH TIME ZONE, 
	last_before TIMESTAMP WITH TIME ZONE, 
	last_after TIMESTAMP WITH TIME ZONE, 
	fetched INTEGER DEFAULT '0' NOT NULL, 
	inserted INTEGER DEFAULT '0' NOT NULL, 
	updated INTEGER DEFAULT '0' NOT NULL, 
	skipped INTEGER DEFAULT '0' NOT NULL, 
	invalid INTEGER DEFAULT '0' NOT NULL, 
	retry_count INTEGER DEFAULT '0' NOT NULL, 
	error VARCHAR(300), 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_market_sync_run_key UNIQUE (run_key), 
	FOREIGN KEY(feed_id) REFERENCES market_data_sync_configs (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_market_sync_enabled ON market_data_sync_configs (enabled);

CREATE UNIQUE INDEX IF NOT EXISTS uq_market_sync_primary ON market_data_sync_configs (instrument_id, timeframe) WHERE is_primary = true;

CREATE INDEX IF NOT EXISTS ix_market_feed_candle_time ON market_data_feed_candles (feed_id, timestamp);

CREATE INDEX IF NOT EXISTS ix_market_sync_runs_feed_created ON market_data_sync_runs (feed_id, created_at);

COMMIT;

-- Verify: SELECT COUNT(*) FROM market_data_sync_configs;
