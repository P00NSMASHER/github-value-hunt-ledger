"""Read-only, ephemeral REAL source checks using RETALLY's installed engines.

Replays five publisher-licensed Pennine CSVs and two public original-document PDFs.
No invoice rows/PDF bytes/customer names/payment references persist in reports.
This is a research diagnostic, NEVER freight error adjudication or bank clearance.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
from collections import Counter
from decimal import Decimal
from typing import Mapping

from freight.ingestion_gateway import IngressEnvelope, ingest_bytes
from freight.research.authorized_original_case_fetch import fetch_pinned_pdf, AcquisitionHold
from freight.research.public_invoice_payment_validation import (
    SOURCE_URLS, REQUIRED, SourceHold, date_value, fetch_official_csv,
    money_cents, profile_csv,
)
from recoveryworks.reconciliation_kernel import (
    ReconTxn, ReconConfig, ManyToOneConfig, reconcile, parse_amount_to_minor,
)

PINNED_SHA256 = {
    "2026-04": "314cd0c021f137b43b94e81bb93f26aece5b3b0a021e99c42d43546a640c3d90",
    "2026-05": "5957ead9c23d57039e267dc18076c7b8d711a14b97cbea6d9a9ff0629aeb5028",
    "2026-06": "318aeeedbf55d05bcffce5076ac893a84bdb6ebe5e7c851bb3f3c45dbbdea8fc",
    "2026-07": "ecb986bd0e33cf402f7cb86ff68bc91368d18a5dfc39410e4e2019c045c3de15",
    "2026-08": "4153ccbbbe27307afddba1d6651bfd9db8a774cc84e4fd23d62b3a2d1059d796",
}
FREIGHT_SOURCE_KEYS = (
    "globaltranz-original-broker-bills",
    "arcbest-underlying-carrier-invoices",
)
# Preselected source-text controls, independently noted before this run.
# These are NOT adjudicated overcharge labels or runtime training examples.
ORIGINAL_PDF_LOCATABILITY_CONTROLS = {
    FREIGHT_SOURCE_KEYS[0]: (
        (4, "30794056", "341.08"),
        (5, "29937996", "201.40"),
        (32, "30984884 A", "29.88"),
        (39, "30988238", "246.61"),
        (7, "31048751", "173.90"),
    ),
    FREIGHT_SOURCE_KEYS[1]: (
        (4, "044177205", "314.77"),
        (10, "051886768", "244.77"),
        (16, "051894063", "2123.79"),
        (23, "086855061", "2132.83"),
        (38, "196876953", "612.79"),
        (43, "279818407", "606.00"),
        (51, "352112867", "351.78"),
        (57, "352176075", "252.38"),
        (61, "436380706", "2950.00"),
        (66, "436430967", "3200.00"),
    ),
}
# Decisions contain disputed/confirmed legal dispositions, not linked invoice
# + authority + shipment + payment + two independent blinded reviewer labels.
HISTORICAL_GAO_CASES = (
    "b-143246", "b-148465", "b-161664", "b-199805-0",
    "b-223311-0", "b-221594-0", "b-195862", "b-221705",
)
PROOF_KEYS = ("original_invoice_verified", "controlling_rate_verified",
              "shipment_evidence_verified", "independent_payment_verified",
              "independent_adjudication_verified", "blinding_verified")


def _table_rows(raw: bytes) -> list[dict[str, str]]:
    """Decode official publisher header including August's two preamble lines."""
    text = raw.decode("utf-8-sig", errors="strict")
    reader = csv.reader(io.StringIO(text, newline=""))
    header = None
    for i, candidate in enumerate(reader):
        names = [" ".join(x.split()) for x in candidate]
        if i >= 6:
            break
        if set(REQUIRED).issubset(names):
            header = names
            break
    if header is None or len(set(header)) != len(header):
        raise SourceHold("PUBLISHER_HEADER_DRIFT")
    parsed = []
    for cells in reader:
        if not cells or not any(x.strip() for x in cells):
            continue
        if len(cells) != len(header):
            raise SourceHold("PUBLISHER_ROW_SHAPE_DRIFT")
        parsed.append(dict(zip(header, (x.strip() for x in cells))))
    return parsed


