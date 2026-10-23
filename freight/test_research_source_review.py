"""Adversarial offline controls for four-engine public-source review priorities."""
from __future__ import annotations

import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from freight.research_source_review import (
    EVIDENCE_GAPS, MAX_REVIEW_PER_ENGINE, PUBLIC_REVIEW_ANCHORS,
    SCOPE, build_queue, render_queue, run,
)
from freight.unified_research_lab import (
    ENGINES, ResearchError, digest, ledger_from, merge_sources,
    source_record,
)

NOW = date(2026, 10, 23)


def sample_ledger():
    entries = [
        source_record("https://www.gao.gov/products/b-160344",
                      "freightrecovery", "2026-10-22"),
        source_record("https://github.com/synthetic-fixture/trucking-tariffs",
                      "freightrecovery", "2026-10-23"),
        source_record("https://zenodo.org/records/12345",
                      "freightrecovery", "2026-10-22"),
        source_record("https://data.cityofnewyork.us/d/rbx6-tga4",
                      "permitplate", "2026-10-23"),
        source_record("https://data.cityofnewyork.us/d/43nn-pn8j",
                      "permitplate", "2026-10-22"),
        source_record("https://github.com/synthetic-fixture/nyc-restaurant-inspection",
                      "permitplate", "2026-10-22"),
        source_record("https://sam.gov/opportunities",
                      "capturebrief", "2026-10-22"),
        source_record("https://www.penninecare.nhs.uk/download_file/5855/277",
                      "recoveryos", "2026-10-22"),
    ]
    return ledger_from(entries)


