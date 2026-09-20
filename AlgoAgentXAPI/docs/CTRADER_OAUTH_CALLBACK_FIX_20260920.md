# cTrader OAuth callback fix — 2026-09-20

## Root cause

cTrader's documented granting-access callback returns the authorization code as
`?code=...`. It does not document an OAuth `state` callback parameter and the
authorization page may drop arbitrary `state`.

AlgoAgentX previously required both `code` and `state`:

    if not code or not state:
        Missing OAuth code or state

That caused a valid cTrader authorization to be rejected before token exchange.

## Fix

- Keep a cryptographically-random server-side OAuth state row.
- Store the same nonce in a short-lived HttpOnly, SameSite=Lax callback cookie.
- The frontend cTrader connect request uses `withCredentials: true` so the cookie
  is accepted when frontend and API run on different localhost ports.
- Callback accepts the cTrader `code`, recovers state from either the query
  parameter (if ever supplied) or the callback cookie, validates it against the
  database row, then exchanges the code immediately.
- Cookie is deleted after callback success/failure.
- cTrader authorization URL now follows the documented parameters and adds
  `product=web`; it no longer depends on cTrader echoing a non-documented state
  parameter.

## Required local redirect URI

    http://localhost:8000/api/v1/broker-accounts/ctrader/callback

The URI configured in the cTrader Open API portal must match exactly.

## Test flow

1. Start API on localhost:8000 and web on localhost:3000.
2. Sign in to AlgoAgentX.
3. Brokers -> cTrader -> Save & Open cTrader OAuth.
4. Select accounts and Allow access.
5. Browser should return to API callback with `?code=...`.
6. API exchanges code for token and redirects to:
   `/brokers?broker=ctrader&connected=true`
7. Click Sync to fetch linked cTrader accounts.

cTrader authorization codes are short-lived, so do not pause on the callback
flow before allowing access.
