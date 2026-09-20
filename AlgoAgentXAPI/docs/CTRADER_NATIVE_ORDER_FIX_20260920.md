# cTrader native DEMO order transport + live symbol dropdown fix

## Why orders were rejected

The old adapter still required `CTRADER_DEMO_ORDER_URL`, an external REST bridge. OAuth, account sync,
quotes and candles were native Open API, but order placement was not.

This update removes that dependency for cTrader DEMO orders and sends `ProtoOANewOrderReq` directly
through the same cTrader JSON WebSocket transport.

## Important: reconnect once

The previous OAuth URL requested `scope=accounts`, which is view-only. cTrader requires `scope=trading`
for `ProtoOANewOrderReq` and `ProtoOAClosePositionReq`.

After installing this update:

1. Brokers -> cTrader -> Reconnect
2. Approve the cTrader access page again
3. Click Sync
4. Confirm the broker card is connected
5. Test on a DEMO account first

## Native execution details

- MARKET entry: ProtoOANewOrderReq (2106)
- Execution result: ProtoOAExecutionEvent (2126)
- Order errors: ProtoOAOrderErrorEvent (2132)
- Close position: ProtoOAClosePositionReq (2111)
- Open positions/orders sync: ProtoOAReconcileReq/Res (2124/2125)
- Full symbol contract data: ProtoOASymbolByIdReq/Res (2116/2117)
- AlgoAgentX lot size is converted to cTrader protocol volume using each symbol's `lotSize`.
- MARKET SL/TP is sent as relativeStopLoss/relativeTakeProfit because cTrader does not support absolute
  stopLoss/takeProfit on a MARKET request.

LIVE cTrader order placement remains intentionally disabled; this patch enables DEMO native execution.
