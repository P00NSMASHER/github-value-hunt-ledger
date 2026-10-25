"""Isolated, research-only original-document benchmark for RETALLY.

This runs RETALLY's existing ingress, reconciliation and rating paths. PDF text
extraction is an explicitly separate LAB ADAPTER: the production ingress route
for PDF is DOCUMENT_EXTRACTION_REQUIRED. No raw document bytes, row-level
records, or bank-like information are persisted, logged or committed.

Results cannot assert commercial authorization, cleared payment, rate errors,
freight classification accuracy or realized cash recovery.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import csv
import hashlib
import io
import json
import re
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

from freight.ingestion_gateway import IngressEnvelope, ingest_bytes
from freight.pennine_publication_integrity import (
    require_canonical_source_identity,
    require_matching_payment_annotations,
    require_stable_invoice_economics,
)
from recoveryworks.reconciliation_kernel import (
    ManyToOneConfig, ReconConfig, ReconTxn, parse_amount_to_minor, reconcile,
)

DOCUMENTS = {
    "globaltranz": "https://ec-p-cus-ewf-ecb-sync-fnc.azurewebsites.net/api/GetImage/10247",
    "arcbest": "https://ec-p-cus-ewf-ecb-sync-fnc.azurewebsites.net/api/GetImage/408",
}
HISTORICAL_GAO = {
    "B-143246": "https://www.gao.gov/products/b-143246",
    "B-148465": "https://www.gao.gov/products/b-148465",
    "B-161664": "https://www.gao.gov/products/b-161664",
    "B-199805-0": "https://www.gao.gov/products/b-199805-0",
    "B-223311-0": "https://www.gao.gov/products/b-223311-0",
    "B-221594-0": "https://www.gao.gov/products/b-221594-0",
    "B-195862": "https://www.gao.gov/products/b-195862",
    "B-221705": "https://www.gao.gov/products/b-221705",
}
# Independently published decision outcomes are REFERENCE CHALLENGES, never
# freight-error ground truth for the unrelated 2024-25 invoices in this lab.
# Each note is backed by the exact public GAO decision URL above.
HISTORICAL_REFERENCE_NOTES = {
    "B-143246": {
        "independent_decision_summary": "AUDIT_SUSTAINED_AFTER_PARTIAL_ALLOWANCE",
        "adversarial_check": "Mixed-commodity container classification may require line-specific rating; do not treat all freight as one highest-rated package.",
    },
    "B-148465": {
        "independent_decision_summary": "AUDITED_OVERCHARGE_COLLECTED_BY_OFFSET",
        "adversarial_check": "Carrier routing responsibilities can alter the correct through-rate calculation; cannot simply assert the original charge is correct.",
    },
    "B-221594-0": {
        "independent_decision_summary": "GOVERNMENT_OVERCHARGE_DETERMINATION_REVERSED",
        "adversarial_check": "Rejected governing-rate tender is not enforceable merely because it yields a smaller calculated charge; prevent false positive.",
    },
}
# Values quoted in the official GAO decisions are reference arithmetic ONLY.
# They lack linked original buyer invoices / controlling-rate exhibits / bank
# records in RETALLY's current 110-invoice original-document population.
HISTORICAL_GAO_AMOUNT_REFERENCES = {
    "B-143246": {
        "paid_major": "627.24",
        "original_audit_deduction_major": "340.21",
        "later_carrier_allowance_major": "11.81",
        "sustained_disputed_reclaim_major": "328.40",
        "legal_disposition": "AUDIT_SUSTAINED_WITH_PARTIAL_ALLOWANCE",
    },
    "B-148465": {
        "paid_major": "546.88",
        "collected_offset_major": "61.22",
        "legal_disposition": "PAID_FREIGHT_OVERCHARGE_OFFSET_AFFIRMED",
    },
    "B-221594-0": {
        "paid_major": "942.00",
        "gsa_proposed_charge_major": "721.25",
        "gsa_collected_deduction_major": "220.75",
        "legal_disposition": "GSA_DEDUCTION_INVALID_REJECTED_TENDER",
    },
}


def historical_reference_money_controls() -> dict:
    """Compare financial arithmetic in GAO narrative *without* freight scoring."""
    b143 = HISTORICAL_GAO_AMOUNT_REFERENCES["B-143246"]
    b148 = HISTORICAL_GAO_AMOUNT_REFERENCES["B-148465"]
    b221 = HISTORICAL_GAO_AMOUNT_REFERENCES["B-221594-0"]
    checks = {
        "gao_b143246_net_reclaim_exact": (
            minor(b143["original_audit_deduction_major"]) -
            minor(b143["later_carrier_allowance_major"]) ==
            minor(b143["sustained_disputed_reclaim_major"])
        ),
        "gao_b148465_collected_offset_within_original_payment": (
            0 < minor(b148["collected_offset_major"]) <= minor(b148["paid_major"])
        ),
        "gao_b221594_ledger_math_does_not_validate_invalid_deduction": (
            minor(b221["paid_major"]) - minor(b221["gsa_proposed_charge_major"]) ==
            minor(b221["gsa_collected_deduction_major"])
            and b221["legal_disposition"] == "GSA_DEDUCTION_INVALID_REJECTED_TENDER"
        ),
    }
    return {
        "reference_cases": len(checks),
        "checks": checks,
        "all_reference_arithmetic_exact": all(checks.values()),
        "source": "PUBLIC_GAO_DECISION_TEXT_CURATED_NOT_INDEPENDENT_BANK_ARTIFACTS",
        "original_invoice_documents_joined": 0,
        "independently_scored_freight_cases": 0,
        "recovery_claims_usd_minor": 0,
    }


PENNINE = {
    "2026-04": "https://www.penninecare.nhs.uk/download_file/5855/277",
    "2026-05": "https://www.penninecare.nhs.uk/download_file/5874/277",
    "2026-06": "https://www.penninecare.nhs.uk/download_file/5910/277",
    "2026-07": "https://www.penninecare.nhs.uk/download_file/5920/277",
    "2026-08": "https://www.penninecare.nhs.uk/download_file/5941/277",
}
# Public invoice-face spot checks. These are NOT freight-error truth labels.
ARCBEST_FACE_ANCHORS = {
    "044177205": (4, 31477),
    "051886768": (10, 24477),
    "051894063": (16, 212379),
    "086855061": (23, 213283),
    "196876953": (38, 61279),
    "279818407": (43, 60600),
    "352112867": (51, 35178),
    "352176075": (57, 25238),
    "436380706": (61, 295000),
    "436430967": (66, 320000),
}
GLOBAL_FACE_ANCHORS = {
    "30794056": (4, 34108),
    "29937996": (5, 20140),
    "30984884 A": (32, 2988),
    "30988238": (39, 24661),
    "31048751": (7, 17390),
}
EXPECTED = {
    "globaltranz_pages": 120,
    "arcbest_pages": 74,
    "globaltranz_statement_rows": 102,
    "globaltranz_original_total_minor": 2602661,
    "globaltranz_current_total_minor": 2595447,
    "pennine_disclosed_rows": 314,
    "pennine_unique_invoices": 273,
}
LIMIT = 35_000_000
ALLOW_HOSTS = {"ec-p-cus-ewf-ecb-sync-fnc.azurewebsites.net", "www.penninecare.nhs.uk", "www.gao.gov", "gao.gov"}
MONEY_RE = re.compile(r"^-?(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d{1,2})?$")


@dataclass(frozen=True)
class InvoiceFace:
    issuer: str
    number: str
    page: int
    cents: int | None
    invoice_date: str | None
    shipment_date: str | None
    mode: str | None
    reason: str | None = None


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


# Frozen source-byte identities from the accepted 2026-10-20 original replay.
# Content changes require an explicit reviewed baseline update, not blind refresh.
FROZEN_DOCUMENT_SHA256 = {
    "globaltranz": "45d4b8fae33234d3b9efe087e60a10dc5f6fc45f8cc9f5099560c6c63bfb33b4",
    "arcbest": "4c3e2f69ae7414bcebacd7d74f31320c2dad37d18f5e85370f46f00aca0bbb17",
}
FROZEN_PENNINE_SHA256 = {
    "2026-04": "314cd0c021f137b43b94e81bb93f26aece5b3b0a021e99c42d43546a640c3d90",
    "2026-05": "5957ead9c23d57039e267dc18076c7b8d711a14b97cbea6d9a9ff0629aeb5028",
    "2026-06": "318aeeedbf55d05bcffce5076ac893a84bdb6ebe5e7c851bb3f3c45dbbdea8fc",
    "2026-07": "ecb986bd0e33cf402f7cb86ff68bc91368d18a5dfc39410e4e2019c045c3de15",
    "2026-08": "4153ccbbbe27307afddba1d6651bfd9db8a774cc84e4fd23d62b3a2d1059d796",
}


def require_frozen_source(kind: str, label: str, data: bytes) -> str:
    expected = (FROZEN_DOCUMENT_SHA256 if kind == "document" else
                FROZEN_PENNINE_SHA256 if kind == "pennine" else None)
    if expected is None or label not in expected:
        raise ValueError("unknown frozen source identity")
    actual = digest(data)
    if actual != expected[label]:
        raise ValueError(f"FROZEN_PUBLIC_SOURCE_CHANGED:{kind}:{label}")
    return actual


class _ApprovedRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        target = urlparse(newurl)
        if target.scheme != "https" or target.hostname not in ALLOW_HOSTS:
            raise ValueError("out-of-allowlist source redirect blocked before request")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch_public(url: str) -> bytes:
    """Fixed allowlist, bounded reads; never accept redirects to new hosts."""
    parts = urlparse(url)
    if parts.scheme != "https" or parts.hostname not in ALLOW_HOSTS or parts.username or parts.password:
        raise ValueError("unapproved HTTPS source origin")
    request = Request(url, headers={"User-Agent": "RETALLY-Research-Document-QA/1.0"})
    with build_opener(_ApprovedRedirects()).open(request, timeout=45) as response:
        final = urlparse(response.geturl())
        if final.scheme != "https" or final.hostname not in ALLOW_HOSTS:
            raise ValueError("unapproved final source origin")
        data = response.read(LIMIT + 1)
    if not data or len(data) > LIMIT:
        raise ValueError("source empty or over 35 MB")
    return data


def minor(raw: str) -> int:
    """Normalize a CSV presentation amount, then use RETALLY's exact parser."""
    value = raw.strip()
    if value.startswith(("£", "$")):
        value = value[1:].strip()
    if value.startswith("(") and value.endswith(")"):
        value = "-" + value[1:-1]
    if not MONEY_RE.fullmatch(value):
        raise ValueError("invalid decimal money or thousands grouping")
    return parse_amount_to_minor(value.replace(",", ""), 2)


def iso_date(raw: str, *, formats: tuple[str, ...] = ("%d/%m/%Y", "%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y")) -> str:
    for fmt in formats:
        try:
            return datetime.strptime(raw.strip(), fmt).date().isoformat()
        except ValueError:
            pass
    raise ValueError("unparseable source date")


def pdf_texts(raw: bytes, *, sort: bool = False) -> list[str]:
    # PyMuPDF is only used to read original PDF text in the ephemeral runner.
    # sort=True is ONLY a second layout-sensitive read of SAME frozen bytes.
    if type(sort) is not bool:
        raise ValueError("PDF_TEXT_READING_ORDER_FLAG_INVALID")
    import pymupdf

    if not raw.startswith(b"%PDF-"):
        raise ValueError("non-PDF supplied")
    doc = pymupdf.open(stream=raw, filetype="pdf")
    try:
        if len(doc) > 150:
            raise ValueError("document page limit exceeded")
        pages: list[str] = []
        for page in doc:
            data = page.get_text("text", sort=sort)
            if len(data) > 200_000:
                raise ValueError("excessive page text size")
            pages.append(data)
        return pages
    finally:
        doc.close()


def _global_page(text: str, page: int) -> InvoiceFace | None:
    if not re.search(r"\bInvoice\s+Date\b", text, re.I):
        return None
    # Layout text shows invoice date, pickup date, then the broker invoice no.
    match = re.search(
        r"(\d{1,2}/\d{1,2}/\d{4})\s+(\d{1,2}/\d{1,2}/\d{4})\s+"
        r"(\d{8}(?:\s*A)?)\b", text, re.I,
    )
    if not match:
        return None
    number = re.sub(r"\s+", " ", match.group(3)).upper()
    # Read invoice face, not credit, statement balance or amount enclosed.
    total = re.search(r"\bTotal:\s*[\d,.]+\s+([\d,.]+)\s+USD\b", text, re.I)
    amount = minor(total.group(1)) if total else None
    return InvoiceFace("globaltranz", number, page, amount,
                       iso_date(match.group(1)), iso_date(match.group(2)),
                       None, None if total else "FACE_TOTAL_UNREADABLE")


