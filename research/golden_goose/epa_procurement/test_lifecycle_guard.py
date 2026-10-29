"""Safety checks for one manually pinned, official EPA lifecycle receipt."""
import copy
import json
from pathlib import Path
import unittest
from lifecycle_guard import screen, PORT_CLINTON_PROJECT

FIXTURE = json.loads(Path(__file__).with_name('port_clinton_2026_lifecycle.json').read_text())
BASE = FIXTURE['event']
AS_OF = FIXTURE['as_of']
ID = PORT_CLINTON_PROJECT


class LifecycleGuardTests(unittest.TestCase):
    def test_official_agency_completion_suppresses_old_project_not_entire_city(self):
        self.assertEqual(screen(ID, AS_OF, [BASE]), tuple(FIXTURE['expected_screen']))
        self.assertEqual(screen('port_clinton_new_wwtp_upgrade', AS_OF, [BASE]),
                         ('REVIEW', 'no_verified_current_lifecycle_evidence'))

    def test_not_court_finality_or_money(self):
        self.assertFalse(FIXTURE['facts']['independent_court_termination_order_verified'])
        self.assertFalse(FIXTURE['facts']['verified_current_open_bid_for_original_project'])
        self.assertEqual(FIXTURE['economics']['verified_user_revenue_usd'], 0)
        self.assertEqual(FIXTURE['economics']['verified_customer_count'], 0)
        self.assertEqual(FIXTURE['economics']['customer_willingness_to_pay'], 'UNKNOWN')

    def test_observation_is_not_backdated(self):
        self.assertEqual(screen(ID, '2026-10-28', [BASE]),
                         ('REVIEW', 'no_verified_current_lifecycle_evidence'))

    def test_bad_inputs_fail_closed(self):
        for case in [('', AS_OF, [BASE]), (ID, '2026-02-30', [BASE]),
                     (ID, AS_OF, None), (ID, AS_OF, [None]),
                     (None, AS_OF, [BASE])]:
            with self.subTest(case=str(case)[:40]):
                self.assertNotEqual(screen(*case)[0], 'PAUSE_PRE_RFP')

    def test_duplicate_not_green(self):
        self.assertEqual(screen(ID, AS_OF, [BASE, BASE]),
                         ('REVIEW', 'duplicate_or_conflicting_lifecycle_evidence'))

    def test_missing_source_not_green(self):
        self.assertEqual(screen(ID, AS_OF, []),
                         ('REVIEW', 'no_verified_current_lifecycle_evidence'))

    def test_tampered_receipts_do_not_suppress_true_unknown_projects(self):
        variations = {
            'fake_host': ('source_url', 'https://www.epa.gov.attacker.example/newsreleases/fake'),
            'homepage': ('source_url', 'https://www.epa.gov/'),
            'query_poison': ('source_url', BASE['source_url'] + '?fake=true'),
            'wrong_report_date': ('published_on', '2026-05-30'),
            'future_report_date': ('published_on', '2026-12-01'),
            'wrong_project': ('project_id', 'port_clinton_other_project'),
            'wrong_kind': ('source_kind', 'vendor_blog'),
            'wrong_state': ('reported_state', 'funding_approved_for_new_project'),
            'unknown_receipt_id': ('receipt_id', 'epa_other_completion'),
            'http': ('source_url', BASE['source_url'].replace('https:', 'http:')),
            'trailing_path': ('source_url', BASE['source_url'] + '/'),
            'fragment': ('source_url', BASE['source_url'] + '#fake'),
            'empty_receipt_id': ('receipt_id', ''),
            'wrong_provenance': ('source_url', 'https://www.justice.gov/'),
            'malformed_date': ('published_on', '2026-02-31'),
            'missing_date': ('observed_on', None),
            'prepublication_observation': ('observed_on', '2026-05-31'),
            'wrong_observation_type': ('observed_on', 20261029),
        }
        self.assertEqual(len(variations), 18)
        for label, (key, val) in variations.items():
            with self.subTest(label=label):
                event = copy.deepcopy(BASE)
                event[key] = val
                self.assertNotEqual(screen(ID, AS_OF, [event])[0], 'PAUSE_PRE_RFP')

    def test_earlier_asof_even_when_event_eventually_known(self):
        self.assertEqual(screen(ID, '2026-06-02', [BASE]),
                         ('REVIEW', 'no_verified_current_lifecycle_evidence'))

    def test_fixture_only_one_case_not_market_rate(self):
        self.assertEqual(FIXTURE['case_id'], 'port-clinton-1999-cwa-consent-decree')
        self.assertTrue(FIXTURE['facts']['epa_reports_required_construction_complete'])


if __name__ == '__main__':
    unittest.main()
