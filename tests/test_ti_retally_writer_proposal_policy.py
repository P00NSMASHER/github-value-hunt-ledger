"""Scoped, adverse-test-first validation before any RETALLY writer PR promotion."""
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from tools import retally_writer_proposal_policy as p

BASE = "a" * 40
HEAD = "b" * 40


class WriterProposalPolicyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.manifest = Path(self.tmp.name) / "generated.txt"
        self.manifest.write_text(
            "intelligence/LEARNING_STATE.json\n"
            "intelligence/NETWORK_PRIORS.md\n", encoding="utf-8"
        )

    def verify(self, lane, files, *, branch=None, base=BASE, head=HEAD,
               parent=BASE, manifest=None):
        branch = branch or p.branch_for_run(lane, "39603064849", "1")
        return p.verify_proposal(lane, branch, base, head, parent, files,
                                 manifest=manifest or self.manifest)

    def test_run_branch_is_bounded_and_lane_specific(self):
        for lane in p.LANES:
            value = p.branch_for_run(lane, "39603064849", "1")
            self.assertTrue(value.startswith("automation/retally-" + lane + "-"))
            self.assertIsNotNone(p.PROPOSAL_BRANCH.fullmatch(value))
        for lane, id_, attempt in (
            ("other", "39603064849", "1"),
            ("scout", "not-number", "1"),
            ("scout", "1", "1"),
            ("scout", "39603064849", "0"),
            ("scout", "39603064849", "10000"),
        ):
            with self.subTest(lane=lane, id=id_, attempt=attempt):
                with self.assertRaises(p.ProposalHold):
                    p.branch_for_run(lane, id_, attempt)

    def test_all_known_actual_output_shapes_are_permitted(self):
        examples = {
            "scout": ["intelligence/scout_queue/HUNTER-01.json",
                      "intelligence/scout_queue/HUNTER-14.json",
                      "automation/SCOUT_DIGEST.md"],
            "catalog": ["CAPABILITIES.md", "hunters/04-run15-2026-09-20.md",
                        "lanes/retally/new_report.json", "referrals/example.md"],
            "integrator": ["README.md", "SEARCH_SKILLS.md",
                           "production/shadow/review.jsonl",
                           "hunters/04-run13-2026-09-20.md"],
            "technology": ["intelligence/LEARNING_STATE.json",
                           "intelligence/NETWORK_PRIORS.md"],
        }
        for lane, files in examples.items():
            with self.subTest(lane=lane):
                self.assertEqual(self.verify(lane, files).files, tuple(files))

    def test_the_real_manifest_is_bounded_and_safe(self):
        entries = p.generated_manifest()
        self.assertGreater(len(entries), 60)
        self.assertIn("intelligence/LEARNING_STATE.json", entries)
        self.assertIn("intelligence/activation_directives.jsonl", entries)
        self.assertTrue(all(entry.startswith("intelligence/") for entry in entries))
        self.assertFalse(any(entry.startswith(".github/") for entry in entries))

    def test_cross_lane_writes_and_execution_payloads_are_rejected(self):
        paths = (
            ".github/workflows/recoveryworks.yml",
            ".github/retally-main-ruleset.json",
            "production/requirements-ci.txt",
            "customer/evidence.json",
            "intelligence/scout_queue/retally.py",
            "intelligence/LEARNING_STATE.json",
            "automation/SCOUT_DIGEST.md",
            "../outside.md", "/absolute.md", "hunters/../../unsafe.md",
            "hunters//hidden.md", "hunters/.secrets.json",
            "hunters/customer.sqlite", "hunters/key.pem",
            "hunters/file.md\nInjected-Header",
        )
        for lane in p.LANES:
            for path in paths:
                allowed = (
                    lane == "scout" and path in {"automation/SCOUT_DIGEST.md"}
                    or lane == "technology" and path == "intelligence/LEARNING_STATE.json"
                )
                if allowed:
                    continue
                with self.subTest(lane=lane, path=path):
                    with self.assertRaises(p.ProposalHold):
                        self.verify(lane, [path])

    def test_sha_parent_branch_and_counts_are_frozen(self):
        for kw in (
            {"base": "abc"}, {"head": "not-a-sha"},
            {"parent": HEAD}, {"head": BASE},
            {"branch": "main"},
            {"branch": "automation/retally-catalog-39603064849-1"},
        ):
            with self.subTest(case=kw), self.assertRaises(p.ProposalHold):
                self.verify("scout", ["automation/SCOUT_DIGEST.md"], **kw)
        with self.assertRaises(p.ProposalHold):
            self.verify("catalog", [])
        with self.assertRaises(p.ProposalHold):
            self.verify("catalog", ["CAPABILITIES.md"] * 2)
        with self.assertRaises(p.ProposalHold):
            self.verify("catalog", ["CAPABILITIES.md"] * 513)

    def test_deletes_and_renames_require_reconciliation_not_auto_merge(self):
        for status in ("removed", "renamed", "unknown", None):
            with self.subTest(status=status), self.assertRaises(p.ProposalHold):
                self.verify("scout", {"automation/SCOUT_DIGEST.md": status})
        self.assertEqual(
            self.verify("scout", {"automation/SCOUT_DIGEST.md": "modified"}).files,
            ("automation/SCOUT_DIGEST.md",)
        )

    def test_manifest_missing_or_unsafe_is_a_hard_hold(self):
        for value in (
            "", "intelligence/LEARNING_STATE.json\nintelligence/LEARNING_STATE.json\n",
            "tools/ti_persist_generated.py\n",
            ".github/workflows/recoveryworks.yml\n",
            "intelligence/private.key\n",
            "intelligence/../private.json\n",
        ):
            self.manifest.write_text(value, encoding="utf-8")
            with self.subTest(manifest=value), self.assertRaises(p.ProposalHold):
                self.verify("technology", ["intelligence/LEARNING_STATE.json"])

    def test_no_provider_write_functions_exist_in_scope_module(self):
        source = Path(p.__file__).read_text(encoding="utf-8")
        for prohibited in ("git push", "gh api", "os.system(", "subprocess.run(",
                           "urllib.request", "requests.post("):
            self.assertNotIn(prohibited, source)


if __name__ == "__main__":
    unittest.main()
