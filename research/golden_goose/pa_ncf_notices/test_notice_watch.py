import copy
import json
import unittest
from pathlib import Path
from notice_watch import SnapshotError, validate, summarize, diff_snapshots

BASE = json.loads((Path(__file__).parent / 'pa_snapshot_2026-10-28.json').read_text())


class SnapshotTests(unittest.TestCase):
    def test_live_transcription_counts_not_verified_chow(self):
        self.assertEqual(summarize(BASE)['total_public_rows'], 3)
        self.assertEqual(summarize(BASE)['initial_application_reviews'], 1)
        self.assertEqual(summarize(BASE)['ambiguous_initial_or_chow_decisions'], 2)
        self.assertEqual(summarize(BASE)['confirmed_pending_chow'], 0)

    def test_review_is_not_chow(self):
        self.assertEqual(summarize(BASE)['confirmed_completed_chow'], 0)

    def test_source_must_be_exact(self):
        s=copy.deepcopy(BASE); s['source_url']='https://example.com'
        with self.assertRaises(SnapshotError): validate(s)

    def test_duplicate_detected(self):
        s=copy.deepcopy(BASE); s['rows'].append(copy.deepcopy(s['rows'][0]))
        with self.assertRaises(SnapshotError): validate(s)

    def test_duplicate_case_insensitive(self):
        s=copy.deepcopy(BASE); r=copy.deepcopy(s['rows'][0]);r['name']='  CHANDLER  hall health services '
        s['rows'].append(r)
        with self.assertRaises(SnapshotError): validate(s)

    def test_illegal_category_status(self):
        s=copy.deepcopy(BASE); s['rows'][0]['status']='APPROVED'
        with self.assertRaises(SnapshotError): validate(s)

    def test_improper_chow_confirmation(self):
        s=copy.deepcopy(BASE); s['rows'][0]['chow_verified']=True
        with self.assertRaises(SnapshotError): validate(s)

    def test_future_posting(self):
        s=copy.deepcopy(BASE); s['rows'][0]['posted']='2026-11-01'
        with self.assertRaises(SnapshotError): validate(s)

    def test_bad_date(self):
        s=copy.deepcopy(BASE); s['rows'][0]['posted']='10/23/2026'
        with self.assertRaises(SnapshotError): validate(s)

    def test_missing_row_identity(self):
        s=copy.deepcopy(BASE); s['rows'][0].pop('address')
        with self.assertRaises(SnapshotError): validate(s)

    def test_no_changes_if_order_only_changed(self):
        old=copy.deepcopy(BASE); old['observed_on']='2026-10-27'
        new=copy.deepcopy(BASE); new['rows'].reverse()
        self.assertEqual(diff_snapshots(old,new)['changes'],[])

    def test_addition_detected_not_chow_verified(self):
        old=copy.deepcopy(BASE); old['observed_on']='2026-10-27'; old['rows']=old['rows'][:2]
        out=diff_snapshots(old,BASE)
        self.assertEqual(len(out['changes']),1)
        self.assertEqual(out['changes'][0]['type'],'ADDED')
        self.assertEqual(out['changes'][0]['chow_claim'],'UNVERIFIED')

    def test_disappearance_does_not_claim_denial(self):
        old=copy.deepcopy(BASE); old['observed_on']='2026-10-27'
        new=copy.deepcopy(BASE); new['rows']=new['rows'][:2]
        out=diff_snapshots(old,new)
        self.assertEqual(out['changes'][0]['type'],'NOT_ON_CURRENT_PAGE')
        self.assertEqual(out['confirmed_chow_count'],0)

    def test_changed_name_creates_unlinked_rows(self):
        old=copy.deepcopy(BASE); old['observed_on']='2026-10-27'
        new=copy.deepcopy(BASE); new['rows'][0]['name']='New entity name'
        out=diff_snapshots(old,new)
        self.assertEqual(sorted(x['type'] for x in out['changes']), ['ADDED','NOT_ON_CURRENT_PAGE'])

    def test_older_snapshot_rejected(self):
        old=copy.deepcopy(BASE)
        new=copy.deepcopy(BASE); new['observed_on']='2026-10-27'
        with self.assertRaises(SnapshotError): diff_snapshots(old,new)

    def test_same_date_rejected(self):
        with self.assertRaises(SnapshotError): diff_snapshots(BASE,BASE)

    def test_changed_status_visible_but_not_chow(self):
        old=copy.deepcopy(BASE); old['observed_on']='2026-10-27'
        new=copy.deepcopy(BASE); new['rows'][1]['status']='DENIED'
        out=diff_snapshots(old,new)
        self.assertEqual(out['changes'][0]['type'],'CHANGED')
        self.assertEqual(out['confirmed_chow_count'],0)


if __name__ == '__main__':
    unittest.main()
