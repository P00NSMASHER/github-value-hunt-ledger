"""Source-bound GAO B-143950 collected-deduction candidate; offline only.

This tests historical GAO decision facts, never original invoices, bank proof,
contemporary tariff accuracy, or RETALLY customer recovery.
"""
from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

PACK = Path(__file__).with_name("fixtures") / "gao_b143950_collected_deduction_candidate_v0.json"
CONTRAST = Path(__file__).with_name("fixtures") / "gao_b143458_capacity_v1.json"


def load_pack():
    return json.loads(PACK.read_text(encoding="utf-8"))


def safe_contract(d):
    """Pinned publisher-fact invariants and intentionally restrictive custody gates."""
    try:
        s, h, g = d["source"], d["historical_reported"], d["ground_truth"]
        return (
            d["schema_version"] == "0.1.0"
            and d["evaluation_family"] == "FREIGHT_ERROR_ADJUDICATION_HISTORICAL_NOT_CUSTOMER_RECONCILIATION"
            and s["official_url"] == "https://www.gao.gov/products/b-143950-0"
            and s["publisher"] == "U.S. Government Accountability Office"
            and s["rights_reference"] == "https://www.gao.gov/copyright"
            and s["rights_scope"] == "GAO_GOVERNMENT_TEXT_US_PUBLIC_DOMAIN_WITH_CREDIT_NO_IMPLIED_ENDORSEMENT_THIRD_PARTY_MATERIAL_SEPARATE"
            and s["decision_id"] == "B-143950"
            and s["decision_date"] == "1960-11-25"
            and s["original_http_sha256"] is None
            and s["raw_original_http_bytes_custodied"] is False
            and s["original_carrier_invoice_bytes_custodied"] is False
            and s["original_bill_of_lading_bytes_custodied"] is False
            and s["original_tariff_pages_custodied"] is False
            and h["reported_bill"] == "396C-57JW"
            and h["reported_government_bill_of_lading"] == "AF-6614902"
            and h["shipment_date"] == "1956-12-01"
            and h["tariff"] == "SOUTHERN_MOTOR_CARRIERS_RATE_CONFERENCE_504_SUPPLEMENT_88_ITEM_10020_A"
            and h["reported_original_payment_cents"] == 75000
            and h["gao_audited_applicable_charge_cents"] == 55200
            and h["gao_reported_overcharge_cents"] == 19800
            and h["gao_reported_deduction_collected_cents"] == 19800
            and h["reported_original_payment_cents"] - h["gao_audited_applicable_charge_cents"] == h["gao_reported_overcharge_cents"]
            and h["gao_applicable_class_55_rate_cents_per_cwt"] * h["gao_applicable_truckload_minimum_weight_lb"] // 100 == 55200
            and h["exclusive_use_class_100_rate_cents_per_cwt"] * h["exclusive_use_minimum_weight_lb"] // 100 == 75000
            and h["carrier_supplemental_reclaim_cents"] == 19800
            and h["carrier_reclaim_disallowed"] is True
            and h["gao_sustained_disallowance_on_present_record"] is True
            and g["historical_collection_label"] == "GAO_REPORTS_ACTUAL_SET_OFF_DEDUCTION"
            and g["independently_heldout_from_engine_training"] == "UNKNOWN"
            and g["current_customer_ground_truth_cases"] == 0
            and g["verified_retally_customer_recovered_cash_cents"] == 0
            and g["independent_original_invoice_rate_and_payment_replay"] is False
            and g["commercial_customer_scoring_approved"] is False
            and g["independent_qa_complete"] is False
            and g["modern_tariff_applicability"] == "UNKNOWN"
        )
    except (KeyError, TypeError, ValueError):
        return False


