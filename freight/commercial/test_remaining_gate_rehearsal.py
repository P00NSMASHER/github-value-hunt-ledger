"""Acceptance tests for the 14-gate synthetic rehearsal boundary."""
import copy
import json
import unittest
from pathlib import Path

from freight.commercial.remaining_gate_rehearsal import (
    EXPECTED_BLOCKED,
    render_markdown,
    run_remaining_gate_rehearsal,
    verify_rehearsal,
)

BASE = json.loads(Path(__file__).with_name("first_customer_acceptance_m2g.json").read_text(encoding="utf-8"))


class RemainingGateRehearsalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = run_remaining_gate_rehearsal(copy.deepcopy(BASE))

    def test_every_real_blocker_has_a_passing_simulation_receipt(self):
        self.assertEqual(tuple(item["gate_id"] for item in self.result["gate_receipts"]), EXPECTED_BLOCKED)
        self.assertEqual(self.result["simulated_gate_count"], 14)
        self.assertEqual(self.result["simulated_pass_count"], 14)
        self.assertEqual({item["simulation_outcome"] for item in self.result["gate_receipts"]}, {"PASS"})
        self.assertEqual(self.result["simulation_scorecard"]["classification"], "FICTIONAL_REHEARSAL_ONLY")
        self.assertEqual(
            {key: self.result["simulation_scorecard"][key] for key in ("PASS", "BLOCKED", "FAIL", "total")},
            {"PASS": 37, "BLOCKED": 0, "FAIL": 0, "total": 37},
        )
        self.assertTrue(self.result["simulation_scorecard"]["real_scorecard_unchanged"])
        self.assertEqual(self.result["simulation_scorecard"]["customer_pilot_decision"], "FULL_GO_SIMULATED")
        self.assertTrue(self.result["simulation_scorecard"]["all_simulated_pilot_stages_available"])
        self.assertEqual(self.result["blockers_removed_in_simulation"], 14)

    def test_simulation_cannot_change_real_launch_status(self):
        self.assertEqual(set(self.result["real_gate_status_before"].values()), {"BLOCKED"})
        self.assertEqual(self.result["real_gate_status_before"], self.result["real_gate_status_after"])
        self.assertEqual(self.result["real_gate_pass_count_created"], 0)
        self.assertEqual(self.result["blockers_removed_in_real_world"], 0)
        self.assertEqual(self.result["real_scorecard"]["PASS"], 23)
        self.assertEqual(self.result["real_scorecard"]["BLOCKED"], 14)
        self.assertFalse(self.result["customer_authority_created"])
        self.assertFalse(self.result["external_effects_performed"])
        self.assertFalse(self.result["simulation_scorecard"]["real_customer_authorization_created"])
        self.assertFalse(self.result["simulation_scorecard"]["real_financial_authorization_created"])
        self.assertEqual(len(self.result["simulation_stage_decisions"]), 8)
        self.assertEqual({item["decision"] for item in self.result["simulation_stage_decisions"]}, {"GO_SIMULATED"})
        self.assertEqual({item["real_action_authorized"] for item in self.result["simulation_stage_decisions"]}, {False})

    def test_all_people_and_provider_identities_are_visibly_fictional(self):
        emails = [actor["email"] for item in self.result["gate_receipts"] for actor in item["simulated_actors"]]
        self.assertTrue(emails)
        self.assertTrue(all(email.endswith(".invalid") for email in emails))
        self.assertFalse(self.result["real_customer_data_used"])
        self.assertFalse(self.result["paid_service_used"])

    def test_money_path_reuses_real_controls_but_remains_nonbillable(self):
        core = self.result["underlying_rehearsal"]
        self.assertEqual(core["invoice_count"], 8)
        self.assertEqual(core["supported_findings_cents"], 32_500)
        self.assertEqual(core["net_recovery_cents"], 27_500)
        self.assertEqual(core["fee_eligible_cents"], 7_500)
        self.assertEqual(core["modeled_fee_cents"], 2_250)
        self.assertFalse(core["billing_authorized"])
        self.assertFalse(core["carrier_action_external_action_performed"])
        self.assertFalse(core["commercial_value_claimed"])
        self.assertTrue(core["stale_report_rejected"])

    def test_hashes_detect_tampering(self):
        tampered = copy.deepcopy(self.result)
        tampered["gate_receipts"][0]["simulated_evidence"]["legal_entity_created"] = True
        with self.assertRaisesRegex(ValueError, "rehearsal digest mismatch"):
            verify_rehearsal(tampered)
        tampered = copy.deepcopy(self.result)
        tampered["gate_receipts"][0]["simulated_evidence"]["legal_entity_created"] = True
        body = {key: value for key, value in tampered.items() if key != "rehearsal_sha256"}
        from freight.commercial.remaining_gate_rehearsal import _hash
        tampered["rehearsal_sha256"] = _hash(body)
        with self.assertRaisesRegex(ValueError, "R22 receipt digest mismatch"):
            verify_rehearsal(tampered)

    def test_markdown_never_promotes_simulation_to_launch_evidence(self):
        text = render_markdown(self.result)
        self.assertIn("37 PASS / 0 BLOCKED / 0 FAIL", text)
        self.assertIn("Customer-pilot simulation decision: **FULL_GO_SIMULATED**", text)
        self.assertIn("14 blockers removed in simulation", text)
        self.assertIn("23 PASS / 14 BLOCKED / 0 FAIL", text)
        self.assertIn("Modeled 30% fee: **$22.50 — nonbillable**", text)
        self.assertIn("Carrier action performed: **No**", text)

    def test_committed_receipt_matches_deterministic_renderer(self):
        committed = Path(__file__).with_name("REMAINING_GATES_SYNTHETIC_REHEARSAL_20261015.md").read_text(encoding="utf-8")
        self.assertEqual(committed, render_markdown(self.result))


if __name__ == "__main__":
    unittest.main()
