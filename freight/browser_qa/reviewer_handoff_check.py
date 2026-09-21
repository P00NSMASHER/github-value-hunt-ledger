"""Offline Chromium regression tests for draft reopening and batching.

Run from repository root:
    PYTHONPATH=. python freight/browser_qa/reviewer_handoff_check.py

Synthetic UI fixtures only; this suite does not replace the real pipeline
renderer/importer tests or prove customer readiness. Chromium must be installed.
Set FREIGHT_CHROMIUM_EXECUTABLE for a preinstalled system Chromium.
Set FREIGHT_BROWSER_QA_DIR to retain screenshots and downloaded test drafts.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
import tempfile
import unittest

from playwright.sync_api import expect, sync_playwright
from freight.reviewer_workbench import MAX_DECISION_BYTES, MAX_DECISIONS, _render_payload


def digest(label: str) -> str:
    return hashlib.sha256(label.encode()).hexdigest()


def fixture(*, limit: int = MAX_DECISIONS) -> dict:
    cases = []
    for index in range(4):
        ready = index < 3
        cases.append({
            'case_hash': digest(f'case-{index}'), 'invoice_id': f'TEST-{index+1:03}',
            'shipment_id': f'SHIP-{index+1}', 'charge_id': f'CHARGE-{index+1}',
            'charge_code': 'DETENTION' if ready else 'UNKNOWN', 'carrier_id': 'TEST-CARRIER',
            'service_date': '2026-09-10', 'buyer_review_ready': ready,
            'currency': 'USD' if ready else 'EUR', 'billed_cents': '12500',
            'expected_cents': '10000' if ready else None,
            'variance_cents': '2500' if ready else None, 'quantity_units': '1',
            'action_hint': 'REVIEW_VALIDATED_FINDING' if ready else 'ADD_APPLICABLE_RULE',
            'charge_source_hash': digest(f'charge-source-{index}'),
            'finding_proof_hash': digest(f'finding-{index}') if ready else None,
            'rule_evidence': [{
                'authority_document_id': 'SYNTHETIC TEST RATE',
                'verified_controlling_authority': True, 'effective_from': '2026-09-01',
                'effective_to': None, 'pricing_model': 'FIXED', 'fixed_cents': '10000',
                'unit_rate_cents': None, 'document_source_hash': digest('authority'),
                'rule_hash': digest('rule'),
            }] if ready else [],
        })
    return {
        'schema_version': 1, 'max_decisions': limit, 'max_decision_bytes': MAX_DECISION_BYTES,
        'buyer_id': 'SYNTHETIC-QA', 'business_unit': 'TEST-ONLY',
        'review_packet_hash': digest('packet'), 'review_routing_hash': digest('routing'),
        'truth_hash': digest('truth'), 'buyer_review_case_count': 3,
        'evidence_remediation_case_count': 1, 'cases': cases,
    }


def envelope(data: dict, indices: tuple[int, ...] = (0,)) -> dict:
    return {
        'schema_version': 1,
        **{key: data[key] for key in ('review_packet_hash','review_routing_hash','truth_hash')},
        'decisions': [{
            'case_hash': data['cases'][index]['case_hash'], 'disposition': 'CONFIRMED',
            'reviewer_minutes': 3, 'reviewed_at': '2026-09-21T09:00:00.000Z',
        } for index in indices],
    }


class ReviewerHandoffChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.driver = sync_playwright().start()
        executable = os.environ.get('FREIGHT_CHROMIUM_EXECUTABLE')
        options = {'headless': True}
        if executable:
            options['executable_path'] = executable
        cls.browser = cls.driver.chromium.launch(**options)
        cls.temp = tempfile.TemporaryDirectory(prefix='freight-browser-qa-')
        cls.output = Path(os.environ.get('FREIGHT_BROWSER_QA_DIR', cls.temp.name))
        cls.output.mkdir(parents=True, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.driver.stop()
        cls.temp.cleanup()

    def setUp(self):
        self.contexts = []
        self.errors = []
        self.requests = []
        self.download_number = 0
        self.data = fixture()
        self.page = self.open_page(self.data)

    def tearDown(self):
        for context in self.contexts:
            context.close()
        self.assertEqual(self.errors, [], 'Unexpected JavaScript error')
        self.assertEqual(self.requests, [], 'Unexpected network request')

    def open_page(self, data, width=1440):
        ctx = self.browser.new_context(offline=True, accept_downloads=True,
                                      viewport={'width': width, 'height': 1050})
        self.contexts.append(ctx)
        ctx.on('request', lambda req: self.requests.append(req.url))
        page = ctx.new_page()
        page.set_default_timeout(5000)
        page.on('pageerror', lambda error: self.errors.append(str(error)))
        page.set_content(_render_payload(data), wait_until='load')
        expect(page.locator("#status")).to_contain_text("Batch")
        return page

    def restore(self, obj=None, *, raw=None, page=None):
        page = page or self.page
        if raw is None:
            raw = json.dumps(obj).encode()
        page.locator('#import-feedback').evaluate('(el) => { el.textContent = ""; }')
        page.locator('#draft-file').set_input_files({
            'name': 'synthetic-draft.json', 'mimeType': 'application/json', 'buffer': raw,
        })
        expect(page.locator("#import-feedback")).to_have_text(re.compile(r"\S"))
        expect(page.locator("#draft-file")).to_have_value("")
        return page.locator('#import-feedback').inner_text()

    def save(self, page=None, *, disposition='CONFIRMED', minutes='3'):
        page = page or self.page
        page.locator('#disposition').select_option(disposition)
        page.locator('#minutes').fill(minutes)
        page.locator('#save').click()

    def export(self, page=None):
        page = page or self.page
        self.download_number += 1
        with page.expect_download() as event:
            page.locator('#export').click()
        download = event.value
        self.assertIsNone(download.failure())
        target = self.output / f'{self._testMethodName}-{self.download_number}.json'
        download.save_as(target)
        return json.loads(target.read_bytes()), download.suggested_filename

    def select_all_case(self, index, page=None):
        page = page or self.page
        page.locator('[data-filter="all"]').click()
        page.locator('#search').fill('')
        page.locator('.case-button').nth(index).click()

    def test_no_default_approval_or_external_assets(self):
        self.assertEqual(self.page.locator('#disposition').input_value(), '')
        self.assertTrue(self.page.locator('#export').is_disabled())
        self.assertIn("connect-src 'none'", self.page.content())
        self.assertEqual(self.page.locator('script[src],link[href]').count(), 0)

    def test_unsaved_edits_survive_case_navigation(self):
        self.page.locator('#disposition').select_option('UNRESOLVED')
        self.page.locator('#minutes').fill('7')
        self.page.locator('.case-button').nth(1).click()
        self.page.locator('.case-button').first.click()
        self.assertEqual(self.page.locator('#disposition').input_value(), 'UNRESOLVED')
        self.assertEqual(self.page.locator('#minutes').input_value(), '7')
        self.assertTrue(self.page.locator('#export').is_disabled())

    def test_unsaved_edits_survive_search_and_filters(self):
        self.page.locator('#minutes').fill('4')
        self.page.locator('#search').fill('does-not-exist')
        self.assertIn('No matching', self.page.locator('#empty').inner_text())
        self.page.locator('#search').fill('')
        self.page.locator('[data-filter="evidence"]').click()
        self.select_all_case(0)
        self.assertEqual(self.page.locator('#minutes').input_value(), '4')

    def test_export_blocked_until_all_case_edits_saved_or_discarded(self):
        self.save()
        self.select_all_case(1)
        self.page.locator('#minutes').fill('9')
        self.assertTrue(self.page.locator('#export').is_disabled())
        self.assertIn('unsaved edits', self.page.locator('#export-help').inner_text())
        self.page.locator('#clear').click()
        self.assertTrue(self.page.locator('#export').is_enabled())
        obj, _ = self.export()
        self.assertEqual(len(obj['decisions']), 1)

    def test_export_and_reopen_preserve_decision_and_timestamp(self):
        self.save(disposition='FALSE_POSITIVE', minutes='12')
        obj, name = self.export()
        self.assertIn('-batch-1.json', name)
        page2 = self.open_page(self.data)
        self.assertIn('1 draft decision(s) reopened', self.restore(obj, page=page2))
        again, _ = self.export(page2)
        self.assertEqual(obj, again)
        self.assertEqual(page2.locator('#disposition').input_value(), 'FALSE_POSITIVE')
        self.assertNotIn('reviewer_role', obj)
        self.assertEqual(set(obj), {'schema_version','review_packet_hash','review_routing_hash','truth_hash','decisions'})

    def test_identical_reopen_is_idempotent(self):
        obj = envelope(self.data)
        self.restore(obj)
        self.assertIn('0 draft decision(s) reopened', self.restore(obj))
        self.assertEqual(self.page.locator('#draft-count').inner_text(), '1')
        actual, _ = self.export()
        self.assertEqual(actual, obj)

    def test_conflicting_file_rejected_atomically(self):
        self.restore(envelope(self.data))
        conflicting = envelope(self.data, (1,0))
        conflicting['decisions'][1]['disposition'] = 'FALSE_POSITIVE'
        self.assertIn('conflicts', self.restore(conflicting))
        self.assertEqual(self.page.locator('#draft-count').inner_text(), '1')
        actual, _ = self.export()
        self.assertEqual(actual, envelope(self.data))

    def test_stale_context_files_rejected(self):
        for field in ('review_packet_hash','review_routing_hash','truth_hash'):
            with self.subTest(field=field):
                obj=envelope(self.data); obj[field]=digest('different')
                self.assertIn('stale audit', self.restore(obj))
                self.assertEqual(self.page.locator('#draft-count').inner_text(),'0')

    def test_unknown_and_remediation_cases_rejected(self):
        for case_hash in (digest('missing'),self.data['cases'][3]['case_hash']):
            with self.subTest(case_hash=case_hash):
                obj=envelope(self.data);obj['decisions'][0]['case_hash']=case_hash
                self.assertIn('unknown or evidence-remediation',self.restore(obj))
        self.select_all_case(3)
        self.assertTrue(self.page.locator('#decision-section').is_hidden())
        self.assertEqual(self.page.locator('#expected').inner_text(),'Not established')

    def test_duplicate_rows_rejected(self):
        obj=envelope(self.data);obj['decisions']*=2
        self.assertIn('Duplicate draft decision',self.restore(obj))

    def test_duplicate_json_keys_including_escaped_spellings_rejected(self):
        raw=json.dumps(envelope(self.data))
        for replacement in ('"schema_version": 1, "schema_version": 1',
                            '"schema_version": 1, "schema_versi\\u006fn": 1'):
            with self.subTest(replacement=replacement):
                result=self.restore(raw=raw.replace('"schema_version": 1',replacement).encode())
                self.assertIn('Duplicate JSON property',result)

    def test_nested_duplicate_keys_rejected(self):
        raw=json.dumps(envelope(self.data)).replace('"reviewer_minutes": 3','"reviewer_minutes": 3,"reviewer_minutes": 4')
        self.assertIn('Duplicate JSON property',self.restore(raw=raw.encode()))

    def test_invalid_utf8_bom_and_nonfinite_json_rejected(self):
        valid=json.dumps(envelope(self.data)).encode()
        for raw in (b'\xff',b'\xef\xbb\xbf'+valid,valid.replace(b'"reviewer_minutes": 3',b'"reviewer_minutes": NaN'),b'[[[',b'[]',b' '):
            with self.subTest(raw=raw[:40]):
                self.assertIn('Draft not opened',self.restore(raw=raw))
                self.assertEqual(self.page.locator('#draft-count').inner_text(),'0')

    def test_extra_identity_and_authority_fields_rejected(self):
        for field in ('reviewer_role','approved','__proto__'):
            with self.subTest(field=field):
                obj=envelope(self.data);obj[field]='test-only'
                self.assertIn('schema',self.restore(obj))
        obj=envelope(self.data);obj['decisions'][0]['reviewer_role']='test-only'
        self.assertIn('Unexpected',self.restore(obj))

    def test_invalid_minutes_disposition_and_version_rejected(self):
        for value in (True,-1,1.5,'3',None,2**53):
            with self.subTest(value=value):
                obj=envelope(self.data);obj['decisions'][0]['reviewer_minutes']=value
                self.assertIn('Draft not opened',self.restore(obj))
        for field,value in (('schema_version',True),('schema_version',2)):
            obj=envelope(self.data);obj[field]=value
            self.assertIn('Draft not opened',self.restore(obj))
        obj=envelope(self.data);obj['decisions'][0]['disposition']='AUTO_APPROVE'
        self.assertIn('Invalid draft disposition',self.restore(obj))

    def test_float_and_exponent_integer_spellings_rejected(self):
        raw=json.dumps(envelope(self.data))
        for replacement in ('3.0','3e0'):
            self.assertIn('Draft not opened',self.restore(raw=raw.replace('"reviewer_minutes": 3','"reviewer_minutes": '+replacement).encode()))

    def test_invalid_calendar_dates_and_naive_times_rejected(self):
        for value in ('2026-09-21T09:00:00','2026-02-30T09:00:00Z','2026-02-29T09:00:00Z',
                      '2026-09-21T24:00:00Z','2026-09-21T09:00:60Z','2026-09-21T09:00:00+24:00',''):
            with self.subTest(value=value):
                obj=envelope(self.data);obj['decisions'][0]['reviewed_at']=value
                self.assertIn('timezone-aware',self.restore(obj))

    def test_valid_offset_and_microsecond_timestamp_preserved(self):
        obj=envelope(self.data);obj['decisions'][0]['reviewed_at']='2026-09-21T09:00:00.123456-04:00'
        self.assertIn('1 draft decision(s) reopened',self.restore(obj))
        actual,_=self.export();self.assertEqual(actual,obj)

    def test_size_and_row_limits_enforced(self):
        self.assertIn('file-size limit',self.restore(raw=b' '*(MAX_DECISION_BYTES+1)))
        obj=envelope(self.data);obj['decisions']=[{}]*(MAX_DECISIONS+1)
        self.assertIn('row limit',self.restore(obj))

    def test_merge_limit_does_not_drop_current_drafts(self):
        self.page=self.open_page(fixture(limit=1))
        self.restore(envelope(self.data))
        self.assertIn('combined drafts exceed',self.restore(envelope(self.data,(1,))))
        self.assertEqual(self.page.locator('#draft-count').inner_text(),'1')

    def test_batch_rollover_requires_file_acknowledgement_and_avoids_reexport(self):
        self.page=self.open_page(fixture(limit=1))
        self.save()
        first,_=self.export()
        self.assertTrue(self.page.locator('#next-batch').is_disabled())
        self.page.locator('#file-saved').check()
        self.page.locator('#next-batch').click()
        self.assertEqual(self.page.locator('#draft-count').inner_text(),'0')
        self.assertIn('1 in earlier exported batches',self.page.locator('#status').inner_text())
        self.assertIn('TEST-002',self.page.locator('#case-title').inner_text())
        self.save(disposition='UNRESOLVED',minutes='5')
        second,name=self.export()
        self.assertIn('-batch-2.json',name)
        self.assertEqual(len(second['decisions']),1)
        self.assertNotEqual(first['decisions'][0]['case_hash'],second['decisions'][0]['case_hash'])
        self.select_all_case(0)
        self.assertIn('not approved',self.page.locator('#case-badge').inner_text())
        self.assertTrue(self.page.locator('#decision-section').is_hidden())

    def test_edit_after_export_invalidates_old_acknowledgement(self):
        self.save();self.export();self.page.locator('#file-saved').check()
        self.page.locator('#minutes').fill('8')
        self.assertTrue(self.page.locator('#export-confirmation').is_hidden())
        self.assertTrue(self.page.locator('#next-batch').is_disabled())
        self.assertFalse(self.page.locator('#file-saved').is_checked())

    def test_reopen_does_not_overwrite_unsaved_editor_input(self):
        self.page.locator('#minutes').fill('8')
        self.assertIn('unsaved case edits',self.restore(envelope(self.data)))
        self.assertEqual(self.page.locator('#minutes').input_value(),'8')
        self.assertEqual(self.page.locator('#draft-count').inner_text(),'0')

    def test_empty_draft_and_empty_packet(self):
        self.assertIn('0 draft decision(s) reopened',self.restore(envelope(self.data,())))
        data=fixture();data['cases']=[];data['buyer_review_case_count']=0;data['evidence_remediation_case_count']=0
        page=self.open_page(data)
        self.assertIn('No queued',page.locator('#empty').inner_text())
        self.assertTrue(page.locator('#export').is_disabled())

    def test_int64_and_negative_amount_formatting(self):
        data=fixture();data['cases'][0]['billed_cents']=str(2**63-1);data['cases'][0]['variance_cents']='-25'
        page=self.open_page(data)
        self.assertEqual(page.locator('#billed').inner_text(),'USD 92,233,720,368,547,758.07')
        self.assertEqual(page.locator('#variance').inner_text(),'USD -0.25')

    def test_actual_2000_decision_limit_can_export_and_continue(self):
        data=fixture()
        exemplar=data['cases'][0]
        data['cases']=[dict(exemplar, case_hash=digest(f'large-case-{i}'),
                            invoice_id=f'TEST-LARGE-{i+1}', charge_id=f'large-{i}')
                       for i in range(MAX_DECISIONS+1)]
        data['buyer_review_case_count']=MAX_DECISIONS+1
        data['evidence_remediation_case_count']=0
        page=self.open_page(data)
        obj=envelope(data,tuple(range(MAX_DECISIONS)))
        self.assertIn('2000 draft decision(s) reopened',self.restore(obj,page=page))
        actual,_=self.export(page)
        self.assertEqual(actual,obj)
        self.assertLessEqual(len((json.dumps(actual,indent=2)+'\n').encode()),MAX_DECISION_BYTES)
        page.locator('#file-saved').check()
        page.locator('#next-batch').click()
        self.assertIn('TEST-LARGE-2001',page.locator('#case-title').inner_text())
        self.save(page,disposition='UNRESOLVED')
        second,_=self.export(page)
        self.assertEqual(len(second['decisions']),1)
        self.assertEqual(second['decisions'][0]['case_hash'],data['cases'][-1]['case_hash'])

    def test_responsive_layout_and_screenshots(self):
        for width in (1440,768,390,320):
            with self.subTest(width=width):
                page=self.open_page(self.data,width)
                self.restore(envelope(self.data),page=page)
                self.export(page)
                self.assertLessEqual(page.evaluate('document.documentElement.scrollWidth'),width)
                page.screenshot(path=str(self.output/f'reviewer-{width}.png'),full_page=True)


if __name__ == '__main__':
    unittest.main(verbosity=2)
