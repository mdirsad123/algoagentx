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
            "POLL_INTERVAL_SECONDS": 1,
            "COMMAND_POLL_INTERVAL_SECONDS": 1,
            "HEARTBEAT_INTERVAL_SECONDS": 5,
            "ALERT_QUOTE_INTERVAL_MS": 250,
            "ALERT_SYMBOL_REFRESH_SECONDS": 1,
            "ENABLE_ORDER_EXECUTION": False,
            "MT5_PATH": "",
            "DEFAULT_DEVIATION": 20,
            "AGENT_VERSION": "0.4.1-alerts-symbols",
        }
        with CONFIG_PATH.open("w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        print(f"Saved {CONFIG_PATH}. You can edit it any time and restart the agent.")

    # Environment variables can override config.json for VPS/service usage.
    for key in ["API_BASE_URL", "AGENT_TOKEN", "POLL_INTERVAL_SECONDS", "COMMAND_POLL_INTERVAL_SECONDS", "HEARTBEAT_INTERVAL_SECONDS", "ALERT_QUOTE_INTERVAL_MS", "ALERT_SYMBOL_REFRESH_SECONDS", "ENABLE_ORDER_EXECUTION", "MT5_PATH", "DEFAULT_DEVIATION", "AGENT_VERSION"]:
        if os.getenv(key) is not None:
            config[key] = os.getenv(key)
    return config


def main() -> None:
    config = load_config()
    api_base_url = str(config.get("API_BASE_URL") or "http://localhost:8000").rstrip("/")
    agent_token = str(config.get("AGENT_TOKEN") or "").strip()
    legacy_poll_interval = int(config.get("POLL_INTERVAL_SECONDS") or 1)
    command_poll_interval = max(1, int(config.get("COMMAND_POLL_INTERVAL_SECONDS") or legacy_poll_interval or 1))
    heartbeat_interval = max(1, int(config.get("HEARTBEAT_INTERVAL_SECONDS") or 5))
    alert_quote_interval = max(0.1, float(config.get("ALERT_QUOTE_INTERVAL_MS") or 250) / 1000.0)
    alert_symbol_refresh = max(1.0, float(config.get("ALERT_SYMBOL_REFRESH_SECONDS") or 1))
    enable_order_execution = _to_bool(config.get("ENABLE_ORDER_EXECUTION"), False)
    agent_version = str(config.get("AGENT_VERSION") or "0.4.1-alerts-symbols")

    if not agent_token or "paste-your-agent-token" in agent_token:
        raise SystemExit("AGENT_TOKEN is missing. Generate token in AlgoAgentX > Brokers > MT5 Agent Setup and paste it into config.json.")

    api = AgentApiClient(api_base_url, agent_token)
    mt5 = MT5Client(str(config.get("MT5_PATH") or ""), int(config.get("DEFAULT_DEVIATION") or 20))

    print("AlgoAgentX MT5 Agent started")
    print(f"API: {api_base_url}")
    print(f"Command polling every {command_poll_interval}s")
    print(f"Heartbeat every {heartbeat_interval}s")
    print(f"Alert quote push every {int(alert_quote_interval * 1000)}ms when alerts are active")
    print(f"Order execution enabled: {enable_order_execution}")

    last_heartbeat_at = 0.0
    last_command_poll_at = 0.0
    last_symbol_refresh_at = 0.0
    last_quote_push_at = 0.0
    active_alert_symbols: list[str] = []
    last_logged_alert_symbols: list[str] = []
    last_quote_log_at = 0.0
    error_backoff_seconds = 1.0
    while True:
        try:
            now_monotonic = time.monotonic()
            if last_heartbeat_at == 0.0 or (now_monotonic - last_heartbeat_at) >= heartbeat_interval:
                status = mt5.status()
                payload = status.to_payload(agent_version)
                api.send_heartbeat(payload)
                last_heartbeat_at = now_monotonic
                print(f"Heartbeat sent | terminal={payload.get('terminal_status')} | login={payload.get('mt5_account_login')} | balance={payload.get('balance')} | equity={payload.get('equity')}")

            if last_symbol_refresh_at == 0.0 or (now_monotonic - last_symbol_refresh_at) >= alert_symbol_refresh:
                try:
                    active_alert_symbols = api.get_alert_symbols()
                    last_symbol_refresh_at = now_monotonic
                    if active_alert_symbols != last_logged_alert_symbols:
                        print(f"Active alert symbols: {active_alert_symbols or 'none'}")
                        last_logged_alert_symbols = list(active_alert_symbols)
                except Exception as exc:
                    print(f"Alert symbol refresh error: {exc}")

            if active_alert_symbols and (last_quote_push_at == 0.0 or (now_monotonic - last_quote_push_at) >= alert_quote_interval):
                quotes = mt5.get_quotes(active_alert_symbols)
                if quotes:
                    response = api.send_quotes(quotes)
                    if last_quote_log_at == 0.0 or (now_monotonic - last_quote_log_at) >= 5.0:
                        sample = quotes[0]
                        print(f"Alert quotes sent | accepted={response.get('accepted') if isinstance(response, dict) else '?'} | sample={sample.get('symbol')} resolved={sample.get('resolved_symbol')} price={sample.get('last')}")
                        last_quote_log_at = now_monotonic
                elif last_quote_log_at == 0.0 or (now_monotonic - last_quote_log_at) >= 5.0:
                    print(f"No MT5 quotes resolved for active alert symbols: {active_alert_symbols}. Check the exact broker symbol in Market Watch.")
                    last_quote_log_at = now_monotonic
                last_quote_push_at = now_monotonic

            commands = []
            if last_command_poll_at == 0.0 or (now_monotonic - last_command_poll_at) >= command_poll_interval:
                commands = api.poll_commands()
                last_command_poll_at = now_monotonic
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
                elif command_type == "FETCH_SYMBOLS":
                    print(f"Received FETCH_SYMBOLS command | command={command_id}")
                    result = mt5.fetch_symbols(command)
                    api.send_command_result(
                        command_id=command_id,
                        success=bool(result.get("success")),
                        message=str(result.get("message") or "MT5 symbols fetched"),
                        raw_response=result.get("raw") or result,
                    )
                    print(f"Symbols result sent | command={command_id} | success={result.get('success')} | {result.get('message')}")
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
            error_backoff_seconds = 1.0
        except KeyboardInterrupt:
            print("Agent stopped by user")
            break
        except Exception as exc:
            print(f"Agent error: {exc}. Reconnecting in {error_backoff_seconds:.0f}s")
            time.sleep(error_backoff_seconds)
            error_backoff_seconds = min(error_backoff_seconds * 2.0, 30.0)
            continue

        time.sleep(min(0.1, alert_quote_interval))


if __name__ == "__main__":
    main()
