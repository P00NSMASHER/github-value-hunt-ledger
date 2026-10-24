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
