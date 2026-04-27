-- Phase 7: Admin Live Execution Control Center
-- Run this once in DBeaver before using /api/v1/admin/live/* endpoints.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS admin_live_actions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    admin_user_id UUID NULL REFERENCES users(id) ON DELETE SET NULL,
    deployment_id UUID NOT NULL REFERENCES strategy_deployments(id) ON DELETE CASCADE,
    action VARCHAR(80) NOT NULL,
    reason TEXT NULL,
    metadata_json JSONB NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_admin_live_actions_deployment_created
    ON admin_live_actions (deployment_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_admin_live_actions_admin_created
    ON admin_live_actions (admin_user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_admin_live_actions_action
    ON admin_live_actions (action);
