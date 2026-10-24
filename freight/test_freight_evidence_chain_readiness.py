"""Falsify source/authority overclaims before freight evidence readiness is published."""
from __future__ import annotations

import copy
import json
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path

from freight.freight_evidence_chain_readiness import (
    EXPECTED_FACE_COUNTS, FROZEN_DOCUMENT_SHA256, GUIDANCE_APPLICABILITY,
    SIGNED_RECORD_CATALOG_HASH, SOURCE_FACE_CATALOG_HASH, SCOPE,
    ARCBEST_PRINTED_REFERENCE_DIGEST, ARCBEST_PRINTED_TARIFF_CLASSES,
    ARCBEST_PRINTED_BOL_HEADER_CLASSES,
    ARCBEST_PRINTED_PRICING_BOL_JOINT_CLASSES,
    ARCBEST_EMBEDDED_QUOTE_MATCH_DIGEST,
    make_receipt, validate_receipt, run,
)
from freight.unified_research_lab import ResearchError, digest


DAY = date(2026, 10, 24)


def source_document_report() -> dict:
    """Synthetic report shape with pinned original-source aggregate fingerprints."""
    def original(issuer: str, faces: int) -> dict:
        return {
            "sha256": FROZEN_DOCUMENT_SHA256[issuer],
            "source_face_catalog_sha256": SOURCE_FACE_CATALOG_HASH[issuer],
            "frozen_original_sha256_verified": True,
            "distinct_invoice_face_ids": faces,
            "invoice_face_amounts_extracted": faces,
            "invoice_face_anchor_verification": {
                "checks": 5 if issuer == "globaltranz" else 10,
                "passed": 5 if issuer == "globaltranz" else 10,
                "failed": 0,
            },
            "retally_native_route": "DOCUMENT_EXTRACTION_REQUIRED",
            "label_state": "UNKNOWN_NO_INDEPENDENT_RATE_OR_ADJUDICATION",
            "validated_overcharge_cents": 0,
            "realized_recovery_cents": 0,
        }

    gt = original("globaltranz", 100)
    gt["original_invoice_line_amount_reconciliation"] = {
        "invoice_faces_considered": 100,
        "invoice_face_exact_line_sum": 100,
        "invoice_face_nonmatching_extracted_line_sum": 0,
        "invoice_face_component_text_unavailable": 0,
        "invoice_faces_containing_negative_discounts": 93,
        "every_face_conserved": True,
        "line_sum_proves_cash_settlement": False,
        "line_sum_proves_controlling_rate_or_overcharge": False,
    }
    gt["canonical_v2_original_invoice_adjustment_lab"] = {
        "scope": "ORIGINAL_PDF_SIGNED_MONEY_REPLAY_WITH_SYNTHETIC_SHIPMENT_NO_TARIFF",
        "source_bound_adjustment_sha256": FROZEN_DOCUMENT_SHA256["globaltranz"],
        "stable_canonical_record_catalog_sha256": SIGNED_RECORD_CATALOG_HASH,
        "original_invoice_faces_considered": 100,
        "canonical_records_built": 100,
        "canonical_invoice_records_with_exact_source_net": 100,
        "canonical_v2_adjustment_records_with_exact_source_net": 93,
        "canonical_v1_charge_only_records_with_exact_source_net": 7,
        "discount_bearing_v2_records": 93,
        "rate_review_required": 100,
        "unrepresentable_or_missing_source": 0,
        "unsafe_auto_money_or_nondeterministic": 0,
        "independent_invoice_overcharge_labels": 0,
        "recovered_cash_cents": 0,
        "customer_contact_actions": 0,
        "input_original_pdf_digest_matches_frozen_baseline": True,
        "shipment_fields_are_synthetic_lab_placeholders": True,
        "invoice_adjustment_kind_is_lab_hypothesis_not_adjudicated": True,
        "production_pdf_extraction_completed": False,
        "commercial_rate_authority_verified": False,
    }
    gt["statement"] = {"bank_payment_reconciliation": "NOT_POSSIBLE_NO_BANK_RECORD"}
    gt["face_statement_identity_diagnostic"] = {
        "same_identifier_and_original_amount": 100,
        "these_differences_are_not_payment_or_overcharge_findings": True,
    }
    abf = original("arcbest", 10)
    abf["retally_rating_engine"] = {
        "invoice_faces_considered": 10,
        "engine_review_required": 5,
        "source_completeness_blocked": 5,
        "unsafe_auto_money_or_nondeterministic": 0,
        "auto_overcharges_asserted": 0,
    }
    abf["source_printed_rate_bol_reference_census"] = {
        "scope": "ORIGINAL_ARCBEST_PDF_PRINTED_REFERENCE_HINTS_ONLY",
        "source_original_pdf_sha256": FROZEN_DOCUMENT_SHA256["arcbest"],
        "original_invoice_faces_considered": 10,
        "source_page_identity_bound_count": 10,
        "unbound_original_source_pages": 0,
        "printed_tariff_reference_class_counts": dict(ARCBEST_PRINTED_TARIFF_CLASSES),
        "printed_bol_header_class_counts": dict(ARCBEST_PRINTED_BOL_HEADER_CLASSES),
        "printed_pricing_bol_joint_class_counts":
            dict(ARCBEST_PRINTED_PRICING_BOL_JOINT_CLASSES),
        "printed_vpq_with_bol_header_identifier_only": 1,
        "printed_vpq_without_bol_header_identifier": 1,
        "original_bol_quote_id_correspondence_independently_verified": 0,
        "printed_bol_header_is_not_original_bol_custody": True,
        "anonymous_page_category_digest_sha256": ARCBEST_PRINTED_REFERENCE_DIGEST,
        "source_pdf_printed_reference_not_executed_rate_contract": True,
        "original_customer_quote_documents_independently_verified": 0,
        "independently_custodied_original_bol_documents": 0,
        "shipment_effective_customer_rate_authorities_verified": 0,
        "independently_scored_customer_overcharges": 0,
        "original_source_identifiers_exported": 0,
        "verified_retally_recovered_cash_cents": 0,
        "third_party_contacts": 0,
    }
    abf["embedded_original_vpq_quote_source_replay"] = {
        "scope": "ORIGINAL_ARCBEST_SAME_PDF_QUOTE_INVOICE_ARITHMETIC_NOT_CUSTOMER_RECOVERY",
        "source_original_pdf_sha256": FROZEN_DOCUMENT_SHA256["arcbest"],
        "embedded_original_vpq_quotation_pages": 2,
        "vpq_original_invoice_faces": 2,
        "same_pdf_exact_quotation_id_invoice_joins": 2,
        "invoice_dates_within_printed_quote_effective_window": 2,
        "printed_invoice_quoted_weights_agree": 2,
        "invoice_amount_equals_printed_quote_minimum": 1,
        "conditional_printed_length_formula_matches": 1,
        "invoice_quote_money_unresolved": 0,
        "anonymous_page_and_match_class_digest_sha256":
            ARCBEST_EMBEDDED_QUOTE_MATCH_DIGEST,
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
        "unresolved_reason_counts": {},
    }
    blind = {
        "precision": None,
        "recall": None,
        "freight_detection_accuracy": None,
        "total_eligible_scored": 0,
        "model_output_evaluated_on_truth_cases": 0,
        "validated_recovery_cents": 0,
        "unknown_cases_preserved": 110,
        "independent_blind_truth_adjudication_completed": False,
    }
    return {
        "schema_version": 1, "laboratory": "RETALLY_REAL_DOCUMENT_RESEARCH_LAB",
        "run_date_utc": "2026-10-24T15:48:32.000000+00:00",
        "production_release_approved": False,
        "commercial_reuse_validated": False,
        "freight_original_document_benchmark": {
            "globaltranz": gt, "arcbest": abf,
        },
        "blinded_freight_error_evaluation": blind,
    }


