"""Source-bound CBCA 3467-RATE historical negative control; not live invoice truth."""
import copy
import json
import unittest
from pathlib import Path

SOURCE = Path(__file__).resolve().parent / "fixtures" / "cbca_3467_detention_negative_candidate_v0.json"

class CBCADetentionNegativeControlTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.item = json.loads(SOURCE.read_text(encoding="utf-8"))

    def test_original_publisher_case_and_truth_boundary(self):
        row = self.item
        self.assertEqual(row["schema_version"], "0.1.0")
        self.assertEqual(row["evaluation_families"], [
            "HISTORICAL_ADJUDICATED_FREIGHT_ERROR_NEGATIVE_CONTROL",
            "GENERAL_ACCOUNTING_CONFLICTING_SOURCE_AMOUNTS",
        ])
        s = row["source"]
        self.assertEqual(s["case_id"], "CBCA 3467-RATE")
        self.assertEqual(s["decision_date"], "2014-05-14")
        self.assertEqual(s["official_index_url"], "https://www.cbca.gov/decisions/rate.html")
        self.assertIn("cbca.gov/files/decisions/2014/", s["official_decision_url"])
        self.assertEqual(s["decision_pdf_zero_based_pages_consulted"], [0, 1, 2, 3, 4, 5])
        self.assertFalse(s["original_publisher_pdf_bytes_acquired"])
        self.assertIsNone(s["original_publisher_pdf_sha256"])
        self.assertFalse(s["original_carrier_invoice_bol_or_tariff_bytes_acquired"])
        self.assertEqual(s["governing_tender_effective_date"], "UNKNOWN")
        self.assertFalse(s["commercial_customer_engine_source_use_approved"])
        self.assertFalse(s["government_endorsement_asserted"])
        q = row["truth_boundaries"]
        self.assertEqual(q["adjudicated_decision_case_count"], 1)
        self.assertEqual(q["independent_heldout_customer_invoice_error_labels"], 0)
        self.assertIsNone(q["modern_customer_overcharge_ground_truth_cents"])
        self.assertFalse(q["commercial_scoring_admission"])
        self.assertEqual(q["final_customer_or_carrier_bank_outcome"], "UNKNOWN")
        self.assertEqual(row["historical_adjudication"]["retally_verified_recovered_cash_cents"], 0)

    def test_79_payments_70_false_assertions_and_two_cent_conflict(self):
        h = self.item["historical_adjudication"]
        self.assertEqual((h["reported_shipments_2010"], h["reported_shipments_2011"]), (4, 75))
        self.assertEqual(h["reported_paid_detention_shipment_total"], 79)
        self.assertEqual(h["reported_shipments_2010"] + h["reported_shipments_2011"], 79)
        self.assertEqual(h["gsa_initially_treated_as_authorized_count"], 9)
        self.assertEqual(h["gsa_postpayment_overcharge_notices_disputed_count"], 70)
        self.assertEqual(h["gsa_initially_treated_as_authorized_count"] +
                         h["gsa_postpayment_overcharge_notices_disputed_count"], 79)
        self.assertTrue(h["initial_payment_by_gsa_reported"])
        self.assertTrue(h["carrier_claim_held_valid_by_board"])
        self.assertTrue(h["gsa_overcharge_notices_held_invalid"])
        self.assertEqual(h["gsa_claimed_repayment_body_cents"], 33989573)
        self.assertEqual(h["gsa_claimed_repayment_disposition_cents"], 33989575)
        self.assertEqual(abs(h["gsa_claimed_repayment_body_cents"] -
                             h["gsa_claimed_repayment_disposition_cents"]), 2)
        self.assertEqual(h["conflicting_quoted_cents_difference"], 2)
        for field in ("post_disposition_carrier_refund_received_cents",
                      "gsa_recoupment_from_carrier_actually_collected_cents",
                      "actual_recoveryos_cleared_bank_receipt_cents"):
            self.assertIsNone(h[field])

    def test_synthetic_controls_reject_claim_promotion_and_mutations(self):
        row = self.item
        controls = row["synthetic_negative_controls"]
        self.assertEqual(len(controls), 5)
        self.assertEqual(len(set(c["id"] for c in controls)), 5)
        self.assertTrue(all(c["kind"] == "SYNTHETIC" and
                            c["id"].startswith("SYNTH_") and
                            c["expected"].startswith("REJECT_") for c in controls))
        pinned = [
            ("source", "original_publisher_pdf_bytes_acquired", False),
            ("source", "original_publisher_pdf_sha256", None),
            ("source", "commercial_customer_engine_source_use_approved", False),
            ("historical_adjudication", "gsa_overcharge_notices_held_invalid", True),
            ("historical_adjudication", "gsa_claimed_repayment_body_cents", 33989573),
            ("historical_adjudication", "gsa_claimed_repayment_disposition_cents", 33989575),
            ("historical_adjudication", "post_disposition_carrier_refund_received_cents", None),
            ("historical_adjudication", "retally_verified_recovered_cash_cents", 0),
            ("truth_boundaries", "adjudicated_decision_case_count", 1),
            ("truth_boundaries", "independent_heldout_customer_invoice_error_labels", 0),
            ("truth_boundaries", "modern_customer_overcharge_ground_truth_cents", None),
            ("truth_boundaries", "commercial_scoring_admission", False),
        ]
        def guard(candidate):
            for section, field, expected in pinned:
                observed = candidate[section][field]
                self.assertIs(type(observed), type(expected))
                self.assertEqual(observed, expected)
            a = candidate["historical_adjudication"]
            self.assertEqual(abs(a["gsa_claimed_repayment_body_cents"] -
                                 a["gsa_claimed_repayment_disposition_cents"]), 2)
        guard(row)
        for section, field, expected in pinned:
            with self.subTest(section=section, field=field):
                poison = copy.deepcopy(row)
                poison[section][field] = (
                    not expected if isinstance(expected, bool)
                    else "FAKE_SOURCE_BYTES_OR_CASH" if expected is None
                    else expected + 1
                )
                with self.assertRaises(AssertionError):
                    guard(poison)

if __name__ == "__main__":
    unittest.main()
