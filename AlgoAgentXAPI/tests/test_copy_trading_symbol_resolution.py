import importlib.util
import sys
import types
from pathlib import Path

# Keep execution_engine imports lightweight in focused CI environments.
if "redis.asyncio" not in sys.modules:
    redis_pkg = types.ModuleType("redis")
    redis_asyncio = types.ModuleType("redis.asyncio")
    redis_asyncio.Redis = object
    redis_asyncio.from_url = lambda *args, **kwargs: None
    redis_pkg.asyncio = redis_asyncio
    sys.modules.setdefault("redis", redis_pkg)
    sys.modules.setdefault("redis.asyncio", redis_asyncio)

from app.services.brokers.ctrader import CTraderAdapter
from app.services.live.execution_engine import _canonical_symbol_fallback


# Import the standalone Windows MT5 Agent client without requiring it to be a package.
_MT5_CLIENT_PATH = Path(__file__).resolve().parents[1] / "AlgoAgentXMT5Agent" / "mt5_client.py"
_spec = importlib.util.spec_from_file_location("algoagentx_mt5_client_test", _MT5_CLIENT_PATH)
_mt5_module = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
sys.modules[_spec.name] = _mt5_module
_spec.loader.exec_module(_mt5_module)
MT5Client = _mt5_module.MT5Client


class _Sym:
    def __init__(self, name):
        self.name = name


class _FakeMT5:
    def __init__(self, symbols):
        self._symbols = list(symbols)
        self.selected = []

    def symbol_select(self, symbol, enabled):
        self.selected.append(symbol)
        return symbol in self._symbols

    def symbols_get(self):
        return [_Sym(name) for name in self._symbols]


def test_canonical_fallback_removes_common_pair_suffixes():
    assert _canonical_symbol_fallback("XAUUSDm") == "XAUUSD"
    assert _canonical_symbol_fallback("xauusd.pro") == "XAUUSD"
    assert _canonical_symbol_fallback("BTCUSD_c") == "BTCUSD"
    assert _canonical_symbol_fallback("US30") == "US30"


def test_ctrader_alias_match_maps_mt5_suffix_to_ctrader_clean_symbol():
    rows = [
        {"symbol_id": "1", "symbol_name": "EURUSD"},
        {"symbol_id": "2", "symbol_name": "XAUUSD"},
        {"symbol_id": "3", "symbol_name": "XAGUSD"},
    ]
    matched = CTraderAdapter._best_symbol_meta("XAUUSDm", rows)
    assert matched is not None
    assert matched["symbol_name"] == "XAUUSD"


def test_ctrader_alias_match_keeps_exact_symbol_first():
    rows = [
        {"symbol_id": "1", "symbol_name": "XAUUSDm"},
        {"symbol_id": "2", "symbol_name": "XAUUSD"},
    ]
    matched = CTraderAdapter._best_symbol_meta("XAUUSDm", rows)
    assert matched is not None
    assert matched["symbol_name"] == "XAUUSDm"


def test_mt5_agent_resolves_clean_symbol_to_terminal_suffix_without_api_roundtrip():
    client = MT5Client()
    client.mt5 = _FakeMT5(["EURUSDm", "XAUUSDm", "XAGUSDm"])
    assert client._resolve_trade_symbol("XAUUSD") == "XAUUSDm"


def test_mt5_agent_resolves_other_suffix_variants_per_account():
    client = MT5Client()
    client.mt5 = _FakeMT5(["XAUUSD.c", "EURUSD.c"])
    assert client._resolve_trade_symbol("XAUUSD") == "XAUUSD.c"


def test_execution_engine_resolved_symbol_prefers_adapter_exact_alias():
    from types import SimpleNamespace
    from app.services.live.execution_engine import _resolved_order_symbol

    result = SimpleNamespace(raw_response={"resolved_symbol": "XAUUSDm"})
    assert _resolved_order_symbol(result, "XAUUSD") == "XAUUSDm"


def test_execution_engine_resolved_symbol_falls_back_to_requested_symbol():
    from types import SimpleNamespace
    from app.services.live.execution_engine import _resolved_order_symbol

    result = SimpleNamespace(raw_response={"provider": "MT5", "execution_mode": "AGENT"})
    assert _resolved_order_symbol(result, "XAUUSD") == "XAUUSD"


def test_persistent_ctrader_worker_maps_mt5_alias_to_ctrader_symbol():
    from app.services.brokers.symbol_utils import best_broker_symbol_ref

    rows = [
        {"symbolId": 101, "symbolName": "EURUSD"},
        {"symbolId": 202, "symbolName": "XAUUSD"},
        {"symbolId": 303, "symbolName": "XAGUSD"},
    ]
    assert best_broker_symbol_ref(rows, "XAUUSDm") == (202, "XAUUSD")


def test_persistent_ctrader_worker_prefers_exact_symbol_when_present():
    from app.services.brokers.symbol_utils import best_broker_symbol_ref

    rows = [
        {"symbolId": 202, "symbolName": "XAUUSD"},
        {"symbolId": 204, "symbolName": "XAUUSDm"},
    ]
    assert best_broker_symbol_ref(rows, "XAUUSDm") == (204, "XAUUSDM")
