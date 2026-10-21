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


from dataclasses import asdict, dataclass
from .models import canonical_hash, normalize_sha256, normalize_utc_timestamp, MAX_CENTS


@dataclass(frozen=True)
class CashEvent:
    """A receipt or linked reversal; signed cents are incremental, never a balance."""
    event_id: str
    finding_id: str
    amount_cents: int
    fee_cents: int
    currency: str
    source_hash: str
    source_locator: str
    observed_at: str
    verified: bool
    reverses_id: str | None = None

    def __post_init__(self):
        for name in ('event_id', 'finding_id', 'source_locator'):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(name + ' required')
            object.__setattr__(self, name, value.strip())
        for name in ('amount_cents', 'fee_cents'):
            value = getattr(self, name)
            if type(value) is not int or abs(value) > MAX_CENTS:
                raise ValueError(name + ' must be bounded integer cents')
        if self.amount_cents == 0:
            raise ValueError('cash event must be nonzero')
        if self.amount_cents > 0:
            if self.reverses_id or not 0 <= self.fee_cents <= self.amount_cents:
                raise ValueError('receipt fee or reversal reference invalid')
        elif not isinstance(self.reverses_id, str) or not self.reverses_id.strip() or not self.amount_cents <= self.fee_cents <= 0:
            raise ValueError('reversal requires original event and nonpositive bounded fee')
        if not isinstance(self.currency, str) or len(self.currency) != 3 or not self.currency.isascii() or not self.currency.isalpha() or not self.currency.isupper():
            raise ValueError('currency must be three uppercase letters')
        object.__setattr__(self, 'source_hash', normalize_sha256('source_hash', self.source_hash))
        object.__setattr__(self, 'observed_at', normalize_utc_timestamp('observed_at', self.observed_at))
        if type(self.verified) is not bool:
            raise ValueError('verified must be boolean')

    @property
    def proof_hash(self):
        return canonical_hash(asdict(self))
