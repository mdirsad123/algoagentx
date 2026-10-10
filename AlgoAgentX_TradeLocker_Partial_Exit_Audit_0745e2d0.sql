-- AlgoAgentX TradeLocker / copy partial-exit audit (READ ONLY).
-- Deployment: 76fba393-e9f0-44e3-aa14-c40f4ecd63d7
-- Verified table/column names against uploaded SQLAlchemy models (2026-10-10).
-- No INSERT, UPDATE, DELETE or schema changes.
-- Use psql -v ON_ERROR_STOP=1 -f <this_file> or pipe it to docker exec -i ... psql.

\pset pager off
\echo '1) DEPLOYMENT + PRIMARY ACCOUNT + COPY TARGETS'
SELECT d.id, d.name, d.status, d.mode, d.instrument, d.broker_symbol,
       d.timeframe, d.partial_exit_enabled, d.partial_exit_at_r,
       d.partial_exit_percent, d.copy_trading_enabled,
       d.copy_broker_account_ids, d.last_broker_sync_at,
       d.last_live_sync_at, d.live_sync_last_error,
       b.id AS primary_broker_account_id, b.broker_code AS primary_provider,
       b.account_label AS primary_account, b.mode AS primary_mode
FROM strategy_deployments d
LEFT JOIN broker_accounts b ON b.id=d.broker_account_id
WHERE d.id='76fba393-e9f0-44e3-aa14-c40f4ecd63d7';

\echo '2) OPEN POSITIONS + EACH ACCOUNTS PARTIAL STATUS'
SELECT CASE WHEN p.broker_account_id=d.broker_account_id THEN 'PRIMARY' ELSE 'COPY' END AS account_role,
       b.account_label, b.broker_code,
       p.id AS local_position_id, p.broker_position_id, p.symbol, p.side,
       p.status AS position_status, p.qty AS broker_synced_lots,
       p.avg_entry_price AS broker_synced_entry,
       p.stop_loss AS local_stop_price, p.target AS local_target_price,
       s.partial_status, s.partial_trigger_price, s.partial_exit_at_r,
       s.partial_exit_percent, s.planned_close_size,
       s.planned_runner_size, s.attempt_count, s.triggered_at,
       s.sent_at, s.filled_at, s.last_error,
       s.partial_close_order_id, s.partial_close_broker_order_id
FROM live_positions p
JOIN strategy_deployments d ON d.id=p.deployment_id
LEFT JOIN broker_accounts b ON b.id=p.broker_account_id
LEFT JOIN live_position_management_states s ON s.live_position_id=p.id
WHERE p.deployment_id='76fba393-e9f0-44e3-aa14-c40f4ecd63d7'
ORDER BY p.status, account_role, p.created_at DESC;

\echo '3) MISSING PARTIAL STATE / ORIGINAL STOP LOSS (BLOCKERS)'
SELECT p.id AS local_position_id, p.broker_account_id, b.broker_code,
       p.broker_position_id, p.symbol, p.side, p.qty, p.stop_loss,
       p.target, p.opened_at,
       CASE
         WHEN p.broker_position_id IS NULL THEN 'MISSING_BROKER_POSITION_ID'
         WHEN p.stop_loss IS NULL THEN 'MISSING_ORIGINAL_STOP_PRICE'
         WHEN s.id IS NULL THEN 'NO_MANAGEMENT_STATE'
         ELSE 'STATE_EXISTS'
       END AS diagnosis
FROM live_positions p
LEFT JOIN live_position_management_states s ON s.live_position_id=p.id
LEFT JOIN broker_accounts b ON b.id=p.broker_account_id
WHERE p.deployment_id='76fba393-e9f0-44e3-aa14-c40f4ecd63d7'
  AND p.status='OPEN'
ORDER BY p.created_at DESC;

\echo '4) ENTRY + PARTIAL EXIT ORDER AUDIT PER PRIMARY/COPY'
SELECT CASE WHEN o.broker_account_id=d.broker_account_id THEN 'PRIMARY' ELSE 'COPY' END AS account_role,
       b.account_label, b.broker_code,
       o.created_at, o.id AS local_order_id, o.signal_id,
       o.action, o.status, o.broker_order_id,
       o.symbol, o.side, o.qty, o.entry_price,
       o.executed_price, o.stop_loss, o.target,
       o.quantity_mode, o.error_message,
       o.raw_response->>'requires_reconciliation' AS needs_broker_reconciliation,
       o.raw_response->'broker_sync'->>'positionId' AS linked_broker_position_id,
       o.raw_response->>'broker_position_id' AS close_broker_position_id
FROM live_orders o
JOIN strategy_deployments d ON d.id=o.deployment_id
LEFT JOIN broker_accounts b ON b.id=o.broker_account_id
WHERE o.deployment_id='76fba393-e9f0-44e3-aa14-c40f4ecd63d7'
  AND o.action IN ('ENTRY','PARTIAL_EXIT')
ORDER BY o.created_at DESC LIMIT 150;

\echo '5) PARTIAL EVENT TIMELINE (TRIGGER, BROKER REQUEST, RECONCILIATION, ERRORS)'
SELECT l.created_at, l.event_type, l.level, l.message, l.metadata_json
FROM live_trade_logs l
WHERE l.deployment_id='76fba393-e9f0-44e3-aa14-c40f4ecd63d7'
  AND (l.event_type LIKE 'PARTIAL_EXIT%' OR l.event_type LIKE 'COPY_%' OR l.event_type LIKE 'TRADELOCKER%')
ORDER BY l.created_at DESC LIMIT 150;

\echo '6) COUNTS BY ACCOUNT + PARTIAL STATUS'
SELECT CASE WHEN p.broker_account_id=d.broker_account_id THEN 'PRIMARY' ELSE 'COPY' END AS account_role,
       p.broker_account_id, b.broker_code,
       COALESCE(s.partial_status, 'NO_STATE') AS partial_status,
       COUNT(*) AS positions,
       COUNT(*) FILTER (WHERE p.status='OPEN') AS still_open
FROM live_positions p
JOIN strategy_deployments d ON d.id=p.deployment_id
LEFT JOIN broker_accounts b ON b.id=p.broker_account_id
LEFT JOIN live_position_management_states s ON s.live_position_id=p.id
WHERE p.deployment_id='76fba393-e9f0-44e3-aa14-c40f4ecd63d7'
GROUP BY 1,2,3,4 ORDER BY 1,2,4;

\echo '7) BROKER POSITION/ORDER EVENTS FOR THIS DEPLOYMENT'
SELECT e.created_at, e.broker_provider_code, e.broker_account_id,
       e.event_type, e.broker_order_id, e.processed,
       e.raw_payload->>'positions_count' AS position_count,
       e.raw_payload->>'status' AS broker_status
FROM broker_order_events e
WHERE e.deployment_id='76fba393-e9f0-44e3-aa14-c40f4ecd63d7'
ORDER BY e.created_at DESC LIMIT 80;

-- Interpretation:
-- PENDING: state exists; wait for valid quote to cross trigger.
-- NO_STATE + missing SL: TradeLocker broker /positions reports stopLossId,
--   not an SL price. A uniquely position-linked entry history row is needed.
-- SKIPPED_MIN_SIZE: close OR runner below approved broker lot minimum/step.
-- DRY_RUN: broker sending disabled in app environment.
-- AWAITING_RECONCILE: request accepted, not proven filled.
-- MANUAL_REVIEW: broker response uncertain; no blind auto retry.
-- DONE: app reconciled expected runner lot amount from broker positions.
-- Important: original SL/TP prices retained from entry are NOT a fresh
-- independent confirmation that broker protective orders still exist.