def _arcbest_page(text: str, page: int) -> InvoiceFace | None:
    if not re.search(r"ORIGINAL\s+INVOICE", text, re.I):
        return None
    match = re.search(r"Freight\s+bill\s+No:?\s*(\d{9})\b", text, re.I)
    if not match:
        return None
    amount = re.search(
        r"\bAMOUNT\s+DUE:\s*(?:\(payable\s+in\s+US\s+funds\)\s*)?"
        r"\$\s*([\d,]+\.\d{2})", text, re.I,
    )
    if not amount:
        # PDF text order can place explanatory notes between label and amount.
        amount = re.search(r"\bAMOUNT\s+DUE:(?:.|\n){0,100}?\$\s*([\d,]+\.\d{2})", text, re.I)
    shipment = re.search(r"\bShipment\s+Date:\s*(\d{1,2}/\d{1,2}/\d{4})", text, re.I)
    mode = re.search(r"\bService:\s*(LTL|Truckload|TL)\b", text, re.I)
    parsed_mode = ("TL" if mode and mode.group(1).lower() in {"truckload", "tl"}
                   else "LTL" if mode else None)
    return InvoiceFace("arcbest", match.group(1), page,
                       minor(amount.group(1)) if amount else None,
                       None, iso_date(shipment.group(1)) if shipment else None,
                       parsed_mode, None if amount else "FACE_AMOUNT_UNREADABLE")


def index_unique_invoice_faces(
    faces: list[InvoiceFace], issuer: str,
) -> dict[str, InvoiceFace]:
    """Index a single original PDF without masking duplicate invoice faces.

    Repeated face IDs may be duplicate pages, conflicting invoice amounts or
    extraction mistakes. All are review-required source ambiguities; never
    last-write-wins. Diagnostic errors intentionally omit invoice identifiers.
    """
    if issuer not in {"globaltranz", "arcbest"} or type(faces) is not list:
        raise ValueError("INVALID_PUBLIC_INVOICE_FACE_CATALOG")
    unique: dict[str, InvoiceFace] = {}
    for face in faces:
        if (
            type(face) is not InvoiceFace
            or face.issuer != issuer
            or type(face.number) is not str
            or not face.number.strip()
            or type(face.page) is not int
            or face.page < 1
            or (face.cents is not None and type(face.cents) is not int)
        ):
            raise ValueError("INVALID_PUBLIC_INVOICE_FACE_CATALOG")
        if face.number in unique:
            raise ValueError("DUPLICATE_PUBLIC_ORIGINAL_INVOICE_FACE")
        unique[face.number] = face
    return unique


def extract_faces(issuer: str, texts: list[str]) -> list[InvoiceFace]:
    selected = []
    for index, text in enumerate(texts):
        if issuer == "globaltranz" and not 4 <= index + 1 <= 114:
            continue
        result = (_global_page(text, index + 1) if issuer == "globaltranz"
                  else _arcbest_page(text, index + 1))
        if result:
            selected.append(result)
    index_unique_invoice_faces(selected, issuer)
    return selected


def statement_rows(texts: list[str]) -> list[dict]:
    """GlobalTranz open-account statement: NOT a payment file."""
    rows = []
    # Table is "Transaction Class Activity Date Entered Currency Original Amount Current Amount".
    expression = re.compile(
        r"(?m)^\s*(\d{8})(?:\s+(A))?\s+Invoice\s+"
        r"(\d{1,2}/\d{1,2}/\d{2,4})\s+USD\s+"
        r"([\d,]+(?:\.\d{1,2})?)\s+([\d,]+(?:\.\d{1,2})?)\s*$",
        re.I,
    )
    for page in texts[114:120]:
        for match in expression.finditer(page):
            number = match.group(1) + (" A" if match.group(2) else "")
            rows.append({
                "number": number, "date": iso_date(match.group(3),
                    formats=("%m/%d/%y", "%m/%d/%Y")),
                "original": minor(match.group(4)), "current": minor(match.group(5)),
            })
    return rows


def check_anchors(faces: list[InvoiceFace], anchors: dict) -> dict:
    by_id = index_unique_invoice_faces(faces, faces[0].issuer) if faces else {}
    checks = []
    for number, (page, cents) in anchors.items():
        face = by_id.get(number)
        checks.append(bool(face and face.page == page and face.cents == cents))
    return {"checks": len(checks), "passed": sum(checks), "failed": len(checks) - sum(checks)}


def globaltranz_charge_components(text: str) -> tuple[int, ...] | None:
    """Extract charge-column decimal tokens, not rates or physical weights.

    The original GlobalTranz pages print variable line charges after the
    'Pieces Pallet ... Charges' header and before the 'Total:' amount. This
    lab-only extraction is deliberately strict and treats PDF text-layout
    uncertainty as UNKNOWN instead of inventing rated charge lines.
    """
    start = re.search(
        r"Pieces\s+Pallet\s+Description\s+Class\s+Weight\s+Charges\b",
        text, re.I)
    if not start:
        return None
    end = re.search(r"\bTotal:\s*[\d,.]+\s+[\d,.]+\s+USD\b",
                    text[start.end():], re.I)
    if not end:
        return None
    region = text[start.end():start.end()+end.start()]
    amounts = []
    for line in region.splitlines():
        candidate = line.strip()
        if re.fullmatch(r"-?(?:\d+|\d{1,3}(?:,\d{3})+)\.\d{2}", candidate):
            amounts.append(minor(candidate))
    return tuple(amounts) if amounts else None


def globaltranz_invoice_line_total_benchmark(
    faces: list[InvoiceFace], texts: list[str],
) -> dict:
    """Measure real invoice-line money with explicit signed-adjustment hold.

    Freight canonical ChargeLine rejects negative billed_cents. Preserve that
    product limitation: do not silently drop or convert original discounts to
    nonnegative charges. Use the REAL reconciliation kernel money parser to
    replay negative amounts separately, and count any affected invoice as not
    fully representable by the production freight line schema.
    """
    from freight.canonical_schema import ChargeLine
    exact = unmatched = unextracted = 0
    line_items = negative_adjustments = 0
    discounted_faces = 0
    canonical_roundtrip_faces = 0
    fingerprints = []
    for face in faces:
        components = globaltranz_charge_components(texts[face.page - 1])
        if not components or face.cents is None:
            unextracted += 1
            continue
        nonnegative_lines = tuple(
            ChargeLine(
                charge_id=f"lab-component:{face.page}:{idx}",
                charge_code="ORIGINAL_PDF_NONNEGATIVE_COMPONENT",
                billed_cents=amount,
            )
            for idx, amount in enumerate(components, 1) if amount >= 0
        )
        negative = [amount for amount in components if amount < 0]
        # Actual RecoveryWorks reconciliation parser handles signed decimals.
        signed_adjustments = [
            parse_amount_to_minor(f"{Decimal(amount) / Decimal(100):.2f}", 2)
            for amount in negative
        ]
        if signed_adjustments != negative:
            raise ValueError("signed original invoice amount corrupted in kernel")
        computed = sum(item.billed_cents for item in nonnegative_lines) + sum(signed_adjustments)
        line_items += len(components)
        negative_adjustments += len(negative)
        discounted_faces += int(bool(negative))
        canonical_roundtrip_faces += int(not negative)
        exact += int(computed == face.cents)
        unmatched += int(computed != face.cents)
        fingerprints.append((face.number, computed, face.cents, len(components), len(negative)))
    return {
        "source": "ORIGINAL_PDF_COMPONENTS_REPLAYED_BY_CANONICAL_POSITIVE_LINES_AND_SIGNED_RECONCILIATION_PARSER",
        "invoice_faces_considered": len(faces),
        "component_tokens_extracted": line_items,
        "negative_adjustment_tokens": negative_adjustments,
        "invoice_faces_containing_negative_discounts": discounted_faces,
        "invoice_faces_canonical_signed_charge_schema_compatible": canonical_roundtrip_faces,
        "production_freight_ChargeLine_accepts_negative_discounts": False,
        "invoice_face_exact_line_sum": exact,
        "invoice_face_nonmatching_extracted_line_sum": unmatched,
        "invoice_face_component_text_unavailable": unextracted,
        "every_face_conserved": exact + unmatched + unextracted == len(faces),
        "line_sum_proves_controlling_rate_or_overcharge": False,
        "line_sum_proves_cash_settlement": False,
        "stable_line_comparison_sha256": digest(json.dumps(
            sorted(fingerprints), separators=(",", ":")).encode()),
    }



def globaltranz_canonical_v2_adjustment_replay(
    faces: list[InvoiceFace], texts: list[str], pdf_sha256: str,
) -> dict:
    """Reconstruct original PDF *invoice math* in canonical v2, never rate truth.

    ChargeLine rightly forbids negative charges. Canonical schema v2 already
    provides separate positive-magnitude InvoiceAdjustment records bound to
    the original PDF SHA. This test exercises that supported model without
    changing production ingress, applying tariffs, or storing invoice IDs.

    Synthetic shipment fields here exist ONLY to satisfy the canonical schema.
    In particular, the placeholder weight, postcodes, carrier and LTL mode
    are not facts extracted from source. This is never a rate accuracy test.
    """
    from freight.canonical_schema import (
        ChargeLine, InvoiceAdjustment, SourceArtifact, ShipmentFacts,
        SCHEMA_VERSION, SIGNED_INVOICE_SCHEMA_VERSION, build_record, verify_record,
    )
    from freight.rate_authority import AuthorityBook
    from freight.rating_engine import REVIEW_REQUIRED, rate_record

    if not re.fullmatch(r"[0-9a-f]{64}", pdf_sha256):
        raise ValueError("LAB_SOURCE_SHA256_REQUIRED")

    exact = built = discounted = charge_only = review = unsafe = blocked = 0
    missing = Counter()
    record_hashes = []
    for face in faces:
        if (face.issuer != "globaltranz" or face.page <= 0
                or face.page > len(texts) or not face.invoice_date
                or not face.shipment_date or face.cents is None
                or face.cents < 0):
            blocked += 1
            missing["FACE_IDENTITY_DATE_OR_AMOUNT_INCOMPLETE"] += 1
            continue
        components = globaltranz_charge_components(texts[face.page - 1])
        if not components or not any(amount > 0 for amount in components):
            blocked += 1
            missing["CHARGE_COMPONENTS_MISSING"] += 1
            continue
        if sum(components) != face.cents:
            blocked += 1
            missing["ORIGINAL_FACE_NET_NOT_RECONCILED"] += 1
            continue
        try:
            charges = tuple(
                ChargeLine(
                    charge_id=f"lab-positive:{face.page}:{idx}",
                    charge_code="PDF_ORIGINAL_POSITIVE_COMPONENT",
                    billed_cents=amount,
                )
                for idx, amount in enumerate(components, 1) if amount >= 0
            )
            adjustments = tuple(
                InvoiceAdjustment(
                    adjustment_id=f"lab-negative:{face.page}:{idx}",
                    kind="DISCOUNT",  # Provisional source sign, NOT verified credit type.
                    amount_cents=-amount,
                    source_sha256=pdf_sha256,
                )
                for idx, amount in enumerate(components, 1) if amount < 0
            )
            source = SourceArtifact(
                source_id="lab:globaltranz:" + _safe_sha(face.number),
                kind="PUBLIC_ORIGINAL_INVOICE_LAB_ONLY",
                sha256=pdf_sha256,
                observed_at="2026-10-20T00:00:00.000000Z",
                transport="BATCH", filename="globaltranz.pdf",
            )
            # No original customer contract, validated weight, location or
            # true freight mode is supplied. The deliberate lab placeholders
            # must NEVER be sent to a rated production invoice workflow.
            shipment = ShipmentFacts(
                shipment_id="LAB_SYNTHETIC:" + _safe_sha(face.number),
                carrier_id="LAB_CARRIER_UNKNOWN",
                mode="LTL", service_date=face.shipment_date,
                origin_postal="LAB_UNKNOWN_ORIGIN",
                destination_postal="LAB_UNKNOWN_DESTINATION",
                actual_weight_grams=1, package_count=1,
            )
            record = build_record(
                buyer_id="ISOLATED_PUBLIC_RESEARCH_ONLY",
                business_unit="LAB_SYNTHETIC_SHIPMENT",
                invoice_id=face.number,
                invoice_date=face.invoice_date,
                customer_id="LAB_UNKNOWN_CUSTOMER",
                currency="USD", shipment=shipment,
                charges=charges, adjustments=adjustments, sources=(source,),
            )
            verify_record(record)
            if record.billed_total_cents != face.cents:
                blocked += 1
                missing["V2_NET_TOTAL_CHANGED"] += 1
                continue
            if adjustments and record.schema_version != SIGNED_INVOICE_SCHEMA_VERSION:
                blocked += 1
                missing["V2_ADJUSTMENT_SCHEMA_NOT_USED"] += 1
                continue
            if not adjustments and record.schema_version != SCHEMA_VERSION:
                blocked += 1
                missing["V1_POSITIVE_CHARGE_SCHEMA_NOT_USED"] += 1
                continue
            first = rate_record(record, AuthorityBook(()))
            second = rate_record(record, AuthorityBook(()))
            if (first.status != REVIEW_REQUIRED or
                    first.expected_total_cents is not None or
                    first.variance_cents is not None or
                    first.billed_total_cents != face.cents or
                    first.rating_hash != second.rating_hash):
                unsafe += 1
                continue
        except ValueError:
            blocked += 1
            missing["SCHEMA_REJECTED_LAB_PROXY"] += 1
            continue
        built += 1
        exact += 1
        discounted += int(bool(adjustments))
        charge_only += int(not adjustments)
        review += 1
        record_hashes.append(record.record_hash)

    return {
        "scope": "ORIGINAL_PDF_SIGNED_MONEY_REPLAY_WITH_SYNTHETIC_SHIPMENT_NO_TARIFF",
        "original_invoice_faces_considered": len(faces),
        "canonical_invoice_records_with_exact_source_net": exact,
        "canonical_v2_adjustment_records_with_exact_source_net": discounted,
        "canonical_v1_charge_only_records_with_exact_source_net": charge_only,
        "canonical_records_built": built,
        "discount_bearing_v2_records": discounted,
        "rate_review_required": review,
        "unrepresentable_or_missing_source": blocked,
        "unsafe_auto_money_or_nondeterministic": unsafe,
        "incomplete_source_reason_counts": dict(sorted(missing.items())),
        "input_original_pdf_digest_matches_frozen_baseline":
            pdf_sha256 == FROZEN_DOCUMENT_SHA256["globaltranz"],
        "source_bound_adjustment_sha256": pdf_sha256,
        "stable_canonical_record_catalog_sha256": digest(
            "".join(sorted(record_hashes)).encode("utf-8")),
        "invoice_adjustment_kind_is_lab_hypothesis_not_adjudicated": True,
        "shipment_fields_are_synthetic_lab_placeholders": True,
        "production_pdf_extraction_completed": False,
        "commercial_rate_authority_verified": False,
        "independent_invoice_overcharge_labels": 0,
        "recovered_cash_cents": 0,
        "customer_contact_actions": 0,
    }


