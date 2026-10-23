"""Safety and deterministic verification for the source-quality receipt."""
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from freight.research_lab_health import build_receipt, rendered_receipt
from freight.unified_research_lab import (
    ENGINES, ResearchError, ledger_from, source_record,
)


class ResearchLabHealthTests(unittest.TestCase):
    def example(self):
        doc = ledger_from([
            source_record("https://www.gao.gov/products/b-160344",
                          "freightrecovery", "2026-10-22"),
            source_record("https://data.cityofnewyork.us/d/43nn-pn8j",
                          "permitplate", "2026-10-22"),
            source_record("https://github.com/owner/nyc-restaurant-inspection",
                          "permitplate", "2026-10-22"),
            source_record("https://sam.gov/opportunities",
                          "capturebrief", "2026-10-22"),
            source_record("https://zenodo.org/records/12345",
                          "recoveryos", "2026-10-22"),
        ])
        return doc

    def test_each_lane_reported_without_promoting_any_unverified_source(self):
        receipt = build_receipt(self.example(), date(2026, 10, 23))
        self.assertEqual(set(receipt["engines"]), set(ENGINES))
        self.assertEqual(receipt["unique_source_pointers"], 5)
        self.assertEqual(receipt["permitplate_wrong_topic_heuristic_flags"], 2)
        self.assertEqual(receipt["engines"]["freightrecovery"]["official_publisher_host_only"], 1)
        self.assertEqual(receipt["engines"]["recoveryos"]["third_party_catalog_host_only"], 1)
        self.assertEqual(receipt["verified_original_document_benchmark_truth_cases"], 0)
        self.assertFalse(receipt["commercial_recovery_allowed"])
        self.assertFalse(any(x["commercial_reuse_confirmed"] for x in receipt["engines"].values()))
        self.assertEqual(receipt["source_document_bytes_stored"], 0)

    def test_source_ids_and_other_text_never_leak_into_aggregate_receipt(self):
        doc = self.example()
        body = rendered_receipt(doc, date(2026, 10, 23))
        self.assertEqual(body, rendered_receipt(doc, date(2026, 10, 23)))
        for record in doc["entries"]:
            self.assertNotIn(record["url"], body)
            self.assertNotIn(record["id"], body)
        self.assertIn(doc["entries_sha256"], body)
        self.assertTrue(body.endswith("\n"))

    def test_bad_source_dates_and_forged_rights_fail_closed(self):
        doc = self.example()
        doc["entries"][0]["commercial_reuse_authorized"] = True
        with self.assertRaises(ResearchError):
            build_receipt(doc, date(2026, 10, 23))
        doc = self.example()
        doc["entries"][0]["first_seen"] = "2099-01-01"
        from freight.unified_research_lab import digest
        doc["entries_sha256"] = digest(doc["entries"])
        with self.assertRaises(ResearchError):
            build_receipt(doc, date(2026, 10, 23))

    def test_shared_source_counted_once_and_per_lane_label_counts_preserved(self):
        doc = self.example()
        from freight.unified_research_lab import merge_sources
        doc, count = merge_sources(doc, "capturebrief",
                                   ["https://www.gao.gov/products/b-160344"],
                                   "2026-10-23")
        self.assertEqual(count, 0)
        x = build_receipt(doc, date(2026, 10, 23))
        self.assertEqual(x["unique_source_pointers"], 5)
        self.assertEqual(x["cross_engine_shared_pointers"], 1)
        self.assertEqual(x["engines"]["capturebrief"]["source_pointers"], 2)

    def test_empty_ledger_is_still_unverified_and_deterministic(self):
        x = build_receipt(ledger_from([]), date(2026, 10, 23))
        self.assertEqual(x["unique_source_pointers"], 0)
        self.assertEqual(x["publisher_host_counts"], {})
        self.assertTrue(all(v["source_pointers"] == 0 for v in x["engines"].values()))
        self.assertFalse(x["commercial_recovery_allowed"])


if __name__ == "__main__":
    unittest.main()
