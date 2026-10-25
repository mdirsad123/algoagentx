SELECT
    timestamp,
    open,
    high,
    low,
    close,
    volume
FROM market_data
WHERE instrument_id  = 3
  AND timeframe = '5m'
  AND timestamp >= '2026-01-01 00:00:00'
  AND timestamp <  '2026-10-21 00:00:00'
ORDER BY timestamp ASC;

-------------------------------------
below query is partial order with deployement id
SELECT
    CASE
        WHEN p.broker_account_id = d.broker_account_id
        THEN 'PRIMARY'
        ELSE 'COPY'
    END AS account_type,

    p.symbol,
    p.side,
    p.status AS position_status,
    p.qty AS current_lot,
    p.avg_entry_price AS entry_price,

    d.partial_exit_enabled AS partial_enabled,
    s.partial_exit_at_r AS trigger_r,
    s.partial_trigger_price AS trigger_price,
    s.trigger_quote_price AS triggered_at_price,

    COALESCE(s.partial_status, 'NO_STATE') AS partial_status,
    s.planned_close_size AS close_lot,
    s.planned_runner_size AS runner_lot,
    s.triggered_at,
    s.filled_at,
    s.last_error

FROM live_positions p
JOIN strategy_deployments d
    ON d.id = p.deployment_id
LEFT JOIN live_position_management_states s
    ON s.live_position_id = p.id

WHERE p.deployment_id =
    '1eea2258-85be-443d-a502-dff0e54f628a'

ORDER BY p.created_at DESC
LIMIT 20;

------------------------------------------
below query to delete deployed strategy

BEGIN;

-- Backup the five local exit-order records
CREATE TABLE live_orders_cleanup_backup_20261011 AS
SELECT *
FROM live_orders
WHERE deployment_id IN (
    '1eea2258-85be-443d-a502-dff0e54f628a',
    '76fba393-e9f0-44e3-aa14-c40f4ecd63d7'
)
AND action = 'FULL_EXIT'
AND status = 'PLACED';

-- Clear only the five confirmed-stale local blockers
DELETE FROM live_orders
WHERE deployment_id IN (
    '1eea2258-85be-443d-a502-dff0e54f628a',
    '76fba393-e9f0-44e3-aa14-c40f4ecd63d7'
)
AND action = 'FULL_EXIT'
AND status = 'PLACED'
AND (
    SELECT COUNT(*)
    FROM strategy_deployments
    WHERE id IN (
        '1eea2258-85be-443d-a502-dff0e54f628a',
        '76fba393-e9f0-44e3-aa14-c40f4ecd63d7'
    )
    AND status = 'STOPPED'
    AND mode = 'DEMO'
) = 2
AND NOT EXISTS (
    SELECT 1
    FROM live_positions
    WHERE deployment_id IN (
        '1eea2258-85be-443d-a502-dff0e54f628a',
        '76fba393-e9f0-44e3-aa14-c40f4ecd63d7'
    )
    AND status = 'OPEN'
)
RETURNING id, deployment_id, action, status;

-- Verify exactly 5 rows returned.
-- Execute COMMIT only if those are the five broker-verified records.
-- Otherwise execute ROLLBACK.
COMMIT;