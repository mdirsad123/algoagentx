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
  "POLL_INTERVAL_SECONDS": 5,
  "ENABLE_ORDER_EXECUTION": false,
  "MT5_PATH": "",
  "DEFAULT_DEVIATION": 20,
  "AGENT_VERSION": "0.1.0"
}
```

`ENABLE_ORDER_EXECUTION` is intentionally `false` by default. Keep it disabled until you confirm heartbeat and demo testing. No withdrawal permissions are required.

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
