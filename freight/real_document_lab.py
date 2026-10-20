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
from urllib.request import Request, urlopen

from freight.ingestion_gateway import IngressEnvelope, ingest_bytes
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
MONEY_RE = re.compile(r"^-?\d+(?:\.\d{1,2})?$")


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


def fetch_public(url: str) -> bytes:
    """Fixed allowlist, bounded reads; never accept redirects to new hosts."""
    if urlparse(url).hostname not in ALLOW_HOSTS:
        raise ValueError("unapproved source host")
    request = Request(url, headers={"User-Agent": "RETALLY-Research-Document-QA/1.0"})
    with urlopen(request, timeout=45) as response:
        if urlparse(response.geturl()).hostname not in ALLOW_HOSTS:
            raise ValueError("source redirect changed host")
        data = response.read(LIMIT + 1)
    if not data or len(data) > LIMIT:
        raise ValueError("source empty or over 35 MB")
    return data


def minor(raw: str) -> int:
    """Normalize a CSV presentation amount, then use RETALLY's exact parser."""
    value = raw.strip().replace(",", "").replace("£", "").replace("$", "").strip()
    if value.startswith("(") and value.endswith(")"):
        value = "-" + value[1:-1]
    if not MONEY_RE.fullmatch(value):
        raise ValueError("invalid decimal money")
    return parse_amount_to_minor(value, 2)


def iso_date(raw: str, *, formats: tuple[str, ...] = ("%d/%m/%Y", "%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y")) -> str:
    for fmt in formats:
        try:
            return datetime.strptime(raw.strip(), fmt).date().isoformat()
        except ValueError:
            pass
    raise ValueError("unparseable source date")


def pdf_texts(raw: bytes) -> list[str]:
    # PyMuPDF is only used to read original PDF text in the ephemeral runner.
    import pymupdf

    if not raw.startswith(b"%PDF-"):
        raise ValueError("non-PDF supplied")
    doc = pymupdf.open(stream=raw, filetype="pdf")
    try:
        return [page.get_text("text", sort=False) for page in doc]
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


