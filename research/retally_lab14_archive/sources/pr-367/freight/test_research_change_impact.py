"""Mission 5: detached capture integrity, source drift and decision dependency tests.

All transport calls are injected mocks. No live public or private network.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timezone
import json
from pathlib import Path
import unittest

from freight.research_source_acquisition import capture, canonical_sha
from freight.research_change_impact import (
    build_refresh_queue, compare_captures, mission5_queue,
    render_html, validate_capture_receipt,
)
from freight.research_public_campaign import campaign_registry
from freight.research_evidence_gate import run_mission


ROOT = Path(__file__).resolve().parent
AS_OF = date(2026, 10, 10)
MANIFEST = json.loads(
    (ROOT / "research/PUBLIC_SOURCE_MANIFEST_20261010.json").read_text(encoding="utf-8")
)


def fake_capture(when_hour: int, *, selected=None,
                 competitor_text="Contingency 20% on eligible recoveries",
                 add_hidden_script=False, failure=False):
    """Deterministic, injected transport; not a verified live HTTP capture."""
    selected = selected or ["recoveraudit.pricing", "nmfta.timeline.2026"]

    def get(url):
        if failure and "recover-audit" in url:
            return 503, url, "text/plain", b"provider unavailable"
        if "recover-audit" in url:
            body = ("<html><body><p>" + competitor_text + "</p>" +
                    ("<script>new-version</script>" if add_hidden_script else "")
                    + "</body></html>").encode()
        else:
            body = b"<html><body><p>Supplement 2026-2 Effective Date December 12, 2026</p></body></html>"
        return 200, url, "text/html", body

    return capture(
        MANIFEST, selected=selected, network_enabled=True,
        transport=get,
        now=datetime(2026, 10, 10, when_hour, 0, tzinfo=timezone.utc),
    )


def recompute(receipt):
    receipt["receipt_sha256"] = canonical_sha({
        k: v for k, v in receipt.items() if k != "receipt_sha256"
    })
    return receipt


def fixtures():
    registry = campaign_registry(as_of=AS_OF)
    _, decisions = run_mission(as_of=AS_OF)
    return registry, decisions


class SourceChangeTests(unittest.TestCase):
    def test_exact_collector_schema_accepts_mock_source_candidates(self):
        receipt = fake_capture(12)
        self.assertEqual(validate_capture_receipt(receipt, MANIFEST, as_of=AS_OF), [])
        self.assertEqual(receipt["fetch_error_count"], 0)
        self.assertTrue(receipt["no_claim_verification"])

    def test_changed_vendor_page_traces_to_claims_and_decisions(self):
        previous = fake_capture(12)
        current = fake_capture(13, competitor_text="Contingency 25% on eligible recoveries")
        registry, decisions = fixtures()
        report = compare_captures(
            before=previous, after=current,
            manifest=MANIFEST, registry=registry,
            decisions=decisions, as_of=AS_OF,
        )
        vendor = next(x for x in report["sources"] if x["source_id"] == "recoveraudit.pricing")
        self.assertEqual(vendor["content_change_status"], "VISIBLE_PREVIEW_CHANGED")
        self.assertTrue(vendor["needs_human_review"])
        self.assertIn("campaign.competitor.price", vendor["dependent_claim_ids"])
        self.assertIn("campaign.economics.offer", vendor["dependent_claim_ids"])
        self.assertIn("M4-03", vendor["affected_decision_ids"])
        self.assertIn("M4-06", vendor["affected_decision_ids"])
        self.assertFalse(vendor["claim_truth_or_falsity_determined"])
        self.assertFalse(vendor["customer_action_authorized"])
        self.assertEqual(report["receipt_sha256"], canonical_sha({
            k: v for k, v in report.items() if k != "receipt_sha256"
        }))

    def test_same_visible_excerpt_with_different_html_is_a_review_candidate(self):
        prev = fake_capture(12)
        new = fake_capture(13, add_hidden_script=True)
        registry, decisions = fixtures()
        report = compare_captures(
            before=prev, after=new, manifest=MANIFEST,
            registry=registry, decisions=decisions, as_of=AS_OF,
        )
        vendor = next(x for x in report["sources"] if x["source_id"] == "recoveraudit.pricing")
        self.assertEqual(vendor["content_change_status"],
                         "RAW_CHANGED_PREVIEW_UNCHANGED")
        self.assertTrue(vendor["needs_human_review"])
        self.assertFalse(vendor["raw_body_reverified_independently"])

    def test_unchanged_snapshot_does_not_claim_fresh_verification(self):
        prev, new = fake_capture(12), fake_capture(13)
        registry, decisions = fixtures()
        report = compare_captures(
            before=prev, after=new, manifest=MANIFEST,
            registry=registry, decisions=decisions, as_of=AS_OF,
        )
        self.assertEqual(report["human_review_sources"], 0)
        self.assertTrue(report["no_claims_automatically_promoted"])
        self.assertFalse(report["any_publisher_authenticity_proven"])
        self.assertEqual(report["status_counts"]["RAW_BODY_UNCHANGED"], 2)
        self.assertEqual(report["status_counts"]["NOT_CHECKED_THIS_RUN"], 11)

    def test_partial_sample_does_not_report_unselected_as_unavailable(self):
        prev = fake_capture(12, selected=["recoveraudit.pricing"])
        new = fake_capture(13, selected=["nmfta.timeline.2026"])
        registry, decisions = fixtures()
        report = compare_captures(
            before=prev, after=new, manifest=MANIFEST,
            registry=registry, decisions=decisions, as_of=AS_OF,
        )
        unobserved = next(x for x in report["sources"] if x["source_id"] == "recoveraudit.pricing")
        self.assertEqual(unobserved["content_change_status"], "NOT_CHECKED_THIS_RUN")
        self.assertFalse(unobserved["needs_human_review"])
        new_item = next(x for x in report["sources"] if x["source_id"] == "nmfta.timeline.2026")
        self.assertEqual(new_item["content_change_status"], "BASELINE_CAPTURE_UNREVIEWED")

    def test_fetch_failure_requires_review_without_inventing_source_change(self):
        prev = fake_capture(12)
        new = fake_capture(13, failure=True)
        registry, decisions = fixtures()
        report = compare_captures(
            before=prev, after=new, manifest=MANIFEST,
            registry=registry, decisions=decisions, as_of=AS_OF,
        )
        candidate = next(x for x in report["sources"] if x["source_id"] == "recoveraudit.pricing")
        self.assertEqual(candidate["content_change_status"], "SOURCE_FETCH_FAILED_REVIEW")
        self.assertTrue(candidate["needs_human_review"])
        self.assertFalse(candidate["claim_truth_or_falsity_determined"])

    def test_recovery_after_prior_failure_is_not_verified_success(self):
        prev = fake_capture(12, failure=True)
        new = fake_capture(13)
        registry, decisions = fixtures()
        report = compare_captures(
            before=prev, after=new, manifest=MANIFEST,
            registry=registry, decisions=decisions, as_of=AS_OF,
        )
        candidate = next(x for x in report["sources"] if x["source_id"] == "recoveraudit.pricing")
        self.assertEqual(candidate["content_change_status"], "SOURCE_REAPPEARED_UNREVIEWED")
        self.assertTrue(candidate["needs_human_review"])

    def test_initial_run_is_unreviewed_baseline_not_independent_fact(self):
        registry, decisions = fixtures()
        report = compare_captures(
            before=None, after=fake_capture(12),
            manifest=MANIFEST, registry=registry, decisions=decisions, as_of=AS_OF,
        )
        self.assertTrue(report["baseline_supplied"] is False)
        self.assertEqual(report["human_review_sources"], 2)
        self.assertEqual(report["status_counts"]["BASELINE_CAPTURE_UNREVIEWED"], 2)

    def test_tampered_excerpt_fails_even_with_forged_new_top_receipt(self):
        receipt = fake_capture(12)
        forged = deepcopy(receipt)
        forged["captures"][0]["preview_excerpt"] += " Fake citation"
        recompute(forged)
        errors = validate_capture_receipt(forged, MANIFEST, as_of=AS_OF)
        self.assertTrue(any("PREVIEW_DIGEST_MISMATCH" in x for x in errors))
        with self.assertRaisesRegex(ValueError, "INVALID_CAPTURE_COMPARISON"):
            compare_captures(before=None, after=forged, manifest=MANIFEST,
                             registry=fixtures()[0], decisions=fixtures()[1],
                             as_of=AS_OF)

    def test_changed_raw_digest_without_original_body_cannot_prove_real_change(self):
        receipt = fake_capture(12)
        forged = deepcopy(receipt)
        forged["captures"][0]["raw_body_sha256"] = "a" * 64
        recompute(forged)
        # Detached output cannot validate bytes it deliberately did not save.
        self.assertEqual(validate_capture_receipt(forged, MANIFEST, as_of=AS_OF), [])
        self.assertFalse(forged["captures"][0]["publisher_content_truth_verified"])
        registry, decisions = fixtures()
        compare = compare_captures(before=None, after=forged,
                                   manifest=MANIFEST, registry=registry,
                                   decisions=decisions, as_of=AS_OF)
        self.assertFalse(compare["any_publisher_authenticity_proven"])

    def test_forged_approval_and_extra_truth_field_are_rejected(self):
        for change in (
            lambda r: r["captures"][0].update({"claim_import_authorized": True}),
            lambda r: r["captures"][0].update({"publisher_content_truth_verified": True}),
            lambda r: r["captures"][0].update({"independently_verified": True}),
            lambda r: r.update({"externally_certified": True}),
        ):
            receipt = fake_capture(12)
            change(receipt)
            recompute(receipt)
            self.assertTrue(validate_capture_receipt(receipt, MANIFEST, as_of=AS_OF))

    def test_changed_source_id_url_and_timestamp_fail(self):
        cases = [
            ("id", "unapproved.source"),
            ("url", "https://www.bts.gov/faf"),
            ("publisher", "Forged official authority"),
            ("captured_at_utc", "2027-01-01T00:00:00+00:00"),
            ("captured_at_utc", "2026-10-10T12:00:00"),
        ]
        for key, value in cases:
            with self.subTest(key=key, value=value):
                receipt = fake_capture(12)
                receipt["captures"][0][key] = value
                recompute(receipt)
                self.assertTrue(validate_capture_receipt(receipt, MANIFEST, as_of=AS_OF))

    def test_nonmonotonic_capture_order_rejected(self):
        registry, decisions = fixtures()
        for before, after in ((fake_capture(13), fake_capture(12)),
                              (fake_capture(12), fake_capture(12))):
            with self.assertRaisesRegex(ValueError, "NON_MONOTONIC_CAPTURE_TIMESTAMPS"):
                compare_captures(before=before, after=after,
                                 manifest=MANIFEST, registry=registry,
                                 decisions=decisions, as_of=AS_OF)

    def test_invalid_failure_census_and_resuscitated_hash_fail(self):
        bad = fake_capture(12, failure=True)
        bad["fetch_error_count"] = 0
        recompute(bad)
        self.assertIn("FETCH_ERROR_CENSUS_MISMATCH",
                      validate_capture_receipt(bad, MANIFEST, as_of=AS_OF))
        bad = fake_capture(12)
        bad["receipt_sha256"] = "0" * 64
        self.assertIn("RECEIPT_TAMPERED",
                      validate_capture_receipt(bad, MANIFEST, as_of=AS_OF))

    def test_refresh_queue_is_prioritized_and_never_verifies(self):
        queue = mission5_queue(as_of=AS_OF)
        self.assertGreater(queue["source_count"], 12)
        self.assertEqual(queue["expired_count"], 0)
        self.assertFalse(queue["automatic_fetch_or_schedule"])
        self.assertFalse(queue["any_sources_independently_fact_checked"])
        ranks = [row["source_priority_ordinal"] for row in queue["review_queue"]]
        self.assertEqual(ranks, sorted(ranks, reverse=True))
        self.assertTrue(all(row["review_required_before_external_use"]
                            for row in queue["review_queue"]))
        self.assertTrue(all(not row["independently_verified"]
                            for row in queue["review_queue"]))
        self.assertEqual(queue["receipt_sha256"], canonical_sha({
            k: v for k, v in queue.items() if k != "receipt_sha256"
        }))

    def test_expiry_never_auto_renews_even_after_unmodified_capture(self):
        now = date(2027, 2, 1)
        queue = mission5_queue(as_of=now)
        self.assertGreater(queue["expired_count"], 0)
        expired = next(x for x in queue["review_queue"] if x["source_id"] ==
                       "20261010.nmfta.timeline.2026")
        self.assertEqual(expired["source_review_state"], "EXPIRED_SOURCE_HOLD")
        self.assertFalse(expired["independently_verified"])
        # An unchanged page today would not refresh its old source authorization.
        registry = campaign_registry(as_of=now)
        _, decisions = run_mission(as_of=now)
        receipt_old = fake_capture(12)
        receipt_new = fake_capture(13)
        comparison = compare_captures(
            before=receipt_old, after=receipt_new,
            manifest=MANIFEST, registry=registry, decisions=decisions,
            as_of=now,
        )
        nmfta = next(x for x in comparison["sources"] if x["source_id"] ==
                     "nmfta.timeline.2026")
        self.assertTrue(nmfta["expired_source_hold"])
        self.assertTrue(nmfta["needs_human_review"])

    def test_html_escapes_untrusted_names_and_source_statuses(self):
        queue = mission5_queue(as_of=AS_OF)
        fake = deepcopy(queue)
        fake["review_queue"][0]["publisher"] = '<script>alert("bad")</script>'
        body = render_html(fake)
        self.assertNotIn("<script>", body)
        self.assertIn("&lt;script&gt;", body)
        self.assertIn("Source Change Radar", body)

    def test_reproducible_queue_has_no_phantom_changes(self):
        a = mission5_queue(as_of=AS_OF)
        b = mission5_queue(as_of=AS_OF)
        self.assertEqual(a, b)
        self.assertEqual(a["scope"], "READ_ONLY_MANUAL_REFRESH_BACKLOG")
        self.assertFalse(a["external_actions_allowed"])


if __name__ == "__main__":
    unittest.main()
