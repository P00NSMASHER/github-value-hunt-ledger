from copy import deepcopy
from datetime import date
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from recoveryworks.seven_branch_simulation import seed, authorize_population
from recoveryworks.workbench import Workspace
from recoveryworks.customer_delivery import build_delivery, csv_cell


class CustomerReadinessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.workspace, self.tokens = seed(Path(self.temp.name) / 'client')

    def test_all_seven_require_exact_reviewed_customer_scope(self):
        statuses = self.workspace.onboarding_status()
        self.assertEqual(len(statuses), 7)
        self.assertTrue(all(item['analysis_ready'] for item in statuses.values()))
        intake = self.workspace._intake()
        scope = deepcopy(intake['onboarding']['ap']['scope'])
        record = self.workspace.submit_onboarding(self.tokens['customer'], 'ap', scope)
        with self.assertRaisesRegex(ValueError, 'independent audit scope review'):
            self.workspace.scan(self.tokens['operator'])
        with self.assertRaises(PermissionError):
            self.workspace.review_onboarding(self.tokens['customer'], 'ap', record['scope_hash'], 'self review')
        self.workspace.review_onboarding(self.tokens['independent'], 'ap', record['scope_hash'], 'Synthetic second review')
        self.workspace.scan(self.tokens['operator'])

    def test_changed_source_or_settings_invalidates_scope(self):
        self.workspace.configure(self.tokens['operator'], 'ap', {'default_effective_from': '2026-02-01'})
        self.assertFalse(self.workspace.onboarding_status()['ap']['analysis_ready'])
        with self.assertRaisesRegex(ValueError, 'renew customer scope'):
            self.workspace.scan(self.tokens['operator'])
        authorize_population(self.workspace, self.tokens, ['ap'])
        self.workspace.scan(self.tokens['operator'])
        source = self.workspace._intake()['sources']['ap/payments_csv']
        raw = self.workspace.read_source(self.tokens['customer'], source['id'])['content'].replace('PAY-2', 'PAY-3')
        updated = self.workspace.upload(self.tokens['customer'], 'ap', 'payments_csv', raw)
        self.workspace.review_source(self.tokens['reviewer'], 'ap', 'payments_csv', updated['normalized_sha256'], 'changed export')
        with self.assertRaisesRegex(ValueError, 'renew customer scope'):
            self.workspace.scan(self.tokens['operator'])

    def test_bad_counts_currency_consent_and_stale_review_blocked(self):
        original = self.workspace._intake()['onboarding']['ap']['scope']
        for field,value in [('currency', 'EUR'), ('authorized_to_analyze', False), ('period_end', '2099-01-01')]:
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.workspace.submit_onboarding(self.tokens['customer'], 'ap', {**original, field: value})
        scope = deepcopy(original);scope['expected_rows']['ap/payments_csv'] += 1
        with self.assertRaisesRegex(ValueError, 'row count'):
            self.workspace.submit_onboarding(self.tokens['customer'], 'ap', scope)
        with self.assertRaises(PermissionError):
            self.workspace.submit_onboarding(self.tokens['operator'], 'ap', original)
        with self.assertRaisesRegex(ValueError, 'stale'):
            self.workspace.review_onboarding(self.tokens['reviewer'], 'ap', '0'*64, 'stale')

    def test_original_evidence_tamper_blocks_scan_even_if_normalized_unchanged(self):
        receipt = self.workspace._intake()['sources']['ap/payments_csv']
        (self.workspace.root / ('sources/' + receipt['id'] + '.original')).write_text('tampered')
        with self.assertRaisesRegex(ValueError, 'source integrity'):
            self.workspace.scan(self.tokens['operator'])

    def test_delivery_is_customer_scoped_traceable_and_not_a_recovery_claim(self):
        self.workspace.scan(self.tokens['operator'])
        report = self.workspace.customer_delivery(self.tokens['customer'])
        payload = json.loads(report['json'])
        self.assertEqual(hashlib.sha256(report['json'].encode()).hexdigest(), report['sha256'])
        self.assertEqual(len(payload['cases']), 7)
        self.assertEqual(payload['totals_by_currency']['USD']['potential_cents'], 29300)
        self.assertEqual(payload['totals_by_currency']['USD']['net_received_cents'], 0)
        self.assertTrue(payload['simulation'])
        for token in self.tokens.values():
            self.assertNotIn(token, report['json'] + report['html'] + report['csv'])
        self.assertNotIn(str(self.workspace.root), report['json'])
        _, other = Workspace.create(Path(self.temp.name) / 'other', 'other')
        with self.assertRaises(PermissionError):
            self.workspace.customer_delivery(other['customer'])

    def test_delivery_escapes_html_formulas_and_never_nets_currencies(self):
        self.workspace.scan(self.tokens['operator'])
        state = self.workspace.cases(self.tokens['customer'])
        first, second = state['cases'][:2]
        first.update(currency='USD', potential_cents=10000, recovered_cents=0, fee_cents=0, remaining_cents=10000,
                     counterparty='<script>alert(1)</script>', reference='=HYPERLINK("bad")')
        second.update(currency='EUR', potential_cents=20000, recovered_cents=0, fee_cents=0, remaining_cents=20000)
        state['cases'] = [first, second]
        report = build_delivery(state)
        self.assertIn('&lt;script&gt;', report['html'])
        self.assertNotIn('<script>', report['html'])
        self.assertIn("'=HYPERLINK", report['csv'])
        payload = json.loads(report['json'])
        self.assertEqual(payload['totals_by_currency']['USD']['potential_cents'], 10000)
        self.assertEqual(payload['totals_by_currency']['EUR']['potential_cents'], 20000)
        for text in ('=1', '+1', '-1', '@SUM(A1)', '\t=1', '  =1'):
            self.assertTrue(csv_cell(text).startswith("'"))

    def test_export_cannot_certify_self_posted_receipts_as_bank_proven_cash(self):
        # Adversarial report-only state: a malicious or mistaken local ledger
        # caller has populated positive recovered cents. This does not create
        # any real customer payment or independently authenticated issuer proof.
        self.workspace.scan(self.tokens['operator'])
        state = self.workspace.cases(self.tokens['customer'])
        state['simulation'] = False
        state['cases'][0]['recovered_cents'] = 12750
        state['cases'][0]['fee_cents'] = 550
        state['cases'][0]['remaining_cents'] = 0
        report = build_delivery(state)
        payload = json.loads(report['json'])
        self.assertEqual(payload['totals_by_currency']['USD']['net_received_cents'], 12750)
        self.assertEqual(payload['external_cash_verification_status'], 'NOT_VERIFIED')
        self.assertIsNone(payload['independently_verified_realized_recovery_cents'])
        self.assertIs(payload['externally_verified_recovery_claim_approved'], False)
        self.assertIs(payload['commercially_validated'], False)
        self.assertIn('Cash verification: NOT VERIFIED.', report['html'])
        self.assertIn('No displayed receipt is independently authenticated', report['html'])
        self.assertIn('12750', report['csv'])
        self.assertEqual(hashlib.sha256(report['json'].encode()).hexdigest(),
                         report['sha256'])
        # Actual synthetic fixture remains source-isolated; no money moved.
        self.assertEqual(self.workspace.store.load().rollup()['recovered_cents'], 0)

    def test_health_checks_restore_and_detects_revocation_and_tamper(self):
        from recoveryworks.workbench_health import check_workspace
        self.workspace.scan(self.tokens['operator'])
        self.assertFalse(check_workspace(self.workspace.root)['healthy'])
        self.workspace.backup(self.tokens['operator'])
        health = check_workspace(self.workspace.root)
        self.assertTrue(health['healthy'], health)
        self.assertFalse(health['production_certified'])
        self.workspace.manage_credential('customer', revoke=True, reason='synthetic lost key')
        self.assertFalse(check_workspace(self.workspace.root)['healthy'])
        self.workspace.manage_credential('customer', reason='synthetic recovery')
        self.workspace.backup(self.tokens['operator'])
        latest = max((self.workspace.root / 'backups').glob('*.json'), key=lambda p:p.stat().st_mtime)
        latest.write_text('{}')
        health = check_workspace(self.workspace.root)
        self.assertFalse(health['healthy'])
        self.assertNotIn(str(self.workspace.root), json.dumps(health))

    def test_duplicate_auth_headers_and_idle_socket_fail_closed(self):
        import http.client
        import socket
        import threading
        from recoveryworks.workbench_server import make_server
        server = make_server(self.workspace)
        server.socket_timeout = 0.2
        thread = threading.Thread(target=server.serve_forever, daemon=True);thread.start()
        try:
            connection = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=2)
            connection.putrequest('GET', '/api/state')
            connection.putheader('Authorization', 'Bearer ' + self.tokens['customer'])
            connection.putheader('Authorization', 'Bearer ' + self.tokens['operator'])
            connection.endheaders()
            response = connection.getresponse()
            self.assertEqual(response.status, 403)
            response.read();connection.close()
            slow = socket.create_connection(('127.0.0.1', server.server_port), timeout=2)
            try:
                slow.sendall(b'GET / HTTP/1.1\r\nHost:')
                self.assertEqual(slow.recv(1), b'')
            finally:
                slow.close()
        finally:
            server.shutdown();server.server_close();thread.join()

    def test_rebate_missing_due_date_cannot_be_promoted_by_source_review(self):
        receipt = self.workspace._intake()['sources']['rebate/programs_json']
        programs = json.loads(self.workspace.read_source(self.tokens['customer'], receipt['id'])['content'])
        del programs[0]['payment_due_date']
        new = self.workspace.upload(self.tokens['customer'], 'rebate', 'programs_json', json.dumps(programs))
        self.workspace.review_source(self.tokens['reviewer'], 'rebate', 'programs_json', new['normalized_sha256'], 'synthetic incomplete terms')
        with self.assertRaisesRegex(ValueError, 'payment due dates'):
            authorize_population(self.workspace, self.tokens, ['rebate'])
        with self.assertRaises(ValueError):
            self.workspace.scan(self.tokens['operator'])

    def test_stale_scan_cannot_be_used_after_reauthorizing_new_sources(self):
        self.workspace.scan(self.tokens['operator'])
        case = next(c for c in self.workspace.cases(self.tokens['reviewer'])['cases'] if c['branch'] == 'ap')
        self.workspace.configure(self.tokens['operator'], 'ap', {'default_effective_from': '2026-02-01'})
        with self.assertRaisesRegex(ValueError, 'current intake approval'):
            self.workspace.action(self.tokens['reviewer'], 'approve', case['finding_id'], self.workspace.store.current_head_hash(), {'note':'stale review'})
        authorize_population(self.workspace, self.tokens, ['ap'])
        with self.assertRaisesRegex(ValueError, 'rescan current approved sources'):
            self.workspace.customer_delivery(self.tokens['customer'])
        with self.assertRaisesRegex(ValueError, 'rescan current approved sources'):
            self.workspace.action(self.tokens['reviewer'], 'approve', case['finding_id'], self.workspace.store.current_head_hash(), {'note':'stale scan'})
