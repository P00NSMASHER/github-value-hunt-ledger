"""Offline regression tests for immutable RETALLY campaign versus current queue."""
import json
import subprocess
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from queue_preflight import compare, render
from social_review import parse_timestamp

NOW = parse_timestamp('2026-10-11T15:00:00Z')


def record(uid, *, network='facebook', draft=False,
           when='2026-10-12T15:00:00'):
    return {
        'uuid': uid, 'providers': [{'network': network, 'status': 'PENDING'}],
        'publicationDate': {'dateTime': when, 'timezone': 'Europe/Madrid'},
        'draft': draft, 'autoPublish': not draft,
        'text': ('Review at https://www.retallyrecovery.com/freight-audit-methodology'
                 '?utm_source=facebook&utm_medium=organic_social'
                 '&utm_campaign=retally_oct2026_launch&utm_content=example'
                 if network == 'facebook' else 'Learn more via the link in our bio.'),
        'media': ['https://static.metricool.com/one.png'],
        'mediaAltText': ['RETALLY informative graphic'],
        network + 'Data': {'type': 'POST'},
    }


class QueuePreflightTests(unittest.TestCase):
    def setUp(self):
        self.initial = {'data': [record('fb-a'), record('ig-d', network='instagram',
                                                     draft=True, when='2026-11-03T16:00:00')]}
        self.latest = deepcopy(self.initial)

    def inspect(self, *, at=NOW):
        return compare(self.initial, self.latest, as_of=at)

    def codes(self):
        return [x['code'] for x in self.inspect()['events']]

    def test_unchanged_queue_clean_and_preserves_draft(self):
        r = self.inspect()
        self.assertEqual(r['preflight_state'], 'NO_HIGH_RISK_DRIFT_DETECTED')
        self.assertEqual(r['severity_counts'], {'HIGH': 0, 'WARN': 0, 'INFO': 0})
        self.assertEqual((r['current_active'], r['current_drafts']), (1, 1))
        self.assertEqual(r['publication_verification'], 'NOT_CHECKED')
        self.assertIn('read-only', render(r).lower())

    def test_numeric_post_id_is_intentionally_ignored(self):
        self.latest['data'][0]['id'] = '999999'
        self.latest['data'][0]['creatorUserMail'] = 'should-not-appear@example.com'
        self.assertFalse(self.inspect()['events'])

    def test_an_additional_draft_is_info_not_approval(self):
        self.latest['data'].append(record('ig-new', network='instagram', draft=True))
        r = self.inspect()
        self.assertEqual(r['severity_counts'], {'HIGH': 0, 'WARN': 0, 'INFO': 1})
        self.assertIn('ADDED_REVIEW_DRAFT', self.codes())
        self.assertEqual(r['current_drafts'], 2)

    def test_an_unapproved_new_active_post_is_high(self):
        self.latest['data'].append(record('fb-new'))
        self.assertIn('NEW_ACTIVE_POST', self.codes())
        self.assertEqual(self.inspect()['preflight_state'], 'REVIEW_HIGH_RISK_DRIFT')

    def test_auto_publish_off_is_high_risk(self):
        self.latest['data'][0]['autoPublish'] = False
        self.assertIn('AUTO_PUBLISH_FLAG_CHANGED', self.codes())
        self.assertIn('ACTIVE_AUTO_PUBLISH_OFF', self.codes())

    def test_draft_flag_change_cannot_silently_publish(self):
        self.latest['data'][1]['draft'] = False
        self.latest['data'][1]['autoPublish'] = True
        self.assertIn('DRAFT_FLAG_CHANGED', self.codes())
        self.assertIn('AUTO_PUBLISH_FLAG_CHANGED', self.codes())

    def test_draft_with_auto_publish_is_high_even_if_preexisting(self):
        self.initial['data'][1]['autoPublish'] = True
        self.latest = deepcopy(self.initial)
        self.assertIn('DRAFT_AUTO_PUBLISH_ON', self.codes())

    def test_schedule_instant_change_and_cadence(self):
        self.latest['data'][0]['publicationDate']['dateTime'] = '2026-10-12T16:00:00'
        self.assertIn('SCHEDULE_INSTANT_CHANGED', self.codes())
        self.assertIn('POSTING_TIME_OUTSIDE_CADENCE', self.codes())

    def test_equivalent_utc_time_with_different_iana_timezone(self):
        self.latest['data'][0]['publicationDate'] = {
            'dateTime': '2026-10-12T14:00:00', 'timezone': 'Europe/London'}
        self.assertNotIn('SCHEDULE_INSTANT_CHANGED', self.codes())
        self.assertEqual(self.inspect()['severity_counts']['HIGH'], 0)

    def test_october_dst_preserves_eastern_nine_am(self):
        self.initial = {'data': [record('fb-late', when='2026-10-26T14:00:00')]}
        self.latest = deepcopy(self.initial)
        self.assertEqual(self.inspect()['severity_counts']['HIGH'], 0)

    def test_rehosted_media_and_caption_are_signaled(self):
        self.latest['data'][0]['media'] = ['https://static.metricool.com/new.png']
        self.latest['data'][0]['text'] += '\nUpdated.'
        self.assertIn('MEDIA_CHANGED', self.codes())
        self.assertIn('CAPTION_CHANGED', self.codes())

    def test_broken_destination_is_high(self):
        self.latest['data'][0]['text'] = 'No campaign link'
        self.assertIn('FACEBOOK_LINK_NOT_TRACKED', self.codes())

    def test_alt_text_drift_and_missing_accessibility(self):
        self.latest['data'][0]['mediaAltText'] = ['']
        self.assertIn('ALT_TEXT_CHANGED', self.codes())
        self.assertIn('ALT_TEXT_MISSING_OR_MISMATCHED', self.codes())

    def test_format_reel_change_high(self):
        self.latest['data'][0]['facebookData'] = {'type': 'REEL'}
        self.assertIn('FORMAT_CHANGED', self.codes())
        self.assertIn('POST_FORMAT_CHANGED', self.codes())

    def test_provider_fail_state_is_not_success(self):
        self.latest['data'][0]['providers'][0]['status'] = 'FAILED'
        self.assertIn('PROVIDER_ERROR_STATE', self.codes())

    def test_before_due_missing_is_not_mistaken_for_published(self):
        self.latest['data'] = [self.latest['data'][1]]
        r = self.inspect()
        self.assertIn('UPCOMING_POST_NO_LONGER_IN_FEED', [x['code'] for x in r['events']])
        self.assertEqual(r['publication_verification'], 'NOT_CHECKED')
        self.assertEqual(r['severity_counts']['HIGH'], 1)

    def test_after_due_disappearance_remains_unverified(self):
        self.latest['data'] = [self.latest['data'][1]]
        late = parse_timestamp('2026-10-13T17:00:00Z')
        r = self.inspect(at=late)
        self.assertIn('DUE_POST_NO_LONGER_IN_FEED', [x['code'] for x in r['events']])
        self.assertEqual(r['severity_counts']['HIGH'], 0)
        self.assertEqual(r['publication_verification'], 'NOT_CHECKED')

    def test_draft_disappearance_is_review_not_publication(self):
        self.latest['data'] = [self.latest['data'][0]]
        self.assertIn('DRAFT_NO_LONGER_IN_FEED', self.codes())
        self.assertEqual(self.inspect()['severity_counts']['HIGH'], 0)

    def test_cross_platform_uuid_mutation_rejected_as_change(self):
        self.latest['data'][0] = record('fb-a', network='instagram')
        self.assertIn('NETWORK_CHANGED', self.codes())

    def test_duplicate_uuid_fails_closed(self):
        self.latest['data'].append(deepcopy(self.latest['data'][0]))
        with self.assertRaises(ValueError):
            self.inspect()

    def test_ambiguous_multi_provider_fails_closed(self):
        self.latest['data'][0]['providers'].append({'network': 'instagram'})
        with self.assertRaises(ValueError):
            self.inspect()

    def test_empty_snapshot_not_reported_as_safe(self):
        with self.assertRaises(ValueError):
            compare(self.initial, {'data': []}, as_of=NOW)

    def test_bad_boolean_and_unknown_time_rejected(self):
        self.latest['data'][0]['autoPublish'] = 'false'
        with self.assertRaises(ValueError):
            self.inspect()
        self.latest = deepcopy(self.initial)
        self.latest['data'][0]['publicationDate']['timezone'] = 'Invalid/Region'
        with self.assertRaises(Exception):
            self.inspect()

    def test_malicious_text_not_echoed_into_markdown(self):
        self.latest['data'][0]['text'] = 'secret-name, account 123456'
        r = render(self.inspect())
        self.assertNotIn('123456', r)

    def test_cli_exit_two_only_when_risk_and_explicit(self):
        script = Path(__file__).with_name('queue_preflight.py')
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            baseline, current = root/'base.json', root/'current.json'
            baseline.write_text(json.dumps(self.initial), encoding='utf-8')
            current.write_text(json.dumps(self.latest), encoding='utf-8')
            cmd = [sys.executable, str(script), '--baseline', str(baseline),
                   '--current', str(current), '--as-of', '2026-10-11T15:00:00Z',
                   '--json-output', str(root/'out.json'), '--fail-on-risk']
            good = subprocess.run(cmd, text=True, capture_output=True)
            self.assertEqual(good.returncode, 0, good.stderr)
            self.latest['data'][0]['autoPublish'] = False
            current.write_text(json.dumps(self.latest), encoding='utf-8')
            bad = subprocess.run(cmd, text=True, capture_output=True)
            self.assertEqual(bad.returncode, 2, bad.stderr)
            summary = json.loads((root/'out.json').read_text(encoding='utf-8'))
            self.assertEqual(summary['preflight_state'], 'REVIEW_HIGH_RISK_DRIFT')


if __name__ == '__main__':
    unittest.main()
