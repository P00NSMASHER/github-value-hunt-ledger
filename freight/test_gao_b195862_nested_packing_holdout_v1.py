"""Research-only original GAO B-195862 holdout: GBL notation is not packaging proof."""
import json
import unittest
from pathlib import Path

PACK = Path(__file__).parent / "fixtures" / "gao_b195862_nested_packing_evidence_holdout_v1.json"


def classify_historical_evidence(f):
    """Decision-bound evidence guard only; NOT a freight pricing or recovery engine."""
    if f.get("decision_id") != "B-195862":
        return "UNKNOWN_OTHER_DECISION"
    if f.get("same_date_and_shipment") is False:
        return "UNKNOWN_CONFLICTING_SHIPMENT_IDENTITY"
    if any(f.get(k) is None for k in (
        "signed_commercial_bol_nested", "same_date_and_shipment",
        "one_third_space_reduction_photos",
    )):
        return "UNKNOWN_CORROBORATION_MISSING"
    if (f["same_date_and_shipment"] and f["signed_commercial_bol_nested"]
            and f["one_third_space_reduction_photos"]):
        return "HISTORICAL_NESTED_RATE_SUPPORTED_ONLY"
    return "UNKNOWN_CORROBORATION_CONFLICT"


def guard_claim(claim):
    return {
        "HISTORIC_OVERCHARGE_AMOUNT_IS_ZERO": "UNKNOWN_AMOUNT_NOT_ZERO",
        "GAO_SETTLEMENT_EQUALS_RETALLY_CASH": "REJECT_NO_REAL_CUSTOMER_CASH",
        "FULL_REPORT_PAGES_ARE_INDEPENDENT_CASES": "REJECT_DUPLICATE_DECISION",
    }.get(claim, "UNKNOWN_UNSUPPORTED_CLAIM")


