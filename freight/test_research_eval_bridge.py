"""Offline adversarial tests for research-lab -> FreightRecovery evaluation feed."""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
import tempfile
import unittest
from pathlib import Path

from freight import lab15_acquisition as legacy
from freight import lab15_evidence_harvester as harvested
from freight import unified_research_lab as unified
from freight.research_eval_bridge import (
    FeedError, _publishable_locator, _reference_urls, build_feed, digest,
    evaluate_feed, validate_feed, verify_against_sources,
)

GAO = "https://www.gao.gov/products/b-160344"
SEC = "https://www.sec.gov/Archives/edgar/data/1507615/000150761511000033/exhibit101.htm"
NOVEL = "https://zenodo.org/records/100001"


def fixture_sources():
    master = unified.ledger_from([
        unified.source_record(GAO, "freightrecovery", "2026-10-22"),
        unified.source_record(SEC, "freightrecovery", "2026-10-22"),
        unified.source_record(NOVEL, "freightrecovery", "2026-10-23"),
        unified.source_record("https://sam.gov/opportunities", "capturebrief", "2026-10-22"),
    ])
    old = {
        "schema_version": 1,
        "records": [legacy.source_record(
            GAO, "GAO_DECISION", "2026-10-17T15:38:43Z", title="historical claim"
        )],
    }
    harvest = harvested.blank_ledger()
    harvest["leads"] = [
        harvested.new_lead(GAO, "legal reference", "previously_observed_public_url",
                           "2026-10-18")
    ]
    harvest["digest_sha256"] = harvested.digest({
        key: harvest[key] for key in harvest if key != "digest_sha256"
    })
    return master, old, harvest


