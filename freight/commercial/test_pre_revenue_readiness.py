"""RETALLY zero-new-spend operator plan: synthetic/source-only safety tests."""
import copy
import json
import unittest
from pathlib import Path

from freight.commercial.first_customer_gate import evaluate
from freight.commercial.pre_revenue_readiness import (
    EXTERNAL_GATE_IDS, FORBIDDEN_AUTOMATIC_ACTIONS, build_plan, main,
)

BASE = json.loads((Path(__file__).with_name("first_customer_acceptance_m2g.json")).read_text(encoding="utf-8"))


class PreRevenueReadinessTests(unittest.TestCase):
    def data(self):
        return copy.deepcopy(BASE)

    def test_owner_spend_and_registration_hold_are_explicit(self):
        result = build_plan(self.data())
        self.assertEqual(result["new_external_spend_authorized_usd"], "0.00")
        self.assertEqual(result["registration_action"], "DEFER_NO_FILING_FROM_THIS_PLAN")
        self.assertEqual(result["classification"], "READ_ONLY_PRE_REVENUE_PREPARATION")
        self.assertTrue(result["not_a_customer_launch_authorization"])
        self.assertTrue(result["safe_pre_revenue_mode"])
        self.assertFalse(result["source_only_customer_authorization"])
        future=result["future_pilot_economics_not_approved"]
        self.assertEqual(future["zero_recovery_cost_usd_in_original_synthetic_example"],"2500.00")
        self.assertEqual(future["actual_owner_hour_and_loss_caps"],"NOT_APPROVED_R37_BLOCKED")
        self.assertEqual(future["independent_reviewer"],"DEFERRED_R25_BLOCKED")
        self.assertFalse(future["cash_spending_or_customer_work_authorized"])

    def test_real_custody_and_legal_stay_held_despite_synthetic_success(self):
        result = build_plan(self.data())
        self.assertEqual(result["historical_external_requirement_status"]["R30"], "FAIL")
        self.assertIn("R22", result["historical_external_requirement_status"])
        self.assertIn("R23", result["historical_external_requirement_status"])
        self.assertIn("R24", result["historical_external_requirement_status"])
        self.assertIn("R27", result["historical_external_requirement_status"])
        self.assertEqual(result["historical_external_requirement_status"]["R37"],"BLOCKED")
        self.assertEqual(set(EXTERNAL_GATE_IDS) & set(result["historical_external_requirement_status"]),
                         set(EXTERNAL_GATE_IDS))
        self.assertFalse(result["source_only_gate_status"]["confidential_pilot"]["ready"])

    def test_independent_human_review_is_deferred_not_waived(self):
        data = self.data()
        item = next(row for row in data["mission_acceptance"]["requirements"]
                    if row["id"] == "R25")
        self.assertEqual(item["status"], "BLOCKED")
        self.assertIn("DEFERRED UNTIL FIRST CREDIBLE CUSTOMER", item["required_owner_action"])
        self.assertIn("Before any confidential pilot", item["remaining_dependency"])
        self.assertFalse(build_plan(data)["source_only_gate_status"]["confidential_pilot"]["ready"])
        self.assertFalse(build_plan(data)["automatic_permissions"]["customer_onboarding_or_service"])

    def test_only_existing_unsent_email_draft_is_prepared(self):
        result = build_plan(self.data())
        self.assertTrue(result["prepared_manual_email_draft"])
        self.assertFalse(result["manual_draft_is_verified_delivery"])
        self.assertIn("OWNER_CONFIRMED", result["zoho_owner_attestation"])
        self.assertIn("non-sensitive", " ".join(result["next_steps"]["when_a_credible_prospect_appears"]))
        self.assertIn("BEFORE", " ".join(result["next_steps"]["before_contract_or_confidential_service"]))

    def test_no_source_metadata_can_auto_activate_real_world_actions(self):
        example = self.data()
        for item in example["requirements"].values():
            item.update(status="VERIFIED", evidence_ref="SYNTHETIC-ONLY",
                        reviewed_by="MOCK-REVIEWER", reviewed_at="2026-10-14")
        example["founding_offer"]["actual_contingency_rate"] = "0.30"
        self.assertTrue(evaluate(example)["gates"]["confidential_pilot"]["declared_fields_complete"])
        self.assertFalse(evaluate(example)["gates"]["confidential_pilot"]["ready"])
        self.assertFalse(evaluate(example)["customer_kickoff_authorized"])
        result = build_plan(example)
        self.assertEqual(set(result["automatic_permissions"]), set(FORBIDDEN_AUTOMATIC_ACTIONS))
        self.assertEqual(set(result["automatic_permissions"].values()), {False})
        self.assertTrue(result["not_a_customer_launch_authorization"])

    def test_drifted_public_intake_state_fails_closed(self):
        example = self.data()
        example["production"]["online_inquiry_status"] = "ONLINE"
        example["production"]["inquiry_get_body"]["online"] = True
        result = build_plan(example)
        self.assertFalse(result["safe_pre_revenue_mode"])
        self.assertEqual(result["no_spend_preparation"], "HOLD_SOURCE_OR_INQUIRY_DRIFT")

    def test_contradictory_inquiry_state_is_an_error(self):
        example = self.data()
        example["production"]["online_inquiry_status"] = "ENABLED"
        with self.assertRaisesRegex(ValueError, "contradicts"):
            build_plan(example)

    def test_missing_original_contact_fallback_is_not_invented(self):
        example = self.data()
        example["production"]["public_fallback"] = "UNKNOWN"
        result = build_plan(example)
        self.assertFalse(result["prepared_manual_email_draft"])

    def test_duplicate_or_missing_external_requirements_are_errors(self):
        example = self.data()
        example["mission_acceptance"]["requirements"].append(
            copy.deepcopy(example["mission_acceptance"]["requirements"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate"):
            build_plan(example)
        example = self.data()
        example["mission_acceptance"]["requirements"] = [
            item for item in example["mission_acceptance"]["requirements"] if item["id"] != "R30"]
        with self.assertRaisesRegex(ValueError, "missing external"):
            build_plan(example)

    def test_plan_does_not_mutate_source_or_require_private_inputs(self):
        example = self.data()
        before = copy.deepcopy(example)
        _ = build_plan(example)
        self.assertEqual(example, before)

    def test_cli_check_has_zero_spend_mode_and_no_side_effects(self):
        import contextlib
        import io
        result = io.StringIO()
        with contextlib.redirect_stdout(result):
            status = main(["--require-safe-pre-revenue-mode"])
        self.assertEqual(status, 0)
        payload = json.loads(result.getvalue())
        self.assertTrue(payload["safe_pre_revenue_mode"])
        self.assertTrue(payload["not_a_customer_launch_authorization"])


if __name__ == "__main__":
    unittest.main()
