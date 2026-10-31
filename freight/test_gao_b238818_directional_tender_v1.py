"""Source-bound GAO B-238818 directional rate holdout; no live source or engine writes."""
import copy
import json
import unittest
from pathlib import Path

PACK = Path(__file__).parent / "fixtures" / "gao_b238818_directional_tender_holdout_v1.json"


def route_matches_tender(case, tender_prefix):
    return (case["actual_origin"] == case[tender_prefix + "_authorized_origin"]
            and case["actual_destination"] == case[tender_prefix + "_authorized_destination"])


class GAOB238818DirectionalTenderEvidence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p = json.loads(PACK.read_text(encoding="utf-8"))

    def test_original_publisher_rights_and_unknown_byte_provenance(self):
        p = self.p
        s = p["source"]
        self.assertEqual(p["schema_version"], 1)
        self.assertEqual(s["decision_id"], "B-238818")
        self.assertEqual(s["official_decision_url"], "https://www.gao.gov/products/b-238818")
        self.assertEqual(s["decision_date"], "1991-02-20")
        self.assertEqual(s["rights_url"], "https://www.gao.gov/copyright")
        self.assertIn("NO_ENDORSEMENT", s["rights"])
        self.assertIsNone(s["publisher_full_response_sha256"])
        self.assertIsNone(s["publisher_full_response_byte_length"])
        self.assertFalse(s["publisher_original_bytes_custodied"])
        self.assertFalse(s["original_GBL_or_tender63_or_tender85_bytes_custodied"])
        self.assertEqual(s["third_party_carrier_rate_tender_rights"], "UNKNOWN_NOT_CLEARED")

    def test_adjudicated_directional_tender_and_historical_money_label(self):
        c = self.p["original_adjudicated_case"]
        self.assertEqual(c["government_bill_of_lading"], "C-1,531,302")
        self.assertEqual((c["actual_origin"], c["actual_destination"]), ("Maryland", "California"))
        self.assertEqual((c["wrong_billed_tender_id"], c["adjudicated_applicable_tender_id"]), ("63", "85"))
        self.assertFalse(route_matches_tender(c, "wrong_tender"))
        self.assertTrue(route_matches_tender(c, "applicable_tender"))
        self.assertEqual(c["overcharge_cents"], 166140)
        self.assertIsNone(c["interest_cents"])
        self.assertFalse(c["GBL_identified_a_rate_tender"])
        self.assertFalse(c["GAO_accepted_oral_advice_as_authority"])
        self.assertEqual(c["GAO_final_holding"], "GSA_DIRECTIONAL_RATE_OVERCHARGE_ASSESSMENT_SUSTAINED")
        self.assertTrue(c["GAO_reported_GSA_deduction_collected"])
        self.assertFalse(c["independent_bank_clearing_proof"])

    def test_direction_flip_and_missing_tender_are_red_controls(self):
        c = self.p["original_adjudicated_case"]
        reversed_route = copy.deepcopy(c)
        reversed_route["actual_origin"], reversed_route["actual_destination"] = (
            reversed_route["actual_destination"], reversed_route["actual_origin"])
        self.assertFalse(route_matches_tender(reversed_route, "applicable_tender"))
        self.assertTrue(route_matches_tender(reversed_route, "wrong_tender"))
        tampered = copy.deepcopy(c)
        tampered["adjudicated_applicable_tender_id"] = tampered["wrong_billed_tender_id"]
        self.assertNotEqual(tampered["adjudicated_applicable_tender_id"], "85")

    def test_synthetic_negatives_and_unknowns_do_not_become_real_labels(self):
        controls = self.p["synthetic_negative_controls"]
        self.assertEqual(len(controls), 6)
        self.assertEqual(len({x["id"] for x in controls}), len(controls))
        self.assertTrue(all(x["id"].startswith("SYNTHETIC_")
                            and x["kind"] == "SYNTHETIC_NOT_REAL_SHIPMENT"
                            and x["independent_real_customer_label"] is None
                            for x in controls))
        expected = {x["expected"] for x in controls}
        self.assertIn("UNKNOWN_INTEREST_AMOUNT", expected)
        self.assertIn("REJECT_GOVERNMENT_DEDUCTION_AS_CUSTOMER_CASH", expected)
        self.assertIn("UNKNOWN_NO_SEPARATE_ORIGINAL_TENDER_BYTES", expected)
        self.assertIn("ORIGINAL_TENDER_63_85_BYTES", self.p["heldout"]["unknowns"])

    def test_holdout_and_cash_boundaries_are_fail_closed(self):
        q = self.p["heldout"]
        c = self.p["original_adjudicated_case"]
        self.assertEqual(q["GAO_publisher_decisions"], 1)
        self.assertEqual(q["independently_adjudicated_historical_decision_labels"], 1)
        self.assertEqual(q["separately_custodied_original_GBL_tender_invoice_triplets"], 0)
        self.assertTrue(q["distinct_independent_decision_not_independent_publisher"])
        self.assertEqual(q["real_customer_truth_cases"], 0)
        self.assertEqual(q["engine_predictions_compared_against_this_holdout"], 0)
        self.assertIsNone(q["freight_error_precision"])
        self.assertIsNone(q["modern_customer_accuracy"])
        self.assertEqual(c["RETALLY_customer_recovery_cents"], 0)
        self.assertEqual(q["recovered_customer_cash_cents"], 0)
        self.assertFalse(self.p["restrictions"]["legacy_15_lab_consolidation_certified"])
        self.assertFalse(self.p["restrictions"]["production_release_allowed"])


if __name__ == "__main__":
    unittest.main()
