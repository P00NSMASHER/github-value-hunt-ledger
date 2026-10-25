"""Offline adversarial contract tests for all four unified research lanes."""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from unittest.mock import patch

from freight.unified_research_lab import (
    ENGINES, SEARCHES, SEEDS, ResearchError, current_engine, ledger_from, merge_sources,
    read_ledger, run, safe_url, scan, source_record, validate_ledger,
    mirror_scout_all, get_json, metadata_in_scope, original_nyc_catalog_entry,
)

NOW = datetime(2026, 10, 22, 20, 0, tzinfo=timezone.utc)


class UnifiedResearchLabTests(unittest.TestCase):
    def test_gao_b215958_source_scope_dedup_and_unknowns(self):
        fixture = Path(__file__).with_name("fixtures") / "gao_b215958_source_v1.json"
        data = json.loads(fixture.read_text(encoding="utf-8"))
        self.assertEqual(data["schema_version"], "1.0.0")
        self.assertEqual(data["status"], "SOURCE_BOUND_DECISION_LEVEL_CANDIDATE_NOT_HELD_OUT")
        source = data["source"]
        url = "https://www.gao.gov/products/b-215958"
        self.assertEqual(source["original_record_url"], url)
        self.assertEqual(source["original_report_url"],
                         "https://www.gao.gov/assets/b-215958-125766.pdf")
        self.assertEqual(source["decision_date"], "1984-12-05")
        self.assertEqual(source["superseding_reconsideration_url"],
                         "https://www.gao.gov/products/b-215958-2")
        self.assertEqual(source["superseding_reconsideration_date"], "1986-02-18")
        self.assertEqual(source["decision_page_for_disposition"], 3)
        self.assertIsNone(source["source_bytes_sha256"])
        self.assertFalse(source["source_bytes_acquired"])
        self.assertFalse(source["commercial_use_of_engine_input_approved"])
        population = data["population"]
        self.assertEqual(population["challenged_government_bills_of_lading"], 55)
        self.assertEqual(population["decision_reversals_with_recorded_numbered_seals"], 53)
        self.assertEqual(population["remainder_cases_with_unresolved_disposition"], 2)
        self.assertEqual(population["decision_outcome"],
                         "GAO_1984_INITIAL_REVERSAL_SUBSEQUENTLY_OVERRULED_IN_1986")
        self.assertFalse(population["per_bill_of_lading_labels_available"])
        self.assertIsNone(population["independently_confirmed_refunds_received"])
        self.assertIsNone(population["independently_confirmed_carrier_overcharge_amount_cents"])
        self.assertFalse(data["limits"]["independent_accuracy_scoring_permitted"])
        self.assertEqual(data["limits"]["realized_retally_recovered_cash_cents"], 0)
        self.assertEqual(len(data["controls"]), 2)
        self.assertEqual(data["controls"][0]["expected"],
                         "1984_INITIAL_FAVORABLE_RULING_NOT_FINAL_1986_WRITTEN_REQUEST_REQUIRED")
        self.assertTrue(all(x["synthetic"] for x in data["controls"]))
        self.assertTrue(all(x["actual_refund_received_cents"] is None
                            and x["actual_customer_overcharge_cents"] is None
                            for x in data["controls"]))
        self.assertIn(url, SEEDS["freightrecovery"])
        self.assertEqual(safe_url(url), url)
        single, added = merge_sources(ledger_from([]), "freightrecovery",
                                      [url, url], "2026-10-23")
        self.assertEqual(added, 1)
        self.assertEqual(len(single["entries"]), 1)
        self.assertFalse(single["entries"][0]["independent_ground_truth"])
        self.assertFalse(single["entries"][0]["commercial_reuse_authorized"])
        self.assertFalse(single["entries"][0]["recovered_cash_verified"])

    def test_gao_b215958_research_manifest_hash_and_negative_control(self):
        fixture = Path(__file__).with_name("fixtures") / "gao_b215958_source_v1.json"
        data = json.loads(fixture.read_text(encoding="utf-8"))
        self.assertEqual(
            data["manifest_hash_contract"],
            "RESEARCH_AUTHORED_MANIFEST_SHA256_CANONICAL_SORTED_JSON_EXCLUDING_SELF_NOT_ORIGINAL_PUBLISHER_BYTES",
        )
        self.assertEqual(data["data_quality"]["publisher_original_review_date"], "2026-10-23")
        self.assertIsNone(data["source"]["source_bytes_sha256"])
        self.assertFalse(data["source"]["source_bytes_acquired"])
        self.assertFalse(data["source"]["commercial_use_of_engine_input_approved"])

        def authored_digest(obj):
            canonical = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

        author_fields = {k: v for k, v in data.items() if k != "manifest_sha256"}
        self.assertEqual(data["manifest_sha256"], authored_digest(author_fields))
        mutated = json.loads(json.dumps(author_fields))
        mutated["population"]["decision_reversals_with_recorded_numbered_seals"] = 55
        self.assertNotEqual(data["manifest_sha256"], authored_digest(mutated))
        self.assertEqual(
            mutated["population"]["decision_reversals_with_recorded_numbered_seals"]
            + data["population"]["remainder_cases_with_unresolved_disposition"],
            57,
        )

    def test_gao_b165091_historical_tariff_contrast_is_labeled_not_laundered(self):
        """GAO gives a numeric adjudication, not a customer invoice truth set."""
        case = json.loads(
            (Path(__file__).with_name("fixtures") / "gao_b165091_source_v1.json")
            .read_text(encoding="utf-8")
        )
        original = {k: v for k, v in case.items() if k != "manifest_sha256"}
        digest = hashlib.sha256(json.dumps(
            original, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")).hexdigest()
        self.assertEqual(case["manifest_sha256"], digest)
        self.assertEqual(case["source"]["decision_date"], "1969-01-03")
        self.assertEqual(case["source"]["historical_tariff"].split(",")[-1].strip(), "item 2400")
        self.assertFalse(case["source"]["source_bytes_acquired"])
        self.assertIsNone(case["source"]["source_bytes_sha256"])
        self.assertFalse(case["source"]["commercial_use_of_engine_input_approved"])
        self.assertFalse(case["cohort"]["independent_holdout_against_engine_training_verified"])
        self.assertFalse(case["limits"]["independent_invoice_error_accuracy_scoring_permitted"])
        adjudicated, conditional = case["adjudications"]
        self.assertTrue(adjudicated["decision_complete"])
        self.assertEqual(adjudicated["adjudicated_sustained_deduction_cents"], 17980)
        self.assertEqual(adjudicated["original_paid_exclusive_use_charge_cents"], 45050)
        self.assertFalse(adjudicated["contemporaneous_written_exclusive_use_order_verified"])
        self.assertIsNone(adjudicated["independently_verified_refund_received_cents"])
        self.assertFalse(conditional["decision_complete"])
        self.assertEqual(conditional["original_claimed_additional_charges_cents"], 39324)
        self.assertIsNone(conditional["finally_allowed_amount_cents"])
        self.assertTrue(all(c["synthetic"] and c["real_invoice_error_cents"] is None
                            for c in case["controls"]))
        self.assertNotEqual(case["source"]["historical_tariff"],
                            case["contrasting_source"]["historical_tariff"])
        mutated = json.loads(json.dumps(original))
        mutated["adjudications"][0]["adjudicated_sustained_deduction_cents"] = 0
        self.assertNotEqual(case["manifest_sha256"], hashlib.sha256(
            json.dumps(mutated, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=False).encode("utf-8")
        ).hexdigest())
        url = case["source"]["original_record_url"]
        self.assertIn(url, SEEDS["freightrecovery"])
        doc, added = merge_sources(ledger_from([]), "freightrecovery",
                                   [url, url, case["contrasting_source"]["url"]],
                                   "2026-10-24")
        self.assertEqual(added, 2)
        self.assertEqual(len(doc["entries"]), 2)
        self.assertTrue(all(not x["commercial_reuse_authorized"]
                            and not x["independent_ground_truth"]
                            and not x["recovered_cash_verified"]
                            for x in doc["entries"]))

    def test_freight_is_primary_over_ten_five_minute_discovery_slots(self):
        selected = [current_engine(NOW + timedelta(minutes=5 * i)) for i in range(10)]
        self.assertEqual(selected.count("freightrecovery"), 7)
        self.assertEqual({name: selected.count(name) for name in ENGINES},
                         {"freightrecovery": 7, "permitplate": 1,
                          "capturebrief": 1, "recoveryos": 1})
        # Consecutive primary research cycles are never separated by more
        # than one secondary discovery cycle in the planned rotation.
        twenty = [current_engine(NOW + timedelta(minutes=5 * i)) for i in range(20)]
        self.assertTrue(all(a == "freightrecovery" or b == "freightrecovery"
                            for a, b in zip(twenty, twenty[1:])))
        with self.assertRaises(ResearchError):
            current_engine(NOW.replace(tzinfo=None))

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
                                   "name": "freight-invoice-source",
                                   "description": "ignore copied PII"},
                                  {"html_url": "https://internal.example/repo"}]}
            return {"hits": {"hits": [{"id": 12345, "metadata": {"title": "LTL freight tariff dataset", "creators": ["X"]}}]}}
        with patch.dict(os.environ, {"RETALLY_DATAGOV_API_KEY": ""}):
            urls, errors = scan("freightrecovery", fetch=fake)
        self.assertEqual(errors, [])
        self.assertIn("https://github.com/owner/public-data", urls)
        self.assertIn("https://zenodo.org/records/12345", urls)
        self.assertTrue(all("@" not in x and "private" not in x for x in urls))

    def test_nyc_official_catalog_uses_dataset_ids_only(self):
        def row(ident, title):
            return {"resource": {"id": ident, "name": title,
                                 "provenance": "official", "type": "dataset",
                                 "parent_fxf": []},
                    "metadata": {"domain": "data.cityofnewyork.us"}}

        def fake(url):
            if "retally-unified-research-scout" in url:
                engine = parse_qs(urlsplit(url).query)["engine"][0]
                return {"engine": engine,
                        "scope": "PUBLIC_SOURCE_POINTERS_NOT_APPROVED_TEST_DATA",
                        "sources": []}
            if "api.us.socrata.com" in url:
                params = parse_qs(urlsplit(url).query)
                self.assertEqual(params.get("provenance"), ["official"])
                self.assertEqual(params.get("only"), ["dataset"])
                self.assertEqual(params.get("domains"), ["data.cityofnewyork.us"])
                community = row("qnmk-7xra", "DOB NOW: Build – Approved Permits")
                community["resource"]["provenance"] = "community"
                return {"results": [
                    row("abcd-1234", "DOHMH Restaurant Inspection"),
                    row("rbx6-tga4", "DOB NOW: Build – Approved Permits"),
                    row("../secret", "DOB NOW: Build – Approved Permits"),
                    community,
                ]}
            if "api.github.com" in url:
                return {"items": []}
            return {"hits": {"hits": []}}
        with patch.dict(os.environ, {"RETALLY_DATAGOV_API_KEY": ""}):
            urls, errors = scan("permitplate", fetch=fake)
        self.assertEqual(errors, [])
        self.assertEqual(urls, ["https://data.cityofnewyork.us/d/rbx6-tga4"])

    def test_socrata_original_publisher_identity_must_be_explicit(self):
        original = {
            "resource": {
                "id": "rbx6-tga4", "name": "DOB NOW: Build – Approved Permits",
                "provenance": "official", "type": "dataset", "parent_fxf": [],
            },
            "metadata": {"domain": "data.cityofnewyork.us"},
        }
        self.assertTrue(original_nyc_catalog_entry(original))
        variations = (
            {"resource": dict(original["resource"], provenance="community"),
             "metadata": original["metadata"]},
            {"resource": dict(original["resource"], type="filter"),
             "metadata": original["metadata"]},
            {"resource": dict(original["resource"], parent_fxf=["rbx6-tga4"]),
             "metadata": original["metadata"]},
            {"resource": dict(original["resource"], provenance=None),
             "metadata": original["metadata"]},
            {"resource": original["resource"],
             "metadata": {"domain": "data.evil.invalid"}},
            {"resource": original["resource"], "metadata": {}},
            {"resource": dict(original["resource"], parent_fxf=None),
             "metadata": original["metadata"]},
            {"resource": dict(original["resource"], name="DOHMH Restaurant Inspection"),
             "metadata": original["metadata"]},
            {},
            None,
        )
        for row in variations:
            with self.subTest(source=row):
                self.assertFalse(original_nyc_catalog_entry(row))

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
            "permitplate": "https://data.cityofnewyork.us/d/w9ak-ipjd",
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

    def test_permitplate_official_dob_seed_replaces_restaurant_and_stays_rights_held(self):
        # Official NYC DOB original source, not the DOHMH restaurant-inspection seed.
        official = "https://data.cityofnewyork.us/d/rbx6-tga4"
        applications = "https://data.cityofnewyork.us/d/w9ak-ipjd"
        self.assertEqual(set(SEEDS["permitplate"]), {official, applications, "https://data.cityofnewyork.us/d/dm9a-ab7w", "https://data.cityofnewyork.us/d/kfp4-dz4h", "https://data.cityofnewyork.us/d/xxbr-ypig"})
        self.assertNotIn("https://data.cityofnewyork.us/d/43nn-pn8j", SEEDS["permitplate"])
        with tempfile.TemporaryDirectory() as root:
            ledger = Path(root) / "permit_sources.json"
            receipt = run(engine="permitplate", live=False, ledger=ledger, now=NOW)
            rows = read_ledger(ledger)["entries"]
            self.assertEqual(receipt["new_leads"], 5)
            self.assertEqual({r["url"] for r in rows}, set(SEEDS["permitplate"]))
            self.assertEqual(receipt["approved_real_truth_cases"], 0)
            self.assertTrue(all(not r["commercial_reuse_authorized"]
                                and not r["independent_ground_truth"]
                                and not r["document_bytes_stored"] for r in rows))
        pack = json.loads((Path(__file__).with_name("fixtures") /
                           "nyc_dob_source_scope_v1.json").read_text(encoding="utf-8"))
        self.assertEqual(pack["evaluation_family"],
                         "GOVERNMENT_PERMIT_SCORING_SOURCE_COVERAGE_ONLY")
        self.assertEqual(pack["real_issuance_cases_ingested"], 0)
        self.assertEqual(pack["acceptance_boundaries"]["independent_labels_count"], 0)
        self.assertEqual(pack["accuracy_evaluation"],
                         "NOT_ESTIMABLE_WITHOUT_INDEPENDENT_LABELS")
        source = next(x for x in pack["official_sources"] if x["dataset_id"] == "rbx6-tga4")
        self.assertEqual(source["official_url"], official)
        self.assertFalse(source["commercial_reuse_authorized"])
        self.assertFalse(source["independent_outcome_adjudicated"])
        self.assertIsNone(source["original_source_bytes_sha256"])
        # Existing approved excluded-scope v1 pack remains the canonical
        # evaluation pointer; this seed linkage does not create a second pack.
        excluded = json.loads((Path(__file__).with_name("fixtures") /
                              "nyc_dob_excluded_scope_v1.json").read_text(encoding="utf-8"))
        self.assertEqual(excluded["real_permit_records_ingested"], 0)
        self.assertEqual(excluded["independent_outcome_labels"], 0)
        self.assertEqual(excluded["cross_dataset_join"], "UNVERIFIED")
        self.assertEqual(excluded["commercial_use"], "UNVERIFIED_NOT_APPROVED")
        self.assertEqual({s["official_url"] for s in excluded["companion_source_candidates"]},
                         set(SEEDS["permitplate"]) - {official, applications})
        self.assertEqual(len(pack["synthetic_negative_controls"]), 4)
        self.assertTrue(all(c["provenance_class"].startswith("SYNTHETIC")
                            and c["real_world_accuracy_label"] is None
                            for c in pack["synthetic_negative_controls"]))

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


    def test_mirror_survives_one_malformed_provider_without_losing_other_lanes(self):
        urls = {
            "freightrecovery": "https://www.gao.gov/products/b-160344",
            "permitplate": "https://data.cityofnewyork.us/d/rbx6-tga4",
            "recoveryos": "https://www.penninecare.nhs.uk/download_file/5855/277",
        }
        def fetch(url):
            engine = parse_qs(urlsplit(url).query)["engine"][0]
            if engine == "capturebrief":
                raise ValueError("untrusted provider text must not leak")
            return {"engine": engine,
                    "scope": "PUBLIC_SOURCE_POINTERS_NOT_APPROVED_TEST_DATA",
                    "sources": [{"url": urls[engine], "first_seen": "2026-10-22"}]}
        with tempfile.TemporaryDirectory() as root:
            ledger = Path(root) / "sources.json"
            result = mirror_scout_all(ledger=ledger, now=NOW, fetch=fetch)
            self.assertEqual(result["new_leads"], 3)
            self.assertEqual(len(result["feed_errors"]), 1)
            self.assertEqual(result["feed_errors"][0],
                             "capturebrief:UNTRUSTED_SCOUT_RESPONSE_ValueError")
            self.assertNotIn("untrusted provider text", str(result))
            self.assertEqual(len(read_ledger(ledger)["entries"]), 3)
            self.assertEqual(result["third_party_documents_saved"], 0)
            self.assertEqual(result["customer_contact_actions"], 0)

    def test_json_provider_invalid_response_is_bounded_error_not_raw_body(self):
        from contextlib import nullcontext
        url = "https://api.github.com/search/repositories?q=metadata"
        class Response:
            status = 200
            headers = {"Content-Type": "application/json"}
            def geturl(self):
                return url
            def read(self, limit):
                return b'{"not-a-valid-object":'
        with patch("freight.unified_research_lab.global_dns"):
            with patch("freight.unified_research_lab.build_opener") as opener:
                opener.return_value.open.return_value = nullcontext(Response())
                with self.assertRaisesRegex(ResearchError, "SOURCE_JSON_INVALID"):
                    get_json(url)




    def test_pagination_mirrors_all_pages_and_respects_40_new_source_budget(self):
        called = []
        def fake(url):
            query = parse_qs(urlsplit(url).query)
            engine = query["engine"][0]
            before = query.get("before", [None])[0]
            called.append((engine, before))
            data = {"engine": engine,
                    "scope": "PUBLIC_SOURCE_POINTERS_NOT_APPROVED_TEST_DATA",
                    "sources": []}
            if engine == "capturebrief":
                if before is None:
                    data["sources"] = [
                        {"url": f"https://github.com/synthetic-fixture/capture-dataset-{i:03d}",
                         "first_seen": "2026-10-22"}
                        for i in range(100)]
                    data["next_cursor"] = "250"
                elif before == "250":
                    data["sources"] = [
                        {"url": f"https://github.com/synthetic-fixture/capture-dataset-{i:03d}",
                         "first_seen": "2026-10-21"}
                        for i in range(100, 102)]
                    data["next_cursor"] = None
                else:
                    raise AssertionError("unexpected cursor")
            return data
        with tempfile.TemporaryDirectory() as root:
            ledger = Path(root) / "sources.json"
            now = NOW + timedelta(days=1)
            outputs = [mirror_scout_all(ledger=ledger, now=now, fetch=fake)
                       for _ in range(3)]
            self.assertEqual([x["new_leads"] for x in outputs], [40,40,22])
            self.assertEqual(len(read_ledger(ledger)["entries"]), 102)
            self.assertEqual(outputs[-1]["per_engine"]["capturebrief"]["available"], 102)
            self.assertEqual(outputs[-1]["per_engine"]["capturebrief"]["pages_read"], 2)
            self.assertEqual(outputs[-1]["feed_errors"], [])
            self.assertEqual(called.count(("capturebrief", "250")), 3)
            self.assertTrue(all(row["rights_state"].startswith("UNVERIFIED")
                                for row in read_ledger(ledger)["entries"]))
            self.assertEqual(
                sorted({row["first_seen"] for row in read_ledger(ledger)["entries"]}),
                ["2026-10-21", "2026-10-22"])

    def test_pagination_invalid_cursor_quarantines_only_affected_lane(self):
        def fake(url):
            engine = parse_qs(urlsplit(url).query)["engine"][0]
            data = {"engine": engine,
                    "scope": "PUBLIC_SOURCE_POINTERS_NOT_APPROVED_TEST_DATA",
                    "sources": []}
            if engine == "capturebrief":
                data["sources"] = [
                    {"url": f"https://github.com/synthetic-fixture/invalid-cursor-{i:03d}",
                     "first_seen": "2026-10-22"} for i in range(100)]
                data["next_cursor"] = "1234bad"
            return data
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "sources.json"
            result = mirror_scout_all(ledger=path, now=NOW, fetch=fake)
            self.assertEqual(result["new_leads"], 0)
            self.assertEqual(result["feed_errors"], ["capturebrief:SCOUT_CURSOR_INVALID"])
            self.assertEqual(result["per_engine"]["capturebrief"]["pages_read"], 0)
            self.assertEqual(read_ledger(path)["entries"], [])

    def test_pagination_six_page_ceiling_is_disclosed_not_silently_ignored(self):
        def fake(url):
            args = parse_qs(urlsplit(url).query)
            engine = args["engine"][0]
            before = args.get("before", [None])[0]
            data = {"engine": engine,
                    "scope": "PUBLIC_SOURCE_POINTERS_NOT_APPROVED_TEST_DATA",
                    "sources": []}
            if engine == "recoveryos":
                index = 0 if before is None else 601 - int(before)
                if index < 0 or index >= 6:
                    raise AssertionError("page beyond configured limit")
                data["sources"] = [
                    {"url": f"https://github.com/synthetic-fixture/recovery-source-{index:02d}-{i:03d}",
                     "first_seen": "2026-10-22"} for i in range(100)]
                data["next_cursor"] = str(600-index)
            return data
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "sources.json"
            report = mirror_scout_all(ledger=path, now=NOW, fetch=fake)
            self.assertIn("recoveryos:SCOUT_PAGE_CAP_REACHED", report["feed_errors"])
            self.assertTrue(report["per_engine"]["recoveryos"]["page_cap_reached"])
            self.assertEqual(report["per_engine"]["recoveryos"]["pages_read"], 6)
            self.assertEqual(report["per_engine"]["recoveryos"]["available"], 600)
            self.assertEqual(report["per_engine"]["recoveryos"]["new"], 40)
            self.assertEqual(len(read_ledger(path)["entries"]), 40)




    def test_public_publisher_topic_filter_discards_off_topic_metadata_per_lane(self):
        cases = (
            ("freightrecovery", "Freight invoice tariff dataset", "Baking and dining recipes"),
            ("permitplate", "NYC DOB NOW approved building permits",
             "NYC restaurant inspection permits"),
            ("capturebrief", "Federal solicitation contract awards",
             "Professional basketball boxscores"),
            ("recoveryos", "Accounts payable supplier invoice reconciliation",
             "Wildlife photography archive"),
        )
        for engine, good, bad in cases:
            for provider in ("github", "zenodo"):
                with self.subTest(engine=engine, provider=provider):
                    good_row = ({"name": "generic", "description": good}
                                if provider == "github" else {"metadata": {"title": good}})
                    bad_row = ({"name": "generic", "description": bad}
                               if provider == "github" else {"metadata": {"title": bad}})
                    self.assertTrue(metadata_in_scope(engine, provider, good_row))
                    self.assertFalse(metadata_in_scope(engine, provider, bad_row))
                    self.assertFalse(metadata_in_scope(engine, provider,
                                                      {"metadata": {"creators": ["A"]}}))
        with self.assertRaises(ResearchError):
            metadata_in_scope("invalid", "github", {"name": "freight"})
        with self.assertRaises(ResearchError):
            metadata_in_scope("freightrecovery", "socrata", {})

    def test_live_scan_rejects_wrong_topic_github_and_zenodo_without_private_metadata(self):
        def fake(url):
            if "retally-unified-research-scout" in url:
                return {"engine": "recoveryos",
                        "scope": "PUBLIC_SOURCE_POINTERS_NOT_APPROVED_TEST_DATA",
                        "sources": []}
            if "api.github.com" in url:
                return {"items": [
                    {"html_url": "https://github.com/synthetic-fixture/vendor-payment-dataset",
                     "name": "unrelated-title",
                     "description": "Accounts payable vendor payment dataset"},
                    {"html_url": "https://github.com/synthetic-fixture/wildlife-project",
                     "name": "not-relevant",
                     "description": "Biology research bird species"},
                ]}
            return {"hits": {"hits": [
                {"id": 345, "metadata": {"title": "Supplier invoice reconciliation research"}},
                {"id": 999, "metadata": {"title": "Bird migration routes"}},
                {"id": 2000, "metadata": {"creators": ["private author info"]}},
            ]}}
        with patch.dict(os.environ, {"RETALLY_DATAGOV_API_KEY": ""}):
            sources, errors = scan("recoveryos", fetch=fake)
        self.assertEqual(errors, [])
        self.assertEqual(sources, [
            "https://github.com/synthetic-fixture/vendor-payment-dataset",
            "https://zenodo.org/records/345",
        ])
        self.assertNotIn("private author", str(sources))
        self.assertNotIn("Bird", str(sources))




