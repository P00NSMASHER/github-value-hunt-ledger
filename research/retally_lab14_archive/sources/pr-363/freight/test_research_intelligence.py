"""Adversarial quality gates for RETALLY's research-only Lab 14 extension."""
from __future__ import annotations

from copy import deepcopy
from datetime import date
import json
from pathlib import Path
import unittest

from freight.research_intelligence import (
    LANES, canonical_digest, compile_brief, digest, phase3_brief,
    render_html, seed_from_phase3, validate_registry,
)


ROOT = Path(__file__).resolve().parent


def seeded():
    e = json.loads((ROOT / "PHASE3_COMPETITOR_EVIDENCE_2026-10-07.json").read_text())
    m = json.loads((ROOT / "PHASE3_COMPETITIVE_MATRIX_2026-10-07.json").read_text())
    return seed_from_phase3(as_of=date(2026, 10, 10), evidence=e, matrix=m)


class ResearchIntelligenceTests(unittest.TestCase):
    def test_imported_real_repo_research_preserves_unverified_boundary(self):
        report = phase3_brief(as_of=date(2026, 10, 10))
        self.assertEqual(report["status"], "RESEARCH_ONLY_NO_AUTONOMOUS_FETCH")
        self.assertEqual([x["lane"] for x in report["lanes"]], list(LANES))
        self.assertEqual(len(report["lanes"]), 8)
        self.assertGreater(report["source_register_count"], 5)
        self.assertGreaterEqual(report["opposition_findings"], 5)
        self.assertFalse(report["customer_claims_or_payment_execution"])
        self.assertTrue(report["no_independent_truth_certification"])
        self.assertTrue(any(x["state"] == "RESEARCH_QUEUE_ONLY" for x in report["lanes"]))
        self.assertTrue(all(not x["can_publish_as_verified"] for x in report["prioritized_findings"]))
        self.assertTrue(all(x["evidence_status"] in {
            "VENDOR_CLAIM_UNVERIFIED", "INTERNAL_RESEARCH_NOT_INDEPENDENTLY_TESTED"
        } for x in report["prioritized_findings"]))

    def test_hash_digest_is_repeatable_without_run_clock(self):
        r1 = phase3_brief(as_of=date(2026, 10, 10))
        r2 = phase3_brief(as_of=date(2026, 10, 10))
        self.assertEqual(r1, r2)
        self.assertEqual(r1["receipt_sha256"],
                         canonical_digest({k: v for k, v in r1.items() if k != "receipt_sha256"}))

    def test_tampered_source_summary_is_rejected(self):
        data = seeded()
        data["sources"][0]["excerpt"] += " forged outcome"
        errors = validate_registry(data, as_of=date(2026, 10, 10))
        self.assertTrue(any("hash mismatch" in x for x in errors))
        with self.assertRaises(ValueError):
            compile_brief(data, as_of=date(2026, 10, 10))

    def test_credentialed_url_and_http_are_rejected(self):
        for url in ("http://example.com", "https://user:secret@example.com/x",
                    "javascript:alert(1)"):
            with self.subTest(url=url):
                data = seeded()
                data["sources"][0]["url"] = url
                self.assertTrue(any("HTTPS URL" in x for x in validate_registry(
                    data, as_of=date(2026, 10, 10))))

    def test_future_source_capture_and_duplicate_source_id_rejected(self):
        data = seeded()
        data["sources"][0]["captured_at"] = "2027-10-07"
        self.assertTrue(any("future source capture" in x for x in validate_registry(
            data, as_of=date(2026, 10, 10))))
        data = seeded()
        data["sources"].append(deepcopy(data["sources"][0]))
        self.assertTrue(any("duplicate id" in x for x in validate_registry(
            data, as_of=date(2026, 10, 10))))

    def test_stale_sources_are_never_presumed_current(self):
        report = phase3_brief(as_of=date(2027, 2, 1))
        self.assertTrue(all(x["evidence_status"] == "STALE_SOURCE_HOLD"
                            for x in report["prioritized_findings"]))
        self.assertTrue(all(x["state"] in {"SOURCE_FRESHNESS_HOLD", "RESEARCH_QUEUE_ONLY"}
                            for x in report["lanes"]))
        self.assertTrue(report["no_independent_truth_certification"])

    def test_no_automatic_verification_or_source_laundering(self):
        for kind in ("INDEPENDENT_VERIFIED", "CONFIRMED", "FACT"):
            data = seeded()
            data["claims"][0]["classification"] = kind
            self.assertTrue(any("never assert VERIFIED" in x for x in validate_registry(
                data, as_of=date(2026, 10, 10))))
        data = seeded()
        data["claims"][0]["classification"] = "PUBLIC_REPORT"
        self.assertTrue(any("requires independently captured" in x for x in validate_registry(
            data, as_of=date(2026, 10, 10))))
        data = seeded()
        data["claims"][-1]["classification"] = "VENDOR_CLAIM"
        self.assertTrue(any("cannot be laundered" in x for x in validate_registry(
            data, as_of=date(2026, 10, 10))))

    def test_claims_must_have_known_sources_and_proper_ints(self):
        data = seeded()
        data["claims"][0]["source_ids"] = ["fake.source.id"]
        data["claims"][1]["importance"] = True
        failures = validate_registry(data, as_of=date(2026, 10, 10))
        self.assertTrue(any("unknown source reference" in x for x in failures))
        self.assertTrue(any("importance must be integer" in x for x in failures))

    def test_conflicting_public_positions_trigger_review_not_truth(self):
        data = seeded()
        counter = deepcopy(data["claims"][0])
        counter["id"] = "claim.counterevidence.1"
        counter["stance"] = "CHALLENGE"
        counter["statement"] = "Contradictory documented account; requires actual investigation."
        data["claims"].append(counter)
        result = compile_brief(data, as_of=date(2026, 10, 10))
        self.assertIn(counter["issue_key"], result["contested_issues"])
        related = [x for x in result["prioritized_findings"] if x["issue_key"] == counter["issue_key"]]
        self.assertEqual(len(related), 2)
        self.assertTrue(all(x["evidence_status"] == "CONTESTED_REQUIRES_REVIEW" for x in related))
        self.assertTrue(all(not x["can_publish_as_verified"] for x in related))

    def test_escaped_operator_report_and_limited_export(self):
        data = seeded()
        data["claims"][0]["statement"] = "<script>alert('unsafe')</script>"
        result = compile_brief(data, as_of=date(2026, 10, 10))
        html = render_html(result)
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertIn("RETALLY", html)
        self.assertIn("No automated searches performed", html)
        self.assertNotIn("API_KEY", html)

    def test_operator_collected_market_source_enters_public_review_not_fact(self):
        data = seeded()
        excerpt = "A prospective public study requires independent review of its sample."
        sid = "public.market.study.001"
        data["sources"].append({
            "id": sid, "type": "INDEPENDENT_REPORT",
            "url": "https://example.org/market-study",
            "publisher": "Demonstration public source",
            "captured_at": "2026-10-10", "valid_until": "2026-11-10",
            "excerpt": excerpt, "excerpt_sha256": digest(excerpt),
        })
        data["claims"].append({
            "id": "market.study.001", "lane": "market",
            "issue_key": "market-sample-unknown", "subject": "Illustrative study",
            "stance": "CHALLENGE",
            "statement": "The sample may not support a market-wide extrapolation.",
            "classification": "PUBLIC_REPORT", "source_ids": [sid],
            "importance": 4,
            "next_test": "Independently reproduce the dataset and sampling method.",
        })
        r = compile_brief(data, as_of=date(2026, 10, 10))
        market = next(row for row in r["lanes"] if row["lane"] == "market")
        finding = next(row for row in r["prioritized_findings"] if row["id"] == "market.study.001")
        self.assertEqual(market["sourced_observations"], 1)
        self.assertEqual(finding["evidence_status"], "PUBLIC_SOURCE_NOT_FACT_CHECKED")
        self.assertFalse(finding["can_publish_as_verified"])

    def test_no_unauthorized_scope(self):
        data = seeded()
        data["scope"] = "LIVE_CARRIER_COLLECTION"
        self.assertTrue(any("PUBLIC_RESEARCH_ONLY" in x for x in validate_registry(
            data, as_of=date(2026, 10, 10))))


if __name__ == "__main__":
    unittest.main()
