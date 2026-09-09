# AlgoAgentX MT5 Agent

This Windows agent connects your local MetaTrader 5 terminal to the AlgoAgentX API. The API can run in Docker/Linux; only this agent needs Windows + MetaTrader 5.

## Setup

1. Install MetaTrader 5 on your Windows PC or VPS.
2. Login to your broker account inside MetaTrader 5.
3. Enable Algo Trading in MetaTrader 5.
4. In AlgoAgentX web app, go to **Brokers > MT5 Agent Setup** and generate an Agent Token.
5. Extract this folder to your Windows PC/VPS.
6. Copy `config.json.example` to `config.json`.
7. Paste your token into `AGENT_TOKEN`.
8. Set `API_BASE_URL`:
   - Local dev: `http://localhost:8000`
   - Production: `https://your-api-domain.com`
9. Install and run:

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## Config

```json
{
  "API_BASE_URL": "http://localhost:8000",
  "AGENT_TOKEN": "paste-your-agent-token-here",
  "POLL_INTERVAL_SECONDS": 1,
  "COMMAND_POLL_INTERVAL_SECONDS": 1,
  "HEARTBEAT_INTERVAL_SECONDS": 5,
  "ALERT_QUOTE_INTERVAL_MS": 250,
  "ALERT_SYMBOL_REFRESH_SECONDS": 1,
  "ENABLE_ORDER_EXECUTION": false,
  "MT5_PATH": "",
  "DEFAULT_DEVIATION": 20,
  "AGENT_VERSION": "0.4.1-alerts-symbols"
}
```

`ENABLE_ORDER_EXECUTION` is intentionally `false` by default. Keep it disabled until you confirm heartbeat and demo testing. No withdrawal permissions are required.

## Real-time alert requirements

Phase 1 alerts require this updated agent to stay running with MetaTrader 5 open and logged in to the **same broker account whose Agent Token was generated in AlgoAgentX**. The agent:

- polls AlgoAgentX for active alert symbols,
- resolves exact MT5 broker symbols such as `XAUUSD.x`, `XAUUSDm`, or `BTCUSD.x`,
- pushes live quotes to the API about every `ALERT_QUOTE_INTERVAL_MS` while alerts are active, and
- responds to `FETCH_SYMBOLS` so the Alerts page can show the actual instruments available in that broker terminal.

When working correctly, the terminal prints lines such as:

```text
Active alert symbols: ['XAUUSD.X']
Alert quotes sent | accepted=1 | sample=XAUUSD.X resolved=XAUUSD.x price=4415.23
```

If you only see heartbeat lines and never see `Active alert symbols` / `Alert quotes sent`, verify that the alert uses the same broker account/token and that the alert is ACTIVE.

## Candle refresh troubleshooting

If AlgoAgentX shows `Stored 0 broker candles` or no candles are returned from MT5:

1. Keep MetaTrader 5 open and logged in to the correct broker account.
2. In MT5 **Market Watch**, right click and choose **Show All**.
3. Open the exact symbol chart once, for example `XAUUSDm` on `M5`.
4. Wait a few seconds for MT5 to download history.
5. Click **Refresh Candles** again in AlgoAgentX.

The agent supports `FETCH_RATES` commands for `M1`, `M5`, `M15`, `M30`, `H1`, `H4`, and `D1`. The currently forming candle is skipped by default so strategies run on closed broker candles only.


## PnL sync notes

AlgoAgentX reads MT5 PnL from real broker data; it does not fake PnL from balance differences.

- Keep MetaTrader 5 open and logged in to the same account linked in AlgoAgentX.
- Open positions are sent in the agent heartbeat as `positions` and `positions_count`.
- Unrealized PnL comes from `mt5.positions_get()` open position profit.
- Today realized PnL uses `mt5.history_deals_get()` from today UTC day start.
- If PnL remains zero, check MT5 **Account History** for current-day closed deals and confirm the symbol matches the deployment broker symbol such as `XAUUSDm`.

## Build Windows EXE

```bat
build_windows_exe.bat
```

The EXE will be created under `dist` if PyInstaller is installed successfully.

## Troubleshooting

- `MT5_PYTHON_PACKAGE_MISSING`: run `pip install -r requirements.txt` on Windows.
- `TERMINAL_NOT_FOUND_OR_NOT_STARTED`: start MetaTrader 5, or set `MT5_PATH` to your terminal64.exe path.
- `TERMINAL_CONNECTED_LOGIN_REQUIRED`: login to your MT5 broker account in the terminal.
- Token error: generate a new token in AlgoAgentX and paste it into `config.json`.
