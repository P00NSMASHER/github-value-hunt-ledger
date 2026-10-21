"""Negative/positive tests for the synthetic-only GitHub PR merge canary."""
from __future__ import annotations

import datetime as dt
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools import retally_guarded_pr_canary as target


BRANCH = "automation/retally-guard-canary-20261021-abcdef12"
HEAD = "a" * 40
BASE = "b" * 40
FILE = "automation/canary/guarded-20261021-abcdef12.md"


class InertCanaryTests(unittest.TestCase):
    def test_branch_identity_is_bounded(self):
        self.assertTrue(target.CANARY_BRANCH.fullmatch(BRANCH))
        for branch in (
            "", "main", "automation/retally-guard-canary-20261021-../x",
            "automation/retally-guard-canary-20261021-XYZ12345",
            "automation/retally-guard-canary-2026102-abcdef12",
            "automation/retally-guard-canary-20261021-abcdef12/extra",
            "automation/retally-guard-canary-20261021-abcdef12..",
        ):
            with self.subTest(branch=branch):
                self.assertIsNone(target.CANARY_BRANCH.fullmatch(branch))

    def _fixture(self):
        tmp = tempfile.TemporaryDirectory(prefix="retally-inert-pr-")
        repo = Path(tmp.name)
        p = repo / FILE
        p.parent.mkdir(parents=True)
        p.write_text(target.SENTINEL + "\n", encoding="utf-8")
        self.addCleanup(tmp.cleanup)
        return repo

    def test_exact_parent_and_single_inert_file(self):
        repo = self._fixture()

        def fake_run(*args, **kwargs):
            if args[1] == "rev-list":
                return HEAD + " " + BASE
            if args[1] == "rev-parse":
                return BASE
            if args[1] == "diff":
                return FILE
            if args[1] == "status":
                return ""
            raise AssertionError("Unexpected git action")

        with patch.object(target, "run", side_effect=fake_run):
            self.assertEqual(target.assert_inert_change(BRANCH, HEAD, repo), BASE)

    def test_changed_main_wrong_parent_and_extra_files_fail_closed(self):
        repo = self._fixture()
        calls = [
            { "parent": "c" * 40, "base": BASE, "diff": FILE },
            { "parent": BASE, "base": "d" * 40, "diff": FILE },
            { "parent": BASE, "base": BASE,
              "diff": FILE + "\n.github/workflows/repository-release-gate.yml" },
            { "parent": BASE, "base": BASE, "diff": "customer/evidence.pdf" },
        ]
        for case in calls:
            with self.subTest(case=case):
                def fake_run(*args, **kwargs):
                    if args[1] == "rev-list":
                        return HEAD + " " + case["parent"]
                    if args[1] == "rev-parse":
                        return case["base"]
                    if args[1] == "diff":
                        return case["diff"]
                    return ""
                with patch.object(target, "run", side_effect=fake_run):
                    with self.assertRaises(target.Hold):
                        target.assert_inert_change(BRANCH, HEAD, repo)

    def test_symlink_oversized_marker_and_dirty_checkout_fail(self):
        repo = self._fixture()
        p = repo / FILE

        def fake_run(*args, **kwargs):
            return {
                "rev-list": HEAD + " " + BASE, "rev-parse": BASE,
                "diff": FILE, "status": "",
            }[args[1]]

        with patch.object(target, "run", side_effect=fake_run):
            p.write_text("not a synthetic release", encoding="utf-8")
            with self.assertRaises(target.Hold):
                target.assert_inert_change(BRANCH, HEAD, repo)
            p.write_text(target.SENTINEL + ("x" * 520), encoding="utf-8")
            with self.assertRaises(target.Hold):
                target.assert_inert_change(BRANCH, HEAD, repo)
            p.write_text(target.SENTINEL, encoding="utf-8")
        with patch.object(target, "run", side_effect=lambda *a, **k:
                          " M unapproved.txt" if a[1] == "status" else fake_run(*a, **k)):
            with self.assertRaises(target.Hold):
                target.assert_inert_change(BRANCH, HEAD, repo)

    def test_api_refuses_cross_repo_even_before_network(self):
        with patch.object(target, "run") as runner:
            with self.assertRaises(target.Hold):
                target.api("GET", "repos/other/repo/pulls/1")
            runner.assert_not_called()
            runner.return_value = '{"number": 19}'
            self.assertEqual(target.api("GET", "repos/" + target.REPO + "/pulls/19"),
                             {"number": 19})

    def test_all_five_successful_fresh_jobs_required(self):
        good = [{"name": x, "conclusion": "success"} for x in target.REQUIRED_JOBS]
        self.assertTrue(target.valid_release_jobs(good))
        self.assertFalse(target.valid_release_jobs(good[:-1]))
        self.assertFalse(target.valid_release_jobs(good[:-1] + [
            {"name": good[-1]["name"], "conclusion": "skipped"}
        ]))
        self.assertFalse(target.valid_release_jobs([{"name": "release-gate",
                                                     "conclusion": "success"}]))
        self.assertFalse(target.valid_release_jobs({}))

    def test_dispatch_run_must_match_ref_sha_event_and_time(self):
        now = dt.datetime(2026, 10, 21, 15, 0, tzinfo=dt.timezone.utc)
        ok = {"event": "workflow_dispatch", "head_sha": HEAD,
              "head_branch": BRANCH, "id": 19,
              "created_at": "2026-10-21T15:00:01Z"}
        self.assertEqual(target.matching_run([ok], BRANCH, HEAD, now), ok)
        for changed in (
            {"event": "pull_request"}, {"head_sha": BASE},
            {"head_branch": "main"}, {"created_at": "2026-10-21T14:58:00Z"},
            {"created_at": "invalid"},
        ):
            with self.subTest(changed=changed):
                self.assertIsNone(target.matching_run(
                    [{**ok, **changed}], BRANCH, HEAD, now))

    def test_non_owner_or_nonpush_cannot_get_to_provider(self):
        env = {"GITHUB_REPOSITORY": target.REPO, "GITHUB_EVENT_NAME": "push",
               "GITHUB_ACTOR": "P00NSMASHER", "GH_TOKEN": "test-not-a-real-secret",
               "GITHUB_REF_NAME": BRANCH, "GITHUB_SHA": HEAD}
        for key, invalid in (
            ("GITHUB_REPOSITORY", "other/repo"),
            ("GITHUB_EVENT_NAME", "pull_request"),
            ("GITHUB_ACTOR", "github-actions[bot]"),
            ("GH_TOKEN", ""),
        ):
            with self.subTest(key=key), patch.dict("os.environ", {
                    **env, key: invalid}, clear=True), patch.object(target, "api") as api:
                with self.assertRaises(target.Hold):
                    target.main()
                api.assert_not_called()

    def test_workflow_only_grants_write_to_inert_branch_job(self):
        yaml = (Path(__file__).resolve().parents[1] /
                ".github/workflows/retally-guarded-pr-canary.yml").read_text()
        self.assertIn("github.actor == 'P00NSMASHER'", yaml)
        self.assertIn("automation/retally-guard-canary-*", yaml)
        self.assertIn("automation/canary/guarded-*.md", yaml)
        self.assertIn("pull-requests: write", yaml)
        self.assertIn("actions: write", yaml)
        self.assertIn("name: RETALLY Guarded Synthetic PR Canary", yaml)
        self.assertNotIn("workflow_run:", yaml)
        self.assertNotIn("schedule:", yaml)


if __name__ == "__main__":
    unittest.main()