class GAOB195862NestedPackingHoldout(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p = json.loads(PACK.read_text(encoding="utf-8"))

    def test_official_source_rights_and_unverified_original_bytes(self):
        s = self.p["original_source"]
        self.assertEqual(self.p["schema_version"], 1)
        self.assertEqual(s["decision_id"], "B-195862")
        self.assertEqual(s["decision_date"], "1980-02-07")
        self.assertEqual(s["original_highlights_url"], "https://www.gao.gov/products/b-195862")
        self.assertEqual(s["rights_url"], "https://www.gao.gov/copyright")
        self.assertIn("NO_IMPLIED_ENDORSEMENT", s["rights"])
        self.assertEqual(s["third_party_document_rights"], "UNKNOWN_NOT_CLEARED")
        self.assertFalse(s["source_bytes_custodied"])
        self.assertIsNone(s["source_content_sha256"])
        self.assertFalse(s["original_document_full_report_reviewed"])
        self.assertEqual(s["original_shipment_or_invoice_documents_custodied"], 0)
        self.assertEqual(s["carrier_tariff_effective_date"], "UNKNOWN")

    def test_one_real_decision_label_not_invoice_or_cash_benchmark(self):
        d, s, b = self.p["adjudicated_case"], self.p["original_source"], self.p["benchmark"]
        self.assertEqual(d["outcome"], "GSA_OVERCHARGE_DEDUCTION_SUSTAINED")
        self.assertEqual(d["shipment_piece_count_notation"], 25)
        self.assertFalse(d["gov_bill_of_lading_alone_conclusively_proves_loose"])
        self.assertTrue(d["same_day_signed_commercial_bol_describes_nested_packages"])
        self.assertTrue(d["GSA_photos_show_at_least_one_third_space_reduction"])
        self.assertTrue(d["GAO_found_original_GSA_initial_packaging_evidence_insufficient"])
        self.assertEqual(s["original_labeled_decision_count"], 1)
        for name in ("original_deduction_amount_cents", "corrected_tariff_rate_cents",
                     "paid_invoice_amount_cents"):
            self.assertIsNone(d[name])
        self.assertEqual(d["actual_retally_customer_recovery_cents"], 0)
        self.assertEqual(b["original_shipments_with_full_rate_triplet"], 0)
        self.assertEqual(b["engine_predictions_recorded"], 0)
        self.assertEqual(b["present_day_customer_labeled_cases"], 0)
        self.assertIsNone(b["precision"])
        self.assertIsNone(b["recall"])

    def test_ten_synthetic_negative_controls_with_unknowns(self):
        c = self.p["synthetic_controls"]
        self.assertEqual(len(c), 10)
        self.assertEqual(len({v["id"] for v in c}), len(c))
        self.assertGreaterEqual(sum(v["split"] == "synthetic_heldout" for v in c), 7)
        for row in c:
            with self.subTest(id=row["id"]):
                self.assertTrue(row["id"].startswith("SYN_"))
                self.assertEqual(row["provenance"], "RESEARCH_AUTHORED_SYNTHETIC_NOT_ORIGINAL_SHIPMENT")
                self.assertIsNone(row["independent_real_customer_label"])
                got = (guard_claim(row["candidate_claim"]) if "candidate_claim" in row
                       else classify_historical_evidence(row["facts"]))
                self.assertEqual(got, row["expected"])

    def test_targeted_red_naive_gbl_and_green_multi_document_guard(self):
        d = self.p["adjudicated_case"]
        # RED baseline: the literal government BOL "25 ea." is not proof of loose freight.
        naive = "LOOSE_RATE_SUPPORTED" if d["shipment_piece_count_notation"] == 25 else "UNKNOWN"
        self.assertEqual(naive, "LOOSE_RATE_SUPPORTED")
        self.assertNotEqual(naive, "HISTORICAL_NESTED_RATE_SUPPORTED_ONLY")
        facts = {
            "decision_id": d["decision_id"], "gbl_piece_count": 25,
            "signed_commercial_bol_nested": d["same_day_signed_commercial_bol_describes_nested_packages"],
            "same_date_and_shipment": True,
            "one_third_space_reduction_photos": d["GSA_photos_show_at_least_one_third_space_reduction"],
        }
        self.assertEqual(classify_historical_evidence(facts), "HISTORICAL_NESTED_RATE_SUPPORTED_ONLY")
        # Input-mutation sensitivity: missing each corroborating fact MUST fail closed.
        for missing in ("signed_commercial_bol_nested", "same_date_and_shipment",
                        "one_third_space_reduction_photos"):
            with self.subTest(missing=missing):
                self.assertEqual(classify_historical_evidence({**facts, missing: None}),
                                 "UNKNOWN_CORROBORATION_MISSING")

    def test_original_independent_counterexample_not_inflated_accuracy(self):
        c, b = self.p["independent_original_contrast"], self.p["benchmark"]
        self.assertEqual(c["decision_id"], "B-203929.2")
        self.assertEqual(c["outcome"], "GSA_AUDIT_DEDUCTION_REVERSED")
        self.assertEqual(b["real_original_decision_labels"], 2)
        self.assertEqual(b["independent_publishers"], 1)
        self.assertEqual(b["naive_always_sustain_gsa_errors_in_two_original_decisions"], 1)
        self.assertEqual(b["naive_government_bol_25_each_means_loose_errors_in_primary_decision"], 1)
        self.assertIn("NOT_PROVED_UNSEEN", c["heldout_split"])
        self.assertIsNone(b["extraction_accuracy"])

    def test_dedup_source_safe_controls_and_downstream_handoff(self):
        p = self.p
        self.assertEqual(p["dedup"]["primary"], "GAO/B-195862")
        self.assertNotEqual(p["dedup"]["contrast"], p["dedup"]["primary"])
        self.assertTrue(p["dedup"]["synthetic_controls_never_real_labels"])
        self.assertFalse(p["ownership"]["legacy_15_lab_consolidation_proved"])
        self.assertTrue(p["controls"]["no_new_schedule"])
        self.assertTrue(p["controls"]["no_engine_code_changes"])
        self.assertTrue(p["controls"]["no_private_records"])
        self.assertFalse(p["controls"]["commercial_scoring_approved"])
        self.assertEqual(set(p["handoffs"]), {
            "freightrecovery_12", "recoveryos_12", "permitplate_48", "capturebrief_52", "qa_44"
        })


if __name__ == "__main__":
    unittest.main()
