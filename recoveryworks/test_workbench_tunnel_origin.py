"""Cloudflare hostname bridge keeps the underlying workbench loopback-only."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from recoveryworks.workbench import Workspace
from recoveryworks.workbench_server import make_server, validated_external_origin


PUBLIC = 'https://workbench.retallyrecovery.com'
HOST = 'workbench.retallyrecovery.com'


class CloudflareOriginTests(unittest.TestCase):
    def test_external_origin_must_be_exact_https_domain(self):
        self.assertEqual(validated_external_origin(PUBLIC), PUBLIC)
        self.assertIsNone(validated_external_origin(None))
        for value in ('http://workbench.retallyrecovery.com',
                      'https://workbench.retallyrecovery.com:443',
                      'https://workbench.retallyrecovery.com/',
                      'https://workbench.retallyrecovery.com/path',
                      'https://workbench.retallyrecovery.com?x=1',
                      'https://workbench.retallyrecovery.com#fragment',
                      'https://user:pw@workbench.retallyrecovery.com',
                      'https://-invalid.retallyrecovery.com',
                      'https://127.0.0.1', 'https://localhost',
                      ' https://workbench.retallyrecovery.com', 'workbench.retallyrecovery.com'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validated_external_origin(value)

    def test_remote_host_origin_is_exact_and_bearer_required(self):
        with tempfile.TemporaryDirectory() as directory:
            work, roles = Workspace.create(Path(directory)/'synthetic', 'SYNTHETIC-ONLY')
            server = make_server(work, port=0, external_origin=PUBLIC)
            self.assertEqual(server.server_address[0], '127.0.0.1')
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = 'http://127.0.0.1:' + str(server.server_port)

            def fetch(path, *, host=HOST, origin=None, token=None):
                headers = {'Host': host}
                if origin is not None:
                    headers['Origin'] = origin
                if token is not None:
                    headers['Authorization'] = 'Bearer ' + token
                return urlopen(Request(base + path, headers=headers), timeout=5)

            try:
                with fetch('/') as response:
                    self.assertEqual(response.status, 200)
                    self.assertEqual(response.headers['Cache-Control'], 'no-store')
                    self.assertNotIn('Access-Control-Allow-Origin', response.headers)
                with fetch('/api/state', origin=PUBLIC, token=roles['customer']) as response:
                    self.assertEqual(json.load(response)['client_id'], 'SYNTHETIC-ONLY')
                for kw in ({'token':roles['customer'], 'origin':'https://evil.invalid'},
                           {'token':roles['customer'], 'host':'evil.invalid'},
                           {'origin':PUBLIC},
                           {'token':'invalid', 'origin':PUBLIC}):
                    with self.subTest(kw=kw), self.assertRaises(HTTPError) as error:
                        fetch('/api/state', **kw)
                    self.assertEqual(error.exception.code, 403)
                with self.assertRaises(HTTPError) as error:
                    fetch('/credentials.json')
                self.assertEqual(error.exception.code, 404)
            finally:
                server.shutdown()
                server.server_close()
                thread.join()

    def test_default_loopback_mode_does_not_accept_external_hostname(self):
        with tempfile.TemporaryDirectory() as directory:
            work, roles = Workspace.create(Path(directory)/'synthetic', 'SYNTHETIC-ONLY')
            server = make_server(work, port=0)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                url = 'http://127.0.0.1:' + str(server.server_port) + '/api/state'
                with self.assertRaises(HTTPError) as error:
                    urlopen(Request(url, headers={'Host':HOST,
                                                   'Origin':PUBLIC,
                                                   'Authorization':'Bearer '+roles['customer']}), timeout=5)
                self.assertEqual(error.exception.code, 403)
            finally:
                server.shutdown()
                server.server_close()
                thread.join()


if __name__ == '__main__':
    unittest.main()