def _pennine_population(fetcher=fetch_official_csv, *, pinned=True):
    """Deduplicate economic invoice identity; preserve contradicting reposts."""
    seen = {}
    repetitions = 0
    contradictions = 0
    source_count = 0
    snapshots = {}
    profile_seen, profile_history = set(), {}
    for period, url in SOURCE_URLS.items():
        raw = fetcher(url)
        digest = hashlib.sha256(raw).hexdigest()
        if pinned and digest != PINNED_SHA256[period]:
            raise SourceHold("PINNED_PUBLIC_COHORT_CHANGED:" + period)
        profile = profile_csv(raw, source_url=url, cross_period_keys=profile_seen,
                              cross_period_history=profile_history, source_month=period)
        snapshots[period] = {
            "source_sha256": digest,
            "published_rows": profile["source_row_count"],
            "complete_paid_reference_rows": profile["complete_paid_reference_rows"],
            "cross_period_duplicate_rows": profile["cross_period_duplicate_invoice_rows"],
            "reported_amount_minor": profile["total_reported_invoice_amount_gbp_cents_for_complete_rows"],
        }
        source_count += profile["source_row_count"]
        for row in _table_rows(raw):
            if any(not row.get(x) for x in REQUIRED):
                raise SourceHold("MISSING_PUBLISHER_FIELD")
            if row["Payment Status Name"].casefold() != "fully paid" or row["Payment Currency"].upper() != "GBP":
                raise SourceHold("PINNED_COHORT_UNEXPECTED_STATUS_OR_CURRENCY")
            amount = money_cents(row["Invoice Amount"])
            invoice_date = date_value(row["Invoice Date"]).isoformat()
            payment_date = date_value(row["Payment Date"]).isoformat()
            if payment_date < invoice_date:
                raise SourceHold("PAYMENT_BEFORE_INVOICE")
            identity = (row["Supplier Number"].upper(), row["Invoice Number"].upper(), invoice_date)
            financial = (amount, row["Payment Number"], payment_date)
            if identity in seen:
                repetitions += 1
                if seen[identity]["financial"] != financial:
                    contradictions += 1
                continue
            seen[identity] = {
                "financial": financial, "invoice_ref": row["Invoice Number"],
                "payment_ref": row["Payment Number"], "invoice_date": invoice_date,
                "payment_date": payment_date, "raw_amount": row["Invoice Amount"],
                "amount_minor": amount,
            }
    if contradictions:
        raise SourceHold("CONFLICTING_REPUBLISHED_INVOICES:" + str(contradictions))
    if pinned and (source_count, len(seen), repetitions) != (314, 273, 41):
        raise SourceHold("PINNED_273_POPULATION_MISMATCH")
    return list(seen.values()), {
        "published_rows": source_count, "unique_invoices": len(seen),
        "repeated_publication_rows": repetitions,
        "snapshots": snapshots,
        "raw_rows_persisted": False,
    }


def _summary_matches(result, count: int) -> dict:
    correct = wrong = matched_pairs = 0
    for group in result.matches:
        # Economic join truth here is *only the publisher's same-row association*.
        if len(group.internal_ids) != 1 or len(group.settlement_ids) != 1:
            wrong += 1
            continue
        matched_pairs += 1
        if group.internal_ids[0].replace("I-", "") == group.settlement_ids[0].replace("P-", ""):
            correct += 1
        else:
            wrong += 1
    return {
        "pairs_matched": matched_pairs,
        "same_publisher_row_links": correct,
        "cross_invoice_misjoins": wrong,
        "unmatched_invoices": len(result.unmatched_internal),
        "unmatched_payment_annotations": len(result.unmatched_settlement),
        "matched_fraction": round(matched_pairs / count, 6) if count else None,
        "matched_against_independent_bank": False,
        "recovery_confirmed_minor": 0,
    }


def benchmark_accounting(fetcher=fetch_official_csv, *, pinned=True) -> dict:
    rows, population = _pennine_population(fetcher, pinned=pinned)
    internal, payments, aligned_internal, aligned_payments = [], [], [], []
    amount_equivalence = 0
    payment_ids = Counter()
    unique_sum = 0
    for i, row in enumerate(rows):
        # Invoke the actual RecoveryWorks currency/amount primitive on PUBLIC raw
        # amounts (after removing display separators) and compare independent cents.
        cleaned = row["raw_amount"].replace("£", "").replace(",", "").strip()
        kernel_minor = parse_amount_to_minor(cleaned, 2)
        amount_equivalence += kernel_minor == row["amount_minor"]
        unique_sum += row["amount_minor"]
        ident = "K" + str(i)
        payment_ids[row["payment_ref"]] += 1
        internal.append(ReconTxn("I-" + ident, cleaned, row["invoice_date"], "GBP",
                                 reference=row["invoice_ref"]))
        payments.append(ReconTxn("P-" + ident, cleaned, row["payment_date"], "GBP",
                                 reference=row["payment_ref"]))
        # Identity-aligned sanity control; settlement is STILL the same ledger row,
        # not an independent statement or bank export.
        aligned_internal.append(ReconTxn("I-" + ident, cleaned, row["payment_date"],
                                         "GBP", reference=ident))
        aligned_payments.append(ReconTxn("P-" + ident, cleaned, row["payment_date"],
                                         "GBP", reference=ident))
    base = dict(amount_tolerance_bps=0, many_to_one=ManyToOneConfig(enabled=False))
    default_window = reconcile(internal, payments, ReconConfig(date_window_days=3, **base))
    broad_window = reconcile(internal, payments, ReconConfig(date_window_days=365, **base))
    identity_control = reconcile(aligned_internal, aligned_payments,
                                 ReconConfig(date_window_days=3, **base))
    return {
        "state": "REAL_PUBLISHER_ACCOUNTING_ANNOTATION_KERNEL_REPLAY",
        "source": "Pennine Care NHS FT OGL v3 April-August 2026",
        "population": population,
        "unique_reported_invoice_total_gbp_minor": unique_sum,
        "actual_kernel_money_parse_equal": amount_equivalence,
        "actual_kernel_money_parse_checked": len(rows),
        "shared_payment_references_not_duplicate_payment_proof":
            sum(n > 1 for n in payment_ids.values()),
        "default_3_day_window": _summary_matches(default_window, len(rows)),
        "broad_365_day_window": _summary_matches(broad_window, len(rows)),
        "source_identity_propagated_control": _summary_matches(identity_control, len(rows)),
        "accounting_false_positive_definition": "cross-invoice join contradicting publisher same-row association",
        "payment_annotations_are_not_independent_bank_evidence": True,
        "freight_detection_accuracy": None, "verified_customer_recovery_minor": 0,
    }


