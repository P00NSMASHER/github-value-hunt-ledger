"""Exact bounded arithmetic, independent of the caller's Decimal context."""
from decimal import Decimal, localcontext, ROUND_HALF_UP, ROUND_HALF_EVEN
import re

MAX_CENTS = 2**63 - 1
_DECIMAL = re.compile(r'(?:0|[1-9][0-9]{0,11})(?:\.[0-9]{1,12})?\Z')
_MODES = {'HALF_UP': ROUND_HALF_UP, 'HALF_EVEN': ROUND_HALF_EVEN}


def parse_decimal(raw: str) -> Decimal:
    """Accept only original nonnegative decimal strings, never binary floats."""
    if type(raw) is not str or not _DECIMAL.fullmatch(raw):
        raise ValueError('INVALID_DECIMAL')
    return Decimal(raw)


def _bounded(value: Decimal) -> None:
    if type(value) is not Decimal or not value.is_finite() or value < 0:
        raise ValueError('INVALID_DECIMAL')
    if value.as_tuple().exponent < -36 or value.adjusted() > 35:
        raise ValueError('DECIMAL_OUT_OF_RANGE')


def multiply(left: Decimal, right: Decimal) -> Decimal:
    _bounded(left)
    _bounded(right)
    with localcontext() as context:
        context.prec = 100
        value = left * right
    _bounded(value)
    return value


def add_decimal(left: Decimal, right: Decimal) -> Decimal:
    _bounded(left)
    _bounded(right)
    with localcontext() as context:
        context.prec = 100
        value = left + right
    _bounded(value)
    return value


def extend_price(price: Decimal, quantity: Decimal, rounding: str = 'HALF_UP') -> int:
    if rounding not in _MODES:
        raise ValueError('UNSUPPORTED_ROUNDING')
    _bounded(price)
    _bounded(quantity)
    with localcontext() as context:
        context.prec = 100
        cents = (price * quantity * 100).quantize(Decimal('1'), rounding=_MODES[rounding])
    if cents < 0 or cents > MAX_CENTS:
        raise ValueError('MONEY_OUT_OF_RANGE')
    return int(cents)
