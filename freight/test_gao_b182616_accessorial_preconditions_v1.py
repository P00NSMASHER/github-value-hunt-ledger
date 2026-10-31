"""Offline source-bounded GAO B-182616 decision checks; no external calls or product code."""
from __future__ import annotations

from datetime import date
from hashlib import sha256
import json
from pathlib import Path
import unittest

PACK = Path(__file__).parent / "fixtures" / "gao_b182616_accessorial_preconditions_v1.json"


def classify_negative(control: dict) -> str:
    """Explicitly guard known invalid extrapolations; never score real customers."""
    f = control["facts"]
    kind = control["kind"]
    if kind == "route_survey":
        if f["request_documented"] is False:
            return "DISALLOW_NO_SHIPPER_REQUEST"
        if (f["request_documented"] is None and
                date.fromisoformat(f["on_shipment_date"]) <
                date.fromisoformat(f["tariff_amendment_effective"])):
            return "UNKNOWN_PRE_AMENDMENT_NO_REQUEST_EVIDENCE"
        return "UNKNOWN_NEEDS_ORIGINAL_TARIFF_AND_REQUEST"
    if kind == "premium_escort":
        return ("DISALLOW_PREMIUM_NO_SPECIFIC_REQUEST"
                if f["specific_request_documented"] is False
                else "UNKNOWN_SHIPPER_REQUEST_RECORD_REQUIRED")
    if kind == "escort_pre_custody":
        return ("DISALLOW_BEFORE_CUSTODY"
                if f["service_date"] < f["custody_date"]
                else "UNKNOWN_SERVICE_VERIFICATION")
    if kind == "weekend_flagman":
        return ("DISALLOW_WEEKEND_PRECONDITION_NOT_MET"
                if f["permit_effective_date"] > f["weekend_date"]
                else "UNKNOWN_NEEDS_FULL_PERMIT_WINDOW")
    if kind == "layover_nights":
        return ("REJECT_THREE_UNSUPPORTED_NIGHTS"
                if f["claimed_nights"] == 18 and
                f["adjudicated_allowed_nights"] == 15
                else "UNKNOWN_ADJUDICATED_WINDOW")
    if kind == "detention_hours":
        return ("UNKNOWN_EXACT_END_NO_MORE_THAN_BOARD_EVIDENCE"
                if f["actual_loading_finished_at"] is None and
                f["claimed_proven_hours"] > f["board_evidence_hours"]
                else "UNKNOWN_REQUIRE_SOURCE_EVIDENCE")
    if kind == "settlement":
        return ("UNKNOWN_NO_ACTUAL_REFUND_RECEIPT"
                if f["claim"] == "REFUND_PAID" and
                f["verified_customer_refund_cents"] is None
                else "UNKNOWN_NO_RECONCILED_BANK_RECORD")
    if kind == "agency_adjustment":
        return ("UNKNOWN_GSA_FINAL_ADJUSTMENT"
                if f["gao_referred_to_gsa"] and
                f["subsequent_final_gsa_adjustment_cents"] is None
                else "UNKNOWN_DOCUMENT_NEEDED")
    if kind == "dedup":
        return ("REJECT_CORRELATED_DUPLICATE_LABELS"
                if f["trailers"] > f["decision_clusters"] == 1 and
                f["government_bill_of_lading_clusters"] == 1
                else "UNKNOWN_INDEPENDENT_CASES")
    if kind == "carrier_concession":
        return ("UNKNOWN_FINAL_RATE_AMOUNT"
                if f["independent_final_rate_adjudication_cents"] is None
                else "UNKNOWN_SEPARATE_TARIFF_VERIFICATION")
    if kind == "modern_tariff":
        return ("UNKNOWN_CURRENT_CONTRACT_RATE"
                if not f["modern_tariff_source_custodied"]
                else "UNKNOWN_MODERN_RATE_MERITS")
    raise ValueError(f"Unexpected synthetic scenario kind: {kind}")