def _safe_sha(identifier: str) -> str:
    return hashlib.sha256(identifier.encode("utf-8")).hexdigest()[:20]


def _recon_result(a: list[ReconTxn], b: list[ReconTxn], lookup: dict[str, str] | None = None) -> dict:
    config = ReconConfig(
        decimals=2, date_window_days=180, amount_tolerance_bps=0,
        many_to_one=ManyToOneConfig(enabled=True, date_window_days=180,
                                   tolerance_bps=0, max_group_size=6),
    )
    result = reconcile(a, b, config)
    wrong = 0
    assessed = 0
    if lookup is not None:
        for group in result.matches:
            for aid in group.internal_ids:
                for bid in group.settlement_ids:
                    assessed += 1
                    wrong += int(lookup.get(aid) != lookup.get(bid))
    return {
        "invoice_rows": result.summary.internal_rows,
        "counterpart_rows": result.summary.settlement_rows,
        "match_groups": result.summary.match_groups,
        "matched_invoices": result.summary.matched_internal,
        "unmatched_invoices": result.summary.unmatched_internal,
        "unmatched_counterparts": result.summary.unmatched_settlement,
        "by_rule": dict(result.summary.by_rule),
        "source_reference_pairs_assessed": assessed,
        "cross_reference_false_joins": wrong,
        "canonical_result_sha256": digest(result.canonical_json().encode()),
    }




def _validate_replay_group_binding(row: ReconTxn, group: str) -> None:
    """Bind a claimed source remittance partition to the actual transaction.

    Full publisher keys contain supplier, reference, date and currency; compact
    synthetic fixtures contain the reference alone. Both forms must agree with
    original source-derived transaction fields before invoking the kernel.
    """
    if type(group) is not str or not group or group != group.strip():
        raise ValueError("PUBLIC_SOURCE_GROUP_BINDING_MISMATCH")
    parts = group.split(chr(31))
    if len(parts) == 4:
        supplier, reference, date, currency = parts
        if (
            not supplier or supplier != supplier.strip()
            or not reference or (reference, date, currency) != (
                row.reference, row.date, row.currency
            )
        ):
            raise ValueError("PUBLIC_SOURCE_GROUP_BINDING_MISMATCH")
    elif len(parts) == 1:
        if group != row.reference:
            raise ValueError("PUBLIC_SOURCE_GROUP_BINDING_MISMATCH")
    else:
        raise ValueError("PUBLIC_SOURCE_GROUP_BINDING_MISMATCH")


def reference_scoped_replay(
    invoices: list[ReconTxn], counterpart: list[ReconTxn],
    invoice_group: dict[str, str], payment_group: dict[str, str],
    *, max_group_size: int = 8,
) -> dict:
    """Safely invoke the EXISTING kernel per source-declared payment reference.

    The native unscoped bounded many-to-one search considers the first 18
    unmatched invoices in its date window, regardless of payment reference.
    The reference-scoped adapter cannot pair an invoice with another remittance
    and preserves the original unscoped result for a comparative diagnostic.
    No bank payment is manufactured: counterparts remain same-source aggregate
    declarations. Groups above the explicit bound abstain. Mapping labels
    cannot silently contradict the source-derived reference, date or currency.
    """
    # The kernel's many-to-one candidate window is 18; a larger bound would
    # silently under-search some supposedly eligible remittance partitions.
    if type(max_group_size) is not int or not 1 <= max_group_size <= 18:
        raise ValueError("INVALID_SOURCE_GROUP_BOUND")
    if type(invoices) is not list or type(counterpart) is not list:
        raise ValueError("PUBLIC_SOURCE_TRANSACTIONS_INVALID")
    all_rows = invoices + counterpart
    if any(type(row) is not ReconTxn or type(row.id) is not str or not row.id
           for row in all_rows):
        raise ValueError("PUBLIC_SOURCE_TRANSACTIONS_INVALID")
    all_ids = [row.id for row in all_rows]
    if len(set(all_ids)) != len(all_ids):
        raise ValueError("DUPLICATE_SOURCE_TRANSACTION_ID")
    if (type(invoice_group) is not dict or type(payment_group) is not dict
            or set(invoice_group) != {row.id for row in invoices}
            or set(payment_group) != {row.id for row in counterpart}):
        raise ValueError("PUBLIC_SOURCE_GROUP_LABEL_COVERAGE_MISMATCH")
    for row in invoices:
        _validate_replay_group_binding(row, invoice_group[row.id])
    for row in counterpart:
        _validate_replay_group_binding(row, payment_group[row.id])

    by_invoice: dict[str, list[ReconTxn]] = defaultdict(list)
    by_payment: dict[str, list[ReconTxn]] = defaultdict(list)
    for row in invoices:
        by_invoice[invoice_group[row.id]].append(row)
    for row in counterpart:
        by_payment[payment_group[row.id]].append(row)
    if any(len(x) != 1 for x in by_payment.values()):
        raise ValueError("ambiguous source-declared grouped counterpart")
    result_by_rule: Counter = Counter()
    grouped_matched = 0
    grouped_unmatched = 0
    grouped_matched_counterparts = 0
    grouped_unmatched_counterparts = 0
    unmatched_source_declaration_groups = 0
    wrong_join = 0
    groups_matched = 0
    limit_groups = 0
    limit_invoices = 0
    observed_max = max((len(x) for x in by_invoice.values()), default=0)
    for ref in sorted(set(by_invoice) | set(by_payment)):
        internal = by_invoice.get(ref, [])
        settlement = by_payment.get(ref, [])
        if not internal or not settlement:
            grouped_unmatched += len(internal)
            grouped_unmatched_counterparts += len(settlement)
            unmatched_source_declaration_groups += int(bool(settlement))
            continue
        if len(internal) > max_group_size:
            limit_groups += 1
            limit_invoices += len(internal)
            grouped_unmatched += len(internal)
            grouped_unmatched_counterparts += len(settlement)
            unmatched_source_declaration_groups += int(bool(settlement))
            continue
        config = ReconConfig(
            decimals=2, date_window_days=0, amount_tolerance_bps=0,
            many_to_one=ManyToOneConfig(
                enabled=True, date_window_days=0, tolerance_bps=0,
                max_group_size=max(2, max_group_size), max_candidates=18, max_nodes=50_000),
        )
        replay = reconcile(internal, settlement, config)
        result_by_rule.update(replay.summary.by_rule)
        grouped_matched += replay.summary.matched_internal
        grouped_unmatched += replay.summary.unmatched_internal
        grouped_matched_counterparts += replay.summary.matched_settlement
        grouped_unmatched_counterparts += replay.summary.unmatched_settlement
        unmatched_source_declaration_groups += int(
            replay.summary.unmatched_settlement > 0
        )
        groups_matched += replay.summary.matched_settlement
        for match in replay.matches:
            for aid in match.internal_ids:
                for bid in match.settlement_ids:
                    wrong_join += int(invoice_group[aid] != payment_group[bid])
    report = {
        "kernel": "recoveryworks.reconciliation_kernel.reconcile",
        "isolation": "SOURCE_DECLARED_PAYMENT_REFERENCE_CURRENCY_AND_DATE",
        "max_group_size": max_group_size,
        "largest_actual_declared_group": observed_max,
        "original_unique_invoices": len(invoices),
        "same_source_payment_reference_groups": len(by_payment),
        "matched_invoices": grouped_matched,
        "unmatched_invoices": grouped_unmatched,
        "matched_counterparts": grouped_matched_counterparts,
        "unmatched_counterparts": grouped_unmatched_counterparts,
        "unmatched_source_declaration_groups": unmatched_source_declaration_groups,
        "source_declaration_reconciliation_complete": bool(
            invoices and counterpart
            and grouped_unmatched == 0
            and grouped_unmatched_counterparts == 0
            and wrong_join == 0
            and limit_groups == 0
        ),
        "matched_groups": groups_matched,
        "unmatched_over_group_bound_invoices": limit_invoices,
        "groups_over_group_bound": limit_groups,
        "by_kernel_rule": dict(result_by_rule),
        "cross_reference_false_joins": wrong_join,
        "independent_bank_settlements_tested": 0,
        "independent_payment_accuracy": None,
    }
    if grouped_matched + grouped_unmatched != len(invoices):
        raise ValueError("invoice-count conservation failed")
    if grouped_matched_counterparts + grouped_unmatched_counterparts != len(counterpart):
        raise ValueError("source-declaration-count conservation failed")
    return report


def adversarial_declared_payment_controls(
    invoices: list[ReconTxn], counterparts: list[ReconTxn],
    invoice_group: dict[str, str], payment_group: dict[str, str],
) -> dict:
    """Falsify source-derived reconciliation using controlled corruptions.

    These tests *do not* supply independent bank transactions. They establish
    that the existing matching engine + bounded reference scope detect
    deliberate one-cent, reference, currency and duplicate-declaration faults
    in a copy of the actual Pennine invoice population.
    """
    counts = Counter(invoice_group.values())
    exemplar = next(
        (row for row in counterparts if counts[payment_group[row.id]] == 1),
        None,
    )
    if exemplar is None:
        raise ValueError("no singleton payment declaration for negative controls")
    base = reference_scoped_replay(invoices, counterparts, invoice_group, payment_group)
    if (base["matched_invoices"] != len(invoices)
            or not base["source_declaration_reconciliation_complete"]):
        raise ValueError("cannot assess controlled corruption before structural baseline matches")

    def altered(*, amount: str | None = None, currency: str | None = None) -> list[ReconTxn]:
        return [
            (ReconTxn(id=row.id,
                      amount=(amount if amount is not None else row.amount),
                      date=row.date, currency=currency or row.currency,
                      reference=row.reference)
             if row.id == exemplar.id else row)
            for row in counterparts
        ]

    tampered_amount = str(Decimal(str(exemplar.amount)) + Decimal("0.01"))
    penny_result = reference_scoped_replay(
        invoices, altered(amount=tampered_amount), invoice_group, payment_group)
    wrong_ref_map = dict(payment_group)
    wrong_ref_map[exemplar.id] = "LAB_NEGATIVE_CONTROL_DIFFERENT_PAYMENT_REFERENCE"
    # The hardened entry boundary rejects a source-label mismatch even before
    # its amount/date fallback can silently match an incorrectly labeled row.
    wrong_ref_held = False
    try:
        wrong_ref_result = reference_scoped_replay(
            invoices, counterparts, invoice_group, wrong_ref_map)
        wrong_ref_held = wrong_ref_result["unmatched_invoices"] == 1
    except ValueError as exc:
        if str(exc) != "PUBLIC_SOURCE_GROUP_BINDING_MISMATCH":
            raise
        wrong_ref_held = True

    wrong_currency_held = False
    try:
        wrong_currency_result = reference_scoped_replay(
            invoices, altered(currency="USD"), invoice_group, payment_group)
        wrong_currency_held = wrong_currency_result["unmatched_invoices"] == 1
    except ValueError as exc:
        if str(exc) != "PUBLIC_SOURCE_GROUP_BINDING_MISMATCH":
            raise
        wrong_currency_held = True

    duplicate_rejected = False
    try:
        reference_scoped_replay(
            invoices, counterparts + [exemplar], invoice_group, payment_group)
    except ValueError as exc:
        duplicate_rejected = str(exc) in {
            "ambiguous source-declared grouped counterpart",
            "DUPLICATE_SOURCE_TRANSACTION_ID",
        }

    checks = {
        "one_penny_corrupt_declaration_unmatched": penny_result["unmatched_invoices"] == 1,
        "wrong_payment_reference_unmatched": wrong_ref_held,
        "wrong_currency_unmatched": wrong_currency_held,
        "duplicate_payment_declaration_rejected": duplicate_rejected,
    }
    return {
        "kind": "CONTROLLED_NEGATIVE_CONTROLS_NOT_REAL_PAYMENT_OUTCOMES",
        "real_invoice_rows_replayed": len(invoices),
        "scenario_count": len(checks),
        "checks": checks,
        "all_controls_detected": all(checks.values()),
        "independently_cleared_bank_rows_used": 0,
        "real_world_economic_false_positive_rate": None,
    }


