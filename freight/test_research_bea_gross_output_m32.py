"""Adversarial tests of BEA Table16 trucking source measurement and lineage.

All JSON sources below are synthetic fixtures. They validate the parser's
invariants but do NOT prove a direct original BEA file was downloaded.
The independent GitHub live job authenticates only a DBnomics HTTP
redistribution of a BEA-origin table, not BEA-original publisher bytes.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date
from decimal import Decimal
from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import patch

from freight.research_evidence_gate import canon_hash
from freight import research_bea_gross_output_m32 as m32

TODAY=date(2026,10,12)


def book():
    return json.loads(m32.BOOK.read_text(encoding="utf-8"))


def source():
    row={
        "provider_code":"BEA",
        "dataset_code":"GDPbyIndustry-16",
        "dataset_name":"Chain-Type Quantity Indexes for Gross Output by Industry",
        "series_code":"484-A",
        "series_name":"Truck transportation – Annually",
        "dimensions":{"industry":"484","FREQ":"A"},
        "indexed_at":"2026-10-01T01:31:34.369Z",
        "period":[str(y) for y in m32.YEARS],
        "value":[float(m32.EXPECTED[y]) for y in m32.YEARS],
    }
    return {
        "errors":None,
        "dataset":{
            "code":"GDPbyIndustry-16",
            "name":"Chain-Type Quantity Indexes for Gross Output by Industry",
            "indexed_at":"2026-10-01T01:31:34.369Z",
            "provider_code":"BEA",
        },
        "provider":{
            "code":"BEA",
            "name":"U.S. Bureau of Economic Analysis",
        },
        "series":{"docs":[row],"num_found":1},
    }


class BEAGrossOutputM32Tests(unittest.TestCase):
    def test_original_source_catalog_git_blob_pinned(self):
        self.assertEqual(m32._git_blob(m32.BOOK.read_bytes()),m32.BOOK_SHA1)
        self.assertEqual(m32.validate_book(book(),as_of=TODAY),[])
        self.assertEqual(book()["bea_source_table_number"],16)
        self.assertEqual(book()["source_record_series_code"],"484-A")

    def test_exact_bea_measurement_and_latest_source_vintage(self):
        b=book()
        self.assertEqual(b["bea_original_table_name"],
                         "Chain-Type Quantity Indexes for Gross Output by Industry")
        self.assertEqual(b["redistributor_dataset_indexed_at"],"2026-10-01T01:31:34.369Z")
        self.assertEqual(b["bea_release_date"],"2026-09-30")
        self.assertEqual(b["industry"],"Truck transportation")
        self.assertEqual(b["naics"],"484")

    def test_direct_original_bea_source_remains_unverified(self):
        r=m32.report_shell(as_of=TODAY)
        self.assertTrue(r["original_bea_publisher_source_verification_hold"])
        self.assertFalse(r["direct_original_bea_table16_numeric_source_bytes_authenticated"])
        self.assertFalse(book()["bea_primary_original_484_numeric_source_authenticated"])
        self.assertEqual(r["source_grade"],"BEA_ORIGIN_DBNOMICS_SECONDARY_SNAPSHOT")
        self.assertEqual(r["redistributor"],"DBnomics (CEPREMAP)")

    def test_complete_source_fixture_accepts_only_annual_bea_484_table16(self):
        result=m32.inspect_redistributor_json(source(),book=book())
        self.assertEqual(result["source_type"],"BEA_ORIGIN_DBNOMICS_THIRD_PARTY_REDISTRIBUTED")
        self.assertFalse(result["original_bea_response_verified"])
        self.assertTrue(result["distributor_api_document_verified"])
        self.assertEqual(result["annual_observations"],8)
        self.assertEqual(result["source_values"]["2024"],"108.047")
        self.assertEqual(result["source_values"]["2017"],"100.000")

    def test_all_eight_annual_years_exact_in_frozen_data(self):
        r=m32.report_shell(as_of=TODAY)
        self.assertEqual([y["year"] for y in r["bea_2017_2024_year_index"]],list(m32.YEARS))
        self.assertEqual([x["chain_type_real_gross_output_index"]
                          for x in r["bea_2017_2024_year_index"]],
                         ["100.000","102.952","102.398","103.678",
                          "109.538","108.519","107.307","108.047"])

    def test_measure_comparison_has_correct_levels_and_units(self):
        r=m32.report_shell(as_of=TODAY)
        self.assertEqual(r["bea_real_gross_output_2017_2024_change_pct"],"8.05")
        self.assertEqual(r["bls_real_sectoral_output_2017_2024_change_pct"],"4.02")
        self.assertEqual(r["m29_illustrative_revenue_ppi_proxy_2017_2024_change_pct"],"1.18")
        self.assertEqual(r["bea_minus_bls_output_descriptive_gap_pp"],"4.03")
        self.assertEqual(r["bea_minus_m29_ppi_proxy_descriptive_gap_pp"],"6.87")
        self.assertTrue(r["real_gross_output_gdp_value_added_sectoral_output_and_ppi_proxy_are_distinct"])
        self.assertTrue(r["discrepancies_are_not_independently_validated_model_errors"])

    def test_offline_evidence_does_not_claim_fresh_distributor_request(self):
        r=m32.report_shell(as_of=TODAY)
        self.assertEqual(r["status"],m32.OFFLINE)
        self.assertFalse(r["new_secondary_source_http_replayed_in_this_run"])
        self.assertEqual(r["new_secondary_api_observations_authenticated_in_this_run"],0)
        self.assertIsNone(r["new_secondary_source_http_raw_sha256"])
        self.assertEqual(r["receipt_sha256"],canon_hash({
            k:v for k,v in r.items() if k!="receipt_sha256"
        }))

    def test_synthetic_parser_is_not_original_bea_source_attestation(self):
        r=m32.verify_secondary(
            as_of=TODAY,source=source(),raw_sha256="b"*64
        )
        self.assertEqual(r["status"],m32.SECONDARY_VERIFIED)
        self.assertTrue(r["new_secondary_source_http_replayed_in_this_run"])
        self.assertEqual(r["new_secondary_api_observations_authenticated_in_this_run"],8)
        self.assertEqual(r["new_secondary_source_http_raw_sha256"],"b"*64)
        self.assertFalse(r["direct_original_bea_table16_numeric_source_bytes_authenticated"])
        self.assertEqual(r["source_grade"],
                         "BEA_ORIGIN_DB_NOMICS_THIRD_PARTY_REPLAYED_NOT_BEAPRIMARY")
        self.assertEqual(len(r["new_secondary_semantic_receipt_sha256"]),64)

    def test_reject_wrong_gdp_value_added_table_in_place_of_gross_output(self):
        for fld,val in (
            ("code","GDPbyIndustry-3"),
            ("name","Chain-Type Quantity Indexes for Value Added by Industry"),
            ("provider_code","INDEPENDENT_AUDIT"),
        ):
            s=source()
            s["dataset"][fld]=val
            with self.assertRaisesRegex(ValueError,
                                        "M32_BEA_GROSS_OUTPUT_TABLE16_MEASURE_IDENTITY_INCORRECT"):
                m32.inspect_redistributor_json(s,book=book())

    def test_reject_wrong_provider_or_direct_bea_impersonation(self):
        s=source()
        s["provider"]["name"]="Private freight overcharge auditing"
        with self.assertRaisesRegex(ValueError,
                                    "M32_BEA_GROSS_OUTPUT_TABLE16_MEASURE_IDENTITY_INCORRECT"):
            m32.inspect_redistributor_json(s,book=book())
        s=source()
        s["provider"]["code"]="FAKE"
        with self.assertRaisesRegex(ValueError,
                                    "M32_BEA_GROSS_OUTPUT_TABLE16_MEASURE_IDENTITY_INCORRECT"):
            m32.inspect_redistributor_json(s,book=book())

    def test_wrong_industry_48412_or_4841_cannot_replace_484(self):
        for dims in (
            {"industry":"48412","FREQ":"A"},
            {"industry":"4841","FREQ":"A"},
            {"industry":"484","FREQ":"Q"},
        ):
            s=source()
            s["series"]["docs"][0]["dimensions"]=dims
            with self.assertRaisesRegex(ValueError,
                                        "M32_BEA_SOURCE_NAICS_FREQUENCY_OR_VALUE_ADDED_SUBSTITUTION"):
                m32.inspect_redistributor_json(s,book=book())

    def test_reject_wrong_series_code_or_title(self):
        for k,val in (
            ("series_code","484-Q"),
            ("series_name","Truck transportation – Quarterly"),
            ("dataset_code","GDPbyIndustry-15"),
            ("dataset_name","Value Added by Industry"),
        ):
            s=source()
            s["series"]["docs"][0][k]=val
            with self.assertRaisesRegex(ValueError,
                                        "M32_BEA_SOURCE_NAICS_FREQUENCY_OR_VALUE_ADDED_SUBSTITUTION"):
                m32.inspect_redistributor_json(s,book=book())

    def test_source_indexed_before_september_2026_update_rejected(self):
        for ix in ("2026-09-29T12:00:00.000Z","2025-10-01T01:01:01.000Z","stale"):
            s=source()
            s["dataset"]["indexed_at"]=ix
            with self.assertRaisesRegex(ValueError,
                                        "M32_BEA_DATASET_PRIOR_TO_SEPTEMBER_2026_REVISION"):
                m32.inspect_redistributor_json(s,book=book())

    def test_series_duplicates_not_two_independent_economic_samples(self):
        for mutation in (
            lambda s: s["series"].update(num_found=2),
            lambda s: s["series"]["docs"].append(deepcopy(s["series"]["docs"][0])),
            lambda s: s["series"]["docs"].clear(),
        ):
            s=source()
            mutation(s)
            with self.assertRaisesRegex(ValueError,
                                        "M32_REQUIRE_EXACTLY_ONE_BEA_484_ANNUAL_SOURCE_SERIES"):
                m32.inspect_redistributor_json(s,book=book())

    def test_missing_2022_year_fails_closed(self):
        s=source()
        d=s["series"]["docs"][0]
        i=d["period"].index("2022")
        d["period"].pop(i)
        d["value"].pop(i)
        with self.assertRaisesRegex(ValueError,
                                    "M32_INCOMPLETE_BEA_GROSS_OUTPUT_2017_2024_YEAR_SERIES"):
            m32.inspect_redistributor_json(s,book=book())

    def test_duplicate_year_fails_even_when_8_years_exist(self):
        s=source()
        d=s["series"]["docs"][0]
        d["period"].append("2022")
        d["value"].append(108.519)
        with self.assertRaisesRegex(ValueError,"M32_DUPLICATE_BEAE_SOURCE_REFERENCE_YEAR"):
            m32.inspect_redistributor_json(s,book=book())

    def test_wrong_magnitude_or_float_mutation_requires_review(self):
        for year,new in ((2017,101.0),(2018,102.953),(2024,108.0)):
            s=source()
            index=s["series"]["docs"][0]["period"].index(str(year))
            s["series"]["docs"][0]["value"][index]=new
            with self.assertRaisesRegex(ValueError,
                                        "M32_BEA_TABLE16_PUBLISHED_YEAR_INDEX_DRIFT_REVIEW"):
                m32.inspect_redistributor_json(s,book=book())

    def test_invalid_suppressed_nan_private_invoice_values_rejected(self):
        for value in (None,False,"S","NaN",float("nan"),{},-1,0,10000):
            s=source()
            s["series"]["docs"][0]["value"][0]=value
            with self.assertRaises(ValueError,msg=repr(value)):
                m32.inspect_redistributor_json(s,book=book())

    def test_nonannual_source_date_not_accepted_as_year(self):
        s=source()
        s["series"]["docs"][0]["period"][0]="2017-Q1"
        with self.assertRaisesRegex(ValueError,
                                    "M32_NONANNUAL_PERIOD_IN_GROSS_OUTPUT_QUANTITY_INDEX"):
            m32.inspect_redistributor_json(s,book=book())

    def test_mismatched_period_and_value_lengths_fail(self):
        s=source()
        s["series"]["docs"][0]["value"].pop()
        with self.assertRaisesRegex(ValueError,
                                    "M32_ANNUAL_PERIOD_AND_VALUE_SOURCE_LENGTH_MISMATCH"):
            m32.inspect_redistributor_json(s,book=book())

    def test_wrong_source_json_error_flag_never_marked_verified(self):
        s=source()
        s["errors"]={"code":403,"description":"not allowed"}
        with self.assertRaisesRegex(ValueError,"M32_DBNOMICS_PUBLICATION_ERROR"):
            m32.inspect_redistributor_json(s,book=book())

    def test_bad_distributor_response_sha256_rejected(self):
        with self.assertRaisesRegex(ValueError,"M32_SECONDARY_HTTP_BODY_SHA256_INVALID"):
            m32.verify_secondary(as_of=TODAY,source=source(),raw_sha256="invalid")

    def test_source_manifest_refuses_forged_original_bea_source_validation(self):
        for field in (
            "bea_primary_original_484_numeric_source_authenticated",
            "original_bea_real_gross_output_2017_2024_verified_without_redistributor",
            "bea_real_gross_output_equals_bls_sectoral_output",
            "bea_gross_output_same_as_bea_gdp_value_added",
            "percent_change_discrepancy_equals_independent_model_error",
            "public_client_recovery_claims_authorized",
            "pilot_18_independent_approvals_satisfied",
            "scheduled_tasks_modified",
        ):
            b=book()
            b[field]=True
            self.assertTrue(m32.validate_book(b,as_of=TODAY),field)

    def test_catalog_wrong_source_url_or_vintage_fails(self):
        for field,value in (
            ("bea_release_date","2025-09-30"),
            ("redistributor_api_url","https://attacker.invalid/freight-bills"),
            ("bea_original_table_name","BEA GDP by Industry Value Added"),
            ("bea_source_table_number",3),
        ):
            b=book()
            b[field]=value
            self.assertTrue(m32.validate_book(b,as_of=TODAY),field)

    def test_original_bea_source_hold_remains_true_after_secondary_replay(self):
        verified=m32.verify_secondary(as_of=TODAY,source=source(),raw_sha256="d"*64)
        self.assertTrue(verified["original_bea_publisher_source_verification_hold"])
        self.assertFalse(verified["direct_original_bea_table16_numeric_source_bytes_authenticated"])
        self.assertTrue(verified["primary_bea_original_source_still_blocked_from_prior_m30_31"])

    def test_no_actual_freight_recoveries_or_customer_invoices_authorized(self):
        r=m32.report_shell(as_of=TODAY)
        self.assertEqual(r["lab"],14)
        self.assertFalse(r["new_lab_created"])
        self.assertEqual(r["paid_customer_freight_invoices_observed"],0)
        self.assertEqual(r["independent_customer_carrier_overcharges_found"],0)
        self.assertIsNone(r["eligible_refund_cash_proven_usd"])
        self.assertIsNone(r["freight_recovery_tam_usd"])
        self.assertIsNone(r["actual_retally_refunds_collected_usd"])
        self.assertFalse(r["external_claims_or_customer_carrier_contact_authorized"])
        self.assertTrue(r["human_pilot_18_independent_requirements_unmet"])
        self.assertFalse(r["scheduled_tasks_created_or_modified"])

    def test_source_observation_date_before_census_bea_release_rejected(self):
        self.assertTrue(m32.validate_book(book(),as_of=date(2026,10,11)))
        with self.assertRaisesRegex(ValueError,"M32_FROZEN_BEA_TABLE16_CATALOG_INVALID"):
            m32.report_shell(as_of=date(2026,10,11))

    def test_bounded_network_timeout_is_not_replayed(self):
        r=m32.blocked(as_of=TODAY)
        self.assertEqual(r["status"],m32.BLOCKED)
        self.assertFalse(r["new_secondary_source_http_replayed_in_this_run"])
        self.assertEqual(r["new_secondary_api_observations_authenticated_in_this_run"],0)
        self.assertEqual(r["receipt_sha256"],canon_hash({
            k:v for k,v in r.items() if k!="receipt_sha256"
        }))

    def test_cli_network_timeout_writes_blocked_file(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch("sys.argv",["m32","--out",folder,"--as-of-date","2026-10-12",
                                   "--fetch-secondary"]):
                with patch.object(m32,"fetch_dbnomics",side_effect=TimeoutError("source down")):
                    m32.main()
            r=json.loads((Path(folder)/"bea_gross_output.json").read_text())
            self.assertEqual(r["status"],m32.BLOCKED)
            self.assertFalse(r["new_secondary_source_http_replayed_in_this_run"])

    def test_cli_broken_available_publisher_source_not_network_block(self):
        s=source()
        s["series"]["docs"][0]["value"][-1]=999.999
        with tempfile.TemporaryDirectory() as folder:
            with patch("sys.argv",["m32","--out",folder,"--as-of-date","2026-10-12",
                                   "--fetch-secondary"]):
                with patch.object(m32,"fetch_dbnomics",return_value=(s,"d"*64)):
                    with self.assertRaisesRegex(
                        ValueError,"M32_BEA_TABLE16_PUBLISHED_YEAR_INDEX_DRIFT_REVIEW"
                    ):
                        m32.main()

    def test_html_renders_eight_years_and_escapes_untrusted_metadata(self):
        r=m32.report_shell(as_of=TODAY)
        r["caveat"]="<script>alert('freight audit')</script>"
        h=m32.render_html(r)
        self.assertIn("&lt;script&gt;",h)
        self.assertNotIn("<script>",h)
        self.assertIn("NOT a directly authenticated original BEA",h)
        self.assertIn("2017",h)
        self.assertIn("2024",h)

    def test_report_hash_is_deterministic(self):
        r=m32.report_shell(as_of=TODAY)
        self.assertEqual(r["receipt_sha256"],canon_hash({
            k:v for k,v in r.items() if k!="receipt_sha256"
        }))


if __name__=="__main__":
    unittest.main()