class ReviewQueueTests(unittest.TestCase):
    def test_all_four_lanes_rank_real_public_anchors_ahead_of_generic_catalogs(self):
        doc = sample_ledger()
        out = build_queue(doc, NOW)
        self.assertEqual(out["scope"], SCOPE)
        self.assertEqual(out["unique_public_source_references"], 8)
        self.assertEqual(set(out["engines"]), set(ENGINES))
        for engine in ENGINES:
            lane = out["engines"][engine]
            self.assertGreaterEqual(lane["ranked_for_manual_evidence_review"], 1)
            self.assertEqual(lane["priority_review_queue"][0]["rank_reason"],
                             "PINNED_PUBLIC_ANCHOR_URL_ONLY")
            self.assertIn(lane["priority_review_queue"][0]["public_source_url"],
                          PUBLIC_REVIEW_ANCHORS[engine])
            self.assertEqual(lane["missing_benchmark_evidence"], list(EVIDENCE_GAPS[engine]))
            self.assertFalse(lane["commercial_use_approved"])
            self.assertEqual(lane["independent_benchmark_truth_cases_from_queue"], 0)
        freight = out["engines"]["freightrecovery"]["priority_review_queue"]
        self.assertEqual([v["rank_reason"] for v in freight], [
            "PINNED_PUBLIC_ANCHOR_URL_ONLY",
            "THIRD_PARTY_URL_TOPIC_HINT_ONLY",
            "UNCLASSIFIED_THIRD_PARTY_CATALOG_URL_ONLY",
        ])
        self.assertEqual(out["queue_sha256"],
                         digest({k: v for k, v in out.items() if k != "queue_sha256"}))

    def test_permitplate_historical_wrong_topic_preserved_but_not_prioritized(self):
        doc = sample_ledger()
        before = json.dumps(doc, sort_keys=True)
        out = build_queue(doc, NOW)
        permit = out["engines"]["permitplate"]
        self.assertEqual(permit["catalog_source_associations"], 3)
        self.assertEqual(permit["url_only_topic_exclusions_not_deleted"], 2)
        self.assertEqual(permit["ranked_for_manual_evidence_review"], 1)
        self.assertEqual(permit["priority_review_queue"][0]["public_source_url"],
                         "https://data.cityofnewyork.us/d/rbx6-tga4")
        self.assertEqual(before, json.dumps(doc, sort_keys=True))
        self.assertEqual(out["external_document_bytes_saved"], 0)

    def test_never_promote_forged_rights_truth_or_future_dated_source(self):
        doc = sample_ledger()
        doc["entries"][0]["commercial_reuse_authorized"] = True
        doc["entries_sha256"] = digest(doc["entries"])
        with self.assertRaisesRegex(ResearchError, "UNTRUSTED_RESEARCH_CLAIM"):
            build_queue(doc, NOW)
        doc = sample_ledger()
        doc["entries"][0]["first_seen"] = "2099-01-01"
        doc["entries_sha256"] = digest(doc["entries"])
        with self.assertRaisesRegex(ResearchError, "REVIEW_SOURCE_FUTURE_DATED"):
            build_queue(doc, NOW)
        with self.assertRaisesRegex(ResearchError, "REVIEW_DATE_REQUIRED"):
            build_queue(sample_ledger(), "2026-10-23")

    def test_top_eight_quota_cannot_inflate_original_evidence_metrics(self):
        rows = [source_record(
            f"https://github.com/synthetic-fixture/government-contract-{i:03d}",
            "capturebrief", "2026-10-23",
        ) for i in range(28)]
        doc = ledger_from(rows)
        out = build_queue(doc, NOW)
        lane = out["engines"]["capturebrief"]
        self.assertEqual(lane["catalog_source_associations"], 28)
        self.assertEqual(lane["ranked_for_manual_evidence_review"], MAX_REVIEW_PER_ENGINE)
        self.assertEqual(lane["candidate_classes"]["third_party_path_topic_hints_only"], 28)
        self.assertEqual(len({r["source_id"] for r in lane["priority_review_queue"]}), 8)
        self.assertEqual(out["independent_outcome_labels_promoted"], 0)
        self.assertEqual(out["real_customer_cases_promoted"], 0)
        self.assertEqual(out["verified_recovered_cash_cents"], 0)
        self.assertFalse(out["commercial_recovery_allowed"])
        for v in lane["priority_review_queue"]:
            self.assertEqual(set(v), {
                "source_id", "public_source_url", "publisher_host", "first_seen",
                "rank_reason", "source_provenance_verified",
                "original_document_bytes_copied", "commercial_reuse_authorized",
                "independent_ground_truth", "benchmark_ready", "review_gates",
            })
            self.assertFalse(v["benchmark_ready"])
            self.assertFalse(v["commercial_reuse_authorized"])
            self.assertFalse(v["independent_ground_truth"])

    def test_shared_source_does_not_inflate_unique_corpus_size(self):
        doc = sample_ledger()
        doc, new = merge_sources(
            doc, "capturebrief", ["https://www.gao.gov/products/b-160344"],
            "2026-10-23",
        )
        self.assertEqual(new, 0)
        out = build_queue(doc, NOW)
        self.assertEqual(out["unique_public_source_references"], 8)
        self.assertEqual(out["engines"]["capturebrief"]["catalog_source_associations"], 2)
        self.assertEqual(out["engines"]["freightrecovery"]["catalog_source_associations"], 3)

    def test_exact_bytes_verification_and_no_untrusted_fields(self):
        doc = sample_ledger()
        rendered = render_queue(doc, NOW)
        self.assertEqual(rendered, render_queue(doc, NOW))
        self.assertTrue(rendered.endswith("\n"))
        self.assertNotIn("private_customer_name", rendered)
        self.assertNotIn("original_invoice_bytes", rendered)
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "ledger.json"
            target = Path(tmp) / "source_review_queue_v1.json"
            src.write_text(json.dumps(doc), encoding="utf-8")
            first = run(ledger_path=src, output=target, as_of=NOW)
            self.assertEqual(first["source_count"], 8)
            saved = target.read_bytes()
            again = run(ledger_path=src, output=target, verify_only=True)
            self.assertTrue(again["verified"])
            self.assertEqual(saved, target.read_bytes())
            data = json.loads(target.read_text())
            data["commercial_recovery_allowed"] = True
            target.write_text(json.dumps(data, sort_keys=True, indent=2) + "\n")
            with self.assertRaisesRegex(ResearchError, "REVIEW_QUEUE_STALE_OR_CHANGED"):
                run(ledger_path=src, output=target, verify_only=True)
            with self.assertRaisesRegex(ResearchError, "REVIEW_DATE_FUTURE_OR_INVALID"):
                run(ledger_path=src, output=target, as_of=NOW + timedelta(days=60))

    def test_empty_corpus_still_lists_each_engine_evidence_deficit(self):
        out = build_queue(ledger_from([]), NOW)
        self.assertEqual(out["unique_public_source_references"], 0)
        for engine in ENGINES:
            self.assertEqual(out["engines"][engine]["priority_review_queue"], [])
            self.assertGreaterEqual(len(out["engines"][engine]["missing_benchmark_evidence"]), 3)
            self.assertFalse(out["engines"][engine]["commercial_use_approved"])


if __name__ == "__main__":
    unittest.main()
