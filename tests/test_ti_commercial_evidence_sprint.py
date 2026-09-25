import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
POLICY=ROOT/"COMMERCIAL_EVIDENCE_SPRINT.md"
CONTRACT=ROOT/"intelligence"/"commercial_evidence_sprint.json"

class CommercialEvidenceSprintTests(unittest.TestCase):
    def test_policy_and_contract_are_active(self):
        text=POLICY.read_text()
        data=json.loads(CONTRACT.read_text())
        self.assertEqual("ACTIVE",data["status"])
        self.assertTrue(data["architecture_freeze"])
        self.assertEqual(["freightrecovery","capturebrief"],data["primary_tracks"])
        self.assertEqual("NAMED_EVIDENCE_GAP_ONLY",data["hunter_mode"])
        self.assertIn("Broad discovery is paused",text)
        self.assertIn("does not authorize outreach",text)

if __name__=="__main__":
    unittest.main()
