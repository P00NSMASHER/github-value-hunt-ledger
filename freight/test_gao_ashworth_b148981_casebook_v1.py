"""Review-only original-GAO B-148981 facts and false-positive gates.
No network, no customer files, no freight engine code, no cash assertions.
"""
import json
from pathlib import Path
import unittest

FIXTURE = Path(__file__).parent / "fixtures" / "gao_b148981_freight_adjudication_v1.json"


class GaoAshworthOriginalDecisionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = json.loads(FIXTURE.read_text(encoding="utf-8"))
        cls.by_id = {x["case_id"]: x for x in cls.d["case_groups"]}

    def test_original_publisher_provenance_and_reuse_limits(self):
        d = self.d
        self.assertEqual(d["schema_version"], 1)
        self.assertEqual(d["source"]["original_public_decision_url"], "https://www.gao.gov/products/b-148981")
        self.assertEqual(d["source"]["decision_date"], "1962-11-29")
        self.assertEqual(d["source"]["source_rights_url"], "https://www.gao.gov/copyright")
        for key in ("source_full_html_response_sha256", "source_original_invoice_bytes_sha256",
                    "source_tariff_bytes_sha256", "source_response_content_length_bytes"):
            self.assertIsNone(d["source"][key])
        self.assertFalse(d["source"]["issuer_http_response_custodied"])
        self.assertFalse(d["source"]["original_bol_or_payment_documents_custodied"])
        self.assertTrue(d["data_quality"]["no_person_identifiers_or_private_customer_records"])

    def test_exact_source_dollar_arithmetic_and_no_duplicate_groups(self):
        d = self.d
        groups = d["case_groups"]
        self.assertEqual(len(groups), 3)
        self.assertEqual(len(self.by_id), 3)
        self.assertEqual({g["carrier_bill_group"] for g in groups}, {"5188", "5193", "5190"})
        self.assertEqual(sum(g["shipment_count"] for g in groups), 7)
        self.assertEqual(sum(g["initial_audit_overcharge_cents"] for g in groups), 184200)
        for g in groups:
            self.assertEqual(sum(g["original_paid_components_cents"]), g["original_paid_cents"])
            self.assertTrue(g["carrier_refund_reported_by_gao"])
            self.assertFalse(g["credit_clearing_independently_proved"])
        self.assertEqual(self.by_id["B148981_BILL_5188"]["original_paid_cents"], 175500)
        self.assertEqual(self.by_id["B148981_BILL_5193"]["initial_audit_overcharge_cents"], 4602)
        self.assertEqual(self.by_id["B148981_BILL_5190"]["later_carrier_credit_authorized_cents"], 39174)

    def test_real_holdout_preserves_the_reversed_part_of_auditor_claim(self):
        a = self.by_id["B148981_BILL_5190"]
        self.assertEqual(a["split"], "holdout_within_single_publisher_decision")
        self.assertEqual(a["gao_decision"], "INITIAL_AUDIT_MODIFIED_CARRIER_CREDIT_AUTHORIZED")
        self.assertEqual(a["initial_audit_overcharge_cents"], 166154)
        self.assertNotEqual(a["later_carrier_credit_authorized_cents"], 0)
        self.assertFalse(a["credit_clearing_independently_proved"])
        for g in self.d["case_groups"][:2]:
            self.assertEqual(g["split"], "calibration")
            self.assertEqual(g["gao_decision"], "INITIAL_AUDIT_SUSTAINED")
        self.assertEqual(self.d["quality"]["within_source_holdout_groups"], 1)
        self.assertEqual(self.d["quality"]["publisher_decisions"], 1)
        self.assertIn("NOT_SEPARATE_INDEPENDENT_PUBLISHER", self.d["quality"]["split_independence"])

    def test_synthetic_negative_controls_fail_closed(self):
        expected = {
            "SYNTHETIC_REFUNDS_AS_RETALLY_CASH": "UNKNOWN_NO_RETALLY_CASH",
            "SYNTHETIC_5190_ORIGINAL_AUDIT_FINAL": "REJECT_GAO_MODIFIED_AUDIT",
            "SYNTHETIC_5190_CREDIT_PAID": "UNKNOWN_CREDIT_SETTLEMENT_NOT_VERIFIED",
            "SYNTHETIC_5193_TRIPLE_DECISION": "REJECT_GROUP_LEVEL_LABEL",
            "SYNTHETIC_MODERN_PRIVATE_TARIFF": "UNKNOWN_NO_PRESENT_DAY_RATE_AUTHORITY",
            "SYNTHETIC_GAO_REFUND_BANK_PROOF": "UNKNOWN_NO_INDEPENDENT_BANK_PROOF",
        }
        controls = self.d["synthetic_negative_controls"]
        self.assertEqual({c["id"]: c["expected"] for c in controls}, expected)
        self.assertTrue(all(c["provenance"] == "SYNTHETIC_NOT_A_REAL_SHIPMENT" and
                            c["independently_verified_customer_label"] is None for c in controls))

    def test_current_customer_accuracy_and_cash_are_unproved(self):
        q = self.d["quality"]
        self.assertEqual(q["modern_independent_positives"], 0)
        self.assertEqual(q["modern_independent_negatives"], 0)
        self.assertEqual(q["externally_linked_modern_invoice_tariff_payment_adjudications"], 0)
        self.assertEqual(q["bank_cleared_refunds_independently_authenticated"], 0)
        self.assertIsNone(q["modern_measured_freight_error_accuracy"])
        self.assertEqual(q["retally_recovered_cash_cents"], 0)
        self.assertFalse(self.d["product_release_authorized"])
        self.assertFalse(self.d["legacy_15_lab_consolidation_certified"])


