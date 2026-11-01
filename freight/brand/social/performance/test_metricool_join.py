"""Independent, network-free adversarial checks of Metricool publication evidence joins."""
import copy
import unittest

from metricool_join import SPEC, _metric, _public_post_url, join
from social_review import parse_timestamp


def post(uid='test-fb', network='facebook', draft=False, caption='SYNTHETIC freight fee checklist'):
    return dict(uuid=uid, providers=[dict(network=network, status='PENDING')],
                publicationDate=dict(dateTime='2026-10-12T15:00:00' if network=='facebook'
                                     else '2026-10-13T16:00:00', timezone='Europe/Madrid'),
                draft=draft, autoPublish=not draft,
                text=caption, media=['https://example.org/fictional.png'],
                mediaAltText=['Synthetic illustration'])


def export(network='facebook', date=None, caption='SYNTHETIC freight fee checklist',
           url=None, **metrics):
    spec=SPEC[network]
    fields=[spec['date'],spec['caption'],spec['url'],*spec['metrics'].values()]
    fields=list(dict.fromkeys(fields))
    values={spec['date']:date or ('20261012' if network=='facebook' else '20261013'),
            spec['caption']:caption,
            spec['url']:url or ('https://facebook.com/retally/posts/12345' if network=='facebook'
                                else 'https://www.instagram.com/p/AbCd123-/')}
    for name, field in spec['metrics'].items():
        if name in metrics: values[field]=str(metrics[name]) if metrics[name] is not None else None
    return dict(field_ids=fields, observed_at='2026-10-13T17:00:00-04:00',
                rows=[[values.get(f) for f in fields]])