def _extract_text_invoice(text: str) -> tuple[str | None, int | None]:
    """Conservative EXPLORATORY textual fields, never a production PDF extractor."""
    flat = " ".join(text.split())
    invoice = re.search(
        r"(?i)\b(?:invoice|bill|pro)\s*(?:number|no\.?|#)\s*[:#]?\s*([0-9]{8,9}(?:\s+[A-Z])?)\b",
        flat,
    )
    amount = re.search(
        r"(?i)\b(?:total\s*(?:amount|charges|due)|amount\s+due|"
        r"invoice\s+total|net\s+charges)\s*[:$ ]*"
        r"(?:USD\s*)?\$?\s*([0-9][0-9,]*\.[0-9]{2})\b",
        flat,
    )
    cents = None
    if amount:
        cents = parse_amount_to_minor(amount.group(1).replace(",", ""), 2)
    return (invoice.group(1).strip().upper() if invoice else None, cents)


def _is_text_amount(page: str, amount: str) -> bool:
    digits = amount.split(".")
    major = int(digits[0])
    variants = (str(major), f"{major:,}")
    return any(re.search(r"(?<![0-9])" + re.escape(x + "." + digits[1]) + r"(?![0-9])", page)
               for x in variants)


def benchmark_freight(fetcher=fetch_pinned_pdf) -> dict:
    from pypdf import PdfReader
    entries = []
    for source in FREIGHT_SOURCE_KEYS:
        result = {"source_id": source, "status": "SOURCE_HOLD"}
        try:
            payload = fetcher(source)
            ingress = ingest_bytes(IngressEnvelope(
                ingress_id="LAB-" + source, buyer_id="NONCUSTOMER_RESEARCH",
                business_unit="ISOLATED", transport="BATCH", filename=source + ".pdf",
            ), payload)
            result.update(
                sha256=hashlib.sha256(payload).hexdigest(),
                source_bytes=len(payload),
                actual_gateway_status=ingress.status,
                actual_gateway_route=ingress.route,
                source_text_uses_experimental_adapter=True,
            )
            if ingress.status != "ACCEPT" or ingress.route != "DOCUMENT_EXTRACTION_REQUIRED":
                result["status"] = "GATEWAY_REJECTED_OR_CHANGED"
                entries.append(result)
                continue
            reader = PdfReader(io.BytesIO(payload), strict=False)
            if reader.is_encrypted or len(reader.pages) > 150:
                result["status"] = "ENCRYPTED_OR_TOO_MANY_PAGES"
                entries.append(result)
                continue
            controls = ORIGINAL_PDF_LOCATABILITY_CONTROLS[source]
            verified_page_count = 0
            invoice_found = amount_found = both_found = extracted_identifier_matches = 0
            extracted_amount_matches = 0
            for page_number, invoice_id, expected_amount in controls:
                page = reader.pages[page_number - 1].extract_text() or ""
                tokens = re.findall(r"(?<!\w)[0-9]{8,9}(?:\s+[A-Z])?(?!\w)", page.upper())
                ident_present = re.sub(r"\s+", "", invoice_id.upper()) in {
                    re.sub(r"\s+", "", v) for v in tokens
                }
                amount_present = _is_text_amount(page, expected_amount)
                invoice_found += ident_present
                amount_found += amount_present
                both_found += ident_present and amount_present
                identified, cents = _extract_text_invoice(page)
                extracted_identifier_matches += (
                    identified is not None and
                    re.sub(r"\s+", "", identified) == re.sub(r"\s+", "", invoice_id)
                )
                extracted_amount_matches += (
                    cents is not None and cents == parse_amount_to_minor(expected_amount)
                )
                verified_page_count += 1
            result.update(
                status="TEXT_EVALUATED_RESEARCH_ONLY",
                original_pdf_pages=len(reader.pages),
                preselected_invoice_pages_checked=verified_page_count,
                number_text_present_on_expected_pages=invoice_found,
                amount_text_present_on_expected_pages=amount_found,
                both_text_tokens_present_on_expected_pages=both_found,
                exploratory_labeled_identifier_extraction_matches=extracted_identifier_matches,
                exploratory_total_field_extraction_matches=extracted_amount_matches,
                production_pdf_field_extractor_implemented=False,
                # Never invent contract authority, service date, class/weight or
                # shipment geography just to force a freight monetary answer.
                eligible_for_freight_rating=0,
                actual_rating_engine_invocations=0,
                rates_verified=0,
                freight_overcharge_labels_verified=0,
                actual_detected_freight_accuracy=None,
            )
        except (AcquisitionHold, ValueError, IndexError, OSError) as exc:
            result["hold_code"] = type(exc).__name__
        except Exception:
            result["hold_code"] = "PDF_PARSE_OR_SOURCE_ERROR"
        entries.append(result)
    return {
        "state": "ACTUAL_PDF_INGESTION_WITH_RESEARCH_TEXT_EXTRACTION",
        "documents": entries,
        "raw_invoice_documents_logged_or_committed": False,
        "freight_rate_calculation_eligible_cases": 0,
        "freight_detection_accuracy": None,
        "production_extractor_gap": "PDF accepted but routed to DOCUMENT_EXTRACTION_REQUIRED",
    }