def benchmark_freight() -> dict:
    results: dict = {}
    for issuer, url in DOCUMENTS.items():
        raw = fetch_public(url)
        source_hash = require_frozen_source("document", issuer, raw)
        native = ingest_bytes(IngressEnvelope(
            ingress_id="test:" + issuer, buyer_id="BENCHMARK_ONLY",
            business_unit="ISOLATED_NO_CUSTOMER", transport="BATCH",
            filename=issuer + ".pdf",
        ), raw)
        texts = pdf_texts(raw)
        faces = extract_faces(issuer, texts)
        anchor = check_anchors(faces,
            GLOBAL_FACE_ANCHORS if issuer == "globaltranz" else ARCBEST_FACE_ANCHORS)
        unique = index_unique_invoice_faces(faces, issuer)
        out = {
            "source_url": url,
            "sha256": digest(raw),
            "frozen_original_sha256_verified": True,
            "source_face_catalog_sha256": digest(json.dumps(
                [(f.number, f.page, f.cents) for f in sorted(unique.values(), key=lambda row: row.number)],
                separators=(",", ":"), ensure_ascii=True).encode()),
            "pdf_bytes": len(raw),
            "pages": len(texts),
            "pages_with_text": sum(bool(t.strip()) for t in texts),
            "retally_native_ingress": native.status,
            "retally_native_route": native.route,
            "lab_adapter": "pymupdf-original-page-text-v1",
            "invoice_face_pages": len(faces),
            "distinct_invoice_face_ids": len(unique),
            "invoice_face_amounts_extracted": sum(f.cents is not None for f in unique.values()),
            "invoice_face_anchor_verification": anchor,
            "production_pdf_invoice_extraction_complete": False,
            "label_state": "UNKNOWN_NO_INDEPENDENT_RATE_OR_ADJUDICATION",
            "validated_overcharge_cents": 0,
            "realized_recovery_cents": 0,
        }
        if issuer == "globaltranz":
            out["original_invoice_line_amount_reconciliation"] = (
                globaltranz_invoice_line_total_benchmark(list(unique.values()), texts))
            out["canonical_v2_original_invoice_adjustment_lab"] = (
                globaltranz_canonical_v2_adjustment_replay(
                    list(unique.values()), texts, source_hash))
            statements = statement_rows(texts)
            invoice_rows = []
            statement_txns = []
            token: dict[str, str] = {}
            for f in unique.values():
                if f.cents is None or not f.invoice_date:
                    continue
                ident = "face:" + _safe_sha(f.number)
                invoice_rows.append(ReconTxn(
                    id=ident, amount=f"{Decimal(f.cents) / 100:.2f}",
                    date=f.invoice_date, currency="USD", reference=f.number))
                token[ident] = f.number
            for s in statements:
                ident = "statement:" + _safe_sha(s["number"])
                statement_txns.append(ReconTxn(
                    id=ident, amount=f"{Decimal(s['original']) / 100:.2f}",
                    date=s["date"], currency="USD", reference=s["number"]))
                token[ident] = s["number"]
            out["statement"] = {
                "source_type": "OPEN_BALANCE_NOT_CLEARED_PAYMENT",
                "rows": len(statements),
                "original_total_minor": sum(s["original"] for s in statements),
                "current_total_minor": sum(s["current"] for s in statements),
                "balance_delta_minor": sum(s["original"] - s["current"] for s in statements),
                "count_expectation_met": len(statements) == EXPECTED["globaltranz_statement_rows"],
                "original_total_expectation_met": sum(s["original"] for s in statements) == EXPECTED["globaltranz_original_total_minor"],
                "current_total_expectation_met": sum(s["current"] for s in statements) == EXPECTED["globaltranz_current_total_minor"],
                "face_to_statement_original_amount": _recon_result(invoice_rows, statement_txns, token),
                "bank_payment_reconciliation": "NOT_POSSIBLE_NO_BANK_RECORD",
            }
            # Explain face/statement non-joins without storing invoice numbers.
            by_statement_number: dict[str, list[dict]] = defaultdict(list)
            for row in statements:
                by_statement_number[row["number"]].append(row)
            face_ids = set(unique)
            statement_ids = set(by_statement_number)
            paired_ids = face_ids & statement_ids
            amount_consistent = sum(
                f.cents is not None and any(s["original"] == f.cents for s in by_statement_number[f.number])
                for f in unique.values() if f.number in paired_ids
            )
            source_date_gaps = [
                min(abs((datetime.fromisoformat(f.invoice_date) -
                         datetime.fromisoformat(st["date"])).days)
                    for st in by_statement_number[f.number])
                for f in unique.values()
                if f.number in paired_ids and f.invoice_date
            ]
            out["face_statement_identity_diagnostic"] = {
                "invoice_face_distinct_ids": len(face_ids),
                "statement_distinct_ids": len(statement_ids),
                "both_sources_share_identifier": len(paired_ids),
                "same_identifier_and_original_amount": amount_consistent,
                "source_date_gaps_over_180_days": sum(gap > 180 for gap in source_date_gaps),
                "maximum_face_to_statement_recorded_date_gap_days": max(source_date_gaps, default=None),
                "same_identifier_but_original_amount_differs": len(paired_ids) - amount_consistent,
                "invoice_face_not_listed_on_statement": len(face_ids - statement_ids),
                "statement_identifier_without_extracted_invoice_face": len(statement_ids - face_ids),
                "duplicate_statement_identifier_rows": len(statements) - len(statement_ids),
                "these_differences_are_not_payment_or_overcharge_findings": True,
            }
            parents = {re.sub(r"\s+A$", "", f.number) for f in unique.values()}
            out["invoice_families_adjustments_not_silently_collapsed"] = len(parents)
        else:
            # Source face amounts are not a bill-to-bank payment comparison.
            out["source_invoice_mode_ltl_count"] = sum(f.mode == "LTL" for f in unique.values())
            out["source_invoice_mode_tl_count"] = sum(f.mode == "TL" for f in unique.values())
            out["source_printed_rate_bol_reference_census"] = (
                arcbest_printed_rate_bol_reference_census(
                    list(unique.values()), texts, source_hash))
            out["embedded_original_vpq_quote_source_replay"] = (
                arcbest_embedded_vpq_quote_reconciliation(
                    list(unique.values()), texts, source_hash))
            out["co_bundled_motor_carrier_bol_source_replay"] = (
                arcbest_embedded_truckload_bol_reconciliation(
                    list(unique.values()), texts, source_hash,
                    layout_texts=pdf_texts(raw, sort=True)))
            out["retally_rating_engine"] = _rating_probe(faces, texts, digest(raw))
        results[issuer] = out
    return results





