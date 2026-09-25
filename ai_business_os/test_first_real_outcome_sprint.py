import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class FirstRealOutcomeSprintTests(unittest.TestCase):
    def setUp(self):
        self.outcome=json.loads((ROOT/"ai_business_os"/"EXTERNAL_OUTCOME_LEARNING_V1.json").read_text())
        self.sprint=json.loads((ROOT/"ai_business_os"/"EVIDENCE_SPRINT_2026_09_25.json").read_text())

    def test_delivery_failure_is_real_but_not_buyer_rejection(self):
        self.assertIn("OUTREACH_DELIVERY_FAILURE",self.outcome["outcome_types"])
        self.assertEqual(-0.2,self.outcome["reward_policy"]["OUTREACH_DELIVERY_FAILURE"])
        self.assertEqual(1,self.outcome["current_real_state"]["verified_external_outcomes"])
        self.assertFalse(self.outcome["first_real_outcome"]["buyer_rejection"])
        self.assertFalse(self.outcome["first_real_outcome"]["allocation_changed"])

    def test_capturebrief_delivery_accounting(self):
        c=self.sprint["capturebrief"]
        self.assertEqual(3,c["sent"])
        self.assertEqual(2,c["delivered"])
        self.assertEqual(1,c["delivery_failures"])
        self.assertEqual(0,c["buyer_replies"])

    def test_starblox_needs_real_receipts_not_more_architecture(self):
        s=self.sprint["starblox"]
        self.assertTrue(s["playtest_harness_present"])
        self.assertEqual(0,s["verified_human_playtest_receipts"])
        self.assertEqual("OPEN",s["playtest_gap_status"])

if __name__=="__main__":
    unittest.main()