def blind_score(predictions: Mapping[str, str], truth: Mapping[str, dict]) -> dict:
    """Calculate accuracy ONLY for independently complete unsealed cases.

    Must be invoked after independent frozen manifest/hash workflows outside
    this adapter. UNRESOLVED is never coerced to NEGATIVE.
    """
    tp = tn = fp = fn = abstained = unknown = 0
    for case_id, row in truth.items():
        label = row.get("label", "UNRESOLVED")
        complete = all(row.get(key) is True for key in PROOF_KEYS)
        if label not in ("POSITIVE", "NEGATIVE") or not complete:
            unknown += 1
            continue
        output = predictions.get(case_id, "REVIEW_REQUIRED")
        if output not in ("POSITIVE", "NEGATIVE"):
            abstained += 1
        elif label == "POSITIVE" and output == "POSITIVE":
            tp += 1
        elif label == "NEGATIVE" and output == "NEGATIVE":
            tn += 1
        elif output == "POSITIVE":
            fp += 1
        else:
            fn += 1
    eligible = tp + tn + fp + fn + abstained
    return {
        "state": "SCORABLE_ONLY_WITH_COMPLETE_INDEPENDENT_BLIND_LABELS" if eligible else
                 "INSUFFICIENT_INDEPENDENT_FREIGHT_LABELS",
        "eligible_labeled_cases": eligible,
        "unknown_cases_excluded": unknown,
        "abstentions": abstained,
        "tp": tp, "tn": tn, "fp": fp, "fn": fn,
        "coverage": ((eligible - abstained) / eligible) if eligible else None,
        "precision": tp / (tp + fp) if tp + fp else None,
        "recall": tp / (tp + fn) if tp + fn else None,
        "specificity": tn / (tn + fp) if tn + fp else None,
        "accuracy": (tp + tn) / (tp + tn + fp + fn) if tp + tn + fp + fn else None,
    }


def historical_references() -> dict:
    records = {case: {"label": "UNRESOLVED", "independent_adjudication_verified": True}
               for case in HISTORICAL_GAO_CASES}
    output = blind_score({}, records)
    output["reference_case_count"] = len(HISTORICAL_GAO_CASES)
    output["historical_cases_are_reference_only_not_linked_original_invoice_sets"] = True
    return output


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--live", action="store_true")
    args = p.parse_args()
    if not args.live:
        raise SystemExit("Real source tests require explicit --live; no synthetic pass substitute")
    result = {"schema_version": 1, "scope": "RESEARCH_ONLY_NO_CUSTOMER_VALIDATION",
              "accounting": None, "original_freight_documents": None,
              "blind_freight": historical_references()}
    try:
        result["accounting"] = benchmark_accounting()
    except (SourceHold, ValueError) as exc:
        result["accounting"] = {"state": "SOURCE_OR_KERNEL_HOLD", "reason": str(exc)}
    result["original_freight_documents"] = benchmark_freight()
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["accounting"]["state"] == "SOURCE_OR_KERNEL_HOLD":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
