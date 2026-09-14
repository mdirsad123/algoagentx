# AlgoAgentX Live Deployment Delete Fix — 2026-09-14

The live-trading page showed `...deleteDeployment is not a function` before any DELETE request reached the API.

## Fix

- The page now calls `DELETE /api/v1/live/deployments/{deployment_id}` directly through the shared authenticated Axios instance.
- The shared `liveTradingApi.deleteDeployment()` method is still present.
- The duplicate legacy `app/lib/api/live-trading.ts` copy was synchronized with the canonical `lib/api/live-trading.ts` to avoid stale method definitions in future builds.

Backend safety remains unchanged: only deletable deployment states are accepted, and deployments with open positions or pending/placed orders are blocked from deletion.
