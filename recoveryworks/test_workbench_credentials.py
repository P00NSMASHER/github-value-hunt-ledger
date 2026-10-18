import contextlib
from datetime import datetime, timedelta, timezone
import io
import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from recoveryworks.cli import write_private_json
from recoveryworks.workbench import Workspace, sha
from recoveryworks.workbench_credentials import main
from recoveryworks.workbench_server import make_server


class CredentialTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.workspace, self.tokens = Workspace.create(Path(self.temp.name) / 'client', 'client')

    def keys(self):
        return json.loads((self.workspace.root / 'credentials.json').read_text())

    def test_rotation_invalidates_existing_server_and_preserves_identity(self):
        server = make_server(self.workspace)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        def state(token):
            request = Request(f'http://127.0.0.1:{server.server_port}/api/state',
                              headers={'Authorization': 'Bearer ' + token})
            with urlopen(request, timeout=3) as response:
                return json.load(response)
        try:
            old = self.tokens['reviewer']
            original = self.workspace.principal(old)['actor_id']
            self.assertEqual(state(old)['client_id'], 'client')
            # A separate process/object updates the credential file.
            Workspace(self.workspace.root).manage_credential('reviewer', reason='routine rotation')
            with self.assertRaises(HTTPError) as error:
                state(old)
            self.assertEqual(error.exception.code, 403)
            fresh = self.keys()['reviewer']
            self.assertEqual(self.workspace.principal(fresh)['actor_id'], original)
            self.assertEqual(state(fresh)['client_id'], 'client')
            Workspace(self.workspace.root).manage_credential('reviewer', revoke=True, reason='lost device')
            with self.assertRaises(HTTPError) as error:
                state(fresh)
            self.assertEqual(error.exception.code, 403)
            self.assertNotIn('reviewer', self.keys())
            # Other roles continue operating.
            self.assertEqual(state(self.tokens['customer'])['client_id'], 'client')
        finally:
            server.shutdown(); server.server_close(); thread.join()

    def test_expired_missing_naive_and_malformed_expirations_fail_closed(self):
        path = self.workspace.root / 'workspace.json'
        meta = json.loads(path.read_text())
        entry = meta['tokens'][sha(self.tokens['customer'].encode())]
        for expiry in (None, 'bad', '2099-01-01T00:00:00',
                       (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()):
            with self.subTest(expiry=expiry):
                entry['expires_at'] = expiry
                write_private_json(path, meta)
                with self.assertRaises(PermissionError):
                    self.workspace.cases(self.tokens['customer'])
        del entry['expires_at']
        write_private_json(path, meta)
        with self.assertRaises(PermissionError):
            self.workspace.principal(self.tokens['customer'])
        self.workspace.manage_credential('customer', reason='migrate legacy credentials')
        self.assertEqual(self.workspace.principal(self.keys()['customer'])['role'], 'customer')

    def test_restore_does_not_resurrect_revoked_keys(self):
        receipt = self.workspace.backup(self.tokens['operator'])
        snapshot = json.loads((self.workspace.root / 'backups' / (receipt['snapshot_id'] + '.json')).read_text())
        self.workspace.manage_credential('customer', revoke=True, reason='compromised')
        restored = Workspace.restore_snapshot(snapshot, Path(self.temp.name) / 'restored')
        for token in self.tokens.values():
            with self.assertRaises(PermissionError):
                restored.principal(token)
        restored.manage_credential('operator', reason='restore recovery')
        fresh = json.loads((restored.root / 'credentials.json').read_text())
        self.assertEqual(restored.principal(fresh['operator'])['role'], 'operator')

    def test_case_currency_is_preserved_in_api_state(self):
        from dataclasses import replace
        from recoveryworks.durable_ledger import DurableRecoveryLedger
        from recoveryworks.test_durable_ledger import verified_finding
        ledger = DurableRecoveryLedger()
        finding = replace(verified_finding(), client_id='client', currency='EUR')
        ledger.add(finding)
        self.workspace.store.save(ledger)
        cases = self.workspace.cases(self.tokens['customer'])['cases']
        self.assertEqual(cases[0]['currency'], 'EUR')

    def test_cli_never_prints_keys_and_changes_are_recorded(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            main(['--workspace', str(self.workspace.root), '--role', 'operator',
                  '--hours', '2', '--reason', 'routine rotation'])
        for key in [*self.tokens.values(), *self.keys().values()]:
            self.assertNotIn(key, output.getvalue())
            self.assertNotIn(key, (self.workspace.root / 'workspace.json').read_text())
        events = self.workspace.meta.get('credential_events', [])
        self.assertEqual(events, [])  # Separate instance, authentication reloads current metadata.
        meta = json.loads((self.workspace.root / 'workspace.json').read_text())
        self.assertEqual(meta['credential_events'][-1]['operation'], 'rotate')
        for hours in (0, 169, True, 1.5):
            with self.assertRaises(ValueError):
                self.workspace.manage_credential('customer', hours=hours, reason='invalid')
        with self.assertRaises(ValueError):
            self.workspace.manage_credential('admin', reason='invalid')
        with self.assertRaises(ValueError):
            self.workspace.manage_credential('customer', reason='')
