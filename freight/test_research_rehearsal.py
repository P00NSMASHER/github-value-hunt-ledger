"""Adversarial synthetic-only accounting, classification and study-design tests."""
from __future__ import annotations

from copy import deepcopy
from datetime import date
import json
import unittest

from freight.research_evidence_gate import canon_hash
from freight.research_rehearsal import (
    FIXTURES, run_rehearsal, render_html, validate_fixture_book,
)
from freight.research_validation_protocols import build_protocol_report

AS_OF = date(2026, 10, 10)


def fixtures():
    return json.loads(FIXTURES.read_text(encoding="utf-8")), build_protocol_report(as_of=AS_OF)


def mutate(pid, key, value, *, index=0):
    book, p = fixtures()
    row = [r for r in book["cases"] if r["protocol_id"] == pid][index]
    row[key] = value
    return book, p


class SyntheticRehearsalTests(unittest.TestCase):
    def test_all_six_methods_are_executed_without_real_studies(self):
        book, protocols = fixtures()
        self.assertEqual(validate_fixture_book(book, protocols, as_of=AS_OF), [])
        report = run_rehearsal(as_of=AS_OF, book=book, protocol_report=protocols)
        self.assertEqual(report["rehearsed_protocols"], 6)
        self.assertEqual(report["invented_case_records"], 35)
        self.assertEqual(report["independent_customer_observations"], 0)
        self.assertEqual(report["external_studies_executed"], 0)
        self.assertEqual(report["human_respondents"], 0)
        self.assertFalse(report["public_claims_authorized"])
        self.assertFalse(report["verified_business_results"])
        self.assertFalse(report["external_actions_allowed"])
        self.assertFalse(report["new_lab_created"])
        self.assertEqual(report["lab_number"], 14)
        self.assertTrue(all(row["only_invented_data"] and
                            row["external_study_completed"] is False and
                            row["marketing_result_authorized"] is False
                            for row in report["rehearsals"]))
        self.assertEqual(report["receipt_sha256"], canon_hash({
            k: v for k, v in report.items() if k != "receipt_sha256"
        }))

    def test_alert_precision_includes_unresolved_positive_in_denominator(self):
        r = run_rehearsal(as_of=AS_OF)
        p = next(x["measure"] for x in r["rehearsals"] if x["protocol_id"] == "M7-01")
        self.assertEqual(p["primary"], {"numerator": 1, "denominator": 3, "fraction": "1/3"})
        self.assertEqual(p["alerts_not_substantiated"], 1)
        self.assertEqual(p["positive_alerts_unresolved"], 1)
        self.assertEqual(p["false_negative_reference_cases"], 1)

    def test_detects_future_rule_leakage_and_contract_exception(self):
        r = run_rehearsal(as_of=AS_OF)
        p = next(x["measure"] for x in r["rehearsals"] if x["protocol_id"] == "M7-02")
        self.assertEqual(p["primary"]["fraction"], "4/5")
        self.assertEqual(p["future_rule_leakage_case_ids"], ["SIM-02-05"])
        self.assertTrue(p["cannot_infer_legal_applicability"])

    def test_survey_counts_every_randomized_fictional_nonresponder(self):
        r = run_rehearsal(as_of=AS_OF)
        p = next(x["measure"] for x in r["rehearsals"] if x["protocol_id"] == "M7-03")
        self.assertEqual(p["primary"]["fraction"], "3/8")
        self.assertEqual(p["arm_breakdown"]["POSTED"]["comprehension"]["fraction"], "2/4")
        self.assertEqual(p["arm_breakdown"]["NEGOTIATED"]["comprehension"]["fraction"], "1/4")
        self.assertEqual(p["arm_breakdown"]["POSTED"]["nonresponse_count"], 1)
        self.assertEqual(p["arm_breakdown"]["NEGOTIATED"]["nonresponse_count"], 1)
        self.assertFalse(p["causal_comparison_authorized"])

    def test_market_frame_keeps_nonresponders_and_unknowns(self):
        r = run_rehearsal(as_of=AS_OF)
        p = next(x["measure"] for x in r["rehearsals"] if x["protocol_id"] == "M7-04")
        self.assertEqual(p["primary"]["fraction"], "2/5")
        self.assertEqual(p["nonresponse"], 1)
        self.assertEqual(p["unknown"], 1)
        self.assertEqual(p["ineligible"], 1)
        self.assertFalse(p["market_extrapolation_authorized"])

    def test_rival_not_tested_is_not_a_failed_vendor_test(self):
        r = run_rehearsal(as_of=AS_OF)
        p = next(x["measure"] for x in r["rehearsals"] if x["protocol_id"] == "M7-05")
        self.assertEqual(p["by_system"]["RETALLY"]["supported_correct"]["fraction"], "1/3")
        self.assertEqual(p["by_system"]["OTHER_LICENSED_VENDOR"]["supported_correct"]["fraction"], "1/2")
        self.assertEqual(p["by_system"]["OTHER_LICENSED_VENDOR"]["not_tested"], 1)
        self.assertFalse(p["head_to_head_ranking_authorized"])

    def test_cash_fees_do_not_include_carrier_credits_and_losses_count(self):
        r = run_rehearsal(as_of=AS_OF)
        p = next(x["measure"] for x in r["rehearsals"] if x["protocol_id"] == "M7-06")
        self.assertEqual(p["collected_fee_cents"], 17000)
        self.assertEqual(p["carrier_credit_not_counted_as_cash_cents"], 110000)
        self.assertEqual(p["fee_refunds_cents"], 5000)
        self.assertEqual(p["attributable_costs_cents"], 18400)
        self.assertEqual(p["net_contribution_cents"], -6400)
        self.assertEqual(p["primary"], {"numerator": -6400, "denominator": 5,
                                        "fraction": "-6400/5"})
        self.assertEqual(p["cases_including_zero_pending_and_reversed"], 5)
        self.assertFalse(p["real_cash_or_bank_data_observed"])

    def test_no_external_source_or_actual_sample_can_be_claimed(self):
        for k, value in (
            ("synthetic_only", False),
            ("external_actions_authorized", True),
            ("external_source_records", 1),
            ("human_respondents", 10),
            ("real_carrier_or_customer_records", 2),
            ("data_origin", "REAL_BUYER_DATA"),
            ("scope", "EXTERNAL_STUDY"),
        ):
            b, protocols = fixtures()
            b[k] = value
            self.assertTrue(validate_fixture_book(b, protocols, as_of=AS_OF), k)
            with self.assertRaisesRegex(ValueError, "INVALID_SYNTHETIC_REHEARSAL"):
                run_rehearsal(as_of=AS_OF, book=b, protocol_report=protocols)

    def test_rejects_private_customer_field_in_any_case(self):
        for pid in ("M7-01", "M7-02", "M7-03", "M7-04", "M7-05", "M7-06"):
            b, p = mutate(pid, "shipper_name", "fictional buyer")
            self.assertIn("no customer data accepted", "; ".join(
                validate_fixture_book(b, p, as_of=AS_OF)))

    def test_duplicate_case_ids_are_rejected_before_aggregation(self):
        book, p = fixtures()
        book["cases"][1]["case_id"] = book["cases"][0]["case_id"]
        self.assertIn("duplicate case", "; ".join(validate_fixture_book(book, p, as_of=AS_OF)))

    def test_fake_historic_invoice_or_wrong_dates_rejected(self):
        for key, val in (("shipment_on", "2026-08-11"),
                         ("synthetic_effective_on", "2026-12-12"),
                         ("shipment_on", "2030-13-01")):
            book, p = mutate("M7-02", key, val)
            self.assertTrue(validate_fixture_book(book, p, as_of=AS_OF))

    def test_future_rule_counterexample_changes_numeric_agreement(self):
        book, p = fixtures()
        row = next(r for r in book["cases"] if r["case_id"] == "SIM-02-05")
        row["engine_decision"] = "IGNORE"
        corrected = run_rehearsal(as_of=AS_OF, book=book, protocol_report=p)
        scenario = next(x["measure"] for x in corrected["rehearsals"]
                        if x["protocol_id"] == "M7-02")
        self.assertEqual(scenario["primary"]["fraction"], "5/5")
        self.assertEqual(scenario["future_rule_leakage_case_ids"], [])
        self.assertEqual(corrected["external_studies_executed"], 0)

    def test_fake_comparison_without_access_is_rejected(self):
        for key, val in (("access", "NOT_TESTED"),
                         ("resolution", "NOT_TESTED")):
            b, p = fixtures()
            row = next(x for x in b["cases"] if x["case_id"] == "SIM-05-04")
            row[key] = val
            self.assertIn("missing vendor access", "; ".join(
                validate_fixture_book(b, p, as_of=AS_OF)))

    def test_inconsistent_head_to_head_comparison_pair_rejected(self):
        b, p = fixtures()
        row = next(x for x in b["cases"] if x["case_id"] == "SIM-05-02")
        row["system"] = "RETALLY"
        self.assertTrue(validate_fixture_book(b, p, as_of=AS_OF))
        self.assertIn("comparator coverage", "; ".join(
            validate_fixture_book(b, p, as_of=AS_OF)))

    def test_bool_or_float_cents_are_never_accepted_as_money(self):
        for v in (True, 100.5, -1, "100", 100000001):
            b, p = mutate("M7-06", "cash_fee_collected_cents", v)
            self.assertIn("exact integers", "; ".join(
                validate_fixture_book(b, p, as_of=AS_OF)))

    def test_zero_fee_episode_with_fees_or_illegal_refund_rejected(self):
        for key, value, index in (
            ("cash_fee_collected_cents", 10, 1),
            ("cash_fee_collected_cents", 10, 3),
            ("fee_refunds_cents", 10001, 0),
            ("fee_refunds_cents", 0, 2),
        ):
            b, p = mutate("M7-06", key, value, index=index)
            self.assertTrue(validate_fixture_book(b, p, as_of=AS_OF))

    def test_zero_positive_alerts_yield_undefined_not_nan_or_100_percent(self):
        b, p = fixtures()
        for row in b["cases"]:
            if row["protocol_id"] == "M7-01":
                row["alert"] = False
        outcome = run_rehearsal(as_of=AS_OF, book=b, protocol_report=p)
        metric = next(x["measure"] for x in outcome["rehearsals"]
                      if x["protocol_id"] == "M7-01")
        self.assertIsNone(metric["primary"]["fraction"])
        self.assertEqual(metric["primary"]["denominator"], 0)

    def test_preregistered_protocols_must_stay_blocked(self):
        b, p = fixtures()
        q = deepcopy(p)
        q["scope"] = "APPROVED_RESEARCH"
        self.assertTrue(validate_fixture_book(b, q, as_of=AS_OF))
        q = deepcopy(p)
        q["external_studies_executed"] = 1
        self.assertTrue(validate_fixture_book(b, q, as_of=AS_OF))
        q = deepcopy(p)
        q["public_performance_claims_allowed"] = True
        self.assertTrue(validate_fixture_book(b, q, as_of=AS_OF))
        for key, value in (
            ("approved_preregistrations", 6),
            ("observed_customer_outcomes", 1),
            ("external_actions_allowed", True),
            ("new_lab_created", True),
        ):
            q = deepcopy(p)
            q[key] = value
            self.assertTrue(validate_fixture_book(b, q, as_of=AS_OF), key)
        q = deepcopy(p)
        q["protocols"][0]["title"] = "tampered design"
        self.assertIn("tampered Mission 7 protocol receipt", "; ".join(
            validate_fixture_book(b, q, as_of=AS_OF)))

    def test_malformed_nested_json_fails_closed_not_with_type_crashes(self):
        for pid, key, value in (
            ("M7-01", "adjudication", []),
            ("M7-02", "engine_decision", {}),
            ("M7-03", "arm", []),
            ("M7-04", "frame_status", {}),
            ("M7-05", "system", []),
            ("M7-05", "fixture_id", {}),
            ("M7-06", "case_state", []),
        ):
            b, p = mutate(pid, key, value)
            errors = validate_fixture_book(b, p, as_of=AS_OF)
            self.assertTrue(errors, f"{pid}/{key} malformed record was accepted")
            with self.assertRaisesRegex(ValueError, "INVALID_SYNTHETIC_REHEARSAL"):
                run_rehearsal(as_of=AS_OF, book=b, protocol_report=p)

    def test_dated_replay_is_deterministic_and_digests_recompute(self):
        a = run_rehearsal(as_of=AS_OF)
        b = run_rehearsal(as_of=AS_OF)
        self.assertEqual(a, b)
        book, protocols = fixtures()
        self.assertEqual(a["fixture_sha256"], canon_hash(book))
        self.assertEqual(a["protocol_report_sha256"], protocols["receipt_sha256"])
        self.assertTrue(run_rehearsal(as_of=date(2027, 2, 1))["external_studies_executed"] == 0)

    def test_untrusted_text_escaped_for_read_only_html(self):
        r = run_rehearsal(as_of=AS_OF)
        dirty = deepcopy(r)
        dirty["rehearsals"][0]["measure"]["selection_warning"] = '<script>alert("x")</script>'
        html = render_html(dirty)
        self.assertIn("&lt;script&gt;", html)
        self.assertNotIn("<script>", html)
        self.assertIn("invented test cases", html)


if __name__ == "__main__":
    unittest.main()
