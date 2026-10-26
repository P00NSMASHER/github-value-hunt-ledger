"""Proof that autonomous discovery feeds freight tests without inventing truth."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest

from freight.lab15_acquisition import source_record as evidence_record
from freight.lab15_evidence_harvester import (
    blank_ledger, digest as legacy_digest,
    new_lead,
)
from freight.real_world_eval_v1 import load_manifest, validate_manifest
from freight.research_eval_bridge import (
    MAX_FEED_ROWS, VERSION, build_feed, read_inputs, run as bridge_run,
    synthetic_proof_gate, validate_feed,
)
from freight.unified_research_lab import (
    ResearchError, digest, ledger_from, merge_sources, run, source_record,
)

NOW = datetime(2026, 10, 23, 0, 0, tzinfo=timezone.utc)
GAO = "https://www.gao.gov/products/b-160344"
SEC = "https://www.sec.gov/Archives/edgar/data/1507615/000150761511000033/exhibit101.htm"


def legacy_evidence(rows=()):
    return {"schema_version": 1, "records": list(rows)}


def legacy_candidates(rows=()):
    base = {"schema_version": 1, "lab": 15,
            "scope": "PUBLIC_METADATA_ONLY_NO_CUSTOMER_DOCUMENTS",
            "leads": list(rows)}
    return {**base, "digest_sha256": legacy_digest(base)}


def sample():
    doc = ledger_from([])
    doc, _ = merge_sources(doc, "freightrecovery",
                           [GAO, SEC, "https://catalog.data.gov/dataset/freight-invoice-example"],
                           "2026-10-22")
    doc, _ = merge_sources(doc, "permitplate",
                           ["https://data.cityofnewyork.us/d/43nn-pn8j"],
                           "2026-10-22")
    legacy = legacy_evidence([
        evidence_record(GAO, "GAO_DECISION", "2026-10-17T00:00:00Z"),
        evidence_record("https://psc.ky.gov/Case/ViewCaseFilings/2024-00200",
                        "PUBLIC_REGULATORY_EXHIBIT", "2026-10-17T00:00:00Z"),
    ])
    candidates = legacy_candidates([
        new_lead("https://github.com/demo/freight-invoices", "Public freight invoices",
                 "github", "2026-10-19"),
    ])
    return doc, legacy, candidates


class UnifiedEvaluationFeedTests(unittest.TestCase):
    def test_frozen_v1_anchors_stay_distinct_from_new_unadjudicated_sources(self):
        manifest = load_manifest()
        self.assertEqual(len(validate_manifest(manifest)), 9)
        doc, evidence, candidates = sample()
        feed = build_feed(doc, evidence, candidates, manifest)
        self.assertEqual(feed["feed_version"], VERSION)
        self.assertEqual(feed["frozen_v1_historical_cases"], 9)
        self.assertEqual(feed["frozen_v1_official_source_matches"], 1)  # SEC matched; GAO is legacy corpus
        self.assertEqual(feed["source_pointers_total"], 5)
        self.assertEqual(feed["selected_for_synthetic_proof_gate"], 5)
        self.assertEqual(feed["verified_recovered_cash_cents"], 0)
        self.assertIsNone(feed["new_customer_proven_overcharges"])
        self.assertFalse(feed["commercial_recovery_allowed"])
        self.assertTrue(all(
            x["model"]["rating_status"] == "REVIEW_REQUIRED"
            and x["model"]["evidence_status"] == "REVIEW_REQUIRED"
            and x["model"]["verified_freight_error_cents"] is None
            and x["model"]["verified_cash_recovered_cents"] == 0
            and x["commercial_reuse_authorized"] is False
            and x["independent_ground_truth"] is False
            for x in feed["candidate_sources"]
        ))

    def test_gao_b215958_candidate_decision_stays_unscored(self):
        """Real adjudication locator cannot become an invoice-level recovery label."""
        from freight.research_eval_bridge import validate_feed

        url = "https://www.gao.gov/products/b-215958"
        source_fixture = json.loads(
            (Path(__file__).with_name("fixtures") / "gao_b215958_source_v1.json")
            .read_text(encoding="utf-8")
        )
        population = source_fixture["population"]
        self.assertEqual(population["decision_reversals_with_recorded_numbered_seals"], 53)
        self.assertEqual(population["remainder_cases_with_unresolved_disposition"], 2)
        self.assertFalse(population["per_bill_of_lading_labels_available"])
        self.assertFalse(source_fixture["limits"]["independent_accuracy_scoring_permitted"])

        unified = ledger_from([source_record(url, "freightrecovery", "2026-10-23")])
        evidence, candidates, manifest = (
            legacy_evidence(), legacy_candidates(), load_manifest()
        )
        feed = build_feed(unified, evidence, candidates, manifest)
        self.assertEqual(feed["source_pointers_total"], 1)
        row = feed["candidate_sources"][0]
        self.assertEqual(row["source_url"], url)
        self.assertIsNone(row["case_id"])
        self.assertEqual(row["source_kind"], "POTENTIAL_HISTORICAL_DECISION_REFERENCE")
        self.assertEqual(row["evaluation_state"], "SOURCE_POINTER_WITH_SYNTHETIC_PROOF_GATE_ONLY")
        self.assertFalse(row["commercial_reuse_authorized"])
        self.assertFalse(row["independent_ground_truth"])
        self.assertFalse(row["independent_payment_verified"])
        self.assertFalse(row["source_document_ingested"])
        self.assertEqual(row["model"]["rating_status"], "REVIEW_REQUIRED")
        self.assertEqual(row["model"]["evidence_status"], "REVIEW_REQUIRED")
        self.assertIsNone(row["model"]["verified_freight_error_cents"])
        self.assertEqual(row["model"]["verified_cash_recovered_cents"], 0)
        self.assertEqual(feed["independently_scored_new_customer_cases"], 0)
        self.assertIsNone(feed["new_customer_proven_overcharges"])

        # Red control: even a recomputed receipt cannot launder an invented
        # invoice-level dollar result into this rights-held source candidate.
        corrupted = deepcopy(feed)
        corrupted["candidate_sources"][0]["model"]["verified_freight_error_cents"] = 1
        body = {k: v for k, v in corrupted.items() if k != "feed_sha256"}
        corrupted["feed_sha256"] = digest(body)
        with self.assertRaises(ResearchError):
            validate_feed(corrupted, unified, evidence, candidates, manifest)
        # Green control: the unchanged, conservative feed is reproducible.
        validate_feed(feed, unified, evidence, candidates, manifest)

    def test_1986_overruling_1984_does_not_forge_invoice_accuracy_or_current_rights(self):
        """A GAO reconsideration is the latest historical case outcome, not cash."""
        from freight.gao_adjudication_chronology import (
            LATEST_HISTORICAL, ruling_as_of,
        )
        from datetime import date

        sources = (
            "https://www.gao.gov/products/b-215958",
            "https://www.gao.gov/products/b-215958-2",
        )
        self.assertEqual(
            ruling_as_of("B-215958", date(1984, 12, 5)),
            "GAO_1984_INITIAL_CARRIER_FAVORABLE_ONLY",
        )
        self.assertEqual(
            ruling_as_of("B-215958", date(1986, 2, 18)),
            LATEST_HISTORICAL,
        )
        doc = ledger_from([source_record(x, "freightrecovery", "2026-10-24")
                           for x in sources])
        evidence, candidates, manifest = (
            legacy_evidence(), legacy_candidates(), load_manifest()
        )
        feed = build_feed(doc, evidence, candidates, manifest)
        self.assertEqual(feed["source_pointers_total"], 2)
        for row in feed["candidate_sources"]:
            self.assertIn(row["source_url"], sources)
            self.assertFalse(row["commercial_reuse_authorized"])
            self.assertFalse(row["independent_ground_truth"])
            self.assertIsNone(row["model"]["verified_freight_error_cents"])
            self.assertEqual(row["model"]["verified_cash_recovered_cents"], 0)
            self.assertEqual(row["model"]["rating_status"], "REVIEW_REQUIRED")
        validate_feed(feed, doc, evidence, candidates, manifest)
        forged = deepcopy(feed)
        forged["candidate_sources"][1]["model"]["verified_freight_error_cents"] = 53
        forged["feed_sha256"] = digest({k:v for k,v in forged.items()
                                        if k != "feed_sha256"})
        with self.assertRaises(ResearchError):
            validate_feed(forged, doc, evidence, candidates, manifest)

    def test_gao_b165091_adjudicated_amount_never_becomes_unverified_freight_score(self):
        """The $179.80 official decision is not a verified customer recovery."""
        url = "https://www.gao.gov/products/b-165091"
        unified = ledger_from([source_record(url, "freightrecovery", "2026-10-24")])
        evidence, candidates, manifest = legacy_evidence(), legacy_candidates(), load_manifest()
        feed = build_feed(unified, evidence, candidates, manifest)
        self.assertEqual(feed["source_pointers_total"], 1)
        row = feed["candidate_sources"][0]
        self.assertEqual(row["source_url"], url)
        self.assertIsNone(row["case_id"])
        self.assertFalse(row["independent_ground_truth"])
        self.assertFalse(row["commercial_reuse_authorized"])
        self.assertFalse(row["source_document_ingested"])
        self.assertIsNone(row["model"]["verified_freight_error_cents"])
        self.assertEqual(row["model"]["verified_cash_recovered_cents"], 0)
        self.assertEqual(feed["independently_scored_new_customer_cases"], 0)
        validate_feed(feed, unified, evidence, candidates, manifest)
        forged = deepcopy(feed)
        forged["candidate_sources"][0]["model"]["verified_freight_error_cents"] = 17980
        forged["feed_sha256"] = digest({
            k: v for k, v in forged.items() if k != "feed_sha256"
        })
        with self.assertRaises(ResearchError):
            validate_feed(forged, unified, evidence, candidates, manifest)

    def test_cross_lab_dedupe_preserves_earliest_provenance_and_no_private_titles(self):
        doc, evidence, candidates = sample()
        feed = build_feed(doc, evidence, candidates, load_manifest())
        match = next(x for x in feed["candidate_sources"] if x["source_url"] == GAO)
        self.assertEqual(match["first_seen"], "2026-10-17")
        self.assertEqual(match["origins"], ["LAB15_EVIDENCE", "UNIFIED"])
        self.assertEqual(match["case_id"], None)  # separate frozen public source corpus
        self.assertNotIn("title", match)
        self.assertNotIn("sha256", match)  # legacy GAO fingerprint is not copied

    def test_exact_frozen_reference_url_is_linked_not_unrelated_dataset(self):
        doc, evidence, candidates = sample()
        feed = build_feed(doc, evidence, candidates, load_manifest())
        hit = next(x for x in feed["candidate_sources"] if x["source_url"] == SEC)
        self.assertEqual(hit["case_id"], "TESORO_2011_TRUCKING")
        self.assertEqual(hit["source_kind"], "MATCHED_FROZEN_V1_REFERENCE")
        generic = next(x for x in feed["candidate_sources"]
                       if x["source_url"].startswith("https://catalog.data.gov/"))
        self.assertIsNone(generic["case_id"])
        self.assertEqual(generic["source_kind"], "UNCLASSIFIED_PUBLIC_DATASET_LEAD")

    def test_exact_historical_gao_reference_stays_rights_held_and_unscored(self):
        # Near-match and forged-money controls are SYNTHETIC, not source labels.
        exact = "https://www.gao.gov/products/b-213717-0"
        near = "https://www.gao.gov/products/b-213717"
        forged = "https://www.gao.gov/products/b-213717-0-fake-cash"
        source = ledger_from([
            source_record(url, "freightrecovery", "2026-10-26")
            for url in (exact, near, forged)
        ])
        evidence, candidates = legacy_evidence(), legacy_candidates()
        manifest = load_manifest()
        feed = build_feed(source, evidence, candidates, manifest)
        rows = {r["source_url"]: r for r in feed["candidate_sources"]}
        match = rows[exact]
        self.assertIsNone(match["case_id"])  # frozen v1 never promoted
        self.assertEqual(match["historical_decision_reference"]["decision_id"],
                         "B-213717")
        self.assertEqual(match["historical_decision_reference"]["decision_date"],
                         "1984-03-20")
        self.assertIsNone(match["historical_decision_reference"]
                          ["original_publisher_response_sha256"])
        self.assertFalse(match["historical_decision_reference"]
                         ["commercial_rights_verified"])
        self.assertEqual(feed["historical_gao_decision_reference_matches"], 1)
        for row in rows.values():
            self.assertFalse(row["commercial_reuse_authorized"])
            self.assertFalse(row["independent_ground_truth"])
            self.assertFalse(row["independent_payment_verified"])
            self.assertFalse(row["source_document_ingested"])
            self.assertEqual(row["model"]["verified_cash_recovered_cents"], 0)
            self.assertIsNone(row["model"]["verified_freight_error_cents"])
        self.assertIsNone(rows[near]["historical_decision_reference"])
        self.assertIsNone(rows[forged]["historical_decision_reference"])
        self.assertEqual(feed["frozen_v1_official_source_matches"], 0)
        self.assertEqual(feed["independently_scored_new_customer_cases"], 0)
        self.assertEqual(feed["verified_recovered_cash_cents"], 0)
        self.assertFalse(feed["commercial_recovery_allowed"])

        for mutation in ("forged_decision", "fake_money"):
            invalid = deepcopy(feed)
            target = next(r for r in invalid["candidate_sources"]
                          if r["source_url"] == exact)
            if mutation == "forged_decision":
                target["historical_decision_reference"]["decision_id"] = "B-999999"
            else:
                target["model"]["verified_cash_recovered_cents"] = 52531
            invalid["feed_sha256"] = digest({
                key: value for key, value in invalid.items()
                if key != "feed_sha256"
            })
            with self.subTest(mutation=mutation), self.assertRaises(ResearchError):
                validate_feed(invalid, source, evidence, candidates, manifest)

    def test_gao_crosswalk_pinned_source_fails_closed_on_missing_or_drift(self):
        from freight.research_eval_bridge import HISTORICAL_GAO_CASEBOOK

        source, evidence, candidates = sample()
        manifest = load_manifest()
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "casebook.json"
            path.write_bytes(HISTORICAL_GAO_CASEBOOK.read_bytes())
            good = build_feed(source, evidence, candidates, manifest,
                              historical_casebook_path=path)
            self.assertEqual(
                len(good["source_receipts"]["reviewed_historical_gao_casebook_file_sha256"]),
                64,
            )
            path.write_bytes(path.read_bytes() + b"\n")
            with self.assertRaisesRegex(ResearchError,
                                        "HISTORICAL_GAO_CASEBOOK_UNREVIEWED_DRIFT"):
                build_feed(source, evidence, candidates, manifest,
                           historical_casebook_path=path)
            path.unlink()
            with self.assertRaisesRegex(ResearchError,
                                        "HISTORICAL_GAO_CASEBOOK_MISSING"):
                build_feed(source, evidence, candidates, manifest,
                           historical_casebook_path=path)

    def test_historical_crosswalk_is_bounded_without_losing_exact_reference(self):
        exact = source_record("https://www.gao.gov/products/b-213717-0",
                              "freightrecovery", "2026-01-01")
        newer = [
            source_record("https://catalog.data.gov/dataset/possible-freight-" + str(i),
                          "freightrecovery", "2026-10-26")
            for i in range(MAX_FEED_ROWS + 5)
        ]
        feed = build_feed(ledger_from([exact, *newer]), legacy_evidence(),
                          legacy_candidates(), load_manifest())
        self.assertEqual(feed["selected_for_synthetic_proof_gate"], MAX_FEED_ROWS)
        self.assertEqual(feed["omitted_for_bounded_execution"], 6)
        self.assertEqual(feed["historical_gao_decision_reference_matches"], 1)
        self.assertEqual(feed["candidate_sources"][0]["source_url"], exact["url"])

    def test_private_invoice_domains_are_excluded_even_when_in_manifest(self):
        doc, evidence, candidates = sample()
        extra = source_record("https://www.gao.gov/products/b-143246",
                              "freightrecovery", "2026-10-22")
        doc = ledger_from(doc["entries"] + [extra])
        feed = build_feed(doc, evidence, candidates, load_manifest())
        self.assertNotIn("BIG_G_2026_FACE", [x["case_id"] for x in feed["candidate_sources"]])
        self.assertNotIn("PYLE_2021_FACE", [x["case_id"] for x in feed["candidate_sources"]])

    def test_nonfreight_unified_source_does_not_appear_in_freight_feed(self):
        doc, evidence, candidates = sample()
        feed = build_feed(doc, evidence, candidates, load_manifest())
        self.assertTrue(all("data.cityofnewyork.us" not in c["source_url"]
                            for c in feed["candidate_sources"]))

    def test_source_probe_uses_native_engine_but_has_no_original_invoice(self):
        case = synthetic_proof_gate(digest(GAO))
        self.assertEqual(case["rating_status"], "REVIEW_REQUIRED")
        self.assertIsNone(case["verified_freight_error_cents"])
        self.assertEqual(case["verified_cash_recovered_cents"], 0)
        with self.assertRaises(ResearchError):
            synthetic_proof_gate("source document")

    def test_rehashed_fake_rights_are_rejected_before_feed(self):
        doc, evidence, candidates = sample()
        wrong = deepcopy(doc)
        wrong["entries"][0]["commercial_reuse_authorized"] = True
        wrong["entries_sha256"] = digest(wrong["entries"])
        with self.assertRaises(ResearchError):
            build_feed(wrong, evidence, candidates, load_manifest())
        changed = deepcopy(evidence)
        changed["records"][0]["actual_payment_verified"] = True
        with self.assertRaises(Exception):
            build_feed(doc, changed, candidates, load_manifest())

    def test_rehashed_candidate_corruption_is_rejected(self):
        doc, evidence, candidates = sample()
        changed = deepcopy(candidates)
        changed["leads"][0]["commercial_reuse_authorized"] = True
        base = {k: v for k, v in changed.items() if k != "digest_sha256"}
        changed["digest_sha256"] = legacy_digest(base)
        with self.assertRaises(Exception):
            build_feed(doc, evidence, changed, load_manifest())

    def test_rehashed_omission_or_case_promotion_detected(self):
        doc, evidence, candidates = sample()
        normal = build_feed(doc, evidence, candidates, load_manifest())
        for mutation in ("delete", "fake_truth", "new_case"):
            altered = deepcopy(normal)
            if mutation == "delete":
                altered["candidate_sources"].pop()
            if mutation == "fake_truth":
                altered["candidate_sources"][0]["independent_ground_truth"] = True
            if mutation == "new_case":
                altered["candidate_sources"][-1]["case_id"] = "GIBSON_FMC_2030I"
            body = {k: v for k, v in altered.items() if k != "feed_sha256"}
            altered["feed_sha256"] = digest(body)
            with self.subTest(mutation=mutation), self.assertRaises(ResearchError):
                validate_feed(altered, doc, evidence, candidates, load_manifest())

    def test_stale_or_tampered_baseline_manifest_rejected(self):
        doc, evidence, candidates = sample()
        altered = deepcopy(load_manifest())
        altered["cases"][0]["real_customer_payment_verified"] = True
        with self.assertRaises(ValueError):
            build_feed(doc, evidence, candidates, altered)

    def test_bounded_dataset_explains_denominator_not_silent_loss(self):
        records = [
            source_record("https://catalog.data.gov/dataset/freight-record-" + str(i),
                          "freightrecovery", "2026-10-23")
            for i in range(MAX_FEED_ROWS + 5)
        ]
        feed = build_feed(ledger_from(records), legacy_evidence(),
                          legacy_candidates(), load_manifest())
        self.assertEqual(feed["source_pointers_total"], MAX_FEED_ROWS + 5)
        self.assertEqual(feed["selected_for_synthetic_proof_gate"], MAX_FEED_ROWS)
        self.assertEqual(feed["omitted_for_bounded_execution"], 5)

    def test_cli_writer_and_exact_readback_are_idempotent(self):
        doc, evidence, candidates = sample()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            unified_file = root / "unified.json"
            evidence_file = root / "evidence.json"
            candidates_file = root / "candidates.json"
            output = root / "feed.json"
            for path, body in ((unified_file, doc), (evidence_file, evidence),
                               (candidates_file, candidates)):
                path.write_text(json.dumps(body), encoding="utf-8")
            first = bridge_run(unified_file, evidence_file, candidates_file, output)
            exact = output.read_bytes()
            second = bridge_run(unified_file, evidence_file, candidates_file, output)
            self.assertEqual(first, second)
            self.assertEqual(exact, output.read_bytes())
            bridge_run(unified_file, evidence_file, candidates_file, output,
                       verify_only=True)
            tampered = json.loads(output.read_text(encoding="utf-8"))
            tampered["verified_recovered_cash_cents"] = 100
            output.write_text(json.dumps(tampered), encoding="utf-8")
            with self.assertRaises(ResearchError):
                bridge_run(unified_file, evidence_file, candidates_file, output,
                           verify_only=True)


if __name__ == "__main__":
    unittest.main()
