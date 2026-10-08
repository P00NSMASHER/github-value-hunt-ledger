"""Deterministic triage checks, not claims of real financial impact."""
import unittest
from copy import deepcopy
from freight.lab_intelligence_runner import make_control_room


def tiny_registry():
    entries=[
        {"id":"LAB-P0-03", "severity":"CRITICAL", "root_cause_cluster":"state-journal-replay",
         "summary":"phantom money", "remediation":"OPEN_UNVERIFIED", "evidence":"REPRODUCED_OFFLINE_PRIOR_AUDIT",
         "candidate_sources":["PAYOPS"]},
        {"id":"LAB-P2-08", "severity":"MEDIUM", "root_cause_cluster":"identity-display-namespace",
         "summary":"identity collision", "remediation":"OPEN_UNVERIFIED", "evidence":"REPRODUCED_OFFLINE_PRIOR_AUDIT"},
        {"id":"GATE-001", "severity":"HIGH", "root_cause_cluster":"release-gate-signal-integrity",
         "summary":"research gate fix", "remediation":"FIXED_AND_REGRESSION_TESTED_RESEARCH_GATE_ONLY",
         "evidence":"REPRODUCED_OFFLINE_PRIOR_AUDIT"}]
    return {"entries":entries, "entries_total":3,"historical_open_findings":2, "recorded_at":"2026-10-08"}


class ControlRoomTests(unittest.TestCase):
    def test_priority_and_scopes(self):
        summary=make_control_room(tiny_registry())
        self.assertEqual(summary["historical_open_findings"],2)
        self.assertEqual(summary["next_experiments"][0]["finding_id"],"LAB-P0-03")
        self.assertEqual(summary["real_world_customer_impact"],"NOT_ESTABLISHED")
        self.assertNotIn("GATE-001",[r["finding_id"] for r in summary["next_experiments"]])

    def test_does_not_mutate_register(self):
        register=tiny_registry()
        before=deepcopy(register)
        make_control_room(register)
        self.assertEqual(register,before)

    def test_detect_duplicate_findings(self):
        register=tiny_registry()
        register["entries"].append(register["entries"][0])
        register["entries_total"]+=1
        register["historical_open_findings"]+=1
        with self.assertRaises(ValueError):
            make_control_room(register)

    def test_detect_count_mismatch(self):
        register=tiny_registry()
        register["historical_open_findings"]=3
        with self.assertRaises(ValueError):
            make_control_room(register)

    def test_limit(self):
        self.assertEqual(len(make_control_room(tiny_registry(),limit=1)["next_experiments"]),1)
        with self.assertRaises(ValueError):
            make_control_room(tiny_registry(),limit=0)


if __name__=="__main__":
    unittest.main()
