"""Read-only original-freight evidence-chain readiness: current federal GSA reference.

The federal GSA transportation-audit checklist provides useful evidence types,
but 41 CFR 102-118 is NOT asserted to govern private RETALLY customers.
This module evaluates only the original-public-PDF lab's *held* evidence.
It does not scrape, contact customers, store invoice IDs, infer contract rates,
adjudicate private claims, or turn invoice arithmetic into recovered cash.
"""
from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timezone
from pathlib import Path

from freight.real_document_lab import FROZEN_DOCUMENT_SHA256
from freight.unified_research_lab import ResearchError, digest

SCOPE = "REAL_ORIGINAL_FREIGHT_PDF_EVIDENCE_CHAIN_READINESS_NOT_RECOVERY_TRUTH"
FEDERAL_REFERENCE_URL = (
    "https://www.gsa.gov/policy-regulations/policy/transportation-management-policy/"
    "transportation-handbook-freight-household-goods-and-small-parcel"
)
FEDERAL_AUDIT_URL = (
    "https://www.gsa.gov/policy-regulations/policy/transportation-management-policy/"
    "transportation-invoice-audit"
)
GUIDANCE_APPLICABILITY = "FEDERAL_GSA_REFERENCE_ONLY_NOT_PRIVATE_CUSTOMER_LEGAL_AUTHORITY"
SOURCE_FACE_CATALOG_HASH = {
    # Verified at original-document nightly acceptance on October 24, 2026.
    "globaltranz": "31dcbe162729ddf3b90027519dc9c5861ca0d892dc5e9a52cbbb0907a2ee3ef8",
    "arcbest": "0ad7c4a290d23beea68f9d4c18757b5da8dd96c884dfe9a917593f130c841eb7",
}
SIGNED_RECORD_CATALOG_HASH = (
    "ecf6f9529909d5f1a3f031a0683c1eba4ca9ccabf9feaa6c445b208c468ef787"
)
# Source-only categories observed on the frozen original 74-page ArcBest PDF
# in isolated real-document run 40140512216. Identifiers themselves excluded.
ARCBEST_PRINTED_REFERENCE_DIGEST = (
    "4915cce3465a44f7ea8c9bf0c50671f4766589ce9725e328875b34201c6a2af0"
)
ARCBEST_PRINTED_TARIFF_CLASSES = {
    "NO_PRINTED_TARIFF_REFERENCE": 2,
    "PRINTED_ABF_ACCOUNT_REFERENCE_ONLY": 6,
    "PRINTED_VOLUME_QUOTE_MARKER_ONLY": 2,
}
ARCBEST_PRINTED_BOL_HEADER_CLASSES = {
    "BOL_HEADER_IDENTIFIER_PRINTED_ONLY": 2,
    "BOL_HEADER_PLACEHOLDER_ONLY": 8,
}
EXPECTED_FACE_COUNTS = {"globaltranz": 100, "arcbest": 10}
EXPECTED_NET_COVERAGE = {"globaltranz": 100, "arcbest": 0}
MISSING_CHAIN_STAGES = (
    "SHIPMENT_SPECIFIC_EFFECTIVE_CONTRACT_OR_TENDER",
    "SEPARATELY_CUSTODIED_ORIGINAL_BOL_SHIPMENT_LINK",
    "INDEPENDENT_DELIVERY_OR_SERVICE_CONFIRMATION",
    "INDEPENDENT_ACTUAL_WEIGHT_OR_CLASS_VERIFICATION",
    "CLEARED_PAYMENT_AND_CREDIT_LEDGER",
    "INDEPENDENTLY_ADJUDICATED_INVOICE_RATE_OUTCOME",
)
LIMITATIONS = (
    "GSA guidance addresses federal transportation audit; private-party contract applicability is NOT established.",
    "Two exact source-PDF byte hashes and 110 invoice faces are source arithmetic, NOT rate accuracy.",
    "Source invoice-to-open-statement matching does NOT establish a cleared bank payment.",
    "GlobalTranz v2 adjustments encode signed invoice components with provisional lab DISCOUNT semantics.",
    "ArcBest printed freight-bill weights, if present, are not independent certified shipment weights.",
    "ArcBest invoice-printed tariff/VPQ codes and BOL headers do not prove an original accepted quote, contract rate or separately held original BOL.",
    "Lab canonical shipment location, carrier, freight mode and weight placeholders are SYNTHETIC.",
    "A missing document in this lab is not proof that a shipper or carrier cannot supply it elsewhere.",
    "No customer contacts, commercial input rights, production extraction, tariffs, actual claims or recovered cash.",
)
RECEIPT_KEYS = frozenset({
    "schema_version", "scope", "as_of_utc_date", "federal_guidance_scope",
    "guidance_reference_urls", "original_pdf_sources_with_verified_byte_hashes",
    "original_invoice_faces_observed", "face_total_amounts_extracted",
    "original_net_amounts_reconciled_to_signed_components",
    "globaltranz_source_adjustment_v2_cases", "globaltranz_positive_only_v1_cases",
    "globaltranz_open_statement_identity_and_original_amount_matches",
    "arcbest_source_proxy_rating_review_count",
    "arcbest_source_printed_tariff_reference_classes",
    "arcbest_source_printed_bol_header_classes",
    "arcbest_source_printed_category_sha256",
    "arcbest_independently_verified_rate_and_original_bol_documents",
    "source_original_sha256", "original_invoice_catalog_sha256",
    "source_bound_canonical_signed_catalog_sha256",
    "independent_evidence_chain_stages", "missing_chain_evidence_from_current_lab",
    "eligible_independently_scored_customer_invoices", "accuracy", "recall",
    "verified_retally_recovered_cash_cents", "commercial_customer_engine_input_approved",
    "modern_rate_authority_proven", "production_engine_modified",
    "external_customer_contact_actions", "readiness",
    "limitations", "receipt_sha256",
})


