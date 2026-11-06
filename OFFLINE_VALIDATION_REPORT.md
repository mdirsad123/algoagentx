# Offline validation report

- Root cause: `algoagentx(5).zip` had **62** `REPLACE_WITH_EXISTING_LOCAL_VALUE` env settings, including seven mandatory typed INT/BOOL settings. Both workers abort during Pydantic Settings construction.
- Confirmed current config parser works with the valid original settings from `algoagentx(4).zip`: `CONFIG_OK True True False False`.
- 38 targeted pytest checks passed: candle boundary timing, candle catch-up classification, adapter registry, V6.4 gate, runner cache.
- 17 additional pytest checks passed: live order de-duplication, optional safety, TradeLocker candle-history consistency, every-candle timing.
- Python compile on packaged code passed; source SHA for `strategy_runner.py` and retained-state engine matched the earlier working archive.
- The front-end artwork was preserved; credentials, historical screenshots, private keys, Docker volumes, real `.env.prod` and runtime files were excluded.
- No real Docker/TradeLocker broker test or 80K parity replay was performed in this repair cycle. Live broker order behavior and signal parity are unverified.

**Operational trade-off:** Strict gap blocking is disabled to restore the previously observed functioning runner. After session breaks, old candles may remain un-evaluated; `RUNNER_CANDLE_GAP` remains an honest diagnostic. Auto Trade state in the database/UI is not changed; the stale-order guard blocks stale trade execution even if Auto Trade is ON.
