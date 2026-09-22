from pathlib import Path
import json
import tempfile
import unittest

from production.repository_ingestion import build_repository_intake, render_json


class RepositoryIngestionTests(unittest.TestCase):
    def test_elite_dedupe_and_capability_link(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "hunters").mkdir()
            (root / "intelligence").mkdir()
            (root / "MASTER.md").write_text(
                "# MASTER\n\n### acme/core\n- Revision: `abc123`.\n- Score: **29/30**.\n",
                encoding="utf-8",
            )
            (root / "hunters" / "01.md").write_text(
                "# H\n\n### acme/core\n- URL: https://github.com/acme/core\n"
                "- Exact commit / revision: `abc123`\n- Status: strong / MASTER contender\n"
                "- Value score: **29/30**.\n"
                "\n### low/value\n- URL: https://github.com/low/value\n"
                "- Exact commit / revision: `zzz`\n- Status: watch\n"
                "- Value score: **19/30**.\n",
                encoding="utf-8",
            )
            (root / "intelligence" / "capabilities.jsonl").write_text(
                json.dumps({"capability_id": "CAP-999", "evidence_basis": "acme/core@abc123"})
                + "\n",
                encoding="utf-8",
            )
            records = build_repository_intake(root)
            self.assertEqual(len(records), 1)
            row = records[0]
            self.assertEqual(row.repository, "acme/core")
            self.assertEqual(row.revision, "abc123")
            self.assertEqual(row.ingestion_priority, "P0")
            self.assertEqual(row.structural_state, "CAPABILITY_LINKED")
            self.assertEqual(row.capability_ids, ("CAP-999",))
            self.assertEqual(len(row.record_sha256), 64)

    def test_master_without_score_is_retained(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "hunters").mkdir()
            (root / "intelligence").mkdir()
            (root / "intelligence" / "capabilities.jsonl").write_text("", encoding="utf-8")
            (root / "MASTER.md").write_text(
                "# MASTER\n\n### owner/repo\n- Revision: `deadbeef`.\n",
                encoding="utf-8",
            )
            records = build_repository_intake(root)
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0].structural_state, "MASTER_UNMAPPED")
            self.assertEqual(records[0].ingestion_priority, "P1")

    def test_master_demotion_is_not_requeued(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "hunters").mkdir()
            (root / "intelligence").mkdir()
            (root / "intelligence" / "capabilities.jsonl").write_text("", encoding="utf-8")
            (root / "MASTER.md").write_text(
                "# MASTER\n\n"
                "### good/core\n- Revision: `abcdef1`.\n- Score: **29/30**.\n"
                "\n### bad/core@1234567 — **REMOVED FROM MASTER**\n"
                "- Revision: `1234567`.\n",
                encoding="utf-8",
            )
            records = build_repository_intake(root)
            self.assertEqual([row.repository for row in records], ["good/core"])

    def test_master_family_expands_explicit_repo_revision_pairs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "hunters").mkdir()
            (root / "intelligence").mkdir()
            (root / "intelligence" / "capabilities.jsonl").write_text("", encoding="utf-8")
            (root / "MASTER.md").write_text(
                "# MASTER\n\n### acqagent FAR Overhaul family\n"
                "- Revisions: `acqagent/far-collector@40789a073134a484b2e4a5a2398629b067da0eea`; "
                "`acqagent/rfo-deviations@ccf31107508085cc311fb07488eb513ab97c6b7d`.\n"
                "- Score: **30/30 family**.\n",
                encoding="utf-8",
            )
            records = build_repository_intake(root)
            self.assertEqual(
                [(row.repository, row.revision) for row in records],
                [
                    ("acqagent/far-collector", "40789a073134a484b2e4a5a2398629b067da0eea"),
                    ("acqagent/rfo-deviations", "ccf31107508085cc311fb07488eb513ab97c6b7d"),
                ],
            )
            self.assertTrue(all(row.ingestion_priority == "P0" for row in records))


if __name__ == "__main__":
    unittest.main()
