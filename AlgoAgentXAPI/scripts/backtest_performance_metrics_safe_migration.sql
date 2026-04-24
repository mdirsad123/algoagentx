BEGIN;

ALTER TABLE IF EXISTS performance_metrics
    ADD COLUMN IF NOT EXISTS period VARCHAR(255);

UPDATE performance_metrics
SET period = COALESCE(period, CONCAT(COALESCE(start_date::text, ''), ' to ', COALESCE(end_date::text, '')))
WHERE period IS NULL;

ALTER TABLE IF EXISTS performance_metrics
    ADD COLUMN IF NOT EXISTS instrument_id INTEGER;

ALTER TABLE IF EXISTS performance_metrics
    ADD COLUMN IF NOT EXISTS timeframe VARCHAR(32);

ALTER TABLE IF EXISTS performance_metrics
    ADD COLUMN IF NOT EXISTS start_date DATE;

ALTER TABLE IF EXISTS performance_metrics
    ADD COLUMN IF NOT EXISTS end_date DATE;

ALTER TABLE IF EXISTS performance_metrics
    ADD COLUMN IF NOT EXISTS initial_capital NUMERIC;

ALTER TABLE IF EXISTS performance_metrics
    ADD COLUMN IF NOT EXISTS final_capital NUMERIC;

ALTER TABLE IF EXISTS performance_metrics
    ADD COLUMN IF NOT EXISTS net_profit NUMERIC;

ALTER TABLE IF EXISTS performance_metrics
    ADD COLUMN IF NOT EXISTS max_drawdown NUMERIC;

ALTER TABLE IF EXISTS performance_metrics
    ADD COLUMN IF NOT EXISTS sharpe_ratio NUMERIC;

ALTER TABLE IF EXISTS performance_metrics
    ADD COLUMN IF NOT EXISTS sortino_ratio NUMERIC;

ALTER TABLE IF EXISTS performance_metrics
    ADD COLUMN IF NOT EXISTS calmar_ratio NUMERIC;

ALTER TABLE IF EXISTS performance_metrics
    ADD COLUMN IF NOT EXISTS win_rate NUMERIC;

ALTER TABLE IF EXISTS performance_metrics
    ADD COLUMN IF NOT EXISTS total_trades INTEGER;

ALTER TABLE IF EXISTS performance_metrics
    ADD COLUMN IF NOT EXISTS winning_trades INTEGER;

ALTER TABLE IF EXISTS performance_metrics
    ADD COLUMN IF NOT EXISTS losing_trades INTEGER;

ALTER TABLE IF EXISTS performance_metrics
    ADD COLUMN IF NOT EXISTS profit_factor NUMERIC;

ALTER TABLE IF EXISTS performance_metrics
    ADD COLUMN IF NOT EXISTS avg_win NUMERIC;

ALTER TABLE IF EXISTS performance_metrics
    ADD COLUMN IF NOT EXISTS avg_loss NUMERIC;

ALTER TABLE IF EXISTS performance_metrics
    ADD COLUMN IF NOT EXISTS expectancy NUMERIC;

ALTER TABLE IF EXISTS performance_metrics
    ADD COLUMN IF NOT EXISTS return_pct NUMERIC;

UPDATE performance_metrics
SET avg_win = COALESCE(avg_win, 0),
    avg_loss = COALESCE(avg_loss, 0),
    expectancy = COALESCE(expectancy, 0),
    return_pct = COALESCE(return_pct, 0)
WHERE avg_win IS NULL OR avg_loss IS NULL OR expectancy IS NULL OR return_pct IS NULL;

ALTER TABLE IF EXISTS performance_metrics
    ALTER COLUMN avg_win SET DEFAULT 0;
ALTER TABLE IF EXISTS performance_metrics
    ALTER COLUMN avg_loss SET DEFAULT 0;
ALTER TABLE IF EXISTS performance_metrics
    ALTER COLUMN expectancy SET DEFAULT 0;
ALTER TABLE IF EXISTS performance_metrics
    ALTER COLUMN return_pct SET DEFAULT 0;

ALTER TABLE IF EXISTS performance_metrics
    ALTER COLUMN avg_win DROP NOT NULL;
ALTER TABLE IF EXISTS performance_metrics
    ALTER COLUMN avg_loss DROP NOT NULL;
ALTER TABLE IF EXISTS performance_metrics
    ALTER COLUMN expectancy DROP NOT NULL;
ALTER TABLE IF EXISTS performance_metrics
    ALTER COLUMN return_pct DROP NOT NULL;

ALTER TABLE IF EXISTS performance_metrics
    ADD COLUMN IF NOT EXISTS status VARCHAR(32) DEFAULT 'completed';

ALTER TABLE IF EXISTS performance_metrics
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();

ALTER TABLE IF EXISTS performance_metrics
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

UPDATE performance_metrics
SET created_at = COALESCE(created_at, NOW()),
    updated_at = COALESCE(updated_at, created_at, NOW())
WHERE created_at IS NULL OR updated_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_performance_metrics_instrument_id
    ON performance_metrics (instrument_id);

CREATE INDEX IF NOT EXISTS idx_performance_metrics_strategy_instrument_tf
    ON performance_metrics (strategy_id, instrument_id, timeframe);

CREATE INDEX IF NOT EXISTS idx_performance_metrics_date_range
    ON performance_metrics (start_date, end_date);

COMMIT;
