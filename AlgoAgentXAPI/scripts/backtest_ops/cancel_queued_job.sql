-- MANUAL ONLY. Replace the placeholder with an exact job ID.
-- Does NOT stop a running task or delete Celery messages.
-- Only cancels a job that has never started; do not cancel valid waiting jobs
-- without also reconciling/revoking their exact Celery task if needed.
BEGIN;
WITH candidate AS (
    SELECT j.id
    FROM job_status j JOIN backtest_execution e ON e.job_id=j.id
    WHERE j.id = 'REPLACE_WITH_EXACT_JOB_ID'
      AND j.job_type='backtest'
      AND j.status IN ('queued','pending','retry')
      AND j.started_at IS NULL
    FOR UPDATE OF j, e
), mark_execution AS (
    UPDATE backtest_execution e
       SET cancel_requested=true, stage='cancelled',
           failure_reason='Manually cancelled unstarted job'
      FROM candidate c WHERE e.job_id=c.id RETURNING e.job_id
)
UPDATE job_status j
   SET status='cancelled', message='Manually cancelled unstarted job',
       completed_at=now(), updated_at=now()
  FROM mark_execution m WHERE j.id=m.job_id
RETURNING j.id, j.status;
COMMIT;
