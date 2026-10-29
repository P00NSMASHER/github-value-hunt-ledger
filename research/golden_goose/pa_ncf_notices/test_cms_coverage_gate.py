import copy
import json
import unittest
from pathlib import Path
from cms_coverage_gate import audit, EvidenceError

HERE = Path(__file__).parent
PA = json.loads((HERE / 'pa_snapshot_2026-10-28.json').read_text())
CMS = json.loads((HERE / 'cms_q2_2026_catalog_metadata.json').read_text())


class CoverageTests(unittest.TestCase):
    def test_three_real_notice_dates_beyond_cms_quarter(self):
        result = audit(PA, CMS)
        self.assertEqual(result['pa_rows_observed'], 3)
        self.assertEqual(result['pa_postings_after_cms_coverage_end'], 3)
        self.assertEqual(result['pa_postings_on_or_before_cms_coverage_end'], 0)

    def test_no_matched_events_and_no_lead_time_claim(self):
        result = audit(PA, CMS)
        self.assertEqual(result['independently_confirmed_same_event_matches'], 0)
        self.assertIsNone(result['measured_first_observation_lead_days'])
        self.assertEqual(result['commercial_status'], 'UNVALIDATED')
        self.assertEqual(result['claimable_revenue_usd'], 0)

    def test_mixed_approved_not_chow(self):
        result = audit(PA, CMS)
        self.assertEqual(result['mixed_initial_or_chow_decision_count'], 2)
        self.assertEqual(result['independently_confirmed_chow_count'], 0)

    def test_source_spoof_fails(self):
        x=copy.deepcopy(PA); x['source_url']='https://example.org'
        with self.assertRaises(EvidenceError): audit(x,CMS)

    def test_cms_source_spoof_fails(self):
        x=copy.deepcopy(CMS); x['source_url']='https://example.org'
        with self.assertRaises(EvidenceError): audit(PA,x)

    def test_cms_dataset_identity_mismatch_fails(self):
        x=copy.deepcopy(CMS); x['dataset_id']='different'
        with self.assertRaises(EvidenceError): audit(PA,x)

    def test_cms_update_before_quarter_end_fails(self):
        x=copy.deepcopy(CMS); x['catalog_last_updated_on']='2026-05-01'
        with self.assertRaises(EvidenceError): audit(PA,x)

    def test_claimed_verified_chow_fails(self):
        x=copy.deepcopy(PA); x['rows'][1]['chow_verified']=True
        with self.assertRaises(EvidenceError): audit(x,CMS)

    def test_claimed_cms_match_fails(self):
        x=copy.deepcopy(PA); x['rows'][1]['matched_cms_event']='ABC'
        with self.assertRaises(EvidenceError): audit(x,CMS)

    def test_future_portal_post_fails(self):
        x=copy.deepcopy(PA); x['rows'][0]['posted']='2026-11-01'
        with self.assertRaises(EvidenceError): audit(x,CMS)

    def test_duplicate_identity_fails(self):
        x=copy.deepcopy(PA); x['rows'].append(copy.deepcopy(x['rows'][0]))
        with self.assertRaises(EvidenceError): audit(x,CMS)

    def test_strict_bad_iso_date_fails(self):
        x=copy.deepcopy(PA); x['rows'][0]['posted']='10/23/2026'
        with self.assertRaises(EvidenceError): audit(x,CMS)

    def test_unknown_category_fails(self):
        x=copy.deepcopy(PA); x['rows'][0]['category']='CONFIRMED_CHOW'
        with self.assertRaises(EvidenceError): audit(x,CMS)

    def test_invalid_status_fails(self):
        x=copy.deepcopy(PA); x['rows'][0]['status']='APPROVED'
        with self.assertRaises(EvidenceError): audit(x,CMS)

    def test_older_date_screen_not_misrepresented_as_match(self):
        x=copy.deepcopy(PA); x['rows'][0]['posted']='2026-05-28'
        result=audit(x,CMS)
        self.assertEqual(result['pa_postings_on_or_before_cms_coverage_end'],1)
        self.assertEqual(result['independently_confirmed_same_event_matches'],0)
        self.assertIsNone(result['measured_first_observation_lead_days'])


if __name__=='__main__':
    unittest.main()
