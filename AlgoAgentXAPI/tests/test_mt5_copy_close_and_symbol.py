from types import SimpleNamespace

from AlgoAgentXMT5Agent.mt5_client import MT5Client


class _OrderResult:
    def _asdict(self):
        return {"retcode": 10009, "order": 12345, "deal": 67890, "price": 4280.5, "comment": "done"}


class _FakeMT5:
    POSITION_TYPE_BUY = 0
    POSITION_TYPE_SELL = 1
    ORDER_TYPE_BUY = 0
    ORDER_TYPE_SELL = 1
    TRADE_ACTION_DEAL = 1
    ORDER_TIME_GTC = 0
    ORDER_FILLING_IOC = 1
    TRADE_RETCODE_DONE = 10009
    TRADE_RETCODE_PLACED = 10008

    def __init__(self):
        self.last_request = None
        self._symbols = [SimpleNamespace(name="XAUUSD"), SimpleNamespace(name="XAUUSDm")]

    def initialize(self, *args, **kwargs):
        return True

    def symbols_get(self):
        return self._symbols

    def symbol_select(self, symbol, enabled):
        return symbol in {"XAUUSD", "XAUUSDm"}

    def symbol_info_tick(self, symbol):
        if symbol == "XAUUSDm":
            return SimpleNamespace(bid=4280.4, ask=4280.6)
        return None

    def positions_get(self, ticket=None):
        pos = SimpleNamespace(ticket=777, symbol="XAUUSDm", type=0, volume=0.06)
        if ticket is None or ticket == 777:
            return [pos]
        return []

    def order_send(self, request):
        self.last_request = request
        return _OrderResult()


def _client():
    client = MT5Client()
    client.mt5 = _FakeMT5()
    return client


def test_symbol_resolution_skips_selectable_alias_without_live_tick():
    client = _client()
    assert client._resolve_trade_symbol("XAUUSD") == "XAUUSDm"


def test_close_position_uses_ticket_and_does_not_require_sltp():
    client = _client()
    result = client.close_position({
        "request_payload": {
            "position_ticket": "777",
            "qty": "0.06",
            "position_side": "LONG",
            "comment": "AlgoAgentX MT5 close",
        }
    }, enable_order_execution=True)

    assert result["success"] is True
    request = client.mt5.last_request
    assert request["position"] == 777
    assert request["symbol"] == "XAUUSDm"
    assert request["type"] == client.mt5.ORDER_TYPE_SELL
    assert "sl" not in request
    assert "tp" not in request
