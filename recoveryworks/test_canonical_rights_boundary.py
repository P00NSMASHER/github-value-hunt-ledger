import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


class RecoveryWorksCanonicalRightsTests(unittest.TestCase):
    def test_recoveryworks_uses_canonical_rights_policy(self):
        data=json.loads((ROOT/"rights"/"RIGHTS_REGISTRY.json").read_text())
        policy=data["subsystem_policy"]["recoveryworks"]
        self.assertTrue(policy["canonical_registry_required"])
        self.assertFalse(policy["allow_global_assertion_auto_effect"])
        self.assertEqual("ANALYSIS",policy["default_stage"])

    def test_portfolio_document_rejects_hunter_inheritance(self):
        text=(ROOT/"recoveryworks"/"PORTFOLIO.md").read_text()
        self.assertIn("does not inherit commercial permission from Hunter",text)
        self.assertIn("rights/RIGHTS_REGISTRY.json",text)


if __name__=="__main__":
    unittest.main()
