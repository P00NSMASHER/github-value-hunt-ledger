"""Adversarial tests for one bounded proof-merge rerun on an unrelated main change."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile
from unittest import TestCase
from unittest.mock import patch

from tools import retally_automated_pr_merge as merge
from tools.retally_writer_proposal_policy import ProposalHold

BASE = "a" * 40
HEAD = "b" * 40
LATEST = "c" * 40
PROOF = "d" * 40
TREE = "e" * 40
MERGED = "f" * 40
LANE = "catalog"
BRANCH = "automation/retally-catalog-39631700353-1"
PROOF_BRANCH = "automation/retally-proof-39631700353-1"
FILE = "lanes/synthetic-only.md"
OTHER = "deployment/oracle-always-free/oci_readonly_health.py"


def proposal():
    return {
        "number": 99, "state": "open", "draft": False, "merged": False,
        "user": {"login": "github-actions[bot]"}, "changed_files": 1,
        "head": {"ref": BRANCH, "sha": HEAD,
                 "repo": {"full_name": merge.REPO}},
        "base": {"ref": "main", "sha": BASE},
    }


def fake_api(method: str, path: str, payload: dict | None = None):
    repo = "repos/" + merge.REPO
    if method == "GET":
        if path == repo + "/pulls/99":
            return proposal()
        if path == repo + "/branches/main":
            return {"commit": {"sha": LATEST}}
        if path == repo + "/git/commits/" + HEAD:
            return {"parents": [{"sha": BASE}]}
        if path == repo + "/git/commits/" + PROOF:
            return {"parents": [{"sha": LATEST}, {"sha": HEAD}],
                    "tree": {"sha": TREE}}
        if path == repo + "/git/commits/" + MERGED:
            return {"tree": {"sha": TREE}}
        if path == repo + "/compare/" + BASE + "..." + HEAD:
            return {"status": "ahead", "ahead_by": 1, "behind_by": 0,
                    "files": [{"filename": FILE, "status": "added"}]}
        if path == repo + "/compare/" + BASE + "..." + LATEST:
            return {"status": "ahead", "ahead_by": 1, "behind_by": 0,
                    "files": [{"filename": OTHER, "status": "modified"}]}
        if path == repo + "/compare/" + LATEST + "..." + PROOF:
            return {"status": "ahead", "ahead_by": 2, "behind_by": 0,
                    "files": [{"filename": FILE, "status": "added"}]}
    if method == "POST":
        if path == repo + "/git/refs":
            assert payload == {"ref": "refs/heads/" + PROOF_BRANCH, "sha": LATEST}
            return {"ref": payload["ref"], "object": {"sha": LATEST}}
        if path == repo + "/merges":
            assert payload["base"] == PROOF_BRANCH
            assert payload["head"] == HEAD
            return {"sha": PROOF}
    if method == "PUT" and path == repo + "/pulls/99/merge":
        assert payload["sha"] == HEAD and payload["merge_method"] == "merge"
        return {"merged": True, "sha": MERGED}
    raise AssertionError("Unexpected provider method/route: " + method + " " + path)


class RaceProofTests(TestCase):
    def test_disjoint_main_update_gets_one_isolated_ci_proof_and_normal_merge(self):
        env = {"GITHUB_RUN_ID": "39631700353", "GITHUB_RUN_ATTEMPT": "1",
               "RETALLY_GUARDED_MAIN_RACE_PROOF_ENABLED": "true"}
        calls = []
        def traced(method, route, payload=None):
            calls.append((method, route))
            return fake_api(method, route, payload)
        with patch.dict(os.environ, env), patch.object(merge, "gh", side_effect=traced), \
             patch.object(merge, "dispatch_and_verify", return_value=455) as fresh:
            result = merge.integrate(LANE, 99, HEAD, BASE)
        fresh.assert_called_once()
        self.assertEqual(fresh.call_args.args, (PROOF_BRANCH, PROOF))
        self.assertIn("deadline", fresh.call_args.kwargs)
        self.assertIsInstance(fresh.call_args.kwargs["deadline"], float)
        self.assertEqual(result["result"], "MERGED_WITH_RECONCILED_TREE_CI")
        self.assertEqual(result["ci_run_id"], 455)
        self.assertEqual(result["merged_sha"], MERGED)
        self.assertEqual(result["proof_sha"], PROOF)
        self.assertEqual(result["tested_main_sha"], LATEST)
        self.assertEqual(result["customer_release"], "HOLD")
        self.assertEqual([name for name, _ in calls if name == "PUT"], ["PUT"])
        self.assertEqual(len([name for name, _ in calls if name == "POST"]), 2)

    def test_unrelated_main_changes_must_be_linear_small_and_source_independent(self):
        with patch.object(merge, "gh", side_effect=fake_api):
            merge._unrelated_main_changes(LANE, BASE, LATEST, (FILE,))
        sensitive = (
            FILE, ".github/workflows/catalog-append.yml",
            "tools/retally_payload_incremental.py",
            "tests/test_ti_retally_generated_pr_controller.py",
            "lanes/another-file.md",
        )
        for changed in sensitive:
            with self.subTest(path=changed):
                def changed_response(method, path, payload=None):
                    if path.endswith(BASE + "..." + LATEST):
                        return {"status": "ahead", "ahead_by": 1, "behind_by": 0,
                                "files": [{"filename": changed, "status": "modified"}]}
                    return fake_api(method, path, payload)
                with patch.object(merge, "gh", side_effect=changed_response), \
                     self.assertRaises(ProposalHold):
                    merge._unrelated_main_changes(LANE, BASE, LATEST, (FILE,))

    def test_non_linear_invalid_or_truncated_main_diff_fails_before_git_writes(self):
        variants = (
            {"status": "diverged", "ahead_by": 1, "behind_by": 1,
             "files": [{"filename": OTHER, "status": "modified"}]},
            {"status": "ahead", "ahead_by": 13, "behind_by": 0,
             "files": [{"filename": OTHER, "status": "modified"}]},
            {"status": "ahead", "ahead_by": 1, "behind_by": 0, "files": []},
            {"status": "ahead", "ahead_by": 1, "behind_by": 0,
             "files": [{"filename": OTHER}, {"filename": OTHER}]},
        )
        for changed in variants:
            with self.subTest(changed=changed):
                def response(method, path, payload=None):
                    if path.endswith(BASE + "..." + LATEST):
                        return changed
                    return fake_api(method, path, payload)
                with patch.object(merge, "gh", side_effect=response), \
                     self.assertRaises(ProposalHold):
                    merge._unrelated_main_changes(LANE, BASE, LATEST, (FILE,))

    def test_fake_tree_and_wrong_proof_parent_are_rejected_before_release_ci(self):
        for target, replacement in (
            ("/git/commits/" + PROOF,
             {"parents": [{"sha": BASE}, {"sha": HEAD}], "tree": {"sha": TREE}}),
            ("/compare/" + LATEST + "..." + PROOF,
             {"status": "ahead", "ahead_by": 1, "behind_by": 0,
              "files": [{"filename": ".github/workflows/evil.yml", "status": "added"}]}),
        ):
            def wrong(method, path, payload=None):
                if method == "GET" and path.endswith(target):
                    return replacement
                return fake_api(method, path, payload)
            with self.subTest(target=target), \
                 patch.dict(os.environ, {"GITHUB_RUN_ID": "39631700353",
                                         "GITHUB_RUN_ATTEMPT": "1",
                                         "RETALLY_GUARDED_MAIN_RACE_PROOF_ENABLED": "true"}), \
                 patch.object(merge, "gh", side_effect=wrong), \
                 patch.object(merge, "dispatch_and_verify") as fresh, \
                 self.assertRaises(ProposalHold):
                merge.integrate(LANE, 99, HEAD, BASE)
                fresh.assert_not_called()

    def test_main_race_after_reconciled_ci_keeps_bot_proposal_unmerged(self):
        calls = []
        main_reads = 0
        def provider(method, path, payload=None):
            nonlocal main_reads
            calls.append((method, path))
            if method == "GET" and path.endswith("/branches/main"):
                main_reads += 1
                if main_reads >= 4:
                    return {"commit": {"sha": "9" * 40}}
            return fake_api(method, path, payload)
        with patch.dict(os.environ, {"GITHUB_RUN_ID": "39631700353",
                                     "GITHUB_RUN_ATTEMPT": "1",
                                     "RETALLY_GUARDED_MAIN_RACE_PROOF_ENABLED": "true"}), \
             patch.object(merge, "gh", side_effect=provider), \
             patch.object(merge, "dispatch_and_verify", return_value=45), \
             self.assertRaises(ProposalHold):
            merge.integrate(LANE, 99, HEAD, BASE)
        self.assertFalse(any(method == "PUT" for method, _ in calls))

    def test_expired_budget_blocks_ci_dispatch_before_provider_writes(self):
        with patch.object(merge.time, "monotonic", return_value=5000.0), \
             patch.object(merge, "gh") as provider, \
             self.assertRaises(ProposalHold):
            merge.dispatch_and_verify(BRANCH, HEAD, deadline=5010.0)
        provider.assert_not_called()

    def test_actual_git_proof_has_two_reachable_commits_and_one_file_change(self):
        """Avoid mocking GitHub's genuine two-parent merged-graph count."""
        with tempfile.TemporaryDirectory(prefix="retally-real-proof-") as tmp:
            repo = Path(tmp)
            def git(*args):
                done = subprocess.run(["git", *args], cwd=repo,
                                      capture_output=True, text=True,
                                      timeout=15, check=True)
                return done.stdout.strip()
            git("init", "-q")
            git("config", "user.email", "offline-qa@example.invalid")
            git("config", "user.name", "Offline QA")
            (repo / "base.txt").write_text("base\n")
            git("add", "base.txt")
            git("commit", "-qm", "base")
            git("branch", "-M", "main")
            git("checkout", "-qb", "writer")
            (repo / "lanes").mkdir()
            (repo / "lanes/synthetic.md").write_text("TEST_ONLY\n")
            git("add", "lanes/synthetic.md")
            git("commit", "-qm", "writer")
            writer = git("rev-parse", "HEAD")
            git("checkout", "-q", "main")
            (repo / "unrelated.txt").write_text("main advance\n")
            git("add", "unrelated.txt")
            git("commit", "-qm", "unrelated main")
            main = git("rev-parse", "HEAD")
            git("checkout", "-qb", "proof")
            git("merge", "--no-ff", "-qm", "merge proof", writer)
            proof = git("rev-parse", "HEAD")
            self.assertEqual(git("rev-list", "--count", main + ".." + proof), "2")
            self.assertEqual(git("rev-list", "--parents", "-n", "1", proof).split()[1:],
                             [main, writer])
            self.assertEqual(git("diff", "--name-only", main, proof),
                             "lanes/synthetic.md")

    def test_forged_single_commit_proof_is_rejected_before_dispatch(self):
        def fake_bad(method, path, payload=None):
            if path.endswith("/compare/" + LATEST + "..." + PROOF):
                return {"status": "ahead", "ahead_by": 1, "behind_by": 0,
                        "files": [{"filename": FILE, "status": "added"}]}
            return fake_api(method, path, payload)
        with patch.dict(os.environ, {"GITHUB_RUN_ID": "39631700353",
                                      "GITHUB_RUN_ATTEMPT": "1",
                                      "RETALLY_GUARDED_MAIN_RACE_PROOF_ENABLED": "true"}), \
             patch.object(merge, "gh", side_effect=fake_bad), \
             patch.object(merge, "dispatch_and_verify") as ci, \
             self.assertRaises(ProposalHold):
            merge.integrate(LANE, 99, HEAD, BASE)
            ci.assert_not_called()

    def test_default_disabled_proof_mode_never_writes_git_refs_or_merges(self):
        calls = []
        def observe(method, path, payload=None):
            calls.append((method, path))
            return fake_api(method, path, payload)
        with patch.dict(os.environ, {"GITHUB_RUN_ID": "39631700353",
                                     "GITHUB_RUN_ATTEMPT": "1",
                                     "RETALLY_GUARDED_MAIN_RACE_PROOF_ENABLED": "false"}), \
             patch.object(merge, "gh", side_effect=observe), \
             patch.object(merge, "dispatch_and_verify") as ci, \
             self.assertRaises(ProposalHold):
            merge.integrate(LANE, 99, HEAD, BASE)
            ci.assert_not_called()
        self.assertFalse(any(method in {"POST", "PUT"} for method, _ in calls))

    def test_missing_run_identity_refuses_provider_write(self):
        with patch.dict(os.environ, {"GITHUB_RUN_ID": "", "GITHUB_RUN_ATTEMPT": "1"}), \
             self.assertRaises(ProposalHold):
            merge._proof_branch_from_run()


if __name__ == "__main__":
    import unittest
    unittest.main()
