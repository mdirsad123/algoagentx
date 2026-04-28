# Phase 14 - Upstox OAuth Broker Connection

- Fixed admin broker provider enable/disable URL wiring.
- Added broker_oauth_states table/model.
- Added Upstox OAuth connect URL and callback routes.
- Added Upstox adapter for OAuth token exchange and profile/test connection.
- Tokens are encrypted and never returned to the frontend.
- Upstox orders remain disabled until a later phase.
- LIVE trading remains disabled.
