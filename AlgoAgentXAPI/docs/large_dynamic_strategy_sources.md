# Large dynamic strategy sources

## Scope and audit (2026-11-07)

The checked-out history already removed the 250,000-character rejection in
commit `0d5f077`. The current loader accepts source without a character/byte
ceiling. No replacement source-size threshold was introduced.

Audited application paths:

- Admin editor create/edit textareas and JSON requests: no source maxlength,
  slicing, or source-file size gate found. Image attachment limits are unrelated
  and remain in place.
- Admin create/update Pydantic models: optional unrestricted source strings;
  nested parameters also supported. Existing whitespace normalization remains.
- Save/duplicate/version metadata: full source and SHA-256; Strategy.parameters
  uses JSONB. No schema change needed.
- Validation, backtest service, shared registry, and live full dry-test:
  use the shared dynamic loader; no separate source-length restriction found.
- No application request-body ceiling was found in the checked-in frontend/API
  configuration. External reverse proxy/ingress limits were not inspected or
  changed. The deployment guide's generic request-body limit is not a strategy
  validator and was not disabled globally.

## Loader changes

The exact AST that passes the existing security visitor is compiled once, then
released before module execution. All banned imports, calls, and attributes,
safe builtins, class selection, parameter filtering, and source-based caching
remain intact. Loading is serialized to avoid simultaneous cache misses and
temporary `sys.modules` registration races; strategy generation is not locked.
Recoverable MemoryError/RecursionError during validation/loading is translated
to DynamicStrategyLoadError without retry or static-strategy substitution.

## Resource boundaries and limitations

No source length can guarantee execution fits RAM. Existing backtest container
memory/swap/CPU limits, single-child execution, child recycling, task time limit,
and durable recovery are unchanged. Full live dry tests remain on their separate
queue. The 64-entry loader cache remains bounded by entry count, not bytes.

This change is not a new OS sandbox or an OOM-proof execution system. Python
MemoryError handling cannot catch SIGKILL or every compiler crash. In particular,
admin Verify currently invokes BacktestService in-process, and admin sandbox
submission retains its existing background fallback. Those paths do not acquire
the dedicated backtest container's limits merely by using this loader. Live
runner and dry-test host capacity still require deployment-level supervision.
No per-request process isolation, global process resource limits, or trading
runner restarts were added in this targeted repair.

## Verification

`tests/test_dynamic_strategy_large_source.py` covers >250K and >1M characters,
multibyte source, a >250K executable AST, trailing security/syntax failures,
single AST compilation, concurrent cache behavior, resource-error cleanup,
admin create/update/nested payload serialization and duplication, both backtest
lookup modes, engine trade/equity/SL/TP/warmup parity, dry-run signal-generation
helpers, and preservation of worker settings.

These are offline tests. Database calls are isolated; JSON round trips do not
constitute PostgreSQL persistence integration tests. No production strategy,
market data, broker order, database schema, or runtime setting is changed.

## Deployment caveat

An instance still emitting the exact old `Strategy source code is too large`
message is not explained by this checked-out loader. Verify its loaded module
path and image/revision. Deploy the updated backend artifact to every service
that imports the loader using the normal controlled release process. Updating
only the frontend or a file outside the running image is insufficient. Restart
live runners only through the operational maintenance procedure, not during an
active trade cycle. No deployment/restart was performed by this repair.