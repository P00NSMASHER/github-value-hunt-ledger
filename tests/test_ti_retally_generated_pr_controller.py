"""Bot-only generated source PR controller: simulated API, no network or writes."""
from __future__ import annotations

import datetime as dt
from pathlib import Path
from unittest.mock import patch
import unittest

from tools import retally_automated_pr_merge as merge
from tools import retally_automated_pr_proposal as proposal
from tools.retally_writer_proposal_policy import ProposalHold

BASE = "a" * 40
HEAD = "b" * 40
BRANCH = "automation/retally-scout-39603064849-1"
FILE = "automation/SCOUT_DIGEST.md"


def candidate_pr():
    return {
        "number": 19, "state": "open", "draft": False, "merged": False,
        "user": {"login": "github-actions[bot]"}, "changed_files": 1,
        "head": {"ref": BRANCH, "sha": HEAD,
                 "repo": {"full_name": proposal.REPO}},
        "base": {"ref": "main", "sha": BASE},
    }


def fake_authority_api(method, endpoint, payload=None):
    if "/actions/workflows/repository-release-gate.yml/runs?event=pull_request" in endpoint:
        return {"workflow_runs": [native_run(candidate_pr())]}
    if endpoint.endswith("/actions/runs/312/jobs?per_page=100"):
        return {"total_count": 5, "jobs": [{"name": name, "conclusion": "success"}
                                            for name in merge.REQUIRED_JOBS]}
    if endpoint.endswith("/branches/main"):
        return {"commit": {"sha": BASE}}
    if endpoint.endswith("/git/commits/" + HEAD):
        return {"parents": [{"sha": BASE}]}
    if endpoint.endswith("/compare/" + BASE + "..." + HEAD):
        return {"status": "ahead", "ahead_by": 1, "behind_by": 0,
                "files": [{"filename": FILE, "status": "modified"}]}
    if endpoint.endswith("/pulls/19"):
        return candidate_pr()
    raise AssertionError("Unexpected provider request: " + method + " " + endpoint)


def native_run(pr):
    return {"id": 312, "event": "pull_request", "status": "completed", "conclusion": "success",
            "path": ".github/workflows/repository-release-gate.yml",
            "head_sha": pr["head"]["sha"], "head_branch": pr["head"]["ref"],
            "head_repository": {"full_name": proposal.REPO}, "pull_requests": [pr]}


