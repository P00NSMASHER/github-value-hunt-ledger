"""Priority-2 source-bound freight audit review: strict authority and joins.

Everything this module produces is review evidence, NEVER an independently
adjudicated freight error, cleared bank payment, customer approval or recovery.
It deliberately does not enable general customer PDF intake or external actions.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass
from hashlib import sha256
from typing import Iterable

from freight.canonical_schema import (
    CanonicalFreightRecord, ShipmentFacts, SourceArtifact, verify_record,
)
from freight.contracts import canonical_hash
from freight.rate_authority import AuthorityBook
from freight.rating_engine import RATED, rate_record
from freight.scoped_reconciliation import ScopedTxn, reconcile_scoped
from recoveryworks.reconciliation_kernel import (
    ManyToOneConfig, ReconConfig, reconcile,
)


@dataclass(frozen=True)
class ShipmentSourceWitness:
    """Content-derived corroboration, not a self-certified independent attestation."""
    source_sha256: str
    source_kind: str
    shipment_facts_sha256: str
    supported_fields: tuple[str, ...]
    witness_hash: str

    @property
    def externally_authenticated(self) -> bool:
        # There is no authenticated source issuer / signing service in this
        # research module. Never let a caller-set 'verified' Boolean mint one.
        return False


REQUIRED_SHIPMENT_FIELDS = frozenset({
    "shipment_id", "carrier_id", "mode", "service_date",
    "origin_postal", "destination_postal", "actual_weight_grams",
    "package_count",
})


def witness_shipment_source(
    shipment: ShipmentFacts,
    *, source_bytes: bytes, source_kind: str,
    supported_fields: Iterable[str],
) -> ShipmentSourceWitness:
    if not isinstance(shipment, ShipmentFacts):
        raise ValueError("complete canonical shipment facts required")
    if not isinstance(source_bytes, bytes) or not source_bytes or len(source_bytes) > 1_000_000:
        raise ValueError("bounded original supporting document bytes are required")
    if source_kind not in {"BILL_OF_LADING", "SCALE_TICKET", "SIGNED_SHIPMENT_EXPORT"}:
        raise ValueError("shipment support source type not recognized")
    fields = tuple(sorted(supported_fields))
    if fields != tuple(sorted(set(fields))):
        raise ValueError("duplicate supported shipment field")
    if not REQUIRED_SHIPMENT_FIELDS.issubset(fields):
        raise ValueError("the source does not support all required shipment facts")
    if any(field not in ShipmentFacts.__dataclass_fields__ for field in fields):
        raise ValueError("support witness contains an unknown shipment field")
    source = sha256(source_bytes).hexdigest()
    fact_hash = canonical_hash({"schema": 1, "shipment": asdict(shipment)})
    body = {
        "schema": 1, "kind": source_kind, "source": source,
        "shipment": fact_hash, "supported_fields": fields,
    }
    return ShipmentSourceWitness(
        source, source_kind, fact_hash, fields, canonical_hash(body),
    )


@dataclass(frozen=True)
class EvidenceBoundRateReview:
    status: str
    blockers: tuple[str, ...]
    invoice_record_sha256: str
    shipment_witness_sha256: str | None
    controlling_authority_sha256: str | None
    provisional_expected_cents: int | None
    provisional_variance_cents: int | None
    externally_verified_freight_error_cents: None
    externally_verified_cash_recovered_cents: int
    independent_accuracy_scored: bool
    review_hash: str


def review_freight_rate(
    record: CanonicalFreightRecord,
    authorities: AuthorityBook,
    *,
    shipment_witness: ShipmentSourceWitness | None = None,
    rejected_authority_hashes: Iterable[str] = (),
) -> EvidenceBoundRateReview:
    """Strict opt-in rate proof: overlapping authorities never auto-win.

    Real contracts may be superseded, but 'priority' alone and an uploaded
    'verified' Boolean do not prove which rate was legally controlling.
    """
    verify_record(record)
    if not isinstance(authorities, AuthorityBook):
        raise ValueError("typed, hash-verified authority book required")
    missing = set()
    source_hashes = {s.sha256 for s in record.sources}
    if shipment_witness is None:
        missing.add("INDEPENDENT_SHIPMENT_DOCUMENT_MISSING")
    elif not isinstance(shipment_witness, ShipmentSourceWitness):
        raise ValueError("typed shipment support witness required")
    else:
        check = canonical_hash({
            "schema": 1, "kind": shipment_witness.source_kind,
            "source": shipment_witness.source_sha256,
            "shipment": shipment_witness.shipment_facts_sha256,
            "supported_fields": shipment_witness.supported_fields,
        })
        if check != shipment_witness.witness_hash:
            raise ValueError("shipment witness content fingerprint changed")
        if shipment_witness.shipment_facts_sha256 != canonical_hash({
            "schema": 1, "shipment": asdict(record.shipment),
        }):
            missing.add("SHIPMENT_WITNESS_FACTS_CONFLICT")
        if shipment_witness.source_sha256 in source_hashes:
            missing.add("SHIPMENT_SOURCE_NOT_INDEPENDENT_FROM_INVOICE")
        if not shipment_witness.externally_authenticated:
            missing.add("SHIPMENT_SOURCE_ISSUER_NOT_AUTHENTICATED")
    day = record.shipment.service_date
    overlapping = sorted(
        (a for a in authorities.authorities if
         (a.buyer_id, a.business_unit, a.customer_id, a.carrier_id, a.currency, a.mode)
         == (record.buyer_id, record.business_unit, record.customer_id,
             record.shipment.carrier_id, record.currency, record.mode)
         and a.effective_from <= day
         and (a.effective_to is None or day <= a.effective_to)),
        key=lambda a: a.authority_hash,
    )
    denied = tuple(sorted(set(rejected_authority_hashes)))
    if any(len(v) != 64 or any(ch not in "0123456789abcdef" for ch in v) for v in denied):
        raise ValueError("rejected authority digests must be exact SHA-256")
    if not overlapping:
        missing.add("NO_EFFECTIVE_SHIPMENT_RATE_AUTHORITY")
    elif len(overlapping) > 1:
        missing.add("MULTIPLE_OVERLAPPING_RATE_AUTHORITIES_NEED_INDEPENDENT_SUPERSESSION")
    authority = overlapping[0] if len(overlapping) == 1 else None
    if authority is not None:
        if authority.authority_hash in denied:
            missing.add("REJECTED_OR_DISPUTED_RATE_TENDER")
        if not authority.verified:
            missing.add("RATE_AUTHORITY_NOT_VERIFIED")
        if authority.source_sha256 in source_hashes:
            missing.add("RATE_AUTHORITY_NOT_INDEPENDENT_FROM_INVOICE")
        if shipment_witness and authority.source_sha256 == shipment_witness.source_sha256:
            missing.add("RATE_AUTHORITY_NOT_INDEPENDENT_FROM_SHIPMENT_SUPPORT")
        # A compiled controlling flag is a source declaration, not proof
        # of genuine executed buyer contracts or rights.
        missing.add("BUYER_CONTRACT_RIGHTS_AND_TERMS_NOT_EXTERNALLY_AUTHENTICATED")
    expected = variance = None
    if authority is not None and authority.verified and authority.authority_hash not in denied:
        result = rate_record(record, AuthorityBook((authority,)))
        if result.status == RATED and not result.blockers:
            expected = result.expected_total_cents
            variance = result.variance_cents
        else:
            missing.update(result.blockers)
            missing.add("RATING_MODEL_REVIEW_REQUIRED")
    missing.add("BANK_CLEARED_PAYMENT_NOT_INDEPENDENTLY_VERIFIED")
    missing.add("FREIGHT_ERROR_NOT_INDEPENDENTLY_ADJUDICATED")
    blockers = tuple(sorted(missing))
    body = {
        "schema": 1, "record": record.record_hash,
        "shipment_witness": shipment_witness.witness_hash if shipment_witness else None,
        "authority": authority.authority_hash if authority else None,
        "overlap": tuple(a.authority_hash for a in overlapping),
        "disputed_authorities": denied, "blockers": blockers,
        "expected": expected, "provisional_variance": variance,
        "real_verified": None, "real_recovered": 0,
    }
    return EvidenceBoundRateReview(
        "REVIEW_REQUIRED", blockers, record.record_hash,
        shipment_witness.witness_hash if shipment_witness else None,
        authority.authority_hash if authority else None, expected, variance,
        None, 0, False, canonical_hash(body),
    )


@dataclass(frozen=True)
class ReconciliationEvidenceRow:
    row_sha256: str
    side: str
    status: str
    reason: str
    independently_verified_payment: bool


@dataclass(frozen=True)
class ReconciliationEvidenceReport:
    invoices: int
    counterpart_declarations: int
    source_declared_matches: int
    source_declared_counterpart_matches: int
    invoice_unknown: int
    counterpart_unknown: int
    rows: tuple[ReconciliationEvidenceRow, ...]
    receipt_sha256: str
    summary_hash: str
    authentic_bank_proof_established: bool = False
    real_freight_detection_accuracy: None = None


def reconcile_invoice_evidence(
    invoices: Iterable[ScopedTxn],
    counterpart_declarations: Iterable[ScopedTxn],
    *, max_group_size: int = 32, date_window_days: int = 30,
) -> ReconciliationEvidenceReport:
    """Large source-reference populations; preserve each unresolved row.

    This is same-source reconciliation. Even a row labeled BANK_CLEARED is
    not an authenticated receipt. No cross-supplier fallback is permitted.
    """
    a = tuple(invoices)
    b = tuple(counterpart_declarations)
    baseline = reconcile_scoped(
        a, b, group_size_limit=max_group_size,
        date_window_days=date_window_days,
    )
    def key(row):
        reference = row.txn.reference
        if not isinstance(reference, str) or not reference.strip():
            return None
        return (row.buyer_id, row.business_unit, row.counterparty_id,
                row.txn.currency, reference.strip())
    aa: dict[tuple, list[ScopedTxn]] = defaultdict(list)
    bb: dict[tuple, list[ScopedTxn]] = defaultdict(list)
    for item in a:
        if (k := key(item)) is not None:
            aa[k].append(item)
    for item in b:
        if (k := key(item)) is not None:
            bb[k].append(item)
    matched_a: set[str] = set()
    matched_b: set[str] = set()
    bounds_a: set[str] = set()
    bounds_b: set[str] = set()
    for k in sorted(set(aa) | set(bb)):
        lhs = aa.get(k, [])
        rhs = bb.get(k, [])
        if not lhs or not rhs:
            continue
        if len(lhs) > max_group_size or len(rhs) > max_group_size:
            bounds_a.update(x.txn.id for x in lhs)
            bounds_b.update(x.txn.id for x in rhs)
            continue
        config = ReconConfig(
            decimals=2, date_window_days=date_window_days,
            amount_tolerance_bps=0, amount_tolerance_min_minor=0,
            many_to_one=ManyToOneConfig(
                enabled=True, date_window_days=date_window_days,
                tolerance_bps=0, max_group_size=max_group_size,
                max_candidates=max_group_size, max_nodes=250_000,
            ),
        )
        result = reconcile((x.txn for x in lhs), (x.txn for x in rhs), config)
        for match in result.matches:
            matched_a.update(match.internal_ids)
            matched_b.update(match.settlement_ids)
    if len(matched_a) != baseline.matched_internal or len(matched_b) != baseline.matched_counterparts:
        raise ValueError("scoped matching and row-level evidence census disagree")
    rows = []
    for side, items, matched, limited in (
        ("INVOICE", a, matched_a, bounds_a),
        ("DECLARED_COUNTERPART", b, matched_b, bounds_b),
    ):
        for item in items:
            if item.txn.id in matched:
                status, reason = "SOURCE_DECLARATION_MATCH", "REFERENCE_AND_AMOUNT_MATCHED_WITHIN_SCOPE"
            elif item.txn.id in limited:
                status, reason = "UNKNOWN", "GROUP_BOUNDS_EXCEEDED"
            elif key(item) is None:
                status, reason = "UNKNOWN", "MISSING_OR_BLANK_REFERENCE"
            elif not (bb if side == "INVOICE" else aa).get(key(item)):
                status, reason = "UNKNOWN", "NO_SCOPE_MATCHED_COUNTERPART"
            else:
                status, reason = "UNKNOWN", "AMOUNT_DATE_OR_AMBIGUITY_REVIEW_REQUIRED"
            rows.append(ReconciliationEvidenceRow(
                canonical_hash({"schema": 1, "side": side, "row": asdict(item)}),
                side, status, reason, False,
            ))
    rows.sort(key=lambda row: (row.side, row.row_sha256))
    unknown_a = sum(x.side == "INVOICE" and x.status == "UNKNOWN" for x in rows)
    unknown_b = sum(x.side == "DECLARED_COUNTERPART" and x.status == "UNKNOWN" for x in rows)
    if unknown_a != baseline.unmatched_internal or unknown_b != baseline.unmatched_counterparts:
        raise ValueError("unmatched source population silently lost")
    body = {
        "schema": 1, "source_reconciliation_hash": baseline.result_hash,
        "rows": [asdict(x) for x in rows],
        "invoices": len(a), "counterparts": len(b),
        "matched_invoice": len(matched_a), "matched_counterpart": len(matched_b),
        "unknown_invoice": unknown_a, "unknown_counterpart": unknown_b,
        "independently_authenticated_bank_clearing": False,
        "freight_detection_accuracy": None,
    }
    return ReconciliationEvidenceReport(
        len(a), len(b), len(matched_a), len(matched_b),
        unknown_a, unknown_b, tuple(rows),
        canonical_hash(body), baseline.result_hash,
    )
