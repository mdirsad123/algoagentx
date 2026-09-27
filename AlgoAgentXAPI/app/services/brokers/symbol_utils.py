"""Broker-neutral symbol matching helpers used by live execution paths.

These helpers intentionally stay dependency-free so worker processes and focused
tests can share exactly the same alias rules without importing DB/session code.
"""

from __future__ import annotations

from typing import Any


def symbol_key(value: Any) -> str:
    return "".join(ch for ch in str(value or "").strip().upper() if ch.isalnum())


def symbol_pair_root(value: Any) -> str:
    key = symbol_key(value)
    if len(key) >= 6 and key[:6].isalpha():
        return key[:6]
    return key


def symbol_match_score(requested: Any, candidate: Any) -> int | None:
    req = symbol_key(requested)
    cand = symbol_key(candidate)
    if not req or not cand:
        return None
    if req == cand:
        return 0
    req_root = symbol_pair_root(req)
    cand_root = symbol_pair_root(cand)
    if req_root and cand_root and req_root == cand_root and len(req_root) >= 6:
        return 10 + abs(len(req) - len(cand))
    if min(len(req), len(cand)) >= 5 and (req.startswith(cand) or cand.startswith(req)):
        return 30 + abs(len(req) - len(cand))
    return None


def best_broker_symbol_ref(rows: list[dict[str, Any]], requested: Any) -> tuple[int, str] | None:
    """Return ``(symbol_id, exact_broker_name)`` for the best broker symbol.

    Supports both REST/DB-style keys (``symbol_id``, ``symbol_name``) and
    cTrader Open API keys (``symbolId``, ``symbolName``). Exact matches always
    beat suffix/root matches such as ``XAUUSDm`` -> ``XAUUSD``.
    """
    ranked: list[tuple[int, int, str, int]] = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        name = str(
            row.get("symbol_name")
            or row.get("symbolName")
            or row.get("trading_symbol")
            or row.get("symbol")
            or row.get("name")
            or ""
        ).strip()
        raw_id = row.get("symbol_id") or row.get("symbolId") or row.get("id")
        if not name or raw_id in (None, ""):
            continue
        score = symbol_match_score(requested, name)
        if score is None:
            continue
        try:
            symbol_id = int(raw_id)
        except (TypeError, ValueError):
            continue
        ranked.append((score, len(name), name.upper(), symbol_id))
    if not ranked:
        return None
    ranked.sort(key=lambda item: (item[0], item[1], item[2]))
    _score, _length, exact_name, symbol_id = ranked[0]
    return symbol_id, exact_name
