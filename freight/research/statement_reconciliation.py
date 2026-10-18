"""Research-only, zero-rights-assumption freight invoice/statement comparator.

Inputs are *structured* values from a separately authorized extraction process.
This code cannot inspect PDFs, validate an underlying rate, create a recovery, or
assert receipt of funds. It contains no GlobalTranz customer invoice records.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


RecordKind = Literal["BASE", "ADJUSTMENT"]


@dataclass(frozen=True)
class StatementLine:
    invoice_ref: str
    kind: RecordKind
    invoice_face_cents: int | None
    statement_original_cents: int
    statement_open_cents: int
    parent_ref: str | None = None
    shipment_pro: str | None = None
    shipment_bol: str | None = None


@dataclass(frozen=True)
class ClaimSnapshot:
    source_label: str
    claim_cents: int
    debtor_ref: str | None = None
    creditor_ref: str | None = None
    claim_ref: str | None = None


@dataclass(frozen=True)
class Reconciliation:
    row_count: int
    invoice_family_count: int | None
    invoice_face_checked_count: int
    statement_original_cents: int
    statement_open_cents: int
    open_balance_reconciles: bool
    exception_codes: tuple[str, ...]
    state: Literal["RESEARCH_ARITHMETIC_ONLY", "REVIEW_REQUIRED"]
    verified_overcharge_cents: int = 0
    verified_recovered_cents: int = 0
    commercial_reuse_authorized: bool = False


def _money(value: int | None, *, optional: bool = False) -> None:
    if value is None and optional:
        return
    if type(value) is not int or not 0 <= value <= 2**63 - 1:
        raise ValueError("money must be nonnegative integer cents (not bool/float)")


def _ref(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("invoice_ref required")
    return value.strip().upper()


def compare(
    rows: list[StatementLine],
    *,
    statement_control_cents: int,
    claims: list[ClaimSnapshot] | None = None,
) -> Reconciliation:
    """Check accounting invariants. No amount delta is classified as recovery.

    Not designed for direct production invoice import; no source documents stored.
    """
    _money(statement_control_cents)
    if not rows:
        raise ValueError("an empty statement cannot establish invoice coverage")
    seen: set[str] = set()
    flags: set[str] = set()
    sum_original = sum_open = checked = 0
    bases = {_ref(r.invoice_ref): r for r in rows if r.kind == "BASE"}
    for row in rows:
        ref = _ref(row.invoice_ref)
        if ref in seen:
            raise ValueError("duplicate invoice reference; fail closed")
        seen.add(ref)
        if row.kind not in ("BASE", "ADJUSTMENT"):
            raise ValueError("unknown kind")
        for amount in (row.statement_original_cents, row.statement_open_cents):
            _money(amount)
        _money(row.invoice_face_cents, optional=True)
        if row.statement_open_cents > row.statement_original_cents:
            flags.add("BALANCE_INCREASE_REQUIRES_SOURCE_EVIDENCE")
        if row.statement_open_cents != row.statement_original_cents:
            flags.add("UNEXPLAINED_BALANCE_CHANGE_NO_RECOVERY_CLAIM")
        if row.invoice_face_cents is None:
            flags.add("MISSING_INVOICE_FACE")
        else:
            checked += 1
            if row.invoice_face_cents != row.statement_original_cents:
                flags.add("INVOICE_FACE_STATEMENT_MISMATCH")
        if row.kind == "ADJUSTMENT":
            parent = bases.get(_ref(row.parent_ref)) if row.parent_ref else None
            if parent is None:
                flags.add("UNRESOLVED_ADJUSTMENT_PARENT")
            else:
                links = (row.shipment_pro, row.shipment_bol, parent.shipment_pro, parent.shipment_bol)
                if any(not isinstance(link, str) or not link.strip() for link in links):
                    flags.add("ADJUSTMENT_SHIPMENT_IDENTITY_UNVERIFIED")
                elif (row.shipment_pro.strip().upper() != parent.shipment_pro.strip().upper()
                      or row.shipment_bol.strip().upper() != parent.shipment_bol.strip().upper()):
                    flags.add("ADJUSTMENT_SHIPMENT_IDENTITY_MISMATCH")
        elif row.parent_ref:
            flags.add("BASE_CANNOT_HAVE_PARENT")
        sum_original += row.statement_original_cents
        sum_open += row.statement_open_cents
    if sum_open != statement_control_cents:
        flags.add("STATEMENT_CONTROL_TOTAL_MISMATCH")
    claims = claims or []
    if len({c.source_label for c in claims}) < len(claims):
        raise ValueError("duplicate claim snapshot source")
    for claim in claims:
        _money(claim.claim_cents)
    if claims:
        identities = []
        for claim in claims:
            identity = (claim.debtor_ref, claim.creditor_ref, claim.claim_ref)
            if any(not isinstance(part, str) or not part.strip() for part in identity):
                flags.add("CLAIM_IDENTITY_UNVERIFIED")
            else:
                identities.append(tuple(part.strip().upper() for part in identity))
        if len(identities) != len(claims) or len(set(identities)) != 1:
            flags.add("CROSS_CLAIM_COMPARISON_BLOCKED")
        else:
            if len({c.claim_cents for c in claims}) > 1:
                flags.add("CONFLICTING_EXTERNAL_CLAIM_SNAPSHOTS")
            if any(c.claim_cents != sum_open for c in claims):
                flags.add("EXTERNAL_CLAIM_DIFFERS_FROM_STATEMENT")
    return Reconciliation(
        row_count=len(rows),
        invoice_family_count=None,  # PRO/BOL and buyer evidence required; never suffix-count.
        invoice_face_checked_count=checked,
        statement_original_cents=sum_original,
        statement_open_cents=sum_open,
        open_balance_reconciles=sum_open == statement_control_cents,
        exception_codes=tuple(sorted(flags)),
        state="REVIEW_REQUIRED" if flags else "RESEARCH_ARITHMETIC_ONLY",
    )


@dataclass(frozen=True)
class SourceReferencedLiabilityTransfer:
    """Court-disposition metadata, not certified document content or cash proof."""

    original: ClaimSnapshot
    revised: ClaimSnapshot
    transferred_liability_cents: int
    receiving_entity: str
    public_court_order_url: str


@dataclass(frozen=True)
class LiabilityTransferAssessment:
    state: Literal["SOURCE_REFERENCED_LIABILITY_TRANSFER", "REVIEW_REQUIRED"]
    exception_codes: tuple[str, ...]
    transferred_liability_cents: int
    remaining_claim_cents: int
    verified_recovered_cents: int = 0
    verified_overcharge_cents: int = 0
    commercial_reuse_authorized: bool = False


def assess_claim_liability_transfer(record: SourceReferencedLiabilityTransfer) -> LiabilityTransferAssessment:
    """Check evidence *references* and ledger arithmetic without inferring cash.

    A matching HTTPS court link is a required provenance pointer, not proof its
    contents were read or independently adjudicated by this pure function.
    """
    _money(record.original.claim_cents)
    _money(record.revised.claim_cents)
    _money(record.transferred_liability_cents)
    flags: set[str] = set()
    identities = []
    for item in (record.original, record.revised):
        parts = (item.debtor_ref, item.creditor_ref, item.claim_ref)
        if any(not isinstance(p, str) or not p.strip() for p in parts):
            flags.add("CLAIM_IDENTITY_UNVERIFIED")
            continue
        identities.append(tuple(p.strip().upper() for p in parts))
    if len(identities) != 2 or identities[0] != identities[1]:
        flags.add("CROSS_CLAIM_COMPARISON_BLOCKED")
    if (record.original.claim_cents - record.transferred_liability_cents
            != record.revised.claim_cents):
        flags.add("CLAIM_TRANSFER_ARITHMETIC_MISMATCH")
    if not isinstance(record.receiving_entity, str) or not record.receiving_entity.strip():
        flags.add("TRANSFER_RECEIVING_ENTITY_UNVERIFIED")
    if (not isinstance(record.public_court_order_url, str)
            or not record.public_court_order_url.startswith(
                "https://document.epiq11.com/document/getdocumentsbydocket/"
            )):
        flags.add("PUBLIC_COURT_ORDER_REFERENCE_MISSING")
    return LiabilityTransferAssessment(
        state="REVIEW_REQUIRED" if flags else "SOURCE_REFERENCED_LIABILITY_TRANSFER",
        exception_codes=tuple(sorted(flags)),
        transferred_liability_cents=record.transferred_liability_cents,
        remaining_claim_cents=record.revised.claim_cents,
    )