def arcbest_embedded_truckload_bol_reconciliation(
    faces: list[InvoiceFace], texts: list[str], pdf_sha256: str, *,
    layout_texts: list[str] | None = None,
) -> dict:
    """Link 2024 truckload invoice faces to co-bundled carrier BOL copies.

    The court exhibit embeds printed "Motor Carrier Bill of Lading" pages,
    sometimes multiple versions of ONE load. Only bound original invoice,
    load reference, shipment pickup date, and printed weight are compared.
    Copies are never new independent shipments; disagreeing printed piece
    counts remain explicit source conflicts rather than being overwritten.
    Source text, IDs, contacts, page contents and unique load numbers never
    enter the receipt. Same-PDF custody cannot authenticate signatures.
    """
    if pdf_sha256 != FROZEN_DOCUMENT_SHA256["arcbest"]:
        raise ValueError("ARCBEST_BOL_SOURCE_SHA256_MISMATCH")
    if type(texts) is not list or len(texts) > 100:
        raise ValueError("ARCBEST_BOL_SOURCE_PAGE_LIMIT")
    if layout_texts is not None and (
            type(layout_texts) is not list or len(layout_texts) != len(texts)
            or any(type(page) is not str or len(page) > 200_000 for page in layout_texts)):
        raise ValueError("ARCBEST_BOL_LAYOUT_SOURCE_PAGES_INVALID")
    if len({(f.number, f.page) for f in faces}) != len(faces):
        raise ValueError("ARCBEST_BOL_DUPLICATE_INVOICE_FACE")

    tl_faces = {}
    for face in faces:
        if (face.issuer != "arcbest" or not re.fullmatch(r"\d{9}", face.number)
                or type(face.page) is not int or face.page < 1
                or face.page > len(texts)):
            raise ValueError("ARCBEST_BOL_INVALID_FACE")
        if face.mode != "TL":
            continue
        if face.number in tl_faces:
            raise ValueError("ARCBEST_BOL_DUPLICATE_INVOICE")
        page = texts[face.page - 1]
        if (not re.search(r"\bORIGINAL\s+INVOICE\b", page, re.I)
                or not re.search(r"\bFreight\s+bill\s+No\.?\s*:\s*" +
                                 re.escape(face.number) + r"\b", page, re.I)
                or face.cents is None or not face.shipment_date):
            raise ValueError("ARCBEST_BOL_INVOICE_SOURCE_UNBOUND")
        # Summary is the invoice's printed rate-billed weight, not an
        # independently certified loaded weight.
        summary = re.search(
            r"\bTotal\s+Pieces\s+Total\s+Weight\s+TOTAL\s+AMOUNT\s+"
            r"\$\s*([\d,]+\.\d{2})\s+([\d,]+)\s+([\d,]+)",
            page, re.I,
        )
        if not summary or minor(summary.group(1)) != face.cents:
            raise ValueError("ARCBEST_BOL_INVOICE_SUMMARY_UNREADABLE")
        weight = int(summary.group(3).replace(",", ""))
        if weight < 1:
            raise ValueError("ARCBEST_BOL_INVOICE_WEIGHT_UNSUPPORTED")
        load_refs = set(re.findall(r"\bCRN\s*:\s*(\d{10})\b", page, re.I))
        tl_faces[face.number] = {
            "face": face, "weight": weight, "pieces": int(summary.group(2).replace(",", "")),
            "load_refs": load_refs,
        }

    bol_pages = 0
    bound_pages = 0
    joined_pages = 0
    matching_invoice_loads = 0
    matching_weights = 0
    matching_pickup_dates = 0
    pickup_extraction_states = Counter()
    bol_header_date_states = Counter()
    pickup_date_exception_copy_ordinals = []
    pickup_date_relative_day_buckets = Counter()
    layout_pickup_observation_states = Counter()
    layout_pickup_matches_invoice = 0
    layout_pickup_disagrees_primary = 0
    missing = Counter()
    by_invoice = {}
    anonymous = []
    for page_number, page in enumerate(texts, 1):
        if not re.search(r"\bMotor\s+Carrier\s+Bill\s+of\s+Lading\b", page, re.I):
            continue
        bol_pages += 1
        pro = re.search(r"\bArcBest\s+Pronumber\s*:\s*(\d{9})\b", page, re.I)
        load = re.search(r"\bLoad\s*#\s*:\s*(\d{10})\b", page, re.I)
        if not pro or not load:
            missing["BOL_FIRST_PAGE_PRO_OR_LOAD_UNREADABLE"] += 1
            anonymous.append((page_number, "UNBOUND_BOL_IDENTIFIERS"))
            continue
        face_doc = tl_faces.get(pro.group(1))
        if face_doc is None:
            missing["BOL_NOT_LINKED_TO_TL_INVOICE_FACE"] += 1
            anonymous.append((page_number, "NOT_BOUND_TO_ORIGINAL_INVOICE"))
            continue
        bound_pages += 1
        # Do not create a *linked* load group until the original invoice
        # itself proves the matching CRN load reference. A same-numbered
        # freight bill with a wrong load is not a joined shipment.
        load_matches_invoice = load.group(1) in face_doc["load_refs"]
        if not load_matches_invoice:
            missing["BOL_LOAD_REFERENCE_NOT_ON_INVOICE"] += 1
            anonymous.append((page_number, "BOL_LOAD_NOT_ON_INVOICE"))
            continue
        matching_invoice_loads += 1
        groups = by_invoice.setdefault(pro.group(1), [])
        pickup_start = re.search(r"\bStop\s+1\s*-\s*Pick\s*Up\b", page, re.I)
        delivery_start = re.search(r"\bStop\s+2\s*-\s*Delivery\b", page, re.I)
        pickup_region = (page[pickup_start.end():delivery_start.start()]
                         if pickup_start and delivery_start and
                         pickup_start.end() < delivery_start.start() else "")
        pickup = re.search(
            r"\bDate\s*:\s*(\d{1,2}/\d{1,2}/\d{4})\b", pickup_region, re.I
        )
        try:
            # The U.S. motor-carrier BOL uses MONTH/DAY/YEAR; the shared
            # UK accounting parser starts day/month and silently swaps
            # dates such as 5/1/2024. Never use that default for freight BOLs.
            pickup_day = (iso_date(pickup.group(1), formats=("%m/%d/%Y",))
                          if pickup else None)
        except ValueError:
            pickup_day = None
        if pickup_start is None:
            pickup_extract_state = "PICKUP_STOP_LABEL_ABSENT"
        elif delivery_start is None:
            pickup_extract_state = "DELIVERY_BOUNDARY_ABSENT"
        elif pickup_start.end() >= delivery_start.start():
            pickup_extract_state = "PICKUP_DELIVERY_ANCHORS_REVERSED"
        elif pickup is None:
            pickup_extract_state = "PICKUP_REGION_DATE_NOT_EXTRACTED"
        elif pickup_day is None:
            pickup_extract_state = "PICKUP_DATE_INVALID_US_FORMAT"
        elif pickup_day == face_doc["face"].shipment_date:
            pickup_extract_state = "PICKUP_DATE_MATCHES_INVOICE"
        else:
            pickup_extract_state = "EXPLICIT_PICKUP_DATE_DIFFERS_FROM_INVOICE"

        # Document creation date is NOT the pickup date. In the real PDF
        # May 30 headers coexist with May 31 pickup events. Track only
        # a category, not the date, invoice, load, shipper or account.
        header_fragment = page[:pickup_start.start()] if pickup_start else page[:350]
        header_date_match = re.search(
            r"\bDate\s*:\s*(\d{1,2}/\d{1,2}/\d{4})\b",
            header_fragment, re.I,
        )
        header_day = None
        if header_date_match is not None:
            try:
                header_day = iso_date(header_date_match.group(1), formats=("%m/%d/%Y",))
            except ValueError:
                pass
        if header_day is None:
            bol_header_state = "BOL_HEADER_DATE_NOT_READABLE"
        elif pickup_day is None:
            bol_header_state = "PICKUP_DATE_UNREADABLE_HEADER_NOT_SUBSTITUTE"
        elif header_day == pickup_day:
            bol_header_state = "DOCUMENT_HEADER_DATE_EQUALS_PICKUP"
        else:
            bol_header_state = "DOCUMENT_HEADER_DATE_DIFFERS_FROM_PICKUP"

        layout_pickup_day = None
        layout_state = None
        if layout_texts is not None:
            # Strict *independent reading order*, but the SAME PDF bytes.
            # Require both original identity anchors on the same PDF page.
            reading = layout_texts[page_number - 1]
            if (not re.search(r"\bMotor\s+Carrier\s+Bill\s+of\s+Lading\b", reading, re.I)
                    or not re.search(r"\bLoad\s*#\s*:\s*" +
                                     re.escape(load.group(1)) + r"\b", reading, re.I)
                    or not re.search(r"\bArcBest\s+Pronumber\s*:\s*" +
                                     re.escape(pro.group(1)) + r"\b", reading, re.I)):
                layout_state = "LAYOUT_READING_SOURCE_IDENTITY_UNBOUND"
            else:
                st = re.search(r"\bStop\s+1\s*-\s*Pick\s*Up\b", reading, re.I)
                en = re.search(r"\bStop\s+2\s*-\s*Delivery\b", reading, re.I)
                if not st or not en or st.end() >= en.start():
                    layout_state = "LAYOUT_READING_STOP_ANCHORS_UNBOUND"
                else:
                    region = reading[st.end():en.start()]
                    tokens = re.findall(
                        r"\bDate\s*:\s*(\d{1,2}/\d{1,2}/\d{4})\b",
                        region, re.I)
                    try:
                        dates = {
                            iso_date(value, formats=("%m/%d/%Y",)) for value in tokens
                        }
                    except ValueError:
                        dates = set()
                    if not dates:
                        layout_state = "LAYOUT_READING_PICKUP_DATE_NOT_READABLE"
                    elif len(dates) > 1:
                        layout_state = "LAYOUT_READING_CONFLICTING_PICKUP_DATES"
                    else:
                        layout_pickup_day = next(iter(dates))
                        layout_state = "LAYOUT_READING_PICKUP_DATE_UNAMBIGUOUS"

        summaries = re.findall(
            r"\bTotal\s+HU\s*:\s*(\d+)\s+Total\s+Pcs\s*:\s*(\d+)\s+"
            r"Total\s+Cmdty\s*:\s*(\d+)\s+Total\s+Wgt\s*:\s*"
            r"([\d,]+)\s*lbs\b", page, re.I,
        )
        numbers = {(int(m[0]), int(m[1]), int(m[2]),
                    int(m[3].replace(",", ""))) for m in summaries}
        if not numbers or len(numbers) != 1:
            missing["BOL_TOTALS_MISSING_OR_INTERNALLY_CONFLICTING"] += 1
            anonymous.append((page_number, "UNREADABLE_OR_CONFLICTING_BOL_TOTALS"))
            continue
        hu, pieces, commodities, weight = next(iter(numbers))
        if hu < 1 or commodities < 1 or weight < 1:
            missing["BOL_TOTALS_OUT_OF_BOUNDS"] += 1
            anonymous.append((page_number, "INVALID_PRINTED_BOL_TOTALS"))
            continue

        joined_pages += 1
        weight_match = weight == face_doc["weight"]
        date_match = pickup_day == face_doc["face"].shipment_date
        pickup_extraction_states[pickup_extract_state] += 1
        bol_header_date_states[bol_header_state] += 1
        if layout_state is not None:
            layout_pickup_observation_states[layout_state] += 1
        if layout_pickup_day is not None:
            layout_pickup_matches_invoice += int(
                layout_pickup_day == face_doc["face"].shipment_date)
            layout_pickup_disagrees_primary += int(
                layout_pickup_day != pickup_day)
        matching_weights += int(weight_match)
        matching_pickup_dates += int(date_match)
        groups.append({
            "load": load.group(1), "weight": weight, "pieces": pieces,
            "hu": hu, "date_match": date_match, "weight_match": weight_match,
        })
        anonymous.append((page_number,
                          "SAME_INVOICE_LOAD",
                          "SOURCE_WEIGHT_AGREES" if weight_match else "SOURCE_WEIGHT_CONFLICT",
                          "PICKUP_DATE_AGREES" if date_match else "PICKUP_DATE_CONFLICT"))
        if not weight_match:
            missing["BOL_INVOICE_PRINTED_WEIGHT_CONFLICT"] += 1
        if not date_match:
            # Only the 1-based position among public BOL-first-pages and
            # relative calendar day offset. No customer/invoice/load identity,
            # raw source date, document content or shipment metadata exported.
            pickup_date_exception_copy_ordinals.append(bol_pages)
            if pickup_day is None:
                pickup_date_relative_day_buckets["UNEXTRACTED"] += 1
            else:
                delta = (datetime.fromisoformat(pickup_day)
                         - datetime.fromisoformat(face_doc["face"].shipment_date)).days
                pickup_date_relative_day_buckets[
                    "EARLIER_ONE_DAY" if delta == -1 else
                    "LATER_ONE_DAY" if delta == 1 else
                    "EARLIER_MULTIDAY" if delta < -1 else
                    "LATER_MULTIDAY" if delta > 1 else "OTHER"
                ] += 1
            missing["BOL_PICKUP_INVOICE_DATE_CONFLICT"] += 1
    conflict_piece_groups = 0
    conflict_weight_groups = 0
    repeated_groups = 0
    for groups in by_invoice.values():
        if len(groups) > 1:
            repeated_groups += 1
        conflict_piece_groups += int(len({x["pieces"] for x in groups}) > 1)
        conflict_weight_groups += int(len({x["weight"] for x in groups}) > 1)
    if bol_pages > 30:
        raise ValueError("ARCBEST_BOL_EXCESS_SOURCE_DOCUMENT_PAGES")
    return {
        "scope": "ARCBEST_PUBLIC_ORIGINAL_PDF_INVOICE_TO_COBUNDLED_MOTOR_CARRIER_BOL_REFERENCES",
        "original_pdf_sha256": pdf_sha256,
        "original_truckload_invoice_faces": len(tl_faces),
        "co_bundled_motor_carrier_bol_first_pages": bol_pages,
        "co_bundled_bol_pages_bound_to_source_invoice": bound_pages,
        "source_invoice_load_reference_matching_bol_pages": matching_invoice_loads,
        "source_invoice_bol_totals_readable_pages": joined_pages,
        "source_invoice_printed_weight_matches_on_bol_copies": matching_weights,
        "source_invoice_pickup_date_matches_on_bol_copies": matching_pickup_dates,
        "pickup_extraction_state_counts": dict(sorted(pickup_extraction_states.items())),
        "bol_header_vs_pickup_date_state_counts": dict(sorted(bol_header_date_states.items())),
        "pickup_date_exception_copy_ordinals": pickup_date_exception_copy_ordinals,
        "pickup_date_relative_day_buckets": dict(sorted(pickup_date_relative_day_buckets.items())),
        "layout_reading_order_used_on_same_frozen_pdf": layout_texts is not None,
        "layout_pickup_observation_state_counts": dict(sorted(layout_pickup_observation_states.items())),
        "layout_reading_pickup_dates_matching_invoice": layout_pickup_matches_invoice,
        "layout_reading_pickup_date_disagreements_with_primary": layout_pickup_disagrees_primary,
        "layout_reading_is_not_independent_document_custody": True,
        "unique_truckload_invoices_with_co_bundled_bol_copies": len(by_invoice),
        "duplicate_co_bundled_bol_copy_pages_not_new_shipments":
            sum(max(0, len(x) - 1) for x in by_invoice.values()),
        "repeated_load_groups_with_piece_count_disagreements": conflict_piece_groups,
        "repeated_load_groups_with_weight_disagreements": conflict_weight_groups,
        "repeated_load_groups_total": repeated_groups,
        "anonymous_page_class_sha256": digest(json.dumps(
            sorted(anonymous), separators=(",", ":")).encode("utf-8")),
        "source_notes": [
            "Printed BOL copies in the SAME public bankruptcy exhibit are not independently custodied or authenticated.",
            "Same load printed in several versions is ONE shipment; conflicting piece counts remain unresolved.",
            "A printed invoice/BOL weight match is not certified actual loaded weight.",
            "Visible signature field labels are not verified signatures or proof of delivery.",
        ],
        "independently_authenticated_signed_bol_acceptances": 0,
        "independent_custody_original_bol_verified": 0,
        "customer_rate_authority_verified": 0,
        "actual_delivery_proof_independently_verified": 0,
        "bank_cleared_payment_verified": 0,
        "independently_adjudicated_customer_overcharges": 0,
        "commercial_reuse_authorized": False,
        "verified_retally_cash_recovered_cents": 0,
        "original_source_customer_or_load_identifiers_exported": 0,
        "external_contact_actions": 0,
        "unresolved_reason_counts": dict(sorted(missing.items())),
    }


