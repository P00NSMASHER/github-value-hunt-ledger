"""Cross-board October 28 bounty-negative-control regression, no network or payout calls."""
from decimal import Decimal
import json
from pathlib import Path
import unittest
from bounty_triage import evaluate

SOURCE = Path(__file__).with_name("bounty_cross_board_2026-10-28.json")

class CrossBoardTests(unittest.TestCase):
    def test_four_source_linked_rows_produce_no_review_ready_bounties(self):
        rows = json.loads(SOURCE.read_text(encoding="utf-8"))
        report = evaluate(rows)
        self.assertEqual(report["listings"], 4)
        self.assertEqual(report["unique_issues"], 4)
        self.assertEqual(report["gross_advertised_usd"], "800.00")
        self.assertEqual(report["review_ready_count"], 0)
        self.assertEqual(report["collectible_usd_verified"], "0.00")
        actual = {v["issue_url"]: v["status"] for v in report["issues"]}
        self.assertEqual(actual["https://github.com/coollabsio/coolify/issues/2378"],
                         "BLOCKED_EXTERNAL_RESTRICTION")
        self.assertEqual(actual["https://github.com/revertinc/revert/issues/372"],
                         "UNVERIFIED_EXTERNAL_ELIGIBILITY")
        self.assertEqual(actual["https://github.com/javelin-anticheat/py-workedtask/issues/4"],
                         "UNVERIFIED_EXTERNAL_ELIGIBILITY")
        self.assertEqual(actual["https://github.com/gyroflow/gyroflow/issues/742"],
                         "UNVERIFIED_EXTERNAL_ELIGIBILITY")

    def test_competition_still_blocks_if_external_eligibility_proved(self):
        """Grant hypothetical outside eligibility; competing attempts still prevent promotion."""
        rows = json.loads(SOURCE.read_text(encoding="utf-8"))
        for r in rows:
            if r["issue_url"].endswith(("/issues/4", "/issues/742")):
                r.update(external_contributors_allowed=True, assignment_required=False, recent_awards_verified=True)
        report = evaluate(rows)
        by_url = {v["issue_url"]: v for v in report["issues"]}
        for key in ["https://github.com/javelin-anticheat/py-workedtask/issues/4",
                    "https://github.com/gyroflow/gyroflow/issues/742"]:
            self.assertEqual(by_url[key]["status"], "UNVERIFIED_OR_HIGH_COMPETITION")
        self.assertEqual(report["review_ready_count"], 0)

    def test_missing_assignee_policy_cannot_be_treated_as_verified(self):
        rows = json.loads(SOURCE.read_text(encoding="utf-8"))
        for r in rows:
            if r["issue_url"].endswith("/issues/372"):
                r.update(external_contributors_allowed=True, assignment_required=False, recent_awards_verified=True, claim_count=0)
        report = evaluate(rows)
        by_url = {v["issue_url"]: v for v in report["issues"]}
        self.assertEqual(by_url["https://github.com/revertinc/revert/issues/372"]["status"], "BLOCKED_ASSIGNED_TO_OTHER")

    def test_source_links_and_nonzero_rewards_are_present(self):
        rows = json.loads(SOURCE.read_text(encoding="utf-8"))
        self.assertTrue(all(r["primary_url"] == r["issue_url"] and r["listing_url"].startswith("https://") for r in rows))
        self.assertEqual(sum((Decimal(r["advertised_usd"]) for r in rows), Decimal("0")), Decimal("800.00"))

if __name__ == "__main__":
    unittest.main()
