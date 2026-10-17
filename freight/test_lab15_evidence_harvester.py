"""Offline security, integrity, and idempotency checks for Lab 15."""
from __future__ import annotations
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
from urllib.error import HTTPError
import socket
import unittest
from unittest.mock import patch

from freight.lab15_evidence_harvester import (
    Rejected, SOURCES, blank_ledger, dedup_key, digest, new_lead, run, sanitize_title, source_items,
    validate_ledger, verify_url, NoRedirect, public_addresses,
)

SEED_FILE = Path(__file__).parent / 'research' / 'lab15_public_seeds.json'
NOW = datetime(2026, 10, 17, 12, tzinfo=timezone.utc)


def seeds():
    return json.loads(SEED_FILE.read_text())


class Tests(unittest.TestCase):
    def test_seed_bootstrap_is_metadata_not_real_benchmark(self):
        ledger, report = run(blank_ledger(), seeds(), now=NOW)
        self.assertEqual(report['new_leads'], 4)
        self.assertEqual(len(ledger['leads']), 4)
        self.assertFalse(any(r['customer_use_authorized'] or r['invoice_bytes_archived']
                             or r['rated_ground_truth_verified'] for r in ledger['leads']))
        self.assertEqual(report['api_queries_attempted'], 0)
        validate_ledger(ledger)

    def test_idempotent_replay_and_no_network_without_opt_in(self):
        getter = lambda url: self.fail('network called without authorization')
        one, report = run(blank_ledger(), seeds(), transport=getter, now=NOW)
        two, other = run(one, seeds(), transport=getter, now=NOW)
        self.assertEqual(one, two)
        self.assertEqual(report['new_leads'], 4)
        self.assertEqual(other['new_leads'], 0)

    def test_mock_live_sources_add_bounded_unique_leads(self):
        def fake(url):
            if 'data.gov' in url:
                return {'result': {'results': [{'name': 'real-freight-invoice-audit', 'title': 'Freight invoice audit data'}]}}
            if 'dataverse' in url:
                return {'data': {'items': [{'type': 'dataset', 'url': 'https://dataverse.harvard.edu/dataset.xhtml?persistentId=doi:10.1/abc', 'name': 'Freight invoice audit research'}]}}
            if 'datacite' in url:
                return {'data': [{'attributes': {'doi': '10.5281/zenodo.12345', 'titles': [{'title': 'LTL freight invoice dataset'}]}}]}
            if 'github' in url:
                return {'items': [{'html_url': 'https://github.com/example/freight-invoice-data', 'name': 'freight-invoice-data', 'description': 'freight invoice audit dataset'}]}
            raise AssertionError(url)
        ledger, report = run(blank_ledger(), seeds(), network=True, transport=fake, now=NOW)
        self.assertEqual(report['api_queries_attempted'], len(SOURCES))
        self.assertEqual(report['api_query_failures'], [])
        self.assertEqual(report['new_leads'], 8)
        self.assertEqual(len(ledger['leads']), 8)
        again, rr = run(ledger, seeds(), network=True, transport=fake, now=NOW)
        self.assertEqual(again, ledger)
        self.assertEqual(rr['new_leads'], 0)

    def test_unapproved_urls_and_secrets_rejected(self):
        bad = [
            'http://catalog.data.gov/dataset/x',
            'https://127.0.0.1/internal',
            'https://api.github.com@evil.test/test',
            'https://github.com.evil.test/example',
            'https://github.com/private?token=abc',
            'https://document.epiq11.com/%40user/report',
            'https://document.epiq11.com/a#frag',
            'https://github.com:444/repo',
            'https://github.com//private',
        ]
        for candidate in bad:
            with self.subTest(candidate=candidate), self.assertRaises(Rejected):
                verify_url(candidate)
        with self.assertRaises(Rejected):
            verify_url('https://www.gao.gov/products/b-143246', api=True)

    def test_reject_data_masquerading_as_license_approval(self):
        entry = new_lead('https://github.com/example/freight-invoice-data', 'LTL invoice audit sample', 'github', '2026-10-17')
        obj = blank_ledger()
        obj['leads'] = [entry]
        obj['digest_sha256'] = '0' * 64
        with self.assertRaisesRegex(Rejected, 'LEDGER_DIGEST_MISMATCH'):
            validate_ledger(obj)
        approved = deepcopy(entry)
        approved['customer_use_authorized'] = True
        from freight.lab15_evidence_harvester import digest
        obj['leads'] = [approved]
        obj['digest_sha256'] = digest({k: obj[k] for k in obj if k != 'digest_sha256'})
        with self.assertRaisesRegex(Rejected, 'UNAPPROVED_LEDGER_PROMOTION'):
            validate_ledger(obj)

    def test_reject_duplicate_seed_and_cross_run_deduplication(self):
        base = seeds()
        base['seeds'].append(deepcopy(base['seeds'][0]))
        result, report = run(blank_ledger(), base, now=NOW)
        self.assertEqual(report['new_leads'], 4)
        self.assertEqual(len(result['leads']), 4)

    def test_privacy_sanitization_and_relevance(self):
        self.assertNotIn('test@example.com', sanitize_title('Freight invoice to test@example.com'))
        self.assertNotIn('555-123-4567', sanitize_title('Freight bill 555-123-4567'))
        self.assertFalse(source_items('github', {'items': [{'name': 'hello', 'description': 'random software', 'html_url': 'https://github.com/a/b'}]}))
        self.assertRaises(Rejected, source_items, 'untrusted', {})

    def test_private_dns_and_redirect_denied(self):
        with patch('freight.lab15_evidence_harvester.socket.getaddrinfo', return_value=[(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('127.0.0.1', 443))]):
            with self.assertRaisesRegex(Rejected, 'DNS_NOT_PUBLIC'):
                public_addresses('catalog.data.gov')
        with self.assertRaisesRegex(Rejected, 'REDIRECT_BLOCKED'):
            NoRedirect().redirect_request(None, None, 302, '', {}, 'http://127.0.0.1')

    def test_failed_provider_is_reported_not_silently_successful(self):
        def broken(url):
            raise TimeoutError('provider offline')
        obj, report = run(blank_ledger(), seeds(), network=True, transport=broken, now=NOW)
        self.assertEqual(report['api_queries_attempted'], len(SOURCES))
        self.assertEqual(len(report['api_query_failures']), len(SOURCES))
        self.assertEqual(report['total_leads'], 4)
        self.assertFalse(report['claims_or_marketing_approved'])
        self.assertEqual(report['status'], 'PARTIAL_DISCOVERY_PROVIDER_ERRORS')
        self.assertTrue(all(x.endswith(':TIMEOUTERROR') for x in report['api_query_failures']))
        validate_ledger(obj)

    def test_first_run_doi_case_collision_collapses_preserving_original_receipt(self):
        low = new_lead('https://doi.org/10.7910/dvn/9c0mus', 'DataCite LTL invoice evidence candidate', 'datacite', '2026-10-16')
        high = new_lead('https://doi.org/10.7910/DVN/9C0MUS', 'Dataverse LTL invoice evidence candidate', 'dataverse', '2026-10-17')
        self.assertEqual(dedup_key(low['url']), dedup_key(high['url']))
        old = blank_ledger()
        old['leads'] = [low, high]
        old['digest_sha256'] = digest({k: old[k] for k in old if k != 'digest_sha256'})
        with self.assertRaisesRegex(Rejected, 'DUPLICATE_CANONICAL_URL'):
            validate_ledger(old)
        repaired, report = run(old, seeds(), now=NOW)
        validate_ledger(repaired)
        self.assertIn(low, repaired['leads'])
        self.assertNotIn(high, repaired['leads'])
        self.assertEqual(report['total_leads'], 5)
        self.assertEqual(report['new_leads'], 4)
        self.assertFalse(any(row['customer_use_authorized'] or row['rated_ground_truth_verified'] for row in repaired['leads']))
        twice, again = run(repaired, seeds(), now=NOW)
        self.assertEqual(twice, repaired)
        self.assertEqual(again['new_leads'], 0)

    def test_provider_http_error_category_and_partial_run_status(self):
        def blocked(url):
            raise HTTPError(url, 403, 'Denied', None, None)
        result, report = run(blank_ledger(), seeds(), network=True, transport=blocked, now=NOW)
        self.assertEqual(report['status'], 'PARTIAL_DISCOVERY_PROVIDER_ERRORS')
        self.assertEqual(report['api_query_failures'].count('data_gov:HTTP_403'), 2)
        self.assertEqual(len(report['api_query_failures']), len(SOURCES))
        validate_ledger(result)


if __name__ == '__main__':
    unittest.main()
