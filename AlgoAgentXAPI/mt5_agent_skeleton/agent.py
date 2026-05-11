"""AlgoAgentX MT5 Agent skeleton.

Run this on the Windows PC/VPS where MetaTrader 5 is installed.
This safe skeleton sends heartbeats and polls commands. Real MT5 order execution
can be implemented in the marked section after packaging/signing the agent.
"""
from __future__ import annotations

import os
import time
from typing import Any

import requests

API_BASE_URL = os.getenv("ALGOAGENTX_API_BASE_URL", "http://localhost:8000").rstrip("/")
AGENT_TOKEN = os.getenv("ALGOAGENTX_MT5_AGENT_TOKEN", "")
POLL_SECONDS = int(os.getenv("POLL_SECONDS", "5"))


def headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {AGENT_TOKEN}"}


def heartbeat() -> None:
    # TODO: Replace these placeholders with real MetaTrader5 terminal checks.
    payload: dict[str, Any] = {
        "terminal_connected": False,
        "terminal_status": "NOT_CONNECTED",
        "account_login": None,
        "server_name": None,
        "balance": None,
        "equity": None,
        "currency": None,
        "algo_trading_enabled": None,
        "agent_version": "0.1.0-skeleton",
        "metadata": {"source": "mt5_agent_skeleton"},
    }
    response = requests.post(f"{API_BASE_URL}/api/v1/mt5-agent/heartbeat", json=payload, headers=headers(), timeout=15)
    response.raise_for_status()


def poll_commands() -> list[dict[str, Any]]:
    response = requests.get(f"{API_BASE_URL}/api/v1/mt5-agent/commands", headers=headers(), timeout=15)
    response.raise_for_status()
    body = response.json()
    return body.get("data") or []


def post_order_result(command_id: str, success: bool, message: str, raw_response: dict[str, Any] | None = None) -> None:
    payload = {
        "command_id": command_id,
        "success": success,
        "status": "COMPLETED" if success else "ERROR",
        "message": message,
        "raw_response": raw_response or {},
    }
    response = requests.post(f"{API_BASE_URL}/api/v1/mt5-agent/order-result", json=payload, headers=headers(), timeout=15)
    response.raise_for_status()


def main() -> None:
    if not AGENT_TOKEN:
        raise RuntimeError("Set ALGOAGENTX_MT5_AGENT_TOKEN first.")
    while True:
        try:
            heartbeat()
            for command in poll_commands():
                # Safe placeholder: reject commands until real MT5 execution is implemented in the installer phase.
                post_order_result(command["id"], False, "MT5 Agent skeleton received command. Real order execution is not enabled in this skeleton.", {"command": command})
        except Exception as exc:
            print(f"Agent loop error: {exc}")
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
