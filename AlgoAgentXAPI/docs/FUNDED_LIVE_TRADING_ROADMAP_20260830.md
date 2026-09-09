# Funded Live Trading Roadmap — 2026-08-30

## Recommendation

Do not create a third execution mode named `FUNDED`.

Use:

- `mode = DEMO` or `LIVE` for execution environment
- optional `funded_profile_id` for prop/funded-account rule enforcement

A funded MT5 account is still a broker LIVE/REAL account; funded rules are a policy layer on top.

## Current blocker in this codebase

`app/services/live/risk_manager.py` currently rejects every deployment whose mode is `LIVE` with `LIVE mode is not enabled yet`.

That safety block should remain until all of the following are implemented and verified:

1. MT5 heartbeat reports actual terminal account mode (DEMO/CONTEST/LIVE). The updated MT5 Agent now includes `metadata.account_mode` and `metadata.account_trade_mode`.
2. API verifies deployment mode matches the connected terminal account mode.
3. Admin `live_trading_enabled` is an explicit execution gate.
4. Strategy is LIVE-approved.
5. User/deployment live approval is explicit, not implicitly assumed.
6. Order idempotency, SL/TP placement, reconnect handling, broker position reconciliation, and kill switch are verified in DEMO.

## Funded policy layer

Add to `strategy_deployments` later:

- `funded_profile_id UUID NULL`
- `funded_guard_enabled BOOLEAN DEFAULT FALSE`
- `funded_phase_number INTEGER NULL`
- `funded_account_start_balance NUMERIC NULL`
- `funded_daily_start_equity NUMERIC NULL`
- `funded_high_watermark_equity NUMERIC NULL`
- `funded_guard_status VARCHAR(32)`
- `funded_guard_reason TEXT`

Before each new entry, calculate from real broker balance/equity:

- daily drawdown against profile rule/mode
- max drawdown against profile rule/mode
- current phase profit target
- minimum trading days (informational / phase gating)
- risk tier from funded profile
- optional consistency/payout constraints

If a hard loss boundary is reached, block NEW entries and optionally pause the deployment. Do not depend only on local realized PnL; broker equity is the source of truth for funded drawdown.

## Recommended sequence

1. Fix/measure M5 candle ingestion latency in DEMO.
2. Run V1.16 DEMO auto-runner for at least several trading days.
3. Verify every signal is processed once and SL/TP matches strategy output.
4. Add funded live guard layer.
5. Test the funded guard against a DEMO MT5 account using a funded profile.
6. Only then enable real LIVE execution behind explicit admin/user gates.
