-- Run only after the 20261106_backtest_reliability migration.
SELECT j.id, j.status, j.progress, j.created_at, j.started_at,
       e.attempts, e.max_attempts, e.stage, e.heartbeat_at,
       e.dispatched_at, e.cancel_requested, e.failure_reason
FROM job_status j
JOIN backtest_execution e ON e.job_id = j.id
WHERE j.job_type = 'backtest'
ORDER BY j.created_at DESC LIMIT 50;
