BEGIN;

ALTER TABLE IF EXISTS job_status
    ADD COLUMN IF NOT EXISTS debit_txn_id VARCHAR(64);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.table_constraints tc
        WHERE tc.table_schema = current_schema()
          AND tc.table_name = 'job_status'
          AND tc.constraint_name = 'job_status_debit_txn_id_fkey'
    ) THEN
        ALTER TABLE job_status
            ADD CONSTRAINT job_status_debit_txn_id_fkey
            FOREIGN KEY (debit_txn_id) REFERENCES credit_transactions(id) ON DELETE SET NULL;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_job_status_debit_txn_id ON job_status (debit_txn_id);

COMMIT;