def extract_faces(issuer: str, texts: list[str]) -> list[InvoiceFace]:
    selected = []
    for index, text in enumerate(texts):
        if issuer == "globaltranz" and not 4 <= index + 1 <= 114:
            continue
        result = (_global_page(text, index + 1) if issuer == "globaltranz"
                  else _arcbest_page(text, index + 1))
        if result:
            selected.append(result)
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
    by_id = {f.number: f for f in faces}
    checks = []
    for number, (page, cents) in anchors.items():
        face = by_id.get(number)
        checks.append(bool(face and face.page == page and face.cents == cents))
    return {"checks": len(checks), "passed": sum(checks), "failed": len(checks) - sum(checks)}


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
    declarations. Groups above the explicit bound abstain.
    """
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
            continue
        if len(internal) > max_group_size:
            limit_groups += 1
            limit_invoices += len(internal)
            grouped_unmatched += len(internal)
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
    return report

def benchmark_freight() -> dict:
    results: dict = {}
    for issuer, url in DOCUMENTS.items():
        raw = fetch_public(url)
        native = ingest_bytes(IngressEnvelope(
            ingress_id="test:" + issuer, buyer_id="BENCHMARK_ONLY",
            business_unit="ISOLATED_NO_CUSTOMER", transport="BATCH",
            filename=issuer + ".pdf",
        ), raw)
        texts = pdf_texts(raw)
        faces = extract_faces(issuer, texts)
        anchor = check_anchors(faces,
            GLOBAL_FACE_ANCHORS if issuer == "globaltranz" else ARCBEST_FACE_ANCHORS)
        unique = {f.number: f for f in faces}
        out = {
            "source_url": url,
            "sha256": digest(raw),
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
            parents = {re.sub(r"\s+A$", "", f.number) for f in unique.values()}
            out["invoice_families_adjustments_not_silently_collapsed"] = len(parents)
        else:
            # Source face amounts are not a bill-to-bank payment comparison.
            out["source_invoice_mode_ltl_count"] = sum(f.mode == "LTL" for f in unique.values())
            out["source_invoice_mode_tl_count"] = sum(f.mode == "TL" for f in unique.values())
            out["retally_rating_engine"] = _rating_probe(faces, texts, digest(raw))
        results[issuer] = out
    return results


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
            observed_at="2026-10-19T00:00:00.000000Z",
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


def parse_pennine_csv(raw: bytes, month: str) -> list[dict]:
    data = raw.decode("utf-8-sig", errors="replace")
    reader = csv.reader(io.StringIO(data, newline=""))
    required = ("supplier number", "invoice number", "invoice date",
                "invoice amount", "payment number", "payment date",
                "payment currency", "payment status name")
    headings = None
    rows: list[dict] = []
    for row in reader:
        names = [re.sub(r"\s+", " ", v.strip().casefold()) for v in row]
        if headings is None:
            if all(n in names for n in required):
                headings = {name: names.index(name) for name in required}
            continue
        if not row or all(not x.strip() for x in row):
            continue
        if max(headings.values()) >= len(row):
            continue
        x = {name: row[pos].strip() for name, pos in headings.items()}
        if not x["invoice number"] and not x["payment number"]:
            continue
        if not x["supplier number"] or not x["invoice number"]:
            raise ValueError("missing invoice identity in source month")
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


def benchmark_pennine() -> dict:
    all_rows: list[dict] = []
    source_hashes = {}
    monthly_counts = {}
    for month, url in PENNINE.items():
        raw = fetch_public(url)
        rows = parse_pennine_csv(raw, month)
        monthly_counts[month] = len(rows)
        source_hashes[month] = {"url": url, "sha256": digest(raw), "bytes": len(raw)}
        all_rows.extend(rows)
    # An invoice's key is not its payment or release date. Preserve all
    # cross-month disclosures before counting unique invoice economics.
    inv_fields = ("supplier number", "invoice number", "invoice date", "invoice_amount_minor")
    declaration_fields = inv_fields + ("payment number", "payment date", "payment currency")
    by_identity: dict[str, list[dict]] = defaultdict(list)
    by_decl: dict[str, list[dict]] = defaultdict(list)
    for row in all_rows:
        by_identity[_key(row, inv_fields)].append(row)
        by_decl[_key(row, declaration_fields)].append(row)
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
        pay_key = _key(row, ("payment number", "payment date", "payment currency"))
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
    payment_ref_sizes = Counter(len(group) for group in payment_declarations.values())
    return {
        "data_classification": "GENERAL_ACCOUNTING_ONLY_NOT_FREIGHT",
        "licence": "UK_OPEN_GOVERNMENT_LICENCE",
        "months": list(PENNINE),
        "source_files": source_hashes,
        "monthly_rows": monthly_counts,
        "original_disclosed_rows": len(all_rows),
        "unique_invoice_economic_identities": len(by_identity),
        "repeated_invoice_disclosures_not_duplicate_payments": disclosed_overlap,
        "exact_repeated_declarations": repeated_declarations,
        "cross_month_repeated_rows": cross_month_repeats,
        "invoice_identity_with_changed_payment_reference": changed_payment_ids,
        "declared_payment_references": len(payment_declarations),
        "payment_reference_group_sizes": dict(sorted(payment_ref_sizes.items())),
        "invoice_total_minor_deduplicated": sum(r["invoice_amount_minor"] for r in unique_rows),
        "payment_declaration_total_minor_derived_from_same_invoices": sum(
            sum(r["invoice_amount_minor"] for r in group)
            for group in payment_declarations.values()
        ),
        "retally_reconciliation_kernel": recon,
        "retally_source_reference_scoped_kernel_replay": reference_scoped_replay(
            invoices, counterparts, invoice_group, payment_group, max_group_size=8),
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
        "predictions_frozen_before_truth": True,
        "independent_blind_truth_adjudication_completed": False,
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