class ResearchEvaluationBridgeTests(unittest.TestCase):
    def test_three_source_ledgers_dedupe_and_preserve_first_seen(self):
        source = fixture_sources()
        feed = build_feed(*source)
        validate_feed(feed)
        self.assertEqual(feed["candidate_count"], 3)
        by_url = {x["url"]: x for x in feed["candidates"]}
        self.assertEqual(by_url[GAO]["source_ledgers"],
                         ["lab15_acquisition", "lab15_harvester", "unified"])
        self.assertEqual(by_url[GAO]["first_seen"], "2026-10-17")
        self.assertEqual(by_url[GAO]["reference_case_ids"], ["public:GAO_B160344"])
        self.assertIn("v1:TESORO_2011_TRUCKING", by_url[SEC]["reference_case_ids"])
        self.assertEqual(by_url[NOVEL]["reference_case_ids"], [])
        self.assertNotIn("https://sam.gov/opportunities", by_url)
        self.assertEqual(feed["candidates_sha256"], digest(feed["candidates"]))

    def test_no_private_invoice_roots_enter_fixed_reference_map(self):
        refs, _ = _reference_urls()
        self.assertNotIn("https://extranet4.biggexpress.com/", refs)
        self.assertNotIn("https://cw.shipandsave.com/", refs)

    def test_newly_discovered_source_is_review_only_and_real_engine_replayed(self):
        feed = build_feed(*fixture_sources())
        receipt = evaluate_feed(feed)
        self.assertEqual(receipt["discovered_candidate_sources"], 3)
        self.assertEqual(receipt["references_matched_to_existing_fixed_cases"], 2)
        self.assertEqual(receipt["unmatched_source_candidates_waiting_for_adjudication"], 1)
        self.assertEqual(receipt["fixed_v1_real_world_cases_replayed"], 9)
        self.assertEqual(receipt["prior_official_source_case_families_replayed"], 5)
        self.assertEqual(receipt["new_source_numeric_claims_evaluated"], 0)
        self.assertEqual(receipt["verified_new_customer_recovery_cents"], 0)
        self.assertIsNone(receipt["real_precision"])
        self.assertFalse(receipt["customer_data_release_authorized"])

    def test_source_hash_is_metadata_only_not_document_proof(self):
        feed = build_feed(*fixture_sources())
        for candidate in feed["candidates"]:
            self.assertIsNone(candidate["original_source_bytes_sha256"])
            self.assertEqual(candidate["status"], "RIGHTS_AND_INDEPENDENT_EVIDENCE_PENDING")
            self.assertFalse(candidate["customer_invoice_ground_truth"])
            self.assertFalse(candidate["independent_payment_verified"])
            self.assertFalse(candidate["automatic_recovery_authorized"])
            self.assertEqual(candidate["id"], sha256(
                candidate["url"].encode("utf-8")).hexdigest())

    def test_adversarial_rehash_cannot_promote_claim_or_commercial_rights(self):
        for key, new_value in (
            ("automatic_recovery_authorized", True),
            ("independent_payment_verified", True),
            ("commercial_use_authorized", True),
            ("customer_invoice_ground_truth", True),
            ("original_source_bytes_sha256", "a" * 64),
            ("status", "ADJUDICATED"),
        ):
            with self.subTest(key=key):
                feed = build_feed(*fixture_sources())
                feed["candidates"][0][key] = new_value
                feed["candidates_sha256"] = digest(feed["candidates"])
                with self.assertRaises(FeedError):
                    validate_feed(feed)

    def test_untrusted_publisher_locator_and_claimed_reference_rejected(self):
        source = fixture_sources()
        for field, changed in (
            ("url", "https://example.org/malicious"),
            ("reference_case_ids", ["v1:BIG_G_2026_FACE"]),
            ("publisher_host", "internal.example"),
        ):
            with self.subTest(field=field):
                feed = build_feed(*source)
                feed["candidates"][0][field] = changed
                feed["candidates_sha256"] = digest(feed["candidates"])
                with self.assertRaises(FeedError):
                    validate_feed(feed)

    def test_structural_mutations_and_duplicate_ids_rejected(self):
        source = fixture_sources()
        bad = build_feed(*source)
        bad["candidates"].append(deepcopy(bad["candidates"][0]))
        bad["candidate_count"] += 1
        bad["candidates_sha256"] = digest(bad["candidates"])
        with self.assertRaises(FeedError):
            validate_feed(bad)
        for attr, value in (("recovery_claims_authorized", True),
                            ("independent_new_truth_cases", 1),
                            ("real_customer_cash_recovered_cents", 1),
                            ("original_customer_documents_saved", True)):
            with self.subTest(attr=attr):
                feed = build_feed(*source)
                feed[attr] = value
                with self.assertRaises(FeedError):
                    validate_feed(feed)

    def test_source_modification_detected_even_when_candidate_snapshot_rehashed(self):
        master, old, harvest = fixture_sources()
        frozen = build_feed(master, old, harvest)
        current = unified.ledger_from([
            *master["entries"],
            unified.source_record(
                "https://github.com/example/freight-sample",
                "freightrecovery", "2026-10-23"
            ),
        ])
        with self.assertRaisesRegex(FeedError, "NOT_DERIVED"):
            verify_against_sources(frozen, current, old, harvest)

    def test_tampered_upstream_ledger_rejected_before_any_claim(self):
        master, old, harvest = fixture_sources()
        old["records"][0]["commercial_test_approved"] = True
        with self.assertRaises(legacy.EvidenceError):
            build_feed(master, old, harvest)
        master, old, harvest = fixture_sources()
        harvest["leads"][0]["actual_cash_recovery_verified"] = True
        harvest["digest_sha256"] = harvested.digest({
            k: harvest[k] for k in harvest if k != "digest_sha256"
        })
        with self.assertRaises(harvested.Rejected):
            build_feed(master, old, harvest)

    def test_unsafe_legacy_document_urls_are_hashed_without_republishing(self):
        self.assertIsNone(_publishable_locator(
            "https://dataverse.harvard.edu/dataset.xhtml?persistentId=doi%3Asecret"
        ))
        self.assertIsNone(_publishable_locator(
            "https://document.epiq11.com/customer-sensitive/document.pdf"
        ))
        self.assertIsNone(_publishable_locator(
            "https://catalog.data.gov/dataset/something?token=private"
        ))
        self.assertIsNone(_publishable_locator("http://127.0.0.1/private"))

    def test_output_does_not_duplicate_legacy_titles_or_original_fingerprints(self):
        master, old, harvest = fixture_sources()
        old["records"][0]["title"] = "real customer name that stays in the legacy ledger"
        old["records"][0]["sha256"] = "a" * 64
        old["records"][0]["bytes_seen"] = 1000
        old["records"][0]["state"] = "PUBLIC_SOURCE_FINGERPRINTED"
        document = build_feed(master, old, harvest)
        output = json.dumps(document)
        self.assertNotIn("real customer name", output)
        self.assertNotIn("a" * 64, output)
        self.assertNotIn("bytes_seen", output)
        self.assertNotIn("title", output)

    def test_empty_ledgers_produce_no_invented_benchmark_evidence(self):
        feed = build_feed(
            unified.ledger_from([]),
            {"schema_version": 1, "records": []},
            harvested.blank_ledger(),
        )
        self.assertEqual(feed["candidate_count"], 0)
        self.assertEqual(feed["candidates"], [])
        self.assertEqual(evaluate_feed(feed)["verified_new_customer_recovery_cents"], 0)

    def test_json_round_trip_is_deterministic(self):
        source = fixture_sources()
        feed = build_feed(*source)
        with tempfile.TemporaryDirectory() as d:
            file = Path(d) / "queue.json"
            file.write_text(json.dumps(feed, sort_keys=True, indent=2) + "\n")
            loaded = json.loads(file.read_text())
            self.assertEqual(loaded, feed)
            verify_against_sources(loaded, *source)


if __name__ == "__main__":
    unittest.main()
