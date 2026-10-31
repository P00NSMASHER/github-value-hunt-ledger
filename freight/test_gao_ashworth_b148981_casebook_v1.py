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


# A separate first-party GAO decision supplies one real held-out *negative*
# rate-entitlement label, not 75 distinct invoice labels or modern buyer accuracy.
B221705_FIXTURE = Path(__file__).parent / "fixtures" / "gao_b221705_negative_rate_holdout_v1.json"


class GaoB221705FalsePositiveIndependentDecisionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = json.loads(B221705_FIXTURE.read_text(encoding="utf-8"))

    def test_official_original_decision_rights_provenance_and_unknown_bytes(self):
        d = self.d
        s = d["source"]
        self.assertEqual(s["original_decision_id"], "B-221705")
        self.assertEqual(s["original_decision_pdf_url"], "https://www.gao.gov/assets/b-221705.pdf")
        self.assertEqual(s["rights_url"], "https://www.gao.gov/copyright")
        self.assertEqual(s["decision_effective_date"], "1987-05-11")
        self.assertEqual(s["original_decision_page_count"], 3)
        self.assertIsNone(s["original_publisher_pdf_sha256"])
        self.assertIsNone(s["original_publisher_pdf_byte_length"])
        self.assertFalse(s["original_pdf_bytes_independently_custodied"])
        self.assertFalse(s["original_carrier_invoice_bol_and_tariff_bytes_custodied"])
        self.assertEqual(s["third_party_carrier_tariff_document_rights"], "UNKNOWN_NOT_CLEARED")

    def test_one_independent_negative_decision_not_seventy_five_independent_invoices(self):
        d = self.d
        s = d["adjudicated_representative_shipment"]
        p = d["case_population"]
        self.assertEqual(s["government_bill_of_lading_number"], "FP-094063")
        self.assertEqual(s["bill_of_lading_period"], "1983-03_EXACT_DAY_UNKNOWN")
        self.assertEqual(s["merger_date"], "1982-09-12")
        self.assertEqual(s["rate_tender"], "ABF Tender ICC 1188")
        self.assertFalse(s["destination_listed_as_ABF_direct_service_in_section_2"])
        self.assertTrue(s["post_merger_operating_authority_extended"])
        self.assertFalse(s["tender_automatically_extended_through_merger"])
        self.assertFalse(s["gao_upheld_GSA_approach"])
        self.assertEqual(s["gao_final_holding"], "REDUCED_TENDER_RATE_NOT_APPLICABLE_TO_LEXINGTON_PARK")
        self.assertEqual(p["minimum_shipments_in_GAO_review"], 75)
        self.assertEqual(p["independent_adjudicated_decisions"], 1)
        self.assertEqual(p["distinct_independently_labeled_negative_decisions"], 1)
        self.assertEqual(p["individual_original_bol_files_custodied"], 0)
        self.assertEqual(d["dedup"]["decision_key"], "GAO/B-221705")
        self.assertEqual(d["dedup"]["do_not_multiply_by_population"], 75)

    def test_naive_overcharge_heuristic_is_wrong_not_a_precision_benchmark(self):
        d = self.d
        c = d["heldout_comparison"]
        self.assertEqual(c["naive_prediction"], "OVERCHARGE_RECOVERABLE")
        self.assertEqual(c["actual_GAO_label"], "FALSE_POSITIVE_TENDER_SCOPE_NOT_EXTENDED")
        self.assertEqual(c["mismatch_count_in_this_one_HISTORICAL_decision"], 1)
        self.assertFalse(c["independently_tested_against_product_engine"])
        self.assertEqual(c["source_original_invoice_tariff_or_payment_pair_count"], 0)
        self.assertIsNone(c["modern_customer_freight_error_accuracy"])
        self.assertIsNone(c["bank_cleared_customer_recovery_cents"])
        self.assertEqual(c["observed_retally_recovery_cents"], 0)
        shipment = d["adjudicated_representative_shipment"]
        for field in ("claimed_tariff_rate_cents", "claimed_reduced_tender_rate_cents", "gsa_deduction_dollars"):
            self.assertIsNone(shipment[field])
        self.assertFalse(shipment["final_settlement_payment_proved"])

    def test_synthetic_adversarial_labels_are_not_inflated_as_real_cases(self):
        d = self.d
        expected = {
            "SYNTH_B221705_MERGER_AUTOMATIC_TENDER_EXTENSION": "REJECT_TENDER_SCOPE_OVER_OPERATING_AUTHORITY",
            "SYNTH_B221705_CARRIER_AUTHORITY_IS_RATE_TENDER": "REJECT_DIFFERENT_LEGAL_FACTS",
            "SYNTH_B221705_75_SHIPMENTS_ARE_75_INDEPENDENT_LABELS": "REJECT_ONE_DECISION_NOT_SEVENTY_FIVE_HOLDOUTS",
            "SYNTH_B221705_DEDUCTION_AS_FINAL_RECOVERY": "REJECT_GAO_OVERRULED_GSA_THEORY",
            "SYNTH_B221705_UNSTATED_AMOUNTS_EQUAL_ZERO": "UNKNOWN_NOT_ZERO",
            "SYNTH_B221705_HISTORICAL_TARIFF_APPLIES_TO_2026": "UNKNOWN_NO_PRESENT_DAY_TARIFF",
        }
        controls = d["synthetic_negative_controls"]
        self.assertEqual({c["id"]: c["expected"] for c in controls}, expected)
        self.assertTrue(all(c["kind"] == "SYNTHETIC_NOT_AN_ADJUDICATED_SHIPMENT" and
                            c["independently_verified_customer_label"] is None for c in controls))
        self.assertFalse(d["restrictions"]["release_authorized"])
        self.assertFalse(d["restrictions"]["legacy_15_lab_consolidation_certified"])



