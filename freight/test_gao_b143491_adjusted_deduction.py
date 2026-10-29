"""Offline original-GAO-text tariff correction regression; historical-only."""
from __future__ import annotations
import copy
import json
import unittest
from pathlib import Path

PACK = Path(__file__).with_name("fixtures") / "gao_b143491_adjusted_deduction_candidate_v0.json"

def load_pack():
    return json.loads(PACK.read_text(encoding="utf-8"))

def safe_contract(p):
    try:
        s, h, g = p["source"], p["historical_reported"], p["ground_truth"]
        return (
            p["schema_version"] == "0.1.0"
            and p["evaluation_family"] == "FREIGHT_ERROR_HISTORICAL_ADJUDICATION_NOT_GENERAL_AP_RECONCILIATION"
            and s["official_url"] == "https://www.gao.gov/products/b-143491"
            and s["decision_id"] == "B-143491" and s["decision_date"] == "1960-11-25"
            and s["rights_reference"] == "https://www.gao.gov/copyright"
            and "NO_IMPLIED_ENDORSEMENT" in s["rights_scope"]
            and s["original_publisher_http_bytes_custodied"] is False
            and s["original_publisher_http_sha256"] is None
            and s["original_invoices_bols_tariffs_vouchers_custodied"] is False
            and s["original_source_documents_independently_replayed"] is False
            and s["rate_sheet_840_stated_effective_date"] == "1956-08-29"
            and s["rate_sheet_846_supplement_6_effective_date"] == "UNKNOWN"
            and h["gbl_first"] == "AF-5116591" and h["gbl_second"] == "AF-5116516"
            and h["paid_per_shipment_cents"] == 17040
            and h["paid_total_cents"] == 34080
            and h["initial_audited_first_cents"] == 12344
            and h["initial_audited_second_cents"] == 10856
            and h["initial_audited_total_cents"] == 23200
            and h["original_overpayment_deducted_cents"] == 10880
            and h["original_overpayment_deduction_reported_collected"] is True
            and h["elevator_weight_initial_lb"] == 2790
            and h["elevator_weight_corrected_lb"] == 3280
            and h["revised_audited_second_cents"] == 10932
            and h["revised_audited_total_cents"] == 23276
            and h["arithmetic_implied_overpayment_after_adjustment_cents"] == 10804
            and h["adjustment_authorized_cents"] == 76
            and h["adjustment_already_paid"] == "UNKNOWN_NOT_PROVEN"
            and h["decision"] == "INITIAL_SETTLEMENT_SUSTAINED_EXCEPT_76_CENT_CONDITIONAL_ADJUSTMENT"
            and h["paid_total_cents"] == 2 * h["paid_per_shipment_cents"]
            and h["initial_audited_total_cents"] == h["initial_audited_first_cents"] + h["initial_audited_second_cents"]
            and h["paid_total_cents"] - h["initial_audited_total_cents"] == h["original_overpayment_deducted_cents"]
            and h["revised_audited_total_cents"] == h["initial_audited_first_cents"] + h["revised_audited_second_cents"]
            and h["paid_total_cents"] - h["revised_audited_total_cents"] == h["arithmetic_implied_overpayment_after_adjustment_cents"]
            and h["original_overpayment_deducted_cents"] - h["arithmetic_implied_overpayment_after_adjustment_cents"] == h["adjustment_authorized_cents"]
            and g["historical_collection_label"] == "GAO_REPORTS_10880_ADMINISTRATIVE_DEDUCTION_COLLECTED"
            and g["actual_76_cent_adjustment_payment"] == "UNKNOWN"
            and g["independent_heldout_original_invoice_labels"] == 0
            and g["modern_rate_applicability"] == "UNKNOWN"
            and g["commercial_engine_scoring_approved"] is False
            and g["verified_retally_customer_recovered_cash_cents"] == 0
            and g["independent_qa_complete"] is False
            and len(p["synthetic_negative_controls"]) == 6
            and len({c["id"] for c in p["synthetic_negative_controls"]}) == 6
            and all(c["kind"] == "SYNTHETIC" and c["expected"].startswith("REJECT_") for c in p["synthetic_negative_controls"])
        )
    except (KeyError, TypeError, ValueError):
        return False

class GAOB143491TariffCorrectionTests(unittest.TestCase):
    def test_publisher_reported_dual_shipment_arithmetic_and_correction(self):
        p = load_pack()
        self.assertTrue(safe_contract(p))
        h = p["historical_reported"]
        self.assertEqual((h["original_overpayment_deducted_cents"],
                          h["adjustment_authorized_cents"],
                          h["arithmetic_implied_overpayment_after_adjustment_cents"]),
                         (10880, 76, 10804))
        self.assertEqual(h["adjustment_already_paid"], "UNKNOWN_NOT_PROVEN")
        self.assertEqual(p["ground_truth"]["independent_heldout_original_invoice_labels"], 0)

    def test_twelve_synthetic_false_promotions_rejected(self):
        source = load_pack()
        edits = (
            ("historical_reported", "revised_audited_second_cents", 10856),
            ("historical_reported", "adjustment_authorized_cents", 0),
            ("historical_reported", "original_overpayment_deducted_cents", 10804),
            ("historical_reported", "elevator_weight_corrected_lb", 2790),
            ("source", "original_publisher_http_sha256", "f" * 64),
            ("source", "original_invoices_bols_tariffs_vouchers_custodied", True),
            ("source", "rate_sheet_846_supplement_6_effective_date", "1956-08-29"),
            ("historical_reported", "adjustment_already_paid", "PAID"),
            ("ground_truth", "independent_heldout_original_invoice_labels", 2),
            ("ground_truth", "commercial_engine_scoring_approved", True),
            ("ground_truth", "verified_retally_customer_recovered_cash_cents", 10880),
        )
        for section, key, value in edits:
            with self.subTest(section=section, key=key):
                altered = copy.deepcopy(source)
                altered[section][key] = value
                self.assertFalse(safe_contract(altered))
        altered = copy.deepcopy(source)
        altered["synthetic_negative_controls"][0]["kind"] = "ORIGINAL"
        self.assertFalse(safe_contract(altered))

if __name__ == "__main__":
    unittest.main()
