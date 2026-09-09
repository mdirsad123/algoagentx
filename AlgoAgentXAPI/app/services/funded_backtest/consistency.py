from decimal import Decimal


def consistency_percentage(best_profitable_day, total_positive_profit) -> Decimal:
    best = Decimal(str(best_profitable_day or 0))
    total = Decimal(str(total_positive_profit or 0))
    if total <= 0 or best <= 0:
        return Decimal("0")
    return best / total


def consistency_requirement_met(best_profitable_day, total_positive_profit, maximum_percentage) -> bool:
    maximum = Decimal(str(maximum_percentage))
    return consistency_percentage(best_profitable_day, total_positive_profit) <= maximum
