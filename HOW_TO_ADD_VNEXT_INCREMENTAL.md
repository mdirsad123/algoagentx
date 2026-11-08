# Future strategy version — incremental upgrade checklist

The live runner, retained-state cache, candle continuity guard, slow-path
fallback and worker architecture are **generic**. A strategy's internal
algorithms are **not automatically incremental**.

For V9.33 / new GBPUSD / new NAS100:

1. Preserve the published strategy source unchanged. Compute the normalized
   SHA256 from its exact DB `parameters.source_code` (strip exterior whitespace
   only if your DB's upload path does that). Save the source under a **new**
   versioned Python module. Never rewrite V9.32 or V6.4 modules.
2. Audit indicators, multi-timeframe aggregation, initialization/warmup,
   zone/swing states, one-position arbitration and entry/suppression ordering.
   Identify stable stateful components and calculations that still require
   rolling full-history replay. Do not silently shorten lookbacks.
3. Implement a separate adapter using the v1 interface
   `LIVE_INCREMENTAL_VERSION=1`, `start_live_incremental(generated)` and
   `on_closed_candle(candle) -> DataFrame` with the exact new candle Date,
   Position, SL, TP and reason. Fail on gaps, revised/duplicate candles, wrong
   source SHA, wrong instrument/timeframe or mismatched required warmup.
4. Add a source-pinned descriptor to
   `app/services/live/incremental_adapter_registry.py`; do not replace the
   V6.4/V9.32 fingerprints. Allow DEMO+monitor first, no LIVE accounts.
5. Add a corresponding full-history vs incremental parity tester on actual
   broker closed candles. Verify 80K rolling history (or the strategy's
   independently documented requirement), several positive/negative signals,
   stop/target/reason parity, next-open execution, weekend/session gaps,
   worker restarts and periodic rebases. Save a machine-readable report.
6. Benchmark end-to-end M5 candle close→decision. If it is late, HOLD; do not
   place a stale order. Only after human review enable orders on DEMO and
   eventually plan an independently approved LIVE release.
7. Keep the prior adapter and DB strategy records for rollback. Never turn a
   new SHA into a shortcut for reusing a prior adapter's trade logic.

**Current V9.32 hybrid:** Retains only the V3.5 horizontal controller. It
re-evaluates V4 trendline, V8/V9 source families, portfolio arbitration and
HTF vetoes per new bar. Future versions can reuse the registry/runner and
parity tool pattern; they may not reuse V9.32's strategy-specific math unless
independent matching tests establish identical semantics.

## Mandatory right-edge check for V9.33

Before authorizing orders, replay each historical signal time as the exact
latest closed candle with no future data. Original V9.32 fails this audit:
2026-11-04 17:30 UTC is BUY with later rows but HOLD on the right edge.
Fix the causal next-open boundary with a new version and revalidate both
research results and live signal existence; do not reuse V9.32 SHA.
