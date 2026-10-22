"""Exact presentation of stored integer cents.

This boundary changes only display text, not accounting, claims, settlement,
rates, hashes, or authority. Floating point must never represent stored cents.
"""


def format_cents(cents: int) -> str:
    """Return a grouped dollars-and-cents amount with no float conversion.

    The caller supplies currency or symbol separately. Booleans, floats and
    Decimal are deliberately rejected to avoid silently rounding evidence.
    """
    if type(cents) is not int:
        raise TypeError("cents must be an exact integer (bool and floats forbidden)")
    whole, minor = divmod(abs(cents), 100)
    sign = "-" if cents < 0 else ""
    return f"{sign}{whole:,}.{minor:02d}"
