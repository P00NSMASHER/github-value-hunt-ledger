"""Historical GAO documentary-evidence boundary, offline and rights-held."""
from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from freight.unified_research_lab import SEEDS, safe_url

PACK = Path(__file__).with_name("fixtures") / "gao_b121220_documentary_proof_candidate_v0.json"
SOURCE = "https://www.gao.gov/products/b-121220-0"


class GAOB121220DocumentaryProofTests(unittest.TestCase):
    """No invoice-scoring or cash-proof promotion from an official decision."""

    @staticmethod
    def _pack():
        return json.loads(PACK.read_text(encoding="utf-8"))

    def _assert_held_source(self, pack):
        self.assertEqual(pack["schema_version"], "0.1.0")
        self.assertEqual(pack["evaluation_family"],
                         "HISTORICAL_FREIGHT_DOCUMENTARY_PROOF_NEGATIVE_CONTROL_NOT_CUSTOMER_INVOICE_SCORING")
        self.assertEqual(pack["engine"], "freightrecovery")
        self.assertEqual(pack["secondary_engine"], "recoveryos")
        source = pack["source"]
        self.assertEqual(source["url"], SOURCE)
        self.assertEqual(source["publisher"], "U.S. Government Accountability Office")
        self.assertEqual(source["decision_id"], "B-121220")
        self.assertEqual(source["decision_date"], "1964-02-13")
        self.assertEqual(source["earlier_modified_decision_date"], "1957-08-02")
        self.assertFalse(source["original_http_response_bytes_acquired"])
        self.assertIsNone(source["original_http_response_sha256"])
        self.assertFalse(source["original_invoices_freight_bills_payment_vouchers_acquired"])
        self.assertIsNone(source["historical_freight_tariff_effective_date"])
        self.assertTrue(pack["provenance"]["source_already_seeded_on_protected_main"])
        self.assertFalse(pack["provenance"]["original_source_byte_hash_verified"])
        rights = pack["rights"]
        self.assertEqual(rights["official_terms_url"], "https://www.gao.gov/copyright")
        self.assertEqual(rights["gao_government_authored_content_us_copyright_status"], "NOT_PROTECTED_IN_US")
        self.assertTrue(rights["acknowledge_publisher_required"])
        self.assertTrue(rights["no_implied_gao_endorsement"])
        self.assertFalse(rights["third_party_material_permission_checked"])
        self.assertFalse(rights["production_commercial_engine_use_authorized"])
        self.assertFalse(rights["redistribution_of_third_party_attachments_authorized"])
        facts = pack["historic_decision_facts"]
        self.assertEqual(facts["historical_small_prepaid_freight_exception_threshold_cents"], 2500)
        self.assertEqual(facts["small_exception_comparison"], "STRICTLY_LESS_THAN")
        self.assertEqual(facts["threshold_applies_only_to"],
                         "LIMITED_1957_PREPAID_FREIGHT_WAIVER_NO_GENERAL_CURRENT_RULE")
        self.assertFalse(facts["over_threshold_blanket_waiver_approved"])
        self.assertFalse(facts["unreceipted_carrier_freight_bill_alone_proves_payment"])
        self.assertFalse(facts["freight_bill_receipt_by_itself_proves_charges_correct"])
        self.assertTrue(facts["party_that_bore_freight_expense_must_be_established"])
        self.assertEqual(facts["case_rules_apply_to_modern_shipments"], "UNKNOWN")
        self.assertEqual(facts["unreceipted_bill_may_be_combined_with"],
                         "CERTIFIED_CARRIER_INVOICE_PAYMENT_EVIDENCE_AND_GOVERNMENT_REIMBURSEMENT_VOUCHER")
        cohort = pack["cohort"]
        self.assertEqual(cohort["historical_decision_count"], 1)
        self.assertEqual(cohort["independent_held_out_real_customer_labeled_invoices"], 0)
        self.assertIsNone(cohort["independently_verified_amount_overcharged_cents"])
        self.assertIsNone(cohort["verified_carrier_refund_received_cents"])
        self.assertEqual(cohort["retally_customer_recovery_cents"], 0)
        for key in ("provider_allowlist_changed", "source_original_bytes_verified",
                    "source_rights_for_automated_commercial_engine_approved",
                    "independent_qa_passed", "merge_authorized"):
            self.assertFalse(pack["acceptance"][key])

    def test_upstream_original_pointer_preserved_in_existing_candidate(self):
        pack = self._pack()
        self._assert_held_source(pack)
        self.assertEqual(safe_url(SOURCE), SOURCE)
        self.assertEqual(SEEDS["freightrecovery"].count(SOURCE), 1)
        self.assertTrue(pack["acceptance"]["main_only_pointer_reconciled_in_existing_draft_after_seed_update"])

    def test_five_synthetic_negative_controls_are_not_independent_truth(self):
        pack = self._pack()
        controls = pack["synthetic_negative_controls"]
        self.assertEqual(len(controls), 5)
        self.assertEqual(len({x["id"] for x in controls}), 5)
        self.assertTrue(all(x["kind"] == "SYNTHETIC"
                            and x["customer_ground_truth"] is None for x in controls))
        self.assertEqual({x["expected"] for x in controls}, {
            "REJECT_PAYMENT_PROOF_PROMOTION",
            "REJECT_RATE_ACCURACY_PROMOTION",
            "REJECT_HISTORICAL_SMALL_EXCEPTION_OVEREXTENSION",
            "REJECT_REAL_PARTY_IN_INTEREST_PROMOTION",
            "REJECT_UNSUPPORTED_MODERN_LEGAL_APPLICATION",
        })

    def test_mutated_rights_and_document_truth_are_rejected(self):
        pack = self._pack()
        self._assert_held_source(pack)
        cases = (
            ("source", "original_http_response_sha256", "unverified-fingerprint"),
            ("source", "original_http_response_bytes_acquired", True),
            ("source", "original_invoices_freight_bills_payment_vouchers_acquired", True),
            ("rights", "production_commercial_engine_use_authorized", True),
            ("rights", "third_party_material_permission_checked", True),
            ("historic_decision_facts", "unreceipted_carrier_freight_bill_alone_proves_payment", True),
            ("historic_decision_facts", "freight_bill_receipt_by_itself_proves_charges_correct", True),
            ("historic_decision_facts", "over_threshold_blanket_waiver_approved", True),
            ("historic_decision_facts", "case_rules_apply_to_modern_shipments", "YES"),
            ("cohort", "independent_held_out_real_customer_labeled_invoices", 1),
            ("cohort", "retally_customer_recovery_cents", 1),
            ("acceptance", "merge_authorized", True),
        )
        for section, key, value in cases:
            mutated = copy.deepcopy(pack)
            mutated[section][key] = value
            with self.subTest(section=section, key=key), self.assertRaises(AssertionError):
                self._assert_held_source(mutated)


if __name__ == "__main__":
    unittest.main()
