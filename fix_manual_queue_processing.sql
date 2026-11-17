-- AlgoAgentX: permit durable in-flight status for MANUAL signals only.
-- This preserves the exact current CHECK expression for all other signals.
-- Execute once against the EXISTING algoagentx_prod PostgreSQL database.
-- The DO block is atomic: any failure rolls back the original constraint.
DO $manual_signal_status_fix$
DECLARE
    previous_check text;
    constraint_oid oid;
BEGIN
    SELECT c.oid, pg_get_expr(c.conbin, c.conrelid)
      INTO constraint_oid, previous_check
    FROM pg_constraint AS c
    WHERE c.conrelid = 'public.live_signals'::regclass
      AND c.conname = 'live_signals_status_check'
      AND c.contype = 'c';

    IF constraint_oid IS NULL OR previous_check IS NULL THEN
        RAISE EXCEPTION 'Expected CHECK constraint public.live_signals.live_signals_status_check not found. No changes made.';
    END IF;

    IF position('PROCESSING' in previous_check) > 0 THEN
        RAISE NOTICE 'Constraint already mentions PROCESSING; inspect the existing expression before making further changes. No changes made.';
        RETURN;
    END IF;

    -- Same constraint name, with only one additional permitted combination.
    EXECUTE 'ALTER TABLE public.live_signals DROP CONSTRAINT live_signals_status_check';
    EXECUTE format(
        'ALTER TABLE public.live_signals ADD CONSTRAINT live_signals_status_check CHECK ((%s) OR ((source)::text = %L AND (status)::text = %L))',
        previous_check, 'MANUAL', 'PROCESSING'
    );
    RAISE NOTICE 'Manual PROCESSING signal status permitted; original constraint rules preserved.';
END
$manual_signal_status_fix$;

SELECT conname, pg_get_constraintdef(oid) AS effective_check
FROM pg_constraint
WHERE conrelid = 'public.live_signals'::regclass
  AND conname = 'live_signals_status_check';
