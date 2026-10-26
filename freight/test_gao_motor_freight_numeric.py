"""FreightRecovery GAO publisher-decision numerical evidence negative controls."""
from __future__ import annotations

import copy
import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

from freight.gao_motor_freight_numeric import (
    FIXTURE, PINNED, SCOPE, load_fixture, validate_fixture, make_receipt,
    validate_receipt, run,
)
from freight.unified_research_lab import ResearchError, SEEDS, digest

DAY = date(2026, 10, 24)


class GAOMotorFreightNumericalEvidenceTests(unittest.TestCase):
    def test_five_distinct_official_historical_cases_are_only_decision_level(self):
        data = load_fixture()
        self.assertEqual(data["scope"], SCOPE)
        self.assertEqual(len(data["cases"]), 5)
        self.assertEqual(list(PINNED), [row["case_number"] for row in data["cases"]])
        self.assertEqual(len({x["official_url"] for x in data["cases"]}), 5)
        for entry in data["cases"]:
            with self.subTest(case=entry["case_number"]):
                self.assertIn(entry["official_url"], SEEDS["freightrecovery"])
                self.assertFalse(entry["commercial_reuse_approved_for_customer_engine"])
                self.assertFalse(entry["modern_rate_authority"])
                self.assertFalse(entry["independent_original_invoice_custody"])
                self.assertIsNone(entry["source_original_bytes_sha256"])
        self.assertEqual(data["original_document_bytes_stored"], 0)
        self.assertEqual(data["real_customer_invoice_records"], 0)
        self.assertEqual(data["independent_invoice_outcome_labels"], 0)
        self.assertEqual(data["verified_retally_recovered_cash_cents"], 0)

    def test_only_1978_decision_has_publisher_reported_complete_arithmetic(self):
        receipt = make_receipt(DAY)
        self.assertEqual(receipt["case_count"], 5)
        self.assertEqual(receipt["exact_publisher_stated_arithmetic_cases"], 1)
        case = {c["case_number"]: c for c in receipt["case_receipts"]}
        one = case["B-191257"]
        self.assertEqual(one["reported_paid_cents"], 82800)
        self.assertEqual(one["reported_audit_charge_cents"], 79600)
        self.assertEqual(one["reported_offset_deduction_cents"], 3200)
        self.assertEqual(one["reported_paid_cents"] -
                         one["reported_audit_charge_cents"],
                         one["reported_offset_deduction_cents"])
        self.assertEqual(one["numeric_reconciliation"], "EXACT_PUBLISHER_REPORTED_CHARGES_MATCH")
        for ident in set(case) - {"B-191257"}:
            with self.subTest(case=ident):
                self.assertIsNone(case[ident]["reported_audit_charge_cents"])
                self.assertEqual(case[ident]["numeric_reconciliation"],
                                 "NO_EXACT_AUDITED_CHARGE_RECONSTRUCTION")
                self.assertEqual(case[ident]["customer_recovery_cents"], 0)
        self.assertEqual(receipt["independent_customer_invoice_truth_cases"], 0)
        self.assertEqual(receipt["verified_retally_recovered_cash_cents"], 0)
        self.assertFalse(receipt["source_specific_commercial_rights_verified"])

    def test_two_shipment_aggregate_and_conflicting_amounts_remain_uncertain(self):
        source = {row["case_number"]: row for row in load_fixture()["cases"]}
        joint = source["B-143048"]
        self.assertEqual(joint["shipment_count"], 2)
        self.assertEqual(joint["reported_offset_deduction_cents"], 13030)
        self.assertEqual(joint["reported_paid_rate_cents_per_cwt"], 1069)
        self.assertEqual(joint["reported_alternative_rate_cents_per_cwt"], 765)
        self.assertIsNone(joint["reported_paid_cents"])
        self.assertFalse(joint["per_shipment_deduction_allocation_known"])
        conflict = source["B-146511"]
        self.assertEqual(conflict["claim_amount_variants_cents"], [2070, 2074, 2076])
        self.assertEqual(conflict["reported_offset_deduction_cents"], 2074)
        self.assertEqual(make_receipt(DAY)["conflicting_amount_cases"], 1)
        self.assertEqual(make_receipt(DAY)["multi_shipment_aggregate_cases"], 1)

    def test_1962_and_1964_later_litigation_caveats_not_erased(self):
        data = {row["case_number"]: row for row in load_fixture()["cases"]}
        self.assertTrue(data["B-148465"]["further_review_explicitly_reserved"])
        self.assertTrue(data["B-152744"]["further_review_explicitly_reserved"])
        self.assertFalse(data["B-191257"]["further_review_explicitly_reserved"])
        self.assertEqual(make_receipt(DAY)["explicit_later_review_caveat_cases"], 2)
        self.assertNotIn("FINAL", data["B-152744"]["decision_as_published"])

    def test_changed_amounts_or_authority_cannot_pass_rehashed_fixture(self):
        original = load_fixture()
        mutations = [
            ("B-191257", "reported_paid_cents", 92800),
            ("B-191257", "reported_audit_charge_cents", 80000),
            ("B-152744", "further_review_explicitly_reserved", False),
            ("B-143048", "shipment_count", 1),
            ("B-143048", "per_shipment_deduction_allocation_known", True),
            ("B-146511", "claim_amount_variants_cents", [2074]),
            ("B-191257", "modern_rate_authority", True),
            ("B-191257", "commercial_reuse_approved_for_customer_engine", True),
            ("B-191257", "independent_original_invoice_custody", True),
            ("B-191257", "official_url", "https://www.gao.gov/products/b-215958"),
            ("B-191257", "historical_tariff", "NASI_RULES_TARIFF_190_A"),
        ]
        for ident, field, bogus in mutations:
            with self.subTest(case=ident, field=field):
                fake = copy.deepcopy(original)
                target = next(row for row in fake["cases"] if row["case_number"] == ident)
                target[field] = bogus
                with self.assertRaises(ResearchError):
                    validate_fixture(fake)
                # A forged digest of altered local authored data is not authority.
                self.assertNotEqual(digest(fake), digest(original))
        forged = copy.deepcopy(original)
        forged["verified_retally_recovered_cash_cents"] = 36646
        with self.assertRaises(ResearchError):
            validate_fixture(forged)

    def test_deterministic_receipt_rejects_even_rehashed_financial_promotions(self):
        original = make_receipt(DAY)
        self.assertEqual(original["scope"], SCOPE)
        validate_receipt(original, at_date=DAY)
        mutations = [
            ("historical_reported_deductions_sum_cents_not_retally_revenue", 50000),
            ("verified_retally_recovered_cash_cents", 36646),
            ("independent_customer_invoice_truth_cases", 5),
            ("source_specific_commercial_rights_verified", True),
            ("exact_publisher_stated_arithmetic_cases", 5),
            ("source_original_document_bytes_stored", 5),
            ("production_engine_changes", 1),
            ("explicit_later_review_caveat_cases", 0),
            ("conflicting_amount_cases", 0),
        ]
        for field, val in mutations:
            with self.subTest(field=field):
                fake = copy.deepcopy(original)
                fake[field] = val
                fake["receipt_sha256"] = digest({
                    k: v for k, v in fake.items() if k != "receipt_sha256"
                })
                with self.assertRaises(ResearchError):
                    validate_receipt(fake, at_date=DAY)
        false_case = copy.deepcopy(original)
        false_case["case_receipts"][0]["reported_offset_deduction_cents"] = 50000
        false_case["receipt_sha256"] = digest({
            k: v for k, v in false_case.items() if k != "receipt_sha256"
        })
        with self.assertRaises(ResearchError):
            validate_receipt(false_case, at_date=DAY)

    def test_one_branch_receipt_atomic_repeat_and_staleness_gate(self):
        with tempfile.TemporaryDirectory() as root:
            file = Path(root) / "gao.json"
            data = run(output=file, at_date=DAY)
            self.assertEqual(data["case_count"], 5)
            self.assertFalse(data["commercial_reuse_approved_for_customer_engine"])
            before = file.read_bytes()
            self.assertTrue(run(output=file, at_date=DAY, verify_only=True)["verified"])
            self.assertEqual(before, file.read_bytes())
            run(output=file, at_date=DAY)
            self.assertEqual(before, file.read_bytes())
            changed = json.loads(before)
            changed["verified_retally_recovered_cash_cents"] = 36646
            file.write_text(json.dumps(changed), encoding="utf-8")
            with self.assertRaises(ResearchError):
                run(output=file, at_date=DAY, verify_only=True)
            with self.assertRaisesRegex(ResearchError,
                                        "GAO_NUMERIC_RECEIPT_STALE_OR_FUTURE"):
                validate_receipt(json.loads(before), at_date=DAY + timedelta(days=3))

    def test_missing_source_and_bad_date_are_explicit_failures(self):
        with patch("freight.gao_motor_freight_numeric.FIXTURE",
                   Path("/nonexistent/not-original-publisher-document")):
            with self.assertRaises(ResearchError):
                make_receipt(DAY)
        with self.assertRaisesRegex(ResearchError, "GAO_NUMERIC_RECEIPT_DATE_INVALID"):
            make_receipt(date(2026, 10, 23))
        with self.assertRaisesRegex(ResearchError, "GAO_NUMERIC_RECEIPT_DATE_INVALID"):
            make_receipt("2026-10-24")
        self.assertTrue(FIXTURE.name.startswith("gao_motor_freight"))


    def test_b143458_published_full_capacity_does_not_override_carrier_specific_tariff(self):
        """Real GAO adjudication is NOT a modern invoice or customer recovery label."""
        path = FIXTURE.parent / "gao_b143458_capacity_v1.json"
        item = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(item["schema_version"], "1.0.0")
        self.assertEqual(item["fixture_id"], "GAO_B143458_TARIFF_SPECIFIC_CAPACITY_CONTROL_V1")
        self.assertEqual(item["evaluation_family"],
                         "FREIGHT_ERROR_ADJUDICATION_HISTORICAL_DECISION_ONLY")
        source = item["source"]
        self.assertEqual(source["official_url"], "https://www.gao.gov/products/b-143458")
        self.assertIn(source["official_url"], SEEDS["freightrecovery"])
        self.assertEqual(source["decision_date"], "1961-03-30")
        self.assertEqual(source["rights_reference"], "https://www.gao.gov/copyright")
        self.assertFalse(source["original_publisher_bytes_acquired"])
        self.assertIsNone(source["original_publisher_bytes_sha256"])
        self.assertFalse(source["customer_engine_commercial_reuse_approved"])
        facts = item["historical_facts"]
        self.assertEqual(facts["shipment_weight_pounds"], 5744)
        # References are transcribed from the GAO decision, not original bill custody.
        self.assertEqual(facts["reported_carrier_name"], "PENNSYLVANIA_TRANSFER_COMPANY")
        self.assertEqual(facts["reported_carrier_bill_number"], "NC 23166")
        self.assertEqual(facts["reported_gbl_number"], "AF-7611030")
        self.assertEqual(facts["reported_gbl_date"], "1958-03-07")
        self.assertEqual(facts["reported_gao_claim_number"], "TK-172387")
        self.assertEqual(facts["reported_certificate_date"], "1960-06-20")
        self.assertTrue(facts["reported_refund_unpaid_on_certificate_date"])
        self.assertEqual(facts["carrier_charged_and_paid_cents"], 30590)
        self.assertEqual(facts["gao_applicable_ltl_charge_cents"], 15060)
        self.assertEqual(facts["gao_overcharge_certificate_cents"], 15530)
        self.assertEqual(facts["ltl_rate_cents_per_cwt"], 251)
        self.assertEqual(facts["ltl_rate_minimum_weight_pounds"], 6000)
        self.assertEqual(facts["ltl_rate_cents_per_cwt"] *
                         facts["ltl_rate_minimum_weight_pounds"] // 100, 15060)
        self.assertEqual(facts["carrier_charged_and_paid_cents"] -
                         facts["gao_applicable_ltl_charge_cents"], 15530)
        self.assertTrue(facts["full_visible_vehicle_capacity_noted_on_gbl"])
        self.assertFalse(facts["carrier_in_capacity_rule_eligible_list"])
        self.assertEqual(facts["capacity_load_rule"], "TARIFF_10_M_RULE_62_2")
        self.assertTrue(facts["certificate_of_indebtedness_issued"])
        # GAO directed a refund in 30 days; deduction/referral were contingent,
        # not authenticated settlement or a completed collection event.
        self.assertNotIn("refund_or_deduction_ordered", facts)
        self.assertEqual(facts["gao_refund_directed_within_days"], 30)
        self.assertTrue(facts["collection_by_deduction_or_justice_referral_contingent"])
        self.assertIsNone(facts["deduction_or_justice_referral_observed"])
        self.assertIsNone(facts["actual_refund_or_offset_collected"])
        self.assertEqual(facts["later_court_disposition"], "UNKNOWN")
        truth = item["truth_boundaries"]
        self.assertTrue(truth["historical_gao_adjudication_published"])
        self.assertFalse(truth["original_paid_invoice_or_gbl_bytes_held"])
        self.assertFalse(truth["original_governing_tariff_pages_held"])
        self.assertFalse(truth["independently_held_out_training_separation_verified"])
        self.assertEqual(truth["modern_contract_applicability"], "UNKNOWN")
        self.assertIsNone(truth["independent_private_customer_invoice_error_cents"])
        self.assertFalse(truth["customer_accuracy_scoring_permitted"])
        self.assertEqual(truth["retally_verified_cash_recovery_cents"], 0)
        controls = item["synthetic_negative_controls"]
        self.assertEqual(len(controls), 5)
        self.assertEqual(len({c["id"] for c in controls}), 5)
        self.assertTrue(all(c["kind"] == "SYNTHETIC" and
                            c["id"].startswith("SYNTHETIC_") for c in controls))
        self.assertEqual({c["expected"] for c in controls}, {
            "REJECT_WITHOUT_APPLICABLE_CARRIER_SPECIFIC_TARIFF_RULE",
            "UNKNOWN_REQUIRES_CONTEMPORANEOUS_TARIFF_AND_CARRIER_SCOPE",
            "REJECT_HISTORICAL_RATE_NOT_CURRENT_CONTRACT",
            "REJECT_NO_EVIDENCE_OF_CUSTOMER_SETTLEMENT_OR_RETALLY_RECOVERY",
            "REJECT_CITATION_IS_NOT_ORIGINAL_BILL_GBL_OR_PAYMENT_CUSTODY",
        })
        # B-152744 presents a DIFFERENT tariff and litigation caveat.
        # The 1961 case is a counterexample to universal 'full truck => TL' rules.
        other = PINNED["B-152744"]
        self.assertNotEqual(other["historical_tariff"], facts["capacity_load_rule"])
        self.assertTrue(other["further_review_explicitly_reserved"])
        self.assertTrue(item["quality"]["published_decision_arithmetic_reconciles"])
        self.assertFalse(item["quality"]["independent_customer_ground_truth_complete"])

    def test_b143458_wrong_money_tariff_scope_and_cash_promotions_are_red(self):
        """Reject altered authored evidence even when new data is self-consistent."""
        item = json.loads((FIXTURE.parent / "gao_b143458_capacity_v1.json").read_text())
        pinned = (
            ("historical_facts", "carrier_charged_and_paid_cents", 30590),
            ("historical_facts", "reported_carrier_bill_number", "NC 23166"),
            ("historical_facts", "reported_gbl_number", "AF-7611030"),
            ("historical_facts", "reported_gbl_date", "1958-03-07"),
            ("historical_facts", "reported_gao_claim_number", "TK-172387"),
            ("historical_facts", "reported_certificate_date", "1960-06-20"),
            ("historical_facts", "gao_refund_directed_within_days", 30),
            ("historical_facts", "collection_by_deduction_or_justice_referral_contingent", True),
            ("historical_facts", "deduction_or_justice_referral_observed", None),
            ("historical_facts", "gao_applicable_ltl_charge_cents", 15060),
            ("historical_facts", "gao_overcharge_certificate_cents", 15530),
            ("historical_facts", "carrier_in_capacity_rule_eligible_list", False),
            ("historical_facts", "actual_refund_or_offset_collected", None),
            ("source", "original_publisher_bytes_sha256", None),
            ("source", "customer_engine_commercial_reuse_approved", False),
            ("truth_boundaries", "independently_held_out_training_separation_verified", False),
            ("truth_boundaries", "original_paid_invoice_or_gbl_bytes_held", False),
            ("truth_boundaries", "customer_accuracy_scoring_permitted", False),
            ("truth_boundaries", "retally_verified_cash_recovery_cents", 0),
        )
        def assert_pinned(row):
            for section, field, value in pinned:
                self.assertEqual(row[section][field], value)
        assert_pinned(item)
        for section, field, original in pinned:
            with self.subTest(section=section, field=field):
                forged = copy.deepcopy(item)
                forged[section][field] = (
                    True if original is False else
                    1 if original is None or original == 0 else
                    "FORGED" if isinstance(original, str) else original + 1
                )
                with self.assertRaises(AssertionError):
                    assert_pinned(forged)
        self.assertNotEqual(digest({**item, "fixture_id": "FORGED"}), digest(item))



    def test_b145308_real_gao_deduction_is_not_requested_refund_or_retally_cash(self):
        """Pin 1961 decision-only evidence: paid, deducted, requested are distinct."""
        item = json.loads((FIXTURE.parent / "gao_b145308_deduction_v1.json").read_text())
        self.assertEqual(item["schema_version"], "1.0.0")
        self.assertEqual(item["fixture_id"], "GAO_B145308_DEDUCTION_VS_REQUESTED_REFUND_V1")
        self.assertEqual(item["evaluation_family"],
                         "FREIGHT_ERROR_ADJUDICATION_HISTORICAL_DECISION_ONLY")
        source = item["source"]
        self.assertEqual(source["official_url"], "https://www.gao.gov/products/b-145308")
        self.assertIn(source["official_url"], SEEDS["freightrecovery"])
        self.assertEqual(source["decision_date"], "1961-08-14")
        self.assertEqual(source["rights_reference"], "https://www.gao.gov/copyright")
        self.assertFalse(source["original_publisher_bytes_acquired"])
        self.assertIsNone(source["original_publisher_bytes_sha256"])
        self.assertFalse(source["customer_engine_commercial_reuse_approved"])
        facts = item["historical_facts"]
        self.assertEqual(facts["shipment_date"], "1957-04-18")
        self.assertEqual(facts["gbl_number_reported_by_gao"], "AF-7288198")
        self.assertEqual(facts["original_payment_cents"], 130883)
        self.assertEqual(facts["actual_gao_reported_deduction_cents"], 28283)
        self.assertEqual(facts["net_payment_after_reported_deduction_cents"], 102600)
        self.assertEqual(facts["gao_computed_applicable_charge_cents"], 52950)
        self.assertEqual(facts["additional_refund_requested_cents"], 49650)
        self.assertEqual(130883 - 28283, 102600)
        self.assertEqual(102600 - 52950, 49650)
        self.assertIsNone(facts["additional_refund_collected_cents"])
        self.assertEqual(facts["separate_carrier_additional_charge_claim_cents"], 28263)
        self.assertNotEqual(facts["separate_carrier_additional_charge_claim_cents"],
                            facts["actual_gao_reported_deduction_cents"])
        self.assertEqual(facts["regulation_effective_date"], "1959-10-12")
        self.assertFalse(facts["regulation_applicable_to_1957_shipment"])
        self.assertTrue(facts["receiving_signature_proved_goods_received_not_exclusive_use"])
        self.assertFalse(facts["exclusive_use_furnished_proven"])
        self.assertTrue(facts["possible_later_carrier_reconsideration_on_new_evidence"])
        self.assertEqual(facts["outcome_after_decision"], "UNKNOWN")
        truth = item["truth_boundaries"]
        self.assertTrue(truth["actual_historical_deduction_is_published_gao_report"])
        self.assertTrue(truth["additional_refund_is_request_not_verified_collection"])
        self.assertFalse(truth["original_paid_invoice_or_gbl_bytes_held"])
        self.assertFalse(truth["independently_held_out_training_separation_verified"])
        self.assertIsNone(truth["independent_private_customer_invoice_error_cents"])
        self.assertFalse(truth["customer_accuracy_scoring_permitted"])
        self.assertEqual(truth["retally_verified_cash_recovery_cents"], 0)

    def test_b145308_synthetic_adversarial_claims_and_forged_promotions_rejected(self):
        """Counterfactual cases are synthetic; the original source claim stays bounded."""
        item = json.loads((FIXTURE.parent / "gao_b145308_deduction_v1.json").read_text())
        controls = item["synthetic_negative_controls"]
        self.assertEqual(len(controls), 5)
        self.assertEqual(len({c["id"] for c in controls}), 5)
        self.assertTrue(all(c["kind"] == "SYNTHETIC" and c["id"].startswith("SYNTHETIC_")
                            for c in controls))
        self.assertEqual({c["expected"] for c in controls}, {
            "REJECT_UNOBSERVED_COLLECTION",
            "REJECT_DISTINCT_AMOUNTS_AND_OUTCOMES",
            "REJECT_LATER_EFFECTIVE_DATE",
            "REJECT_MISSING_EXCLUSIVE_USE_PROOF",
            "REJECT_NO_MODERN_CUSTOMER_SETTLEMENT_EVIDENCE",
        })
        pinned = (
            ("historical_facts", "actual_gao_reported_deduction_cents", 28283),
            ("historical_facts", "separate_carrier_additional_charge_claim_cents", 28263),
            ("historical_facts", "additional_refund_requested_cents", 49650),
            ("historical_facts", "additional_refund_collected_cents", None),
            ("historical_facts", "regulation_applicable_to_1957_shipment", False),
            ("historical_facts", "exclusive_use_furnished_proven", False),
            ("source", "original_publisher_bytes_sha256", None),
            ("source", "customer_engine_commercial_reuse_approved", False),
            ("truth_boundaries", "original_paid_invoice_or_gbl_bytes_held", False),
            ("truth_boundaries", "customer_accuracy_scoring_permitted", False),
            ("truth_boundaries", "retally_verified_cash_recovery_cents", 0),
        )
        def verify(values):
            for section, field, expected in pinned:
                self.assertEqual(values[section][field], expected)
            x = values["historical_facts"]
            self.assertEqual(x["original_payment_cents"] -
                             x["actual_gao_reported_deduction_cents"],
                             x["net_payment_after_reported_deduction_cents"])
            self.assertEqual(x["net_payment_after_reported_deduction_cents"] -
                             x["gao_computed_applicable_charge_cents"],
                             x["additional_refund_requested_cents"])
        verify(item)
        for section, field, expected in pinned:
            with self.subTest(field=field):
                forged = copy.deepcopy(item)
                forged[section][field] = (
                    True if expected is False else
                    1 if expected is None or expected == 0 else expected + 1
                )
                with self.assertRaises(AssertionError):
                    verify(forged)
        self.assertNotEqual(digest({**item, "fixture_id": "FORGED"}), digest(item))



    def test_b148981_three_reported_historical_refunds_and_credit_are_not_modern_labels(self):
        """Official decision's refunded amounts differ from unverified future credits."""
        item = json.loads((FIXTURE.parent / "gao_b148981_refunded_adjustment_candidate_v0.json").read_text())
        source = item["source"]
        self.assertEqual(item["admission_state"],
                         "OFFICIAL_DECISION_ONLY_NOT_INDEPENDENT_INVOICE_HOLDOUT")
        self.assertEqual(item["evaluation_family"],
                         "FREIGHT_ERROR_ADJUDICATION_HISTORICAL_DECISION_ONLY")
        self.assertEqual(source["official_url"], "https://www.gao.gov/products/b-148981")
        self.assertIn(source["official_url"], SEEDS["freightrecovery"])
        self.assertEqual(source["decision_date"], "1962-11-29")
        self.assertEqual(source["rights_reference"], "https://www.gao.gov/copyright")
        self.assertIsNone(source["original_publisher_http_sha256"])
        self.assertFalse(source["original_publisher_http_bytes_acquired"])
        self.assertFalse(source["customer_engine_commercial_reuse_approved"])
        cases = item["historical_case_groups"]
        self.assertEqual([x["supplemental_bill"] for x in cases], ["5188", "5193", "5190"])
        self.assertEqual([x["gao_reported_refund_cents"] for x in cases],
                         [13444, 4602, 166154])
        self.assertEqual([x["carrier_amended_supplemental_claim_cents"] for x in cases],
                         [50944, 6429, 122405])
        self.assertTrue(all(x["gao_says_refund_occurred"] for x in cases))
        self.assertTrue(all(len(x["original_paid_by_bol_cents"]) == x["reported_bol_count"]
                            for x in cases))
        self.assertEqual(sum(x["gao_reported_refund_cents"] for x in cases), 184200)
        self.assertEqual(item["reported_historical_refunds_total_cents"], 184200)
        self.assertTrue(cases[1]["cross_referenced_volume_shipment_rate_group"])
        self.assertTrue(cases[2]["credit_decision_is_future_direction_not_verified_posting"])
        self.assertEqual(cases[2]["future_carrier_credit_allowed_cents"], 39174)
        self.assertTrue(all(x["future_carrier_credit_paid_cents"] is None for x in cases))
        truth = item["truth_boundaries"]
        self.assertTrue(truth["historical_refunds_reported_by_gao_not_independently_bank_cleared"])
        self.assertFalse(truth["independent_payment_provider_verification"])
        self.assertFalse(truth["freight_error_precision_recall_scoring_allowed"])
        self.assertEqual(truth["independently_held_out_customer_labels"], 0)
        self.assertEqual(truth["contemporary_rate_applicability"], "UNKNOWN")
        self.assertEqual(truth["retally_verified_customer_cash_cents"], 0)

    def test_b148981_synthetic_refund_credit_and_volume_forgery_are_rejected(self):
        """Adversarial edits cannot convert decision-only data into settlement truth."""
        item = json.loads((FIXTURE.parent / "gao_b148981_refunded_adjustment_candidate_v0.json").read_text())
        controls = item["synthetic_negative_controls"]
        self.assertEqual(len(controls), 7)
        self.assertEqual(len({row["id"] for row in controls}), 7)
        self.assertTrue(all(row["kind"] == "SYNTHETIC" and
                            row["id"].startswith("SYNTHETIC_") for row in controls))
        self.assertEqual({row["expected"] for row in controls}, {
            "REJECT_INDEPENDENT_CASH_EVIDENCE_ABSENT",
            "REJECT_CREDIT_POSTING_NOT_VERIFIED",
            "REJECT_VOLUME_SHIPMENT_GROUPING_ERROR",
            "REJECT_OPPOSING_PARTY_CLAIM_SEMANTICS",
            "REJECT_HISTORICAL_RATE_APPLICABILITY",
            "REJECT_CUSTOMER_AND_SETTLEMENT_PROVENANCE",
            "REJECT_GAO_TRANSCRIBED_BOL_LINEAGE_CONFLICT",
        })
        pinned = (
            ("historical_case_groups", 0, "gao_reported_refund_cents", 13444),
            ("historical_case_groups", 1, "gao_reported_refund_cents", 4602),
            ("historical_case_groups", 2, "gao_reported_refund_cents", 166154),
            ("historical_case_groups", 2, "future_carrier_credit_paid_cents", None),
            ("source", None, "original_publisher_http_sha256", None),
            ("source", None, "customer_engine_commercial_reuse_approved", False),
            ("truth_boundaries", None, "freight_error_precision_recall_scoring_allowed", False),
            ("truth_boundaries", None, "retally_verified_customer_cash_cents", 0),
        )
        def verify(row):
            for key, index, field, value in pinned:
                target = row[key] if index is None else row[key][index]
                self.assertEqual(target[field], value)
            self.assertEqual(sum(c["gao_reported_refund_cents"]
                                 for c in row["historical_case_groups"]),
                             row["reported_historical_refunds_total_cents"])
        verify(item)
        for key, index, field, value in pinned:
            with self.subTest(field=field):
                changed = copy.deepcopy(item)
                target = changed[key] if index is None else changed[key][index]
                target[field] = (True if value is False else
                                 1 if value is None or value == 0 else value + 1)
                with self.assertRaises(AssertionError):
                    verify(changed)
        self.assertNotEqual(digest({**item, "fixture_id": "FORGED"}), digest(item))



    def test_b148981_decision_transcribed_bol_lineage_blocks_cross_supplemental_join(self):
        """Seven original payment references are GAO transcriptions, not seven held invoices."""
        item = json.loads((FIXTURE.parent /
                           "gao_b148981_refunded_adjustment_candidate_v0.json").read_text())
        expected = [
            [("WY 7616843", "1958-04-21", 175500)],
            [("AF-6807627", "1956-10-15", 33833),
             ("AF-6807626", "1956-10-15", 41438),
             ("AF-6807628", "1956-10-16", 26432)],
            [("WY-6564503", "1955-11-02", 132620),
             ("WY-6564509", "1955-11-02", 107213),
             ("WY-6564515", "1955-11-03", 132571)],
        ]
        self.assertEqual(item["schema_version"], "0.1.1")
        self.assertEqual(item["source"]["bol_lineage_proof"],
                         "GAO_DECISION_TRANSCRIPTION_NOT_ORIGINAL_BOL_CUSTODY")
        self.assertFalse(item["source"]["original_bol_invoice_tariff_bytes_held"])
        self.assertIsNone(item["source"]["original_publisher_http_sha256"])
        def validate_bol_map(doc):
            groups = doc["historical_case_groups"]
            actual = [[(r["bol_reference"], r["bill_of_lading_date"],
                        r["gao_reported_paid_cents"]) for r in group["gao_transcribed_bol_refs"]]
                      for group in groups]
            self.assertEqual(actual, expected)
            refs = [ref[0] for group in actual for ref in group]
            self.assertEqual(len(refs), 7)
            self.assertEqual(len(refs), len(set(refs)))
            for group in groups:
                self.assertEqual([r["gao_reported_paid_cents"] for r in group["gao_transcribed_bol_refs"]],
                                 group["original_paid_by_bol_cents"])
                self.assertEqual(len(group["gao_transcribed_bol_refs"]), group["reported_bol_count"])
        validate_bol_map(item)
        # Both mutations are SYNTHETIC adversarial controls, not source facts.
        forged_join = copy.deepcopy(item)
        forged_join["historical_case_groups"][1]["gao_transcribed_bol_refs"][0]["bol_reference"] = "WY 7616843"
        with self.assertRaises(AssertionError):
            validate_bol_map(forged_join)
        forged_charge = copy.deepcopy(item)
        forged_charge["historical_case_groups"][2]["gao_transcribed_bol_refs"][0]["gao_reported_paid_cents"] += 1
        with self.assertRaises(AssertionError):
            validate_bol_map(forged_charge)
        self.assertFalse(item["truth_boundaries"]["freight_error_precision_recall_scoring_allowed"])
        self.assertEqual(item["truth_boundaries"]["independently_held_out_customer_labels"], 0)

    def test_b190624_original_gao_pdf_two_cases_and_reported_deduction_limits(self):
        """Pin historically reported first deduction; never turn claims into cash truth."""
        item = json.loads((FIXTURE.parent / "gao_b190624_settlement_provenance_candidate_v0.json").read_text())
        self.assertEqual(item["schema_version"], "0.1.0")
        self.assertEqual(item["admission_state"],
                         "GAO_ORIGINAL_DECISION_VISUALLY_REVIEWED_NOT_INDEPENDENT_INVOICE_HOLDOUT")
        self.assertEqual(item["source"]["official_pdf_url"],
                         "https://www.gao.gov/assets/b-190624.pdf")
        self.assertIn(item["source"]["official_pdf_url"], SEEDS["freightrecovery"])
        self.assertEqual(item["source"]["decision_date"], "1978-08-29")
        self.assertEqual(item["source"]["official_pdf_pages"], 5)
        self.assertEqual(item["source"]["visually_checked_original_pdf_pages"], [1, 2, 5])
        self.assertIsNone(item["source"]["original_publisher_pdf_sha256"])
        self.assertFalse(item["source"]["original_publisher_pdf_bytes_retained"])
        self.assertFalse(item["source"]["customer_engine_commercial_reuse_approved"])
        self.assertEqual(len(item["historical_cases"]), 2)
        first, second = item["historical_cases"]
        self.assertEqual(first["case_id"], "H-1876085")
        self.assertEqual(first["gao_reported_carrier_paid_cents"], 315390)
        self.assertEqual(first["gao_reported_notice_overcharge_cents"], 124264)
        self.assertTrue(first["gao_reports_deduction_collected"])
        self.assertEqual(first["gao_reported_deduction_dates"], ["1974-11-08", "1975-06-09"])
        self.assertFalse(first["independent_payment_provider_receipt"])
        self.assertEqual(first["carrier_followup_claim_cents"], 143375)
        self.assertEqual(first["printed_excess_over_deduction_cents"], 19110)
        self.assertEqual(first["arithmetic_excess_over_deduction_cents"], 19111)
        self.assertEqual(first["carrier_followup_claim_cents"] -
                         first["gao_reported_notice_overcharge_cents"], 19111)
        self.assertTrue(first["one_cent_original_decision_numeric_disagreement"])
        self.assertIsNone(first["commissioned_final_settlement_amount_cents"])
        self.assertEqual(second["case_id"], "F-8824363")
        self.assertEqual(second["gao_reported_original_carrier_billed_cents"], 715185)
        self.assertEqual(second["gao_reported_loss_and_damage_deduction_cents"], 406140)
        self.assertEqual(second["gao_reported_net_carrier_paid_cents"], 309045)
        self.assertEqual(715185 - 406140, 309045)
        self.assertEqual(second["gao_reported_overcharge_deduction_cents_in_admin_report"], 246850)
        self.assertIsNone(second["overcharge_deduction_date"])
        self.assertFalse(second["overcharge_deduction_independently_verified"])
        self.assertFalse(second["overcharge_deduction_source_documents_held"])
        self.assertIsNone(second["commissioned_final_settlement_amount_cents"])
        self.assertTrue(item["decision_scope"]["gao_directs_settlement_subject_to_authorized_deduction_and_three_year_limit"])
        self.assertFalse(item["truth_boundaries"]["modern_customer_error_precision_recall_allowed"])
        self.assertEqual(item["truth_boundaries"]["retally_verified_recovered_cash_cents"], 0)

    def test_b190624_misclassification_one_cent_and_cash_negative_controls(self):
        """Source typo, loss/damage, administrative report and late settlement fail closed."""
        item = json.loads((FIXTURE.parent / "gao_b190624_settlement_provenance_candidate_v0.json").read_text())
        controls = item["synthetic_negative_controls"]
        self.assertEqual(len(controls), 7)
        self.assertEqual(len({x["id"] for x in controls}), 7)
        self.assertTrue(all(x["kind"] == "SYNTHETIC" and x["id"].startswith("SYNTHETIC_")
                            for x in controls))
        self.assertEqual({x["expected"] for x in controls}, {
            "REJECT_MISMATCHED_DEDUCTION_CAUSE",
            "REJECT_SECOND_SHIPMENT_UNDATED_UNVERIFIED_COLLECTION",
            "REJECT_UNKNOWN_POST_DECISION_SETTLEMENT",
            "REJECT_TENDER_SCOPE_COLLISION",
            "REJECT_SILENT_SOURCE_CORRECTION",
            "REJECT_MODERN_CUSTOMER_CASH_CLAIM",
            "REJECT_SOURCE_TOTAL_REWRITE",
        })
        def verify(row):
            first, second = row["historical_cases"]
            self.assertEqual(first["gao_reported_notice_overcharge_cents"], 124264)
            self.assertEqual(first["printed_excess_over_deduction_cents"], 19110)
            self.assertEqual(first["arithmetic_excess_over_deduction_cents"], 19111)
            self.assertTrue(first["one_cent_original_decision_numeric_disagreement"])
            self.assertFalse(first["independent_payment_provider_receipt"])
            self.assertIsNone(second["overcharge_deduction_date"])
            self.assertFalse(second["overcharge_deduction_independently_verified"])
            self.assertEqual(second["gao_reported_loss_and_damage_deduction_cents"], 406140)
            self.assertIsNone(first["commissioned_final_settlement_amount_cents"])
            self.assertIsNone(second["commissioned_final_settlement_amount_cents"])
            self.assertIsNone(row["source"]["original_publisher_pdf_sha256"])
            self.assertFalse(row["source"]["customer_engine_commercial_reuse_approved"])
            self.assertEqual(row["truth_boundaries"]["retally_verified_recovered_cash_cents"], 0)
        verify(item)
        for key, field, bad in (
            ("historical_cases.0", "printed_excess_over_deduction_cents", 19111),
            ("historical_cases.0", "independent_payment_provider_receipt", True),
            ("historical_cases.1", "overcharge_deduction_date", "1975-01-01"),
            ("historical_cases.1", "overcharge_deduction_independently_verified", True),
            ("historical_cases.1", "gao_reported_loss_and_damage_deduction_cents", 0),
            ("source", "customer_engine_commercial_reuse_approved", True),
            ("truth_boundaries", "retally_verified_recovered_cash_cents", 124264),
        ):
            with self.subTest(field=field):
                forged = copy.deepcopy(item)
                obj = forged
                for part in key.split("."):
                    obj = obj[int(part)] if part.isdigit() else obj[part]
                obj[field] = bad
                with self.assertRaises(AssertionError):
                    verify(forged)
        self.assertNotEqual(digest({**item, "fixture_id": "FORGED"}), digest(item))

    def test_b190624_two_distinct_one_cent_disagreements_are_not_silently_fixed(self):
        """Original PDF p1 reports $3,902.24; p2 two claims sum to $3,902.25."""
        item = json.loads((FIXTURE.parent /
                           "gao_b190624_settlement_provenance_candidate_v0.json").read_text())
        total = item["claim_total_crosscheck"]
        self.assertEqual(total["source_pages"], {"printed_total": 1, "component_claims": 2})
        self.assertEqual(total["gao_printed_total_disallowed_claims_cents"], 390224)
        self.assertEqual(total["sum_of_two_gao_reported_carrier_claims_cents"], 390225)
        component_sum = sum(c["carrier_followup_claim_cents"] for c in item["historical_cases"])
        self.assertEqual(component_sum, total["sum_of_two_gao_reported_carrier_claims_cents"])
        self.assertEqual(total["difference_cents"],
                         component_sum - total["gao_printed_total_disallowed_claims_cents"])
        self.assertEqual(total["difference_cents"], 1)
        self.assertEqual(item["quality"]["distinct_one_cent_publisher_disagreement_count"], 2)
        self.assertTrue(total["requires_independent_reconciliation"])
        self.assertFalse(total["customer_cash_proved"])
        self.assertFalse(item["truth_boundaries"]["modern_customer_error_precision_recall_allowed"])

        forged = json.loads(json.dumps(item))
        forged["claim_total_crosscheck"]["gao_printed_total_disallowed_claims_cents"] = 390225
        self.assertNotEqual(forged["claim_total_crosscheck"]["gao_printed_total_disallowed_claims_cents"],
                            390224)
        self.assertNotEqual(digest(forged), digest(item))


    def test_b142112_original_decision_separates_request_service_and_reported_cash(self):
        """GAO historical deduction is source-observed; original service proof is absent."""
        item = json.loads((FIXTURE.parent /
                           "gao_b142112_exclusive_use_proof_candidate_v0.json").read_text())
        self.assertEqual(item["schema_version"], "0.1.0")
        self.assertEqual(item["admission_state"],
                         "OFFICIAL_GAO_DECISION_ONLY_NOT_ORIGINAL_INVOICE_OR_HELDOUT_TRUTH")
        self.assertEqual(item["evaluation_family"],
                         "FREIGHT_ERROR_ADJUDICATION_HISTORICAL_DECISION_ONLY")
        src = item["source"]
        self.assertEqual(src["official_url"], "https://www.gao.gov/products/b-142112-1")
        self.assertIn(src["official_url"], SEEDS["freightrecovery"])
        self.assertEqual(src["decision_date"], "1960-11-23")
        self.assertEqual(src["rights_reference"], "https://www.gao.gov/copyright")
        self.assertFalse(src["original_publisher_response_bytes_held"])
        self.assertIsNone(src["original_publisher_response_sha256"])
        self.assertFalse(src["original_carrier_invoice_gbl_tariff_bytes_held"])
        self.assertIsNone(src["governing_tariff_effective_date"])
        self.assertFalse(src["customer_engine_commercial_reuse_approved"])
        scope = item["decision_scope"]
        self.assertEqual(scope["carrier_requests_reviewed"], 19)
        self.assertEqual(scope["claims_with_revised_settlements_authorized"], 12)
        self.assertIsNone(scope["revised_settlements_observed_paid_count"])
        self.assertTrue(scope["exclusive_use_entitlement_requires_shipper_request"])
        self.assertTrue(scope["exclusive_use_entitlement_requires_proven_carrier_performance"])
        self.assertEqual(len(item["historical_cases"]), 2)
        first, second = item["historical_cases"]
        self.assertEqual(first["gbl_number_reported"], "WY-4250601")
        self.assertEqual(first["supplemental_bill"], "7854-A")
        self.assertEqual(first["original_carrier_freight_paid_cents"], 45000)
        self.assertEqual(first["gao_reported_truckload_charge_cents"], 35820)
        self.assertEqual(first["gao_reported_overpayment_cents"], 9180)
        self.assertEqual(45000 - 35820, 9180)
        self.assertTrue(first["gao_reports_deduction_collected"])
        self.assertFalse(first["independently_authenticated_bank_offset_receipt"])
        self.assertTrue(first["exclusive_use_requested_on_bol"])
        self.assertEqual(first["reported_origin_seal"], "1895936")
        self.assertEqual(first["reported_destination_seal"], "40530")
        self.assertNotEqual(first["reported_origin_seal"], first["reported_destination_seal"])
        self.assertFalse(first["seals_match"])
        self.assertFalse(first["exclusive_use_furnished_proven"])
        self.assertTrue(first["carrier_reclaim_disallowed_and_sustained"])
        self.assertEqual(second["gbl_number_reported"], "AF-6538038")
        self.assertEqual(second["initial_reclaim_bill"], "9911-A")
        self.assertEqual(second["later_reclaim_bill"], "7711-A")
        self.assertEqual(second["initial_reclaim_requested_cents"], 29215)
        self.assertEqual(second["later_reclaim_requested_cents"], 29275)
        self.assertFalse(second["same_reclaim_bill_identity"])
        self.assertEqual(second["original_carrier_freight_paid_cents"], 88740)
        self.assertEqual(second["gao_first_audit_allowable_charge_cents"], 59465)
        self.assertEqual(second["first_overcharge_deduction_collected_cents"], 29275)
        self.assertEqual(second["later_audit_allowable_charge_cents"], 46421)
        self.assertEqual(second["later_statement_additional_overcharge_cents"], 13044)
        self.assertEqual(second["concluding_paragraph_refund_requested_cents"], 13040)
        self.assertEqual(second["conflicting_published_refund_amount_cents"], 4)
        self.assertEqual(88740 - 59465, 29275)
        self.assertEqual(88740 - 46421, 42319)
        self.assertEqual(29275 + 13044, 42319)
        self.assertEqual(13044 - 13040, 4)
        self.assertFalse(second["gao_reports_additional_refund_collected"])
        self.assertIsNone(second["later_additional_refund_collected_cents"])
        self.assertFalse(second["exclusive_use_furnished_proven"])
        self.assertFalse(item["truth_boundaries"]["independent_holdout_verification"])
        self.assertFalse(item["truth_boundaries"]["modern_customer_freight_error_accuracy_scoring_allowed"])
        self.assertEqual(item["truth_boundaries"]["independently_held_out_customer_labels"], 0)
        self.assertEqual(item["truth_boundaries"]["modern_applicability"], "UNKNOWN")
        self.assertEqual(item["truth_boundaries"]["actual_retally_customer_recovered_cash_cents"], 0)

    def test_b142112_negative_controls_reject_forged_proof_and_refund_normalization(self):
        """Counterfactual edits must not erase published contradictions or mint payment."""
        item = json.loads((FIXTURE.parent /
                           "gao_b142112_exclusive_use_proof_candidate_v0.json").read_text())
        controls = item["synthetic_negative_controls"]
        self.assertEqual(len(controls), 7)
        self.assertEqual(len({x["id"] for x in controls}), 7)
        self.assertTrue(all(x["kind"] == "SYNTHETIC" and
                            x["id"].startswith("SYNTHETIC_") for x in controls))
        self.assertEqual({x["expected"] for x in controls}, {
            "REJECT_PROOF_OF_PERFORMANCE_ABSENT",
            "REJECT_SEAL_IDENTITY_CONTRADICTION",
            "REJECT_SILENT_BILL_AND_AMOUNT_NORMALIZATION",
            "REJECT_FOUR_CENT_SOURCE_DISAGREEMENT_ERASURE",
            "REJECT_UNVERIFIED_ADDITIONAL_REFUND",
            "REJECT_12_OF_19_IS_NOT_19_PAID",
            "REJECT_NO_CONTEMPORARY_CUSTOMER_OR_PAYMENT_EVIDENCE",
        })
        def verify(row):
            first, second = row["historical_cases"]
            self.assertEqual(row["decision_scope"]["claims_with_revised_settlements_authorized"], 12)
            self.assertIsNone(row["decision_scope"]["revised_settlements_observed_paid_count"])
            self.assertNotEqual(first["reported_origin_seal"], first["reported_destination_seal"])
            self.assertFalse(first["exclusive_use_furnished_proven"])
            self.assertFalse(second["exclusive_use_furnished_proven"])
            self.assertEqual(second["initial_reclaim_requested_cents"], 29215)
            self.assertEqual(second["later_reclaim_requested_cents"], 29275)
            self.assertEqual(second["later_statement_additional_overcharge_cents"], 13044)
            self.assertEqual(second["concluding_paragraph_refund_requested_cents"], 13040)
            self.assertEqual(second["later_statement_additional_overcharge_cents"] -
                             second["concluding_paragraph_refund_requested_cents"], 4)
            self.assertIsNone(second["later_additional_refund_collected_cents"])
            self.assertIsNone(row["source"]["original_publisher_response_sha256"])
            self.assertFalse(row["source"]["customer_engine_commercial_reuse_approved"])
            self.assertFalse(row["truth_boundaries"]["modern_customer_freight_error_accuracy_scoring_allowed"])
            self.assertEqual(row["truth_boundaries"]["actual_retally_customer_recovered_cash_cents"], 0)
        verify(item)
        mutations = (
            ("decision_scope", None, "claims_with_revised_settlements_authorized", 19),
            ("decision_scope", None, "revised_settlements_observed_paid_count", 12),
            ("historical_cases", 0, "reported_destination_seal", "1895936"),
            ("historical_cases", 0, "exclusive_use_furnished_proven", True),
            ("historical_cases", 1, "initial_reclaim_requested_cents", 29275),
            ("historical_cases", 1, "later_statement_additional_overcharge_cents", 13040),
            ("historical_cases", 1, "later_additional_refund_collected_cents", 13040),
            ("source", None, "original_publisher_response_sha256", "FORGED"),
            ("source", None, "customer_engine_commercial_reuse_approved", True),
            ("truth_boundaries", None, "modern_customer_freight_error_accuracy_scoring_allowed", True),
            ("truth_boundaries", None, "actual_retally_customer_recovered_cash_cents", 13040),
        )
        for section, index, key, false_value in mutations:
            with self.subTest(field=key):
                forged = copy.deepcopy(item)
                (forged[section] if index is None else forged[section][index])[key] = false_value
                with self.assertRaises(AssertionError):
                    verify(forged)
        self.assertNotEqual(digest({**item, "fixture_id": "FORGED"}), digest(item))


    def test_b168539_promised_refund_is_not_received_payment_or_approved_claim(self):
        """Official GAO original decision separates payees, promise, and cash."""
        case = json.loads((FIXTURE.parent / "gao_b168539_promised_refund_candidate_v0.json")
                          .read_text(encoding="utf-8"))
        self.assertEqual(case["schema_version"], "0.1.0")
        self.assertEqual(case["evaluation_family"],
                         "FREIGHT_SETTLEMENT_PROVENANCE_HISTORICAL_DECISION_ONLY")
        self.assertEqual(case["admission_state"],
                         "OFFICIAL_GAO_DECISION_METADATA_NOT_ORIGINAL_INVOICE_OR_INDEPENDENT_PAYMENT_TRUTH")
        src = case["source"]
        self.assertEqual(src["official_url"], "https://www.gao.gov/products/b-168539")
        self.assertIn(src["official_url"], SEEDS["freightrecovery"])
        self.assertEqual(SEEDS["freightrecovery"].count(src["official_url"]), 1)
        self.assertEqual(src["decision_date"], "1970-09-29")
        self.assertEqual(src["rights_reference"], "https://www.gao.gov/copyright")
        self.assertFalse(src["customer_engine_commercial_reuse_approved"])
        self.assertFalse(src["original_publisher_response_bytes_acquired"])
        self.assertIsNone(src["original_publisher_response_sha256"])
        self.assertFalse(src["original_gbl_freight_bill_voucher_bytes_acquired"])
        h = case["historically_reported_facts"]
        self.assertEqual(h["gbl_date_reported"], "1968-06-07")
        self.assertEqual(h["competing_carrier_bill_reference_transcribed"], "A-820099")
        self.assertEqual(h["delivering_carrier_paid_bill_reference_transcribed"], "0069")
        self.assertEqual(h["navy_paid_voucher_reference_transcribed"], "K-6740")
        self.assertNotEqual(h["competing_carrier_bill_reference_transcribed"],
                            h["delivering_carrier_paid_bill_reference_transcribed"])
        self.assertFalse(h["cited_bill_and_voucher_originals_acquired"])
        self.assertTrue(case["quality"]["competing_and_paid_bills_are_distinct_transactions"])
        self.assertEqual(h["original_competing_carrier_claim_cents"], 98970)
        self.assertEqual(h["navy_payment_to_delivering_carrier_cents"], 95120)
        self.assertEqual(h["competing_carrier_reduced_claim_cents"], 37966)
        self.assertEqual(h["delivering_carrier_promised_refund_cents"], 37966)
        self.assertTrue(h["navy_payment_reported_by_gao"])
        self.assertFalse(h["independently_authenticated_navy_payment_receipt_held"])
        self.assertFalse(h["gao_reported_refund_received_as_of_decision"])
        self.assertIsNone(h["refund_received_after_decision_cents"])
        self.assertFalse(h["gao_certified_competing_carrier_claim"])
        self.assertFalse(h["government_second_payment_to_competing_carrier_verified"])
        self.assertTrue(h["waiver_forgery_alleged_by_claimant"])
        self.assertIsNone(h["waiver_forgery_independently_adjudicated"])
        self.assertEqual(h["final_intercarrier_allocation"], "UNKNOWN")
        b = case["truth_boundaries"]
        self.assertFalse(b["independent_holdout_training_separation_verified"])
        self.assertEqual(b["independent_customer_payment_labels"], 0)
        self.assertFalse(b["modern_customer_freight_error_precision_recall_allowed"])
        self.assertFalse(b["modern_accounting_reconciliation_accuracy_allowed"])
        self.assertEqual(b["retally_verified_recovered_cash_cents"], 0)
        self.assertTrue(case["quality"]["financial_claim_vs_received_funds_separated"])

        from freight.unified_research_lab import ledger_from, merge_sources
        entry, added = merge_sources(ledger_from([]), "freightrecovery",
                                     [src["official_url"], src["official_url"]], "2026-10-25")
        self.assertEqual(added, 1)
        self.assertEqual(len(entry["entries"]), 1)
        again, new = merge_sources(entry, "freightrecovery", [src["official_url"]], "2026-10-25")
        self.assertEqual(new, 0)
        self.assertEqual(again, entry)
        self.assertFalse(entry["entries"][0]["commercial_reuse_authorized"])
        self.assertFalse(entry["entries"][0]["recovered_cash_verified"])

    def test_b168539_synthetic_counterfactuals_reject_promoted_cash_and_forgery(self):
        """Adversarial mutations must fail the case-specific source contract."""
        case = json.loads((FIXTURE.parent / "gao_b168539_promised_refund_candidate_v0.json")
                          .read_text(encoding="utf-8"))
        controls = case["synthetic_negative_controls"]
        self.assertEqual(len(controls), 8)
        self.assertEqual(len({c["id"] for c in controls}), 8)
        self.assertTrue(all(c["kind"] == "SYNTHETIC" and
                            c["id"].startswith("SYNTHETIC_") for c in controls))
        self.assertEqual({c["expected"] for c in controls}, {
            "REJECT_GAO_EXPLICITLY_REPORTS_NOT_RECEIVED_AS_OF_DECISION",
            "REJECT_GAO_DISALLOWED_COMPETING_CARRIER_CLAIM",
            "REJECT_DIFFERENT_PAYEES_AND_TRANSACTION_TYPES",
            "UNKNOWN_NOT_ADJUDICATED_IN_GAO_DECISION",
            "REJECT_GAO_CONSIDERED_CONTRARY_ACTUAL_DELIVERY_EVIDENCE",
            "REJECT_NO_MODERN_CUSTOMER_OR_RETALLY_SETTLEMENT",
            "REJECT_DISTINCT_CARRIER_PAYEES_AND_BILL_REFERENCES",
            "REJECT_GAO_TRANSCRIPTION_IS_NOT_VOUCHER_CUSTODY",
        })

        def verify(row):
            src, h, truth = row["source"], row["historically_reported_facts"], row["truth_boundaries"]
            self.assertFalse(src["customer_engine_commercial_reuse_approved"])
            self.assertIsNone(src["original_publisher_response_sha256"])
            self.assertEqual(h["navy_payment_to_delivering_carrier_cents"], 95120)
            self.assertEqual(h["competing_carrier_bill_reference_transcribed"], "A-820099")
            self.assertEqual(h["delivering_carrier_paid_bill_reference_transcribed"], "0069")
            self.assertEqual(h["navy_paid_voucher_reference_transcribed"], "K-6740")
            self.assertFalse(h["cited_bill_and_voucher_originals_acquired"])
            self.assertTrue(row["quality"]["competing_and_paid_bills_are_distinct_transactions"])
            self.assertEqual(h["competing_carrier_reduced_claim_cents"], 37966)
            self.assertEqual(h["delivering_carrier_promised_refund_cents"], 37966)
            self.assertFalse(h["gao_reported_refund_received_as_of_decision"])
            self.assertIsNone(h["refund_received_after_decision_cents"])
            self.assertFalse(h["gao_certified_competing_carrier_claim"])
            self.assertIsNone(h["waiver_forgery_independently_adjudicated"])
            self.assertEqual(h["final_intercarrier_allocation"], "UNKNOWN")
            self.assertEqual(truth["independent_customer_payment_labels"], 0)
            self.assertFalse(truth["modern_customer_freight_error_precision_recall_allowed"])
            self.assertEqual(truth["retally_verified_recovered_cash_cents"], 0)

        verify(case)
        alterations = (
            ("source", "customer_engine_commercial_reuse_approved", True),
            ("source", "original_publisher_response_sha256", "FORGED"),
            ("historically_reported_facts", "navy_payment_to_delivering_carrier_cents", 37966),
            ("historically_reported_facts", "competing_carrier_bill_reference_transcribed", "0069"),
            ("historically_reported_facts", "delivering_carrier_paid_bill_reference_transcribed", "A-820099"),
            ("historically_reported_facts", "navy_paid_voucher_reference_transcribed", "K-6740-FORGED"),
            ("historically_reported_facts", "cited_bill_and_voucher_originals_acquired", True),
            ("quality", "competing_and_paid_bills_are_distinct_transactions", False),
            ("historically_reported_facts", "competing_carrier_reduced_claim_cents", 95120),
            ("historically_reported_facts", "delivering_carrier_promised_refund_cents", 0),
            ("historically_reported_facts", "gao_reported_refund_received_as_of_decision", True),
            ("historically_reported_facts", "refund_received_after_decision_cents", 37966),
            ("historically_reported_facts", "gao_certified_competing_carrier_claim", True),
            ("historically_reported_facts", "waiver_forgery_independently_adjudicated", True),
            ("historically_reported_facts", "final_intercarrier_allocation", "FINAL_37966"),
            ("truth_boundaries", "independent_customer_payment_labels", 1),
            ("truth_boundaries", "modern_customer_freight_error_precision_recall_allowed", True),
            ("truth_boundaries", "retally_verified_recovered_cash_cents", 37966),
        )
        for section, key, bogus in alterations:
            with self.subTest(field=key):
                forged = copy.deepcopy(case)
                forged[section][key] = bogus
                with self.assertRaises(AssertionError):
                    verify(forged)
                self.assertNotEqual(digest(forged), digest(case))


    def test_b261127_original_gao_case_prevents_arithmetic_only_freight_false_positive(self):
        """GAO held TCN billing valid: a numerical GBL contrast alone is not a debt."""
        row = json.loads((FIXTURE.parent /
                          "gao_b261127_tcn_gbl_ambiguity_candidate_v0.json").read_text())
        src = row["source"]
        ex = row["numeric_example"]
        case = row["case"]
        eval_scope = row["evaluation"]
        self.assertEqual(row["schema_version"], "0.1.0")
        self.assertEqual(row["evaluation_family"], "FREIGHT_ERROR_ADJUDICATION_HISTORICAL_DECISION_ONLY")
        self.assertEqual(src["official_decision_url"], "https://www.gao.gov/products/b-261127")
        self.assertIn(src["official_decision_url"], SEEDS["freightrecovery"])
        self.assertEqual(src["decision_date"], "1996-02-15")
        self.assertEqual(src["original_solicitation_date"], "1990-03-26")
        self.assertFalse(src["original_source_html_response_bytes_acquired"])
        self.assertIsNone(src["original_source_response_sha256"])
        self.assertFalse(src["original_invoice_or_gbl_image_acquired"])
        self.assertFalse(src["customer_engine_specific_commercial_reuse_approved"])
        self.assertEqual(case["tender_reference"], "600029")
        self.assertEqual(case["note_12_rate_cents_per_cwt"], 200)
        self.assertEqual(case["note_12_minimum_charge_cents_per_shipment"], 2500)
        self.assertEqual(case["carrier_asserted_tcn_billed_gbls_before_objection"], 1062)
        self.assertFalse(case["asserted_population_independently_verified"])
        self.assertFalse(case["external_standard_gbl_definition_incorporated_into_note_12"])
        self.assertEqual(case["historical_note_12_disposition"],
                         "GAO_UPHELD_CARRIER_TCN_BILLING_UNDER_SPECIFIC_AMBIGUOUS_CONTRACT")
        self.assertEqual(case["historical_note_14_disposition"],
                         "GAO_DENIED_SEPARATE_ADDITIONAL_TERMINAL_CHARGES_AS_OVERLAPPING")
        self.assertEqual(ex["tcn_minimum_charge_unit_count"], 63)
        self.assertEqual(ex["carrier_billed_tcn_total_cents"], 165940)
        self.assertEqual(ex["carrier_billed_tcn_total_cents"],
                         63 * case["note_12_minimum_charge_cents_per_shipment"] +
                         sum(ex["extra_tcn_charges_cents"]))
        self.assertEqual(ex["government_gbl_interpretation_total_weight_lbs"], 14320)
        self.assertEqual(ex["alternate_gbl_total_cents"],
                         14320 * case["note_12_rate_cents_per_cwt"] // 100)
        self.assertEqual(ex["unadjudicated_arithmetic_difference_cents"], 137300)
        self.assertEqual(ex["unadjudicated_arithmetic_difference_cents"],
                         ex["carrier_billed_tcn_total_cents"] - ex["alternate_gbl_total_cents"])
        self.assertFalse(ex["difference_is_final_overcharge_or_recovery"])
        self.assertIsNone(case["final_actual_refund_or_offset_proved"])
        self.assertIsNone(case["carrier_note_14_claim_amount_cents"])
        self.assertFalse(case["independent_postdecision_payment_or_collection_receipt"])
        self.assertEqual(eval_scope["independent_heldout_labeled_customer_invoices"], 0)
        self.assertIsNone(eval_scope["real_current_customer_error_precision_recall"])
        self.assertEqual(eval_scope["independently_verified_cash_recoveries"], 0)
        self.assertFalse(eval_scope["labels_currently_promotable_to_live_engine"])

    def test_b261127_adversarial_negative_controls_reject_scope_and_cash_promotion(self):
        """A historical holding does not prove a modern rate or collected refund."""
        row = json.loads((FIXTURE.parent /
                          "gao_b261127_tcn_gbl_ambiguity_candidate_v0.json").read_text())
        controls = row["synthetic_negative_controls"]
        self.assertEqual(len(controls), 6)
        self.assertEqual(len({c["id"] for c in controls}), 6)
        self.assertTrue(all(c["kind"] == "SYNTHETIC" and
                            c["id"].startswith("SYNTH_") for c in controls))
        self.assertEqual({c["expected"] for c in controls}, {
            "REJECT_MATH_CONTRAST_NOT_GAO_UPHELD_OVERCHARGE",
            "REJECT_OMITTED_INCORPORATION_AND_PREBILLING_GUIDANCE",
            "REJECT_ADDITIONAL_NOTE14_DENIED",
            "REJECT_CARRIER_REPORTED_COUNT_NOT_ORIGINAL_BILL_CUSTODY",
            "UNKNOWN_NO_POSTDECISION_PAYMENT_RECEIPT",
            "REJECT_1990_TENDER_DOES_NOT_AUTHORIZE_CURRENT_CONTRACT",
        })
        def verify(value):
            self.assertFalse(value["numeric_example"]["difference_is_final_overcharge_or_recovery"])
            self.assertFalse(value["source"]["original_invoice_or_gbl_image_acquired"])
            self.assertFalse(value["source"]["customer_engine_specific_commercial_reuse_approved"])
            self.assertIsNone(value["source"]["original_source_response_sha256"])
            self.assertFalse(value["case"]["external_standard_gbl_definition_incorporated_into_note_12"])
            self.assertIsNone(value["case"]["final_actual_refund_or_offset_proved"])
            self.assertIsNone(value["case"]["carrier_note_14_claim_amount_cents"])
            self.assertEqual(value["evaluation"]["independent_heldout_labeled_customer_invoices"], 0)
            self.assertEqual(value["evaluation"]["independently_verified_cash_recoveries"], 0)
            self.assertFalse(value["evaluation"]["labels_currently_promotable_to_live_engine"])
        verify(row)
        for section, field, replacement in (
            ("numeric_example", "difference_is_final_overcharge_or_recovery", True),
            ("source", "original_invoice_or_gbl_image_acquired", True),
            ("source", "customer_engine_specific_commercial_reuse_approved", True),
            ("source", "original_source_response_sha256", "unverified-forged"),
            ("case", "external_standard_gbl_definition_incorporated_into_note_12", True),
            ("case", "final_actual_refund_or_offset_proved", 137300),
            ("case", "carrier_note_14_claim_amount_cents", 137300),
            ("evaluation", "independent_heldout_labeled_customer_invoices", 1062),
            ("evaluation", "independently_verified_cash_recoveries", 137300),
            ("evaluation", "labels_currently_promotable_to_live_engine", True),
        ):
            with self.subTest(field=field):
                altered = copy.deepcopy(row)
                altered[section][field] = replacement
                with self.assertRaises(AssertionError):
                    verify(altered)
                self.assertNotEqual(digest(altered), digest(row))


    def test_b143246_multi_decision_netting_is_one_historical_case_not_customer_cash(self):
        """A GAO-reported collected offset differs from allowance and bank-cash proof."""
        item = json.loads((FIXTURE.parent / "gao_b143246_conex_netting_candidate_v0.json").read_text())
        self.assertEqual(item["schema_version"], "0.1.0")
        self.assertEqual(item["fixture_id"], "GAO_B143246_CONEX_CLASSIFICATION_AND_RECOUPMENT_NETTING_V0")
        self.assertEqual(item["evaluation_families"], [
            "FREIGHT_ERROR_ADJUDICATION_HISTORICAL_DECISION_ONLY",
            "GENERAL_ACCOUNTING_RECONCILIATION_OF_PUBLISHED_DECISION_EVENTS",
        ])
        self.assertEqual([x["official_url"] for x in item["sources"]], [
            "https://www.gao.gov/products/b-143246",
            "https://www.gao.gov/products/b-143246-0",
        ])
        self.assertEqual([x["decision_date"] for x in item["sources"]],
                         ["1961-05-12", "1961-11-20"])
        self.assertEqual(item["source_snapshot_case_count"], 1)
        self.assertEqual(item["rights_reference"], "https://www.gao.gov/copyright")
        self.assertFalse(item["customer_engine_commercial_reuse_approved"])
        self.assertFalse(item["original_publisher_http_bytes_acquired"])
        self.assertIsNone(item["original_publisher_response_sha256"])
        self.assertFalse(item["original_bill_voucher_gbl_tariff_pages_acquired"])
        self.assertEqual(item["independently_held_out_real_customer_labels"], 0)
        facts = item["historical_facts"]
        controls = item["accounting_controls"]
        self.assertEqual(facts["original_gbl_gao_transcription"], "AF-4940529")
        self.assertEqual(facts["carrier_bill_gao_transcription"], "G-01678")
        self.assertEqual(facts["original_carrier_paid_cents"], 62724)
        self.assertEqual(facts["initially_deducted_as_overcharge_cents"], 34021)
        self.assertTrue(facts["initial_deduction_reported_collected"])
        self.assertEqual(facts["carrier_reclaim_allowed_cents"], 1181)
        self.assertIsNone(facts["allowance_cash_posting_verified"])
        self.assertEqual(facts["remaining_carrier_reclaim_disallowed_cents"], 32840)
        self.assertEqual(facts["gao_reported_adjusted_charge_cents"], 29884)
        self.assertEqual(62724 - 34021, controls["reported_paid_minus_reported_collected_deduction_cents"])
        self.assertEqual(34021 - 1181, controls["reported_initial_deduction_less_allowed_reclaim_cents"])
        self.assertEqual(62724 - 32840, facts["gao_reported_adjusted_charge_cents"])
        self.assertEqual(28703 + 1181, controls[
            "conditional_adjusted_charge_if_allowed_reclaim_were_cash_posted_cents"])
        self.assertIsNone(facts["bank_cleared_net_after_allowance_cents"])
        self.assertTrue(facts["two_decisions_are_one_shipment"])
        self.assertFalse(facts["highest_class_package_rule_applies_to_whole_mixed_shipment"])
        self.assertTrue(facts["further_reconsideration_conditioned_on_adverse_court_ruling"])
        self.assertEqual(facts["actual_subsequent_court_disposition"], "UNKNOWN")
        self.assertEqual(controls["modern_contract_tariff_applicability"], "UNKNOWN")
        self.assertEqual(controls["modern_customer_recovery_cents"], 0)
        self.assertFalse(controls["customer_freight_error_accuracy_scoring_permitted"])

    def test_b143246_false_cash_package_and_duplicate_claims_fail_contract(self):
        item = json.loads((FIXTURE.parent / "gao_b143246_conex_netting_candidate_v0.json").read_text())
        controls = item["synthetic_negative_controls"]
        self.assertEqual(len(controls), 6)
        self.assertEqual(len({x["id"] for x in controls}), 6)
        self.assertTrue(all(x["kind"] == "SYNTHETIC" and
                            x["id"].startswith("SYNTHETIC_") for x in controls))
        pinned = [
            ("historical_facts", "initial_deduction_reported_collected", True),
            ("historical_facts", "allowance_cash_posting_verified", None),
            ("historical_facts", "highest_class_package_rule_applies_to_whole_mixed_shipment", False),
            ("historical_facts", "two_decisions_are_one_shipment", True),
            ("historical_facts", "further_reconsideration_conditioned_on_adverse_court_ruling", True),
            ("historical_facts", "original_carrier_paid_cents", 62724),
            ("historical_facts", "initially_deducted_as_overcharge_cents", 34021),
            ("historical_facts", "carrier_reclaim_allowed_cents", 1181),
            ("historical_facts", "remaining_carrier_reclaim_disallowed_cents", 32840),
            ("historical_facts", "gao_reported_adjusted_charge_cents", 29884),
            ("historical_facts", "bank_cleared_net_after_allowance_cents", None),
            ("accounting_controls", "modern_customer_recovery_cents", 0),
            ("accounting_controls", "customer_freight_error_accuracy_scoring_permitted", False),
        ]
        def verify(row):
            for section, field, expected in pinned:
                self.assertEqual(row[section][field], expected)
            x = row["historical_facts"]
            self.assertEqual(x["original_carrier_paid_cents"] -
                             x["initially_deducted_as_overcharge_cents"], 28703)
            self.assertEqual(x["initially_deducted_as_overcharge_cents"] -
                             x["carrier_reclaim_allowed_cents"], 32840)
            self.assertEqual(x["original_carrier_paid_cents"] -
                             x["remaining_carrier_reclaim_disallowed_cents"], 29884)
        verify(item)
        for section, field, expected in pinned:
            with self.subTest(field=field):
                forged = copy.deepcopy(item)
                forged[section][field] = (
                    (not expected) if isinstance(expected, bool)
                    else 1 if expected is None else expected + 1
                )
                with self.assertRaises(AssertionError):
                    verify(forged)
                self.assertNotEqual(digest(forged), digest(item))

    def test_gao_1968_published_printout_arithmetic_is_not_invoice_truth(self):
        """1968 GAO printed audit-form illustration: extraction only, no original invoice."""
        item = json.loads((FIXTURE.parent /
            "gao_review_1968_household_goods_audit_printout_candidate_v0.json"
        ).read_text(encoding="utf-8"))
        self.assertEqual(item["schema_version"], "0.1.0")
        self.assertEqual(item["admission_state"],
            "PUBLISHER_ILLUSTRATION_INDEXED_NOT_ORIGINAL_INVOICE_OR_SCORING_TRUTH")
        source = item["source"]
        self.assertEqual(source["official_pdf_url"], "https://www.gao.gov/assets/091196.pdf")
        self.assertEqual(source["pdf_zero_based_page_index"], 39)
        self.assertEqual(source["printed_page_number"], 38)
        self.assertEqual(source["publication_year"], 1968)
        self.assertEqual(source["printed_form_date_as_published"], "6 14 67")
        self.assertEqual(source["governing_tariff_effective_date"], "UNKNOWN")
        self.assertEqual(source["rights_url"], "https://www.gao.gov/copyright")
        self.assertTrue(source["publisher_page_visited_and_visually_reviewed"])
        self.assertFalse(source["source_pdf_bytes_acquired"])
        self.assertIsNone(source["source_pdf_sha256"])
        self.assertFalse(source["original_carrier_invoice_or_gbl_bytes_acquired"])
        self.assertFalse(source["original_tariff_pages_acquired"])
        self.assertFalse(source["customer_engine_commercial_source_admission"])
        x = item["published_example"]
        self.assertEqual(x["printed_mileage_miles"], 2133)
        self.assertEqual(x["transport_weight_pounds"], 2960)
        self.assertEqual(x["linehaul_cents_per_cwt"], 1660)
        self.assertEqual(x["linehaul_charge_cents"], 49136)
        self.assertEqual(x["accessorial_charge_cents"], 525)
        self.assertEqual(x["gao_audit_should_be_cents"], 49661)
        self.assertEqual(x["amount_paid_cents"], 50845)
        self.assertEqual(x["printed_difference_due_us_cents"], 1184)
        self.assertEqual(x["transport_weight_pounds"] *
            x["linehaul_cents_per_cwt"], x["linehaul_charge_cents"] * 100)
        self.assertEqual(x["linehaul_charge_cents"] +
            x["accessorial_charge_cents"], x["gao_audit_should_be_cents"])
        self.assertEqual(x["amount_paid_cents"] -
            x["gao_audit_should_be_cents"], x["printed_difference_due_us_cents"])
        q = item["data_quality"]
        self.assertTrue(q["page_image_visually_checked"])
        self.assertTrue(q["is_gao_published_printout_illustration"])
        self.assertFalse(q["illustration_is_independently_authenticated_actual_paid_invoice"])
        self.assertFalse(q["underlying_shipment_independently_verified"])
        self.assertEqual(q["labeled_real_world_invoice_error_cases"], 0)
        self.assertEqual(q["independently_held_out_labeled_cases"], 0)
        self.assertIsNone(q["external_ground_truth_invoice_error_cents"])
        self.assertEqual(q["customer_outcome"], "UNKNOWN")
        self.assertEqual(q["final_refund_collection"], "UNKNOWN")
        self.assertEqual(q["recovered_retally_cash_cents"], 0)

    def test_gao_1968_printout_false_invoice_cash_and_heldout_controls(self):
        item = json.loads((FIXTURE.parent /
            "gao_review_1968_household_goods_audit_printout_candidate_v0.json"
        ).read_text(encoding="utf-8"))
        controls = item["synthetic_negative_controls"]
        self.assertEqual(len(controls), 5)
        self.assertEqual(len({c["id"] for c in controls}), 5)
        self.assertTrue(all(c["kind"] == "SYNTHETIC" and
            c["id"].startswith("SYNTHETIC_") and c["expected"].startswith("REJECT_")
            for c in controls))
        pinned = [
            ("published_example", "amount_paid_cents", 50845),
            ("published_example", "gao_audit_should_be_cents", 49661),
            ("published_example", "printed_difference_due_us_cents", 1184),
            ("published_example", "transport_weight_pounds", 2960),
            ("published_example", "linehaul_cents_per_cwt", 1660),
            ("source", "source_pdf_bytes_acquired", False),
            ("source", "source_pdf_sha256", None),
            ("source", "customer_engine_commercial_source_admission", False),
            ("data_quality", "illustration_is_independently_authenticated_actual_paid_invoice", False),
            ("data_quality", "independently_held_out_labeled_cases", 0),
            ("data_quality", "recovered_retally_cash_cents", 0),
        ]
        def bounded_check(candidate):
            for section, field, expected in pinned:
                self.assertEqual(candidate[section][field], expected)
            x = candidate["published_example"]
            self.assertEqual(x["amount_paid_cents"] -
                x["gao_audit_should_be_cents"], x["printed_difference_due_us_cents"])
            self.assertEqual(x["transport_weight_pounds"] *
                x["linehaul_cents_per_cwt"], x["linehaul_charge_cents"] * 100)
            self.assertEqual(x["linehaul_charge_cents"] +
                x["accessorial_charge_cents"], x["gao_audit_should_be_cents"])
        bounded_check(item)
        for section, field, expected in pinned:
            with self.subTest(field=field):
                bogus = copy.deepcopy(item)
                bogus[section][field] = (
                    not expected if isinstance(expected, bool) else
                    "FORGED_SOURCE_HASH" if expected is None else expected + 1
                )
                with self.assertRaises(AssertionError):
                    bounded_check(bogus)
                self.assertNotEqual(digest(bogus), digest(item))

if __name__ == "__main__":
    unittest.main()
