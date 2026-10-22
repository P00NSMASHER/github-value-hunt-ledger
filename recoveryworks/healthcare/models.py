"""Immutable records. Identities are exact and always include buyer/account scope."""
from dataclasses import dataclass, fields
from datetime import date
import re
from typing import get_type_hints, get_origin, get_args, Union
from types import UnionType
from .money import parse_decimal, MAX_CENTS

_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.:/@+\-]{0,199}\Z')
_HASH = re.compile(r'[0-9a-f]{64}\Z')
_DATE = re.compile(r'[0-9]{4}-[0-9]{2}-[0-9]{2}\Z')


def check_id(value: str) -> None:
    if type(value) is not str or not _ID.fullmatch(value):
        raise ValueError('INVALID_IDENTITY')


def check_cents(value: int) -> None:
    if type(value) is not int or not 0 <= value <= MAX_CENTS:
        raise ValueError('INVALID_CENTS')


def check_date(value: str) -> None:
    if type(value) is not str or not _DATE.fullmatch(value):
        raise ValueError('INVALID_DATE')
    try:
        date.fromisoformat(value)
    except ValueError:
        raise ValueError('INVALID_DATE') from None


def _check_type(value, annotation):
    origin = get_origin(annotation)
    if origin in (Union, UnionType):
        if value is None and type(None) in get_args(annotation):
            return
        options = [x for x in get_args(annotation) if x is not type(None)]
        if len(options) != 1:
            raise ValueError('INVALID_SCHEMA')
        return _check_type(value, options[0])
    if origin is tuple:
        if type(value) is not tuple:
            raise ValueError('IMMUTABLE_TUPLE_REQUIRED')
        args = get_args(annotation)
        for item in value:
            _check_type(item, args[0])
    elif type(value) is not annotation:
        raise ValueError('INVALID_FIELD_TYPE')


@dataclass(frozen=True)
class ScopeKey:
    client_id: str
    buyer_id: str
    facility_id: str
    supplier_id: str
    account_id: str
    currency: str

    def __post_init__(self):
        for f in fields(self):
            check_id(getattr(self, f.name))
        if self.currency != 'USD':
            raise ValueError('UNSUPPORTED_CURRENCY')


@dataclass(frozen=True)
class SourceRef:
    sha256: str
    locator: str
    system: str = 'synthetic'

    def __post_init__(self):
        if type(self.sha256) is not str or not _HASH.fullmatch(self.sha256):
            raise ValueError('INVALID_SOURCE_HASH')
        if type(self.locator) is not str or not 1 <= len(self.locator) <= 240:
            raise ValueError('INVALID_SOURCE_LOCATOR')
        if any(ord(c) < 32 or ord(c) > 126 for c in self.locator):
            raise ValueError('INVALID_SOURCE_LOCATOR')
        check_id(self.system)


@dataclass(frozen=True)
class Hold:
    code: str
    record_id: str
    evidence: tuple[SourceRef, ...] = ()


@dataclass(frozen=True)
class ApprovedScope:
    scopes: tuple[ScopeKey, ...]
    source_hash: str
    declared_counts: tuple[tuple[str, int], ...]
    period_start: str
    period_end: str
    as_of: str
    audit_start: str
    synthetic: bool

    def __post_init__(self):
        if type(self.scopes) is not tuple or not self.scopes or len(set(self.scopes)) != len(self.scopes):
            raise ValueError('INVALID_APPROVED_SCOPE')
        if any(type(s) is not ScopeKey for s in self.scopes):
            raise ValueError('INVALID_APPROVED_SCOPE')
        if type(self.source_hash) is not str or not _HASH.fullmatch(self.source_hash):
            raise ValueError('INVALID_SOURCE_HASH')
        if type(self.synthetic) is not bool:
            raise ValueError('INVALID_ENVIRONMENT')
        if type(self.declared_counts) is not tuple:
            raise ValueError('INVALID_DECLARED_COUNTS')
        seen = set()
        for item in self.declared_counts:
            if type(item) is not tuple or len(item) != 2:
                raise ValueError('INVALID_DECLARED_COUNTS')
            name, count = item
            if name not in TABLE_TYPES or name in seen or type(count) is not int or not 0 <= count <= 50000:
                raise ValueError('INVALID_DECLARED_COUNTS')
            seen.add(name)
        for value in (self.period_start, self.period_end, self.as_of, self.audit_start):
            check_date(value)
        if not self.period_start <= self.audit_start <= self.as_of <= self.period_end:
            raise ValueError('INVALID_AUDIT_PERIOD')


