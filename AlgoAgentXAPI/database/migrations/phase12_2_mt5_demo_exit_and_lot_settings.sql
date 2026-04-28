-- Phase 12.2: MT5 DEMO exit matching + per-deployment lot cap
-- Run manually in DBeaver after replacing API code.
-- LIVE mode remains disabled. This only adds DEMO-safe configuration.

BEGIN;

ALTER TABLE strategy_deployments
ADD COLUMN IF NOT EXISTS mt5_demo_max_lot NUMERIC(18, 8);

COMMENT ON COLUMN strategy_deployments.mt5_demo_max_lot IS
'Optional per-deployment MT5 DEMO max lot cap. NULL uses MT5_DEMO_MAX_LOT env/default; broker adapter still enforces symbol min/max/step.';

UPDATE strategy_deployments
SET mt5_demo_max_lot = 0.02
WHERE mode = 'DEMO'
  AND mt5_demo_max_lot IS NULL;

COMMIT;
