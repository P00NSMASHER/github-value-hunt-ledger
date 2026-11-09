"""Regression controls for Cloudflare Access's reserved callback routes."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from freight.site import verify_retally_os_access as smoke


class AccessCallbackRoutingTests(unittest.TestCase):
    def test_reject_apex_to_www_callback_redirect(self):
        def redirected(url):
            return 301, url.replace("retallyrecovery.com", "www.retallyrecovery.com"), b""

        with patch.object(smoke, "_anonymous_get", side_effect=redirected):
            with self.assertRaisesRegex(AssertionError, "canonicalized to www"):
                smoke._require_access_callback_keeps_apex()

    def test_reject_apex_to_www_cert_redirect(self):
        def only_certs_redirect(url):
            if url.endswith("/callback"):
                return 400, "", b""
            return 301, "https://www.retallyrecovery.com/cdn-cgi/access/certs", b""

        with patch.object(smoke, "_anonymous_get", side_effect=only_certs_redirect):
            with self.assertRaisesRegex(AssertionError, "canonicalized to www"):
                smoke._require_access_callback_keeps_apex()

    def test_allows_cloudflare_owned_callbacks(self):
        def retained_apex(url):
            if url.endswith("/callback"):
                return 400, "", b"Invalid or missing callback state"
            return 200, "", b'{"keys":[]}'

        with patch.object(smoke, "_anonymous_get", side_effect=retained_apex):
            smoke._require_access_callback_keeps_apex()


if __name__ == "__main__":
    unittest.main()
