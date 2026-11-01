"""Adversarial acceptance for Mission 4 evidence anchoring and opposition."""
from __future__ import annotations

from copy import deepcopy
from datetime import date
import json
from pathlib import Path
import unittest

from freight.research_evidence_gate import (
    canon_hash, decision_register, render_html, review_evidence, run_mission,
    validate_anchor_book,
)
from freight.research_public_campaign import campaign_registry


ROOT = Path(__file__).resolve().parent
DATE = date(2026, 10, 10)


def fixtures():
    registry = campaign_registry(as_of=DATE)
    book = json.loads((ROOT/"research/SOURCE_ANCHORS_20261010.json").read_text())
    return registry, book


class EvidenceGateTests(unittest.TestCase):
    def test_source_quotes_are_bounded_and_referenced_without_truth_promotion(self):
        registry, book = fixtures()
        self.assertEqual(len(book["anchors"]), 14)
        self.assertEqual(validate_anchor_book(book, registry, as_of=DATE), [])
        result = review_evidence(registry, book, as_of=DATE)
        self.assertEqual(result["anchor_count"], 14)
        self.assertEqual(result["anchored_claim_count"], 18)
        self.assertGreater(result["claim_count"], result["anchored_claim_count"])
        self.assertTrue(all(a["vendor_or_internal_claim_verified"] is False
                            for a in result["assessments"]))
        self.assertTrue(all(a["public_marketing_permitted"] is False
                            for a in result["assessments"]))
        self.assertEqual(result["receipt_sha256"], canon_hash(
            {k: v for k, v in result.items() if k != "receipt_sha256"}))

    def test_future_nmfc_supplement_cannot_be_in_force_in_october(self):
        registry, book = fixtures()
        result = review_evidence(registry, book, as_of=DATE)
        for cid in ("campaign.carrier.timeline", "campaign.strategy.classification"):
            row = next(a for a in result["assessments"] if a["claim_id"] == cid)
            self.assertEqual(row["review_status"], "FUTURE_EFFECTIVE_RULE_HOLD")
            self.assertFalse(row["independent_real_world_proof"])

    def test_search_result_cannot_be_demoted_to_direct_authority(self):
        registry, book = fixtures()
        result = review_evidence(registry, book, as_of=DATE)
        for cid in ("campaign.opposition.own", "campaign.carrier.billcontest"):
            row = next(a for a in result["assessments"] if a["claim_id"] == cid)
            self.assertEqual(row["review_status"], "SEARCH_SNIPPET_ONLY_RECHECK")
        book = deepcopy(book)
        target = next(a for a in book["anchors"] if a["id"] == "source.usc.13710.window")
        target["support_scope"] = "DIRECT_SCOPE"
        self.assertTrue(any("search snippet cannot" in x for x in
                            validate_anchor_book(book, registry, as_of=DATE)))

    def test_current_codification_observed_but_legal_applicability_unproven(self):
        registry, book = fixtures()
        result = review_evidence(registry, book, as_of=DATE)
        row = next(a for a in result["assessments"]
                   if a["claim_id"] == "campaign.carrier.response")
        self.assertEqual(row["review_status"], "CURRENT_ECFR_TEXT_OBSERVED_LEGAL_REVIEW_PENDING")
        self.assertEqual(row["current_codification_as_of"], "2026-10-01")
        self.assertFalse(row["client_specific_legal_applicability_established"])
        self.assertFalse(row["public_marketing_permitted"])
        self.assertIn("source.govinfo.3788.historical", row["source_quote_ids"])
        self.assertIn("source.ecfr.3788.current", row["source_quote_ids"])

    def test_current_codification_cannot_be_forged_or_backdated(self):
        registry, book = fixtures()
        original = next(a for a in book["anchors"] if a["id"] == "source.ecfr.3788.current")
        for key, wrong in (
            ("regulatory_applicability_established", True),
            ("codification_as_of", "2026-10-11"),
            ("method", "SEARCH_RESULT_ONLY"),
            ("support_scope", "HISTORICAL_TEXT"),
        ):
            modified = deepcopy(book)
            anchor = next(a for a in modified["anchors"] if a["id"] == original["id"])
            anchor[key] = wrong
            errors = validate_anchor_book(modified, registry, as_of=DATE)
            self.assertTrue(errors, f"{key} was not rejected")
            with self.assertRaises(ValueError):
                review_evidence(registry, modified, as_of=DATE)

    def test_current_ecfr_cannot_be_silently_replaced_by_historical_anchor(self):
        registry, book = fixtures()
        modified = deepcopy(book)
        modified["anchors"] = [a for a in modified["anchors"]
                               if a["id"] != "source.ecfr.3788.current"]
        result = review_evidence(registry, modified, as_of=DATE)
        row = next(a for a in result["assessments"]
                   if a["claim_id"] == "campaign.carrier.response")
        self.assertEqual(row["review_status"], "CONTEXT_OR_HISTORICAL_REVIEW")

    def test_vendor_pricing_and_benchmark_are_not_independent_proof(self):
        registry, book = fixtures()
        result = review_evidence(registry, book, as_of=DATE)
        for cid in ("campaign.competitor.price", "campaign.economics.offer",
                    "campaign.competitor.loop", "campaign.technology.benchmark"):
            row = next(a for a in result["assessments"] if a["claim_id"] == cid)
            self.assertEqual(row["classification"], "VENDOR_CLAIM")
            self.assertFalse(row["vendor_or_internal_claim_verified"])
            self.assertFalse(row["public_marketing_permitted"])

    def test_tampered_quote_fails_closed_even_when_normalized_summary_is_unchanged(self):
        registry, book = fixtures()
        bad = deepcopy(book)
        bad["anchors"][0]["quote"] += " someone invented this"
        failures = validate_anchor_book(bad, registry, as_of=DATE)
        self.assertTrue(any("source quote checksum mismatch" in x for x in failures))
        with self.assertRaisesRegex(ValueError, "INVALID_SOURCE_ANCHORS"):
            review_evidence(registry, bad, as_of=DATE)

    def test_mismatched_page_url_and_cross_claim_reference_rejected(self):
        registry, book = fixtures()
        bad = deepcopy(book)
        bad["anchors"][0]["url"] = "https://www.bts.gov/different-document"
        self.assertTrue(any("source URL mismatched" in x for x in
                            validate_anchor_book(bad, registry, as_of=DATE)))
        bad = deepcopy(book)
        bad["anchors"][0]["claim_ids"].append("campaign.competitor.price")
        self.assertTrue(any("lacks source binding" in x for x in
                            validate_anchor_book(bad, registry, as_of=DATE)))

    def test_quotes_cannot_unilaterally_approve_external_truth_or_money(self):
        registry, book = fixtures()
        bad = deepcopy(book)
        bad["anchors"][0]["verified_external_fact"] = True
        self.assertTrue(any("never promote" in x for x in
                            validate_anchor_book(bad, registry, as_of=DATE)))
        bad = deepcopy(book)
        bad["anchors"][0]["customer_action_authorized"] = True
        self.assertTrue(any("cannot authorize customer action" in x for x in
                            validate_anchor_book(bad, registry, as_of=DATE)))

    def test_future_effective_date_forgery_cannot_be_used_as_current_rule(self):
        registry, book = fixtures()
        bad = deepcopy(book)
        target = next(x for x in bad["anchors"] if x["id"] == "source.nmfta.future.2026")
        target["represents_current_rule"] = True
        self.assertTrue(any("future rule misrepresented" in x for x in
                            validate_anchor_book(bad, registry, as_of=DATE)))

    def test_literal_numeric_markers_must_actually_appear_in_quote(self):
        registry, book = fixtures()
        bad = deepcopy(book)
        target = next(x for x in bad["anchors"] if x["id"] == "source.loop.benchmark.claim")
        target["literal_markers"].append("99.9%")
        self.assertTrue(any("claimed literal absent" in x for x in
                            validate_anchor_book(bad, registry, as_of=DATE)))

    def test_anchor_constraints_reject_duplicates_and_unsupported_excerpt(self):
        registry, book = fixtures()
        bad = deepcopy(book)
        bad["anchors"].append(deepcopy(bad["anchors"][0]))
        self.assertTrue(any("duplicate id" in x for x in
                            validate_anchor_book(bad, registry, as_of=DATE)))
        bad = deepcopy(book)
        bad["anchors"][0]["quote"] = ("much " * 27).strip()
        self.assertTrue(any("25-word" in x for x in
                            validate_anchor_book(bad, registry, as_of=DATE)))

    def test_decisions_are_source_linked_ranked_and_explicitly_research_only(self):
        registry, book = fixtures()
        proof = review_evidence(registry, book, as_of=DATE)
        decisions = decision_register(registry, proof)
        self.assertEqual(len(decisions["decisions"]), 6)
        self.assertEqual(
            decisions["evidence_receipt_sha256"], proof["receipt_sha256"])
        self.assertEqual(decisions["receipt_sha256"], canon_hash(
            {k:v for k,v in decisions.items() if k != "receipt_sha256"}))
        scores = [x["priority_score_ordinal_not_forecast"] for x in decisions["decisions"]]
        self.assertEqual(scores, sorted(scores, reverse=True))
        self.assertTrue(all(x["external_actions_allowed"] is False
                            for x in decisions["decisions"]))
        self.assertTrue(all(x["claim_ids"] for x in decisions["decisions"]))
        self.assertTrue(all(x["recommended_test"] for x in decisions["decisions"]))

    def test_without_sources_decision_is_blocked_not_made_up(self):
        registry, book = fixtures()
        proof = review_evidence(registry, book, as_of=DATE)
        del registry["claims"][-1]
        with self.assertRaisesRegex(ValueError, "missing required evidence dependency"):
            decision_register(registry, proof)

    def test_render_does_not_execute_adversarial_material(self):
        proof, decisions = run_mission(as_of=DATE)
        dirty = deepcopy(decisions)
        dirty["decisions"][0]["subject"] = '<script>alert("unsafe")</script>'
        html = render_html(proof, dirty)
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertIn("What could prove us wrong?", html)
        self.assertIn("INTERNAL_DESK_RESEARCH_ONLY", str(dirty))

    def test_reproducible_replay_and_stale_quote_hold(self):
        proof_a, decisions_a = run_mission(as_of=DATE)
        proof_b, decisions_b = run_mission(as_of=DATE)
        self.assertEqual(proof_a, proof_b)
        self.assertEqual(decisions_a, decisions_b)
        stale, _ = run_mission(as_of=date(2027, 2, 1))
        self.assertTrue(any(x["review_status"] == "EXPIRED_SOURCE_HOLD"
                            for x in stale["assessments"]))


if __name__ == "__main__":
    unittest.main()
