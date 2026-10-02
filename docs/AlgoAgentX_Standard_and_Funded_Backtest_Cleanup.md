# AlgoAgentX — Backtest History Cleanup Guide

This file contains **two separate cleanup queries**:

1. **Standard Backtest History Cleanup**
2. **Funded Backtest History Cleanup**

You can run either one separately, or run both when you want to completely clear all saved backtest history.

---

# IMPORTANT

Before deleting history:

- Stop any active backtest worker/process.
- Take a PostgreSQL backup if this is production.
- These queries delete **backtest history only**.
- They do not delete strategies, market data, users, broker accounts, subscriptions, live trading data, or funded account configuration.

---

# 1. STANDARD BACKTEST HISTORY

## Standard Backtest Tables

This cleanup removes history from:

- `performance_metrics`
- `trades`
- `equity_curve`
- `pnl_calendar`
- `metrics`
- `job_status` where `job_type = 'backtest'`

It preserves:

- strategies
- users
- instruments
- market data
- credit transaction history
- live trading data
- broker accounts
- subscriptions
- pricing
- funded account configuration

---

## 1.1 Check Standard Backtest Rows Before Cleanup

```sql
SELECT 'performance_metrics' AS table_name, COUNT(*) AS rows
FROM performance_metrics

UNION ALL
SELECT 'trades', COUNT(*) FROM trades

UNION ALL
SELECT 'equity_curve', COUNT(*) FROM equity_curve

UNION ALL
SELECT 'pnl_calendar', COUNT(*) FROM pnl_calendar

UNION ALL
SELECT 'metrics', COUNT(*) FROM metrics

UNION ALL
SELECT 'backtest_jobs', COUNT(*)
FROM job_status
WHERE LOWER(COALESCE(job_type, '')) = 'backtest';
```

---

## 1.2 STANDARD BACKTEST CLEANUP QUERY

Run this query to clear only standard/normal backtest history.

```sql
BEGIN;

-- ============================================================
-- A. Capture standard backtest IDs
-- ============================================================

CREATE TEMP TABLE _cleanup_standard_backtest_ids
ON COMMIT DROP
AS
SELECT CAST(id AS TEXT) AS id
FROM performance_metrics;


-- ============================================================
-- B. Capture standard backtest job IDs
-- ============================================================

CREATE TEMP TABLE _cleanup_standard_job_ids
ON COMMIT DROP
AS
SELECT CAST(id AS TEXT) AS id
FROM job_status
WHERE LOWER(COALESCE(job_type, '')) = 'backtest';


-- ============================================================
-- C. Preserve credit transaction history
--    Only remove references to deleted backtests/jobs.
-- ============================================================

DO $$
BEGIN

    IF to_regclass('public.credit_transactions') IS NOT NULL THEN

        IF EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'credit_transactions'
              AND column_name = 'backtest_id'
        ) THEN

            UPDATE credit_transactions
            SET backtest_id = NULL
            WHERE backtest_id IS NOT NULL
              AND CAST(backtest_id AS TEXT) IN (
                  SELECT id
                  FROM _cleanup_standard_backtest_ids
              );

        END IF;


        IF EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'credit_transactions'
              AND column_name = 'job_id'
        ) THEN

            UPDATE credit_transactions
            SET job_id = NULL
            WHERE job_id IS NOT NULL
              AND CAST(job_id AS TEXT) IN (
                  SELECT id
                  FROM _cleanup_standard_job_ids
              );

        END IF;

    END IF;

END $$;


-- ============================================================
-- D. Delete standard backtest child/history tables
-- ============================================================

DELETE FROM metrics
WHERE CAST(backtest_id AS TEXT) IN (
    SELECT id
    FROM _cleanup_standard_backtest_ids
);


DELETE FROM trades
WHERE CAST(backtest_id AS TEXT) IN (
    SELECT id
    FROM _cleanup_standard_backtest_ids
);


DELETE FROM equity_curve
WHERE CAST(backtest_id AS TEXT) IN (
    SELECT id
    FROM _cleanup_standard_backtest_ids
);


DELETE FROM pnl_calendar
WHERE CAST(backtest_id AS TEXT) IN (
    SELECT id
    FROM _cleanup_standard_backtest_ids
);


-- ============================================================
-- E. Delete main standard backtest history
-- ============================================================

DELETE FROM performance_metrics;


-- ============================================================
-- F. Delete only standard backtest jobs
-- ============================================================

DELETE FROM job_status
WHERE LOWER(COALESCE(job_type, '')) = 'backtest';


COMMIT;
```

---

## 1.3 Verify Standard Backtest Cleanup

