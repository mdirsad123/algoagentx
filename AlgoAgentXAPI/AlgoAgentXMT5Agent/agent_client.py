from __future__ import annotations

from typing import Any
import requests


class AgentApiClient:
    def __init__(self, api_base_url: str, agent_token: str, timeout: int = 20):
        self.api_base_url = api_base_url.rstrip("/")
        self.agent_token = agent_token.strip()
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.agent_token}",
            "Content-Type": "application/json",
            "User-Agent": "AlgoAgentXMT5Agent/0.1.0",
        })

    def _url(self, path: str) -> str:
        return f"{self.api_base_url}{path if path.startswith('/') else '/' + path}"

    @staticmethod
    def _unwrap(response: requests.Response) -> Any:
        response.raise_for_status()
        payload = response.json()
        if isinstance(payload, dict) and "data" in payload:
            return payload["data"]
        return payload

    def send_heartbeat(self, payload: dict[str, Any]) -> Any:
        # token is also included in body so older API builds still accept the heartbeat.
        payload = {**payload, "agent_token": self.agent_token}
        response = self.session.post(self._url("/api/v1/mt5-agent/heartbeat"), json=payload, timeout=self.timeout)
        return self._unwrap(response)

    def poll_commands(self) -> list[dict[str, Any]]:
        response = self.session.get(self._url("/api/v1/mt5-agent/commands"), timeout=self.timeout)
        data = self._unwrap(response)
        return data if isinstance(data, list) else []

    def send_order_result(self, command_id: str, success: bool, message: str, raw_response: dict[str, Any] | None = None, broker_order_id: str | None = None, executed_price: float | None = None) -> Any:
        payload = {
            "agent_token": self.agent_token,
            "command_id": command_id,
            "success": success,
            "status": "COMPLETED" if success else "ERROR",
            "message": message,
            "raw_response": raw_response or {},
            "broker_order_id": broker_order_id,
            "executed_price": executed_price,
        }
        response = self.session.post(self._url("/api/v1/mt5-agent/order-result"), json=payload, timeout=self.timeout)
        return self._unwrap(response)