def _mapping(x: object, field: str) -> dict:
    if type(x) is not dict:
        raise ResearchError("FREIGHT_EVIDENCE_CHAIN_" + field + "_INVALID")
    return x


def _count(x: object, field: str, target: int | None = None) -> int:
    if type(x) is not int or x < 0 or x > 1_000_000:
        raise ResearchError("FREIGHT_EVIDENCE_CHAIN_" + field + "_INVALID")
    if target is not None and x != target:
        raise ResearchError("FREIGHT_EVIDENCE_CHAIN_" + field + "_DRIFT")
    return x


def _is_false(x: object, field: str) -> None:
    if x is not False:
        raise ResearchError("FREIGHT_EVIDENCE_CHAIN_" + field + "_MUST_REMAIN_FALSE")


def _is_true(x: object, field: str) -> None:
    if x is not True:
        raise ResearchError("FREIGHT_EVIDENCE_CHAIN_" + field + "_MUST_REMAIN_TRUE")


def make_receipt(report: dict, *, as_of: date) -> dict:
    if type(as_of) is not date or as_of > datetime.now(timezone.utc).date():
        raise ResearchError("FREIGHT_EVIDENCE_CHAIN_DATE_INVALID")
    doc = _mapping(report, "REPORT")
    if doc.get("schema_version") != 1 or doc.get("laboratory") != "RETALLY_REAL_DOCUMENT_RESEARCH_LAB":
        raise ResearchError("FREIGHT_EVIDENCE_CHAIN_REPORT_IDENTITY_MISMATCH")
    _is_false(doc.get("production_release_approved"), "PRODUCTION_RELEASE")
    _is_false(doc.get("commercial_reuse_validated"), "COMMERCIAL_REUSE")

    source = _mapping(doc.get("freight_original_document_benchmark"), "FREIGHT_SOURCES")
    if set(source) != set(EXPECTED_FACE_COUNTS):
        raise ResearchError("FREIGHT_EVIDENCE_CHAIN_SOURCE_POPULATION_CHANGED")
    result = {}
    for issuer, expected in EXPECTED_FACE_COUNTS.items():
        item = _mapping(source[issuer], "ORIGINAL_" + issuer.upper())
        _is_true(item.get("frozen_original_sha256_verified"), "ORIGINAL_PDF_SHA256")
        if (item.get("sha256") != FROZEN_DOCUMENT_SHA256[issuer]
                or item.get("source_face_catalog_sha256") != SOURCE_FACE_CATALOG_HASH[issuer]
                or item.get("retally_native_route") != "DOCUMENT_EXTRACTION_REQUIRED"
                or item.get("label_state") != "UNKNOWN_NO_INDEPENDENT_RATE_OR_ADJUDICATION"):
            raise ResearchError("FREIGHT_EVIDENCE_CHAIN_PUBLISHER_OR_FACE_CATALOG_DRIFT")
        _count(item.get("distinct_invoice_face_ids"), issuer + "_FACES", expected)
        _count(item.get("invoice_face_amounts_extracted"), issuer + "_AMOUNTS", expected)
        anchor = _mapping(item.get("invoice_face_anchor_verification"), issuer + "_ANCHORS")
        _count(anchor.get("failed"), issuer + "_FAILED_ANCHORS", 0)
        if _count(anchor.get("passed"), issuer + "_PASSED_ANCHORS") != _count(
                anchor.get("checks"), issuer + "_TOTAL_ANCHORS"):
            raise ResearchError("FREIGHT_EVIDENCE_CHAIN_ORIGINAL_FACE_ANCHOR_DRIFT")
        _count(item.get("validated_overcharge_cents"), "INVALID_SOURCE_OVERCHARGE", 0)
        _count(item.get("realized_recovery_cents"), "INVALID_SOURCE_RECOVERY", 0)
        result[issuer] = item

    gt, abf = result["globaltranz"], result["arcbest"]
    source_lines = _mapping(gt.get("original_invoice_line_amount_reconciliation"), "SIGNED_LINES")
    for key, expected in (
            ("invoice_faces_considered", 100), ("invoice_face_exact_line_sum", 100),
            ("invoice_face_nonmatching_extracted_line_sum", 0),
            ("invoice_face_component_text_unavailable", 0),
            ("invoice_faces_containing_negative_discounts", 93)):
        _count(source_lines.get(key), key.upper(), expected)
    _is_true(source_lines.get("every_face_conserved"), "SOURCE_LINE_CONSERVATION")
    _is_false(source_lines.get("line_sum_proves_cash_settlement"), "SOURCE_SETTLEMENT_INFERENCE")
    _is_false(source_lines.get("line_sum_proves_controlling_rate_or_overcharge"),
              "SOURCE_RATE_INFERENCE")

    signed = _mapping(gt.get("canonical_v2_original_invoice_adjustment_lab"), "CANONICAL_INVOICE")
    if (signed.get("scope") != "ORIGINAL_PDF_SIGNED_MONEY_REPLAY_WITH_SYNTHETIC_SHIPMENT_NO_TARIFF"
            or signed.get("source_bound_adjustment_sha256") != FROZEN_DOCUMENT_SHA256["globaltranz"]
            or signed.get("stable_canonical_record_catalog_sha256") != SIGNED_RECORD_CATALOG_HASH):
        raise ResearchError("FREIGHT_EVIDENCE_CHAIN_CANONICAL_RECORD_DIGEST_DRIFT")
    for key, expected in (
            ("original_invoice_faces_considered", 100), ("canonical_records_built", 100),
            ("canonical_invoice_records_with_exact_source_net", 100),
            ("canonical_v2_adjustment_records_with_exact_source_net", 93),
            ("canonical_v1_charge_only_records_with_exact_source_net", 7),
            ("discount_bearing_v2_records", 93), ("rate_review_required", 100),
            ("unrepresentable_or_missing_source", 0),
            ("unsafe_auto_money_or_nondeterministic", 0),
            ("independent_invoice_overcharge_labels", 0), ("recovered_cash_cents", 0),
            ("customer_contact_actions", 0)):
        _count(signed.get(key), key.upper(), expected)
    for flag in ("input_original_pdf_digest_matches_frozen_baseline",
                 "shipment_fields_are_synthetic_lab_placeholders",
                 "invoice_adjustment_kind_is_lab_hypothesis_not_adjudicated"):
        _is_true(signed.get(flag), flag.upper())
    for flag in ("production_pdf_extraction_completed",
                 "commercial_rate_authority_verified"):
        _is_false(signed.get(flag), flag.upper())

    statement = _mapping(gt.get("statement"), "OPEN_STATEMENT")
    if statement.get("bank_payment_reconciliation") != "NOT_POSSIBLE_NO_BANK_RECORD":
        raise ResearchError("FREIGHT_EVIDENCE_CHAIN_PAYMENT_CANNOT_BE_INFERRED")
    statement_ids = _mapping(gt.get("face_statement_identity_diagnostic"), "STATEMENT_IDENTITIES")
    _count(statement_ids.get("same_identifier_and_original_amount"), "IDENTITY_AMOUNT_MATCH", 100)
    _is_true(statement_ids.get("these_differences_are_not_payment_or_overcharge_findings"),
             "STATEMENT_NOT_SETTLEMENT")
    abf_rated = _mapping(abf.get("retally_rating_engine"), "ARCBEST_RATE_REVIEW")
    _count(abf_rated.get("invoice_faces_considered"), "ARCBEST_CONSIDERED", 10)
    _count(abf_rated.get("engine_review_required"), "ARCBEST_REVIEW", 5)
    _count(abf_rated.get("source_completeness_blocked"), "ARCBEST_PARTIAL", 5)
    _count(abf_rated.get("unsafe_auto_money_or_nondeterministic"), "ARCBEST_UNSAFE", 0)
    _count(abf_rated.get("auto_overcharges_asserted"), "ARCBEST_AUTO_OVERCHARGES", 0)
    printed = _mapping(abf.get("source_printed_rate_bol_reference_census"),
                       "ARCBEST_PRINTED_HEADER_REFERENCES")
    if (printed.get("scope") != "ORIGINAL_ARCBEST_PDF_PRINTED_REFERENCE_HINTS_ONLY"
            or printed.get("source_original_pdf_sha256") != FROZEN_DOCUMENT_SHA256["arcbest"]
            or printed.get("anonymous_page_category_digest_sha256") != ARCBEST_PRINTED_REFERENCE_DIGEST):
        raise ResearchError("FREIGHT_EVIDENCE_CHAIN_ARCBEST_PRINTED_SOURCE_IDENTITY_DRIFT")
    for key, expected in (("original_invoice_faces_considered", 10),
                          ("source_page_identity_bound_count", 10),
                          ("unbound_original_source_pages", 0),
                          ("original_customer_quote_documents_independently_verified", 0),
                          ("independently_custodied_original_bol_documents", 0),
                          ("shipment_effective_customer_rate_authorities_verified", 0),
                          ("independently_scored_customer_overcharges", 0),
                          ("original_source_identifiers_exported", 0),
                          ("verified_retally_recovered_cash_cents", 0),
                          ("third_party_contacts", 0)):
        _count(printed.get(key), "ARCBEST_" + key.upper(), expected)
    _is_true(printed.get("source_pdf_printed_reference_not_executed_rate_contract"),
             "ARCBEST_PRINTED_CODE_NOT_EFFECTIVE_TARIFF")
    tariff_classes = _mapping(printed.get("printed_tariff_reference_class_counts"),
                              "ARCBEST_TARIFF_CATEGORIES")
    bol_classes = _mapping(printed.get("printed_bol_header_class_counts"),
                           "ARCBEST_BOL_CATEGORIES")
    if (set(tariff_classes) != set(ARCBEST_PRINTED_TARIFF_CLASSES)
            or set(bol_classes) != set(ARCBEST_PRINTED_BOL_HEADER_CLASSES)):
        raise ResearchError("FREIGHT_EVIDENCE_CHAIN_ARCBEST_PRINTED_REFERENCE_SCOPE_DRIFT")
    for name, target in ARCBEST_PRINTED_TARIFF_CLASSES.items():
        _count(tariff_classes[name], "ARCBEST_PRINTED_" + name, target)
    for name, target in ARCBEST_PRINTED_BOL_HEADER_CLASSES.items():
        _count(bol_classes[name], "ARCBEST_PRINTED_" + name, target)

    blind = _mapping(doc.get("blinded_freight_error_evaluation"), "BLIND_ASSESSMENT")
    for field in ("precision", "recall", "freight_detection_accuracy"):
        if blind.get(field) is not None:
            raise ResearchError("FREIGHT_EVIDENCE_CHAIN_UNEARNED_ACCURACY")
    for key in ("total_eligible_scored", "model_output_evaluated_on_truth_cases",
                "validated_recovery_cents"):
        _count(blind.get(key), key.upper(), 0)
    _count(blind.get("unknown_cases_preserved"), "ALL_ORIGINAL_CASES_UNKNOWN", 110)
    _is_false(blind.get("independent_blind_truth_adjudication_completed"), "INDEPENDENT_TRUTH")

    total = sum(EXPECTED_FACE_COUNTS.values())
    base = {
        "schema_version": 1,
        "scope": SCOPE, "as_of_utc_date": as_of.isoformat(),
        "federal_guidance_scope": GUIDANCE_APPLICABILITY,
        "guidance_reference_urls": [FEDERAL_REFERENCE_URL, FEDERAL_AUDIT_URL],
        "original_pdf_sources_with_verified_byte_hashes": len(EXPECTED_FACE_COUNTS),
        "original_invoice_faces_observed": total,
        "face_total_amounts_extracted": total,
        "original_net_amounts_reconciled_to_signed_components": 100,
        "globaltranz_source_adjustment_v2_cases": 93,
        "globaltranz_positive_only_v1_cases": 7,
        "globaltranz_open_statement_identity_and_original_amount_matches": 100,
        "arcbest_source_proxy_rating_review_count": 5,
        "arcbest_source_printed_tariff_reference_classes":
            dict(ARCBEST_PRINTED_TARIFF_CLASSES),
        "arcbest_source_printed_bol_header_classes":
            dict(ARCBEST_PRINTED_BOL_HEADER_CLASSES),
        "arcbest_source_printed_category_sha256": ARCBEST_PRINTED_REFERENCE_DIGEST,
        "arcbest_independently_verified_rate_and_original_bol_documents": 0,
        "source_original_sha256": {k: FROZEN_DOCUMENT_SHA256[k] for k in sorted(FROZEN_DOCUMENT_SHA256)},
        "original_invoice_catalog_sha256": {k: SOURCE_FACE_CATALOG_HASH[k] for k in sorted(SOURCE_FACE_CATALOG_HASH)},
        "source_bound_canonical_signed_catalog_sha256": SIGNED_RECORD_CATALOG_HASH,
        "independent_evidence_chain_stages": {
            "original_invoice_source_face": total,
            "source_face_amount": total,
            "source_signed_component_net": 100,
            "independent_bol_or_shipment_link_in_lab": 0,
            "shipment_specific_effective_customer_rate_authority_in_lab": 0,
            "independent_delivery_or_service_confirmation_in_lab": 0,
            "independent_actual_weight_or_class_validation_in_lab": 0,
            "cleared_bank_payment_or_refund_in_lab": 0,
            "independently_adjudicated_customer_invoice_outcome_in_lab": 0,
        },
        "missing_chain_evidence_from_current_lab": {
            stage: total for stage in MISSING_CHAIN_STAGES
        },
        "eligible_independently_scored_customer_invoices": 0,
        "accuracy": None, "recall": None,
        "verified_retally_recovered_cash_cents": 0,
        "commercial_customer_engine_input_approved": False,
        "modern_rate_authority_proven": False,
        "production_engine_modified": False,
        "external_customer_contact_actions": 0,
        "readiness": "SOURCE_INVOICE_NET_RECONCILED_INDEPENDENT_RATE_BOL_PAYMENT_CHAIN_MISSING",
        "limitations": list(LIMITATIONS),
    }
    return {**base, "receipt_sha256": digest(base)}


