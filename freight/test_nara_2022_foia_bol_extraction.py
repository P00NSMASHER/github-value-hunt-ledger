"""NARA FOIA redacted original 2022 GBL: extraction-only, no rate or cash claim."""
from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

PACK = (Path(__file__).with_name("fixtures")
        / "nara_2022_foia_redacted_bol_extraction_candidate_v0.json")


class NARAOriginalBOLExtractionTests(unittest.TestCase):
    """Offline checks on one publicly rendered BOL, not an original paid invoice."""

    @staticmethod
    def _pack():
        return json.loads(PACK.read_text(encoding="utf-8"))

    def _assert_scope(self, p):
        self.assertEqual(p["schema_version"], "0.1.1")
        self.assertEqual(p["fixture_id"],
                         "NARA_FOIA_2022_REDACTED_ORIGINAL_GOVERNMENT_BOL_EXTRACTION_CANDIDATE_V0")
        self.assertEqual(p["status"], "DRAFT_SOURCE_BOUND_HOLD_UNRELEASED")
        self.assertEqual(p["evaluation_family"],
                         "FREIGHT_DOCUMENT_EXTRACTION_PUBLIC_REDACTED_ORIGINAL_BOL_NOT_FREIGHT_ERROR_OR_PAYMENT_SCORING")
        self.assertEqual((p["engine"], p["secondary_engine"]),
                         ("freightrecovery", "recoveryos"))
        s, r = p["source"], p["rights"]
        self.assertEqual(s["publisher"], "U.S. National Archives and Records Administration")
        self.assertEqual(s["official_url"],
                         "https://www.archives.gov/files/foia/category-4-final.pdf")
        self.assertEqual((s["format"], s["page_count"]), ("PDF", 3))
        self.assertEqual(s["document_issue_date"], "2022-01-12")
        self.assertEqual(s["source_release_date"], "UNKNOWN")
        self.assertEqual(s["source_retrieved_for_visual_review_utc_date"], "2026-10-29")
        self.assertEqual(s["public_pages_visually_reviewed"], 3)
        for key in ("raw_publisher_pdf_bytes_acquired",
                    "publisher_http_status_and_headers_archived",
                    "original_signed_document_independently_verified",
                    "invoice_face_acquired", "tariff_or_tender_original_document_acquired",
                    "carrier_payment_receipt_acquired"):
            self.assertFalse(s[key], key)
        self.assertIsNone(s["original_publisher_pdf_sha256"])
        self.assertEqual(r["policy_url"],
                         "https://www.archives.gov/research/still-pictures/permissions")
        self.assertTrue(r["general_us_government_created_records_us_public_domain_guidance"])
        self.assertTrue(r["public_foia_redactions_preserved"])
        for key in ("source_specific_third_party_or_restriction_clearance_complete",
                    "automated_commercial_customer_scoring_approved",
                    "redistribution_of_original_document_authorized_by_lab"):
            self.assertFalse(r[key], key)
        self.assertEqual(r["confidential_or_unredacted_rows_retained"], 0)

        x = p["extraction"]
        self.assertEqual(x["label_origin"],
                         "MANUAL_VISIBLE_FIELD_TRANSCRIPTION_FROM_NARA_PUBLIC_REDACTED_RENDERED_PAGES_NOT_INDEPENDENT_HOLDOUT")
        self.assertEqual((x["bol_number"], x["agency_shipment_id"]),
                         ("F0004196", "NAR22GBL032"))
        self.assertEqual((x["bol_issue_date"], x["bol_print_date"]),
                         ("2022-01-12", "2022-01-12"))
        self.assertEqual((x["requested_pickup_date"], x["required_delivery_date"]),
                         ("2022-01-17", "2022-01-19"))
        self.assertEqual((x["actual_pickup_date_field"], x["delivered_on_date_field"]),
                         ("BLANK", "BLANK"))
        self.assertEqual((x["annotation_pickup_date_time"],
                          x["annotation_delivery_date_time"]),
                         ("2022-01-17 14:00", "2022-01-19 09:00"))
        self.assertEqual((x["total_packages"], x["total_weight_reported_number"],
                          x["total_weight_unit"]),
                         (1, 500, "UNKNOWN_NOT_LABELED_IN_VISIBLE_BOX"))
        self.assertEqual(x["mode"], "Motor")
        self.assertEqual(x["item_description_category"], "Government Records")
        self.assertEqual(x["rate_authority_reference_printed"],
                         "Tender ID OTO $4990.2 ON 01/12/2022")
        self.assertEqual(x["estimate_box_usd_cents"], 499020)
        self.assertEqual(x["continuation_page_total_usd_cents"], 499020)
        for key in ("linehaul_displayed_usd_cents", "fuel_displayed_usd_cents",
                    "accessorial_displayed_usd_cents"):
            self.assertEqual(x[key], 0)
        self.assertEqual((x["shipper_signature_field"], x["carrier_signature_field"]),
                         ("BLANK", "BLANK"))
        self.assertEqual(x["carrier_name"], "REDACTED_NOT_REPLICATED")

        q, g = p["quality"], p["ground_truth"]
        for key in ("document_total_is_not_sum_of_displayed_zero_itemization",
                    "zero_component_rows_are_not_proof_of_499020_cent_overcharge",
                    "estimate_and_total_agree",
                    "all_visible_dates_are_not_proof_of_actual_service",
                    "public_bol_is_not_carrier_invoice_or_bank_payment",
                    "redacted_identifiers_not_reconstructed"):
            self.assertTrue(q[key], key)
        b = p["billing_direction_observation"]
        self.assertEqual(b["source_grounding"],
                         "PAGE_1_BOX_9_BILL_CHARGES_TO_AND_PAGE_2_PRINTED_TSP_BILLING_CERTIFICATE_HEADING")
        self.assertEqual(b["printed_bill_charges_to"],
                         "THIRD_PARTY_BILLING_SERVICE_AT_US_BANK")
        self.assertEqual(b["printed_tsp_billing_certificate_scope"],
                         "CONSIGNEE_MUST_NOT_PAY_ANY_CHARGES")
        self.assertEqual(b["original_label_kind"],
                         "VISUAL_PUBLIC_FORM_TEXT_NOT_LEDGER_ENTRY_OR_INDEPENDENT_PAYMENT_LABEL")
        for key in ("printed_instruction_is_validated_account_payable_liability",
                    "printed_instruction_proves_payment_was_made",
                    "consignee_is_verified_debtor"):
            self.assertIs(b[key], False, key)
        self.assertEqual(b["actual_payer_identity"], "UNKNOWN")
        self.assertEqual(b["verified_payment_status"], "UNKNOWN")
        self.assertEqual(b["recoveryos_reconciliation_label"],
                         "UNKNOWN_DO_NOT_POST_CONSIGNEE_PAYABLE_OR_ASSUME_THIRD_PARTY_PAYMENT")
        self.assertTrue(q["printed_billing_direction_not_payment_evidence"])
        self.assertTrue(q["consignee_is_not_verified_accounts_payable_debtor"])

        for key in ("actual_valid_tender_rate_usd_cents",
                    "freight_amount_overcharged_usd_cents",
                    "carrier_payment_amount_usd_cents"):
            self.assertIsNone(q[key])
        self.assertEqual(g["source_documents_publicly_viewed"], 1)
        self.assertEqual(g["original_bol_images_in_lab_custody"], 0)
        for key in ("independently_heldout_labeled_original_bols",
                    "independent_invoice_face_error_labels",
                    "verified_carrier_invoice_payments",
                    "verified_retally_customer_recovered_usd_cents"):
            self.assertEqual(g[key], 0, key)
        for key in ("document_extraction_accuracy", "rate_accuracy",
                    "real_overcharge", "carrier_refund"):
            self.assertIn("UNKNOWN", g[key], key)
        self.assertFalse(g["production_acceptance"])
        self.assertEqual(p["consumers"]["qa_44"],
                         "INDEPENDENT_PDF_CUSTODY_LABELS_RIGHTS_AND_PYTHON_CI_PENDING")
        c = p["synthetic_negative_controls"]
        self.assertEqual(len(c), 9)
        self.assertEqual(len({row["id"] for row in c}), 9)
        self.assertTrue(all(row["id"].startswith("SYNTHETIC-NARA-")
                            and row["kind"] == "SYNTHETIC"
                            and row["expected"] == "REJECT" for row in c))

    def test_source_visible_fields_are_extraction_only(self):
        self._assert_scope(self._pack())

    def test_zero_cost_breakdown_does_not_establish_an_overcharge(self):
        p = self._pack()
        self._assert_scope(p)
        x = p["extraction"]
        self.assertEqual(sum(x[k] for k in (
            "linehaul_displayed_usd_cents", "fuel_displayed_usd_cents",
            "accessorial_displayed_usd_cents")), 0)
        self.assertEqual(x["continuation_page_total_usd_cents"], 499020)
        self.assertIsNone(p["quality"]["freight_amount_overcharged_usd_cents"])
        self.assertEqual(p["ground_truth"]["rate_accuracy"], "UNKNOWN")

    def test_synthetic_false_ownership_custody_payment_and_rate_claims_rejected(self):
        changes = (
            lambda p: p["source"].update(raw_publisher_pdf_bytes_acquired=True),
            lambda p: p["source"].update(original_publisher_pdf_sha256="a" * 64),
            lambda p: p["source"].update(invoice_face_acquired=True),
            lambda p: p["source"].update(carrier_payment_receipt_acquired=True),
            lambda p: p["rights"].update(automated_commercial_customer_scoring_approved=True),
            lambda p: p["rights"].update(source_specific_third_party_or_restriction_clearance_complete=True),
            lambda p: p["extraction"].update(continuation_page_total_usd_cents=0),
            lambda p: p["extraction"].update(linehaul_displayed_usd_cents=499020),
            lambda p: p["extraction"].update(carrier_signature_field="SIGNED"),
            lambda p: p["extraction"].update(actual_pickup_date_field="2022-01-17"),
            lambda p: p["extraction"].update(total_weight_unit="POUNDS_VERIFIED"),
            lambda p: p["quality"].update(zero_component_rows_are_not_proof_of_499020_cent_overcharge=False),
            lambda p: p["quality"].update(freight_amount_overcharged_usd_cents=499020),
            lambda p: p["ground_truth"].update(independently_heldout_labeled_original_bols=1),
            lambda p: p["ground_truth"].update(verified_retally_customer_recovered_usd_cents=499020),
            lambda p: p["ground_truth"].update(production_acceptance=True),
            lambda p: p["billing_direction_observation"].update(printed_instruction_proves_payment_was_made=True),
            lambda p: p["billing_direction_observation"].update(consignee_is_verified_debtor=True),
            lambda p: p["billing_direction_observation"].update(actual_payer_identity="US_BANK_CONFIRMED_PAID"),
            lambda p: p["billing_direction_observation"].update(verified_payment_status="PAID"),
            lambda p: p["billing_direction_observation"].update(printed_tsp_billing_certificate_scope="CONSIGNEE_MUST_PAY"),
            lambda p: p["quality"].update(printed_billing_direction_not_payment_evidence=False),
            lambda p: p["quality"].update(consignee_is_not_verified_accounts_payable_debtor=False),
            lambda p: p["synthetic_negative_controls"][0].update(kind="ORIGINAL"),
        )
        for i, edit in enumerate(changes):
            with self.subTest(synthetic_mutation=i):
                p = copy.deepcopy(self._pack())
                edit(p)
                with self.assertRaises(AssertionError):
                    self._assert_scope(p)


if __name__ == "__main__":
    unittest.main()
