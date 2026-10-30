"""Review-only original-GAO B-148981 facts and false-positive gates.
No network, no customer files, no freight engine code, no cash assertions.
"""
import json
from pathlib import Path
import unittest

FIXTURE = Path(__file__).parent / "fixtures" / "gao_b148981_freight_adjudication_v1.json"


class GaoAshworthOriginalDecisionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = json.loads(FIXTURE.read_text(encoding="utf-8"))
        cls.by_id = {x["case_id"]: x for x in cls.d["case_groups"]}

    def test_original_publisher_provenance_and_reuse_limits(self):
        d = self.d
        self.assertEqual(d["schema_version"], 1)
        self.assertEqual(d["source"]["original_public_decision_url"], "https://www.gao.gov/products/b-148981")
        self.assertEqual(d["source"]["decision_date"], "1962-11-29")
        self.assertEqual(d["source"]["source_rights_url"], "https://www.gao.gov/copyright")
        for key in ("source_full_html_response_sha256", "source_original_invoice_bytes_sha256",
                    "source_tariff_bytes_sha256", "source_response_content_length_bytes"):
            self.assertIsNone(d["source"][key])
        self.assertFalse(d["source"]["issuer_http_response_custodied"])
        self.assertFalse(d["source"]["original_bol_or_payment_documents_custodied"])
        self.assertTrue(d["data_quality"]["no_person_identifiers_or_private_customer_records"])

    def test_exact_source_dollar_arithmetic_and_no_duplicate_groups(self):
        d = self.d
        groups = d["case_groups"]
        self.assertEqual(len(groups), 3)
        self.assertEqual(len(self.by_id), 3)
        self.assertEqual({g["carrier_bill_group"] for g in groups}, {"5188", "5193", "5190"})
        self.assertEqual(sum(g["shipment_count"] for g in groups), 7)
        self.assertEqual(sum(g["initial_audit_overcharge_cents"] for g in groups), 184200)
        for g in groups:
            self.assertEqual(sum(g["original_paid_components_cents"]), g["original_paid_cents"])
            self.assertTrue(g["carrier_refund_reported_by_gao"])
            self.assertFalse(g["credit_clearing_independently_proved"])
        self.assertEqual(self.by_id["B148981_BILL_5188"]["original_paid_cents"], 175500)
        self.assertEqual(self.by_id["B148981_BILL_5193"]["initial_audit_overcharge_cents"], 4602)
        self.assertEqual(self.by_id["B148981_BILL_5190"]["later_carrier_credit_authorized_cents"], 39174)

    def test_real_holdout_preserves_the_reversed_part_of_auditor_claim(self):
        a = self.by_id["B148981_BILL_5190"]
        self.assertEqual(a["split"], "holdout_within_single_publisher_decision")
        self.assertEqual(a["gao_decision"], "INITIAL_AUDIT_MODIFIED_CARRIER_CREDIT_AUTHORIZED")
        self.assertEqual(a["initial_audit_overcharge_cents"], 166154)
        self.assertNotEqual(a["later_carrier_credit_authorized_cents"], 0)
        self.assertFalse(a["credit_clearing_independently_proved"])
        for g in self.d["case_groups"][:2]:
            self.assertEqual(g["split"], "calibration")
            self.assertEqual(g["gao_decision"], "INITIAL_AUDIT_SUSTAINED")
        self.assertEqual(self.d["quality"]["within_source_holdout_groups"], 1)
        self.assertEqual(self.d["quality"]["publisher_decisions"], 1)
        self.assertIn("NOT_SEPARATE_INDEPENDENT_PUBLISHER", self.d["quality"]["split_independence"])

    def test_synthetic_negative_controls_fail_closed(self):
        expected = {
            "SYNTHETIC_REFUNDS_AS_RETALLY_CASH": "UNKNOWN_NO_RETALLY_CASH",
            "SYNTHETIC_5190_ORIGINAL_AUDIT_FINAL": "REJECT_GAO_MODIFIED_AUDIT",
            "SYNTHETIC_5190_CREDIT_PAID": "UNKNOWN_CREDIT_SETTLEMENT_NOT_VERIFIED",
            "SYNTHETIC_5193_TRIPLE_DECISION": "REJECT_GROUP_LEVEL_LABEL",
            "SYNTHETIC_MODERN_PRIVATE_TARIFF": "UNKNOWN_NO_PRESENT_DAY_RATE_AUTHORITY",
            "SYNTHETIC_GAO_REFUND_BANK_PROOF": "UNKNOWN_NO_INDEPENDENT_BANK_PROOF",
        }
        controls = self.d["synthetic_negative_controls"]
        self.assertEqual({c["id"]: c["expected"] for c in controls}, expected)
        self.assertTrue(all(c["provenance"] == "SYNTHETIC_NOT_A_REAL_SHIPMENT" and
                            c["independently_verified_customer_label"] is None for c in controls))

    def test_current_customer_accuracy_and_cash_are_unproved(self):
        q = self.d["quality"]
        self.assertEqual(q["modern_independent_positives"], 0)
        self.assertEqual(q["modern_independent_negatives"], 0)
        self.assertEqual(q["externally_linked_modern_invoice_tariff_payment_adjudications"], 0)
        self.assertEqual(q["bank_cleared_refunds_independently_authenticated"], 0)
        self.assertIsNone(q["modern_measured_freight_error_accuracy"])
        self.assertEqual(q["retally_recovered_cash_cents"], 0)
        self.assertFalse(self.d["product_release_authorized"])
        self.assertFalse(self.d["legacy_15_lab_consolidation_certified"])


if __name__ == "__main__":
    unittest.main()