def arcbest_embedded_vpq_quote_reconciliation(
    faces: list[InvoiceFace], texts: list[str], pdf_sha256: str,
) -> dict:
    """Match co-bundled quote pages to original invoices without promoting rates.

    The public bankruptcy-claim PDF contains source-printed original invoices
    AND appended ArcBest volume-pricing quotation documents. Match by exact
    normalized quotation code, shipment date, quoted weight and invoice face
    money, entirely in ephemeral runner memory. Quote documents come from the
    SAME frozen PDF as the invoice; they are not independent BOL acceptance,
    payment, external issuer certification or independently adjudicated truth.
    Original identifiers, customer details, source text, quote page numbers
    and quote prices must NEVER enter the returned receipt or Git.
    """
    if pdf_sha256 != FROZEN_DOCUMENT_SHA256["arcbest"]:
        raise ValueError("ARCBEST_EMBEDDED_QUOTE_SOURCE_SHA256_MISMATCH")
    if len({(face.number, face.page) for face in faces}) != len(faces):
        raise ValueError("ARCBEST_EMBEDDED_QUOTE_DUPLICATE_INVOICE")
    if not isinstance(texts, list) or len(texts) > 100:
        raise ValueError("ARCBEST_EMBEDDED_QUOTE_UNBOUNDED_SOURCE")

    def quote_id(token: str) -> str:
        if type(token) is not str:
            raise ValueError("ARCBEST_EMBEDDED_QUOTE_ID_INVALID")
        cleaned = re.sub(r"[-\s]", "", token).upper()
        if not re.fullmatch(r"[A-Z0-9]{8,18}", cleaned):
            raise ValueError("ARCBEST_EMBEDDED_QUOTE_ID_INVALID")
        return cleaned

    def quote_day(token: str) -> str:
        try:
            return datetime.strptime(token.strip(), "%d-%b-%Y").date().isoformat()
        except (ValueError, TypeError) as exc:
            raise ValueError("ARCBEST_EMBEDDED_QUOTE_DATE_INVALID") from exc

    def dollars_to_cents(token: str) -> int:
        # Strict original USD decimal text; no inferred or rounded floats.
        raw = token.strip()
        if not re.fullmatch(r"(?:\d+|\d{1,3}(?:,\d{3})+)\.\d{2}", raw):
            raise ValueError("ARCBEST_EMBEDDED_QUOTE_MONEY_INVALID")
        return int(raw.replace(",", "").replace(".", ""))

    quote_pages = {}
    for i, page in enumerate(texts, start=1):
        if not re.search(r"\bVolume\s+Pricing\s+Quotation\b", page, re.I):
            continue
        code = re.search(
            r"\bVPQ\s+Quotation\s+ID\s*:\s*"
            r"([A-Z0-9]{8,18})(?:\s*-\s*([A-Z]))?\b",
            page, re.I,
        )
        effective = re.search(r"\bEffective\s+Date\s*:\s*(\d{1,2}-[A-Z]{3}-\d{4})", page, re.I)
        expires = re.search(r"\bExpiration\s+Date\s*:\s*(\d{1,2}-[A-Z]{3}-\d{4})", page, re.I)
        minimum = re.search(
            r"\bMinimum\s+price\s+including\s+Fuel\s+Surcharge\*?\s*"
            r"\(max\s*([\d,]+)\s*lbs\s*/\s*(\d{1,3})\s*linear\s*ft\)"
            r"\s*:\s*\$\s*([\d,]+\.\d{2})",
            page, re.I,
        )
        extra = re.search(
            r"\bCharge\s+per\s+additional\s+linear\s+foot\s*:\s*"
            r"\$\s*([\d,]+\.\d{2})",
            page, re.I,
        )
        weight = re.search(r"\bWeight\s*:\s*([\d,]+)\s*lbs\b", page, re.I)
        if not all((code, effective, expires, minimum, extra, weight)):
            raise ValueError("ARCBEST_EMBEDDED_QUOTE_PRIMARY_FIELDS_INCOMPLETE")
        ident = quote_id(code.group(1) + (code.group(2) or ""))
        if ident in quote_pages:
            raise ValueError("ARCBEST_EMBEDDED_QUOTE_DUPLICATE_QUOTE_ID")
        starts, ends = quote_day(effective.group(1)), quote_day(expires.group(1))
        if starts > ends:
            raise ValueError("ARCBEST_EMBEDDED_QUOTE_REVERSED_EFFECTIVE_WINDOW")
        max_weight, max_feet = int(minimum.group(1).replace(",", "")), int(minimum.group(2))
        quoted_weight = int(weight.group(1).replace(",", ""))
        if min(max_weight, max_feet, quoted_weight) <= 0:
            raise ValueError("ARCBEST_EMBEDDED_QUOTE_NONPOSITIVE_BASIS")
        quote_pages[ident] = {
            "page": i, "from": starts, "to": ends,
            "max_weight": max_weight, "max_feet": max_feet,
            "quoted_weight": quoted_weight,
            "minimum_cents": dollars_to_cents(minimum.group(3)),
            "per_extra_foot_cents": dollars_to_cents(extra.group(1)),
        }

    counts = Counter()
    anonymous = []
    seen_invoice_codes = set()
    for face in faces:
        if (face.issuer != "arcbest" or face.cents is None or face.cents < 0
                or not face.shipment_date or face.page < 1
                or face.page > len(texts) or not face.number):
            raise ValueError("ARCBEST_EMBEDDED_QUOTE_INVOICE_FACE_INVALID")
        page = texts[face.page - 1]
        if not re.search(r"\bTariff\s*:\s*VPQ\b", page, re.I):
            continue
        counts["vpq_original_invoice_faces"] += 1
        if (not re.search(r"\bORIGINAL\s+INVOICE\b", page, re.I)
                or not re.search(r"\bFreight\s+bill\s+No\.?\s*:\s*" +
                                 re.escape(face.number) + r"\b", page, re.I)):
            counts["unbound_invoice_page"] += 1
            continue
        schedule = re.search(
            r"\bPQ\s+SCHEDULE\s+NO\s*:\s*([A-Z0-9-]{8,20})\b",
            page, re.I,
        )
        if not schedule:
            counts["vpq_no_invoice_schedule_code"] += 1
            continue
        ident = quote_id(schedule.group(1))
        if ident in seen_invoice_codes:
            raise ValueError("ARCBEST_EMBEDDED_QUOTE_ID_REUSED_ACROSS_INVOICES")
        seen_invoice_codes.add(ident)
        quote = quote_pages.get(ident)
        if quote is None:
            counts["vpq_no_embedded_quote_id_match"] += 1
            continue
        counts["vpq_exact_id_matched_quote_documents_in_same_pdf"] += 1
        if not quote["from"] <= face.shipment_date <= quote["to"]:
            counts["vpq_outside_quote_date_window"] += 1
            continue
        counts["vpq_shipment_within_quoted_date_window"] += 1
        # A weight printed on both the invoice and quote is cross-document
        # corroboration inside ONE bankruptcy bundle, not independently
        # measured actual loaded weight.
        listed_weight = re.search(
            r"\bITEM\s+[A-Z0-9-]{5,22}\s+([\d,]+)\s+PPU\b", page, re.I,
        )
        if listed_weight is None:
            counts["vpq_invoice_weight_not_extracted"] += 1
            continue
        original_weight = int(listed_weight.group(1).replace(",", ""))
        if original_weight != quote["quoted_weight"]:
            counts["vpq_invoice_quote_weight_conflict"] += 1
            continue
        counts["vpq_co_bundled_printed_weight_agrees"] += 1

        result = "INVOICE_QUOTE_AMOUNT_UNRESOLVED"
        if face.cents == quote["minimum_cents"]:
            result = "EXACT_PRINTED_QUOTE_MINIMUM_MATCH"
            counts["vpq_exact_printed_quote_minimum_amount_matches"] += 1
        else:
            # This is a deliberately CONDITIONAL check: a printed LWH first
            # dimension need not be independently confirmed trailer footage.
            length = re.search(
                r"\bLWH\s*:\s*([\d,]+)\s*[Xx]\s*[\d,]+\s*[Xx]\s*[\d,]+\s*INCHES\b",
                page, re.I,
            )
            if length:
                length_inches = int(length.group(1).replace(",", ""))
                length_feet_rounded_up = (length_inches + 11) // 12
                added_feet = max(0, length_feet_rounded_up - quote["max_feet"])
                if (added_feet > 0 and
                        quote["minimum_cents"] + added_feet *
                        quote["per_extra_foot_cents"] == face.cents):
                    result = "CONDITIONAL_PRINTED_LWH_LINEAR_FOOT_FORMULA_MATCH"
                    counts["vpq_conditional_printed_length_formula_matches"] += 1
        if result == "INVOICE_QUOTE_AMOUNT_UNRESOLVED":
            counts["vpq_quoted_money_not_reconciled"] += 1
        # Hash ONLY fixed public page indices and our finite internal enums;
        # never print/persist quote ID, invoice ID or business names.
        anonymous.append((face.page, quote["page"], result))

    nfaces = counts["vpq_original_invoice_faces"]
    successful_matches = (
        counts["vpq_exact_printed_quote_minimum_amount_matches"]
        + counts["vpq_conditional_printed_length_formula_matches"]
    )
    return {
        "scope": "ORIGINAL_ARCBEST_SAME_PDF_QUOTE_INVOICE_ARITHMETIC_NOT_CUSTOMER_RECOVERY",
        "source_original_pdf_sha256": pdf_sha256,
        "embedded_original_vpq_quotation_pages": len(quote_pages),
        "vpq_original_invoice_faces": nfaces,
        "same_pdf_exact_quotation_id_invoice_joins":
            counts["vpq_exact_id_matched_quote_documents_in_same_pdf"],
        "invoice_dates_within_printed_quote_effective_window":
            counts["vpq_shipment_within_quoted_date_window"],
        "printed_invoice_quoted_weights_agree":
            counts["vpq_co_bundled_printed_weight_agrees"],
        "invoice_amount_equals_printed_quote_minimum":
            counts["vpq_exact_printed_quote_minimum_amount_matches"],
        "conditional_printed_length_formula_matches":
            counts["vpq_conditional_printed_length_formula_matches"],
        "invoice_quote_money_unresolved": nfaces - successful_matches,
        "anonymous_page_and_match_class_digest_sha256": digest(json.dumps(
            sorted(anonymous), separators=(",", ":")).encode("utf-8")),
        "quote_and_invoice_documents_are_co_bundled_in_same_source_pdf": True,
        "conditional_length_footage_is_independently_certified": False,
        "original_signed_bol_quotes_independently_verified": 0,
        "separate_quote_acceptance_independently_verified": 0,
        "commercial_reuse_authorized": False,
        "independent_customer_invoice_overcharge_labels": 0,
        "bank_cleared_payments_verified": 0,
        "verified_retally_recovered_cash_cents": 0,
        "raw_invoice_quote_bol_identifiers_exported": 0,
        "customer_contact_actions": 0,
        "unresolved_reason_counts": {
            key: counts[key] for key in sorted(counts)
            if key in {
                "unbound_invoice_page", "vpq_no_invoice_schedule_code",
                "vpq_no_embedded_quote_id_match",
                "vpq_outside_quote_date_window",
                "vpq_invoice_weight_not_extracted",
                "vpq_invoice_quote_weight_conflict",
                "vpq_quoted_money_not_reconciled",
            } and counts[key] > 0
        },
    }


