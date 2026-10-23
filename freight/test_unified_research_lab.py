"""Offline adversarial contract tests for all four unified research lanes."""
from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from freight.unified_research_lab import (
    ENGINES, ResearchError, current_engine, ledger_from, merge_sources,
    read_ledger, run, safe_url, scan, source_record, validate_ledger,
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
            if "catalog.data.gov" in url:
                return {"result": {"results": [
                    {"name": "shipping-invoice-2026", "title": "Hidden personal name",
                     "notes": "private bill-to account", "email": "none@example.org"},
                    {"name": "../secret", "title": "bad"},
                ]}}
            if "api.github.com" in url:
                return {"items": [{"html_url": "https://github.com/owner/public-data",
                                   "description": "ignore copied PII"},
                                  {"html_url": "https://internal.example/repo"}]}
            return {"hits": {"hits": [{"id": 12345, "metadata": {"creators": ["X"]}}]}}
        urls, errors = scan("freightrecovery", fetch=fake)
        self.assertEqual(errors, [])
        self.assertIn("https://github.com/owner/public-data", urls)
        self.assertIn("https://catalog.data.gov/dataset/shipping-invoice-2026", urls)
        self.assertIn("https://zenodo.org/records/12345", urls)
        self.assertTrue(all("@" not in x and "private" not in x for x in urls))

    def test_partial_provider_failure_is_disclosed_but_all_fail_closed(self):
        def partial(url):
            if "catalog.data.gov" in url:
                raise ResearchError("OFFLINE")
            return {"items": []} if "github.com" in url else {"hits": {"hits": []}}
        urls, errors = scan("permitplate", fetch=partial)
        self.assertEqual(urls, [])
        self.assertEqual(len(errors), 2)
        def all_failed(_):
            raise ResearchError("OFFLINE")
        with self.assertRaisesRegex(ResearchError, "ALL_PUBLIC_FEEDS_UNAVAILABLE"):
            scan("recoveryos", fetch=all_failed)

    def test_corrupt_saved_ledger_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "leads.json"
            path.write_text('{"entries":[]}', encoding="utf-8")
            before = path.read_bytes()
            with self.assertRaises(ResearchError):
                run(engine="capturebrief", live=False, ledger=path, now=NOW)
            self.assertEqual(path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
