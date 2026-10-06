# Live Warm-up + Runtime Contract Follow-up Fix — 06 Oct 2026

## Root causes confirmed

1. `CTRADER_BOOTSTRAP` intentionally fetched 300 bars and excluded the forming M5 candle, so a fresh deployment displayed 299 closed candles.
2. V1.37 dry-run rejected the deployment before history warm-up because the live deployment inherited generic runtime defaults: opposite exit ON, partial exit OFF, 1.0R, 50%.
3. Deployment partial-exit DB columns were authoritative for the position manager, so merely fixing the strategy preset was not sufficient.
4. cTrader Open API websocket establishment showed transient opening-handshake timeouts after rebuild.

## Fixes

- Live runtime resolver overlays the exact executable strategy runtime contract after presets/deployment/user overrides.
- Deployment creation materializes contract-backed RR/max-open/partial-exit values into the deployment DB row.
- Refresh Candles now performs strategy-aware history warm-up first (V1.37=20,000, V3.5=1,000), then refreshes the latest 300 bars.
- cTrader large-history websocket establishment retries up to 3 times for transient handshake failures.
- Frontend Refresh Candles reports required/stored readiness rather than only the small latest refresh count.

No strategy signal logic was changed.