class GAOB182616HistoricalCaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = json.loads(PACK.read_text(encoding="utf-8"))

    def test_official_decision_scope_rights_and_missing_original_bytes(self):
        d = self.doc
        source = d["original_source"]
        self.assertEqual(d["schema_version"], 1)
        self.assertEqual(source["decision_id"], "B-182616")
        self.assertEqual(source["source_url"], "https://www.gao.gov/products/b-182616-0")
        self.assertEqual(source["decision_date"], "1976-02-20")
        self.assertEqual(source["source_http_body_sha256"], None)
        self.assertFalse(source["raw_html_or_pdf_bytes_custodied"])
        self.assertFalse(source["original_governing_1971_tariff_100_e_held"])
        self.assertFalse(source["original_carrier_invoice_bol_pages_held"])
        self.assertFalse(d["rights"]["retally_commercial_accuracy_scoring_approved"])
        self.assertEqual(source["source_access_cost_usd"], 0)
        self.assertFalse(d["restrictions"]["writer_branch_modified"])
        self.assertFalse(d["restrictions"]["legacy_15_lab_consolidation_certified"])
        self.assertFalse(d["restrictions"]["release_authorized"])

    def test_original_publisher_projection_sha_is_not_source_http_hash(self):
        d = self.doc
        payload = json.dumps(d["source_fact_projection"], sort_keys=True,
                             separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        self.assertEqual(sha256(payload).hexdigest(),
                         "b67b511a6b27c539161c0c6dd2dbcbc91a2957b0c0d9d32d9f6bca79ad944d85")
        self.assertEqual(d["source_fact_projection_sha256"], sha256(payload).hexdigest())
        self.assertIsNone(d["original_source"]["source_http_body_sha256"])
        self.assertNotEqual(d["source_fact_projection_sha256"],
                            d["original_source"]["source_http_body_sha256"])

    def test_amounts_are_distinct_and_actual_gsa_adjustment_is_unknown(self):
        p = self.doc["source_fact_projection"]
        self.assertEqual(p["original_billing_cents"], 1903557)
        self.assertEqual(p["original_audit_overcharge_cents"], 795940)
        self.assertEqual(p["revised_deduction_collected_cents"], 523440)
        self.assertEqual(p["carrier_conceded_overcharge_cents"], 101230)
        self.assertEqual(p["carrier_reclaim_cents"], 422210)
        self.assertEqual(p["revised_deduction_collected_cents"] -
                         p["carrier_conceded_overcharge_cents"], p["carrier_reclaim_cents"])
        self.assertEqual(p["original_audit_overcharge_cents"] -
                         p["revised_deduction_collected_cents"], 272500)
        self.assertIsNone(self.doc["historical_scope"]["final_aggregate_revised_overcharge_cents"])
        self.assertIsNone(self.doc["historical_scope"]["carrier_refund_received_cents"])
        self.assertIsNone(self.doc["adjudicated_source_outcome"]["actual_final_gsa_adjustment_cents"])
        self.assertEqual(self.doc["adjudicated_source_outcome"]["actual_retally_customer_recovery_cents"], 0)

    def test_historical_component_labels_are_six_not_modern_accuracy(self):
        d = self.doc
        b = d["benchmark_readiness"]
        self.assertEqual(b["distinct_independent_gao_decision_clusters"], 1)
        self.assertEqual(b["source_ground_truth_component_findings"], 6)
        self.assertEqual(len(d["source_ground_truth_labels"]), 6)
        self.assertEqual(len({x["id"] for x in d["source_ground_truth_labels"]}), 6)
        self.assertEqual(b["independent_carrier_invoice_tariff_payment_triplets"], 0)
        self.assertEqual(b["independent_modern_customer_heldout_cases"], 0)
        self.assertEqual(b["blind_prior_product_predictions"], 0)
        self.assertTrue(b["source_selected_for_this_lab_after_outcome_known"])
        self.assertIsNone(b["independent_modern_rate_precision"])
        self.assertIsNone(b["freight_error_accuracy"])
        self.assertIsNone(b["recoveryos_settlement_accuracy"])
        self.assertIn("CBCA_1317", b["other_case_comparison"])

    def test_synthetic_controls_are_unique_separated_and_green(self):
        d = self.doc
        cases = d["synthetic_negative_controls"]
        self.assertEqual(len(cases), 12)
        self.assertEqual(len({c["id"] for c in cases}), 12)
        self.assertEqual(sum(c["split"] == "synthetic_calibration" for c in cases), 3)
        self.assertEqual(sum(c["split"] == "synthetic_heldout" for c in cases), 9)
        for c in cases:
            with self.subTest(c["id"]):
                self.assertEqual(c["provenance"],
                                 "RESEARCH_AUTHORED_SYNTHETIC_NOT_REAL_CASE")
                self.assertIsNone(c["independent_real_world_label"])
                self.assertEqual(classify_negative(c), c["expected"])

    def test_naive_red_and_conditional_green_are_not_measured_engine_accuracy(self):
        cases = self.doc["synthetic_negative_controls"]
        naive_payable_ids = {
            "SYN_ROUTE_SURVEY_NO_REQUEST",
            "SYN_PREMIUM_ESCORT_NO_SPECIFIC_SHIPPER_REQUEST",
            "SYN_WEEKEND_FLAGMAN_WITH_LATE_PERMIT",
            "SYN_ALL_EIGHTEEN_ESCORT_LAYOVER_NIGHTS_ALLOWED",
        }
        selected = [c for c in cases if c["id"] in naive_payable_ids]
        self.assertEqual(len(selected), 4)
        naive = ["PAYABLE" for _ in selected]
        # RED: unconditional accessorial payment contradicts all four sourced conditions.
        self.assertEqual(sum(x != c["expected"] for x, c in zip(naive, selected)), 4)
        # GREEN: source-bound guard rejects these adversarial synthetic inferences.
        self.assertEqual([classify_negative(c) for c in selected],
                         [c["expected"] for c in selected])
        self.assertEqual(self.doc["benchmark_readiness"]["blind_prior_product_predictions"], 0)
        self.assertIsNone(self.doc["benchmark_readiness"]["independent_modern_rate_precision"])


if __name__ == "__main__":
    unittest.main()
