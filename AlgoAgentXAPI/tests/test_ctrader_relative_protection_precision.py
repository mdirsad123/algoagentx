from decimal import Decimal

from app.services.brokers.ctrader import CTraderAdapter


def test_xauusd_relative_protection_is_normalized_before_protocol_scaling():
    # Simulates float tails that can be hidden by the UI's 2-decimal display.
    entry = Decimal("4277.0500000001")
    target = Decimal("4260.1699999997")
    relative = CTraderAdapter._price_distance_to_relative(entry, target, {"digits": 2})
    assert relative == 1_688_000
    assert relative % 1_000 == 0


def test_three_digit_symbol_relative_value_respects_symbol_precision():
    entry = Decimal("132.874000244")
    stop = Decimal("137.2237701")
    relative = CTraderAdapter._price_distance_to_relative(entry, stop, {"digits": 3})
    assert relative == 435_000
    assert relative % 100 == 0
