-- OPTIONAL EMERGENCY REPAIR -- CHANGES DATA. NOT needed if the V6 UI works.
-- Backup PROD PostgreSQL first. Review the read-only verification SQL first.
-- Replace the UUID below with the exact BTCUSD cTrader primary feed_id from
-- VERIFY_MARKET_DATA_CANONICAL_V6.sql. The all-zero UUID intentionally fails.
-- This writes ONLY missing BTCUSD M5 timestamps. Existing OHLCV never change.
-- The source must already be Primary + publish_approved from the UI.
BEGIN;
SET LOCAL TIME ZONE 'UTC';

DO $$
DECLARE
    selected_id uuid := '00000000-0000-0000-0000-000000000000';
    approved_count int;
BEGIN
    IF to_regclass('public.market_data_canonical_provenance') IS NULL THEN
        RAISE EXCEPTION 'Missing V5 provenance table. Apply the existing V5 migration first.';
    END IF;
    SELECT count(*) INTO approved_count
    FROM market_data_sync_configs c
    JOIN instruments i ON i.id=c.instrument_id
    WHERE c.id = selected_id AND upper(i.symbol)='BTCUSD'
      AND c.provider = 'CTRADER' AND c.timeframe='5m'
      AND c.is_primary AND c.publish_approved AND NOT c.is_archived;
    IF approved_count <> 1 THEN
        RAISE EXCEPTION 'No approved BTCUSD M5 cTrader Primary at selected feed UUID. Check the UUID and UI Publish Missing approval.';
    END IF;
END $$;

WITH selected AS (
    SELECT c.id, c.instrument_id, c.timeframe
    FROM market_data_sync_configs c
    JOIN instruments i ON i.id=c.instrument_id
    WHERE c.id='00000000-0000-0000-0000-000000000000'::uuid
      AND upper(i.symbol)='BTCUSD' AND c.provider='CTRADER'
      AND c.timeframe='5m' AND c.is_primary AND c.publish_approved
      AND NOT c.is_archived
), inserted AS (
    INSERT INTO market_data (instrument_id,timeframe,"timestamp",open,high,low,close,volume)
    SELECT s.instrument_id, s.timeframe, fc."timestamp" AT TIME ZONE 'UTC',
           round(fc.open,5),round(fc.high,5),round(fc.low,5),round(fc.close,5),fc.volume
    FROM market_data_feed_candles fc JOIN selected s ON s.id=fc.feed_id
    WHERE fc."timestamp" + interval '5 minutes' <= now()
      AND fc.open>0 AND fc.low>0 AND fc.high>=greatest(fc.open,fc.close,fc.low)
      AND fc.low<=least(fc.open,fc.close,fc.high) AND fc.volume>=0
      AND (extract(epoch FROM fc."timestamp")::bigint % 300)=0
    ON CONFLICT (instrument_id,timeframe,"timestamp") DO NOTHING
    RETURNING instrument_id,timeframe,"timestamp"
), audited AS (
    INSERT INTO market_data_canonical_provenance
      (instrument_id,timeframe,"timestamp",feed_id)
    SELECT i.instrument_id,i.timeframe,i."timestamp" AT TIME ZONE 'UTC', s.id
    FROM inserted i CROSS JOIN selected s
    ON CONFLICT (instrument_id,timeframe,"timestamp") DO NOTHING
    RETURNING instrument_id
)
SELECT (SELECT count(*) FROM inserted) AS newly_added_backtest_candles,
       (SELECT count(*) FROM audited) AS provenance_records;
COMMIT;