class GAOB143950CollectedDeductionEvidenceTests(unittest.TestCase):
    def test_authentic_adjudicated_historical_fact_scope(self):
        d = load_pack()
        self.assertTrue(safe_contract(d))
        self.assertEqual(d["cohort"], "US_GAO_MOTOR_FREIGHT_1956_SHIPMENT_1960_DECISION")
        self.assertEqual(d["historical_reported"]["reported_government_bill_of_lading"], "AF-6614902")
        self.assertEqual(d["historical_reported"]["reported_bill"], "396C-57JW")
        self.assertEqual(d["source"]["tariff_effective_date"], "UNKNOWN_HISTORICAL_TARIFF_PAGES_NOT_HELD")
        self.assertIn("NO_IMPLIED_ENDORSEMENT", d["source"]["rights_scope"])

    def test_reported_paid_versus_audited_versus_actually_deducted(self):
        h = load_pack()["historical_reported"]
        self.assertEqual((h["reported_original_payment_cents"], h["gao_audited_applicable_charge_cents"],
                          h["gao_reported_overcharge_cents"], h["gao_reported_deduction_collected_cents"]),
                         (75000, 55200, 19800, 19800))
        self.assertEqual(500 * 15000 // 100 - 276 * 20000 // 100, 19800)
        self.assertTrue(h["carrier_reclaim_disallowed"])

    def test_collected_government_offset_not_conflated_with_other_case_or_retally_cash(self):
        h = load_pack()["historical_reported"]
        contrast = json.loads(CONTRAST.read_text(encoding="utf-8"))
        self.assertEqual(h["gao_reported_deduction_collected_cents"], 19800)
        self.assertIsNone(contrast["historical_facts"]["actual_refund_or_offset_collected"])
        self.assertEqual(contrast["historical_facts"]["gao_overcharge_certificate_cents"], 15530)
        self.assertEqual(load_pack()["ground_truth"]["verified_retally_customer_recovered_cash_cents"], 0)

    def test_five_explicitly_synthetic_fraudulent_inferences(self):
        controls = load_pack()["synthetic_negative_controls"]
        self.assertEqual(len(controls), 5)
        self.assertEqual(len({c["id"] for c in controls}), 5)
        self.assertTrue(all(c["kind"] == "SYNTHETIC" for c in controls))
        self.assertTrue(all(c["expected"].startswith("REJECT_") for c in controls))

    def test_rehashed_or_relabelled_authored_claims_fail_scope_contract(self):
        source = load_pack()
        mutations = (
            ("historical_reported", "reported_original_payment_cents", 75001),
            ("historical_reported", "gao_audited_applicable_charge_cents", 55199),
            ("historical_reported", "gao_reported_overcharge_cents", 19799),
            ("historical_reported", "gao_reported_deduction_collected_cents", 0),
            ("historical_reported", "carrier_reclaim_disallowed", False),
            ("source", "original_http_sha256", "fabricated"),
            ("source", "original_carrier_invoice_bytes_custodied", True),
            ("source", "publisher", "UNVERIFIED_PRIVATE_DATA_VENDOR"),
            ("source", "rights_reference", "https://example.com/unverified"),
            ("source", "rights_scope", "UNRESTRICTED_COMMERCIAL_REUSE"),
            ("source", "original_bill_of_lading_bytes_custodied", True),
            ("historical_reported", "reported_bill", "SYNTHETIC-FORGED-BILL"),
            ("historical_reported", "reported_government_bill_of_lading", "SYNTHETIC-FORGED-GBL"),
            ("historical_reported", "shipment_date", "2026-10-29"),
            ("historical_reported", "tariff", "SYNTHETIC_MODERN_TARIFF"),
            ("source", "original_tariff_pages_custodied", True),
            ("ground_truth", "independently_heldout_from_engine_training", "YES"),
            ("ground_truth", "verified_retally_customer_recovered_cash_cents", 19800),
            ("ground_truth", "commercial_customer_scoring_approved", True),
            ("ground_truth", "independent_qa_complete", True),
            ("ground_truth", "modern_tariff_applicability", "CURRENT"),
        )
        for section, key, invalid in mutations:
            with self.subTest(section=section, key=key):
                forged = copy.deepcopy(source)
                forged[section][key] = invalid
                self.assertFalse(safe_contract(forged))


if __name__ == "__main__":
    unittest.main()