# One new adjudicated GAO historical holdout with opposite outcome to B-221705.
# Both are GAO decisions, not independent original carrier invoices or modern accuracy.
B221615_FIXTURE = Path(__file__).parent / "fixtures" / "gao_b221615_in_transit_merger_rate_contrast_v1.json"


class GaoB221615InTransitMergerContrastTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = json.loads(B221615_FIXTURE.read_text(encoding="utf-8"))
        cls.other = json.loads(B221705_FIXTURE.read_text(encoding="utf-8"))

    @staticmethod
    def research_only_source_rule(*, gbl_party_match=None, tender_in_effect=None, route_in_scope=None):
        if route_in_scope is False:
            return "REDUCED_TENDER_RATE_NOT_APPLICABLE"
        if gbl_party_match is True and tender_in_effect is True and route_in_scope is True:
            return "ORIGINAL_GBL_TENDER_APPLICABLE"
        return "UNKNOWN_MISSING_TENDER_OR_GBL_EVIDENCE"

    def test_original_GAO_rights_date_and_unavailable_publisher_bytes(self):
        d = self.d
        self.assertEqual(d["schema_version"], 1)
        a,b = d["sources"]
        self.assertEqual(a["source_url"], "https://www.gao.gov/products/b-221615-0")
        self.assertEqual(a["effective_decision_date"], "1986-06-24")
        self.assertEqual(b["source_url"], "https://www.gao.gov/products/b-221705")
        self.assertEqual(b["effective_decision_date"], "1987-05-11")
        for s in (a,b):
            self.assertEqual(s["rights_url"], "https://www.gao.gov/copyright")
            self.assertIsNone(s["public_source_html_http_body_sha256"])
            self.assertIsNone(s["public_source_html_response_length_bytes"])
            self.assertFalse(s["source_original_http_response_custodied"])
            self.assertFalse(s["original_gbl_bytes_custodied"])
            self.assertFalse(s["original_tender_bytes_custodied"])
            self.assertEqual(s["third_party_carrier_document_reuse_rights"], "UNKNOWN_NOT_CLEARED")

    def test_historical_original_GBL_merger_order_and_deduction(self):
        x = self.d["original_new_adjudicated_decision"]
        self.assertEqual(x["government_bill_of_lading"], "S4270096")
        self.assertLess(x["bill_of_lading_issued_date"], x["merger_effective_date"])
        self.assertLess(x["merger_effective_date"], x["shipment_delivered_date"])
        self.assertEqual(x["original_gbl_referenced_tender"], "ETMF ICC 691")
        self.assertTrue(x["tender_691_effective_on_tendered_day"])
        self.assertFalse(x["GAO_accepted_ABF_tender_adoption_proof"])
        self.assertTrue(x["GSA_rate_basis_sustained_despite_absent_adoption_evidence"])
        self.assertEqual(x["carrier_initial_overcharge_cents_as_reported_by_GAO"], 15604)
        self.assertEqual(x["GSA_overcharge_deduction_cents_as_reported_by_GAO"], 15604)
        self.assertIsNone(x["independent_bank_or_private_customer_cash_recovery_cents"])
        self.assertFalse(x["underlying_rate_and_tariff_line_item_math_independently_recomputed"])

    def test_two_real_decisions_have_opposite_outcomes_without_false_merger_rule(self):
        new = self.d["original_new_adjudicated_decision"]
        old = self.other["adjudicated_representative_shipment"]
        self.assertEqual(old["gao_final_holding"], "REDUCED_TENDER_RATE_NOT_APPLICABLE_TO_LEXINGTON_PARK")
        self.assertFalse(old["destination_listed_as_ABF_direct_service_in_section_2"])
        self.assertEqual(new["merger_effective_date"], old["merger_date"])
        self.assertEqual(
            self.research_only_source_rule(gbl_party_match=new["GBL_contract_party_is_original_tender_issuing_carrier"],
                tender_in_effect=new["tender_691_effective_on_tendered_day"],
                route_in_scope=new["route_in_original_tender_scope_as_adjudicated"]),
            "ORIGINAL_GBL_TENDER_APPLICABLE")
        self.assertEqual(self.research_only_source_rule(route_in_scope=False), "REDUCED_TENDER_RATE_NOT_APPLICABLE")
        # A merger-only 'never recover' rule misses the 1986 positive; an
        # 'always recover' rule falsely flags the 1987 negative. Counterfactual
        # RED logic, not a historical failing CI or a product-engine score.
        naive_never_recover = ["REDUCED_TENDER_RATE_NOT_APPLICABLE"] * 2
        naive_always_recover = ["ORIGINAL_GBL_TENDER_APPLICABLE"] * 2
        truth = ["ORIGINAL_GBL_TENDER_APPLICABLE", "REDUCED_TENDER_RATE_NOT_APPLICABLE"]
        self.assertEqual(sum(a != b for a,b in zip(naive_never_recover,truth)), 1)
        self.assertEqual(sum(a != b for a,b in zip(naive_always_recover,truth)), 1)
        self.assertEqual(sum(a != b for a,b in zip(truth,truth)), 0)

    def test_missing_originals_are_unknown_not_negative_labels(self):
        for missing in (
            {"gbl_party_match":None,"tender_in_effect":True,"route_in_scope":True},
            {"gbl_party_match":True,"tender_in_effect":None,"route_in_scope":True},
            {"gbl_party_match":True,"tender_in_effect":True,"route_in_scope":None},
            {"gbl_party_match":False,"tender_in_effect":True,"route_in_scope":True},
        ):
            self.assertEqual(self.research_only_source_rule(**missing), "UNKNOWN_MISSING_TENDER_OR_GBL_EVIDENCE")

    def test_dedup_posthoc_holdout_synthetic_separation_and_no_customer_cash(self):
        d = self.d
        q = d["comparison"]
        self.assertEqual(q["new_decisions_this_increment"], 1)
        self.assertEqual(q["independently_adjudicated_decisions_in_pair"], 2)
        self.assertEqual(q["distinct_source_publishers"], 1)
        self.assertTrue(q["post_hoc_curated_comparison"])
        self.assertEqual(len({s["decision_id"] for s in d["sources"]}), 2)
        self.assertEqual(q["modern_invoice_tariff_payment_adjudication_triplets"], 0)
        self.assertEqual(q["product_engine_predictions_evaluated"], 0)
        self.assertEqual(q["true_independent_modern_holdout_count"], 0)
        self.assertIsNone(q["modern_freight_error_precision"])
        self.assertEqual(q["retally_recovered_customer_cash_cents"], 0)
        cs = d["synthetic_negative_controls"]
        self.assertEqual(len(cs), 8)
        self.assertEqual(len({c["id"] for c in cs}), 8)
        self.assertEqual(sum(c["split"] == "synthetic_holdout" for c in cs), 6)
        self.assertTrue(all(c["kind"] == "SYNTHETIC_NOT_A_REAL_SHIPMENT" and c["independent_real_label"] is None for c in cs))
        self.assertFalse(d["restrictions"]["legacy_15_labs_consolidated"])
        self.assertFalse(d["restrictions"]["release_authorized"])


if __name__ == "__main__":
    unittest.main()
