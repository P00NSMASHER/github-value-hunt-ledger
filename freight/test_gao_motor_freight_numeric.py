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
        self.assertEqual(len({c["id"] for c in controls}), 4)
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



if __name__ == "__main__":
    unittest.main()
