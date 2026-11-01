"""Original-PDF freight invoice extraction with exact source and field witnesses.

Intentionally bounded to two authorized public bankruptcy exhibits. Extending
the parser to new carriers/customers requires a separately approved template
and independent document-rights review. This is *not* a universal PDF/OCR
product and never infers buyer terms or payment evidence from PDF text.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import re
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

from freight.canonical_schema import (
    ChargeLine, InvoiceAdjustment, ShipmentFacts, SourceArtifact, build_record,
)
from freight.contracts import canonical_hash
from freight.ingestion_gateway import IngressEnvelope, ingest_bytes
from recoveryworks.reconciliation_kernel import parse_amount_to_minor

KNOWN_ORIGINALS = {
    "GLOBALTRANZ": {
        "url": "https://ec-p-cus-ewf-ecb-sync-fnc.azurewebsites.net/api/GetImage/10247",
        "sha256": "45d4b8fae33234d3b9efe087e60a10dc5f6fc45f8cc9f5099560c6c63bfb33b4",
        "pages": 120,
        "faces": 100,
    },
    "ARCBEST": {
        "url": "https://ec-p-cus-ewf-ecb-sync-fnc.azurewebsites.net/api/GetImage/408",
        "sha256": "4c3e2f69ae7414bcebacd7d74f31320c2dad37d18f5e85370f46f00aca0bbb17",
        "pages": 74,
        "faces": 10,
    },
}
MAX_PDF_BYTES = 25_000_000
MAX_PAGES = 150
MAX_TEXT_PER_PAGE = 200_000
MONEY = re.compile(r"^-?(?:\d+|\d{1,3}(?:,\d{3})+)\.\d{2}$")


@dataclass(frozen=True)
class FieldWitness:
    field: str
    page: int
    value: str
    source_sha256: str


@dataclass(frozen=True)
class OriginalInvoice:
    issuer: str
    invoice_id: str
    page: int
    invoice_date: str | None
    original_face_cents: int
    charges: tuple[ChargeLine, ...]
    adjustments: tuple[InvoiceAdjustment, ...]
    source_sha256: str
    blockers: tuple[str, ...]
    field_witnesses: tuple[FieldWitness, ...]
    document_hash: str

    @property
    def gross_cents(self) -> int:
        return sum(x.billed_cents for x in self.charges)

    @property
    def adjustment_cents(self) -> int:
        return sum(x.amount_cents for x in self.adjustments)

    @property
    def signed_net_cents(self) -> int:
        return self.gross_cents - self.adjustment_cents


@dataclass(frozen=True)
class OriginalExtractionBatch:
    issuer: str
    source_sha256: str
    document_page_count: int
    invoices: tuple[OriginalInvoice, ...]
    original_amount_match_count: int
    incomplete_charge_breakdown_count: int
    typed_adjustment_invoice_count: int
    extraction_hash: str
    settlement_labels_available: bool = False
    controlling_tariffs_available: bool = False

    @property
    def invoice_count(self) -> int:
        return len(self.invoices)


def _pennies(value: str) -> int:
    if not MONEY.fullmatch(value.strip()):
        raise ValueError("malformed original PDF money token")
    return parse_amount_to_minor(value.replace(",", ""))


def _extract_page(issuer: str, text: str, number: int, source_hash: str) -> OriginalInvoice | None:
    if issuer == "GLOBALTRANZ":
        if not 4 <= number <= 114:
            return None
        match = re.search(
            r"(\d{1,2}/\d{1,2}/\d{4})\s+(\d{1,2}/\d{1,2}/\d{4})\s+"
            r"(\d{8}(?:\s*A)?)\b", text, re.I)
        if not match or not re.search(r"\bInvoice\s+Date\b", text, re.I):
            return None
        invoice_id = re.sub(r"\s+", " ", match.group(3)).upper()
        from datetime import datetime
        inv_date = datetime.strptime(match.group(1), "%m/%d/%Y").date().isoformat()
        face = re.search(r"\bTotal:\s*[\d,.]+\s+([\d,.]+)\s+USD\b", text, re.I)
        if not face:
            raise ValueError("invoice face amount missing: page " + str(number))
        amount = _pennies(face.group(1))
        begin = re.search(
            r"Pieces\s+Pallet\s+Description\s+Class\s+Weight\s+Charges\b", text, re.I)
        if not begin:
            raise ValueError("original charge table header absent: page " + str(number))
        tail = text[begin.end():]
        end = re.search(r"\bTotal:\s*[\d,.]+\s+[\d,.]+\s+USD\b", tail, re.I)
        if not end:
            raise ValueError("original charge total missing: page " + str(number))
        tokens = tuple(
            _pennies(line.strip()) for line in tail[:end.start()].splitlines()
            if MONEY.fullmatch(line.strip())
        )
        if not tokens:
            raise ValueError("no original charge tokens")
        positives = tuple(ChargeLine(
            charge_id=f"pdf:{number}:positive:{i}", charge_code="ORIGINAL_PDF_CHARGE",
            billed_cents=value,
        ) for i, value in enumerate(tokens, 1) if value >= 0)
        negatives = tuple(InvoiceAdjustment(
            adjustment_id=f"pdf:{number}:discount:{i}",
            kind="DISCOUNT",
            amount_cents=-value,
            source_sha256=source_hash,
        ) for i, value in enumerate(tokens, 1) if value < 0)
        blockers = ("CONTROLLING_RATE_UNVERIFIED", "BANK_PAYMENT_NOT_VERIFIED",
                    "SHIPMENT_FACTS_NOT_INDEPENDENTLY_CONFIRMED")
        witnesses = (
            FieldWitness("invoice_id", number, invoice_id, source_hash),
            FieldWitness("invoice_date", number, inv_date, source_hash),
            FieldWitness("face_total_cents", number, str(amount), source_hash),
            FieldWitness("charge_token_count", number, str(len(tokens)), source_hash),
        )
    else:
        if "ORIGINAL INVOICE" not in text.upper():
            return None
        match = re.search(r"Freight\s+bill\s+No:?\s*(\d{9})\b", text, re.I)
        if not match:
            return None
        invoice_id = match.group(1)
        face = re.search(
            r"\bAMOUNT\s+DUE:(?:.|\n){0,100}?\$\s*([\d,]+\.\d{2})", text, re.I)
        if not face:
            raise ValueError("ArcBest face amount missing: page " + str(number))
        amount = _pennies(face.group(1))
        inv_date = None  # Shipment date is NOT invoice issue date.
        positives = (ChargeLine(
            charge_id=f"pdf:{number}:face", charge_code="UNALLOCATED_INVOICE_TOTAL",
            billed_cents=amount,
        ),)
        negatives = ()
        blockers = ("CHARGE_LINES_NOT_INDEPENDENTLY_EXTRACTED",
                    "INVOICE_ISSUE_DATE_MISSING",
                    "CONTROLLING_RATE_UNVERIFIED",
                    "BANK_PAYMENT_NOT_VERIFIED",
                    "SHIPMENT_FACTS_NOT_INDEPENDENTLY_CONFIRMED")
        witnesses = (FieldWitness("invoice_id", number, invoice_id, source_hash),
                     FieldWitness("face_total_cents", number, str(amount), source_hash))
    if amount < 0 or sum(x.billed_cents for x in positives) - sum(
        x.amount_cents for x in negatives
    ) != amount:
        raise ValueError("original invoice charge components do not conserve face total: page " + str(number))
    stable = {
        "schema": 1, "issuer": issuer, "id": invoice_id, "page": number,
        "source": source_hash, "date": inv_date, "gross": sum(x.billed_cents for x in positives),
        "discounts": [asdict(x) for x in negatives],
        "lines": [asdict(x) for x in positives],
        "face": amount, "blockers": blockers,
    }
    return OriginalInvoice(
        issuer, invoice_id, number, inv_date, amount,
        positives, negatives, source_hash, blockers, witnesses,
        canonical_hash(stable),
    )


def parse_original_pdf(source: str, raw: bytes) -> OriginalExtractionBatch:
    """Template-bound parsing: reject unknown/revised PDFs, no OCR guesses."""
    source = source.upper()
    spec = KNOWN_ORIGINALS.get(source)
    if spec is None:
        raise ValueError("original PDF issuer is not approved")
    if not isinstance(raw, bytes) or len(raw) > MAX_PDF_BYTES:
        raise ValueError("invalid/or oversized PDF")
    original_hash = sha256(raw).hexdigest()
    if original_hash != spec["sha256"]:
        raise ValueError("original PDF source changed; halt for independent review")
    envelope = IngressEnvelope(
        ingress_id="original-template:" + source,
        buyer_id="RESEARCH_ONLY_NO_CUSTOMER_SCOPE",
        business_unit="ISOLATED_SOURCE_REPLAY",
        transport="BATCH", filename=source.lower() + ".pdf",
    )
    receipt = ingest_bytes(envelope, raw)
    if receipt.status != "ACCEPT" or receipt.route != "DOCUMENT_EXTRACTION_REQUIRED":
        raise ValueError("PDF failed native ingestion policy")
    try:
        import pymupdf  # optional parser, installed only in isolated runner
    except ImportError as exc:
        raise ValueError("PyMuPDF document adapter not installed") from exc
    pdf = pymupdf.open(stream=raw, filetype="pdf")
    try:
        if pdf.is_encrypted or len(pdf) != spec["pages"] or len(pdf) > MAX_PAGES:
            raise ValueError("original document encryption/page profile unexpected")
        pages: list[str] = []
        for page in pdf:
            text = page.get_text("text", sort=False)
            if len(text) > MAX_TEXT_PER_PAGE:
                raise ValueError("PDF page text exceeds safety bound")
            pages.append(text)
    finally:
        pdf.close()
    extracted = tuple(x for i, text in enumerate(pages, 1)
                      if (x := _extract_page(source, text, i, original_hash)) is not None)
    if len(extracted) != spec["faces"] or len({x.invoice_id for x in extracted}) != len(extracted):
        raise ValueError("original invoice population changed or duplicate identifiers present")
    correct = sum(x.original_face_cents == x.signed_net_cents for x in extracted)
    if correct != len(extracted):
        raise ValueError("original invoice arithmetic inconsistency")
    return OriginalExtractionBatch(
        issuer=source, source_sha256=original_hash,
        document_page_count=len(pages), invoices=extracted,
        original_amount_match_count=correct,
        incomplete_charge_breakdown_count=sum(
            "CHARGE_LINES_NOT_INDEPENDENTLY_EXTRACTED" in x.blockers for x in extracted),
        typed_adjustment_invoice_count=sum(bool(x.adjustments) for x in extracted),
        extraction_hash=canonical_hash({
            "schema": 1, "source": original_hash, "issuer": source,
            "invoice_proofs": [x.document_hash for x in extracted],
        }),
    )


def bind_independent_shipment(
    extracted: OriginalInvoice,
    *,
    buyer_id: str, business_unit: str, customer_id: str, currency: str,
    shipment: ShipmentFacts, observed_at: str,
):
    """Only caller-supplied independently established shipment facts can rate.

    Original invoice PDF cannot supply actual bank clearing, governing tariff
    or an independent adjudication. ArcBest lacks the original issue date and
    audited itemization, so cannot enter the rated canonical engine yet.
    """
    if not isinstance(shipment, ShipmentFacts):
        raise ValueError("a complete independent ShipmentFacts object is required")
    if extracted.invoice_date is None:
        raise ValueError("original invoice date is not independently established")
    if extracted.issuer == "ARCBEST":
        raise ValueError("ArcBest line-level charge allocation has not been independently extracted")
    return build_record(
        buyer_id=buyer_id, business_unit=business_unit,
        invoice_id=extracted.invoice_id, invoice_date=extracted.invoice_date,
        customer_id=customer_id, currency=currency, shipment=shipment,
        charges=extracted.charges, adjustments=extracted.adjustments,
        sources=(SourceArtifact(
            source_id="public-original:" + extracted.document_hash,
            kind="PUBLIC_ORIGINAL_COURT_INVOICE",
            sha256=extracted.source_sha256, observed_at=observed_at,
            transport="BATCH", filename=extracted.issuer.lower() + ".pdf",
        ),),
    )


class _SameOriginRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        first = urlparse(req.full_url)
        last = urlparse(newurl)
        if last.scheme != "https" or last.hostname != first.hostname:
            raise ValueError("cross-origin original-document redirects prohibited")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch_frozen_public_original(source: str) -> bytes:
    """Read-only research fetch; does not save originals to public GitHub."""
    spec = KNOWN_ORIGINALS.get(source.upper())
    if spec is None:
        raise ValueError("unregistered original-document source")
    url = spec["url"]
    assert urlparse(url).scheme == "https"
    with build_opener(_SameOriginRedirect()).open(
        Request(url, headers={"User-Agent": "RETALLY-bounded-evidence-lab/1.0"}),
        timeout=40,
    ) as response:
        if urlparse(response.geturl()).hostname != urlparse(url).hostname:
            raise ValueError("source redirect escaped original host")
        raw = response.read(MAX_PDF_BYTES + 1)
    if len(raw) > MAX_PDF_BYTES:
        raise ValueError("oversized downloaded original")
    if sha256(raw).hexdigest() != spec["sha256"]:
        raise ValueError("retrieved original changed on the source host")
    return raw


def safe_summary(batch: OriginalExtractionBatch) -> dict:
    """No invoice IDs, billing addresses, raw PDF content or customer rows."""
    return {
        "issuer": batch.issuer,
        "source_sha256": batch.source_sha256,
        "page_count": batch.document_page_count,
        "original_invoice_count": batch.invoice_count,
        "exact_original_invoice_amount_count": batch.original_amount_match_count,
        "typed_discount_or_credit_invoice_count": batch.typed_adjustment_invoice_count,
        "missing_independent_line_item_invoices": batch.incomplete_charge_breakdown_count,
        "extraction_hash": batch.extraction_hash,
        "freight_error_accuracy": None,
        "bank_clearance_verified": False,
        "controlling_tariff_verified": False,
        "claimable_recovery_cents": 0,
    }
