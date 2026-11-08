# AlgoAgentX — Standard + Funded Backtest History Cleanup

**Use in DBeaver:** Stop backtest workers, take a database backup, then run the entire SQL block as a script (`Alt+X`). This permanently removes saved backtest results. It preserves strategies, candles, live trading records, funded account configuration, and credit transaction ledger rows (while clearing their backtest/job references).

```sql
ROLLBACK;

BEGIN;

-- Preserve credit ledger rows; remove references to deleted backtests/jobs.
UPDATE public.credit_transactions
SET backtest_id = NULL
WHERE backtest_id IS NOT NULL;

UPDATE public.credit_transactions
SET job_id = NULL
WHERE job_id IN (
    SELECT id
    FROM public.job_status
    WHERE LOWER(BTRIM(job_type)) = 'backtest'
);

-- Standard backtest results (all records in these history tables).
TRUNCATE TABLE
    public.backtest_execution,
    public.trades,
    public.equity_curve,
    public.pnl_calendar,
    public.metrics;

DELETE FROM public.performance_metrics;

DELETE FROM public.job_status
WHERE LOWER(BTRIM(job_type)) = 'backtest';

-- Funded backtest results (child records first).
DELETE FROM public.funded_backtest_events;
DELETE FROM public.funded_backtest_daily_snapshots;
DELETE FROM public.funded_backtest_trades;
DELETE FROM public.funded_backtest_phases;
DELETE FROM public.funded_backtest_runs;

COMMIT;

-- All counts should be zero.
SELECT 'standard_backtests' AS history_type, COUNT(*) AS remaining
FROM public.performance_metrics
UNION ALL SELECT 'backtest_jobs', COUNT(*) FROM public.job_status WHERE LOWER(BTRIM(job_type)) = 'backtest'
UNION ALL SELECT 'backtest_execution', COUNT(*) FROM public.backtest_execution
UNION ALL SELECT 'trades', COUNT(*) FROM public.trades
UNION ALL SELECT 'equity_curve', COUNT(*) FROM public.equity_curve
UNION ALL SELECT 'pnl_calendar', COUNT(*) FROM public.pnl_calendar
UNION ALL SELECT 'metrics', COUNT(*) FROM public.metrics
UNION ALL SELECT 'funded_backtest_runs', COUNT(*) FROM public.funded_backtest_runs
UNION ALL SELECT 'funded_backtest_phases', COUNT(*) FROM public.funded_backtest_phases
UNION ALL SELECT 'funded_backtest_trades', COUNT(*) FROM public.funded_backtest_trades
UNION ALL SELECT 'funded_backtest_daily_snapshots', COUNT(*) FROM public.funded_backtest_daily_snapshots
UNION ALL SELECT 'funded_backtest_events', COUNT(*) FROM public.funded_backtest_events;
```

If the script fails before `COMMIT`, execute `ROLLBACK;` in the same connection and inspect the reported error. Do not run `TRUNCATE ... CASCADE`.

**Schema note:** `public.backtest_runs` is intentionally excluded because it does not exist in the inspected AlgoAgentX database.
