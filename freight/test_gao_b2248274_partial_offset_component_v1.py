"""GAO B-224827.4: one real agency decision, synthetic guards, no modern cash truth."""
import json
import unittest
from pathlib import Path

PACK = Path(__file__).parent / "fixtures" / "gao_b2248274_partial_offset_component_v1.json"


def guarded_claim(claim, facts):
    if claim == "FULL_GOVERNMENT_OFFSET_IS_CARRIER_REFUND":
        return "REJECT" if facts["government_collected_offset_cents"] != facts["carrier_refund_awarded_cents"] else "UNKNOWN"
    if claim == "MEMBER_INITIAL_PAYMENT_CAPS_CARRIER_LIABILITY":
        return "REJECT" if facts["carrier_liability_offset_cents"] > facts["member_initial_payment_cents"] else "UNKNOWN"
    if claim == "CLAIM_AWARD_COMPONENTS_SUM_TO_INCORRECT_CENTS":
        return "REJECT" if facts["additional_valuation_cents"] + facts["recovered_items_freight_cents"] != facts["proposed_total_cents"] else "UNKNOWN"
    if claim == "DAMAGE_LIABILITY_PROVES_FREIGHT_TARIFF_OVERCHARGE":
        return "REJECT" if facts["source_cause"] == "DAMAGE_AND_LOSS" and not facts["controlling_modern_tariff_verified"] else "UNKNOWN"
    if claim == "REFUND_AWARD_EQUALS_CASH_RECEIVED":
        return "UNKNOWN" if facts["bank_receipt_cents"] is None else "REVIEW_REQUIRED"
    if claim == "GBL_VALUATION_CHARGE_IS_SAME_AS_ADDITIONAL_AWARD":
        return "REJECT" if facts["valuation_charge_on_gbl_cents"] != facts["additional_valuation_cents"] else "UNKNOWN"
    if claim == "TWO_MEMBER_PAYMENTS_ARE_TWO_INDEPENDENT_FREIGHT_CASES":
        return "REJECT" if facts["distinct_decisions"] < facts["member_payment_events"] else "UNKNOWN"
    if claim == "HISTORICAL_OFFSET_HOLDING_APPLIES_TO_ALL_CURRENT_CARRIERS":
        return "UNKNOWN" if not facts["current_contract_verified"] else "REVIEW_REQUIRED"
    if claim == "GOVERNMENT_CARRIER_CASE_PROVES_RETALLY_CASH":
        return "REJECT" if facts["real_customer_receipts"] == 0 else "UNKNOWN"
    if claim == "CARRIER_COMPONENT_ENTITLEMENT_IS_FREIGHT_RATE_OVERCHARGE":
        return "REJECT" if not facts["original_invoice_rate_error_independent_label"] else "UNKNOWN"
    raise AssertionError("Unexpected claim type")


class AgencyCaseReconciliation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = json.loads(PACK.read_text(encoding="utf-8"))

    def test_original_first_party_source_and_rights(self):
        d = self.doc
        self.assertEqual(d["schema_version"], 1)
        self.assertEqual(d["original_source"]["decision_id"], "B-224827.4")
        self.assertEqual(d["original_source"]["url"], "https://www.gao.gov/products/b-224827.4-0")
        self.assertEqual(d["rights"]["publisher_policy"], "https://www.gao.gov/copyright")
        self.assertIsNone(d["original_source"]["original_http_body_sha256"])
        self.assertFalse(d["original_source"]["official_publisher_original_response_custodied"])
        self.assertFalse(d["rights"]["customer_reuse_or_production_scoring_authorized"])
        self.assertFalse(d["ownership"]["legacy_15_labs_consolidated"])

    def test_real_publisher_components_and_exact_cents(self):
        f = self.doc["published_historical_case_facts"]
        self.assertEqual(f["government_member_initial_paid_cents"] + f["government_member_additional_reimbursement_cents"], 1_200_000)
        self.assertEqual(f["government_collected_damage_offset_cents"], 1_200_000)
        self.assertEqual(f["carrier_additional_unbilled_valuation_awarded_cents"] + f["carrier_freight_on_recovered_items_awarded_cents"], 9_487)
        self.assertEqual(f["carrier_total_refund_awarded_cents"], 9_487)
        self.assertEqual(f["carrier_GBL_released_valuation_charge_cents"], 6_000)
        self.assertIsNone(f["carrier_total_refund_later_paid_cents"])

    def test_red_naive_full_offset_vs_green_component_ledger(self):
        b = self.doc["benchmark_readiness"]
        f = self.doc["published_historical_case_facts"]
        # RED: wrongly conflates damage setoff of $12,000 with carrier refund.
        self.assertEqual(b["unsafe_baseline_full_offset_as_refund_cents"], 1_200_000)
        self.assertNotEqual(b["unsafe_baseline_full_offset_as_refund_cents"], f["carrier_total_refund_awarded_cents"])
        # GREEN: two separate amounts awarded total $94.87; paid is unknown.
        self.assertEqual(b["guarded_awarded_refund_cents"], f["carrier_total_refund_awarded_cents"])
        self.assertIsNone(b["observed_actual_refund_paid_cents"])
        self.assertEqual(f["verified_2026_customer_cash_cents"], 0)

    def test_synthetic_holdouts_are_distinct_and_ground_truth_unknown(self):
        c = self.doc["synthetic_controls"]
        self.assertEqual(len(c), 10)
        self.assertEqual(len({v["id"] for v in c}), 10)
        self.assertEqual(sum(v["split"] == "synthetic_calibration" for v in c), 4)
        self.assertEqual(sum(v["split"] == "synthetic_holdout" for v in c), 6)
        for v in c:
            self.assertTrue(v["id"].startswith("SYN_"))
            self.assertIsNone(v["independent_real_label"])
            self.assertEqual(guarded_claim(v["claim"], v["facts"]), v["expected_guard"])

    def test_independent_historical_case_not_modern_accuracy(self):
        b = self.doc["benchmark_readiness"]
        self.assertEqual(b["independently_adjudicated_historical_government_decisions"], 1)
        for k in ("independent_modern_freight_rate_positive_labels",
                  "independent_modern_freight_rate_clean_negative_labels",
                  "heldout_real_2026_customer_cases", "production_model_predictions"):
            self.assertEqual(b[k], 0)
        for k in ("measured_accuracy", "precision", "recall"):
            self.assertIsNone(b[k])
        self.assertEqual(self.doc["published_historical_case_facts"]["tariff_or_invoice_overcharge_ground_truth"],
                         "UNKNOWN_NOT_AN_ADJUDICATED_RATE_ERROR")

    def test_handoffs_and_scope_safety(self):
        self.assertEqual(set(self.doc["consumers"]),
                         {"retally_recoveryos_12", "freightrecovery_12", "permitplate_48",
                          "capturebrief_52", "independent_qa_44", "executive_director"})
        self.assertEqual(self.doc["safety"]["private_records_persisted"], 0)
        self.assertEqual(self.doc["safety"]["new_provider_calls_in_workflow"], 0)
        self.assertFalse(self.doc["safety"]["release_bypass"])


if __name__ == "__main__":
    unittest.main()
