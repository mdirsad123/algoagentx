# AlgoAgentX Twilio WhatsApp Templates V2

Use **two Twilio Content Templates** so the same backend can format both approach alerts and reached/triggered alerts cleanly.

## 1) Approaching template

Suggested Twilio template name: `algoagentx_alert_approaching_v2`

Recommended body:

```text
🟡 *AlgoAgentX Approaching Alert*

Symbol: *{{1}}*
Status: *{{2}}*
Level / Zone: *{{3}}*
Current Price: *{{4}}*
Distance: *{{5}}*
Direction: *{{6}}*
Triggered: *{{7}} IST*
Alert ID: *{{8}}*

Please review the chart before taking any trading action.
```

Variable mapping:

- `{{1}}` symbol, e.g. `XAUUSDm`
- `{{2}}` status, e.g. `Approaching Zone` or `Approaching Target`
- `{{3}}` target or zone, e.g. `4320.00 - 4325.00`
- `{{4}}` current price
- `{{5}}` distance to target/zone boundary
- `{{6}}` direction, e.g. `From Above` / `From Below`
- `{{7}}` IST timestamp
- `{{8}}` AlgoAgentX alert event ID

## 2) Triggered / reached template

Suggested Twilio template name: `algoagentx_alert_triggered_v2`

Recommended body:

```text
🔴 *AlgoAgentX Price Alert*

Symbol: *{{1}}*
Status: *{{2}}*
Level / Zone: *{{3}}*
Current Price: *{{4}}*
Triggered: *{{5}} IST*
Alert ID: *{{6}}*

Price condition has been reached. Please review the chart before taking any trading action.
```

Variable mapping:

- `{{1}}` symbol
- `{{2}}` status, e.g. `Entering Zone`, `Leaving Zone`, `Target Hit`, or another configured main alert condition
- `{{3}}` target or zone
- `{{4}}` current price
- `{{5}}` IST timestamp
- `{{6}}` AlgoAgentX alert event ID

## Environment configuration

Add the following to the **API / alert-worker environment**, not to the browser frontend:

```env
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_secret_token
TWILIO_FROM_WHATSAPP_NUMBER=+14155238886
TWILIO_TO_WHATSAPP_NUMBER=+91xxxxxxxxxx

TWILIO_CONTENT_SID_APPROACHING=HXxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_CONTENT_SID_TRIGGERED=HXxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Optional legacy fallback. Leave blank after V2 templates are working.
TWILIO_CONTENT_SID=
TWILIO_TIMEOUT_SECONDS=10
```

Use the same variable names in `.env.dev`, `.env.prod`, Docker Compose environment, or your deployment secret manager—wherever the API/alert worker actually loads environment variables.

## Routing behavior

- `APPROACHING_ZONE` and `APPROACHING_TARGET` use `TWILIO_CONTENT_SID_APPROACHING`.
- All main/reached alert events use `TWILIO_CONTENT_SID_TRIGGERED`.
- If a dedicated SID is missing, the backend falls back to legacy `TWILIO_CONTENT_SID`.
- If no SID is configured, it sends a normal `Body` message, subject to WhatsApp/Twilio session rules.

After changing environment values, restart both the API and any alert worker process/container that imports the API settings.
