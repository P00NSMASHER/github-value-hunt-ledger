"""Deterministic, offline tests for RETALLY's read-only social verifier."""
import unittest

from social_review import markdown, parse_timestamp, review, scheduled_datetime


def post(uuid, network='facebook', date='2026-10-12T15:00:00', draft=False, auto=True, status='PENDING'):
    return {
        'uuid': uuid, 'providers': [{'network': network, 'status': status}],
        'publicationDate': {'dateTime': date, 'timezone': 'Europe/Madrid'},
        'draft': draft, 'autoPublish': auto,
        'media': ['https://example.com/img.png'], 'mediaAltText': ['Graphic title and content'],
        'text': 'See https://www.retallyrecovery.com/?utm_source=facebook for details.' if network == 'facebook'
           else 'Explore the link in our bio for details.'
    }


class SocialReviewTests(unittest.TestCase):
    def setUp(self):
        self.at = parse_timestamp('2026-10-11T11:00:00-04:00')

    def test_madrid_to_eastern_daylight_transition(self):
        for local, target in (
            ('2026-10-12T15:00:00', '09:00 AM EDT'),
            ('2026-10-26T14:00:00', '09:00 AM EDT'),
            ('2026-11-02T15:00:00', '09:00 AM EST'),
        ):
            x = post('u', date=local)
            got = review({'data':[x]}, {}, {}, as_of=self.at)['posts'][0]
            self.assertIn(target, got['date_et'])
            self.assertNotIn('Eastern publication hour', ''.join(got['warnings']))

    def test_pending_not_public_or_failure(self):
        x = post('f1')
        future = review({'data': [x]}, {}, {}, as_of=self.at)
        self.assertEqual(future['counts']['UPCOMING_NOT_YET_PUBLIC'], 1)
        later = review({'data':[x]}, {}, {},as_of=parse_timestamp('2026-10-13T12:00:00-04:00'))
        self.assertEqual(later['posts'][0]['status'], 'PUBLICATION_UNVERIFIED')

    def test_human_receipt_is_required_and_validated(self):
        x = post('f1')
        as_of = parse_timestamp('2026-10-13T12:00:00-04:00')
        doc = {'verified_publications':[{'uuid':'f1','network':'facebook',
            'permalink':'https://www.facebook.com/Retally/posts/12345',
            'verified_at':'2026-10-12T10:30:00-04:00'}]}
        result = review({'data':[x]},doc,{},as_of=as_of)
        self.assertEqual(result['counts']['VERIFIED_PUBLIC'],1)
        doc['verified_publications'][0]['network'] = 'instagram'
        with self.assertRaises(ValueError):
            review({'data':[x]},doc,{},as_of=as_of)

    def test_draft_cannot_be_mistaken_for_autopublished(self):
        x = post('d1', network='instagram', draft=True, auto=False)
        result = review({'data':[x]}, {}, {}, as_of=parse_timestamp('2026-10-13T12:00:00-04:00'))
        self.assertEqual(result['counts']['DRAFT'],1)
        self.assertFalse(result['posts'][0]['warnings'])

    def test_unknown_metrics_are_not_zero(self):
        x = post('f1')
        data = review({'data':[x]}, {}, {'posts':[{'uuid':'f1','reach':5, 'reactions':0}]},as_of=self.at)
        self.assertIsNone(data['posts'][0]['interactions'])
        self.assertIsNone(data['posts'][0]['interaction_rate'])

    def test_complete_measured_post_and_sample_caution(self):
        x = post('f1')
        when = parse_timestamp('2026-10-13T12:00:00-04:00')
        receipts = {'verified_publications':[{'uuid':'f1','network':'facebook',
                  'permalink':'https://www.facebook.com/Retally/posts/12345',
                  'verified_at':'2026-10-12T12:00:00-04:00'}]}
        metrics = {'posts':[{'uuid':'f1','reach':120,'impressions':140,'reactions':6,
                    'comments':2,'shares':1,'clicks':3}]}
        result=review({'data':[x]},receipts,metrics,as_of=when)
        self.assertEqual(result['posts'][0]['interactions'],12)
        self.assertEqual(result['posts'][0]['interaction_rate'],.1)
        self.assertFalse(result['by_network']['facebook']['can_prioritize_content_by_results'])
        self.assertIn('Evidence limitations',markdown(result))

    def test_fail_closed_on_future_receipt_or_unknown_uuid(self):
        x = post('f1')
        future={'verified_publications':[{'uuid':'f1','network':'facebook',
              'permalink':'https://www.facebook.com/Retally/posts/12345',
              'verified_at':'2026-10-12T12:00:00-04:00'}]}
        with self.assertRaises(ValueError):
            review({'data':[x]},future,{},as_of=self.at)
        with self.assertRaises(ValueError):
            review({'data':[x]}, {}, {'posts':[{'uuid':'wrong','reach':0}]},as_of=self.at)

    def test_bad_schema_and_tracking_warnings(self):
        with self.assertRaises(ValueError):
            review({}, {}, {}, as_of=self.at)
        x=post('f1');x['mediaAltText']=[];x['text']='Hello!'
        r=review({'data':[x]}, {}, {}, as_of=self.at)
        self.assertEqual(len(r['posts'][0]['warnings']),2)

    def test_invalid_metric_negative(self):
        with self.assertRaises(ValueError):
            review({'data':[post('f1')]},{},{'posts':[{'uuid':'f1','reach':-1}]},as_of=self.at)

    def test_dst_gap_rejected(self):
        with self.assertRaises(ValueError):
            scheduled_datetime(post('x',date='2026-03-29T02:30:00'))

    def test_no_timezone_assumptions(self):
        with self.assertRaises(ValueError):
            parse_timestamp('2026-10-11T12:00:00')


if __name__ == '__main__':
    unittest.main()
