"""Check the four scoped PR publishing lanes remain disabled by default."""
from pathlib import Path
import json
import unittest

ROOT=Path(__file__).resolve().parents[1]

class WriterModeTests(unittest.TestCase):
    def test_four_lanes_keep_original_writer_as_default(self):
        lanes={"public-repo-hunter.yml":"scout","catalog-append.yml":"catalog",
               "integrator-sync.yml":"integrator",
               "technology-intelligence.yml":"technology"}
        for file,lane in lanes.items():
            s=(ROOT/".github"/"workflows"/file).read_text()
            with self.subTest(file=file):
                self.assertIn("RETALLY_AUTOMATED_PR_WRITERS_ENABLED",s)
                self.assertIn('if [ "$PR_MODE" = "true" ]; then',s)
                self.assertIn("  submit-pr:",s)
                self.assertIn("--lane "+lane,s)
                self.assertIn("proposal_ready == 'true'",s)
                self.assertIn("refs/heads/main",s)
                self.assertIn("pull-requests: write",s)
                self.assertIn("actions: write",s)

    def test_legacy_job_schedules_and_payloads_remain_present(self):
        files={".github/workflows/public-repo-hunter.yml":'7 4,16 * * *',
               ".github/workflows/catalog-append.yml":"catalog_append_payload.json",
               ".github/workflows/integrator-sync.yml":"integrator_sync_payload.md",
               ".github/workflows/technology-intelligence.yml":"--clean-untracked-on-rebuild"}
        for name,marker in files.items():
            with self.subTest(name=name):
                self.assertIn(marker,(ROOT/name).read_text())

    def test_automatic_main_protection_is_not_enabled_during_migration(self):
        d=json.loads((ROOT/".github/retally-main-ruleset.json").read_text())
        self.assertEqual(d["enforcement"],"disabled")
        policy=(ROOT/"recoveryworks/CODE_RELEASE_POLICY.md").read_text()
        self.assertIn("production_release=HOLD",policy)

if __name__=="__main__":
    unittest.main()
