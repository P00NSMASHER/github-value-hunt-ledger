"""Mission 10 adversarial acceptance: invoice document provenance is not truth."""
from __future__ import annotations

from copy import deepcopy
from datetime import date
import unittest

from freight.research_evidence_gate import canon_hash
from freight.research_ground_truth import (
    invented_fixture_book, validate_fixtures, run_ground_truth, render_html,
    _doc, _payment_body, _digest, CASE_IDS,
)
from freight.research_validation_protocols import build_protocol_report

AS_OF = date(2026, 10, 10)


def fixtures():
    return invented_fixture_book(), build_protocol_report(as_of=AS_OF)


def mutated(index: int, key: str, value):
    book, protocol = fixtures()
    book["cases"][index][key] = value
    return book, protocol


class InvoiceGroundTruthTests(unittest.TestCase):
    def test_ten_fictional_cases_with_no_real_invoice_adjudications(self):
        book, protocols = fixtures()
        self.assertEqual(validate_fixtures(book, protocols, as_of=AS_OF), [])
        r = run_ground_truth(as_of=AS_OF, book=book, protocols=protocols)
        self.assertEqual(r["case_count"], 10)
        self.assertEqual(r["verified_ground_truth_cases"], 0)
        self.assertEqual(r["real_customer_cases"], 0)
        self.assertEqual(r["actual_cash_recovered_cents"], 0)
        self.assertTrue(r["synthetic_only"])
        self.assertFalse(r["legal_applicability_established"])
        self.assertFalse(r["external_actions_allowed"])
        self.assertFalse(r["approved_public_performance_benchmark"])
        self.assertEqual(r["existing_lab_number"], 14)
        self.assertFalse(r["new_lab_created"])
        self.assertEqual(r["fixture_sha256"], canon_hash(book))
        self.assertEqual(r["receipt_sha256"], canon_hash({
            k: v for k, v in r.items() if k != "receipt_sha256"
        }))
        self.assertTrue(all(x["independent_real_world_truth"] is False
                            and x["money_recovered_cents"] == 0
                            and x["customer_claim_authorized"] is False
                            for x in r["cases"]))

    def test_each_fictional_edge_case_is_differentiated(self):
        r = run_ground_truth(as_of=AS_OF)
        expected = (
            "SYNTHETIC_PAID_NUMERIC_DIFFERENCE_CANDIDATE",
            "SYNTHETIC_NO_DISCREPANCY_CONTROL",
            "SYNTHETIC_DUPLICATE_PAYMENT_CANDIDATE",
            "HOLD_NO_CONTROLLING_AUTHORITY",
            "HOLD_RATE_EFFECTIVE_DATE",
            "HOLD_BLIND_REVIEW_DISAGREEMENT",
            "SYNTHETIC_PRIOR_REFUND_NO_REMAINING_CASH_EXCESS",
            "SYNTHETIC_UNPAID_BILLING_DIFFERENCE",
            "HOLD_CARRIER_SCOPE_MISMATCH",
            "HOLD_CREDIT_NOT_CASH_RECONCILIATION",
        )
        self.assertEqual(tuple(x["status"] for x in r["cases"]), expected)
        self.assertEqual(len(r["case_status_counts"]), 10)
        self.assertTrue(all(x["case_status_counts"].get(s) == 1 for s in expected))

    def test_overbilled_mock_paid_amount_separate_from_cash_recovery(self):
        row = run_ground_truth(as_of=AS_OF)["cases"][0]
        self.assertEqual(row["invoice_cents_fictional"], 15000)
        self.assertEqual(row["expected_cents_fictional"], 12000)
        self.assertEqual(row["billed_difference_cents_fictional"], 3000)
        self.assertEqual(row["cash_above_mock_expected_cents_not_a_refund_right"], 3000)
        self.assertEqual(row["money_recovered_cents"], 0)

    def test_invoice_correct_control_has_zero_difference(self):
        row = run_ground_truth(as_of=AS_OF)["cases"][1]
        self.assertEqual(row["billed_difference_cents_fictional"], 0)
        self.assertEqual(row["net_cash_paid_cents_fictional"], 12000)
        self.assertEqual(row["money_recovered_cents"], 0)

    def test_double_payment_is_separate_from_invoice_overcharge(self):
        row = run_ground_truth(as_of=AS_OF)["cases"][2]
        self.assertEqual(row["billed_difference_cents_fictional"], 0)
        self.assertEqual(row["gross_payment_cents_fictional"], 20000)
        self.assertEqual(row["cash_above_mock_expected_cents_not_a_refund_right"], 10000)
        self.assertEqual(row["claim_category"], "DUPLICATE_PAYMENT")

    def test_missing_rate_authority_cannot_produce_verified_result(self):
        row = run_ground_truth(as_of=AS_OF)["cases"][3]
        self.assertIsNone(row["expected_cents_fictional"])
        self.assertIsNone(row["billed_difference_cents_fictional"])
        self.assertEqual(row["status"], "HOLD_NO_CONTROLLING_AUTHORITY")

    def test_future_effective_rate_cannot_be_backapplied(self):
        b, _ = fixtures()
        a = b["cases"][4]["authority"]
        self.assertGreater(a["effective_on"], b["cases"][4]["shipment_on"])
        row = run_ground_truth(as_of=AS_OF)["cases"][4]
        self.assertEqual(row["status"], "HOLD_RATE_EFFECTIVE_DATE")

    def test_two_blinded_reviewers_disagree_without_auto_majority(self):
        row = run_ground_truth(as_of=AS_OF)["cases"][5]
        self.assertEqual(row["reviewer_votes"], ["EXCESS_BILLING", "NO_DIFFERENCE"])
        self.assertEqual(row["status"], "HOLD_BLIND_REVIEW_DISAGREEMENT")

    def test_cash_refund_reduces_paid_excess_with_full_cohort_retention(self):
        row = run_ground_truth(as_of=AS_OF)["cases"][6]
        self.assertEqual(row["gross_payment_cents_fictional"], 15000)
        self.assertEqual(row["refund_cents_fictional"], 3000)
        self.assertEqual(row["net_cash_paid_cents_fictional"], 12000)
        self.assertEqual(row["cash_above_mock_expected_cents_not_a_refund_right"], 0)

    def test_unpaid_billed_overcharge_is_not_a_cash_recovery(self):
        row = run_ground_truth(as_of=AS_OF)["cases"][7]
        self.assertEqual(row["billed_difference_cents_fictional"], 3000)
        self.assertEqual(row["gross_payment_cents_fictional"], 0)
        self.assertEqual(row["cash_above_mock_expected_cents_not_a_refund_right"], 0)

    def test_authority_for_wrong_carrier_is_inadmissible(self):
        row = run_ground_truth(as_of=AS_OF)["cases"][8]
        self.assertEqual(row["status"], "HOLD_CARRIER_SCOPE_MISMATCH")

    def test_carrier_credit_is_not_refunded_cash(self):
        row = run_ground_truth(as_of=AS_OF)["cases"][9]
        self.assertEqual(row["refund_cents_fictional"], 0)
        self.assertEqual(row["carrier_credit_not_cash_cents_fictional"], 3000)
        self.assertEqual(row["net_cash_paid_cents_fictional"], 15000)
        self.assertEqual(row["status"], "HOLD_CREDIT_NOT_CASH_RECONCILIATION")

    def test_doc_hash_tamper_is_detected(self):
        b, p = fixtures()
        b["cases"][0]["documents"][0]["body"] += " UNVERIFIED"
        self.assertIn("hash mismatched", "; ".join(validate_fixtures(b, p, as_of=AS_OF)))

    def test_doc_content_with_recomputed_hash_still_not_accepted(self):
        b, p = fixtures()
        d = b["cases"][0]["documents"][0]
        d["body"] += " tamper"
        d["body_sha256"] = _digest(d["body"])
        self.assertTrue(validate_fixtures(b, p, as_of=AS_OF))

    def test_duplicate_invoice_shipment_payment_ids_are_rejected(self):
        for path, value in (
            (("invoice_id",), "SYN-INV-01"),
            (("shipment_id",), "SYN-SHIP-01"),
        ):
            b,p = fixtures()
            b["cases"][1][path[0]] = value
            self.assertTrue(validate_fixtures(b,p,as_of=AS_OF))
        b,p = fixtures()
        b["cases"][1]["payment_events"][0]["event_id"] = b["cases"][0]["payment_events"][0]["event_id"]
        self.assertIn("misbound", "; ".join(validate_fixtures(b,p,as_of=AS_OF)))

    def test_cross_case_or_missing_payment_source_rejected(self):
        b,p = fixtures()
        b["cases"][0]["payment_events"][0]["source_document_id"] = (
            b["cases"][1]["documents"][0]["id"])
        self.assertIn("payment source/invoice link", "; ".join(
            validate_fixtures(b,p,as_of=AS_OF)))

    def test_no_private_fields_are_ever_allowed(self):
        b,p = fixtures()
        b["cases"][0]["customer_email"] = "someone@example.net"
        self.assertIn("unexpected/missing fields", "; ".join(
            validate_fixtures(b,p,as_of=AS_OF)))
        b,p = fixtures()
        b["cases"][0]["documents"][0]["customer_name"] = "not allowed"
        self.assertIn("unknown or malformed document", "; ".join(
            validate_fixtures(b,p,as_of=AS_OF)))

    def test_cannot_promote_reviewers_to_real_or_unblind(self):
        for key, val in (("real_person", True), ("blinded", False),
                         ("saw_other_vote", True), ("finding", "CERTIFIED_VERIFIED")):
            b,p = fixtures()
            b["cases"][0]["reviewers"][0][key] = val
            self.assertTrue(validate_fixtures(b,p,as_of=AS_OF), key)

    def test_vote_reference_cannot_cross_case_or_skip_invoice(self):
        b,p = fixtures()
        b["cases"][0]["reviewers"][0]["evidence_document_ids"] = [
            b["cases"][1]["documents"][0]["id"]]
        self.assertIn("orphan or missing", "; ".join(
            validate_fixtures(b,p,as_of=AS_OF)))

    def test_wrong_rate_interval_and_scope_are_rejected_or_held(self):
        b,p = fixtures()
        b["cases"][0]["authority"]["expires_on"] = "2025-01-01"
        self.assertIn("inverted authority", "; ".join(
            validate_fixtures(b,p,as_of=AS_OF)))
        b,p = fixtures()
        b["cases"][0]["authority"]["real_contract_applicability_established"] = True
        self.assertIn("fake external rate", "; ".join(
            validate_fixtures(b,p,as_of=AS_OF)))

    def test_noncanonical_or_future_payment_dates_rejected(self):
        for val in ("2026-22-03", "2027-01-01", "2026-01-01"):
            b,p = fixtures()
            b["cases"][0]["payment_events"][0]["posted_on"] = val
            self.assertTrue(validate_fixtures(b,p,as_of=AS_OF), val)

    def test_invalid_amount_types_rejected_no_float_money(self):
        for val in (-1, True, 100.5, "15000", 100_000_001):
            b,p = mutated(0, "invoice_cents", val)
            self.assertIn("integer invoice cents", "; ".join(
                validate_fixtures(b,p,as_of=AS_OF)))
        for val in (-1, True, 100.5, "30"):
            b,p = fixtures()
            b["cases"][0]["payment_events"][0]["amount_cents"] = val
            self.assertIn("positive integer cents", "; ".join(
                validate_fixtures(b,p,as_of=AS_OF)))

    def test_currency_mismatch_cannot_be_net_settled(self):
        for nested, value in (
            ("invoice", "EUR"),
            ("authority", "EUR"),
            ("payment", "EUR"),
        ):
            b,p=fixtures()
            if nested == "invoice":
                b["cases"][0]["currency"] = value
            elif nested == "authority":
                b["cases"][0]["authority"]["currency"] = value
            else:
                b["cases"][0]["payment_events"][0]["currency"] = value
            self.assertTrue(validate_fixtures(b,p,as_of=AS_OF), nested)
            with self.assertRaisesRegex(ValueError, "INVALID_SYNTHETIC_GROUND_TRUTH"):
                run_ground_truth(as_of=AS_OF,book=b,protocols=p)

    def test_malformed_nested_payloads_fail_closed_as_errors(self):
        for field, value in (
            ("invoice_id", []),
            ("shipment_on", []),
            ("authority", {"bad": 1}),
            ("documents", [1]),
            ("reviewers", [None]),
            ("payment_events", [{"invalid": 1}]),
        ):
            b,p=fixtures()
            b["cases"][0][field]=value
            self.assertTrue(validate_fixtures(b,p,as_of=AS_OF),field)
            with self.assertRaisesRegex(ValueError,"INVALID_SYNTHETIC_GROUND_TRUTH"):
                run_ground_truth(as_of=AS_OF,book=b,protocols=p)

    def test_refunds_larger_than_paid_cannot_be_counted(self):
        b,p = fixtures()
        e = b["cases"][6]["payment_events"][1]
        e["amount_cents"] = 40000
        self.assertIn("refund larger than cash", "; ".join(
            validate_fixtures(b,p,as_of=AS_OF)))

    def test_cargo_loss_damage_must_not_be_laundered_as_billing(self):
        b,p = mutated(0, "claim_category", "LOSS_OR_DAMAGE")
        self.assertIn("cargo loss/damage", "; ".join(
            validate_fixtures(b,p,as_of=AS_OF)))

    def test_all_external_authorization_and_results_are_unavailable(self):
        for key, value in (
            ("synthetic_only", False),
            ("actual_customer_records", 2),
            ("real_invoice_ground_truth_verified", True),
            ("external_data_acquisition_authorized", True),
            ("claims_or_financial_actions_authorized", True),
        ):
            b,p = fixtures()
            b[key] = value
            self.assertTrue(validate_fixtures(b,p,as_of=AS_OF))
            with self.assertRaisesRegex(ValueError, "INVALID_SYNTHETIC_GROUND_TRUTH"):
                run_ground_truth(as_of=AS_OF, book=b, protocols=p)

    def test_upstream_preregistration_approval_cannot_be_forged(self):
        b,p = fixtures()
        q = deepcopy(p)
        q["external_studies_executed"] = 1
        self.assertTrue(validate_fixtures(b,q,as_of=AS_OF))
        q = deepcopy(p)
        q["protocols"][0]["title"] = "tampered"
        self.assertIn("held original protocol", "; ".join(
            validate_fixtures(b,q,as_of=AS_OF)))

    def test_frozen_fixture_changes_cannot_be_reported_without_review(self):
        b,p = fixtures()
        b["cases"][0]["reviewers"][0]["finding"] = "NO_DIFFERENCE"
        self.assertIn("fixture drift", "; ".join(
            validate_fixtures(b,p,as_of=AS_OF)))

    def test_empty_or_duplicate_case_inventory_fails_closed(self):
        b,p = fixtures()
        b["cases"].pop()
        self.assertTrue(validate_fixtures(b,p,as_of=AS_OF))
        b,p = fixtures()
        b["cases"][1]["case_id"] = CASE_IDS[0]
        self.assertTrue(validate_fixtures(b,p,as_of=AS_OF))

    def test_report_reproducibility_and_later_date_never_promote_truth(self):
        r = run_ground_truth(as_of=AS_OF)
        self.assertEqual(r, run_ground_truth(as_of=AS_OF))
        future = run_ground_truth(as_of=date(2027, 2, 1))
        self.assertEqual(future["verified_ground_truth_cases"], 0)
        self.assertEqual(future["actual_cash_recovered_cents"], 0)
        self.assertFalse(future["approved_public_performance_benchmark"])

    def test_escaped_html_does_not_execute_untrusted_label(self):
        r = run_ground_truth(as_of=AS_OF)
        bad = deepcopy(r)
        bad["cases"][0]["reason"] = '<script>alert("x")</script>'
        html = render_html(bad)
        self.assertIn("&lt;script&gt;", html)
        self.assertNotIn("<script>", html)
        self.assertIn("zero verified recoveries", html.lower())


if __name__ == "__main__":
    unittest.main()
