"""Negative-control QA: dated public freight metadata != licensed invoice proof."""
from __future__ import annotations

from copy import deepcopy
from datetime import date
import json
import unittest

from freight.research_evidence_gate import canon_hash
from freight.research_data_readiness import (
    BOOK, build_readiness, render_html, validate_catalog,
)
from freight.research_validation_protocols import build_protocol_report

DAY = date(2026, 10, 10)


def fixture():
    return json.loads(BOOK.read_text(encoding="utf-8")), build_protocol_report(as_of=DAY)


def altered(ident, key, value):
    book, protocols = fixture()
    next(s for s in book["sources"] if s["id"] == ident)[key] = value
    return book, protocols


class PublicFreightDataReadinessTests(unittest.TestCase):
    def test_seven_leads_and_zero_real_world_benchmarks(self):
        book, protocols = fixture()
        self.assertEqual(validate_catalog(book, protocols, as_of=DAY), [])
        r = build_readiness(as_of=DAY, book=book, protocols=protocols)
        self.assertEqual(r["source_leads"], 7)
        self.assertEqual(r["datasets_imported"], 0)
        self.assertEqual(r["rights_cleared_reuse_count"], 0)
        self.assertEqual(r["invoice_ground_truth_benchmarks"], 0)
        self.assertEqual(r["independently_verified_recovery_benchmarks"], 0)
        self.assertFalse(r["live_customer_or_carrier_data_used"])
        self.assertFalse(r["external_source_content_fetched"])
        self.assertFalse(r["automated_network_or_schedule"])
        self.assertFalse(r["public_performance_claims_allowed"])
        self.assertFalse(r["new_lab_created"])
        self.assertEqual(r["existing_lab_number"], 14)
        self.assertEqual(r["catalog_sha256"], canon_hash(book))
        self.assertEqual(r["protocol_report_sha256"], protocols["receipt_sha256"])
        self.assertEqual(r["receipt_sha256"], canon_hash({
            k:v for k,v in r.items() if k != "receipt_sha256"
        }))
        self.assertTrue(all(
            s["status"] == "PUBLIC_METADATA_CATALOGUED_NOT_ADMITTED"
            and s["import_or_republish_allowed"] is False
            and s["can_run_customer_accuracy_benchmark"] is False
            for s in r["review_queue"]
        ))

    def test_granularity_and_shared_lineage_not_double_counted(self):
        r = build_readiness(as_of=DAY)
        c = r["source_grain_counts"]
        self.assertEqual(c["PUBLIC_USE_SHIPMENT_MICRODATA"], 1)
        self.assertEqual(c["ESTIMATED_AGGREGATE_FLOW"], 1)
        self.assertEqual(c["PUBLISHED_AGGREGATE_STATISTICS"], 2)
        self.assertEqual(c["PUBLISHED_EDI_EXAMPLE_NOT_A_REAL_VERIFIED_INVOICE"], 2)
        self.assertEqual(c["STANDARD_DESCRIPTION_ONLY"], 1)
        self.assertEqual(
            r["lineage_family_counts"]["CFS_FAF_2022_INTERDEPENDENT"], 4
        )
        self.assertEqual(
            r["lineage_family_counts"]["EDIFABRIC_210_EXAMPLE_ORIGIN_UNCERTAIN"], 2
        )

    def test_only_market_or_edi_discovery_has_leads_not_truth(self):
        r = build_readiness(as_of=DAY)
        by = r["related_protocols"]
        self.assertEqual(by["M7-04"]["candidate_count"], 4)
        self.assertEqual(by["M7-05"]["candidate_count"], 3)
        for p in ("M7-01", "M7-02", "M7-03", "M7-06"):
            self.assertEqual(by[p]["candidate_count"], 0)
        self.assertTrue(all(v["independent_real_world_benchmark_sets"] == 0
                            and v["method_is_verified"] is False
                            for v in by.values()))

    def test_source_order_is_internal_priority_not_verification(self):
        r = build_readiness(as_of=DAY)
        self.assertEqual([x["research_priority_ordinal_not_market_quality"]
                          for x in r["review_queue"]], list(range(1, 8)))
        self.assertEqual(r["review_queue"][0]["source_id"], "census.cfs2022.pums")
        self.assertEqual(r["review_queue"][1]["source_id"], "bts.faf6.regional")
        self.assertTrue(all(len(x["decision_blockers"]) == 4
                            for x in r["review_queue"]))

    def test_fake_downloaded_bytes_or_cryptographic_proof_rejected(self):
        for key,value in (
            ("source_content_downloaded", True),
            ("data_bytes_examined", True),
            ("checksum_of_downloaded_bytes", "a"*64),
        ):
            b,p = altered("census.cfs2022.pums", key, value)
            errors = validate_catalog(b,p,as_of=DAY)
            self.assertTrue(errors, key)
            with self.assertRaisesRegex(ValueError, "INVALID_PUBLIC_FREIGHT_SOURCE_CATALOG"):
                build_readiness(as_of=DAY, book=b, protocols=p)

    def test_forged_usage_rights_are_not_granted_by_public_website(self):
        for key in ("rights_cleared_for_internal_reuse",
                    "rights_cleared_for_redistribution",
                    "privacy_clearance_completed"):
            b,p = altered("edifabric.edi210.sample", key, True)
            self.assertIn(key, "; ".join(validate_catalog(b,p,as_of=DAY)))
        b,p = altered("github.freighttrust.x12examples",
                      "rights_evidence", "MIT_PUBLIC_LICENSE_VERIFIED")
        self.assertIn("rights falsely cleared", "; ".join(
            validate_catalog(b,p,as_of=DAY)))

    def test_unlicensed_github_visibility_never_counts_as_invoice_truth(self):
        for key in ("independent_invoice_ground_truth_present",
                    "independent_recovery_ground_truth_present",
                    "may_support_customer_accuracy_claims",
                    "any_customer_case_ingested"):
            b,p = altered("github.freighttrust.x12examples", key, True)
            self.assertIn(key, "; ".join(validate_catalog(b,p,as_of=DAY)))
        r = build_readiness(as_of=DAY)
        row = next(x for x in r["review_queue"]
                   if x["source_id"] == "github.freighttrust.x12examples")
        self.assertEqual(row["license_status"],
                         "NO_ROOT_LICENSE_OBSERVED_AND_UPSTREAM_PROVENANCE_UNRESOLVED")
        self.assertFalse(row["license_cleared"])

    def test_no_metadata_source_can_claim_study_01_success(self):
        b,p = altered("census.cfs2022.pums", "linked_protocols", ["M7-01"])
        self.assertIn("unapproved research protocol", "; ".join(
            validate_catalog(b,p,as_of=DAY)))
        b,p = altered("edifabric.edi210.sample", "linked_protocols",
                      ["M7-01", "M7-05"])
        self.assertTrue(validate_catalog(b,p,as_of=DAY))

    def test_forged_invoice_granularity_rejected(self):
        b,p = altered("bts.faf6.regional", "grain", "REAL_CUSTOMER_BILLING_GROUND_TRUTH")
        self.assertIn("grain laundered", "; ".join(validate_catalog(b,p,as_of=DAY)))
        b,p = altered("edifabric.edi210.sample", "source_kind", "OFFICIAL_FEDERAL_DATASET")
        self.assertIn("authority/source type changed", "; ".join(
            validate_catalog(b,p,as_of=DAY)))

    def test_fabricated_released_license_or_concealed_overlap_rejected(self):
        b,p = altered("census.cfs2022.api", "rights_evidence", "CC0")
        self.assertIn("rights falsely cleared", "; ".join(
            validate_catalog(b,p,as_of=DAY)))
        b,p = altered("bts.faf6.regional", "lineage_family", "INDEPENDENT_INVOICE_TAM")
        self.assertIn("source dependence concealed", "; ".join(
            validate_catalog(b,p,as_of=DAY)))

    def test_source_url_and_host_are_bound(self):
        b,p = altered("census.cfs2022.pums", "url",
                      "https://www.census.gov.example.com/phish")
        self.assertIn("source URL provenance mismatched", "; ".join(
            validate_catalog(b,p,as_of=DAY)))
        for uri in ("http://www.census.gov/data",
                    "https://attacker.example/fake",
                    "https://user:password@www.census.gov/",
                    "https://www.census.gov/#fake"):
            b,p = altered("census.cfs2022.pums", "documentation_url", uri)
            self.assertTrue(validate_catalog(b,p,as_of=DAY), uri)

    def test_publisher_and_research_document_are_version_pinned(self):
        b,p = altered("census.cfs2022.pums", "publisher", "Fake Census Authority")
        self.assertIn("publisher provenance mismatched", "; ".join(
            validate_catalog(b,p,as_of=DAY)))
        b,p = altered("bts.faf6.regional", "documentation_url",
                      "https://www.bts.gov/other-data")
        self.assertIn("documentation URL provenance mismatched", "; ".join(
            validate_catalog(b,p,as_of=DAY)))
        b,p = altered("census.cfs2022.pums", "release_on", "2025-01-01")
        self.assertIn("source release chronology", "; ".join(
            validate_catalog(b,p,as_of=DAY)))

    def test_duplicate_and_removed_source_are_rejected(self):
        b,p = fixture()
        b["sources"][1]["id"] = b["sources"][0]["id"]
        self.assertIn("duplicate/unknown", "; ".join(
            validate_catalog(b,p,as_of=DAY)))
        b,p = fixture()
        b["sources"].pop()
        self.assertTrue(validate_catalog(b,p,as_of=DAY))
        b,p = fixture()
        b["sources"].append(deepcopy(b["sources"][0]))
        self.assertTrue(validate_catalog(b,p,as_of=DAY))

    def test_unknown_personal_or_bank_fields_are_rejected(self):
        b,p = fixture()
        b["sources"][0]["customer_name"] = "private party"
        self.assertIn("unexpected fields", "; ".join(
            validate_catalog(b,p,as_of=DAY)))
        b,p = fixture()
        b["source_file_path"] = "/customer/invoices"
        self.assertIn("unexpected top-level", "; ".join(
            validate_catalog(b,p,as_of=DAY)))

    def test_source_dates_must_not_claim_future_capture(self):
        for key,value in (
            ("reviewed_on", "2026-10-11"),
            ("release_on", "2026-10-11"),
            ("release_on", "not-a-date"),
        ):
            b,p = altered("census.cfs2022.pums",key,value)
            self.assertTrue(validate_catalog(b,p,as_of=DAY), key)
        b,p = fixture()
        b["research_as_of"] = "2030-01-01"
        self.assertTrue(validate_catalog(b,p,as_of=DAY))

    def test_no_download_or_benchmark_can_be_activated(self):
        b,p = fixture()
        for k,v in (
            ("datasets_reproduced_locally", 1),
            ("actual_invoice_benchmark_count", 2),
            ("data_imports_authorized", True),
            ("automatic_network_requests_authorized", True),
            ("real_invoice_accuracy_claims_authorized", True),
        ):
            bad = deepcopy(b)
            bad[k] = v
            self.assertTrue(validate_catalog(bad,p,as_of=DAY),k)

    def test_strict_integer_not_bool_counts(self):
        b,p = fixture()
        b["actual_invoice_benchmark_count"] = False
        self.assertTrue(validate_catalog(b,p,as_of=DAY))
        b,p = fixture()
        b["datasets_reproduced_locally"] = False
        self.assertTrue(validate_catalog(b,p,as_of=DAY))

    def test_upstream_protocol_receipt_and_permissions_cannot_be_forged(self):
        b,p = fixture()
        bad = deepcopy(p)
        bad["protocols"][0]["title"] = "tampered approval"
        self.assertIn("unmodified, held Mission 7", "; ".join(
            validate_catalog(b,bad,as_of=DAY)))
        bad = deepcopy(p)
        bad["external_studies_executed"] = 1
        self.assertTrue(validate_catalog(b,bad,as_of=DAY))
        bad = deepcopy(p)
        bad["public_performance_claims_allowed"] = True
        self.assertTrue(validate_catalog(b,bad,as_of=DAY))

    def test_html_escape_malicious_source_text(self):
        r = build_readiness(as_of=DAY)
        bad = deepcopy(r)
        bad["review_queue"][0]["name"] = '<script>alert("bad")</script>'
        bad["review_queue"][0]["limitations"] = '<img src=x onerror=alert(1)>'
        html = render_html(bad)
        self.assertNotIn("<script>", html)
        self.assertNotIn("<img ", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertIn("Seven public source leads", html)

    def test_replay_is_deterministic_not_fake_new_verification(self):
        self.assertEqual(build_readiness(as_of=DAY),build_readiness(as_of=DAY))
        later=build_readiness(as_of=date(2027,2,1))
        self.assertEqual(later["datasets_imported"],0)
        self.assertEqual(later["invoice_ground_truth_benchmarks"],0)
        self.assertFalse(later["public_performance_claims_allowed"])
        self.assertEqual(later["metadata_refresh_window_days"],90)
        self.assertEqual(later["metadata_sources_due_for_recheck"],7)
        self.assertTrue(all(x["status"]=="PUBLIC_METADATA_STALE_RECHECK"
                            and x["source_recheck_due"] for x in later["review_queue"]))

    def test_row_malformed_nested_scalar_is_held_not_promoted(self):
        for key,value in (
            ("documentation_url", {}),
            ("rights_evidence", []),
            ("linked_protocols", {"bad":"M7-01"}),
            ("reviewed_on", 23),
        ):
            b,p = altered("census.cfs2022.pums",key,value)
            self.assertTrue(validate_catalog(b,p,as_of=DAY),key)


if __name__ == "__main__":
    unittest.main()
