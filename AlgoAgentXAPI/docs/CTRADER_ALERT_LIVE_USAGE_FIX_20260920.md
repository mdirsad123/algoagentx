# cTrader connected-broker usage fix — 2026-09-20

This patch keeps MT5 unchanged and extends the existing provider-agnostic paths so a connected cTrader account can be used by Alerts and Live Trading.

## Fixed
- Alerts API no longer hard-rejects every provider except MT5.
- Alerts UI lists connected broker providers/accounts and loads exact symbols from the selected broker.
- cTrader adapter now exposes broker symbols through the common `get_symbols()` interface.
- Alert worker polls cloud/API broker quotes and publishes them to the same Redis quote bus used by the existing evaluator/notification pipeline. MT5 Agent push flow remains unchanged.
- cTrader adapter implements spot quote retrieval from Open API `ProtoOASubscribeSpotsReq/ProtoOASpotEvent`.
- Live Trading instrument picker loads exact symbols from the selected broker instead of depending only on Market Master.
- STANDARD deployment creation no longer sends `funded_profile_id=""`; backend also normalizes empty optional UUID fields to `None`.
- cTrader historical candles are implemented with `ProtoOAGetTrendbarsReq/Res` and the live candle service accepts cTrader as a candle provider.

## Runtime
The cTrader JSON transport needs the `websockets` dependency. It is now listed in both requirements.txt and pyproject.toml.

For Alerts, restart the alert worker after deploying this patch because the worker now contains the cloud-broker quote loop.