def arcbest_printed_rate_bol_reference_census(
    faces: list[InvoiceFace], texts: list[str], pdf_sha256: str,
) -> dict:
    """Count source-printed *hints*, never prove an applicable customer rate.

    Uses only the already-frozen public ArcBest PDF already fetched by the
    isolated original-document lab. No raw invoice number, quote reference,
    BOL identifier, contact, description or other source text is output.
    A printed account tariff token or VPQ label is not the effective contract,
    original signed quote or underlying bill of lading.
    """
    if pdf_sha256 != FROZEN_DOCUMENT_SHA256["arcbest"]:
        raise ValueError("ARCBEST_SOURCE_SHA256_MISMATCH")
    if len({(f.number, f.page) for f in faces}) != len(faces):
        raise ValueError("ARCBEST_DUPLICATE_FACE_REFERENCE")
    tariff_counts = Counter()
    bol_counts = Counter()
    pricing_bol_joint = Counter()
    observed = bound = missing_identity = 0
    aggregate = []
    for face in faces:
        if (face.issuer != "arcbest" or face.cents is None or face.cents < 0
                or face.page < 1 or face.page > len(texts) or not face.number):
            raise ValueError("ARCBEST_INVALID_SOURCE_FACE")
        observed += 1
        page = texts[face.page - 1]
        # The existing source extractor has already found the invoice face.
        # Rebind its page and original freight-bill ID before accepting any
        # nearby tariff/BOL tokens. Never export the identifier.
        if (not re.search(r"\bORIGINAL\s+INVOICE\b", page, re.I)
                or not re.search(r"\bFreight\s+bill\s+No\.?\s*:\s*" +
                                 re.escape(face.number) + r"\b", page, re.I)):
            missing_identity += 1
            tariff_counts["UNBOUND_SOURCE_PAGE"] += 1
            bol_counts["UNBOUND_SOURCE_PAGE"] += 1
            pricing_bol_joint[("UNBOUND_SOURCE_PAGE", "UNBOUND_SOURCE_PAGE")] += 1
            continue
        bound += 1
        tariff_tokens = {
            x.upper() for x in re.findall(
                r"\bTariff\s*:\s*([A-Za-z0-9][A-Za-z0-9._-]{0,31})\b",
                page, re.I)
        }
        if not tariff_tokens:
            tariff = "NO_PRINTED_TARIFF_REFERENCE"
        elif len(tariff_tokens) > 1:
            tariff = "CONFLICTING_PRINTED_TARIFF_REFERENCES"
        elif next(iter(tariff_tokens)) == "VPQ":
            tariff = "PRINTED_VOLUME_QUOTE_MARKER_ONLY"
        elif re.fullmatch(r"ABF[0-9]{3,10}", next(iter(tariff_tokens))):
            tariff = "PRINTED_ABF_ACCOUNT_REFERENCE_ONLY"
        else:
            tariff = "OTHER_PRINTED_PRICING_REFERENCE_ONLY"
        tariff_counts[tariff] += 1

        bol_tokens = {
            " ".join(x.upper().split()) for x in re.findall(
                r"\bBill\s+of\s+Lading\s+No\.?\s*:\s*"
                r"(SEE\s+BELOW|[A-Za-z0-9][A-Za-z0-9/.-]{0,31})",
                page, re.I)
        }
        placeholders = {"SEE BELOW", "NS", "NONE", "N/A", "NA", "UNKNOWN",
                        "TARIFF", "AMOUNT", "DUE", "PAYMENT", "SHIPPING",
                        "SHIPMENT", "DATE", "SEE"}
        if not bol_tokens:
            bol = "BOL_HEADER_NOT_READABLE"
        elif len(bol_tokens) > 1:
            bol = "BOL_HEADER_CONFLICTING_REFERENCES"
        elif next(iter(bol_tokens)) in placeholders:
            bol = "BOL_HEADER_PLACEHOLDER_ONLY"
        else:
            bol = "BOL_HEADER_IDENTIFIER_PRINTED_ONLY"
        bol_counts[bol] += 1
        pricing_bol_joint[(tariff, bol)] += 1
        aggregate.append((face.page, tariff, bol))
    # Anonymous category digest: only page number + fixed classification
    # enums; no printed commercial identifiers or invoice details.
    return {
        "scope": "ORIGINAL_ARCBEST_PDF_PRINTED_REFERENCE_HINTS_ONLY",
        "source_original_pdf_sha256": pdf_sha256,
        "original_invoice_faces_considered": observed,
        "source_page_identity_bound_count": bound,
        "unbound_original_source_pages": missing_identity,
        "printed_tariff_reference_class_counts": dict(sorted(tariff_counts.items())),
        "printed_bol_header_class_counts": dict(sorted(bol_counts.items())),
        # Join the *same* invoice's printed pricing class to its printed BOL
        # header class, exposing only fixed enum counts, never the BOL or
        # quotation identifiers themselves. This is not original BOL custody.
        "printed_pricing_bol_joint_class_counts": {
            pricing + "|" + bol: count
            for (pricing, bol), count in sorted(pricing_bol_joint.items())
        },
        "printed_vpq_with_bol_header_identifier_only": pricing_bol_joint[
            ("PRINTED_VOLUME_QUOTE_MARKER_ONLY", "BOL_HEADER_IDENTIFIER_PRINTED_ONLY")
        ],
        "printed_vpq_without_bol_header_identifier": sum(
            count for (pricing, bol), count in pricing_bol_joint.items()
            if pricing == "PRINTED_VOLUME_QUOTE_MARKER_ONLY"
            and bol != "BOL_HEADER_IDENTIFIER_PRINTED_ONLY"
        ),
        "original_bol_quote_id_correspondence_independently_verified": 0,
        "printed_bol_header_is_not_original_bol_custody": True,
        "anonymous_page_category_digest_sha256": digest(json.dumps(
            sorted(aggregate), separators=(",", ":")).encode("utf-8")),
        "source_pdf_printed_reference_not_executed_rate_contract": True,
        "original_customer_quote_documents_independently_verified": 0,
        "independently_custodied_original_bol_documents": 0,
        "shipment_effective_customer_rate_authorities_verified": 0,
        "independently_scored_customer_overcharges": 0,
        "original_source_identifiers_exported": 0,
        "verified_retally_recovered_cash_cents": 0,
        "third_party_contacts": 0,
    }


def _rating_probe(faces: list[InvoiceFace], texts: list[str], pdf_sha256: str) -> dict:
    """Run the actual freight schema/rating engine on SOURCE-DERIVED lab proxies.

    PDF invoice 'total weight' is a BILL-REPORTED rated weight, not an
    independently established actual shipment weight. Shipment date substitutes
    for absent invoice issue date. Invoice face total substitutes for a detailed
    freight charge breakdown. These are prohibited as freight-accuracy ground
    truth and may only smoke-test the engine's REVIEW_REQUIRED behavior.
    """
    from freight.canonical_schema import ChargeLine, ShipmentFacts, SourceArtifact, build_record
    from freight.rate_authority import AuthorityBook
    from freight.rating_engine import REVIEW_REQUIRED, rate_record

    accepted = blocked = review = unsafe = 0
    reasons: Counter = Counter()
    rating_hashes = []
    for face in faces:
        page_text = texts[face.page - 1]
        if (face.cents is None or not face.shipment_date or
                not face.mode or face.cents <= 0):
            blocked += 1
            reasons["SOURCE_MISSING_AMOUNT_MODE_OR_SHIPMENT_DATE"] += 1
            continue

        # Parse shipper and consignee ZIP codes from the repeated main
        # invoice freight-bill header, not from the lockbox/Bill To fields.
        references = list(re.finditer(
            r"Freight\s+Bill\s+No:?\s*" + re.escape(face.number) + r"\b",
            page_text, re.I))
        if len(references) < 2:
            blocked += 1
            reasons["MAIN_FREIGHT_BILL_SHIPPER_CONSIGNEE_NOT_FOUND"] += 1
            continue
        shipment_region = page_text[references[-1].end():]
        shipment_region = re.split(r"Shipping\s+Date:", shipment_region, maxsplit=1, flags=re.I)[0]
        zips = re.findall(r"\b(\d{5})(?:-\d{4})?\b", shipment_region)
        if len(zips) != 2:
            blocked += 1
            reasons["SOURCE_ORIGIN_DESTINATION_POSTAL_AMBIGUOUS"] += 1
            continue

        # Read printed billed pieces/weight only. Never silently infer it
        # from later weight certificates or third-party contracted rates.
        weight = re.search(
            r"Total\s+Pieces\s+Total\s+Weight\s+TOTAL\s+AMOUNT\s+"
            r"\$?\s*[\d,]+\.\d{2}\s+([\d,]+)\s+([\d,]+)",
            page_text, re.I,
        )
        if not weight:
            blocked += 1
            reasons["SOURCE_BILLED_PIECES_WEIGHT_UNREADABLE"] += 1
            continue
        pieces = int(weight.group(1).replace(",", ""))
        pounds = int(weight.group(2).replace(",", ""))
        if pieces < 1 or pounds < 1:
            blocked += 1
            reasons["SOURCE_NON_POSITIVE_BILLED_PIECES_WEIGHT"] += 1
            continue

        document = SourceArtifact(
            source_id="public:arcbest:" + _safe_sha(face.number),
            kind="PUBLIC_COURT_ORIGINAL_INVOICE",
            sha256=pdf_sha256,
            observed_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            transport="BATCH", filename="arcbest.pdf",
        )
        # All three stand-ins are explicitly test-only, not trusted buyer facts.
        record = build_record(
            buyer_id="ISOLATED_PUBLIC_RESEARCH_ONLY", business_unit="DOCUMENT_PROBE",
            invoice_id=face.number, invoice_date=face.shipment_date,
            customer_id="SDI_USA_LLC", currency="USD",
            shipment=ShipmentFacts(
                shipment_id="invoice-reference:" + face.number,
                carrier_id="ABF_FREIGHT", mode=face.mode,
                service_date=face.shipment_date,
                origin_postal=zips[0], destination_postal=zips[1],
                actual_weight_grams=int((Decimal(pounds) * Decimal("453.59237")).to_integral_value()),
                package_count=pieces,
            ),
            charges=(ChargeLine(
                charge_id="LAB_INVOICE_FACE_" + _safe_sha(face.number),
                charge_code="DOCUMENT_FACE_TOTAL_NOT_RATE_LINE",
                billed_cents=face.cents),),
            sources=(document,),
        )
        try:
            outcome = rate_record(record, AuthorityBook(()))
            rerun = rate_record(record, AuthorityBook(()))
            if (outcome.status != REVIEW_REQUIRED or
                    outcome.expected_total_cents is not None or
                    outcome.variance_cents is not None or
                    outcome.rating_hash != rerun.rating_hash):
                unsafe += 1
                reasons["ENGINE_UNSAFE_DECISION_OR_NONDETERMINISM"] += 1
                continue
            accepted += 1
            review += 1
            rating_hashes.append(outcome.rating_hash)
        except ValueError:
            blocked += 1
            reasons["SCHEMA_REJECTED_LAB_PROXY"] += 1
    return {
        "invoice_faces_considered": len(faces),
        "lab_proxy_canonical_records_executed": accepted,
        "source_completeness_blocked": blocked,
        "engine_review_required": review,
        "unsafe_auto_money_or_nondeterministic": unsafe,
        "auto_overcharges_asserted": 0,
        "lab_proxy_rating_hash_sha256": digest(
            "".join(rating_hashes).encode("utf-8")),
        "status": "NO_VERIFIED_CONTROLLING_RATE_SO_REVIEW_ONLY",
        "source_proxies_not_accuracy_evidence": [
            "Shipment date used in place of missing invoice issue date",
            "Bill-reported rated weight not independently established actual weight",
            "Source invoice grand total used as placeholder charge, not rated charge lines",
            "No shipment-specific effective customer tariff/rate authority",
        ],
        "blockers": dict(reasons),
    }


def _key(row: dict, fields: tuple[str, ...]) -> str:
    return "\x1f".join(str(row[k]) for k in fields)


def _payment_scope_key(row: dict) -> str:
    """Supplier is part of remittance identity; identical payment numbers alone are not."""
    return _key(row, ("supplier number", "payment number", "payment date", "payment currency"))


def parse_pennine_csv(raw: bytes, month: str) -> list[dict]:
    data = raw.decode("utf-8-sig", errors="strict")
    reader = csv.reader(io.StringIO(data, newline=""), strict=True)
    required = ("supplier number", "invoice number", "invoice date",
                "invoice amount", "payment number", "payment date",
                "payment currency", "payment status name")
    headings = None
    rows: list[dict] = []
    for row in reader:
        names = [re.sub(r"\s+", " ", v.strip().casefold()) for v in row]
        if headings is None:
            if all(n in names for n in required):
                if any(names.count(name) != 1 for name in required):
                    raise ValueError("AMBIGUOUS_PUBLIC_SOURCE_HEADERS")
                headings = {name: names.index(name) for name in required}
            continue
        if not row or all(not x.strip() for x in row):
            continue
        if max(headings.values()) >= len(row):
            raise ValueError("TRUNCATED_PUBLIC_CSV_INVOICE_RECORD")
        x = {name: row[pos].strip() for name, pos in headings.items()}
        if not x["invoice number"] and not x["payment number"]:
            # Both adapters must fail closed on populated, unidentifiable rows.
            raise ValueError("MISSING_PUBLIC_INVOICE_AND_PAYMENT_ID")
        if not x["supplier number"] or not x["invoice number"]:
            raise ValueError("missing invoice identity in source month")
        for name in ("supplier number", "invoice number"):
            require_canonical_source_identity(
                x[name], raw_value=row[headings[name]],
            )
        require_canonical_source_identity(
            x["payment number"], allow_empty=True,
            raw_value=row[headings["payment number"]],
        )
        x["invoice date"] = iso_date(x["invoice date"])
        x["payment date"] = iso_date(x["payment date"])
        x["invoice_amount_minor"] = minor(x["invoice amount"])
        x["payment currency"] = x["payment currency"].upper()
        if x["payment currency"] != "GBP":
            raise ValueError("unexpected payment currency")
        x["month"] = month
        rows.append(x)
    if headings is None:
        raise ValueError("invoice/payment column headers not found for source month")
    if not rows:
        raise ValueError("month has no valid invoice rows")
    return rows


def verify_public_csv_adapter_parity(
    laboratory_rows: list[dict], publisher_rows: tuple[dict, ...] | list[dict],
) -> int:
    """Check independent parser outputs for exact same-source row multiset.

    Both parsers consume the same public source; agreement is a parser
    consistency test, not a second bank ledger or payment authentication.
    Never include private source identifiers in raised errors or reports.
    """
    if type(laboratory_rows) is not list or type(publisher_rows) not in (list, tuple):
        raise ValueError("PUBLIC_CSV_ADAPTER_PARITY_INVALID")
    fields = ("supplier number", "invoice number", "invoice date",
              "payment number", "payment date", "payment currency",
              "payment status name")

    def row_key(row: dict, amount_field: str) -> tuple:
        try:
            amount = row[amount_field]
            parts = tuple(row[field] for field in fields)
        except (TypeError, KeyError):
            raise ValueError("PUBLIC_CSV_ADAPTER_PARITY_INVALID") from None
        if type(amount) is not int or any(type(value) is not str for value in parts):
            raise ValueError("PUBLIC_CSV_ADAPTER_PARITY_INVALID")
        return parts + (amount,)

    left = Counter(row_key(row, "invoice_amount_minor") for row in laboratory_rows)
    right = Counter(row_key(row, "invoice amount minor") for row in publisher_rows)
    if left != right:
        raise ValueError("PUBLIC_CSV_ADAPTER_PARITY_MISMATCH")
    return len(laboratory_rows)


