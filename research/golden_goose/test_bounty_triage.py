import json
from pathlib import Path
import unittest
from decimal import Decimal
from bounty_triage import dollars, evaluate, issue_key


BASE = dict(listing_id='1', issue_url='https://github.com/example/thing/issues/5',
            advertised_usd='100.00', github_state='open', repo_archived=False,
            external_contributors_allowed=True, recent_awards_verified=True, claim_count=0)


def row(**kwargs):
    r = BASE.copy()
    r.update(kwargs)
    return r


class BountyTriageTests(unittest.TestCase):
    def test_valid_but_not_guaranteed(self):
        self.assertEqual(evaluate([row()])['issues'][0]['status'], 'REVIEW_READY_NOT_PAYMENT_GUARANTEE')

    def test_closed_dominates_platform_open(self):
        self.assertEqual(evaluate([row(github_state='closed')])['issues'][0]['status'], 'BLOCKED_CLOSED')

    def test_archived_dominates(self):
        self.assertEqual(evaluate([row(repo_archived=True)])['issues'][0]['status'], 'BLOCKED_ARCHIVED')

    def test_unknown_state_never_passes(self):
        self.assertEqual(evaluate([row(github_state=None)])['issues'][0]['status'], 'UNVERIFIED_STATE')

    def test_small_bounty_not_first_100(self):
        self.assertEqual(evaluate([row(advertised_usd='3')])['issues'][0]['status'], 'TOO_SMALL_FOR_FIRST_100')

    def test_restricted_contributors(self):
        self.assertEqual(evaluate([row(external_contributors_allowed=False)])['issues'][0]['status'], 'UNVERIFIED_EXTERNAL_ELIGIBILITY')

    def test_no_recent_award_evidence(self):
        self.assertEqual(evaluate([row(recent_awards_verified=None)])['issues'][0]['status'], 'UNVERIFIED_RECENT_PAYOUT')

    def test_high_competition(self):
        self.assertEqual(evaluate([row(claim_count=19)])['issues'][0]['status'], 'UNVERIFIED_OR_HIGH_COMPETITION')

    def test_group_multiple_awards_single_issue(self):
        report = evaluate([row(), row(listing_id='2', advertised_usd='25')])
        self.assertEqual(report['unique_issues'], 1)
        self.assertEqual(report['gross_advertised_usd'], '125.00')
        self.assertEqual(report['collectible_usd_verified'], '0.00')

    def test_conflict_in_group_fails_closed(self):
        report = evaluate([row(), row(listing_id='2', github_state='closed')])
        self.assertEqual(report['issues'][0]['status'], 'BLOCKED_CLOSED')

    def test_money_validation(self):
        for v in ['nan', 'Infinity', '-1', '3.111']:
            with self.assertRaises(ValueError):
                dollars(v)

    def test_url_validation(self):
        for u in ['http://github.com/x/y/issues/1', 'https://evil.com/x/y/issues/1', 'https://github.com/x/y/pull/1']:
            with self.assertRaises(ValueError):
                issue_key(u)

    def test_observed_census_regression(self):
        data = json.loads(Path(__file__).with_name('bounty_census_2026-10-28.json').read_text())
        report = evaluate(data)
        self.assertEqual(report['listings'], 10)
        self.assertEqual(report['unique_issues'], 6)
        self.assertEqual(report['gross_advertised_usd'], '450.00')
        self.assertEqual(report['review_ready_count'], 0)
        blocked = sum(Decimal(issue['advertised_usd']) for issue in report['issues'] if issue['status'] in ('BLOCKED_CLOSED', 'BLOCKED_ARCHIVED'))
        self.assertEqual(blocked, Decimal('417.00'))

    def test_open_assigned_bounties_are_not_claimable(self):
        """Open high-dollar issue != eligible first-$100 payout."""
        data = json.loads(Path(__file__).with_name(
            'tenstorrent_open_assigned_2026-10-28.json').read_text())
        report = evaluate(data)
        self.assertEqual(report['listings'], 3)
        self.assertEqual(report['unique_issues'], 3)
        self.assertEqual(report['gross_advertised_usd'], '6750.00')
        self.assertEqual(report['collectible_usd_verified'], '0.00')
        self.assertEqual(report['review_ready_count'], 0)
        self.assertTrue(all(r['status'] == 'UNVERIFIED_EXTERNAL_ELIGIBILITY'
                            for r in report['issues']))

    def test_duplicate_listing_id_rejected(self):
        with self.assertRaises(ValueError):
            evaluate([row(), row()])

    def test_missing_claims_is_not_zero_competition(self):
        self.assertEqual(evaluate([row(claim_count=None)])['issues'][0]['status'], 'UNVERIFIED_OR_HIGH_COMPETITION')


if __name__ == '__main__':
    unittest.main()
