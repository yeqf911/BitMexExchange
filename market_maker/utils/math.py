from decimal import Decimal


def to_nearrest(num, ticksize):
    tick_dec = Decimal(str(ticksize))
    return float(Decimal(round(num / ticksize, 0)) * tick_dec)
