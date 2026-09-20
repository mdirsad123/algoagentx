# cTrader connection fix — 2026-09-20

This patch removes the hard dependency on the unconfigured `CTRADER_ACCOUNTS_URL`, `CTRADER_ACCOUNT_INFO_URL`, and `CTRADER_SYMBOLS_URL` REST bridge for the cTrader connection/sync flow.

The backend now uses cTrader Open API's cloud JSON WebSocket transport on port 5036 for:

- application authentication
- linked cTrader account discovery
- trading-account authentication
- trader/account details and balance
- asset/currency lookup
- symbol-list sync

Legacy REST bridge URLs are still supported as optional overrides. MT5 code was not changed. cTrader order execution remains intentionally separate from this connection/sync patch.

Validation performed: Python compile-all passed for the complete `app` package. A real OAuth/account test still requires valid cTrader application credentials and an authorized cTrader account at runtime.