class _Record:
    def __post_init__(self):
        hints = get_type_hints(type(self))
        for f in fields(self):
            value = getattr(self, f.name)
            _check_type(value, hints[f.name])
            if value is None:
                continue
            if f.name == 'id' or f.name.endswith('_id') or f.name in ('unit', 'from_unit', 'to_unit', 'external_reference', 'invoice_number', 'line_number'):
                check_id(value)
            if f.name.endswith('_cents'):
                check_cents(value)
            if f.name.endswith('_date') or f.name in ('effective_from', 'effective_to'):
                check_date(value)
            if f.name in ('quantity', 'unit_price', 'factor'):
                parse_decimal(value)
        if hasattr(self, 'effective_to') and self.effective_to is not None and self.effective_to < self.effective_from:
            raise ValueError('INVALID_EFFECTIVE_PERIOD')


@dataclass(frozen=True)
class ProductIdentity(_Record):
    id: str
    scope: ScopeKey
    source: SourceRef
    sku: str
    effective_from: str
    effective_to: str | None = None
    category: str = 'FIXED_PACK_NONPHARMA'


@dataclass(frozen=True)
class InvoiceLine(_Record):
    id: str
    scope: ScopeKey
    source: SourceRef
    invoice_number: str
    product_id: str
    po_line_id: str
    quantity: str
    unit: str
    amount_cents: int
    invoice_date: str
    order_date: str | None = None
    ship_date: str | None = None
    line_number: str = '1'
    status: str = 'ACTIVE'
    supersedes_id: str | None = None
    unsupported_components: tuple[str, ...] = ()


@dataclass(frozen=True)
class ContractAuthority(_Record):
    id: str
    scope: ScopeKey
    source: SourceRef
    product_id: str
    unit: str
    unit_price: str
    date_basis: str
    effective_from: str
    effective_to: str | None = None
    rounding: str = 'HALF_UP'
    quantity_basis: str = 'ACCEPTED_RECEIPTS'


@dataclass(frozen=True)
class PackConversion(_Record):
    id: str
    scope: ScopeKey
    source: SourceRef
    product_id: str
    from_unit: str
    to_unit: str
    factor: str
    effective_from: str
    effective_to: str | None = None


@dataclass(frozen=True)
class ReceiptEvent(_Record):
    id: str
    scope: ScopeKey
    source: SourceRef
    product_id: str
    po_line_id: str
    quantity: str
    unit: str
    receipt_date: str
    accepted: bool = True


@dataclass(frozen=True)
class ReceiptAllocation(_Record):
    id: str
    scope: ScopeKey
    source: SourceRef
    receipt_id: str
    invoice_line_id: str
    quantity: str


@dataclass(frozen=True)
class QuantityDecision(_Record):
    id: str
    scope: ScopeKey
    source: SourceRef
    invoice_line_id: str
    quantity: str
    unit: str
    decision_date: str


@dataclass(frozen=True)
class PaymentEvent(_Record):
    id: str
    scope: ScopeKey
    source: SourceRef
    external_reference: str
    amount_cents: int
    event_date: str
    kind: str = 'PAYMENT'
    reversal_of_id: str | None = None


@dataclass(frozen=True)
class PaymentAllocation(_Record):
    id: str
    scope: ScopeKey
    source: SourceRef
    payment_id: str
    invoice_line_id: str
    amount_cents: int


