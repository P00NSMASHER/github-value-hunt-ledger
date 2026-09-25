import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


class TechnologyIntelligenceCanonicalRightsTests(unittest.TestCase):
    def test_master_no_longer_auto_promotes_standing_assertion(self):
        text=(ROOT/"MASTER.md").read_text()
        self.assertIn("automatic_scope_effect=false",text)
        self.assertNotIn(
            "treat repository-owned code as commercially usable under that separate permission",
            text,
        )

    def test_hunter_policy_is_analysis_only_by_default(self):
        data=json.loads((ROOT/"rights"/"RIGHTS_REGISTRY.json").read_text())
        policy=data["subsystem_policy"]["hunter"]
        self.assertEqual("ANALYSIS",policy["default_stage"])
        self.assertFalse(policy["allow_global_assertion_auto_effect"])
        assertion=data["global_assertions"][0]
        self.assertEqual("OWNER_ATTESTED",assertion["evidence_class"])
        self.assertFalse(assertion["automatic_scope_effect"])


if __name__=="__main__":
    unittest.main()
