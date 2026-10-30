"""Source-bound GAO B-192872 historical classification and amount-abstention control.

1979 decision: GSA initial $502.01 setoff, but corrected 2,200 lb vs 1,700 lb
requires upward settlement adjustment of UNKNOWN dollar amount. This is NOT
a modern freight error, independently cleared refund, or RETALLY recovery.
No network calls, paid services, source-text copying, or engine changes.
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path


class GAOB192872AdjustedWeightEvidenceTests(unittest.TestCase):
    @staticmethod
    def pack():
        p = Path(__file__).with_name("fixtures") / "gao_b192872_weight_corrected_adjudication_candidate_v0.json"
        return json.loads(p.read_text(encoding="utf-8"))

    @staticmethod
    def held(d):
        try:
            s, c, g, a, p, l, q, h = (
                d["source"], d["cohort"], d["government_bill_of_lading"],
                d["initial_government_audit"], d["published_adjudication"],
                d["labels"], d["quality"], d["consumers"]
            )
            neg = d["synthetic_negative_controls"]
            return (
                d["schema_version"] == "0.1.0"
                and d["pack_id"] == "GAO_B192872_WEIGHT_CORRECTED_CLASSIFICATION_CANDIDATE_V0"
                and d["evaluation_family"] == "FREIGHT_HISTORICAL_CLASSIFICATION_ADJUDICATION_AND_FINAL_AMOUNT_ABSTENTION"
                and d["status"] == "HISTORICAL_PUBLIC_ADJUDICATION_CONTROL_NOT_CUSTOMER_OVERCHARGE_ACCURACY"
                and s["official_decision_url"] == "https://www.gao.gov/products/b-192872"
                and s["original_pdf_url"] == "https://www.gao.gov/assets/b-192872.pdf"
                and s["rights_url"] == "https://www.gao.gov/copyright"
                and s["decision_id"] == "B-192872"
                and s["decision_date"] == "1979-05-07"
                and s["inspected_pdf_printed_pages"] == [2, 5]
                and s["original_publisher_pdf_http_bytes_held"] is False
                and s["original_publisher_pdf_http_sha256"] is None
                and s["original_gbl_tariff_pages_diagrams_or_paid_invoice_bytes_held"] is False
                and s["historical_nmfc_rate_table_commercial_reproduction_cleared"] is False
                and s["modern_customer_rate_authority"] == "UNKNOWN"
                and c["type"] == "ONE_HISTORICAL_US_GOVERNMENT_SHIPMENT"
                and c["original_shipment_month"] == "1975-07"
                and c["historical_effective_tariff"] == "NMFC_100_B_ITEM_178160_AS_REPORTED_BY_GAO"
                and c["exact_shipment_day"] == "UNKNOWN"
                and c["heldout_from_110_commercial_invoice_faces"] is True
                and c["no_modern_customer_invoice_or_payment_data"] is True
                and g["number"] == "M-0068206"
                and g["originally_listed_weight_lb"] == 1700
                and g["corrected_actual_weight_lb_reported_by_GSA"] == 2200
                and g["invoice_charge_cents"] is None
                and g["contemporaneous_original_gbl_acquired"] is False
                and g["controlling_tender_tariff_pages_acquired"] is False
                and a["original_carrier_rated_class"] == 300
                and a["gsa_alleged_overcharge_and_initial_setoff_cents"] == 50201
                and a["initial_setoff_reported_executed"] is True
                and a["amount_is_final_adjusted_freight_overcharge"] is False
                and a["independent_treasury_settlement_receipt_held"] is False
                and p["published_classification_outcome"] ==
                    "GSA_LOWER_CLASSIFICATION_UPHELD_WITH_WEIGHT_ADJUSTMENT_REQUIRED"
                and p["applicable_historical_class"] == 125
                and p["knocked_down_condition_accepted"] is True
                and p["banded_guardrails_satisfy_packages_condition"] is True
                and p["diagrammatic_cubage_as_set_up_cubic_ft"] == 440
                and p["diagrammatic_cubage_as_shipped_cubic_ft"] == 154
                and p["cubage_reduction_percent"] == 65
                and 100 * (1 - 154 / 440) == p["cubage_reduction_percent"]
                and p["weight_correction_requires_upward_adjustment_to_carrier"] is True
                and p["lower_rate_original_published_tariff_bytes_held"] is False
                and p["revised_total_charge_cents"] is None
                and p["revised_correct_government_setoff_cents"] is None
                and p["adjustment_dollars_published"] == "UNKNOWN"
                and p["actual_subsequent_refund_or_collection_cents"] is None
                and l["independent_agency_adjudicated_historical_classification_cases"] == 1
                and l["independently_adjudicated_exact_final_adjusted_amount_cases"] == 0
                and l["independently_heldout_modern_private_overcharge_cases"] == 0
                and l["independently_cleared_private_payment_refund_cases"] == 0
                and l["verified_retally_customer_recovery_cents"] == 0
                and l["permitted_customer_precision_recall"] == "UNKNOWN"
                and l["agency_classification_label_is_not_final_money_truth"] is True
                and q["rate_effective_date_and_original_source_terms_fully_verified"] is False
                and q["later_supersession_exhaustively_checked"] is False
                and q["original_issuer_source_byte_sha256"] == "UNKNOWN"
                and q["independent_final_cash_label"] == "UNKNOWN"
                and q["source_specific_commercial_customer_scoring_rights"] == "UNVERIFIED_HOLD"
                and q["no_provider_queries_or_private_data_added"] is True
                and len(neg) == 8
                and len({x["id"] for x in neg}) == 8
                and all(x["kind"] == "SYNTHETIC" and
                        x["expected"].startswith("REJECT_") for x in neg)
                and h["retally_recoveryos_engineering"] == ":12"
                and h["permitplate_cross_lane_source_policy"] == ":48"
                and h["capturebrief_cross_lane_proof_policy"] == ":52"
                and h["independent_qa"] == ":44"
                and h["engine_code_changed"] is False
                and h["production_release_authorized"] is False
            )
        except (KeyError, TypeError, ValueError):
            return False

    def test_source_bound_historical_classification_candidate(self):
        self.assertTrue(self.held(self.pack()))

    def test_adjusted_weight_blocks_exact_dollar_promotion(self):
        d = self.pack()
        self.assertEqual(
            d["government_bill_of_lading"]["corrected_actual_weight_lb_reported_by_GSA"] -
            d["government_bill_of_lading"]["originally_listed_weight_lb"], 500)
        self.assertEqual(d["initial_government_audit"]["gsa_alleged_overcharge_and_initial_setoff_cents"], 50201)
        self.assertIsNone(d["published_adjudication"]["revised_correct_government_setoff_cents"])
        self.assertIsNone(d["published_adjudication"]["actual_subsequent_refund_or_collection_cents"])
        self.assertEqual(d["labels"]["verified_retally_customer_recovery_cents"], 0)

    def test_synthetic_forged_money_provenance_and_authority_rejected(self):
        baseline = self.pack()
        self.assertTrue(self.held(baseline))
        attacks = [
            ("source.original_publisher_pdf_http_sha256", "a" * 64),
            ("source.original_publisher_pdf_http_bytes_held", True),
            ("source.original_gbl_tariff_pages_diagrams_or_paid_invoice_bytes_held", True),
            ("source.modern_customer_rate_authority", "VERIFIED"),
            ("cohort.heldout_from_110_commercial_invoice_faces", False),
            ("government_bill_of_lading.originally_listed_weight_lb", 2200),
            ("government_bill_of_lading.corrected_actual_weight_lb_reported_by_GSA", 1700),
            ("government_bill_of_lading.invoice_charge_cents", 50201),
            ("initial_government_audit.amount_is_final_adjusted_freight_overcharge", True),
            ("published_adjudication.applicable_historical_class", 300),
            ("published_adjudication.revised_correct_government_setoff_cents", 50201),
            ("published_adjudication.actual_subsequent_refund_or_collection_cents", 50201),
            ("labels.independently_adjudicated_exact_final_adjusted_amount_cases", 1),
            ("labels.independently_heldout_modern_private_overcharge_cases", 1),
            ("labels.verified_retally_customer_recovery_cents", 50201),
            ("quality.source_specific_commercial_customer_scoring_rights", "APPROVED"),
            ("consumers.production_release_authorized", True),
        ]
        for path, forged in attacks:
            with self.subTest(synthetic_attack=path):
                modified = json.loads(json.dumps(baseline))
                target = modified
                keys = path.split(".")
                for key in keys[:-1]:
                    target = target[key]
                target[keys[-1]] = forged
                self.assertFalse(self.held(modified))


if __name__ == "__main__":
    unittest.main()
