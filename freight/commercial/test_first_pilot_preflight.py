"""Tests for the fail-closed first-pilot operator preflight."""
import contextlib
import copy
import io
import json
import unittest
from pathlib import Path

from freight.commercial.first_pilot_preflight import (
    EVENT_STAGE_EVIDENCE,
    OPTIONAL_AUTOMATION,
    PILOT_CRITICAL_PATH,
    build_preflight,
    main,
    render_markdown,
)

BASE = json.loads(Path(__file__).with_name("first_customer_acceptance_m2g.json").read_text(encoding="utf-8"))


class FirstPilotPreflightTests(unittest.TestCase):
    def data(self):
        return copy.deepcopy(BASE)

    def test_only_public_manual_discovery_is_available_now(self):
        result = build_preflight(self.data())
        available = [stage["id"] for stage in result["stages"] if stage["action_available_now"]]
        self.assertEqual(available, ["public_manual_discovery"])
        self.assertEqual(result["new_external_spend_authorized_usd"], "0.00")
        self.assertFalse(result["available_now"]["confidential_customer_intake"])
        self.assertFalse(result["available_now"]["financial_operations"])
        self.assertFalse(result["source_only_customer_authorization"])

    def test_packet_covers_every_remaining_manual_pilot_gate(self):
        result = build_preflight(self.data())
        self.assertEqual({row["id"] for row in result["pilot_critical_path"]}, set(PILOT_CRITICAL_PATH))
        self.assertEqual({row["id"] for row in result["event_stage_evidence"]}, set(EVENT_STAGE_EVIDENCE))
        self.assertEqual({row["id"] for row in result["optional_automation_held"]}, set(OPTIONAL_AUTOMATION))
        self.assertEqual(result["resolved_artifact_control"]["id"], "R36")
        self.assertEqual(result["resolved_artifact_control"]["status"], "PASS")

    def test_all_source_rows_cannot_self_authorize_a_real_action(self):
        data = self.data()
        for row in data["mission_acceptance"]["requirements"]:
            row["status"] = "PASS"
        score = data["mission_acceptance"]["scorecard"]
        score.update(PASS=37, BLOCKED=0, FAIL=0)
        result = build_preflight(data)
        self.assertTrue(next(stage for stage in result["stages"] if stage["id"] == "confidential_intake")["ledger_prerequisites_met"])
        self.assertFalse(next(stage for stage in result["stages"] if stage["id"] == "confidential_intake")["action_available_now"])
        self.assertTrue(result["not_a_signature_or_release_system"])

    def test_scorecard_drift_fails_closed(self):
        data = self.data()
        data["mission_acceptance"]["scorecard"]["PASS"] += 1
        with self.assertRaisesRegex(ValueError, "scorecard PASS"):
            build_preflight(data)

    def test_markdown_is_an_operator_packet_not_an_approval(self):
        text = render_markdown(build_preflight(self.data()))
        self.assertIn("# RETALLY first-pilot activation packet", text)
        self.assertIn("R22", text)
        self.assertIn("R37", text)
        self.assertIn("do not constitute a signature", text)

    def test_committed_operator_packet_matches_canonical_generator(self):
        committed = Path(__file__).with_name("FIRST_PILOT_ACTIVATION_PACKET.md").read_text(encoding="utf-8")
        self.assertEqual(committed, render_markdown(build_preflight(self.data())))

    def test_cli_allows_public_stage_and_blocks_confidential_stage(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(["--require-stage", "public_manual_discovery"]), 0)
            self.assertEqual(main(["--require-stage", "confidential_intake"]), 2)


if __name__ == "__main__":
    unittest.main()