class FMCIndexOnlySourceCandidateTests(unittest.TestCase):
    """Original publisher indexed case is a held, not score-admitted source."""

    def test_final_commission_interest_supersedes_preliminary_denial(self):
        path = Path(__file__).with_name("fixtures") / "fmc_22fmc94_girton_index_candidate_v0.json"
        item = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(item["schema_version"], "0.1.0")
        self.assertEqual(item["admission_state"], "DISCOVERED_SOURCE_ONLY_NOT_EVALUATION_ADMITTED")
        self.assertEqual(item["evaluation_family"],
                         "FREIGHT_ERROR_ADJUDICATION_HISTORICAL_MARITIME_DECISION_ONLY")
        source = item["source"]
        self.assertIn(source["official_pdf_url"], SEEDS["freightrecovery"])
        self.assertEqual(source["citation"], "22 F.M.C. 94")
        self.assertEqual(source["docket"], "Informal Docket 594(I)")
        self.assertEqual(source["commission_decision_date"], "1979-09-05")
        self.assertFalse(source["original_publisher_pdf_bytes_held"])
        self.assertIsNone(source["original_publisher_pdf_sha256"])
        self.assertFalse(source["rights_or_customer_engine_commercial_reuse_verified"])
        facts = item["historical_decision_only"]
        self.assertEqual(facts["commission_reparation_award_cents"], 40930)
        self.assertTrue(facts["commission_interest_awarded"])
        self.assertEqual(facts["commission_interest_rate_basis_points_per_year"], 600)
        self.assertEqual(facts["interest_accrual_start"], "1978-04-03")
        self.assertTrue(facts["preliminary_settlement_officer_interest_denied"])
        self.assertTrue(facts["preliminary_officer_1979_claim_filing_date_corrected_by_commission"])
        self.assertIsNone(facts["commission_award_collected_cents"])
        self.assertIsNone(facts["interest_actually_paid_cents"])
        self.assertEqual(facts["later_disposition"], "UNKNOWN")
        limits = item["truth_boundaries"]
        self.assertFalse(limits["independently_replayable_original_invoice_truth"])
        self.assertFalse(limits["independently_held_out_from_training_verified"])
        self.assertFalse(limits["admitted_for_freight_error_accuracy"])
        self.assertFalse(limits["admitted_for_modern_rate_authority"])
        self.assertFalse(limits["customer_score_or_cash_promotion_allowed"])
        self.assertIsNone(limits["independent_private_customer_error_cents"])
        self.assertEqual(limits["verified_retally_recovered_cash_cents"], 0)

    def test_fmc_index_candidate_negative_controls_remain_synthetic(self):
        path = Path(__file__).with_name("fixtures") / "fmc_22fmc94_girton_index_candidate_v0.json"
        item = json.loads(path.read_text(encoding="utf-8"))
        controls = item["synthetic_negative_controls"]
        self.assertEqual(len(controls), 6)
        self.assertEqual(len({c["id"] for c in controls}), 6)
        self.assertTrue(all(c["kind"] == "SYNTHETIC" and
                            c["id"].startswith("SYNTHETIC_") for c in controls))
        self.assertEqual({c["expected"] for c in controls}, {
            "REJECT_FINAL_COMMISSION_AWARDED_INTEREST",
            "REJECT_SETTLEMENT_PAYMENT_UNKNOWN",
            "REJECT_UNRELATED_HISTORICAL_AUTHORITY",
            "REJECT_ORIGINAL_BYTES_SHA256_UNKNOWN",
            "REJECT_INTEREST_SETTLEMENT_UNKNOWN",
            "REJECT_CROSS_DOCKET_CARRIER_AND_INTEREST_COLLISION",
        })
        self.assertFalse(item["quality"]["complete_publisher_pdf_byte_read_succeeded"])
        self.assertFalse(item["quality"]["source_original_sha256_known"])
        self.assertEqual(item["quality"]["independent_commercial_customer_labels"], 0)
        bad = json.loads(json.dumps(item))
        bad["historical_decision_only"]["commission_interest_awarded"] = False
        self.assertNotEqual(bad["historical_decision_only"],
                            item["historical_decision_only"])


    def test_fmc_same_claimant_distinct_docket_interest_and_identity_hold(self):
        path = Path(__file__).with_name("fixtures") / "fmc_22fmc94_girton_index_candidate_v0.json"
        item = json.loads(path.read_text(encoding="utf-8"))
        first = item["source"]
        other = item["same_claimant_distinct_docket_counterexample"]
        self.assertEqual(other["source_class"],
                         "PUBLISHER_INDEX_EXCERPT_ONLY_SEPARATE_DECISION_NOT_PACK_ADMITTED")
        self.assertEqual(other["official_pdf_url"],
                         "https://www.fmc.gov/wp-content/uploads/2019/04/vol23.pdf")
        self.assertEqual(other["citation"], "23 F.M.C. 78")
        self.assertEqual(other["docket"], "Informal Docket 746(I)")
        self.assertEqual(other["respondent"], "Prudential Lines, Inc.")
        self.assertIn("Girton Manufacturing", first["decision_title"])
        self.assertEqual(other["claimant"], "Girton Manufacturing Company")
        self.assertEqual(other["commission_adoption_date"], "1980-07-30")
        self.assertEqual(other["shipment_bill_date"], "1977-10-30")
        self.assertEqual(other["reparation_claimed_cents"], 22476)
        self.assertIsNone(other["reparation_amount_awarded_cents"])
        self.assertTrue(other["adopted_officer_disposition_says_reparation_awarded"])
        self.assertTrue(other["offsetting_claim_denied"])
        self.assertFalse(other["final_interest_awarded"])
        self.assertTrue(item["historical_decision_only"]["commission_interest_awarded"])
        self.assertNotEqual((first["citation"], first["docket"]),
                            (other["citation"], other["docket"]))
        self.assertNotEqual(first["commission_decision_date"],
                            other["commission_adoption_date"])
        self.assertFalse(other["cross_case_join_allowed"])
        self.assertIsNone(other["commission_award_collected_cents"])
        self.assertIsNone(other["original_publisher_pdf_sha256"])
        self.assertFalse(other["original_publisher_pdf_bytes_held"])
        self.assertFalse(other["original_bill_of_lading_invoice_tariff_bytes_held"])
        self.assertFalse(other["rights_for_customer_engine_commercial_use_verified"])
        self.assertFalse(other["independently_adjudicated_invoice_ground_truth"])


if __name__ == "__main__":
    unittest.main()
