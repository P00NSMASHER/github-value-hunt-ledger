"""Exact human-readable formatting for integer-cent Freight Recovery amounts."""

from __future__ import annotations


def _amount(cents: int) -> str:
    if type(cents) is not int:
        raise ValueError("cents must be an integer")
    sign = "-" if cents < 0 else ""
    whole, fraction = divmod(abs(cents), 100)
    return sign + f"{whole:,}.{fraction:02d}"


def format_cents(currency: str, cents: int) -> str:
    if not isinstance(currency, str) or not currency.strip():
        raise ValueError("currency is required")
    return currency.strip() + " " + _amount(cents)


def format_dollars(cents: int) -> str:
    return "$" + _amount(cents)
