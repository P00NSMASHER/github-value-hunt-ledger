"""Adversarial checks for the first manually reviewed eight-lane public campaign."""
from __future__ import annotations

from datetime import date
import json
from pathlib import Path
import tempfile
import unittest

from freight.research_intelligence import compile_brief
from freight.research_public_campaign import (
    CAMPAIGN_DATE, CLAIMS, SOURCE_META, campaign_brief, campaign_registry,
)

ROOT = Path(__file__).parent


class PublicResearchCampaignTests(unittest.TestCase):
    def test_campaign_reuses_prior_comparison_and_sources_all_eight_lanes(self):
        registry = campaign_registry(as_of=date(2026, 10, 10))
        results = campaign_brief(as_of=date(2026, 10, 10))
        self.assertEqual(len(SOURCE_META), 12)
        self.assertEqual(len(CLAIMS), 18)
        self.assertEqual(len(results["lanes"]), 8)
        self.assertTrue(all(x["sourced_observations"] > 0 for x in results["lanes"]))
        self.assertEqual(len(registry["sources"]), results["source_register_count"])
        self.assertEqual(len(registry["claims"]), results["claim_count"])
        self.assertTrue(any(x["id"].startswith("claim.trax") for x in registry["claims"]))
        self.assertTrue(any(x["id"] == "campaign.market.cfs" for x in registry["claims"]))
        self.assertTrue(all(x["can_publish_as_verified"] is False for x in results["prioritized_findings"]))

    def test_competitor_pricing_dispute_is_review_required_not_automatic_verdict(self):
        results = campaign_brief(as_of=date(2026, 10, 10))
        self.assertIn("retally:pricing:clarity", results["contested_issues"])
        rows = [x for x in results["prioritized_findings"]
                if x["issue_key"] == "retally:pricing:clarity"]
        self.assertEqual(len(rows), 2)
        self.assertEqual({x["stance"] for x in rows}, {"SUPPORT", "CHALLENGE"})
        self.assertEqual({x["evidence_status"] for x in rows},
                         {"CONTESTED_REQUIRES_REVIEW"})

    def test_future_supplement_is_not_silently_active(self):
        registry = campaign_registry(as_of=date(2026, 10, 10))
        row = next(x for x in registry["claims"] if x["id"] == "campaign.carrier.timeline")
        self.assertIn("scheduled", row["statement"])
        self.assertIn("December 12, 2026", row["statement"])
        self.assertIn("effective date", row["next_test"])

    def test_limited_federal_claim_does_not_assert_universal_deadline(self):
        registry = campaign_registry(as_of=date(2026, 10, 10))
        dispute = next(x for x in registry["claims"] if x["id"] == "campaign.carrier.billcontest")
        self.assertIn("covered motor-carrier", dispute["statement"])
        self.assertIn("counsel", dispute["next_test"].lower())
        response = next(x for x in registry["claims"] if x["id"] == "campaign.carrier.response")
        self.assertIn("2018 published text", response["statement"])
        self.assertIn("contractual exceptions", response["next_test"])
        source = next(x for x in registry["sources"] if x["id"] == "20261010.govinfo.3788")
        self.assertIn("govinfo.gov", source["url"])
        self.assertEqual(source["published_at"], "2018-04-16")

    def test_vendor_benchmarks_and_fees_are_not_market_facts(self):
        result = campaign_brief(as_of=date(2026, 10, 10))
        for target in ("campaign.competitor.price", "campaign.competitor.loop",
                       "campaign.economics.offer", "campaign.technology.benchmark"):
            row = next(x for x in result["prioritized_findings"] if x["id"] == target)
            self.assertEqual(row["classification"], "VENDOR_CLAIM")
            self.assertEqual(row["evidence_status"], "VENDOR_CLAIM_UNVERIFIED")
            self.assertFalse(row["customer_or_financial_authority"])

    def test_expired_carrier_changes_fall_to_hold(self):
        result = campaign_brief(as_of=date(2027, 1, 12))
        self.assertTrue(any(x["evidence_status"] in {
            "STALE_SOURCE_HOLD", "STALE_AND_CONTESTED_HOLD",
        } for x in result["prioritized_findings"]))
        target = next(x for x in result["prioritized_findings"]
                      if x["id"] == "campaign.carrier.timeline")
        self.assertEqual(target["evidence_status"], "STALE_SOURCE_HOLD")
        self.assertFalse(target["can_publish_as_verified"])

    def test_manifest_drift_blocks_source_import(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "research").mkdir()
            for name in ("PHASE3_COMPETITOR_EVIDENCE_2026-10-07.json",
                         "PHASE3_COMPETITIVE_MATRIX_2026-10-07.json"):
                (root / name).write_bytes((ROOT / name).read_bytes())
            source = json.loads(
                (ROOT / "research/PUBLIC_SOURCE_MANIFEST_20261010.json").read_text())
            source["sources"].pop()
            (root / "research/PUBLIC_SOURCE_MANIFEST_20261010.json").write_text(
                json.dumps(source), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "PUBLIC_MANIFEST_SOURCE_SET_MISMATCH"):
                campaign_registry(as_of=date(2026, 10, 10), root=root)

    def test_same_campaign_is_replayable_without_network(self):
        a = campaign_brief(as_of=date(2026, 10, 10))
        b = campaign_brief(as_of=date(2026, 10, 10))
        self.assertEqual(a, b)
        self.assertEqual(len(a["receipt_sha256"]), 64)
        self.assertTrue(a["no_independent_truth_certification"])
        self.assertFalse(a["customer_claims_or_payment_execution"])


if __name__ == "__main__":
    unittest.main()