class MetricoolJoinTests(unittest.TestCase):
    def setUp(self):
        self.now=parse_timestamp('2026-10-13T18:00:00-04:00')
        self.base=post()
        self.feed=export(reach='120.0',impressions=150,reactions=5,comments=2,shares=1,clicks=3)

    def check(self, source=None, base=None, receipts=None, as_of=None):
        return join({'data':[self.base] if base is None else base},
                    {'facebook':self.feed} if source is None else source,
                    receipts or {},as_of=as_of or self.now)

    def test_unverified_provider_url_not_certificate(self):
        result=self.check()
        self.assertEqual(result['counts']['provider_matched'],1)
        self.assertEqual(result['counts']['independently_verified_matched'],0)
        self.assertEqual(result['verified_metrics']['posts'],[])
        self.assertEqual(result['candidates'][0]['metrics']['reach'],120)

    def test_explicit_human_verified_receipt_yields_metrics(self):
        verified=dict(verified_publications=[dict(uuid='test-fb',network='facebook',
            permalink='https://www.facebook.com/retally/posts/12345/',
            verified_at='2026-10-12T12:30:00-04:00')])
        result=self.check(receipts=verified)
        self.assertEqual(result['counts']['independently_verified_matched'],1)
        self.assertEqual(result['verified_metrics']['posts'][0]['reach'],120)

    def test_bad_receipt_url_blocks_assignment(self):
        receipt=dict(verified_publications=[dict(uuid='test-fb',network='facebook',
            permalink='https://www.facebook.com/retally/posts/DIFFERENT',
            verified_at='2026-10-12T12:30:00-04:00')])
        self.assertEqual(self.check(receipts=receipt)['skipped'][0]['reason'],
                         'INDEPENDENT_RECEIPT_URL_MISMATCH')

    def test_frozen_caption_must_match_exactly(self):
        data=export(caption='This is a different introductory post')
        self.assertEqual(self.check(source={'facebook':data})['skipped'][0]['reason'],
                         'NOT_IN_FROZEN_CAMPAIGN')

    def test_newlines_and_case_are_normalized(self):
        data=export(caption='SYNTHETIC\nFREIGHT   FEE CHECKLIST')
        self.assertEqual(self.check(source={'facebook':data})['counts']['provider_matched'],1)

    def test_reused_caption_in_schedule_is_ambiguous(self):
        self.assertEqual(self.check(base=[self.base,post('another-uuid')])['skipped'][0]['reason'],
                         'AMBIGUOUS_DUPLICATE_CAPTION')

    def test_draft_cannot_become_post_through_metrics(self):
        self.assertEqual(self.check(base=[post(draft=True)])['counts']['provider_matched'],0)

    def test_duplicate_analytics_row_is_not_double_counted(self):
        data=copy.deepcopy(self.feed)
        data['rows'].append(list(data['rows'][0]))
        r=self.check(source={'facebook':data})
        self.assertEqual(r['counts']['provider_matched'],1)
        self.assertEqual(r['skipped'][0]['reason'],'DUPLICATE_ANALYTICS_ROW')

    def test_wrong_date_and_malformed_date_are_rejected(self):
        for d,reason in [('20261120','DATE_MISMATCH'),('unknown','BAD_PROVIDER_DATE')]:
            self.assertEqual(self.check(source={'facebook':export(date=d)})['skipped'][0]['reason'],reason)

    def test_profile_url_cannot_prove_individual_post(self):
        self.assertEqual(self.check(source={'facebook':export(url='https://facebook.com/retally/')})['skipped'][0]['reason'],
                         'NOT_A_PUBLIC_POST_URL')
        for u in ['https://facebook.com.evil.test/retally/posts/12',
                  'http://facebook.com/retally/posts/12',
                  'https://facebook.com/login.php']:
            self.assertFalse(_public_post_url('facebook',u))
        self.assertFalse(_public_post_url('instagram','https://www.instagram.com/p/'))

    def test_unknown_is_not_zero(self):
        self.assertIsNone(_metric(None))
        self.assertIsNone(_metric(''))
        self.assertEqual(_metric('0.0'),0)
        r=self.check(source={'facebook':export(reach='0.0',comments=0)})
        self.assertEqual(r['candidates'][0]['metrics']['reach'],0)
        self.assertIsNone(r['candidates'][0]['metrics']['shares'])

    def test_invalid_metric_is_not_silently_coerced(self):
        for v in [-1,True,'-1','7.2','NaN','inf']:
            data=export(reach=5)
            data['rows'][0][data['field_ids'].index('FBPO12')]=v
            self.assertEqual(self.check(source={'facebook':data})['skipped'][0]['reason'],
                             'INVALID_PROVIDER_METRIC')

    def test_schema_shape_and_required_fields(self):
        d=copy.deepcopy(self.feed)
        d['field_ids']=d['field_ids'][:-1]
        with self.assertRaises(ValueError): self.check(source={'facebook':d})
        d=copy.deepcopy(self.feed)
        d['field_ids'][1]='not-caption'
        with self.assertRaises(ValueError): self.check(source={'facebook':d})

    def test_future_observation_rejected(self):
        d=copy.deepcopy(self.feed);d['observed_at']='2026-10-25T13:00:00Z'
        with self.assertRaises(ValueError): self.check(source={'facebook':d})

    def test_instagram_post_matching_and_no_implicit_confirmation(self):
        p=post('test-ig',network='instagram')
        d=export('instagram',reach=20,likes=5,comments=1,saves=1,shares=1)
        r=self.check(source={'instagram':d},base=[p])
        self.assertEqual(r['counts']['provider_matched'],1)
        self.assertEqual(r['counts']['independently_verified_matched'],0)
        self.assertEqual(r['candidates'][0]['metrics']['likes'],5)

    def test_future_and_unknown_receipts_rejected(self):
        for uid,time in [('test-fb','2026-10-14T14:00:00-04:00'),
                         ('unknown','2026-10-12T14:00:00-04:00')]:
            receipt=dict(verified_publications=[dict(uuid=uid,network='facebook',
                permalink='https://facebook.com/retally/posts/12345',verified_at=time)])
            with self.assertRaises(ValueError): self.check(receipts=receipt)

    def test_no_exports_means_no_false_results(self):
        self.assertEqual(self.check(source={})['counts']['provider_matched'],0)


if __name__=='__main__':
    unittest.main()