def benchmark_pennine() -> dict:
    from freight.public_pennine_integration import decode_month as independent_decode_month

    all_rows: list[dict] = []
    source_hashes = {}
    monthly_counts = {}
    parity_records = 0
    for month, url in PENNINE.items():
        raw = fetch_public(url)
        require_frozen_source("pennine", month, raw)
        rows = parse_pennine_csv(raw, month)
        parity_records += verify_public_csv_adapter_parity(
            rows, independent_decode_month(raw, month),
        )
        monthly_counts[month] = len(rows)
        source_hashes[month] = {"url": url, "sha256": digest(raw), "bytes": len(raw)}
        all_rows.extend(rows)
    # An invoice's key is not its payment or release date. Preserve all
    # cross-month disclosures before counting unique invoice economics.
    inv_fields = ("supplier number", "invoice number", "invoice date", "invoice_amount_minor")
    declaration_fields = inv_fields + ("payment number", "payment date", "payment currency")
    by_identity: dict[str, list[dict]] = defaultdict(list)
    by_decl: dict[str, list[dict]] = defaultdict(list)
    supplier_invoice_first: dict[tuple[str, str], dict] = {}
    for row in all_rows:
        supplier_invoice = (row["supplier number"], row["invoice number"])
        if supplier_invoice in supplier_invoice_first:
            require_stable_invoice_economics(
                supplier_invoice_first[supplier_invoice], row,
                amount_field="invoice_amount_minor",
            )
        else:
            supplier_invoice_first[supplier_invoice] = row
        by_identity[_key(row, inv_fields)].append(row)
        by_decl[_key(row, declaration_fields)].append(row)
    for group in by_identity.values():
        for republished in group[1:]:
            require_matching_payment_annotations(group[0], republished)
    unique_rows = [group[0] for group in by_identity.values()]
    disclosed_overlap = sum(len(x) - 1 for x in by_identity.values())
    repeated_declarations = sum(len(x) - 1 for x in by_decl.values())
    cross_month_repeats = sum(
        len(group) - 1 for group in by_identity.values()
        if len({x["month"] for x in group}) > 1
    )
    changed_payment_ids = sum(
        len({(x["payment number"], x["payment date"]) for x in group}) > 1
        for group in by_identity.values()
    )
    invoices: list[ReconTxn] = []
    payment_declarations: dict[str, list[dict]] = defaultdict(list)
    invoice_group: dict[str, str] = {}
    payment_group: dict[str, str] = {}
    for row in unique_rows:
        key = _key(row, inv_fields)
        pay_key = _payment_scope_key(row)
        tid = "inv:" + _safe_sha(key)
        invoice_group[tid] = pay_key
        invoices.append(ReconTxn(
            id=tid, amount=f"{Decimal(row['invoice_amount_minor']) / 100:.2f}",
            date=row["payment date"], currency="GBP", reference=row["payment number"]))
        payment_declarations[pay_key].append(row)
    counterparts = []
    for key, group in payment_declarations.items():
        row = group[0]
        ident = "declared:" + _safe_sha(key)
        payment_group[ident] = key
        amount = sum(x["invoice_amount_minor"] for x in group)
        counterparts.append(ReconTxn(
            id=ident, amount=f"{Decimal(amount) / 100:.2f}",
            date=row["payment date"], currency="GBP", reference=row["payment number"]))
    recon = _recon_result(invoices, counterparts, {**invoice_group, **payment_group})
    payment_status_counts = Counter(
        str(row["payment status name"]).strip().casefold() or "<empty>"
        for row in unique_rows
    )
    supplier_invoice_variants: dict[str, set[str]] = defaultdict(set)
    for row in unique_rows:
        supplier_invoice_key = _key(row, ("supplier number", "invoice number"))
        supplier_invoice_variants[supplier_invoice_key].add(
            _key(row, ("invoice date", "invoice_amount_minor")))
    changed_invoice_amount_or_date = sum(
        len(variants) > 1 for variants in supplier_invoice_variants.values())
    empty_pay_references = sum(not row["payment number"] for row in unique_rows)
    negative_invoice_rows = sum(row["invoice_amount_minor"] < 0 for row in unique_rows)
    zero_invoice_rows = sum(row["invoice_amount_minor"] == 0 for row in unique_rows)
    payment_ref_sizes = Counter(len(group) for group in payment_declarations.values())
    return {
        "data_classification": "GENERAL_ACCOUNTING_ONLY_NOT_FREIGHT",
        "licence": "UK_OPEN_GOVERNMENT_LICENCE",
        "months": list(PENNINE),
        "source_files": source_hashes,
        "monthly_rows": monthly_counts,
        "original_disclosed_rows": len(all_rows),
        "same_source_dual_adapter_parity_verified": True,
        "same_source_dual_adapter_records_cross_checked": parity_records,
        "unique_invoice_economic_identities": len(by_identity),
        "repeated_invoice_disclosures_not_duplicate_payments": disclosed_overlap,
        "republication_payment_annotations_consistent": True,
        "exact_repeated_declarations": repeated_declarations,
        "cross_month_repeated_rows": cross_month_repeats,
        "invoice_identity_with_changed_payment_reference": changed_payment_ids,
        "declared_payment_references": len(payment_declarations),
        "published_payment_status_counts": dict(sorted(payment_status_counts.items())),
        "same_supplier_invoice_with_different_amount_or_date": changed_invoice_amount_or_date,
        "missing_payment_number_rows": empty_pay_references,
        "negative_invoice_amount_rows": negative_invoice_rows,
        "zero_invoice_amount_rows": zero_invoice_rows,
        "payment_reference_group_sizes": dict(sorted(payment_ref_sizes.items())),
        "invoice_total_minor_deduplicated": sum(r["invoice_amount_minor"] for r in unique_rows),
        "payment_declaration_total_minor_derived_from_same_invoices": sum(
            sum(r["invoice_amount_minor"] for r in group)
            for group in payment_declarations.values()
        ),
        "retally_reconciliation_kernel": recon,
        "retally_source_reference_scoped_kernel_replay": reference_scoped_replay(
            invoices, counterparts, invoice_group, payment_group, max_group_size=8),
        "adversarial_source_declared_payment_controls": adversarial_declared_payment_controls(
            invoices, counterparts, invoice_group, payment_group),
        "global_kernel_limit_interpretation":
            "The default unscoped many-to-one first-18-candidate search is not reference-partitioned; unmatched is NOT evidence of unpaid invoices.",
        "row_count_matches_prior_baseline": len(all_rows) == EXPECTED["pennine_disclosed_rows"],
        "unique_count_matches_prior_baseline": len(by_identity) == EXPECTED["pennine_unique_invoices"],
        "independent_bank_clearing_verified": False,
        "economic_false_positive_rate": None,
        "duplicate_payment_claims": 0,
        "recovery_cents": 0,
        "limitations": [
            "Payments are references and status reported in the same publisher CSV, not independently cleared bank transactions.",
            "Many invoices under one payment reference are normal and must not become duplicate-payment allegations.",
            "Cross-month republishing is not an independent second payment.",
            "All monetary totals are source disclosures; they are not RETALLY-recovered dollars.",
        ],
    }




def survey_historical_adjudications() -> dict:
    """Fingerprint actual historical government decisions as reference sources.

    A decision about SOME freight billing does not label a different carrier
    invoice in the original-document test population. Original underlying
    invoice+effective tariff+payment+fully linked adjudication are still
    required to score a specific detection.
    """
    notes = {}
    for case_id, url in HISTORICAL_GAO.items():
        try:
            raw = fetch_public(url)
            notes[case_id] = {
                "source_url": url,
                "source_accessible": True,
                "sha256": digest(raw),
                "source_bytes": len(raw),
                "independently_matched_to_a_test_invoice": False,
                "complete_invoice_rate_payment_adjudication_chain": False,
                "classification": "UNRESOLVED_NOT_AN_ACCURACY_LABEL",
            }
        except (OSError, ValueError) as exc:
            notes[case_id] = {
                "source_url": url,
                "source_accessible": False,
                "reason": type(exc).__name__,
                "independently_matched_to_a_test_invoice": False,
                "complete_invoice_rate_payment_adjudication_chain": False,
                "classification": "SOURCE_UNAVAILABLE_NOT_AN_ACCURACY_LABEL",
            }
    return {
        "government_decision_reference_count": len(notes),
        "source_pages_fetched": sum(x["source_accessible"] for x in notes.values()),
        "full_independent_case_labels_for_test_invoices": 0,
        "real_freight_accuracy_from_these_sources": None,
        "decision_text_arithmetic_controls": historical_reference_money_controls(),
        "curated_official_decision_challenge_examples": {
            key: {"official_source": HISTORICAL_GAO[key], **value, "is_label_for_test_invoice": False}
            for key, value in HISTORICAL_REFERENCE_NOTES.items()
        },
        "references": notes,
    }

def blind_freight_assessment(freight: dict) -> dict:
    from freight.rate_authority import AuthorityBook
    from freight.rating_engine import REVIEW_REQUIRED

    # Lock decisions before reference comparison: no approved controlling
    # customer rates, bank settlements or independently complete truth labels.
    pred = {
        kind: {
            "eligible_independently_labeled_cases": 0,
            "automatic_positive_decisions": 0,
            "human_review_unknown": info["distinct_invoice_face_ids"],
            "truth_unsealed": False,
        }
        for kind, info in freight.items()
    }
    # GAO decisions can be useful research references but a narrative GAO
    # disposition is not the four-source linked invoice/rate/paid/adjudicated
    # truth package required to score RETALLY freight error detection.
    return {
        "protocol": "freight/AUDIT_ACCEPTANCE_PROTOCOL_V2.md",
        "blinding_protocol_status": "NOT_EXECUTED_INDEPENDENT_TRUTH_AND_REVIEWERS_ABSENT",
        "predictions_frozen_before_truth": False,
        "independent_blind_truth_adjudication_completed": False,
        "frozen_unscored_case_catalog_sha256": digest(json.dumps(
            sorted((kind, info["sha256"], info["source_face_catalog_sha256"],
                    info["distinct_invoice_face_ids"]) for kind, info in freight.items()),
            separators=(",", ":"), ensure_ascii=True).encode()),
        "model_output_evaluated_on_truth_cases": 0,
        "prediction_summary": pred,
        "reference_cases": "HISTORICAL_GAO_DECISIONS_REFERENCE_ONLY_WITHOUT_LINKED_INVOICE_RATE_AND_PAYMENT",
        "label_policy": "POSITIVE_OR_NEGATIVE_ONLY_WHEN_FULLY_INDEPENDENT_EVIDENCE_EXISTS",
        "total_eligible_scored": 0,
        "true_positive": 0,
        "false_positive": 0,
        "true_negative": 0,
        "false_negative": 0,
        "precision": None,
        "recall": None,
        "specificity": None,
        "freight_detection_accuracy": None,
        "unknown_cases_preserved": sum(x["distinct_invoice_face_ids"] for x in freight.values()),
        "state": "INSUFFICIENT_EVIDENCE_NOT_A_PASS_OR_A_FAILURE",
        "validated_recovery_cents": 0,
    }


def run() -> dict:
    freight = benchmark_freight()
    accounting = benchmark_pennine()
    blind = blind_freight_assessment(freight)
    historical = survey_historical_adjudications()
    report = {
        "schema_version": 1,
        "laboratory": "RETALLY_REAL_DOCUMENT_RESEARCH_LAB",
        "run_date_utc": datetime.now(timezone.utc).isoformat(),
        "isolation": "EPHEMERAL_GITHUB_ACTIONS_NO_RAW_DOCUMENT_ARTIFACTS",
        "production_release_approved": False,
        "commercial_reuse_validated": False,
        "freight_original_document_benchmark": freight,
        "general_accounting_invoice_payment_reference_benchmark": accounting,
        "blinded_freight_error_evaluation": blind,
        "historical_adjudication_reference_survey": historical,
    }
    assert blind["precision"] is None and blind["freight_detection_accuracy"] is None
    assert all(info["validated_overcharge_cents"] == 0 for info in freight.values())
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    report = run()
    raw = json.dumps(report, indent=2, sort_keys=True) + "\n"
    Path(args.output).write_text(raw, encoding="utf-8")
    # Public PR logs contain aggregate metrics and content digests only.
    print("===RETALLY_LAB_REPORT_BEGIN===")
    print(raw)
    print("===RETALLY_LAB_REPORT_END===")


if __name__ == "__main__":
    main()
