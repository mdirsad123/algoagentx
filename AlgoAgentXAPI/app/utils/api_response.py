from typing import Any

def success_response(data: Any, message: str | None = None) -> dict:
    payload = {"success": True, "data": data}
    if message:
        payload["message"] = message
    return payload
