"""Offline adversarial tests for source-qualified RETALLY incident alerts."""
from __future__ import annotations

import unittest
from unittest.mock import Mock

from freight.site.live_audit_incident import (
    TITLE, event_details, is_latest_trusted_run, process,
)


class IncidentEventTests(unittest.TestCase):
    def payload(
        self, *, conclusion="failure", event="schedule", branch="main",
        name="P00NSMASHER/github-value-hunt-ledger", run_id=5,
    ):
        return {
            "repository": {"full_name": name},
            "workflow_run": {
                "head_branch": branch,
                "event": event,
                "conclusion": conclusion,
                "id": run_id,
            },
        }

    def test_only_actual_main_trusted_workflow_completions_qualify(self):
        self.assertEqual(
            event_details(self.payload()),
            {"conclusion": "failure", "event": "schedule", "id": 5},
        )
        self.assertEqual(
            event_details(self.payload(conclusion="success"))["conclusion"],
            "success",
        )
        for kw in (
            {"event": "pull_request"}, {"branch": "other"},
            {"name": "attacker/repo"}, {"conclusion": "cancelled"},
            {"conclusion": "skipped"}, {"run_id": "5"}, {"run_id": -1},
        ):
            with self.subTest(kw=kw):
                self.assertIsNone(event_details(self.payload(**kw)))
        self.assertIsNone(event_details({"workflow_run": {}}))

    def test_newer_run_prevents_stale_alert(self):
        runs = [
            {"id": 100, "head_branch": "main", "event": "schedule",
             "status": "completed", "conclusion": "failure"},
            {"id": 101, "head_branch": "main", "event": "push",
             "status": "completed", "conclusion": "success"},
            {"id": 102, "head_branch": "main", "event": "schedule",
             "status": "completed", "conclusion": "cancelled"},
            {"id": 103, "head_branch": "main", "event": "schedule",
             "status": "in_progress", "conclusion": None},
        ]
        self.assertFalse(is_latest_trusted_run(100, runs))
        self.assertTrue(is_latest_trusted_run(101, runs))
        self.assertFalse(is_latest_trusted_run(102, runs))
        self.assertFalse(is_latest_trusted_run(101, []))

    def api(self, runs=None, issues=None, conclusion="failure"):
        mock = Mock()

        def route(method, path, data=None):
            if path.startswith("/actions/workflows/"):
                return {"workflow_runs": runs if runs is not None else [
                    {"id": 5, "head_branch": "main", "event": "schedule",
                     "status": "completed", "conclusion": conclusion},
                ]}
            if path.startswith("/issues?"):
                return issues if issues is not None else []
            if method == "GET" and path.startswith("/labels/"):
                return {"name": "existing"}
            if method == "POST" and path == "/issues":
                return {"number": 101}
            return {}

        mock.call.side_effect = route
        return mock

    def test_new_failure_creates_one_accurate_issue(self):
        api = self.api()
        self.assertEqual(
            process(api, {"id": 5, "conclusion": "failure", "event": "schedule"}),
            "LIVE_AUDIT_INCIDENT_OPENED",
        )
        new_issue = [
            c for c in api.call.call_args_list
            if c.args[:2] == ("POST", "/issues")
        ]
        self.assertEqual(len(new_issue), 1)
        self.assertEqual(new_issue[0].args[2]["title"], TITLE)
        self.assertIn("@P00NSMASHER", new_issue[0].args[2]["body"])
        self.assertIn(
            "does not prove customer-visible downtime",
            new_issue[0].args[2]["body"],
        )
        self.assertNotIn(
            "EdgeResponseStatus",
            new_issue[0].args[2]["body"],
        )

    def test_existing_failure_updates_not_duplicates(self):
        api = self.api(issues=[{"number": 9, "title": TITLE}])
        self.assertEqual(
            process(api, {"id": 5, "conclusion": "failure", "event": "schedule"}),
            "ACTIVE_INCIDENT_UPDATED",
        )
        paths = [x.args[1] for x in api.call.call_args_list]
        self.assertIn("/issues/9/comments", paths)
        self.assertNotIn("/issues", paths)

    def test_success_closes_only_matching_incidents(self):
        api = self.api(issues=[
            {"number": 9, "title": TITLE},
            {"number": 10, "title": "Other"},
        ], conclusion="success")
        self.assertEqual(
            process(api, {"id": 5, "conclusion": "success", "event": "schedule"}),
            "RECOVERY_EVIDENCED_AND_INCIDENT_CLOSED",
        )
        paths = [x.args[1] for x in api.call.call_args_list]
        self.assertIn("/issues/9", paths)
        self.assertNotIn("/issues/10", paths)
        self.assertEqual(
            process(self.api(conclusion="success"), {"id": 5, "conclusion": "success", "event": "schedule"}),
            "LIVE_AUDIT_PASSED_NO_OPEN_INCIDENT",
        )

    def test_stale_events_do_not_touch_issues(self):
        api = self.api(runs=[
            {"id": 6, "head_branch": "main", "event": "schedule",
             "status": "completed", "conclusion": "success"},
            {"id": 5, "head_branch": "main", "event": "schedule",
             "status": "completed", "conclusion": "failure"},
        ])
        self.assertEqual(
            process(api, {"id": 5, "conclusion": "failure", "event": "schedule"}),
            "STALE_RUN_IGNORED",
        )
        self.assertEqual(api.call.call_count, 1)

    def test_reject_mismatched_authoritative_conclusion(self):
        api = self.api(conclusion="success")
        with self.assertRaisesRegex(RuntimeError, "completion could not be verified"):
            process(api, {"id": 5, "conclusion": "failure", "event": "schedule"})
        self.assertEqual(api.call.call_count, 1)

    def test_cancelled_newer_run_does_not_hide_older_failure(self):
        api = self.api(runs=[
            {"id": 5, "head_branch": "main", "event": "schedule",
             "status": "completed", "conclusion": "failure"},
            {"id": 6, "head_branch": "main", "event": "push",
             "status": "completed", "conclusion": "cancelled"},
        ])
        self.assertEqual(
            process(api, {"id": 5, "conclusion": "failure", "event": "schedule"}),
            "LIVE_AUDIT_INCIDENT_OPENED",
        )

    def test_missing_run_confirmation_fails_closed(self):
        api = self.api(runs=[])
        with self.assertRaises(RuntimeError):
            process(api, {"id": 5, "conclusion": "success", "event": "schedule"})
        self.assertEqual(api.call.call_count, 1)


if __name__ == "__main__":
    unittest.main()