def validate_receipt(doc: dict, report: dict, *, as_of: date) -> None:
    if type(doc) is not dict or frozenset(doc) != RECEIPT_KEYS:
        raise ResearchError("FREIGHT_EVIDENCE_CHAIN_RECEIPT_SCHEMA_INVALID")
    if doc != make_receipt(report, as_of=as_of):
        raise ResearchError("FREIGHT_EVIDENCE_CHAIN_RECEIPT_TAMPERED")


def run(*, source: Path, output: Path, verify_only: bool = False) -> dict:
    try:
        report = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ResearchError("FREIGHT_EVIDENCE_CHAIN_SOURCE_REPORT_UNAVAILABLE") from exc
    try:
        stamp = datetime.fromisoformat(report["run_date_utc"].replace("Z", "+00:00"))
        if stamp.tzinfo is None or stamp.utcoffset() is None:
            raise ValueError("source observation must be timezone aware")
        at_date = stamp.astimezone(timezone.utc).date()
    except (KeyError, AttributeError, ValueError, TypeError) as exc:
        raise ResearchError("FREIGHT_EVIDENCE_CHAIN_OBSERVATION_DATE_INVALID") from exc
    if (at_date > datetime.now(timezone.utc).date()
            or (datetime.now(timezone.utc).date() - at_date).days > 2):
        raise ResearchError("FREIGHT_EVIDENCE_CHAIN_OBSERVATION_STALE_OR_FUTURE")
    expected = make_receipt(report, as_of=at_date)
    if verify_only:
        try:
            receipt = json.loads(output.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ResearchError("FREIGHT_EVIDENCE_CHAIN_RECEIPT_UNAVAILABLE") from exc
        validate_receipt(receipt, report, as_of=at_date)
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        output_tmp = output.with_suffix(".tmp")
        output_tmp.write_text(json.dumps(expected, sort_keys=True, indent=2) + "\n",
                              encoding="utf-8")
        output_tmp.replace(output)
    return {
        "scope": SCOPE,
        "source_invoice_faces": expected["original_invoice_faces_observed"],
        "signed_net_totals_reconciled": expected["original_net_amounts_reconciled_to_signed_components"],
        "missing_effective_rate_authority": expected["missing_chain_evidence_from_current_lab"]["SHIPMENT_SPECIFIC_EFFECTIVE_CONTRACT_OR_TENDER"],
        "independent_customer_invoice_truth_cases": 0,
        "verified_recovered_cash_cents": 0,
        "federal_guidance_not_private_legal_authority": True,
        "receipt_sha256": expected["receipt_sha256"],
        "verified": verify_only,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run(source=args.source, output=args.output, verify_only=args.verify),
                     sort_keys=True))


if __name__ == "__main__":
    main()
