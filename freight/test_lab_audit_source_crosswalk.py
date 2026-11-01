"""Keep two historical Freight research registries aligned, without certifying production."""
from __future__ import annotations

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent


def read(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


class AuditCrosswalkTests(unittest.TestCase):
    def test_26_historical_and_two_gate_findings_are_never_silently_lost(self):
        first = read("research/LAB_FINDINGS_CUMULATIVE.json")
        second = read("lab_integrity/CUMULATIVE_FINDINGS.json")
        primary = {row["id"]: row for row in first["entries"]}
        detailed = {row["id"]: row for row in second["items"]}
        self.assertEqual(len(primary), 28)
        self.assertEqual(set(primary), set(detailed))
        self.assertEqual(first["entries_total"], 28)
        self.assertEqual(second["total_observations"], 28)
        self.assertEqual(second["historical_observations"], 26)
        self.assertEqual(second["open_unrepaired_historical"], 26)
        self.assertEqual(second["gate_self_test_observations"], 2)
        gate = {"GATE-001", "GATE-002"}
        self.assertEqual({k for k in primary if k.startswith("GATE-")}, gate)
        for key in set(primary) - gate:
            self.assertIn("OPEN", primary[key]["remediation"])
            self.assertIn("OPEN", detailed[key]["remediation"])
        for key in gate:
            self.assertIn("RESEARCH_GATE_ONLY", primary[key]["remediation"])
            self.assertIn("RESEARCH_ONLY", detailed[key]["remediation"])

    def test_donor_shortlists_are_distinct_and_not_executable_evidence(self):
        broad = read("research/HUNTED_CODE_REUSE_CANDIDATES.json")
        narrow = read("lab_integrity/HUNTED_DONOR_SHORTLIST.json")
        self.assertEqual(len(broad["ranked"]), 9)
        self.assertEqual(len(narrow["candidates"]), 8)
        self.assertIs(narrow["code_copied_into_recoveryos"], False)
        self.assertEqual(len({
            row["repository"].lower() for row in broad["ranked"]
        }), 9)
        self.assertEqual(len({
            row["repository"].lower() for row in narrow["candidates"]
        }), 8)


if __name__ == "__main__":
    unittest.main()
