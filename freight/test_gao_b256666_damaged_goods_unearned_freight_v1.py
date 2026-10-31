"""GAO B-256666 historical freight-damage deduction cause, separate from rate errors."""
import json
from pathlib import Path
import unittest

PACK = Path(__file__).parent / "fixtures" / "gao_b256666_damaged_goods_unearned_freight_v1.json"

def guard_claim(claim, *, has_gao_adjudication=True, duplicate=False):
    if duplicate:
        return "REJECT_DUPLICATE_DECISION"
    if not has_gao_adjudication:
        return "UNKNOWN_NO_ADJUDICATION"
    if claim in ("TARIFF_RATE_ERROR", "MERE_DAMAGE_IS_TARIFF_ERROR"):
        return "REJECT_WRONG_CAUSE"
    return {
        "BANK_CLEARED_CASH": "UNKNOWN_NO_BANK_PROOF",
        "RETALLY_CUSTOMER_RECOVERY": "UNKNOWN_NO_CUSTOMER_CASE",
        "ORIGINAL_INVOICE_CUSTODIED": "UNKNOWN_NO_ORIGINAL_BYTES",
        "CURRENT_2026_REGULATORY_ENTITLEMENT": "UNKNOWN_HISTORICAL_SCOPE",
        "TWO_INDEPENDENT_DECISIONS_FROM_DUPLICATE": "REJECT_DUPLICATE_DECISION",
        "DEFINITIVE_UNEARNED_FREIGHT_WITHOUT_GAO_FINDING": "UNKNOWN_NO_ADJUDICATION",
    }.get(claim, "UNKNOWN_UNSUPPORTED_CLAIM")

class GAOB256666DamagedGoodsScope(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pack = json.loads(PACK.read_text(encoding="utf-8"))

    def test_original_publisher_rights_and_document_custody_bounds(self):
        p = self.pack
        self.assertEqual(p["schema_version"], 1)
        self.assertEqual(p["source"]["decision_id"], "B-256666")
        self.assertEqual(p["source"]["published_at"], "1994-12-08")
        self.assertEqual(p["source"]["original_decision_url"], "https://www.gao.gov/products/b-256666")
        self.assertEqual(p["source"]["rights_url"], "https://www.gao.gov/copyright")
        self.assertIn("NO_ENDORSEMENT", p["source"]["rights"])
        self.assertIsNone(p["source"]["source_document_response_sha256"])
        self.assertIsNone(p["source"]["source_document_response_length_bytes"])
        self.assertFalse(p["source"]["source_original_http_bytes_custodied"])
        self.assertFalse(p["source"]["original_GBL_or_invoice_or_carrier_tender_bytes_custodied"])
        self.assertFalse(p["source"]["shipper_or_service_member_PII_copied"])

    def test_adjudicated_deduction_not_rate_error_or_settled_customer_cash(self):
        a = self.pack["adjudication"]
        self.assertEqual(a["canonical_case_key"], "GAO/B-256666")
        self.assertEqual(a["amount_freight_charges_setoff_cents"], 9653)
        self.assertEqual(a["finding"], "GAO_AFFIRMED_DFAS_RECOUPMENT_BY_SETOFF_OF_9653_CENTS")
        self.assertEqual(a["adjudicated_charge_cause"], "DAMAGE_RELATED_UNEARNED_FREIGHT_NOT_RATE_OR_TARIFF_MISAPPLICATION")
        self.assertFalse(a["rate_table_or_directional_tender_overcharge_proved"])
        self.assertIsNone(a["amount_independent_customer_bank_clearing_cents"])
        self.assertIsNone(a["amount_independently_settled_customer_recovery_cents"])
        self.assertEqual(len(a["proof_missing"]), 6)

    def test_two_real_decisions_one_publisher_no_modern_benchmark(self):
        x = self.pack["contrast"]
        self.assertEqual(x["comparison_source_id"], "GAO/B-238818")
        self.assertEqual(x["comparison_1991_rate_overcharge_cents"], 166140)
        self.assertNotEqual(x["this_decision_cause"], x["comparison_cause"])
        self.assertEqual(x["independent_decision_level_historical_labels"], 2)
        self.assertEqual(x["distinct_original_publishers"], 1)
        self.assertEqual(x["naive_all_setoffs_equal_rate_overcharge_wrong_causes_in_pair"], 1)
        self.assertEqual(x["product_engine_predictions_executed"], 0)
        self.assertEqual(x["independent_modern_heldout_samples"], 0)
        self.assertIsNone(x["real_customer_precision"])
        self.assertIsNone(x["real_customer_recall"])

    def test_eight_explicit_synthetic_adversarial_guards(self):
        controls = self.pack["synthetic_controls"]
        self.assertEqual(len(controls), 8)
        self.assertEqual(len({c["id"] for c in controls}), 8)
        self.assertEqual(sum(c["split"] == "synthetic_holdout" for c in controls), 5)
        for c in controls:
            with self.subTest(c=c["id"]):
                self.assertTrue(c["id"].startswith("SYNTH_"))
                self.assertEqual(c["kind"], "SYNTHETIC_NOT_REAL_SHIPMENT")
                self.assertIsNone(c["independent_real_label"])
                self.assertEqual(
                    guard_claim(c["candidate_claim"],
                                has_gao_adjudication=c["candidate_claim"] != "DEFINITIVE_UNEARNED_FREIGHT_WITHOUT_GAO_FINDING",
                                duplicate=c["candidate_claim"] == "TWO_INDEPENDENT_DECISIONS_FROM_DUPLICATE"),
                    c["expected"])

    def test_naive_red_guard_green_without_real_engine_inference(self):
        # Naive baseline: all positive governmental setoffs counted as tender-rate errors.
        a = self.pack["adjudication"]
        naive_rate_error = a["amount_freight_charges_setoff_cents"] > 0
        self.assertTrue(naive_rate_error)  # deliberately wrong cause for this case
        self.assertFalse(a["rate_table_or_directional_tender_overcharge_proved"])
        self.assertEqual(guard_claim("TARIFF_RATE_ERROR"), "REJECT_WRONG_CAUSE")
        self.assertFalse(self.pack["restrictions"]["release_authorized"])
        self.assertFalse(self.pack["restrictions"]["legacy_15_lab_consolidation_certified"])

if __name__ == "__main__":
    unittest.main()