# This second decision is a publisher-adjudicated holdout independent of B-148981,
# not a separate publisher, original invoice, modern freight-rate trial, or cash event.
RAIL_FIXTURE = Path(__file__).parent / "fixtures" / "gao_b151387_independent_rail_holdout_v1.json"


class GaoB151387IndependentHistoricalRailHoldoutTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = json.loads(RAIL_FIXTURE.read_text(encoding="utf-8"))

    def test_original_source_rights_and_missing_source_byte_proof(self):
        d = self.d
        self.assertEqual(d["source"]["original_public_decision_url"], "https://www.gao.gov/products/b-151387")
        self.assertEqual(d["source"]["effective_decision_date"], "1963-12-09")
        self.assertEqual(d["source"]["original_rights_url"], "https://www.gao.gov/copyright")
        self.assertIsNone(d["source"]["original_issuer_http_response_bytes_sha256"])
        self.assertIsNone(d["source"]["original_issuer_http_response_length_bytes"])
        self.assertFalse(d["source"]["publisher_http_response_custodied"])
        self.assertFalse(d["source"]["original_tariff_bytes_custodied"])
        self.assertFalse(d["source"]["original_carrier_invoices_custodied"])
        self.assertEqual(d["source"]["third_party_tariff_or_embedded_content_reuse_rights"], "UNKNOWN_SEPARATE_RIGHTS_NOT_CLEARED")

    def test_six_historical_shipment_arithmetic_by_charge_group(self):
        d = self.d
        groups = d["adjudicated_rail_shipment_groups"]
        self.assertEqual(len(groups), 2)
        self.assertEqual([g["shipment_count"] for g in groups], [4, 2])
        self.assertEqual([g["carrier_selected_minimum_weight_pounds"] for g in groups], [20000, 12500])
        self.assertTrue(all(g["gao_applicable_minimum_weight_pounds"] == 10000 for g in groups))
        self.assertEqual(d["source_explicit_facts"]["agreed_actual_weight_each_shipment_pounds"], 8400)
        assessed = sum(g["shipment_count"] * g["reported_carrier_charged_per_shipment_cents"] for g in groups)
        applicable = sum(g["shipment_count"] * g["gao_applicable_per_shipment_cents"] for g in groups)
        difference = sum(g["shipment_count"] * g["disputed_difference_per_shipment_cents"] for g in groups)
        self.assertEqual((assessed, applicable, difference), (367500, 210000, 157500))
        self.assertEqual(assessed - applicable, difference)
        self.assertEqual(d["derived_reconciliation"]["discrepancy_cents"], 0)
        self.assertEqual(d["source_explicit_facts"]["carrier_supplemental_claims_disallowed_cents"], [35000, 113750])
        self.assertEqual(sum(d["source_explicit_facts"]["carrier_supplemental_claims_disallowed_cents"]) + 8750, difference)

    def test_holdout_is_separate_decision_not_six_independent_cases(self):
        d = self.d
        q = d["benchmark_quality"]
        self.assertEqual(q["decision_count"], 1)
        self.assertEqual(q["described_original_rail_carloads"], 6)
        self.assertEqual(q["group_level_labels"], 2)
        self.assertTrue(q["independent_from_existing_B148981_decision"])
        self.assertFalse(q["independent_from_GAO_publisher"])
        self.assertEqual(q["independent_source_original_bol_bytes"], 0)
        self.assertTrue(d["dedup"]["no_per_shipment_ids_invented"])
        self.assertIsNone(q["current_freight_error_accuracy"])
        self.assertEqual(q["modern_buyer_authorized_invoice_rate_payment_and_adjudication_pairs"], 0)
        self.assertEqual(q["modern_positive_and_negative_label_count"], 0)
        self.assertFalse(d["production_release_authorized"])

    def test_recovery_and_synthetic_negative_controls_fail_closed(self):
        d = self.d
        facts = d["source_explicit_facts"]
        self.assertEqual(facts["separately_collected_government_overcharge_by_deduction_cents"], 8750)
        self.assertFalse(d["derived_reconciliation"]["source_reports_all_157500_collected"])
        self.assertEqual(d["derived_reconciliation"]["customer_or_retally_recovered_cash_cents"], 0)
        expected = {
            "SYNTH_B151387_LONGER_CAR_ALWAYS_HIGHER_MINIMUM": "REJECT_IN_THIS_HISTORICAL_ADJUDICATED_CASE",
            "SYNTH_B151387_ALL_DIFFERENCE_CASH_CLEARED": "UNKNOWN_ONLY_8750_CENTS_DEDUCTION_REPORTED",
            "SYNTH_B151387_SIX_INDEPENDENT_DECISIONS": "REJECT_ONE_GAO_DECISION_NO_ORIGINAL_BOLS",
            "SYNTH_B151387_1962_COMPARISON_EQUIVALENT": "REJECT_GAO_DISTINGUISHED_PRECEDENT",
            "SYNTH_B151387_1963_TARIFF_CURRENT": "UNKNOWN_NO_CURRENT_TARIFF_OR_CUSTOMER_AUTHORITY",
        }
        controls = d["synthetic_negative_controls"]
        self.assertEqual({c["id"]: c["expected"] for c in controls}, expected)
        self.assertTrue(all(c["kind"] == "SYNTHETIC_NOT_A_REAL_SHIPMENT" and
                            c["independently_verified_customer_label"] is None for c in controls))
        self.assertFalse(d["legacy_lab_consolidation_certified"])


if __name__ == "__main__":
    unittest.main()
