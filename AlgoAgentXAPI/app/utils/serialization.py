"""
Safe serialization utilities for AlgoAgentXAPI.

Handles date/time objects and other non-JSON serializable types.
"""

import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict


class SafeJSONEncoder(json.JSONEncoder):
    """
    Custom JSON encoder that handles date, datetime, and Decimal objects.
    """

    def default(self, obj):
        if isinstance(obj, date):
            return obj.isoformat()
        elif isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, Decimal):
            return float(obj)
        # Let the base class default method raise the TypeError
        return super().default(obj)


def safe_json_dumps(obj: Any) -> str:
    """
    Safely serialize an object to JSON string, handling date/time objects.

    Args:
        obj: Object to serialize

    Returns:
        JSON string representation

    Raises:
        TypeError: If object contains non-serializable types
    """
    return json.dumps(obj, cls=SafeJSONEncoder)


def serialize_backtest_payload(
    strategy_id: str,
    instrument_id: int,
    timeframe: str,
    start_date: date,
    end_date: date,
    capital: float
) -> Dict[str, Any]:
    """
    Serialize backtest parameters to a JSON-safe dictionary.

    Args:
        strategy_id: Strategy identifier
        instrument_id: Instrument identifier
        timeframe: Timeframe string
        start_date: Start date
        end_date: End date
        capital: Initial capital

    Returns:
        Dictionary with all values as JSON-serializable types
    """
    return {
        "strategy_id": strategy_id,
        "instrument_id": instrument_id,
        "timeframe": timeframe,
        "start_date": start_date.isoformat() if isinstance(start_date, date) else str(start_date),
        "end_date": end_date.isoformat() if isinstance(end_date, date) else str(end_date),
        "capital": capital
    }


def deserialize_backtest_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deserialize backtest parameters, converting date strings back to date objects.

    Args:
        payload: Dictionary with serialized backtest parameters

    Returns:
        Dictionary with date strings converted to date objects where appropriate
    """
    result = payload.copy()

    # Convert date strings back to date objects
    if "start_date" in result and isinstance(result["start_date"], str):
        result["start_date"] = date.fromisoformat(result["start_date"])
    if "end_date" in result and isinstance(result["end_date"], str):
        result["end_date"] = date.fromisoformat(result["end_date"])

    return result
