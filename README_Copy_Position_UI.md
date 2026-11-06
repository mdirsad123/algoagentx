# AlgoAgentX TradeLocker: copy-trading open positions vs order history (UI only)

## What the screenshots show
- Copy Trading Managed Positions already contains only `OPEN` records, and shows one 0.01 SHORT position.
- Copy Trading Orders includes all recent copy order records; the 02:01 BUY and 02:10 SELL have different broker order IDs. Two historical fills do **not** prove two concurrent open positions or duplicate execution.
- `Entries Today: 2` counts entry-order history for the current day, **not** the number of currently open positions. Keep these history rows to preserve audit records.

## What this patch changes
One frontend file only: `AlgoAgentXApp/app/(user)/live-trading/[deploymentId]/page.tsx`
- Renames Copy Trading Managed Positions to **Copy Trading Open Positions (N)**.
- Renames Copy Trading Orders to **Copy Trading Order History** with clearer help text.
- Collapses historical orders by default; click **Show History** to expand. The live open-position list remains visible.
- Leaves all broker execution, copy routing, reconciliation, database rows, and max-position checks unchanged.

## Install
Merge the `.patch` with your current frontend version, or copy the included updated `page.tsx` **only if** your existing page matches the previous source release `AlgoAgentX_TradeLocker_Position_Copy_Safety_20261010.zip`.

From project root, to recreate only frontend:

```powershell
docker compose --env-file .env.prod -f docker-compose.yml up -d --build --force-recreate --no-deps web
```

## Live safety observations
The screenshots show `SL=0` and `TP=0` in the position sync for both primary and copy while earlier orders show stop values. This may be a display/mapping issue **or** missing broker-side protections. Check actual SL and TP directly in TradeLocker; do not assume protected stops until confirmed. Also `Current` matching entry could signal stale market-price sync.

This UI patch does **not** establish that copy-trading orders/reconciliation are fully safe, nor does it close any broker positions.