class GeneratedBotControllerTests(unittest.TestCase):
    def test_valid_generated_main_sha_and_path(self):
        with patch.object(merge, "gh", side_effect=fake_authority_api):
            pr, verified = merge.guarded_target("scout", 19, HEAD, BASE)
        self.assertEqual(pr["number"], 19)
        self.assertEqual(verified.files, (FILE,))

    def test_bad_pr_authority_is_refused_before_ci_or_merge(self):
        for mutation in (
            {"user": {"login": "P00NSMASHER"}},
            {"head": {"ref": BRANCH, "sha": HEAD,
                      "repo": {"full_name": "other/fork"}}},
            {"head": {"ref": "main", "sha": HEAD,
                      "repo": {"full_name": proposal.REPO}}},
            {"base": {"ref": "other", "sha": BASE}},
            {"state": "closed"},
            {"draft": True},
        ):
            def api(method, endpoint, payload=None):
                if endpoint.endswith("/pulls/19"):
                    return {**candidate_pr(), **mutation}
                return fake_authority_api(method, endpoint, payload)
            with self.subTest(mutation=mutation), patch.object(merge, "gh", side_effect=api):
                with self.assertRaises(ProposalHold):
                    merge.guarded_target("scout", 19, HEAD, BASE)

    def test_changed_main_wrong_parent_or_cross_scope_never_pass(self):
        for case in ("stale", "second_parent", "workflow_path",
                     "deletion", "many_commits", "truncated"):
            def api(method, endpoint, payload=None):
                if case == "stale" and endpoint.endswith("/branches/main"):
                    return {"commit": {"sha": "c" * 40}}
                if case == "second_parent" and "/git/commits/" in endpoint:
                    return {"parents": [{"sha": BASE}, {"sha": HEAD}]}
                if "/compare/" in endpoint:
                    result = fake_authority_api(method, endpoint, payload).copy()
                    if case == "workflow_path":
                        result["files"] = [{
                            "filename": ".github/workflows/recoveryworks.yml",
                            "status": "modified"}]
                    if case == "deletion":
                        result["files"] = [{"filename": FILE, "status": "removed"}]
                    if case == "many_commits":
                        result["ahead_by"] = 2
                    if case == "truncated":
                        result["files"] = []
                    return result
                return fake_authority_api(method, endpoint, payload)
            with self.subTest(case=case), patch.object(merge, "gh", side_effect=api):
                with self.assertRaises(ProposalHold):
                    merge.guarded_target("scout", 19, HEAD, BASE)

    def test_actual_release_gate_requires_five_passes(self):
        items = [{"name": x, "conclusion": "success"} for x in merge.REQUIRED_JOBS]
        self.assertTrue(merge.completed_release_jobs(items))
        self.assertFalse(merge.completed_release_jobs(items[:-1]))
        for status in ("pending", "skipped", "neutral", "failure", "cancelled"):
            with self.subTest(status=status):
                item = items[:-1] + [{"name": items[-1]["name"], "conclusion": status}]
                self.assertFalse(merge.completed_release_jobs(item))

    def test_dispatched_run_must_match_sha_branch_event_and_time(self):
        now = dt.datetime(2026, 10, 21, 14, 0, tzinfo=dt.timezone.utc)
        item = {"event": "workflow_dispatch", "head_sha": HEAD,
                "head_branch": BRANCH, "created_at": "2026-10-21T14:00:01Z"}
        self.assertEqual(merge.match_fresh_run([item], BRANCH, HEAD, now), item)
        for replace in ({"event": "pull_request"}, {"head_sha": BASE},
                        {"head_branch": "main"},
                        {"created_at": "2026-10-21T13:55:00Z"},
                        {"created_at": "invalid"}):
            with self.subTest(replace=replace):
                self.assertIsNone(merge.match_fresh_run(
                    [{**item, **replace}], BRANCH, HEAD, now))

    def test_integrate_rechecks_source_after_ci_then_requests_one_normal_merge(self):
        requests = []
        def api(method, endpoint, payload=None):
            if method == "PUT":
                requests.append((endpoint, payload))
                return {"merged": True, "sha": "c" * 40}
            return fake_authority_api(method, endpoint, payload)
        with patch.object(merge, "gh", side_effect=api), \
             patch.object(merge, "dispatch_and_verify", return_value=991) as ci:
            result = merge.integrate("scout", 19, HEAD, BASE)
        ci.assert_called_once()
        self.assertEqual(ci.call_args.args, (BRANCH, HEAD))
        self.assertEqual(result["pr_ci_run_id"], 312)
        self.assertEqual(result["result"], "MERGED_WITH_ACTUAL_CI")
        self.assertEqual(result["customer_release"], "HOLD")
        self.assertEqual(requests, [(
            f"repos/{proposal.REPO}/pulls/19/merge",
            {"sha": HEAD, "merge_method": "merge",
             "commit_title": "Automated source-verified scout evidence refresh",
             "commit_message": "Owner-authorized, scoped evidence-only PR. "
                               "The five exact-head repository release jobs passed. "
                               "Financial/customer release evidence remains HOLD."}
        )])

    def test_merge_must_fail_on_provider_rejection_or_missing_receipt(self):
        with patch.object(merge, "gh", side_effect=lambda meth, endpoint, payload=None:
                          {"merged": False} if meth == "PUT"
                          else fake_authority_api(meth, endpoint, payload)), \
             patch.object(merge, "dispatch_and_verify", return_value=42):
            with self.assertRaises(ProposalHold):
                merge.integrate("scout", 19, HEAD, BASE)

    def test_skip_marker_blocks_before_dispatch_or_merge(self):
        def original(method, path, payload=None):
            if path.endswith("/git/commits/" + HEAD):
                return {"parents": [{"sha": BASE}], "message": "chore: refresh technology intelligence [skip ci]"}
            self.assertEqual(method, "GET")
            return fake_authority_api(method, path, payload)
        with patch.object(merge, "gh", side_effect=original), self.assertRaisesRegex(ProposalHold, "suppresses"):
            merge.integrate("scout", 19, HEAD, BASE)

    def test_dispatch_wrong_pr_fork_stale_or_failed_native_run_never_merges(self):
        for change in ({"event": "workflow_dispatch"}, {"head_sha": BASE}, {"pull_requests": []},
                       {"head_repository": {"full_name": "other/fork"}}, {"conclusion": "failure"}):
            def provider(method, path, payload=None):
                self.assertEqual(method, "GET")
                if "runs?event=pull_request" in path:
                    return {"workflow_runs": [{**native_run(candidate_pr()), **change}]}
                return fake_authority_api(method, path, payload)
            with self.subTest(change=change), patch.object(merge, "gh", side_effect=provider), \
                 self.assertRaises(ProposalHold):
                merge.integrate("scout", 19, HEAD, BASE)

    def test_missing_native_gate_reports_action_and_never_writes(self):
        with patch.object(merge, "gh", return_value={"workflow_runs": []}) as gh, \
             patch.object(merge.time, "sleep"), self.assertRaisesRegex(ProposalHold, "lacks a pull_request"):
            merge.require_pr_gate(candidate_pr(), deadline=float("inf"))
        self.assertEqual({c.args[0] for c in gh.call_args_list}, {"GET"})

    def test_duplicate_release_job_never_qualifies(self):
        jobs = [{"name": name, "conclusion": "success"} for name in merge.REQUIRED_JOBS]
        self.assertFalse(merge.completed_release_jobs([*jobs, jobs[0]]))

    def test_provider_denial_only_exposes_fixed_diagnostics(self):
        reason = proposal.merge_denial('{"message":"Required status check release-gate is expected. PRIVATE"}',
                                       "gh: PRIVATE (HTTP 405)")
        self.assertIn("HTTP 405", reason)
        self.assertIn("release-gate", reason)
        self.assertNotIn("PRIVATE", reason)
        self.assertIn("unknown", proposal.merge_denial("private provider body", "private stderr"))

    def test_proposal_creation_requires_actual_pinned_single_parent(self):
        env = {"GITHUB_REPOSITORY": proposal.REPO,
               "GITHUB_EVENT_NAME": "schedule",
               "GITHUB_RUN_ID": "39603064849",
               "GITHUB_RUN_ATTEMPT": "1", "GH_TOKEN": "synthetic-placeholder"}
        def api(method, endpoint, payload=None):
            if endpoint.endswith("/branches/main"):
                return {"commit": {"sha": BASE}}
            if endpoint.endswith("/git/commits/" + HEAD):
                return {"parents": [{"sha": BASE}]}
            if "/compare/" in endpoint:
                return {"status": "ahead", "ahead_by": 1, "behind_by": 0,
                        "files": [{"filename": FILE, "status": "modified"}]}
            raise AssertionError(endpoint)
        with patch.dict("os.environ", env, clear=True), \
             patch.object(proposal, "gh", side_effect=api):
            verified = proposal.checked_proposal_state("scout", BRANCH, BASE, HEAD)
        self.assertEqual(verified.files, (FILE,))
        with patch.dict("os.environ", env, clear=True), \
             patch.object(proposal, "gh") as gh:
            with self.assertRaises(ProposalHold):
                proposal.checked_proposal_state(
                    "scout", "automation/retally-scout-9999999999-1", BASE, HEAD)
            gh.assert_not_called()

    def test_untrusted_manual_dispatch_cannot_invoke_bot_merge(self):
        env = {"GITHUB_REPOSITORY": proposal.REPO,
               "GITHUB_EVENT_NAME": "workflow_dispatch", "GITHUB_REF": "refs/heads/main",
               "GITHUB_ACTOR": "P00NSMASHER", "GH_TOKEN": "synthetic-placeholder"}
        with patch.dict("os.environ", env, clear=True), patch.object(merge, "gh") as gh:
            with self.assertRaises(ProposalHold):
                merge.main()
            gh.assert_not_called()

    def test_workflow_never_triggers_on_untrusted_pr_write_events(self):
        yaml = (Path(__file__).resolve().parents[1] /
                ".github/workflows/retally-generated-pr-merge.yml").read_text()
        self.assertIn("github.actor == 'github-actions[bot]'", yaml)
        self.assertIn("github.ref == 'refs/heads/main'", yaml)
        self.assertIn("workflow_dispatch:", yaml)
        self.assertNotIn("workflow_run:", yaml)
        self.assertNotIn("schedule:", yaml)
        self.assertIn("contents: write", yaml)
        self.assertIn("pull-requests: write", yaml)
        self.assertIn("checks: read", yaml)


if __name__ == "__main__":
    unittest.main()
