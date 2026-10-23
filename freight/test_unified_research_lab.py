"""Offline adversarial contract tests for all four unified research lanes."""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from unittest.mock import patch

from freight.unified_research_lab import (
    ENGINES, SEARCHES, ResearchError, current_engine, ledger_from, merge_sources,
    read_ledger, run, safe_url, scan, source_record, validate_ledger,
    mirror_scout_all,
)

NOW = datetime(2026, 10, 22, 20, 0, tzinfo=timezone.utc)


class UnifiedResearchLabTests(unittest.TestCase):
    def test_every_engine_scheduled_in_one_twenty_minute_cycle(self):
        selected = [current_engine(NOW + timedelta(minutes=5 * i)) for i in range(4)]
        self.assertEqual(set(selected), set(ENGINES))

    def test_offline_populates_only_rights_held_real_source_pointers(self):
        with tempfile.TemporaryDirectory() as root:
            ledger = Path(root) / "sources.json"
            for engine in ENGINES:
                result = run(engine=engine, live=False, ledger=ledger, now=NOW)
                self.assertFalse(result["network_enabled"])
                self.assertEqual(result["customer_contact_actions"], 0)
            records = read_ledger(ledger)["entries"]
            self.assertGreaterEqual(len(records), 6)
            self.assertTrue(all(x["rights_state"].startswith("UNVERIFIED") for x in records))
            self.assertTrue(all(not x["commercial_reuse_authorized"] for x in records))
            self.assertTrue(all(not x["recovered_cash_verified"] for x in records))
            self.assertTrue(all(not x["independent_ground_truth"] for x in records))

    def test_repeat_preserves_first_seen_and_exact_file_bytes(self):
        with tempfile.TemporaryDirectory() as root:
            ledger = Path(root) / "sources.json"
            a = run(engine="freightrecovery", live=False, ledger=ledger, now=NOW)
            contents = ledger.read_bytes()
            b = run(engine="freightrecovery", live=False, ledger=ledger,
                    now=NOW + timedelta(days=1))
            self.assertGreater(a["new_leads"], 0)
            self.assertEqual(b["new_leads"], 0)
            self.assertEqual(ledger.read_bytes(), contents)

    def test_one_canonical_source_can_feed_multiple_engines(self):
        link = "https://catalog.data.gov/dataset/real-example"
        doc, count = merge_sources(ledger_from([]), "freightrecovery",
                                   [link], "2026-10-22")
        self.assertEqual(count, 1)
        later, count2 = merge_sources(doc, "recoveryos", [link], "2026-10-23")
        self.assertEqual(count2, 0)
        self.assertEqual(len(later["entries"]), 1)
        self.assertEqual(later["entries"][0]["first_seen"], "2026-10-22")
        self.assertEqual(later["entries"][0]["engines"],
                         ["freightrecovery", "recoveryos"])

    def test_source_flags_cannot_be_forged_even_if_digest_recomputed(self):
        doc = ledger_from([source_record(
            "https://www.gao.gov/products/b-160344", "freightrecovery", "2026-10-22"
        )])
        doc["entries"][0]["independent_ground_truth"] = True
        from freight.unified_research_lab import digest
        doc["entries_sha256"] = digest(doc["entries"])
        with self.assertRaises(ResearchError):
            validate_ledger(doc)

    def test_rows_cannot_hide_document_bytes_or_unknown_fields(self):
        doc = ledger_from([source_record(
            "https://sam.gov/opportunities", "capturebrief", "2026-10-22"
        )])
        doc["entries"][0]["private_invoice_bytes"] = "secret"
        with self.assertRaises(ResearchError):
            validate_ledger(doc)

    def test_untrusted_external_links_blocked(self):
        for url in (
            "http://catalog.data.gov/dataset/x",
            "https://catalog.data.gov@127.0.0.1/dataset/x",
            "https://127.0.0.1/dataset/x",
            "https://catalog.data.gov/dataset/x?token=private",
            "https://catalog.data.gov/../private",
            "https://evil.invalid/records/3",
            "https://catalog.data.gov/%0Aevil",
            "https://github.com/owner/repo#fragment",
        ):
            with self.subTest(url=url), self.assertRaises(ResearchError):
                safe_url(url)

    def test_feed_parses_canonical_metadata_and_not_raw_rows(self):
        def fake(url):
            if "retally-unified-research-scout" in url:
                engine = parse_qs(urlsplit(url).query)["engine"][0]
                return {"engine": engine,
                        "scope": "PUBLIC_SOURCE_POINTERS_NOT_APPROVED_TEST_DATA",
                        "sources": []}
            if "api.github.com" in url:
                return {"items": [{"html_url": "https://github.com/owner/public-data",
                                   "description": "ignore copied PII"},
                                  {"html_url": "https://internal.example/repo"}]}
            return {"hits": {"hits": [{"id": 12345, "metadata": {"creators": ["X"]}}]}}
        with patch.dict(os.environ, {"RETALLY_DATAGOV_API_KEY": ""}):
            urls, errors = scan("freightrecovery", fetch=fake)
        self.assertEqual(errors, [])
        self.assertIn("https://github.com/owner/public-data", urls)
        self.assertIn("https://zenodo.org/records/12345", urls)
        self.assertTrue(all("@" not in x and "private" not in x for x in urls))

    def test_nyc_official_catalog_uses_dataset_ids_only(self):
        def fake(url):
            if "retally-unified-research-scout" in url:
                engine = parse_qs(urlsplit(url).query)["engine"][0]
                return {"engine": engine,
                        "scope": "PUBLIC_SOURCE_POINTERS_NOT_APPROVED_TEST_DATA",
                        "sources": []}
            if "api.us.socrata.com" in url:
                return {"results": [
                    {"resource": {"id": "abcd-1234", "name": "DOHMH Restaurant Inspection"},
                     "owner": {"email": "nobody@example.invalid"}},
                    {"resource": {"id": "rbx6-tga4", "name": "DOB NOW: Build – Approved Permits"}},
                    {"resource": {"id": "../secret"}},
                ]}
            if "api.github.com" in url:
                return {"items": []}
            return {"hits": {"hits": []}}
        with patch.dict(os.environ, {"RETALLY_DATAGOV_API_KEY": ""}):
            urls, errors = scan("permitplate", fetch=fake)
        self.assertEqual(errors, [])
        self.assertEqual(urls, ["https://data.cityofnewyork.us/d/rbx6-tga4"])

    def test_data_gov_v4_is_not_used_without_a_production_api_key(self):
        seen = []
        def fake(url):
            if "retally-unified-research-scout" in url:
                engine = parse_qs(urlsplit(url).query)["engine"][0]
                return {"engine": engine,
                        "scope": "PUBLIC_SOURCE_POINTERS_NOT_APPROVED_TEST_DATA",
                        "sources": []}
            seen.append(url)
            return {"items": []} if "api.github.com" in url else {"hits": {"hits": []}}
        with patch.dict(os.environ, {"RETALLY_DATAGOV_API_KEY": ""}):
            scan("capturebrief", fetch=fake)
        self.assertFalse(any("api.gsa.gov" in url for url in seen))
        self.assertFalse(any("catalog.data.gov/api/3/" in url for url in seen))

    def test_data_gov_v4_only_admits_public_dataset_metadata(self):
        def fake(url):
            if "retally-unified-research-scout" in url:
                engine = parse_qs(urlsplit(url).query)["engine"][0]
                return {"engine": engine,
                        "scope": "PUBLIC_SOURCE_POINTERS_NOT_APPROVED_TEST_DATA",
                        "sources": []}
            if "api.gsa.gov" in url:
                return {"results": [
                    {"slug": "public-data-2026", "dcat": {"accessLevel": "public"},
                     "description": "contains arbitrary names and private details"},
                    {"slug": "restricted-data-2026", "dcat": {"accessLevel": "restricted public"}},
                    {"slug": "../unsafe", "dcat": {"accessLevel": "public"}},
                ]}
            return {"items": []} if "api.github.com" in url else {"hits": {"hits": []}}
        with patch.dict(os.environ, {"RETALLY_DATAGOV_API_KEY": "fake-test-key"}):
            urls, errors = scan("recoveryos", fetch=fake)
        self.assertEqual(errors, [])
        self.assertEqual(urls, ["https://catalog.data.gov/dataset/public-data-2026"])

    def test_partial_provider_failure_is_disclosed_but_all_fail_closed(self):
        def partial(url):
            if "retally-unified-research-scout" in url:
                engine = parse_qs(urlsplit(url).query)["engine"][0]
                return {"engine": engine,
                        "scope": "PUBLIC_SOURCE_POINTERS_NOT_APPROVED_TEST_DATA",
                        "sources": []}
            if "zenodo.org" in url:
                raise ResearchError("HTTP_STATUS_503")
            if "api.us.socrata.com" in url:
                return {"results": []}
            return {"items": []}
        with patch.dict(os.environ, {"RETALLY_DATAGOV_API_KEY": ""}):
            urls, errors = scan("permitplate", fetch=partial)
        self.assertEqual(urls, [])
        self.assertEqual(len(errors), 2)
        self.assertTrue(all("HTTP_STATUS_503" in x for x in errors))
        def all_failed(_):
            raise ResearchError("OFFLINE")
        with patch.dict(os.environ, {"RETALLY_DATAGOV_API_KEY": ""}):
            with self.assertRaisesRegex(ResearchError, "ALL_PUBLIC_FEEDS_UNAVAILABLE"):
                scan("recoveryos", fetch=all_failed)

    def test_independent_scout_validated_metadata_is_prioritized(self):
        def fake(url):
            if "retally-unified-research-scout" in url:
                return {"engine": "recoveryos",
                        "scope": "PUBLIC_SOURCE_POINTERS_NOT_APPROVED_TEST_DATA",
                        "sources": [
                            {"url": "https://zenodo.org/records/12345",
                             "private_account": "never copied"},
                            {"url": "https://github.com/public/recon-dataset"},
                        ]}
            return {"items": []} if "api.github.com" in url else {"hits": {"hits": []}}
        with patch.dict(os.environ, {"RETALLY_DATAGOV_API_KEY": ""}):
            urls, errors = scan("recoveryos", fetch=fake)
        self.assertEqual(errors, [])
        self.assertEqual(urls, ["https://zenodo.org/records/12345",
                                "https://github.com/public/recon-dataset"])
        self.assertNotIn("private_account", str(urls))

    def test_independent_scout_rejects_invalid_or_cross_engine_source(self):
        def fake(url):
            if "retally-unified-research-scout" in url:
                return {"engine": "freightrecovery",
                        "scope": "PUBLIC_SOURCE_POINTERS_NOT_APPROVED_TEST_DATA",
                        "sources": [{"url": "https://evil.invalid/private"}]}
            return {"items": []} if "api.github.com" in url else {"hits": {"hits": []}}
        with patch.dict(os.environ, {"RETALLY_DATAGOV_API_KEY": ""}):
            urls, errors = scan("permitplate", fetch=fake)
        self.assertEqual(urls, [])
        self.assertTrue(any("UNTRUSTED_SCOUT_FEED" in e for e in errors))

    def test_corrupt_saved_ledger_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "leads.json"
            path.write_text('{"entries":[]}', encoding="utf-8")
            before = path.read_bytes()
            with self.assertRaises(ResearchError):
                run(engine="capturebrief", live=False, ledger=path, now=NOW)
            self.assertEqual(path.read_bytes(), before)


    def test_one_git_run_mirrors_all_four_lanes_and_preserves_scout_first_seen(self):
        observed = []
        urls = {
            "freightrecovery": "https://www.gao.gov/products/b-160344",
            "permitplate": "https://data.cityofnewyork.us/d/43nn-pn8j",
            "capturebrief": "https://sam.gov/opportunities",
            "recoveryos": "https://www.penninecare.nhs.uk/download_file/5855/277",
        }
        def fake(url):
            self.assertTrue(url.startswith("https://retally-unified-research-scout."))
            engine = parse_qs(urlsplit(url).query)["engine"][0]
            observed.append(engine)
            return {"engine": engine, "scope": "PUBLIC_SOURCE_POINTERS_NOT_APPROVED_TEST_DATA",
                    "sources": [{"url": urls[engine], "first_seen": "2026-10-22",
                                 "extra_personal_note": "never copied"}]}
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "leads.json"
            now = NOW + timedelta(days=1)
            out = mirror_scout_all(ledger=path, now=now, fetch=fake)
            self.assertEqual(observed, list(ENGINES))
            self.assertEqual(out["new_leads"], 4)
            self.assertEqual(out["feed_errors"], [])
            before = path.read_bytes()
            again = mirror_scout_all(ledger=path, now=now, fetch=fake)
            self.assertEqual(again["new_leads"], 0)
            self.assertEqual(before, path.read_bytes())
            records = read_ledger(path)["entries"]
            self.assertEqual(len(records), 4)
            self.assertTrue(all(row["first_seen"] == "2026-10-22" for row in records))
            self.assertTrue(all(row["commercial_reuse_authorized"] is False for row in records))
            self.assertTrue(all(row["independent_ground_truth"] is False for row in records))
            self.assertNotIn("extra_personal_note", path.read_text())

    def test_mirror_quarantines_failed_or_future_dated_lane_without_overwriting_ledger(self):
        def fake(url):
            engine = parse_qs(urlsplit(url).query)["engine"][0]
            if engine == "permitplate":
                return {"engine": "recoveryos", "scope": "PUBLIC_SOURCE_POINTERS_NOT_APPROVED_TEST_DATA",
                        "sources": []}
            if engine == "capturebrief":
                return {"engine": engine, "scope": "PUBLIC_SOURCE_POINTERS_NOT_APPROVED_TEST_DATA",
                        "sources": [{"url": "https://sam.gov/opportunities",
                                     "first_seen": "2099-12-01"}]}
            return {"engine": engine, "scope": "PUBLIC_SOURCE_POINTERS_NOT_APPROVED_TEST_DATA",
                    "sources": []}
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "leads.json"
            run(engine="freightrecovery", live=False, ledger=path, now=NOW)
            before = path.read_bytes()
            report = mirror_scout_all(ledger=path, now=NOW, fetch=fake)
            self.assertEqual(report["new_leads"], 0)
            self.assertEqual(len(report["feed_errors"]), 2)
            self.assertTrue(any("UNTRUSTED_SCOUT_FEED" in e for e in report["feed_errors"]))
            self.assertTrue(any("SCOUT_OBSERVATION_DATE_INVALID" in e for e in report["feed_errors"]))
            self.assertEqual(before, path.read_bytes())


    def test_permitplate_searches_are_construction_not_restaurant(self):
        self.assertTrue(all("restaurant" not in q.lower() for q in SEARCHES["permitplate"]))
        self.assertTrue(any("permit" in q.lower() for q in SEARCHES["permitplate"]))

    def test_permitplate_obvious_wrong_topic_is_excluded_but_history_unchanged(self):
        prior = source_record("https://github.com/owner/nyc-restaurant-inspections",
                              "permitplate", "2026-10-22")
        ledger = ledger_from([prior])
        revised, added = merge_sources(
            ledger, "permitplate",
            ["https://github.com/owner/nyc-restaurant-inspections-2026",
             "https://github.com/owner/NYC-DOB-Building-Permits"],
            "2026-10-23")
        self.assertEqual(added, 1)
        self.assertEqual(len(revised["entries"]), 2)
        self.assertIn(prior, revised["entries"])
        self.assertTrue(any("NYC-DOB-Building-Permits" in row["url"]
                            for row in revised["entries"]))


if __name__ == "__main__":
    unittest.main()
