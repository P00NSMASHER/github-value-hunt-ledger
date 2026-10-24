"""Adversarial tests for authentic URL observations, not approved benchmark truth."""
from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from freight.research_publisher_provenance import (
    CONTENT_CLASSES, MAX_RESPONSE_BYTES, OUTPUT, SCOPE,
    _safe_head_and_digest, _validate_receipt, build_receipt, fingerprint_media,
    pinned_rows, run,
)
from freight.research_source_review import PUBLIC_REVIEW_ANCHORS
from freight.unified_research_lab import (
    ENGINES, ResearchError, digest, ledger_from, source_record,
)

PAST = date(2026, 10, 22)
TODAY = date(2026, 10, 23)
HASH = "a" * 64


def full_anchors():
    return ledger_from([
        source_record(url, engine, "2026-10-21")
        for engine in ENGINES
        for url in PUBLIC_REVIEW_ANCHORS[engine]
    ])


def observed_http(_url: str) -> dict:
    return {"probe_state": "PUBLIC_CONTENT_FINGERPRINTED",
            "head_http_status": 200, "media_class": "HTML",
            "content_sha256": HASH, "bytes_hashed": 25}


def unreachable(_url: str) -> dict:
    return {"probe_state": "NETWORK_UNAVAILABLE", "head_http_status": None,
            "media_class": "UNKNOWN", "content_sha256": None, "bytes_hashed": 0}


