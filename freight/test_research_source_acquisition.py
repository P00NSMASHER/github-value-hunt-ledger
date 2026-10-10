"""Offline adversarial validation for manually authorized public-page captures."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import socket
import unittest
from unittest.mock import patch

from freight.research_source_acquisition import (
    CaptureError, DenyRedirects, MAX_BYTES, capture, canonical_sha,
    resolve_public_host, sha_hex, text_excerpt, validate_manifest, validate_url,
)

ROOT = Path(__file__).parent
MANIFEST = ROOT / "research" / "PUBLIC_SOURCE_MANIFEST_20261010.json"
NOW = datetime(2026, 10, 10, 12, 43, tzinfo=timezone.utc)


def manifest():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def fake_get(url):
    assert url.startswith("https://")
    html = b"<html><head><style>.hidden{}</style></head><body><h1>Public source</h1><script>HACKED</script><p>Invoice facts.</p></body></html>"
    return 200, url, "text/html", html


class SourceAcquisitionTests(unittest.TestCase):
    def test_approved_twelve_source_manifest(self):
        m = manifest()
        validate_manifest(m)
        self.assertEqual(len(m["sources"]), 12)
        self.assertEqual(len({x["id"] for x in m["sources"]}), 12)

    def test_network_never_runs_without_explicit_opt_in(self):
        with self.assertRaisesRegex(CaptureError, "NETWORK_DISABLED"):
            capture(manifest(), transport=lambda url: self.fail("network called"))

    def test_approved_mock_fetch_creates_unreviewed_citations_only(self):
        r = capture(manifest(), selected=["bts.cfs.2022", "recoveraudit.pricing"],
                    network_enabled=True, transport=fake_get, now=NOW)
        self.assertEqual(len(r["captures"]), 2)
        self.assertEqual(r["fetch_error_count"], 0)
        self.assertEqual(r["status"], "CANDIDATES_NEED_HUMAN_SOURCE_REVIEW")
        self.assertFalse(any(x["claim_import_authorized"] for x in r["captures"]))
        self.assertFalse(any(x["publisher_content_truth_verified"] for x in r["captures"]))
        self.assertNotIn("HACKED", r["captures"][0]["preview_excerpt"])
        self.assertIn("Invoice facts.", r["captures"][0]["preview_excerpt"])
        self.assertNotIn("raw", r["captures"][0].keys())
        self.assertTrue(all(x["full_body_saved"] is False for x in r["captures"]))
        self.assertEqual(len(r["captures"][0]["raw_body_sha256"]), 64)
        self.assertEqual(r["receipt_sha256"], canonical_sha(
            {k: v for k, v in r.items() if k != "receipt_sha256"}))

    def test_unknown_or_duplicate_selection_fails_before_network(self):
        for selections in (["fake"], ["bts.cfs.2022", "bts.cfs.2022"], []):
            with self.subTest(selections=selections):
                with self.assertRaises(CaptureError):
                    capture(manifest(), selected=selections, network_enabled=True,
                            transport=lambda url: self.fail("fetch before validation"))

    def test_overlarge_body_never_becomes_candidate(self):
        def oversized(url):
            return 200, url, "text/html", b"x" * (MAX_BYTES + 1)
        r = capture(manifest(), selected=["bts.cfs.2022"],
                    network_enabled=True, transport=oversized, now=NOW)
        self.assertEqual(r["captures"][0]["status"], "FETCH_FAILED_OR_REJECTED")
        self.assertEqual(r["captures"][0]["reason"], "BODY_EMPTY_OR_TOO_LARGE")

    def test_redirect_and_status_never_succeed(self):
        for response in (
            (200, "https://other.example.org/redirected", "text/html", b"not empty"),
            (302, "https://www.bts.gov/faf", "text/html", b"redirect"),
            (200, "https://www.bts.gov/newsroom/commodity-flow-survey-2022-data-released",
             "application/pdf", b"%PDF not parsed"),
        ):
            with self.subTest(response=response[:3]):
                r = capture(manifest(), selected=["bts.cfs.2022"],
                            network_enabled=True, transport=lambda url: response, now=NOW)
                self.assertEqual(r["captures"][0]["status"], "FETCH_FAILED_OR_REJECTED")
                self.assertFalse(r["captures"][0]["claim_import_authorized"])

    def test_url_allowlist_rejects_ssrf_credentials_and_redirect_substitution(self):
        bad = [
            "https://127.0.0.1/private", "https://localhost/internal",
            "https://169.254.169.254/latest/meta-data", "http://www.bts.gov/faf",
            "https://www.bts.gov.evil.com/faf", "https://user:pass@www.bts.gov/faf",
            "https://www.bts.gov:8443/faf", "javascript:alert(1)",
            "https://www.bts.gov//internal", "https://www.bts.gov/faf#section",
        ]
        for value in bad:
            with self.subTest(url=value):
                with self.assertRaises(CaptureError):
                    validate_url(value)

    def test_manifest_duplicate_url_and_unapproved_lanes_fail(self):
        data = manifest()
        data["sources"][1]["url"] = data["sources"][0]["url"]
        with self.assertRaisesRegex(CaptureError, "DUPLICATE_URL"):
            validate_manifest(data)
        data = manifest()
        data["sources"][0]["lane"] = "live_customer_pii"
        with self.assertRaisesRegex(CaptureError, "UNKNOWN_RESEARCH_LANE"):
            validate_manifest(data)

    def test_dns_private_ip_and_empty_answer_rejected(self):
        with patch("freight.research_source_acquisition.socket.getaddrinfo",
                   return_value=[(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443))]):
            with self.assertRaisesRegex(CaptureError, "DNS_NONPUBLIC_ADDRESS"):
                resolve_public_host("www.bts.gov")
        with patch("freight.research_source_acquisition.socket.getaddrinfo", return_value=[]):
            with self.assertRaisesRegex(CaptureError, "DNS_NO_ANSWERS"):
                resolve_public_host("www.bts.gov")

    def test_http_redirect_handler_disallows_redirect(self):
        with self.assertRaisesRegex(CaptureError, "REDIRECT_REJECTED"):
            DenyRedirects().redirect_request(None, None, 302, "", {},
                                             "https://www.bts.gov/faf")

    def test_truncated_html_contains_no_executable_markup(self):
        raw = b"<p>First</p><script>secret();</script><style>bad{}</style><p>Second</p>"
        preview = text_excerpt(raw, "text/html")
        self.assertEqual(preview, "First Second")
        self.assertEqual(sha_hex(raw), sha_hex(raw))


if __name__ == "__main__":
    unittest.main()
