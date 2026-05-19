from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from agent_client import AgentApiClient
from mt5_client import MT5Client

CONFIG_PATH = Path(__file__).with_name("config.json")
EXAMPLE_CONFIG_PATH = Path(__file__).with_name("config.json.example")


def _to_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def load_config() -> dict[str, Any]:
    if CONFIG_PATH.exists():
        with CONFIG_PATH.open("r", encoding="utf-8") as f:
            config = json.load(f)
    else:
        print("config.json not found. Creating it now.")
        api_base = input("API_BASE_URL [http://localhost:8000]: ").strip() or "http://localhost:8000"
        token = input("AGENT_TOKEN: ").strip()
        config = {
            "API_BASE_URL": api_base,
            "AGENT_TOKEN": token,
            "POLL_INTERVAL_SECONDS": 5,
            "ENABLE_ORDER_EXECUTION": False,
            "MT5_PATH": "",
            "DEFAULT_DEVIATION": 20,
            "AGENT_VERSION": "0.1.0",
        }
        with CONFIG_PATH.open("w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        print(f"Saved {CONFIG_PATH}. You can edit it any time and restart the agent.")

    # Environment variables can override config.json for VPS/service usage.
    for key in ["API_BASE_URL", "AGENT_TOKEN", "POLL_INTERVAL_SECONDS", "ENABLE_ORDER_EXECUTION", "MT5_PATH", "DEFAULT_DEVIATION", "AGENT_VERSION"]:
        if os.getenv(key) is not None:
            config[key] = os.getenv(key)
    return config


def main() -> None:
    config = load_config()
    api_base_url = str(config.get("API_BASE_URL") or "http://localhost:8000").rstrip("/")
    agent_token = str(config.get("AGENT_TOKEN") or "").strip()
    poll_interval = int(config.get("POLL_INTERVAL_SECONDS") or 5)
    enable_order_execution = _to_bool(config.get("ENABLE_ORDER_EXECUTION"), False)
    agent_version = str(config.get("AGENT_VERSION") or "0.1.0")

    if not agent_token or "paste-your-agent-token" in agent_token:
        raise SystemExit("AGENT_TOKEN is missing. Generate token in AlgoAgentX > Brokers > MT5 Agent Setup and paste it into config.json.")

    api = AgentApiClient(api_base_url, agent_token)
    mt5 = MT5Client(str(config.get("MT5_PATH") or ""), int(config.get("DEFAULT_DEVIATION") or 20))

    print("AlgoAgentX MT5 Agent started")
    print(f"API: {api_base_url}")
    print(f"Polling every {poll_interval}s")
    print(f"Order execution enabled: {enable_order_execution}")

    while True:
        try:
            status = mt5.status()
            payload = status.to_payload(agent_version)
            api.send_heartbeat(payload)
            print(f"Heartbeat sent | terminal={payload.get('terminal_status')} | login={payload.get('mt5_account_login')} | balance={payload.get('balance')} | equity={payload.get('equity')}")

            commands = api.poll_commands()
            if commands:
                print(f"Received {len(commands)} command(s)")
            for command in commands:
                command_id = str(command.get("id"))
                command_type = str(command.get("command_type") or "").upper()
                if command_type == "PLACE_ORDER":
                    result = mt5.place_order(command, enable_order_execution=enable_order_execution)
                    api.send_order_result(
                        command_id=command_id,
                        success=bool(result.get("success")),
                        message=str(result.get("message") or "MT5 command processed"),
                        raw_response=result.get("raw") or {},
                        broker_order_id=result.get("broker_order_id"),
                        executed_price=result.get("executed_price"),
                    )
                    print(f"Order result sent | command={command_id} | success={result.get('success')} | {result.get('message')}")
                elif command_type == "FETCH_RATES":
                    print(f"Received FETCH_RATES command | command={command_id}")
                    result = mt5.fetch_rates(command)
                    api.send_command_result(
                        command_id=command_id,
                        success=bool(result.get("success")),
                        message=str(result.get("message") or "MT5 rates fetched"),
                        raw_response=result.get("raw") or result,
                    )
                    print(f"Rates result sent | command={command_id} | success={result.get('success')} | {result.get('message')}")
                elif command_type == "FETCH_DEALS_PNL":
                    print(f"Received FETCH_DEALS_PNL command | command={command_id}")
                    result = mt5.fetch_deals_pnl(command)
                    api.send_command_result(
                        command_id=command_id,
                        success=bool(result.get("success")),
                        message=str(result.get("message") or "MT5 deals PnL fetched"),
                        raw_response=result.get("raw") or result,
                    )
                    print(f"Deals PnL result sent | command={command_id} | success={result.get('success')} | {result.get('message')}")
                else:
                    api.send_command_result(command_id, False, f"Unsupported command type: {command_type}", {"command": command})
                    print(f"Unsupported command type: {command_type}")
        except KeyboardInterrupt:
            print("Agent stopped by user")
            break
        except Exception as exc:
            print(f"Agent error: {exc}")

        time.sleep(max(1, poll_interval))


if __name__ == "__main__":
    main()