class PublisherEvidenceProvenanceTests(unittest.TestCase):
    def test_all_four_source_lanes_have_public_pinned_allowlisted_observations(self):
        ledger = full_anchors()
        anchors, missing = pinned_rows(ledger)
        self.assertEqual(len(anchors), 11)
        self.assertIn("https://www.gao.gov/products/b-215958", PUBLIC_REVIEW_ANCHORS["freightrecovery"])
        self.assertIn("https://www.gao.gov/products/b-215958-2", PUBLIC_REVIEW_ANCHORS["freightrecovery"])
        self.assertEqual(set(missing), set(ENGINES))
        self.assertTrue(all(value == 0 for value in missing.values()))
        self.assertEqual(set(x["engine"] for x in anchors), set(ENGINES))
        doc = build_receipt(ledger, TODAY, fetcher=observed_http)
        self.assertEqual(doc["schema_version"], 1)
        self.assertEqual(doc["scope"], SCOPE)
        self.assertEqual(doc["source_pointers_probed"], 11)
        self.assertEqual(doc["publisher_http_responses_observed"], 11)
        self.assertEqual(doc["full_public_responses_fingerprinted"], 11)
        self.assertEqual(doc["anchor_set_sha256"], digest(anchors))
        self.assertEqual(doc["receipt_sha256"],
                         digest({k: v for k, v in doc.items() if k != "receipt_sha256"}))
        self.assertEqual(_validate_receipt(doc, ledger, TODAY), doc)
        for observation in doc["observations"]:
            self.assertFalse(observation["commercial_reuse_approved"])
            self.assertFalse(observation["independent_outcome_verified"])
            self.assertFalse(observation["benchmark_ready"])
            self.assertFalse(observation["source_document_bytes_stored"])
            self.assertNotIn("url", observation)
            self.assertEqual(observation["content_sha256"], HASH)

    def test_missing_anchor_is_disclosed_not_fabricated(self):
        ledger = ledger_from([source_record(
            "https://www.gao.gov/products/b-160344",
            "freightrecovery", "2026-10-21",
        )])
        anchors, missing = pinned_rows(ledger)
        self.assertEqual(len(anchors), 1)
        self.assertEqual(missing["freightrecovery"], 4)
        self.assertEqual(missing["capturebrief"], 2)
        doc = build_receipt(ledger, TODAY, fetcher=unreachable)
        self.assertEqual(doc["source_pointers_probed"], 1)
        self.assertEqual(doc["publisher_http_responses_observed"], 0)
        self.assertEqual(doc["full_public_responses_fingerprinted"], 0)
        self.assertEqual(_validate_receipt(doc, ledger, TODAY), doc)

    def test_one_day_cache_avoids_duplicate_paid_or_unpaid_network_fetches(self):
        ledger = full_anchors()
        calls = []
        def fake(url):
            calls.append(url)
            return observed_http(url)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "leads.json"
            receipt = Path(tmp) / "publisher_provenance_v1.json"
            path.write_text(json.dumps(ledger), encoding="utf-8")
            first = run(ledger_path=path, output=receipt,
                        as_of=PAST, live=True, fetcher=fake)
            self.assertEqual(first["pinned_public_sources_checked"], 11)
            self.assertEqual(len(calls), 11)
            self.assertTrue(first["performed_new_network_probes"])
            saved = receipt.read_bytes()
            again = run(ledger_path=path, output=receipt,
                        as_of=PAST, live=True, fetcher=fake)
            self.assertFalse(again["performed_new_network_probes"])
            self.assertEqual(len(calls), 11)
            self.assertEqual(saved, receipt.read_bytes())
            verified = run(ledger_path=path, output=receipt,
                           as_of=TODAY, verify_only=True)
            self.assertFalse(verified["performed_new_network_probes"])
            self.assertEqual(verified["receipt_sha256"], first["receipt_sha256"])
            newer = run(ledger_path=path, output=receipt,
                        as_of=TODAY, live=True, fetcher=fake)
            self.assertTrue(newer["performed_new_network_probes"])
            self.assertEqual(len(calls), 22)
            self.assertNotEqual(saved, receipt.read_bytes())

    def test_tampering_rights_outcomes_fingerprints_or_anchor_ids_rejected(self):
        ledger = full_anchors()
        baseline = build_receipt(ledger, TODAY, fetcher=observed_http)
        edits = (
            ("commercial_reuse_approved", True),
            ("independent_outcome_labels_verified", 1),
            ("independently_scored_benchmark_cases", 1),
            ("verified_recovered_cash_cents", 1),
            ("source_document_bytes_stored", 1),
        )
        for field, value in edits:
            doc = json.loads(json.dumps(baseline))
            doc[field] = value
            doc["receipt_sha256"] = digest(
                {k: v for k, v in doc.items() if k != "receipt_sha256"})
            with self.subTest(field=field), self.assertRaises(ResearchError):
                _validate_receipt(doc, ledger, TODAY)
        for field, value in (
            ("source_id", "0" * 64), ("content_sha256", "not-sha256"),
            ("probe_state", "COMMERCIAL_LICENSE_APPROVED"),
            ("benchmark_ready", True), ("source_document_bytes_stored", True),
        ):
            doc = json.loads(json.dumps(baseline))
            doc["observations"][0][field] = value
            doc["receipt_sha256"] = digest(
                {k: v for k, v in doc.items() if k != "receipt_sha256"})
            with self.subTest(field=field), self.assertRaises(ResearchError):
                _validate_receipt(doc, ledger, TODAY)

    def test_adding_unrelated_catalog_urls_does_not_invalidate_daily_anchor_receipt(self):
        original = full_anchors()
        report = build_receipt(original, TODAY, fetcher=observed_http)
        rows = original["entries"] + [source_record(
            "https://github.com/synthetic-fixture/federal-contract-dataset",
            "capturebrief", "2026-10-23",
        )]
        updated = ledger_from(rows)
        self.assertNotEqual(original["entries_sha256"], updated["entries_sha256"])
        self.assertEqual(_validate_receipt(report, updated, TODAY), report)
        replaced = ledger_from([row for row in original["entries"]
                                if row["url"] != "https://sam.gov/opportunities"])
        with self.assertRaises(ResearchError):
            _validate_receipt(report, replaced, TODAY)

    def test_unpinned_target_is_refused_before_any_dns_resolution(self):
        with patch("freight.research_publisher_provenance.global_dns",
                   side_effect=AssertionError("DNS_NOT_ALLOWED")):
            with self.assertRaisesRegex(ResearchError, "UNPINNED_EXTERNAL_REQUEST_BLOCKED"):
                _safe_head_and_digest("https://github.com/synthetic-fixture/personal-private")
            with self.assertRaisesRegex(ResearchError, "UNPINNED_EXTERNAL_REQUEST_BLOCKED"):
                _safe_head_and_digest("http://www.gao.gov/products/b-160344")

    def test_head_and_get_fingerprint_bounded_same_public_origin_no_source_storage(self):
        url = "https://www.gao.gov/products/b-160344"
        content = b"<html><title>Public source test only</title></html>"
        calls = []
        class Response:
            status = 200
            def __init__(self, method):
                self.method = method
                self.headers = {"Content-Type": "text/html",
                                "Content-Length": str(len(content)),
                                "Content-Encoding": "identity"}
            def __enter__(self):
                return self
            def __exit__(self, *_):
                return None
            def geturl(self):
                return url
            def read(self, n):
                self_limit = n
                assert self_limit == MAX_RESPONSE_BYTES + 1
                return content
        class Opener:
            def open(self, request, timeout):
                calls.append((request.get_method(), timeout))
                return Response(request.get_method())
        with patch("freight.research_publisher_provenance.global_dns", return_value=None), \
                patch("freight.research_publisher_provenance.build_opener", return_value=Opener()):
            report = _safe_head_and_digest(url)
        self.assertEqual([x[0] for x in calls], ["HEAD", "GET"])
        self.assertEqual(report["probe_state"], "PUBLIC_CONTENT_FINGERPRINTED")
        self.assertEqual(report["bytes_hashed"], len(content))
        self.assertEqual(report["content_sha256"], hashlib.sha256(content).hexdigest())
        self.assertEqual(report["head_http_status"], 200)
        self.assertNotIn("content", report)
        self.assertNotIn(content.decode(), str(report))

    def test_large_response_is_not_fetched_and_no_truncated_hash_is_claimed(self):
        url = "https://www.gao.gov/products/b-160344"
        class Response:
            status = 200
            headers = {"Content-Type": "application/pdf",
                       "Content-Length": str(MAX_RESPONSE_BYTES + 1)}
            def __enter__(self):
                return self
            def __exit__(self, *_):
                return None
            def geturl(self):
                return url
        class Opener:
            def open(self, request, timeout):
                if request.get_method() == "GET":
                    raise AssertionError("UNBOUNDED_DOWNLOAD_ATTEMPT")
                return Response()
        with patch("freight.research_publisher_provenance.global_dns", return_value=None), \
                patch("freight.research_publisher_provenance.build_opener", return_value=Opener()):
            report = _safe_head_and_digest(url)
        self.assertEqual(report["probe_state"], "PUBLISHER_CONTENT_TOO_LARGE")
        self.assertIsNone(report["content_sha256"])
        self.assertEqual(report["bytes_hashed"], 0)

    def test_provider_unavailable_becomes_failed_observation_not_verified_truth(self):
        url = "https://www.gao.gov/products/b-160344"
        with patch("freight.research_publisher_provenance.global_dns",
                   side_effect=ResearchError("DNS_UNAVAILABLE")):
            report = _safe_head_and_digest(url)
        self.assertEqual(report["probe_state"], "DNS_UNAVAILABLE")
        self.assertIsNone(report["head_http_status"])
        self.assertIsNone(report["content_sha256"])
        doc = build_receipt(
            ledger_from([source_record(url, "freightrecovery", "2026-10-21")]),
            TODAY, fetcher=lambda _: report)
        self.assertEqual(doc["publisher_http_responses_observed"], 0)
        self.assertFalse(doc["commercial_reuse_approved"])

    def test_hash_requires_complete_bounded_response_not_partial(self):
        from freight.research_publisher_provenance import _observation
        ledger = full_anchors()
        anchor = pinned_rows(ledger)[0][0]
        for probe in (
            {"probe_state": "PUBLIC_CONTENT_FINGERPRINTED",
             "head_http_status": 200, "media_class": "HTML",
             "content_sha256": None, "bytes_hashed": 12},
            {"probe_state": "PUBLIC_HTTP_METADATA_ONLY",
             "head_http_status": 200, "media_class": "HTML",
             "content_sha256": HASH, "bytes_hashed": 12},
            {"probe_state": "PUBLIC_CONTENT_FINGERPRINTED",
             "head_http_status": None, "media_class": "HTML",
             "content_sha256": HASH, "bytes_hashed": 12},
            {"probe_state": "PUBLIC_CONTENT_FINGERPRINTED",
             "head_http_status": 200, "media_class": "HTML",
             "content_sha256": HASH, "bytes_hashed": MAX_RESPONSE_BYTES + 1},
        ):
            with self.subTest(probe=probe), self.assertRaises(ResearchError):
                _observation(anchor, probe)

    def test_media_codes_are_fixed_and_never_save_response_headers(self):
        for mime, expected in (
            ("text/html; charset=utf-8", "HTML"),
            ("application/json", "JSON"),
            ("application/pdf", "PDF"),
            ("text/csv", "CSV"),
            ("text/plain", "TEXT"),
            ("image/jpeg", "OTHER"),
            ("", "UNKNOWN"),
        ):
            with self.subTest(mime=mime):
                self.assertEqual(fingerprint_media(mime), expected)
                self.assertIn(expected, CONTENT_CLASSES)
        self.assertNotEqual(str(OUTPUT), "")
        with self.assertRaises(ResearchError):
            run(live=False, verify_only=False)


    def test_incomplete_http_byte_range_is_never_reported_as_complete_hash(self):
        url = "https://www.gao.gov/products/b-160344"
        class Response:
            status = 200
            headers = {"Content-Type": "text/html", "Content-Length": "50"}
            def __enter__(self):
                return self
            def __exit__(self, *_):
                return None
            def geturl(self):
                return url
            def read(self, n):
                return b"<html>short</html>"
        class Opener:
            def open(self, request, timeout):
                return Response()
        with patch("freight.research_publisher_provenance.global_dns", return_value=None), \
                patch("freight.research_publisher_provenance.build_opener", return_value=Opener()):
            report = _safe_head_and_digest(url)
        self.assertEqual(report["head_http_status"], 200)
        self.assertEqual(report["probe_state"], "GET_NOT_VERIFIABLE")
        self.assertIsNone(report["content_sha256"])
        self.assertEqual(report["bytes_hashed"], 0)

    def test_receipt_must_not_claim_fresh_verification_after_two_days(self):
        ledger = full_anchors()
        three_days_old = date(2026, 10, 20)
        doc = build_receipt(ledger, three_days_old, fetcher=observed_http)
        with self.assertRaisesRegex(ResearchError, "STALE_PUBLISHER_PROVENANCE_RECEIPT"):
            _validate_receipt(doc, ledger, TODAY)

    def test_mutated_provenance_receipt_is_not_reused_same_day(self):
        ledger = full_anchors()
        calls = []
        def fake(url):
            calls.append(url)
            return unreachable(url)
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "ledger.json"
            receipt = Path(tmp) / "provenance.json"
            source.write_text(json.dumps(ledger))
            run(ledger_path=source, output=receipt, as_of=TODAY,
                live=True, fetcher=fake)
            self.assertEqual(len(calls), 11)
            malicious = json.loads(receipt.read_text())
            malicious["observations"][0]["benchmark_ready"] = True
            malicious["receipt_sha256"] = digest(
                {k: v for k, v in malicious.items() if k != "receipt_sha256"})
            receipt.write_text(json.dumps(malicious))
            res = run(ledger_path=source, output=receipt, as_of=TODAY,
                      live=True, fetcher=fake)
            self.assertTrue(res["performed_new_network_probes"])
            self.assertEqual(len(calls), 22)
            self.assertFalse(json.loads(receipt.read_text())[
                "observations"][0]["benchmark_ready"])



if __name__ == "__main__":
    unittest.main()
