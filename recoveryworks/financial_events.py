"""Reconcile signed settlements with explicit, bounded reversal lineage."""
from __future__ import annotations

from datetime import date


def net_settlements(events, *, amount_field, id_field="settlement_id",
                    date_field="settlement_date", reversal_field="reverses_id"):
    events = tuple(events)
    indexed = {}
    reversed_amounts = {}
    for event in events:
        identity = getattr(event, id_field)
        if identity in indexed:
            raise ValueError("duplicate financial event identity")
        indexed[identity] = event
        amount = getattr(event, amount_field)
        if type(amount) is not int:
            raise ValueError("financial event amount must be integer cents")
    for event in events:
        amount = getattr(event, amount_field)
        reversal = getattr(event, reversal_field, None)
        if amount >= 0:
            if reversal:
                raise ValueError("only a negative event may reference a reversal")
            continue
        original = indexed.get(reversal)
        if original is None or getattr(original, amount_field) <= 0:
            raise ValueError("reversal requires its original positive event in the same scope")
        if date.fromisoformat(getattr(event, date_field)) < date.fromisoformat(getattr(original, date_field)):
            raise ValueError("reversal cannot predate its original event")
        reversed_amounts[reversal] = reversed_amounts.get(reversal, 0) - amount
        if reversed_amounts[reversal] > getattr(original, amount_field):
            raise ValueError("reversals exceed the original event amount")
    return sum(getattr(event, amount_field) for event in events)
