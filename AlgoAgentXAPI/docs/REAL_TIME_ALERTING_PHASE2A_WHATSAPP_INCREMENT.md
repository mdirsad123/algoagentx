# AlgoAgentX Phase 2A — Distance Fix + Twilio WhatsApp Increment

This is a small additive improvement on top of the working Phase 2A approaching-alert system. It is **not** the full original Phase 4.

## What changed

- Active Alerts `Distance` now works for both target alerts and zones.
- For a zone, distance means the distance from the latest price to the nearest zone boundary:
  - below zone: `zone_low - last_price`
  - above zone: `last_price - zone_high`
  - inside zone: `0`
- Added Twilio WhatsApp as an optional notification channel.
- Telegram remains supported and can be used alone or together with WhatsApp.
- Existing `notification_deliveries` is reused; there is no new table/migration for WhatsApp.
- The Alerts page now includes WhatsApp setup, test, per-alert ON/OFF, and channel delivery statuses in history.

## Why the old Distance column was empty

The Phase 2A frontend only calculated distance when `target_price` existed. `ENTERING_ZONE` alerts have `target_price = NULL`, so the UI displayed `—`. The new frontend calculates distance to the nearest zone boundary.

## Environment variables

Add these to the API/alert-worker environment (`.env.dev` and/or `.env.prod` as appropriate):

```env
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_FROM_WHATSAPP_NUMBER=
TWILIO_TO_WHATSAPP_NUMBER=
TWILIO_CONTENT_SID=
TWILIO_TIMEOUT_SECONDS=10
```

Use E.164 numbers such as `+919876543210`. The service adds the `whatsapp:` prefix automatically.

`TWILIO_TO_WHATSAPP_NUMBER` is only an optional owner/admin fallback. A user can save a destination number from the Alerts page.

## Twilio Content Template mode

The older reference code uses a Twilio `content_sid`. AlgoAgentX supports the same model.

When `TWILIO_CONTENT_SID` is configured, these variables are sent:

```text
1 = symbol
2 = condition/event
3 = target or zone
4 = current/trigger price
```

Example:

```text
1 = XAUUSDm
2 = Approaching Zone
3 = 4400.00 - 4402.00
4 = 4398.25
```

Your approved Twilio template should use those four placeholders in that order.

If `TWILIO_CONTENT_SID` is blank, AlgoAgentX sends a normal `Body` message. WhatsApp/Twilio session/template policies still apply, so a body message may be rejected outside the allowed customer-service session.

## No new Python package

The integration uses the project's existing `aiohttp` dependency and calls the Twilio Messages REST API directly. The `twilio` Python package is not required.

## API endpoints

```text
GET  /api/v1/alerts/whatsapp-channel
PUT  /api/v1/alerts/whatsapp-channel
POST /api/v1/alerts/test-whatsapp
```

Existing alert create/update payloads now allow:

```json
{
  "telegram_enabled": true,
  "whatsapp_enabled": true
}
```

## Testing

1. Add Twilio variables to the environment used by both the API and `alert_worker`.
2. Restart API and alert worker.
3. Open Alerts.
4. Confirm the WhatsApp health card says `Configured`.
5. Enter the destination number, e.g. `+919876543210`.
6. Click **Save Number**.
7. Click **Test WhatsApp**.
8. Create a close XAUUSDm approach/zone alert with WhatsApp ON.
9. Trigger the approach event.
10. Verify Telegram and/or WhatsApp independently.
11. Check Alert History: `TG SENT` and `WA SENT` are displayed separately when both channels are enabled.

## Production Docker

No new container is required. The existing `alert_worker` dispatches both channels.

After updating APP/API source and `.env.prod`:

```powershell
docker compose --env-file .env.prod -f docker-compose.yml up -d --build api alert_worker web
```

No Alembic migration is required for this incremental update because `whatsapp_enabled`, `whatsapp_status`, `notification_deliveries`, and `user_notification_channels` already exist in the current alert schema.

## Reliability behavior

- Confirmed temporary Twilio failures (HTTP 429/5xx) use the existing bounded retry pattern.
- Ambiguous timeouts after a send may have reached Twilio are not blindly retried, reducing duplicate WhatsApp notifications.
- A WhatsApp failure does not block Telegram delivery.
- Telegram remains the primary timing metric when Telegram and WhatsApp are both enabled; channel-specific status and provider response are persisted in `notification_deliveries`.

## Phase 3 recommendation

Do not implement the full Phase 3 just because it exists in the roadmap. For the current workflow, Phase 1 + Phase 2A + Telegram/WhatsApp already covers:

```text
important level/zone
→ approaching warning
→ entered/reached alert
→ phone notification
→ manual chart review
```

Only add a small Phase 3A later if you specifically want:

```text
zone entered
→ wait for 5m bullish/bearish rejection candle
→ send a second confirmation alert
```

That confirmation feature is useful, but it should remain separate from the fast tick-based level/zone alerts.
