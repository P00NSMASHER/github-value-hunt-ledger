"""Fail-closed metadata pre-admission for independent REAL freight case replay.

No document bytes, source fetching, customer data, tariff scraping, accounting
book entry, or bank instruction. A passing result is only *ready for blind
replay*, never evidence that a source was actually checked or that RETALLY
found an error or recovered any dollars. No automatic commercial release.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Literal
from urllib.parse import urlsplit
import re


EvidenceKind = Literal[
    "ORIGINAL_CARRIER_INVOICE",
    "EFFECTIVE_RATE_AUTHORITY",
    "SHIPMENT_BOL_POD",
    "ORIGINAL_PAYMENT_CLEARING",
    "INDEPENDENT_FINAL_ADJUDICATION",
    "EXECUTED_RECOVERY_CLEARING",
]
REQUIRED_KINDS = frozenset((
    "ORIGINAL_CARRIER_INVOICE",
    "EFFECTIVE_RATE_AUTHORITY",
    "SHIPMENT_BOL_POD",
    "ORIGINAL_PAYMENT_CLEARING",
    "INDEPENDENT_FINAL_ADJUDICATION",
    "EXECUTED_RECOVERY_CLEARING",
))
ORIGIN_REQUIRED = {
    "ORIGINAL_CARRIER_INVOICE": "CARRIER_ISSUED_ORIGINAL",
    "EFFECTIVE_RATE_AUTHORITY": "EXECUTED_AGREEMENT_OR_ISSUED_TARIFF",
    "SHIPMENT_BOL_POD": "SHIPMENT_ISSUER_OR_SIGNED_DELIVERY",
    "ORIGINAL_PAYMENT_CLEARING": "INDEPENDENT_BANK_OR_PROCESSOR_CLEARED",
    "INDEPENDENT_FINAL_ADJUDICATION": "INDEPENDENT_FINAL_REVIEW",
    "EXECUTED_RECOVERY_CLEARING": "INDEPENDENT_BANK_OR_PROCESSOR_CLEARED",
}
_SHA256 = re.compile(r"[a-f0-9]{64}\Z")


@dataclass(frozen=True)
class EvidencePointer:
    """Independently reviewed source-receipt claims; no source bytes are ingested."""

    kind: EvidenceKind
    url: str
    source_sha256: str
    invoice_ref: str
    shipment_ref: str | None
    issuer_role: str
    rights_authority_url: str | None = None
    explicit_commercial_testing_grant: bool = False
    source_bytes_independently_verified: bool = False
    independently_reviewed: bool = False
    effective_from: str | None = None
    effective_until: str | None = None


@dataclass(frozen=True)
class RecoveryCaseCandidate:
    """Assertions, not evidence. Original dollars always distinct from cash."""

    legal_debtor_ref: str
    creditor_ref: str
    carrier_ref: str
    invoice_ref: str
    shipment_ref: str
    shipment_date: str
    currency: str
    billed_cents: int
    original_paid_cents: int
    controlling_charge_cents: int
    adjudicated_error_cents: int
    executed_recovery_cents: int
    original_payment_reference: str
    recovery_clearing_reference: str
    outcome_independent_of_retally: bool
    blind_label_frozen_sha256: str | None
    evidence: tuple[EvidencePointer, ...]
    liability_transfer_only: bool = False


@dataclass(frozen=True)
class AdmissionDecision:
    state: Literal["READY_FOR_INDEPENDENT_BLIND_REPLAY", "RESEARCH_HOLD"]
    flags: tuple[str, ...]
    # Source-metadata review cannot verify bank value or customer recoveries.
    verified_retally_recovered_cents: int = 0
    freight_accuracy_independently_validated: bool = False
    production_admission_authorized: bool = False


def _ref(raw: str) -> str | None:
    if not isinstance(raw, str) or not raw.strip():
        return None
    return " ".join(raw.strip().upper().split())


def _iso(raw: str) -> date | None:
    if not isinstance(raw, str):
        return None
    try:
        parsed = date.fromisoformat(raw)
        if parsed.isoformat() != raw:
            return None
        return parsed
    except ValueError:
        return None


def _https(url: str | None) -> bool:
    if not isinstance(url, str):
        return False
    try:
        p = urlsplit(url)
        return (
            p.scheme == "https" and bool(p.hostname)
            and p.username is None and p.password is None
            and p.port in (None, 443)
            and not p.fragment and len(url) < 1800
            and not any(ord(c) < 32 for c in url)
        )
    except ValueError:
        return False


def _cents(v: int) -> bool:
    return type(v) is int and 0 <= v <= 2**63 - 1


def assess_candidate(case: RecoveryCaseCandidate) -> AdmissionDecision:
    """Documentary screening only. ALL money remains unverified candidate metadata."""
    flags: set[str] = set()
    if case.liability_transfer_only:
        flags.add("NONCASH_LIABILITY_TRANSFER_NOT_A_RECOVERY")
    for ref in (case.legal_debtor_ref, case.creditor_ref, case.carrier_ref,
                case.invoice_ref, case.shipment_ref, case.original_payment_reference,
                case.recovery_clearing_reference):
        if not _ref(ref):
            flags.add("CASE_IDENTITY_OR_PAYMENT_LINK_MISSING")
    shipment = _iso(case.shipment_date)
    if not shipment:
        flags.add("SHIPMENT_DATE_UNVERIFIED")
    if case.currency != "USD":
        flags.add("CURRENCY_SCOPE_UNSUPPORTED")
    for v in (case.billed_cents, case.original_paid_cents,
              case.controlling_charge_cents, case.adjudicated_error_cents,
              case.executed_recovery_cents):
        if not _cents(v):
            flags.add("INVALID_CENTS")
    if "INVALID_CENTS" not in flags:
        if (case.billed_cents <= case.controlling_charge_cents
                or case.billed_cents - case.controlling_charge_cents
                != case.adjudicated_error_cents):
            flags.add("ADJUDICATED_ERROR_ARITHMETIC_UNSUPPORTED")
        # Partial customer payment may be valid but needs an explicit allocation
        # that this narrow, full-chain positive benchmark cannot currently model.
        if case.original_paid_cents != case.billed_cents:
            flags.add("ORIGINAL_PAYMENT_ALLOCATION_UNVERIFIED")
        if (case.executed_recovery_cents == 0
                or case.executed_recovery_cents > case.adjudicated_error_cents):
            flags.add("RECOVERY_NOT_EXECUTED_OR_EXCEEDS_ERROR")
    if not case.outcome_independent_of_retally:
        flags.add("NOT_INDEPENDENTLY_ADJUDICATED")
    if (not isinstance(case.blind_label_frozen_sha256, str)
            or not _SHA256.fullmatch(case.blind_label_frozen_sha256)):
        flags.add("BLIND_FROZEN_LABEL_MISSING")
    if not isinstance(case.evidence, tuple):
        flags.add("UNTRUSTED_EVIDENCE_SHAPE")
        records: tuple[EvidencePointer, ...] = ()
    else:
        records = case.evidence
    kinds = [x.kind for x in records if isinstance(x, EvidencePointer)]
    for kind in REQUIRED_KINDS - set(kinds):
        flags.add("MISSING_" + kind)
    if len(kinds) != len(set(kinds)):
        flags.add("DUPLICATE_EVIDENCE_ROLE")
    if len(records) != len(kinds) or len(records) > 20:
        flags.add("UNTRUSTED_EVIDENCE_SHAPE")
    digests: set[str] = set()
    for doc in records:
        if not isinstance(doc, EvidencePointer):
            continue
        if doc.kind not in REQUIRED_KINDS:
            flags.add("UNKNOWN_EVIDENCE_ROLE")
            continue
        if not _https(doc.url) or not isinstance(doc.source_sha256, str) or not _SHA256.fullmatch(doc.source_sha256):
            flags.add("SOURCE_PROVENANCE_UNVERIFIED")
        if doc.source_sha256 in digests:
            flags.add("INDEPENDENT_DOCUMENT_PROVENANCE_NOT_DISTINCT")
        digests.add(doc.source_sha256)
        if _ref(doc.invoice_ref) != _ref(case.invoice_ref):
            flags.add("INVOICE_IDENTITY_MISMATCH")
        if doc.kind in ("ORIGINAL_CARRIER_INVOICE", "SHIPMENT_BOL_POD",
                        "EFFECTIVE_RATE_AUTHORITY", "INDEPENDENT_FINAL_ADJUDICATION"):
            if _ref(doc.shipment_ref) != _ref(case.shipment_ref):
                flags.add("SHIPMENT_IDENTITY_MISMATCH")
        elif doc.shipment_ref and _ref(doc.shipment_ref) != _ref(case.shipment_ref):
            flags.add("SHIPMENT_IDENTITY_MISMATCH")
        if doc.issuer_role != ORIGIN_REQUIRED[doc.kind]:
            flags.add("NOT_ORIGINAL_OR_INDEPENDENT_SOURCE_" + doc.kind)
        if (not doc.explicit_commercial_testing_grant
                or not _https(doc.rights_authority_url)):
            flags.add("COMMERCIAL_TEST_RIGHTS_NOT_CLEARED")
        if not doc.source_bytes_independently_verified or not doc.independently_reviewed:
            flags.add("SOURCE_NOT_INDEPENDENTLY_VERIFIED")
        if doc.kind == "EFFECTIVE_RATE_AUTHORITY":
            beginning = _iso(doc.effective_from)
            ending = _iso(doc.effective_until) if doc.effective_until else None
            if (not shipment or not beginning or beginning > shipment
                    or (ending is not None and (ending < shipment or ending < beginning))):
                flags.add("RATE_NOT_CONFIRMED_EFFECTIVE_AT_SHIPMENT")
    return AdmissionDecision(
        state="RESEARCH_HOLD" if flags else "READY_FOR_INDEPENDENT_BLIND_REPLAY",
        flags=tuple(sorted(flags)),
    )