@dataclass(frozen=True)
class CreditEvent(_Record):
    id: str
    scope: ScopeKey
    source: SourceRef
    invoice_line_id: str
    credit_id: str
    amount_cents: int
    event_date: str
    kind: str
    reversal_of_id: str | None = None


@dataclass(frozen=True)
class ReturnEntitlement(_Record):
    """Explicitly pre-assessed return terms; never inferred from an RGA."""
    id: str
    scope: ScopeKey
    source: SourceRef
    invoice_line_id: str
    approved_gross_cents: int
    restocking_cents: int
    decision_date: str
    authority_source: SourceRef | None = None
    receipt_source: SourceRef | None = None
    notice_source: SourceRef | None = None
    notice_required: bool = True


TABLE_TYPES = {
    'products': ProductIdentity, 'invoices': InvoiceLine, 'contracts': ContractAuthority,
    'conversions': PackConversion, 'receipts': ReceiptEvent,
    'receipt_allocations': ReceiptAllocation, 'quantity_decisions': QuantityDecision,
    'payments': PaymentEvent, 'payment_allocations': PaymentAllocation,
    'credits': CreditEvent, 'returns': ReturnEntitlement,
}


@dataclass(frozen=True)
class ImportBatch:
    records: tuple[_Record, ...]
    scope: ApprovedScope
    holds: tuple[Hold, ...]
    declared_rows: int
    observed_rows: int
    accepted_rows: int
    rejected_rows: int
    missing_rows: int
    original_hash: str
    normalized_hash: str

    @property
    def complete(self):
        return not self.holds and self.observed_rows > 0 and self.accepted_rows == self.declared_rows


@dataclass(frozen=True)
class CanonicalBatch:
    records: tuple[_Record, ...]
    scope: ApprovedScope
    holds: tuple[Hold, ...]
    duplicate_rows: int
    import_batch: ImportBatch

    def of_type(self, cls):
        return tuple(x for x in self.records if type(x) is cls)


@dataclass(frozen=True)
class Finding:
    economic_loss_id: str
    scope: ScopeKey
    invoice_line_id: str
    billed_cents: int
    expected_cents: int
    paid_cents: int
    return_entitlement_cents: int
    gross_price_variance_cents: int
    payment_above_invoice_cents: int
    funded_exposure_cents: int
    net_issued_credit_cents: int
    applied_credit_cents: int
    refunded_credit_cents: int
    remaining_candidate_cents: int
    issued_unapplied_cents: int
    unpaid_discrepancy_cents: int
    simulated_new_realized_cents: int
    evidence: tuple[SourceRef, ...]
    trace: tuple[tuple[str, str], ...]
    status: str = 'REVIEW'


@dataclass(frozen=True)
class AuditResult:
    findings: tuple[Finding, ...]
    holds: tuple[Hold, ...]
    assessed_lines: int
    unassessed_lines: int
    skipped_cancelled_lines: int
    synthetic: bool
    source_hash: str
    normalized_hash: str
    engine_version: str = '0.1.0'

    @property
    def verified_realized_cents(self):
        # No implemented issuer-authenticated outcome channel exists in v0.1.
        return 0

    @property
    def remaining_candidate_cents(self):
        return sum(f.remaining_candidate_cents for f in self.findings)


@dataclass(frozen=True)
class RuleSetVersion:
    """Reproducibility coordinates; they are NOT proof of signed customer rules."""
    commit_sha: str
    config_sha256: str
    policy_ids: tuple[str, ...]

    def __post_init__(self):
        if type(self.commit_sha) is not str or not re.fullmatch(r'[0-9a-f]{40}', self.commit_sha):
            raise ValueError('INVALID_ENGINE_COMMIT')
        if type(self.config_sha256) is not str or not _HASH.fullmatch(self.config_sha256):
            raise ValueError('INVALID_CONFIG_DIGEST')
        if type(self.policy_ids) is not tuple or not self.policy_ids:
            raise ValueError('INVALID_POLICY_VERSIONS')
        for name in self.policy_ids:
            check_id(name)
