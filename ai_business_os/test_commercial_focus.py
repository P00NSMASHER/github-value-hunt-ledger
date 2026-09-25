import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
POLICY=ROOT/"ai_business_os"/"COMMERCIAL_FOCUS_V1.json"

class CommercialFocusTests(unittest.TestCase):
    def test_two_primary_tracks_and_one_infrastructure_track(self):
        data=json.loads(POLICY.read_text())
        self.assertEqual("ACTIVE",data["status"])
        self.assertEqual(["FreightRecovery","CaptureBrief"],[x["business"] for x in data["primary_validation_tracks"]])
        self.assertEqual(["RecoveryOS"],[x["business"] for x in data["shared_infrastructure"]])
        self.assertEqual(0,data["current_verified_external_outcomes"])
        self.assertFalse(data["consequential_actions_authorized"])
        self.assertTrue(all(x["current_stage"]=="MEASURING" for x in data["primary_validation_tracks"]))

if __name__=="__main__":
    unittest.main()
