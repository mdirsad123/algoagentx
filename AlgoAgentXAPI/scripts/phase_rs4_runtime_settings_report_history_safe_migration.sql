-- Phase RS-4 Runtime Settings Report + History Transparency Upgrade
-- Safe to run more than once in DBeaver.

ALTER TABLE IF EXISTS performance_metrics
  ADD COLUMN IF NOT EXISTS runtime_config_snapshot JSONB NULL,
  ADD COLUMN IF NOT EXISTS instrument_spec_snapshot JSONB NULL,
  ADD COLUMN IF NOT EXISTS professional_summary JSONB NULL;

-- Optional but useful when filtering/reporting recent runs.
CREATE INDEX IF NOT EXISTS idx_performance_metrics_runtime_config_snapshot_gin
  ON performance_metrics USING GIN (runtime_config_snapshot);
