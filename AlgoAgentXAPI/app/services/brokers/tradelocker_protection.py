"""Verify current protective orders, not requested entry prices or order history."""
from decimal import Decimal, InvalidOperation


def verify_protection(position, orders):
    result = {'status': 'UNVERIFIED', 'stop_loss': None, 'target': None}
    by_id = {str(row.get('id')): row for row in orders if isinstance(row, dict)}
    for link, output, price_key, order_type in (
        ('stopLossId', 'stop_loss', 'stopPrice', 'stop'),
        ('takeProfitId', 'target', 'price', 'limit'),
    ):
        order = by_id.get(str(position.get(link)))
        if not position.get('id') or not position.get(link) or not order:
            continue
        if str(order.get('positionId')) != str(position.get('id')):
            continue
        # Partial fills do not prove the remaining protective quantity. Report
        # unverified until a fresh, fully covering linked order is available.
        if str(order.get('status', '')).lower() not in {'new', 'placed', 'open', 'pending', 'working'}:
            continue
        if str(order.get('type', '')).lower() != order_type:
            continue
        side = str(position.get('side')).lower()
        if side not in {'buy', 'sell'}:
            continue
        opposite = 'sell' if side == 'buy' else 'buy'
        if str(order.get('side', '')).lower() != opposite:
            continue
        try:
            price = Decimal(str(order.get(price_key)))
            quantity = Decimal(str(order.get('qty')))
            position_quantity = Decimal(str(position.get('qty')))
            filled = Decimal(str(order.get('filledQty') or 0))
            if (price.is_finite() and price > 0 and quantity.is_finite()
                    and position_quantity.is_finite() and position_quantity > 0
                    and filled.is_finite() and filled == 0 and quantity >= position_quantity):
                result[output] = str(price)
        except (InvalidOperation, ValueError, TypeError):
            continue
    if result['stop_loss'] is not None and result['target'] is not None:
        result['status'] = 'VERIFIED'
    else:
        result['warning'] = 'Broker-side SL/TP could not be verified; check this position in TradeLocker.'
    return result