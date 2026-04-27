-- Phase 8: Strategy deployment safety gate
-- Run this manually in DBeaver before starting the updated API.

ALTER TABLE strategies
    ADD COLUMN IF NOT EXISTS lifecycle_status VARCHAR(40) NOT NULL DEFAULT 'DRAFT',
    ADD COLUMN IF NOT EXISTS is_deployable_paper BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS is_deployable_demo BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS is_live_approved BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS verified_at TIMESTAMPTZ NULL,
    ADD COLUMN IF NOT EXISTS sandbox_passed_at TIMESTAMPTZ NULL,
    ADD COLUMN IF NOT EXISTS paper_enabled_at TIMESTAMPTZ NULL,
    ADD COLUMN IF NOT EXISTS demo_enabled_at TIMESTAMPTZ NULL,
    ADD COLUMN IF NOT EXISTS live_approved_at TIMESTAMPTZ NULL,
    ADD COLUMN IF NOT EXISTS approved_by UUID NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_strategies_approved_by_users'
    ) THEN
        ALTER TABLE strategies
            ADD CONSTRAINT fk_strategies_approved_by_users
            FOREIGN KEY (approved_by) REFERENCES users(id) ON DELETE SET NULL;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_strategies_lifecycle_status ON strategies(lifecycle_status);
CREATE INDEX IF NOT EXISTS idx_strategies_deployable_paper ON strategies(is_deployable_paper);
CREATE INDEX IF NOT EXISTS idx_strategies_deployable_demo ON strategies(is_deployable_demo);
CREATE INDEX IF NOT EXISTS idx_strategies_live_approved ON strategies(is_live_approved);
CREATE INDEX IF NOT EXISTS idx_strategies_approved_by ON strategies(approved_by);

-- Backfill lifecycle from existing visibility/workflow metadata without enabling deployment automatically.
UPDATE strategies
SET lifecycle_status = CASE
    WHEN visibility = 'PUBLIC' AND lifecycle_status IN ('DRAFT', 'PRIVATE') THEN 'PUBLISHED'
    ELSE lifecycle_status
END;
