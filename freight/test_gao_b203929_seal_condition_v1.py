"""GAO B-203929.2 original reversal: exclusive use never silently waives sealing precondition."""
import json
import unittest
from pathlib import Path

PACK = Path(__file__).parent / "fixtures" / "gao_b203929_seal_precondition_reversed_holdout_v1.json"


def classify_historical_tender(facts):
    """Research-only guard for THIS GAO adjudication; never an engine rate calculation."""
    if facts.get("decision_id") != "B-203929.2":
        return "UNKNOWN_DIFFERENT_DECISION"
    if facts.get("tender") != "266":
        return "UNKNOWN_DIFFERENT_TENDER"
    if facts.get("mandatory_seals") is None:
        return "UNKNOWN_TENDER_TERMS"
    if facts.get("shipper_sealed") is None:
        return "UNKNOWN_MISSING_SEAL_FACT"
    if facts["mandatory_seals"] and not facts["shipper_sealed"]:
        return "TENDER_NOT_APPLICABLE_GAO_REVERSED"
    return "UNKNOWN_OTHER_TENDER_CONDITIONS"


def guard_unfounded_claim(claim):
    return {
        "HISTORIC_DEDUCTION_AMOUNT_EQUALS_ZERO": "UNKNOWN_AMOUNT_NOT_ZERO",
        "RETALLY_REAL_CUSTOMER_RECOVERY": "REJECT_NOT_CUSTOMER_BANK_CASH",
        "THREE_PDF_PAGES_ARE_THREE_INDEPENDENT_INVOICES": "REJECT_DUPLICATE_DECISION",
    }.get(claim, "UNKNOWN_UNSUPPORTED_CLAIM")


class GAOB203929SealConditionHoldout(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pack = json.loads(PACK.read_text(encoding="utf-8"))

    def test_official_original_rights_and_source_hash_limits(self):
        p, s = self.pack, self.pack["original_source"]
        self.assertEqual(p["schema_version"], 1)
        self.assertEqual(s["decision_id"], "B-203929.2")
        self.assertEqual(s["decision_date"], "1982-04-09")
        self.assertEqual(s["original_publisher_pdf_url"], "https://www.gao.gov/assets/b-203929.2.pdf")
        self.assertEqual(s["rights_url"], "https://www.gao.gov/copyright")
        self.assertIn("NO_ENDORSEMENT", s["rights"])
        self.assertEqual(s["original_pdf_pages"], 3)
        self.assertEqual(s["official_pdf_pages_visually_reviewed"], [1, 2, 3])
        self.assertIsNone(s["original_pdf_response_sha256"])
        self.assertIsNone(s["original_pdf_response_bytes"])
        self.assertFalse(s["original_pdf_http_bytes_custodied"])
        self.assertFalse(s["original_bill_of_lading_or_invoice_bytes_custodied"])
        self.assertEqual(s["third_party_tender_and_original_invoice_rights"], "UNKNOWN_NOT_CLEARED")

    def test_one_adjudicated_negative_not_numeric_recovery(self):
        d = self.pack["original_decision"]
        self.assertTrue(d["exclusive_use_requested_and_furnished"])
        self.assertFalse(d["shipper_numbered_seals_applied"])
        self.assertEqual(d["mandatory_tender_item"], "179")
        self.assertEqual(d["optional_exclusive_use_item"], "130")
        self.assertEqual(d["referenced_tender"], "AFL Tender 266")
        self.assertFalse(d["optional_exclusive_use_seal_clause_overrides_mandatory_tender_condition"])
        self.assertEqual(d["GAO_outcome"], "GSA_AUDIT_DEDUCTION_REVERSED")
        self.assertIsNone(d["adjudicated_amount_cents"])
        self.assertIsNone(d["exact_rate_difference_cents"])
        self.assertFalse(d["historic_settlement_banking_verified"])
        self.assertEqual(d["actual_RETALLY_customer_recovery_cents"], 0)
        self.assertEqual(self.pack["original_source"]["original_decision_label_count"], 1)

    def test_original_contrast_one_reversed_one_upheld_not_accuracy(self):
        c, h = self.pack["independent_contrast"], self.pack["heldout"]
        self.assertEqual(c["decision_id"], "B-192872")
        self.assertEqual(c["GAO_outcome"], "GSA_OVERCHARGE_DEDUCTION_UPHELD")
        self.assertIn("HIGHLIGHTS_ONLY", c["source_scope"])
        self.assertEqual(h["distinct_original_decisions"], 2)
        self.assertEqual(h["source_publisher_count"], 1)
        self.assertEqual(h["original_per_shipment_paid_invoice_and_tariff_triplets"], 0)
        self.assertEqual(h["product_predictions_recorded"], 0)
        self.assertEqual(h["modern_customer_heldout_cases"], 0)
        self.assertIsNone(h["independent_real_world_error_precision"])
        self.assertIsNone(h["independent_real_world_error_recall"])
        self.assertEqual(h["naive_always_sustain_GSA_errors_in_two_original_decisions"], 1)
        self.assertTrue(h["one_reversed_one_upheld"])

    def test_ten_synthetic_controls_and_missing_label_fail_closed(self):
        controls = self.pack["synthetic_negative_controls"]
        self.assertEqual(len(controls), 10)
        self.assertEqual(len({x["id"] for x in controls}), 10)
        self.assertEqual(sum(x["split"] == "synthetic_heldout" for x in controls), 8)
        for control in controls:
            with self.subTest(control=control["id"]):
                self.assertTrue(control["id"].startswith("SYNTH_"))
                self.assertEqual(control["kind"], "SYNTHETIC_NOT_ORIGINAL_GAO_SHIPMENT")
                self.assertIsNone(control["independent_real_customer_label"])
                if "facts" in control:
                    result = classify_historical_tender(control["facts"])
                else:
                    result = guard_unfounded_claim(control["candidate_claim"])
                self.assertEqual(result, control["expected"])

    def test_naive_red_guard_green_for_exact_historical_facts(self):
        d = self.pack["original_decision"]
        naive_applies = d["exclusive_use_requested_and_furnished"] and d["referenced_tender"] == "AFL Tender 266"
        self.assertTrue(naive_applies)
        self.assertEqual(d["GAO_outcome"], "GSA_AUDIT_DEDUCTION_REVERSED")
        expected = "TENDER_NOT_APPLICABLE_GAO_REVERSED"
        guarded = classify_historical_tender({
            "decision_id": "B-203929.2", "tender": "266",
            "mandatory_seals": True, "shipper_sealed": False,
            "exclusive_use": True,
        })
        self.assertEqual(guarded, expected)
        self.assertNotEqual("TENDER_APPLIES" if naive_applies else "TENDER_NOT_APPLICABLE", expected)

    def test_dedup_and_research_only_handoffs(self):
        p = self.pack
        self.assertEqual(p["dedup"]["key"], "GAO/B-203929.2")
        self.assertEqual(p["dedup"]["contrast_key"], "GAO/B-192872")
        self.assertTrue(p["dedup"]["never_count_pdf_pages_as_cases"])
        self.assertTrue(p["dedup"]["never_count_synthetic_negative_controls_as_real_labels"])
        self.assertFalse(p["restrictions"]["engine_code_changed"])
        self.assertFalse(p["restrictions"]["writer_branch_changed"])
        self.assertFalse(p["restrictions"]["release_approved"])
        self.assertFalse(p["restrictions"]["commercial_scoring_approved"])
        self.assertFalse(p["ownership"]["legacy_15_lab_consolidation_proved"])
        self.assertIn("qa_44", p["downstream_handoffs"])


if __name__ == "__main__":
    unittest.main()
