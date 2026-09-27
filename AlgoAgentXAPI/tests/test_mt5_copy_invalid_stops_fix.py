from types import SimpleNamespace

from AlgoAgentXMT5Agent.mt5_client import MT5Client


class _Result:
    def __init__(self, retcode=10009, price=4281.0, comment="done"):
        self.retcode = retcode
        self.price = price
        self.comment = comment

    def _asdict(self):
        return {
            "retcode": self.retcode,
            "order": 12345 if self.retcode == 10009 else 0,
            "deal": 67890 if self.retcode == 10009 else 0,
            "price": self.price,
            "comment": self.comment,
        }


class _FakeMT5:
    ORDER_TYPE_BUY = 0
    ORDER_TYPE_SELL = 1
    TRADE_ACTION_DEAL = 1
    ORDER_TIME_GTC = 0
    ORDER_FILLING_IOC = 1
    TRADE_RETCODE_DONE = 10009
    TRADE_RETCODE_PLACED = 10008
    TRADE_RETCODE_INVALID_STOPS = 10016

    def __init__(self, *, bid=4280.8, ask=4281.0, stops_level=0, results=None, retry_tick=None):
        self.bid = bid
        self.ask = ask
        self.retry_tick = retry_tick
        self.stops_level = stops_level
        self.results = list(results or [_Result()])
        self.requests = []
        self.tick_calls = 0

    def initialize(self, *args, **kwargs):
        return True

    def symbols_get(self):
        return [SimpleNamespace(name="XAUUSDm")]

    def symbol_select(self, symbol, enabled):
        return symbol == "XAUUSDm"

    def symbol_info_tick(self, symbol):
        self.tick_calls += 1
        if self.retry_tick is not None and self.tick_calls >= 3:
            # _resolve_trade_symbol consumes one tick, initial place_order consumes
            # the second; the retry fetch is the third call.
            return SimpleNamespace(bid=self.retry_tick[0], ask=self.retry_tick[1])
        return SimpleNamespace(bid=self.bid, ask=self.ask)

    def symbol_info(self, symbol):
        return SimpleNamespace(digits=2, point=0.01, trade_stops_level=self.stops_level)

    def order_send(self, request):
        self.requests.append(dict(request))
        return self.results.pop(0)


def _client(fake):
    client = MT5Client()
    client.mt5 = fake
    return client


def test_primary_mt5_uses_live_market_price_but_keeps_absolute_strategy_sltp():
    fake = _FakeMT5(bid=4280.8, ask=4281.0)
    client = _client(fake)

    result = client.place_order({
        "request_payload": {
            "symbol": "XAUUSD",
            "side": "BUY",
            "qty": "0.10",
            "price": "4280.00",
            "stop_loss": "4274.00",
            "target": "4292.00",
            "is_copy_execution": False,
        }
    }, enable_order_execution=True)

    assert result["success"] is True
    request = fake.requests[-1]
    assert request["price"] == 4281.00
    assert request["sl"] == 4274.00
    assert request["tp"] == 4292.00


def test_copy_to_mt5_rebases_sltp_by_target_live_price_offset():
    fake = _FakeMT5(bid=4280.8, ask=4281.0)
    client = _client(fake)

    result = client.place_order({
        "request_payload": {
            "symbol": "XAUUSD",
            "side": "BUY",
            "qty": "0.10",
            "price": "4280.00",
            "stop_loss": "4274.00",
            "target": "4292.00",
            "is_copy_execution": True,
            "source_broker_code": "CTRADER",
        }
    }, enable_order_execution=True)

    assert result["success"] is True
    request = fake.requests[-1]
    assert request["price"] == 4281.00
    assert request["sl"] == 4275.00
    assert request["tp"] == 4293.00
    assert result["raw"]["protection_debug"]["price_offset"] == 1.0


def test_copy_to_mt5_blocks_locally_when_broker_minimum_stop_distance_is_too_large():
    # 700 points * 0.01 = 7.00 minimum. The translated BUY SL is only 6.80
    # below Bid, so the command is rejected before order_send().
    fake = _FakeMT5(bid=4280.8, ask=4281.0, stops_level=700)
    client = _client(fake)

    result = client.place_order({
        "request_payload": {
            "symbol": "XAUUSD",
            "side": "BUY",
            "qty": "0.10",
            "price": "4280.00",
            "stop_loss": "4274.00",
            "target": "4292.00",
            "is_copy_execution": True,
        }
    }, enable_order_execution=True)

    assert result["success"] is False
    assert "minimum stop distance" in result["message"]
    assert fake.requests == []


def test_copy_to_mt5_retries_once_after_broker_invalid_stops_with_fresh_tick():
    fake = _FakeMT5(
        bid=4280.8,
        ask=4281.0,
        results=[_Result(retcode=10016, price=0, comment="Invalid stops"), _Result(retcode=10009, price=4281.2, comment="done")],
        retry_tick=(4281.0, 4281.2),
    )
    client = _client(fake)

    result = client.place_order({
        "request_payload": {
            "symbol": "XAUUSD",
            "side": "BUY",
            "qty": "0.10",
            "price": "4280.00",
            "stop_loss": "4274.00",
            "target": "4292.00",
            "is_copy_execution": True,
        }
    }, enable_order_execution=True)

    assert result["success"] is True
    assert len(fake.requests) == 2
    assert fake.requests[0]["price"] == 4281.0
    assert fake.requests[1]["price"] == 4281.2
    assert fake.requests[1]["sl"] == 4275.2
    assert fake.requests[1]["tp"] == 4293.2
    assert result["raw"]["invalid_stops_retry"]["attempted"] is True