```sql
SELECT 'performance_metrics' AS table_name, COUNT(*) AS remaining_rows
FROM performance_metrics

UNION ALL
SELECT 'trades', COUNT(*) FROM trades

UNION ALL
SELECT 'equity_curve', COUNT(*) FROM equity_curve

UNION ALL
SELECT 'pnl_calendar', COUNT(*) FROM pnl_calendar

UNION ALL
SELECT 'metrics', COUNT(*) FROM metrics

UNION ALL
SELECT 'backtest_jobs', COUNT(*)
FROM job_status
WHERE LOWER(COALESCE(job_type, '')) = 'backtest';
```

Expected result:

```text
performance_metrics    0
trades                 0
equity_curve           0
pnl_calendar           0
metrics                0
backtest_jobs          0
```

Your normal dashboard backtest count should also become `0` because the standard history is stored through `performance_metrics`.

---

# 2. FUNDED BACKTEST HISTORY

## Funded Backtest Tables

This cleanup removes history from:

- `funded_backtest_events`
- `funded_backtest_daily_snapshots`
- `funded_backtest_trades`
- `funded_backtest_phases`
- `funded_backtest_runs`

It preserves funded account configuration/profile/rules and all normal application data.

---

## 2.1 Check Funded Backtest Rows Before Cleanup

```sql
SELECT 'funded_backtest_runs' AS table_name, COUNT(*) AS rows
FROM funded_backtest_runs

UNION ALL
SELECT 'funded_backtest_phases', COUNT(*)
FROM funded_backtest_phases

UNION ALL
SELECT 'funded_backtest_trades', COUNT(*)
FROM funded_backtest_trades

UNION ALL
SELECT 'funded_backtest_daily_snapshots', COUNT(*)
FROM funded_backtest_daily_snapshots

UNION ALL
SELECT 'funded_backtest_events', COUNT(*)
FROM funded_backtest_events;
```

---

## 2.2 FUNDED BACKTEST CLEANUP QUERY

Run this query to clear only funded backtest history.

```sql
BEGIN;

-- ============================================================
-- FUNDED BACKTEST HISTORY CLEANUP
--
-- Child tables first.
-- Parent table last.
-- ============================================================


DELETE FROM funded_backtest_events;


DELETE FROM funded_backtest_daily_snapshots;


DELETE FROM funded_backtest_trades;


DELETE FROM funded_backtest_phases;


DELETE FROM funded_backtest_runs;


COMMIT;
```

---

## 2.3 Verify Funded Backtest Cleanup

```sql
SELECT 'funded_backtest_runs' AS table_name, COUNT(*) AS remaining_rows
FROM funded_backtest_runs

UNION ALL
SELECT 'funded_backtest_phases', COUNT(*)
FROM funded_backtest_phases

UNION ALL
SELECT 'funded_backtest_trades', COUNT(*)
FROM funded_backtest_trades

UNION ALL
SELECT 'funded_backtest_daily_snapshots', COUNT(*)
FROM funded_backtest_daily_snapshots

UNION ALL
SELECT 'funded_backtest_events', COUNT(*)
FROM funded_backtest_events;
```

Expected result:

```text
funded_backtest_runs             0
funded_backtest_phases           0
funded_backtest_trades           0
funded_backtest_daily_snapshots  0
funded_backtest_events           0
```

---

# 3. COMPLETE CLEANUP — RUN BOTH

If you want to remove **all saved backtest history**, run:

1. `STANDARD BACKTEST CLEANUP QUERY`
2. `FUNDED BACKTEST CLEANUP QUERY`

Both are intentionally kept separate so it is easy to understand which data is being removed.

---

# 4. Final Verification — Standard + Funded

```sql
SELECT 'standard_backtests' AS history_type, COUNT(*) AS remaining_rows
FROM performance_metrics

UNION ALL

SELECT 'funded_backtests', COUNT(*)
FROM funded_backtest_runs;
```

Expected:

```text
standard_backtests    0
funded_backtests      0
```

---

# 5. PostgreSQL Maintenance

After deleting the history:

```sql
VACUUM (ANALYZE);
```

This makes deleted PostgreSQL space reusable and refreshes query-planner statistics.

---

# 6. Important Data That Must Remain

The cleanup above does NOT intentionally delete:

```text
users
user_credits
credit_transactions
strategies
strategy_assets
strategy_runtime_presets
instruments
asset_classes
timeframes
market_data
broker accounts
live deployments
live orders
live positions
live trade logs
subscriptions
payments
pricing configuration
funded account profiles
funded account rules
funded risk tiers
alerts
notification configuration
```

---

# Recommended Usage

### Only standard backtest history is messy

Run:

```text
Section 1.2
```

### Only funded backtest history is messy

Run:

```text
Section 2.2
```

### You want a completely clean backtest history

Run:

```text
Section 1.2
then
Section 2.2
```

Then run:

```sql
VACUUM (ANALYZE);
```