class FreightEvidenceChainReadinessTests(unittest.TestCase):
    def test_110_original_faces_are_not_110_verified_customer_overcharges(self):
        source = source_document_report()
        receipt = make_receipt(source, as_of=DAY)
        self.assertEqual(receipt["scope"], SCOPE)
        self.assertEqual(receipt["federal_guidance_scope"], GUIDANCE_APPLICABILITY)
        self.assertEqual(receipt["original_pdf_sources_with_verified_byte_hashes"], 2)
        self.assertEqual(receipt["original_invoice_faces_observed"], 110)
        self.assertEqual(receipt["face_total_amounts_extracted"], 110)
        self.assertEqual(receipt["original_net_amounts_reconciled_to_signed_components"], 100)
        self.assertEqual(receipt["globaltranz_source_adjustment_v2_cases"], 93)
        self.assertEqual(receipt["globaltranz_positive_only_v1_cases"], 7)
        self.assertEqual(receipt["globaltranz_open_statement_identity_and_original_amount_matches"], 100)
        self.assertEqual(receipt["arcbest_source_proxy_rating_review_count"], 5)
        self.assertEqual(receipt["arcbest_source_printed_tariff_reference_classes"],
                         ARCBEST_PRINTED_TARIFF_CLASSES)
        self.assertEqual(receipt["arcbest_source_printed_bol_header_classes"],
                         ARCBEST_PRINTED_BOL_HEADER_CLASSES)
        self.assertEqual(receipt["arcbest_source_printed_pricing_bol_joint_classes"],
                         ARCBEST_PRINTED_PRICING_BOL_JOINT_CLASSES)
        self.assertEqual(receipt["arcbest_source_vpq_header_with_bol_identifier_only"], 1)
        self.assertEqual(receipt["arcbest_source_vpq_header_without_bol_identifier"], 1)
        self.assertEqual(receipt["arcbest_original_bol_quote_id_correspondence_verified"], 0)
        self.assertEqual(receipt["arcbest_source_printed_category_sha256"],
                         ARCBEST_PRINTED_REFERENCE_DIGEST)
        self.assertEqual(receipt["arcbest_embedded_original_quote_pages"], 2)
        self.assertEqual(receipt["arcbest_embedded_invoice_quote_id_joins"], 2)
        self.assertEqual(receipt["arcbest_embedded_quote_effective_date_matches"], 2)
        self.assertEqual(receipt["arcbest_embedded_quote_printed_weight_matches"], 2)
        self.assertEqual(receipt["arcbest_embedded_quote_minimum_money_matches"], 1)
        self.assertEqual(receipt["arcbest_embedded_conditional_length_formula_matches"], 1)
        self.assertEqual(receipt["arcbest_embedded_quote_match_class_sha256"],
                         ARCBEST_EMBEDDED_QUOTE_MATCH_DIGEST)
        self.assertTrue(receipt[
            "arcbest_same_pdf_quotes_not_independent_customer_rate_authorization"])
        self.assertEqual(receipt["arcbest_independently_verified_rate_and_original_bol_documents"], 0)
        self.assertEqual(receipt["eligible_independently_scored_customer_invoices"], 0)
        self.assertEqual(receipt["verified_retally_recovered_cash_cents"], 0)
        self.assertIsNone(receipt["accuracy"])
        self.assertIsNone(receipt["recall"])
        self.assertFalse(receipt["commercial_customer_engine_input_approved"])
        self.assertFalse(receipt["modern_rate_authority_proven"])
        self.assertEqual(receipt["source_bound_canonical_signed_catalog_sha256"],
                         SIGNED_RECORD_CATALOG_HASH)
        self.assertEqual(receipt["receipt_sha256"], digest({
            k: v for k, v in receipt.items() if k != "receipt_sha256"
        }))
        validate_receipt(receipt, source, as_of=DAY)
        self.assertEqual(set(EXPECTED_FACE_COUNTS), {"arcbest", "globaltranz"})

    def test_gsa_federal_reference_never_claims_private_customer_rule(self):
        r = make_receipt(source_document_report(), as_of=DAY)
        self.assertEqual(r["federal_guidance_scope"],
                         "FEDERAL_GSA_REFERENCE_ONLY_NOT_PRIVATE_CUSTOMER_LEGAL_AUTHORITY")
        self.assertTrue(all(u.startswith("https://www.gsa.gov/") for u in
                            r["guidance_reference_urls"]))
        self.assertIn("private-party contract applicability is NOT established",
                      r["limitations"][0])
        for k, v in r["independent_evidence_chain_stages"].items():
            if k not in {"original_invoice_source_face", "source_face_amount",
                         "source_signed_component_net"}:
                self.assertEqual(v, 0, k)
        self.assertEqual(set(r["missing_chain_evidence_from_current_lab"].values()), {110})
        self.assertEqual(r["external_customer_contact_actions"], 0)
        self.assertFalse(r["production_engine_modified"])

    def test_forged_source_custody_and_cash_evidence_fails_closed(self):
        base = source_document_report()
        mutations = [
            ("freight_original_document_benchmark", "globaltranz", "sha256", "0" * 64),
            ("freight_original_document_benchmark", "arcbest", "source_face_catalog_sha256", "0" * 64),
            ("freight_original_document_benchmark", "arcbest", "frozen_original_sha256_verified", False),
            ("freight_original_document_benchmark", "globaltranz", "retally_native_route", "PRODUCTION_AUTORATED"),
            ("freight_original_document_benchmark", "globaltranz", "invoice_face_amounts_extracted", 98),
            ("freight_original_document_benchmark", "globaltranz", "realized_recovery_cents", 7165),
        ]
        for level1, issuer, field, val in mutations:
            with self.subTest(issuer=issuer, field=field):
                edited = copy.deepcopy(base)
                edited[level1][issuer][field] = val
                with self.assertRaises(ResearchError):
                    make_receipt(edited, as_of=DAY)

    def test_signed_v2_digest_or_one_cent_money_drift_fails_closed(self):
        for field, val in (
            ("stable_canonical_record_catalog_sha256", "0" * 64),
            ("canonical_v2_adjustment_records_with_exact_source_net", 92),
            ("canonical_invoice_records_with_exact_source_net", 99),
            ("rate_review_required", 99),
            ("independent_invoice_overcharge_labels", 1),
            ("recovered_cash_cents", 1),
            ("commercial_rate_authority_verified", True),
            ("shipment_fields_are_synthetic_lab_placeholders", False),
            ("invoice_adjustment_kind_is_lab_hypothesis_not_adjudicated", False),
        ):
            with self.subTest(field=field):
                bad = source_document_report()
                bad["freight_original_document_benchmark"]["globaltranz"][
                    "canonical_v2_original_invoice_adjustment_lab"][field] = val
                with self.assertRaises(ResearchError):
                    make_receipt(bad, as_of=DAY)
        bad = source_document_report()
        bad["freight_original_document_benchmark"]["globaltranz"][
            "original_invoice_line_amount_reconciliation"]["invoice_face_exact_line_sum"] = 99
        with self.assertRaises(ResearchError):
            make_receipt(bad, as_of=DAY)

    def test_arcbest_header_hints_do_not_create_governing_contract_or_original_bol(self):
        report = source_document_report()
        categories = report["freight_original_document_benchmark"]["arcbest"][
            "source_printed_rate_bol_reference_census"]
        self.assertEqual(categories["source_page_identity_bound_count"], 10)
        for field, forged in (
            ("shipment_effective_customer_rate_authorities_verified", 1),
            ("original_customer_quote_documents_independently_verified", 2),
            ("independently_custodied_original_bol_documents", 2),
            ("independently_scored_customer_overcharges", 1),
            ("original_source_identifiers_exported", 10),
            ("source_page_identity_bound_count", 9),
            ("anonymous_page_category_digest_sha256", "0" * 64),
            ("source_original_pdf_sha256", "0" * 64),
            ("source_pdf_printed_reference_not_executed_rate_contract", False),
        ):
            with self.subTest(field=field):
                bad = copy.deepcopy(report)
                bad["freight_original_document_benchmark"]["arcbest"][
                    "source_printed_rate_bol_reference_census"][field] = forged
                with self.assertRaises(ResearchError):
                    make_receipt(bad, as_of=DAY)
        for field, forged in (
            ("printed_tariff_reference_class_counts",
             {"PRINTED_ABF_ACCOUNT_REFERENCE_ONLY": 8, "PRINTED_VOLUME_QUOTE_MARKER_ONLY": 2}),
            ("printed_bol_header_class_counts",
             {"BOL_HEADER_IDENTIFIER_PRINTED_ONLY": 10}),
        ):
            bad = copy.deepcopy(report)
            bad["freight_original_document_benchmark"]["arcbest"][
                "source_printed_rate_bol_reference_census"][field] = forged
            with self.assertRaises(ResearchError):
                make_receipt(bad, as_of=DAY)
        text = json.dumps(make_receipt(report, as_of=DAY))
        self.assertNotIn("ABF80193", text)
        self.assertNotIn("Bill of Lading No", text)
        self.assertNotIn("PRIVATE CUSTOMER", text)
        self.assertEqual(make_receipt(report, as_of=DAY)["accuracy"], None)

    def test_arcbest_vpq_bol_joint_counts_and_quote_id_are_immutable(self):
        base = source_document_report()
        original = make_receipt(base, as_of=DAY)
        cross = original["arcbest_source_printed_pricing_bol_joint_classes"]
        self.assertEqual(sum(cross.values()), 10)
        self.assertEqual(
            cross["PRINTED_VOLUME_QUOTE_MARKER_ONLY|BOL_HEADER_IDENTIFIER_PRINTED_ONLY"], 1)
        self.assertEqual(
            cross["PRINTED_VOLUME_QUOTE_MARKER_ONLY|BOL_HEADER_PLACEHOLDER_ONLY"], 1)
        self.assertEqual(original["arcbest_original_bol_quote_id_correspondence_verified"], 0)
        for field, forged in (
            ("printed_vpq_with_bol_header_identifier_only", 2),
            ("printed_vpq_without_bol_header_identifier", 0),
            ("original_bol_quote_id_correspondence_independently_verified", 1),
            ("printed_bol_header_is_not_original_bol_custody", False),
        ):
            with self.subTest(field=field):
                mutated = copy.deepcopy(base)
                mutated["freight_original_document_benchmark"]["arcbest"][
                    "source_printed_rate_bol_reference_census"][field] = forged
                with self.assertRaises(ResearchError):
                    make_receipt(mutated, as_of=DAY)
        for key, replacement in (
            ("PRINTED_VOLUME_QUOTE_MARKER_ONLY|BOL_HEADER_PLACEHOLDER_ONLY", 2),
            ("PRINTED_ABF_ACCOUNT_REFERENCE_ONLY|BOL_HEADER_PLACEHOLDER_ONLY", 4),
        ):
            with self.subTest(category=key):
                mutated = copy.deepcopy(base)
                mutated["freight_original_document_benchmark"]["arcbest"][
                    "source_printed_rate_bol_reference_census"][
                    "printed_pricing_bol_joint_class_counts"][key] = replacement
                with self.assertRaises(ResearchError):
                    make_receipt(mutated, as_of=DAY)
        self.assertEqual(original["eligible_independently_scored_customer_invoices"], 0)
        self.assertEqual(original["verified_retally_recovered_cash_cents"], 0)
        out = json.dumps(original)
        self.assertNotIn("ABF80193", out)
        self.assertNotIn("Bill of Lading No:", out)


    def test_two_embedded_quote_pages_are_real_source_but_not_independent_rate_truth(self):
        receipt = make_receipt(source_document_report(), as_of=DAY)
        self.assertEqual(receipt["arcbest_embedded_original_quote_pages"], 2)
        self.assertEqual(receipt["arcbest_embedded_invoice_quote_id_joins"], 2)
        self.assertEqual(receipt["arcbest_embedded_quote_minimum_money_matches"], 1)
        self.assertEqual(receipt["arcbest_embedded_conditional_length_formula_matches"], 1)
        self.assertTrue(receipt[
            "arcbest_same_pdf_quotes_not_independent_customer_rate_authorization"])
        self.assertEqual(receipt["arcbest_original_bol_quote_id_correspondence_verified"], 0)
        self.assertEqual(receipt["arcbest_independently_verified_rate_and_original_bol_documents"], 0)
        self.assertEqual(receipt["eligible_independently_scored_customer_invoices"], 0)
        self.assertEqual(receipt["verified_retally_recovered_cash_cents"], 0)
        for field, forged in (
            ("embedded_original_vpq_quotation_pages", 0),
            ("same_pdf_exact_quotation_id_invoice_joins", 1),
            ("invoice_dates_within_printed_quote_effective_window", 1),
            ("printed_invoice_quoted_weights_agree", 1),
            ("invoice_amount_equals_printed_quote_minimum", 2),
            ("conditional_printed_length_formula_matches", 0),
            ("invoice_quote_money_unresolved", 1),
            ("anonymous_page_and_match_class_digest_sha256", "0" * 64),
            ("original_signed_bol_quotes_independently_verified", 2),
            ("separate_quote_acceptance_independently_verified", 2),
            ("conditional_length_footage_is_independently_certified", True),
            ("quote_and_invoice_documents_are_co_bundled_in_same_source_pdf", False),
            ("commercial_reuse_authorized", True),
            ("independent_customer_invoice_overcharge_labels", 2),
            ("bank_cleared_payments_verified", 2),
            ("verified_retally_recovered_cash_cents", 1),
        ):
            with self.subTest(field=field):
                altered = source_document_report()
                altered["freight_original_document_benchmark"]["arcbest"][
                    "embedded_original_vpq_quote_source_replay"][field] = forged
                with self.assertRaises(ResearchError):
                    make_receipt(altered, as_of=DAY)
        leaked = json.dumps(receipt)
        for text in ("VPQ Quotation ID:", "PQ SCHEDULE NO", "V5WH1D1314",
                     "VKQS7R1064", "086855061", "279818407"):
            self.assertNotIn(text, leaked)

    def test_statement_identity_is_not_bank_payment_or_refund(self):
        source = source_document_report()
        source["freight_original_document_benchmark"]["globaltranz"]["statement"][
            "bank_payment_reconciliation"] = "PAID_VERIFIED"
        with self.assertRaisesRegex(ResearchError, "PAYMENT_CANNOT_BE_INFERRED"):
            make_receipt(source, as_of=DAY)
        source = source_document_report()
        source["blinded_freight_error_evaluation"]["precision"] = 1.0
        with self.assertRaisesRegex(ResearchError, "UNEARNED_ACCURACY"):
            make_receipt(source, as_of=DAY)
        source = source_document_report()
        source["blinded_freight_error_evaluation"]["unknown_cases_preserved"] = 109
        with self.assertRaises(ResearchError):
            make_receipt(source, as_of=DAY)

    def test_original_invoice_identifiers_are_never_serialized(self):
        data = source_document_report()
        data["freight_original_document_benchmark"]["globaltranz"][
            "accidentally_nested_private_info"] = {
                "customer": "DO_NOT_EXPORT_THIS_NAME",
                "invoice_id": "DO_NOT_EXPORT_THIS_INVOICE",
            }
        encoded = json.dumps(make_receipt(data, as_of=DAY))
        self.assertNotIn("DO_NOT_EXPORT", encoded)
        self.assertNotIn("invoice_id", encoded)
        self.assertIn("GSA_REFERENCE_ONLY", encoded)

    def test_unsigned_observation_time_is_rejected_before_publication(self):
        with tempfile.TemporaryDirectory() as root:
            source = Path(root) / "source.json"
            out = Path(root) / "receipt.json"
            fake = source_document_report()
            fake["run_date_utc"] = "2026-10-24T15:48:32"
            source.write_text(json.dumps(fake), encoding="utf-8")
            with self.assertRaisesRegex(ResearchError, "OBSERVATION_DATE_INVALID"):
                run(source=source, output=out)
            self.assertFalse(out.exists())

    def test_written_receipt_reproduces_and_rejects_rehashed_forgery(self):
        with tempfile.TemporaryDirectory() as root:
            source = Path(root) / "input.json"
            output = Path(root) / "audit.json"
            current = source_document_report()
            current["run_date_utc"] = datetime.now(timezone.utc).isoformat()
            source.write_text(json.dumps(current), encoding="utf-8")
            out = run(source=source, output=output)
            self.assertEqual(out["source_invoice_faces"], 110)
            self.assertEqual(out["signed_net_totals_reconciled"], 100)
            self.assertEqual(out["missing_effective_rate_authority"], 110)
            self.assertEqual(out["verified_recovered_cash_cents"], 0)
            self.assertFalse(out["verified"])
            before = output.read_bytes()
            self.assertTrue(run(source=source, output=output, verify_only=True)["verified"])
            self.assertEqual(before, output.read_bytes())
            bad = json.loads(before)
            bad["eligible_independently_scored_customer_invoices"] = 110
            bad["receipt_sha256"] = digest({
                k: v for k, v in bad.items() if k != "receipt_sha256"
            })
            output.write_text(json.dumps(bad), encoding="utf-8")
            with self.assertRaises(ResearchError):
                run(source=source, output=output, verify_only=True)
            with self.assertRaises(ResearchError):
                make_receipt(source_document_report(), as_of=date(2099, 1, 1))


if __name__ == "__main__":
    unittest.main()
