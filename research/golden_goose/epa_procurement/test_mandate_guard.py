"""Twenty independent variations of synthetic bad leads plus official Akron fixture."""
import copy
import json
import unittest
from pathlib import Path
from mandate_guard import review

F = json.loads(Path(__file__).with_name('akron_2026_amendment.json').read_text())
E = F['event']
ID = F['project_id']
ASOF = F['as_of']

class MandateGuardTests(unittest.TestCase):
    def test_official_akron_pending_not_final(self):
        self.assertEqual(review(ID, ASOF, [E]), ('REVIEW','pending_scope_replacement_not_court_final'))

    def test_another_project_cannot_modify_this_one(self):
        other = {**E, 'project_id':'another_city_other_facility'}
        self.assertEqual(review(ID, ASOF, [other]), ('REVIEW','no_complete_current_mandate_and_bid_authority'))

    def test_late_observation_not_injected_into_earlier_replay(self):
        self.assertEqual(review(ID, '2026-10-13', [E]), ('REVIEW','no_complete_current_mandate_and_bid_authority'))

    def test_terminal_historical_bid_is_not_a_live_lead(self):
        self.assertEqual(review(ID, ASOF, [], bid_status='CLOSED'), ('NOT_ACTIONABLE','tender_not_open'))

    def test_third_party_prices_do_not_become_revenue(self):
        self.assertEqual(F['verified_owner_revenue_usd'],0)
        self.assertFalse(F['verified_open_bid'])

    def test_frozen_doj_set_is_exactly_five(self):
        snap=json.loads(Path(__file__).with_name('doj_snapshot_2026-10-29.json').read_text())
        self.assertEqual(len(snap['entries']),5)
        self.assertEqual(len({row['url'] for row in snap['entries']}),5)
        self.assertEqual(snap['verified_new_actionable_municipal_wastewater_bids'],0)

    def test_twenty_distinct_adversarial_scenarios_fail_closed(self):
        scenarios=[]
        def add(label, change, expected):
            e=copy.deepcopy(E)
            change(e)
            scenarios.append((label,e,expected))
        add('spoof_subdomain',lambda e:e.update(source_url='https://www.govinfo.gov.attacker.example/content/pkg/FR-2026-10-14/html/2026-21003.htm'),'unverified_project_change')
        add('notices_index',lambda e:e.update(source_url='https://www.govinfo.gov/'),'unverified_project_change')
        add('query_string',lambda e:e.update(source_url=e['source_url']+'?replace=1'),'unverified_project_change')
        add('fragment',lambda e:e.update(source_url=e['source_url']+'#history'),'unverified_project_change')
        add('http_only',lambda e:e.update(source_url=e['source_url'].replace('https:', 'http:')),'unverified_project_change')
        add('user_info',lambda e:e.update(source_url=e['source_url'].replace('www.govinfo.gov','foo@www.govinfo.gov')),'unverified_project_change')
        add('bad_doc_path',lambda e:e.update(source_url='https://www.govinfo.gov/file.pdf'),'unverified_project_change')
        add('date_conflict',lambda e:e.update(published_on='2026-10-15'),'unverified_project_change')
        add('bad_date',lambda e:e.update(published_on='2026-02-31'),'undated_project_event')
        add('missing_date',lambda e:e.pop('observed_on'),'undated_project_event')
        add('observation_before_publication',lambda e:e.update(observed_on='2026-10-13'),'unverified_project_change')
        add('wrong_source_kind',lambda e:e.update(source_kind='blog_post'),'unverified_project_change')
        add('unknown_event_kind',lambda e:e.update(kind='new_$300m_award'),'unverified_project_change')
        add('proposed_fake_final',lambda e:e.update(kind='reported_final_replacement'),'finality_must_be_verified_from_court_order')
        add('claimed_completion',lambda e:e.update(kind='reported_completion'),'completion_must_be_independently_verified')
        add('claimed_reinstatement',lambda e:e.update(kind='reinstatement'),'reinstatement_requires_new_authority')
        add('no_title_required_but_source_not_authenticated',lambda e:e.update(extra_freeform='anyone can type this'),'pending_scope_replacement_not_court_final')
        add('observed_after_snapshot_ignore',lambda e:e.update(observed_on='2026-10-30'),'no_complete_current_mandate_and_bid_authority')
        add('missing_observed_url',lambda e:e.update(source_url=None),'unverified_project_change')
        add('cross_project_wrong_document',lambda e:e.update(project_id='akron_ehrt_facility',source_url='https://www.govinfo.gov/content/pkg/FR-2026-10-14/html/2026-00000.htm'),'pending_scope_replacement_not_court_final')
        # The last case exposes a residual limitation: government-shaped URL syntax
        # alone cannot authenticate page content. None of these outputs is green.
        self.assertEqual(len(scenarios),20)
        for label,event,reason in scenarios:
            with self.subTest(label=label):
                status,why=review(ID,ASOF,[event])
                self.assertIn(status,{'REVIEW','NOT_ACTIONABLE'})
                self.assertEqual(why,reason)

    def test_duplicate_conflicting_same_day_review(self):
        other={**E,'kind':'reported_completion'}
        self.assertEqual(review(ID,ASOF,[E,other]),('REVIEW','conflicting_project_changes'))

    def test_open_bid_without_verified_currentness_still_not_positive(self):
        self.assertEqual(review(ID,ASOF,[],bid_status='OPEN',bid_due='2026-12-01'), ('REVIEW','no_complete_current_mandate_and_bid_authority'))

    def test_deadline_today_expired(self):
        self.assertEqual(review(ID,ASOF,[],bid_status='OPEN',bid_due=ASOF), ('NOT_ACTIONABLE','bid_deadline_passed'))

    def test_no_valid_date_is_not_positive(self):
        self.assertEqual(review(ID,'2026-02-31',[E]),('REVIEW','bad_review_input'))

    def test_missing_deadline_is_review(self):
        self.assertEqual(review(ID,ASOF,[],bid_status='OPEN'),('REVIEW','missing_issuer_verified_deadline'))

    def test_nonlist_fails_closed(self):
        self.assertEqual(review(ID,ASOF,{}),('REVIEW','bad_review_input'))

if __name__ == '__main__':
    unittest.main()
