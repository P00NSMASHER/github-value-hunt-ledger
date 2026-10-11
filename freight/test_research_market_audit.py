"""Mission 12 adversarial first-party public CFS source-math checks."""
from __future__ import annotations

from copy import deepcopy
from datetime import date
import json
import unittest

from freight.research_evidence_gate import canon_hash
from freight.research_market_audit import (
    AUDIT, build_market_audit, render_html, validate_catalog,
)
from freight.research_validation_protocols import build_protocol_report

AS_OF = date(2026, 10, 11)


def fixture():
    return json.loads(AUDIT.read_text(encoding="utf-8")), build_protocol_report(as_of=AS_OF)


def mutated_row(ident: str, key: str, value):
    book, p = fixture()
    r = next(r for r in book["table_rows"] if r["id"] == ident)
    r[key] = value
    return book, p


class PublishedFreightResearchTests(unittest.TestCase):
    def test_official_excerpt_reconciles_exact_truck_components(self):
        book, p = fixture()
        self.assertEqual(validate_catalog(book, p, as_of=AS_OF), [])
        r = build_market_audit(as_of=AS_OF, book=book, protocols=p)
        self.assertEqual(r["source_count"], 3)
        self.assertEqual(r["table_excerpt_rows"], 6)
        t = r["published_estimate_measurements"]
        self.assertEqual(t["total_value_million_usd"], 17996782)
        self.assertEqual(t["total_weight_thousand_tons"], 12169793)
        self.assertEqual(t["all_single_mode_truck_value_million_usd"], 13222965)
        self.assertEqual(t["for_hire_truck_value_million_usd"], 8062541)
        self.assertEqual(t["company_owned_truck_value_million_usd"], 4141550)
        self.assertEqual(t["customer_pickup_value_million_usd"], 1018874)
        self.assertEqual(8062541 + 4141550 + 1018874, 13222965)
        self.assertEqual(3909476 + 2994372 + 1389653, 8293501)
        self.assertTrue(t["truck_mode_value_components_equal_source_total"])
        self.assertTrue(t["truck_mode_weight_components_equal_source_total"])
        self.assertEqual(r["receipt_sha256"], canon_hash({
            k: v for k, v in r.items() if k != "receipt_sha256"
        }))

    def test_source_math_shares_are_independent_of_press_denominators(self):
        t = build_market_audit(as_of=AS_OF)["published_estimate_measurements"]
        self.assertEqual(t["truck_value_share_of_all_shipments_pct"], "73.47")
        self.assertEqual(t["truck_weight_share_of_all_shipments_pct"], "68.15")
        self.assertEqual(t["for_hire_truck_value_share_of_all_shipments_pct"], "44.80")
        self.assertEqual(t["for_hire_truck_weight_share_of_all_shipments_pct"], "32.12")
        self.assertEqual(t["for_hire_value_share_of_truck_total_pct"], "60.97")
        self.assertEqual(t["company_owned_value_share_of_truck_total_pct"], "31.32")
        self.assertEqual(t["customer_pickup_value_share_of_truck_total_pct"], "7.71")

    def test_quoted_press_truck_percent_is_consistent_with_detailed_table(self):
        r = build_market_audit(as_of=AS_OF)
        p = r["press_release_reconciliation"]
        self.assertTrue(p["truck_value_pct_agrees_with_detailed_table"])
        self.assertTrue(p["truck_weight_pct_agrees_with_detailed_table"])
        self.assertTrue(p["all_modes_shipment_value_agrees_at_press_precision"])
        self.assertTrue(p["all_modes_shipment_weight_agrees_at_press_precision"])
        self.assertEqual(len(p["regional_flagged_conflicts"]), 1)

    def test_south_region_published_press_claim_is_quarantined(self):
        r = build_market_audit(as_of=AS_OF)
        conflict = r["press_release_reconciliation"]["regional_flagged_conflicts"][0]
        self.assertEqual(conflict["status"], "UNRESOLVED_FIRST_PARTY_PUBLICATION_CONTRADICTION")
        self.assertEqual(conflict["press_release_billion_tons"], "1.9")
        self.assertEqual(conflict["press_release_south_share_pct"], "40.4")
        self.assertEqual(conflict["official_detailed_table_thousand_tons"], 4919551)
        self.assertEqual(conflict["official_table_south_share_pct_calculated"], "40.42")
        self.assertEqual(conflict["press_release_claimed_tonnage_as_share_pct_calculated"], "15.61")
        self.assertTrue(conflict["table_share_consistent_with_press_percent"])
        self.assertFalse(conflict["press_tonnage_consistent_with_table"])
        self.assertFalse(conflict["automatic_correction_authorized"])
        self.assertFalse(conflict["press_number_cleared_for_use"])

    def test_survey_value_is_not_ltl_freight_or_recoverable_invoice_value(self):
        r = build_market_audit(as_of=AS_OF)
        t = r["published_estimate_measurements"]
        for k in (
            "actual_paid_ltl_freight_invoices_count",
            "paid_ltl_invoice_spend_usd",
            "freight_audit_addressable_market_usd",
            "verified_overcharge_prevalence",
            "actual_contingency_revenue_usd",
        ):
            self.assertIsNone(t[k], k)
        self.assertTrue(t["for_hire_is_not_ltl_only"])
        self.assertTrue(t["includes_company_owned_and_customer_pickup"])
        self.assertTrue(t["survey_values_not_freight_bills"])
        self.assertTrue(t["truck_mode_2017_to_2022_definition_changed_customer_pickup_added"])
        self.assertFalse(r["market_ranking_or_recovery_tam_established"])
        self.assertFalse(r["buyer_demand_confirmed"])
        self.assertFalse(r["performance_marketing_claims_allowed"])

    def test_all_three_buyer_types_are_hypotheses_not_verified_opportunities(self):
        r = build_market_audit(as_of=AS_OF)
        rows = r["prospective_buyer_research_hypotheses"]
        self.assertEqual([x["id"] for x in rows],
                         ["manufacturing", "wholesale", "distribution"])
        self.assertTrue(all(
            x["claim_status"] == "EXPLICIT_UNTESTED_BUYER_HYPOTHESIS"
            and x["actual_ltl_invoice_spend_measured"] is False
            and x["independent_customer_evidence"] == 0
            and x["commercial_recommendation_authorized"] is False
            for x in rows
        ))

    def test_missing_raw_archive_and_no_external_observation_are_explicit(self):
        book, p = fixture()
        r = build_market_audit(as_of=AS_OF, book=book, protocols=p)
        self.assertFalse(r["raw_zip_data_downloaded"])
        self.assertFalse(r["independent_full_table_replication_completed"])
        self.assertFalse(r["real_customer_or_invoice_data_ingested"])
        self.assertFalse(r["customer_contact_or_carrier_actions_allowed"])
        self.assertEqual(r["existing_lab_number"], 14)
        self.assertFalse(r["new_lab_created"])
        self.assertFalse(r["source_review_is_stale"])
        self.assertEqual(r["source_audit_record_sha256"], canon_hash(book))
        self.assertEqual(r["protocol_receipt_sha256"], p["receipt_sha256"])

    def test_number_of_official_table_followups_is_constrained(self):
        r = build_market_audit(as_of=AS_OF)
        self.assertEqual([x["table_id"] for x in r["source_request_backlog"]],
                         ["CF2200A18", "CF2200A19", "CF2200A01"])
        self.assertTrue(all(x["download_approved"] is False
                            for x in r["source_request_backlog"]))

    def test_stale_review_requires_rechecking_and_never_renews_source(self):
        r = build_market_audit(as_of=date(2027, 2, 1))
        self.assertTrue(r["source_review_is_stale"])
        self.assertEqual(r["source_count"], 3)
        self.assertFalse(r["performance_marketing_claims_allowed"])
        self.assertFalse(r["independent_full_table_replication_completed"])

    def test_tampered_primary_survey_row_does_not_get_new_verified_hash(self):
        for ident, key, value in (
            ("us.forhire.2022", "value_million_usd", 9000000),
            ("us.company.2022", "weight_thousand_tons", 2994372000),
            ("south.allmodes.2022", "weight_thousand_tons", 1900000),
            ("us.truck.2022", "mode_code", "111"),
            ("us.truck.2022", "geo_class", "REGION"),
            ("us.truck.2022", "year", 2017),
            ("us.allmodes.2022", "value_million_usd", 17996782000),
        ):
            book, p = mutated_row(ident, key, value)
            errors = validate_catalog(book, p, as_of=AS_OF)
            self.assertTrue(errors, (ident, key))
            with self.assertRaisesRegex(ValueError, "INVALID_CFS_SOURCE_AUDIT"):
                build_market_audit(as_of=AS_OF, book=book, protocols=p)

    def test_source_press_clips_are_not_independent_original_csv_downloads(self):
        for key in (
            "raw_zip_downloaded", "original_csv_contents_examined",
            "independent_issuer_signature_verified",
            "commercial_market_tam_established", "public_performance_claims_permitted",
            "actual_ltl_invoice_spend_measured", "new_lab_created",
        ):
            book, p = fixture()
            book[key] = True
            self.assertIn("unapproved source truth", "; ".join(
                validate_catalog(book, p, as_of=AS_OF)), key)

    def test_fabricated_file_checksum_without_zip_is_rejected(self):
        book, p = fixture()
        book["upstream_zip_sha256"] = "f" * 64
        self.assertIn("original source archive was not downloaded", "; ".join(
            validate_catalog(book, p, as_of=AS_OF)))

    def test_forged_customer_records_or_invoice_stats_are_rejected(self):
        for key, value in (
            ("invoice_level_records_received", 4),
            ("real_buyer_data_ingested", True),
            ("claim_submission_or_fee_authorized", True),
        ):
            book, p = fixture()
            book[key] = value
            self.assertTrue(validate_catalog(book, p, as_of=AS_OF), key)

    def test_press_numbers_cannot_be_relabelled_as_freight_prices(self):
        for key, value in (
            ("truck_mode_value_pct", 80.0),
            ("south_claimed_billion_tons", 4.9),
            ("manufacturing_rounded_trillion_usd", 15.0),
            ("wholesale_rounded_billion_tons", 0),
        ):
            book, p = fixture()
            book["press_release"][key] = value
            self.assertIn("Census press excerpt number modified", "; ".join(
                validate_catalog(book, p, as_of=AS_OF)), key)
        book, p = fixture()
        book["press_release"]["claimed_price_or_invoice_field_present"] = True
        self.assertIn("no verified freight billing", "; ".join(
            validate_catalog(book, p, as_of=AS_OF)))

    def test_original_press_south_error_cannot_be_cleared_silently(self):
        book, p = fixture()
        book["press_release"]["press_south_tonnage_consistent_with_percent"] = True
        self.assertIn("unresolved South regional press contradiction", "; ".join(
            validate_catalog(book, p, as_of=AS_OF)))

    def test_malformed_missing_or_crosslinked_published_sources_rejected(self):
        for key, value in (
            ("publisher", "Disinformation Author"),
            ("url", "https://attacker.example/fake-census"),
            ("review_method", "RAW_ZIP_VERIFIED"),
            ("publication_date", "2026-10-11"),
            ("raw_dataset_downloaded", True),
        ):
            book, p = fixture()
            book["sources"][0][key] = value
            self.assertTrue(validate_catalog(book, p, as_of=AS_OF), key)
        book, p = fixture()
        book["sources"].append(deepcopy(book["sources"][0]))
        self.assertTrue(validate_catalog(book, p, as_of=AS_OF))
        book, p = fixture()
        book["table_rows"][0]["source_id"] = "cfs.2022.press.release"
        self.assertIn("unbound Census vintage", "; ".join(
            validate_catalog(book, p, as_of=AS_OF)))

    def test_2017_to_2022_mode_definitions_cannot_be_mixed(self):
        book, p = mutated_row("us.truck.2022", "year", 2017)
        self.assertTrue(validate_catalog(book, p, as_of=AS_OF))
        book, p = fixture()
        book["survey_year"] = 2017
        self.assertIn("unsupported survey vintage", "; ".join(
            validate_catalog(book, p, as_of=AS_OF)))

    def test_vertical_hypothesis_cannot_be_promoted_into_verified_buyer(self):
        for key, value in (
            ("buyer_authorization_observed", True),
            ("carrier_mode_LTL_confirmed", True),
            ("invoice_spend_measured", True),
            ("demand_validated", True),
            ("source_group", "VERIFIED_INDEPENDENT_BUYER_STUDY"),
            ("source_field", "private.invoice.file"),
            ("research_priority_not_market_ranking", False),
        ):
            book, p = fixture()
            book["candidate_verticals"][0][key] = value
            self.assertTrue(validate_catalog(book, p, as_of=AS_OF), key)

    def test_unknown_market_opportunity_or_customer_payload_fields_rejected(self):
        book, p = fixture()
        book["annual_recovery_tam_usd"] = 20_000_000
        self.assertIn("unauthorized CFS snapshot schema", "; ".join(
            validate_catalog(book, p, as_of=AS_OF)))
        book, p = fixture()
        book["table_rows"][0]["confidential_carrier_invoice"] = "do not use"
        self.assertIn("wrong row shape", "; ".join(
            validate_catalog(book, p, as_of=AS_OF)))

    def test_fake_external_license_and_future_review_not_admitted(self):
        book, p = fixture()
        book["sources"][0]["observed_on"] = "2026-12-01"
        self.assertTrue(validate_catalog(book, p, as_of=AS_OF))
        book, p = fixture()
        book["research_as_of"] = "2027-01-01"
        self.assertIn("future market observation", "; ".join(
            validate_catalog(book, p, as_of=AS_OF)))

    def test_malformed_nested_types_are_errors_not_stack_traces(self):
        for key, bad in (
            ("sources", [0, None, []]),
            ("press_release", {"foo": []}),
            ("table_rows", ["invalid"] * 6),
            ("candidate_verticals", ["raw"] * 3),
            ("open_research_tasks", [1, 2, 3]),
        ):
            book, p = fixture()
            book[key] = bad
            self.assertTrue(validate_catalog(book, p, as_of=AS_OF), key)
            with self.assertRaisesRegex(ValueError, "INVALID_CFS_SOURCE_AUDIT"):
                build_market_audit(as_of=AS_OF, book=book, protocols=p)

    def test_rehashed_forged_original_study_is_still_denied(self):
        book, p = fixture()
        p["external_studies_executed"] = 1
        p["receipt_sha256"] = canon_hash({
            k: v for k, v in p.items() if k != "receipt_sha256"
        })
        self.assertIn("unchanged, held Mission 7", "; ".join(
            validate_catalog(book, p, as_of=AS_OF)))

    def test_html_harmless_source_context_and_escape(self):
        r = build_market_audit(as_of=AS_OF)
        dirty = deepcopy(r)
        dirty["prospective_buyer_research_hypotheses"][0]["industry_claim"] = (
            '<script>alert("test")</script>')
        html = render_html(dirty)
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertIn("Freight exposure is not freight-recovery revenue.", html)
        self.assertIn("South", html)
        self.assertIn("The original ZIP was NOT downloaded", html)

    def test_reports_are_stable_and_local_hashes_not_external_validation(self):
        a = build_market_audit(as_of=AS_OF)
        b = build_market_audit(as_of=AS_OF)
        self.assertEqual(a, b)
        self.assertEqual(a["source_count"], 3)
        self.assertFalse(a["independent_full_table_replication_completed"])
        self.assertIn("not carrier freight invoice", a["limitations"])
        self.assertEqual(a["existing_lab_number"], 14)
        self.assertFalse(a["new_lab_created"])


if __name__ == "__main__":
    unittest.main()
