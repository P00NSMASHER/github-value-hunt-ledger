"""Conservative end-to-end freight *evidence* pipeline, not a customer pilot.

The source-pinned PDF parser and a separately supplied shipment document are
bound before rating; ambiguous tariffs, unverified settlement and absent human
independent adjudication always hold release. A historical invoice face never
becomes a recovery claim merely because arithmetic balances.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable

from freight.canonical_schema import ShipmentFacts
from freight.contracts import canonical_hash
from freight.original_pdf_extraction import (
    FieldWitness, KNOWN_ORIGINALS, OriginalExtractionBatch, OriginalInvoice,
    bind_independent_shipment, parse_original_pdf,
)
from freight.priority2_evidence import (
    EvidenceBoundRateReview, ShipmentSourceWitness, review_freight_rate,
)
from freight.rate_authority import AuthorityBook


@dataclass(frozen=True)
class OriginalEvidenceReview:
    issuer: str
    source_sha256: str
    invoice_count: int
    face_amounts_verified: int
    source_bytes_replayed_and_verified: bool
    calculated_face_amount_count: int
    frozen_source_expected_invoice_count: int
    frozen_original_population_complete: bool
    invoices_missing_freight_accuracy_evidence: int
    unresolved_invoice_count: int
    provisional_rated_count: int
    provisional_positive_variance_cents: int
    amount_currency: str
    case_receipt_hashes: tuple[str, ...]
    report_sha256: str
    commercially_recovered_cents: int = 0
    independently_adjudicated_freight_errors: int = 0
    bank_cleared_payment_receipts: int = 0
    real_precision: None = None
    real_recall: None = None


def _validated_original(invoice: OriginalInvoice, *, issuer: str, expected_source: str) -> None:
    if not isinstance(invoice, OriginalInvoice) or invoice.issuer != issuer:
        raise ValueError("original invoice has incorrect or missing source profile")
    if invoice.source_sha256 != expected_source:
        raise ValueError("original invoice source hash does not match approved original")
    if invoice.original_face_cents < 0 or invoice.signed_net_cents != invoice.original_face_cents:
        raise ValueError("original invoice charges do not conserve printed face amount")
    if invoice.page < 1 or not invoice.invoice_id:
        raise ValueError("original invoice identity/page missing")
    body = {
        "schema": 1, "issuer": invoice.issuer, "id": invoice.invoice_id,
        "page": invoice.page, "source": invoice.source_sha256,
        "date": invoice.invoice_date, "gross": invoice.gross_cents,
        "discounts": [asdict(x) for x in invoice.adjustments],
        "lines": [asdict(x) for x in invoice.charges],
        "face": invoice.original_face_cents,
        "blockers": invoice.blockers,
    }
    if invoice.document_hash != canonical_hash(body):
        raise ValueError("original invoice page-level arithmetic/proof hash altered")
    fields = {w.field: w for w in invoice.field_witnesses}
    for required, amount in (("invoice_id", invoice.invoice_id),
                             ("face_total_cents", str(invoice.original_face_cents))):
        witness = fields.get(required)
        if not isinstance(witness, FieldWitness) or witness.value != amount:
            raise ValueError("required original PDF field witness missing or changed")
    count_witness = fields.get("charge_token_count")
    if count_witness is not None and count_witness.value != str(len(invoice.charges) + len(invoice.adjustments)):
        raise ValueError("PDF charge-token source witness does not match original charge census")
    if invoice.invoice_date is not None:
        date_witness = fields.get("invoice_date")
        if date_witness is None or date_witness.value != invoice.invoice_date:
            raise ValueError("PDF issue date is not bound to original page")
    for witness in invoice.field_witnesses:
        if witness.page != invoice.page or witness.source_sha256 != expected_source:
            raise ValueError("PDF page/source witness incorrectly attributed")


def verify_original_batch(batch: OriginalExtractionBatch) -> None:
    if not isinstance(batch, OriginalExtractionBatch):
        raise ValueError("typed original-extraction batch required")
    spec = KNOWN_ORIGINALS.get(batch.issuer)
    if spec is None or batch.source_sha256 != spec["sha256"]:
        raise ValueError("original PDF is not an authorized frozen research profile")
    if batch.document_page_count != spec["pages"]:
        raise ValueError("original PDF page count differs from frozen source")
    if not batch.invoices or len(batch.invoices) > spec["faces"]:
        raise ValueError("original PDF invoice population exceeds authorized source")
    ids = [x.invoice_id for x in batch.invoices]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate original PDF invoice identity")
    for invoice in batch.invoices:
        _validated_original(invoice, issuer=batch.issuer, expected_source=batch.source_sha256)
    if batch.original_amount_match_count != len(batch.invoices):
        raise ValueError("original invoice face total denominator changed")
    if batch.typed_adjustment_invoice_count != sum(bool(x.adjustments) for x in batch.invoices):
        raise ValueError("typed original discount population changed")
    if batch.incomplete_charge_breakdown_count != sum(
        "CHARGE_LINES_NOT_INDEPENDENTLY_EXTRACTED" in x.blockers for x in batch.invoices
    ):
        raise ValueError("incomplete charge-line census changed")
    expected_batch_hash = canonical_hash({
        "schema": 1, "source": batch.source_sha256, "issuer": batch.issuer,
        "invoice_proofs": [x.document_hash for x in batch.invoices],
    })
    if batch.extraction_hash != expected_batch_hash:
        raise ValueError("original extraction manifest hash altered")


def review_original_extraction(
    batch: OriginalExtractionBatch,
    *,
    original_pdf_bytes: bytes | None = None,
    shipment_by_invoice: dict[str, tuple[ShipmentFacts, ShipmentSourceWitness]] | None = None,
    authorities: AuthorityBook | None = None,
    buyer_id: str = "RESEARCH_ONLY",
    business_unit: str = "ISOLATED",
    customer_id: str = "RESEARCH_BUYER",
    rejected_authorities: Iterable[str] = (),
) -> OriginalEvidenceReview:
    """No real claim, contact, release, invoice upload or verified-dollar output."""
    verify_original_batch(batch)
    source_bytes_verified = False
    if original_pdf_bytes is not None:
        if not isinstance(original_pdf_bytes, bytes):
            raise ValueError("original PDF byte evidence must be bytes")
        # A copied SHA or self-authored field manifest is not original-document
        # proof. Replay the *exact bytes* through the same approved parser.
        independent_replay = parse_original_pdf(batch.issuer, original_pdf_bytes)
        if independent_replay != batch:
            raise ValueError("declared invoice fields do not match original PDF source bytes")
        source_bytes_verified = True
    if authorities is None:
        authorities = AuthorityBook(())
    if not isinstance(authorities, AuthorityBook):
        raise ValueError("typed authority book required")
    if shipment_by_invoice is None:
        shipment_by_invoice = {}
    if set(shipment_by_invoice).difference(x.invoice_id for x in batch.invoices):
        raise ValueError("shipment evidence references an invoice outside the frozen source")
    count_rated = candidate_positive = 0
    proof_hashes = []
    for invoice in batch.invoices:
        candidate: EvidenceBoundRateReview | None = None
        blockers = set(invoice.blockers)
        submitted = shipment_by_invoice.get(invoice.invoice_id)
        if submitted is None:
            blockers.add("INDEPENDENT_SHIPMENT_EVIDENCE_MISSING")
        elif not isinstance(submitted, tuple) or len(submitted) != 2:
            raise ValueError("shipment submission must contain typed facts and witness")
        elif invoice.invoice_date is None or "CHARGE_LINES_NOT_INDEPENDENTLY_EXTRACTED" in invoice.blockers:
            blockers.add("ORIGINAL_INVOICE_NOT_RATEABLE")
        elif any(charge.charge_code in {"ORIGINAL_PDF_CHARGE", "UNALLOCATED_INVOICE_TOTAL"}
                 for charge in invoice.charges):
            # Unspecialized PDF charge tokens are exact money, not independent
            # FUEL/LINEHAUL/rate-line classification. Do not silently rate a
            # face amount against a line-item tariff without source evidence.
            blockers.add("ORIGINAL_PDF_CHARGE_CODES_NOT_INDEPENDENTLY_MAPPED")
        else:
            shipment, witness = submitted
            if not isinstance(shipment, ShipmentFacts) or not isinstance(witness, ShipmentSourceWitness):
                raise ValueError("shipment facts and witness must be typed")
            from datetime import datetime, timezone
            observed = datetime(2026, 10, 22, tzinfo=timezone.utc).isoformat(timespec="microseconds").replace("+00:00","Z")
            record = bind_independent_shipment(
                invoice, buyer_id=buyer_id, business_unit=business_unit,
                customer_id=customer_id, currency="USD",
                shipment=shipment, observed_at=observed,
            )
            candidate = review_freight_rate(
                record, authorities, shipment_witness=witness,
                rejected_authority_hashes=rejected_authorities,
            )
            blockers.update(candidate.blockers)
            if candidate.provisional_expected_cents is not None:
                count_rated += 1
                candidate_positive += candidate.provisional_variance_cents or 0
        blockers.update((
            "NO_INDEPENDENT_BANK_CLEARED_PAYMENT_EVIDENCE",
            "NO_INDEPENDENT_FREIGHT_ERROR_ADJUDICATION",
            "NO_AUTHORIZED_REAL_CUSTOMER_PILOT",
        ))
        proof_hashes.append(canonical_hash({
            "schema": 1, "original": invoice.document_hash,
            "rate": candidate.review_hash if candidate else None,
            "blockers": sorted(blockers),
            "claimable": 0, "independent_labels": 0,
        }))
    body = {
        "schema": 1, "original": batch.extraction_hash,
        "invoice_census": len(batch.invoices),
        "original_source_expected_census": KNOWN_ORIGINALS[batch.issuer]["faces"],
        "original_population_complete": len(batch.invoices) == KNOWN_ORIGINALS[batch.issuer]["faces"],
        "original_amounts_verified": batch.original_amount_match_count if source_bytes_verified else 0,
        "original_source_bytes_replayed": source_bytes_verified,
        "provisional_rated": count_rated,
        "provisional_positive_cents": candidate_positive,
        "case_proofs": proof_hashes, "real_cash": 0,
        "real_independent_adjudications": 0,
    }
    return OriginalEvidenceReview(
        batch.issuer, batch.source_sha256, len(batch.invoices),
        batch.original_amount_match_count if source_bytes_verified else 0,
        source_bytes_verified,
        batch.original_amount_match_count,
        KNOWN_ORIGINALS[batch.issuer]["faces"],
        len(batch.invoices) == KNOWN_ORIGINALS[batch.issuer]["faces"],
        len(batch.invoices),
        len(batch.invoices), count_rated, candidate_positive, "USD",
        tuple(proof_hashes), canonical_hash(body),
    )


def review_frozen_pdf_source(
    issuer: str, raw: bytes,
    **review_kwargs,
) -> OriginalEvidenceReview:
    """Read only one existing frozen public original; no network or storage."""
    batch = parse_original_pdf(issuer, raw)
    return review_original_extraction(batch, original_pdf_bytes=raw, **review_kwargs)
