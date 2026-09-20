# Live Trading: +10s runner, 1s retry, fresh cTrader equity

## Auto Runner
- First attempt = exact timeframe close +10 seconds.
- If the expected closed candle is not stored, retry every 1 second.
- Maximum active broker refresh attempts per candle = 10.
- The local candle DB is checked every scheduler pass, so a candle already stored by
  another request is processed immediately.
- Existing duplicate-signal DB guard and broker idempotency key remain unchanged.
- Next Scheduled Run is persisted as the next timeframe close +10 seconds.

## cTrader capital
- Account balance is fetched from ProtoOATraderRes on every broker sync.
- Unrealized PnL is fetched from ProtoOAGetPositionUnrealizedPnLReq/Res.
- Equity = current balance + sum(current net unrealized PnL).
- The fresh balance/equity is persisted into broker metadata used by live order sizing
  and the deployment Broker Summary.
- Pre-trade broker sync remains mandatory, so 1% risk sizing uses current broker equity,
  not the old OAuth/account-selection balance.

## cTrader candle latency
- Market-data requests now use the selected account's known DEMO/LIVE environment
  directly instead of opening an additional account-discovery connection first.
