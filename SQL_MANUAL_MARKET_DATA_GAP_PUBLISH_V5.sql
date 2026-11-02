-- Run ONCE against your intended PostgreSQL database, after a verified backup.
-- Safe / additive: existing market_data OHLCV is not updated or deleted.
-- If you apply this manually, do NOT also execute the corresponding Alembic upgrade.
BEGIN;
ALTER TABLE public.market_data_sync_configs
  ADD COLUMN IF NOT EXISTS is_archived boolean NOT NULL DEFAULT false;
CREATE TABLE IF NOT EXISTS public.market_data_canonical_provenance (
    instrument_id integer NOT NULL REFERENCES public.instruments(id),
    timeframe varchar(20) NOT NULL,
    "timestamp" timestamptz NOT NULL,
    feed_id uuid NOT NULL REFERENCES public.market_data_sync_configs(id) ON DELETE RESTRICT,
    published_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (instrument_id, timeframe, "timestamp")
);
CREATE INDEX IF NOT EXISTS ix_market_canonical_provenance_feed
  ON public.market_data_canonical_provenance(feed_id, "timestamp");
COMMIT;
