"""Mission 31 adversarial original BLS Industry Productivity output series tests.

Synthetic fixtures verify parsing and negative safety properties, not an
independent original publisher fetch. Separate CI must verify the complete
24 annual BLS IPU records via an actual BLS v2 HTTPS request.
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
from freight import research_bls_sectoral_output_m31 as m31

TODAY=date(2026,10,12)


def catalog():
    return json.loads(m31.BOOK.read_text(encoding="utf-8"))


def synthetic_bls():
    series=[]
    for item in reversed(catalog()["series"]):
        rows=[]
        for year in reversed(m31.YEARS):
            rows.append({
                "year":str(year),"period":"A01",
                "value":item["values_by_year"][str(year)],
                "footnotes":[{}],
            })
        series.append({"seriesID":item["native_bls_id"],"data":rows})
    return {"status":"REQUEST_SUCCEEDED","message":[],"Results":{"series":series}}


class OriginalBLSSectoralOutputTests(unittest.TestCase):
    def test_catalog_git_blob_and_direct_native_ipu_identifiers(self):
        self.assertEqual(m31._blob_id(m31.BOOK.read_bytes()),m31.BOOK_SHA1)
        self.assertEqual(m31.validate_catalog(catalog(),as_of=TODAY),[])
        self.assertEqual(m31.IDS,(
            "IPUIN484___T010000000",
            "IPUIN4841__T010000000",
            "IPUIN48412_T010000000",
        ))
        self.assertEqual(catalog()["source_grain"],
                         "ANNUAL_A01_NOT_SEASONALLY_ADJUSTED_2017_EQUALS_100")

    def test_all_native_annual_source_grains_are_24_genuine_year_cells(self):
        source=catalog()
        self.assertEqual(sum(len(s["values_by_year"]) for s in source["series"]),24)
        self.assertEqual(source["source_years"],list(m31.YEARS))
        self.assertEqual([s["naics"] for s in source["series"]],list(m31.CODES))
        self.assertTrue(all(s["values_by_year"]["2017"]=="100.000"
                            for s in source["series"]))

    def test_raw_bls_v2_complete_three_source_fixture_is_parsed(self):
        got=m31.validate_original_bls_response(synthetic_bls(),catalog=catalog())
        self.assertEqual(set(got),set(m31.IDS))
        self.assertEqual(sum(len(x) for x in got.values()),24)
        self.assertEqual(got["IPUIN484___T010000000"][2024],"104.019")
        self.assertEqual(got["IPUIN4841__T010000000"][2024],"105.912")
        self.assertEqual(got["IPUIN48412_T010000000"][2024],"102.984")

    def test_annual_source_cannot_be_silently_replaced_with_fred_alias(self):
        bad=synthetic_bls()
        bad["Results"]["series"][0]["seriesID"]="IPUIN48412T010000000"
        with self.assertRaisesRegex(ValueError,"M31_WRONG_NATIVE_BLS_ID_FRED_ALIAS_OR_DUPLICATE"):
            m31.validate_original_bls_response(bad,catalog=catalog())

    def test_wrong_source_id_even_with_correct_economic_values_rejected(self):
        for i in range(3):
            data=synthetic_bls()
            data["Results"]["series"][i]["seriesID"]="IPUIN484T010000000"
            with self.assertRaisesRegex(ValueError,"M31_WRONG_NATIVE_BLS_ID_FRED_ALIAS_OR_DUPLICATE"):
                m31.validate_original_bls_response(data,catalog=catalog())

    def test_one_series_missing_rejected(self):
        data=synthetic_bls()
        data["Results"]["series"].pop()
        with self.assertRaisesRegex(ValueError,"M31_EXACTLY_THREE_INDUSTRY_SOURCE_SERIES_REQUIRED"):
            m31.validate_original_bls_response(data,catalog=catalog())

    def test_duplicate_series_cannot_fake_three_industries(self):
        data=synthetic_bls()
        data["Results"]["series"][1]["seriesID"]=data["Results"]["series"][0]["seriesID"]
        with self.assertRaisesRegex(ValueError,"M31_WRONG_NATIVE_BLS_ID_FRED_ALIAS_OR_DUPLICATE"):
            m31.validate_original_bls_response(data,catalog=catalog())

    def test_one_missing_year_source_detected(self):
        for i in range(3):
            data=synthetic_bls()
            data["Results"]["series"][i]["data"].pop()
            with self.assertRaisesRegex(ValueError,"M31_EIGHT_SOURCE_ANNUAL_VALUES_REQUIRED"):
                m31.validate_original_bls_response(data,catalog=catalog())

    def test_year_2025_outside_requested_history_rejected(self):
        data=synthetic_bls()
        data["Results"]["series"][0]["data"][0]["year"]="2025"
        with self.assertRaisesRegex(ValueError,"M31_BLS_OUTPUT_YEAR_OUT_OF_RANGE"):
            m31.validate_original_bls_response(data,catalog=catalog())

    def test_monthly_and_annual_average_wrong_period_must_fail(self):
        for period in ("M01","M12","M13","A02","S01","Q01",""):
            data=synthetic_bls()
            data["Results"]["series"][0]["data"][0]["period"]=period
            with self.assertRaisesRegex(ValueError,"M31_BLS_REAL_SECTORAL_OUTPUT_NOT_ANNUAL_A01",
                                        msg=period):
                m31.validate_original_bls_response(data,catalog=catalog())

    def test_duplicate_year_does_not_replace_missing_year(self):
        data=synthetic_bls()
        data["Results"]["series"][0]["data"].append(deepcopy(
            data["Results"]["series"][0]["data"][0]
        ))
        with self.assertRaisesRegex(ValueError,"M31_DUPLICATED_BLS_SECTORAL_OUTPUT_YEAR"):
            m31.validate_original_bls_response(data,catalog=catalog())

    def test_bls_http_200_but_series_does_not_exist_is_error(self):
        data=synthetic_bls()
        data["message"]=["Series does not exist for Series IPUIN484T010000000"]
        with self.assertRaisesRegex(ValueError,"M31_BLS_IP_API_ERROR_DIAGNOSTIC_OR_WRONG_ALIAS"):
            m31.validate_original_bls_response(data,catalog=catalog())

    def test_request_failed_must_not_be_certified(self):
        data=synthetic_bls()
        data["status"]="REQUEST_FAILED"
        with self.assertRaisesRegex(ValueError,"M31_BLS_IP_API_NOT_REQUEST_SUCCEEDED"):
            m31.validate_original_bls_response(data,catalog=catalog())

    def test_flagged_preliminary_source_row_must_fail(self):
        data=synthetic_bls()
        data["Results"]["series"][0]["data"][0]["footnotes"]=[
            {"code":"P","text":"Preliminary"}
        ]
        with self.assertRaisesRegex(ValueError,"M31_PRELIMINARY_SUPPRESSED_OR_FLAGGED_SOURCE_VALUE"):
            m31.validate_original_bls_response(data,catalog=catalog())

    def test_revised_value_from_government_not_silently_backfilled(self):
        for i in range(3):
            data=synthetic_bls()
            data["Results"]["series"][i]["data"][0]["value"]="999.999"
            with self.assertRaisesRegex(ValueError,"M31_BLS_OFFICIAL_SOURCE_VALUE_CHANGED_REQUIRES_REVIEW"):
                m31.validate_original_bls_response(data,catalog=catalog())

    def test_non_numeric_zero_sentinel_bool_suppression_rejected(self):
        for value in (None,False,0,"","NaN","S","-1","0","0.000","120.456789",123.45,{},[]):
            with self.assertRaises(ValueError,msg=repr(value)):
                m31._source_decimal(value)

    def test_output_2017_2024_growth_exact(self):
        r=m31.report_shell(as_of=TODAY)
        vals={x["naics"]:x for x in r["original_bls_sectoral_output_industry_series"]}
        self.assertEqual(vals["484"]["2017_2024_real_sectoral_output_change_pct"],"4.02")
        self.assertEqual(vals["4841"]["2017_2024_real_sectoral_output_change_pct"],"5.91")
        self.assertEqual(vals["48412"]["2017_2024_real_sectoral_output_change_pct"],"2.98")
        self.assertEqual(vals["484"]["2024_index"],"104.019")
        self.assertEqual(vals["4841"]["2024_index"],"105.912")
        self.assertEqual(vals["48412"]["2024_index"],"102.984")

    def test_m29_ppi_proxy_gross_output_gap_is_descriptive_not_error(self):
        r=m31.report_shell(as_of=TODAY)
        self.assertEqual(r["aggregate_naics484_real_sectoral_output_2017_2024_pct"],"4.02")
        self.assertEqual(r["m29_aggregate_illustrative_census_ppi_revenue_proxy_2017_2024_pct"],"1.18")
        self.assertEqual(r["bls_minus_ppi_proxy_descriptive_gap_percentage_points"],"2.84")
        self.assertEqual(r["comparison_verdict"],
                         "DESCRIPTIVE_DIFFERENCE_NOT_VALIDATED_MODEL_ERROR_OR_OFFICIAL_BEA_REAL_OUTPUT")
        self.assertTrue(r["bls_sectoral_output_and_m29_revenue_proxy_can_share_input_sources"])

    def test_combined_long_distance_48412_not_same_as_ltl_484122(self):
        r=m31.report_shell(as_of=TODAY)
        self.assertTrue(r["bls48412_is_combined_long_distance_not_ltl_484122_or_tl_484121"])
        self.assertTrue(r["naics484_contains_4841_contains_48412_not_independent"])
        self.assertEqual(len(r["original_bls_sectoral_output_industry_series"]),3)
        self.assertFalse(catalog()["bls_original_sectoral_output_equals_bea_gdp_value_added"])

    def test_unretrieved_bea_real_gross_output_must_remain_held(self):
        r=m31.report_shell(as_of=TODAY)
        self.assertTrue(r["gross_output_original_bea_naics484_source_still_unverified"])
        self.assertFalse(r["be_a_real_output_484_2017_2024_available"])
        self.assertEqual(r["bea_api_no_key_original_probe_blocker"],
                         "API_ERROR_4_USER_ID_NOT_ACTIVE")
        self.assertFalse(catalog()["bea_api_key_acquired"])
        self.assertFalse(catalog()["gross_output_original_bea_quantity_index_naics484_verified"])

    def test_offline_source_catalog_is_not_new_original_api_replay(self):
        r=m31.report_shell(as_of=TODAY)
        self.assertEqual(r["status"],m31.OFFLINE)
        self.assertFalse(r["fresh_original_bls_output_source_replayed_this_run"])
        self.assertEqual(r["fresh_original_bls_source_year_cells_authenticated"],0)
        self.assertIsNone(r["fresh_api_response_sha256"])
        self.assertFalse(r["current_source_has_been_directly_downloaded_in_this_report"])
        self.assertEqual(r["receipt_sha256"],canon_hash({
            k:v for k,v in r.items() if k!="receipt_sha256"
        }))

    def test_valid_complete_synthetic_fixture_is_not_network_origin_proof(self):
        r=m31.verify_origins(
            as_of=TODAY,response=synthetic_bls(),raw_sha256="c"*64
        )
        self.assertEqual(r["status"],m31.VERIFIED)
        self.assertTrue(r["fresh_original_bls_output_source_replayed_this_run"])
        self.assertEqual(r["fresh_original_bls_source_year_cells_authenticated"],24)
        self.assertEqual(r["fresh_api_response_sha256"],"c"*64)
        self.assertEqual(len(r["fresh_semantic_values_receipt_sha256"]),64)

    def test_wrong_sha256_proof_cannot_be_submitted(self):
        with self.assertRaisesRegex(ValueError,"M31_ORIGINAL_BLS_RESPONSE_SHA256_INVALID"):
            m31.verify_origins(as_of=TODAY,response=synthetic_bls(),raw_sha256="invalid")

    def test_source_book_tampered_value_rejected(self):
        data=catalog()
        data["series"][0]["values_by_year"]["2024"]="107.000"
        self.assertTrue(m31.validate_catalog(data,as_of=TODAY))

    def test_source_book_wrong_bls_or_bea_authority_rejected(self):
        for key,value in (
            ("publisher","Private freight audit"),
            ("source_api_url","https://attacker.invalid/source"),
            ("source_grain","MONTHLY_PPI_NOT_REAL_OUTPUT"),
            ("bea_api_key_acquired",True),
            ("direct_bea_real_output_competitor_validation_completed",True),
        ):
            data=catalog()
            data[key]=value
            self.assertTrue(m31.validate_catalog(data,as_of=TODAY),key)

    def test_source_book_false_recovery_and_market_claims_rejected(self):
        for key in m31.FALSE_GUARDS:
            data=catalog()
            data[key]=True
            self.assertTrue(m31.validate_catalog(data,as_of=TODAY),key)
        data=catalog()
        data["real_customer_paid_ltl_invoices_observed"]=1
        self.assertTrue(m31.validate_catalog(data,as_of=TODAY))

    def test_initial_ineligible_blended_survey_comparison_prohibited(self):
        r=m31.report_shell(as_of=TODAY)
        self.assertTrue(r["bls_real_sectoral_output_is_not_bea_gross_output"])
        self.assertTrue(r["bls_real_sectoral_output_is_not_bea_gdp_value_added"])
        self.assertEqual(r["real_paid_customer_freight_invoices_observed"],0)
        self.assertIsNone(r["recoverable_freight_audit_tam_usd"])
        self.assertFalse(r["external_marketing_or_contact_authorized"])

    def test_no_client_fee_refund_or_authorized_buyer_demand_inferred(self):
        r=m31.report_shell(as_of=TODAY)
        self.assertEqual(r["real_paid_customer_freight_invoices_observed"],0)
        self.assertEqual(r["independently_adjudicated_overcharges_observed"],0)
        self.assertIsNone(r["refund_cash_proven_usd"])
        self.assertIsNone(r["recoverable_freight_audit_tam_usd"])
        self.assertFalse(r["buyer_demand_verified"])
        self.assertTrue(r["original_18_real_customer_pilot_requirements_unmet"])
        self.assertFalse(r["scheduled_tasks_created_or_modified"])
        self.assertFalse(r["private_customer_or_carrier_documents_imported"])

    def test_date_before_observed_source_is_blocked(self):
        self.assertTrue(m31.validate_catalog(catalog(),as_of=date(2026,10,11)))
        with self.assertRaisesRegex(ValueError,"M31_FROZEN_SOURCE_CATALOG_VALIDATION_FAILED"):
            m31.report_shell(as_of=date(2026,10,11))

    def test_source_network_timeout_reports_explicit_hold(self):
        with tempfile.TemporaryDirectory() as root:
            with patch("sys.argv",["m31","--as-of-date","2026-10-12","--out",root,"--fetch-original"]):
                with patch.object(m31,"fetch_original_bls",side_effect=TimeoutError("synthetic")):
                    m31.main()
            r=json.loads((Path(root)/"bls_sectoral_output.json").read_text())
            self.assertEqual(r["status"],m31.BLOCKED)
            self.assertFalse(r["fresh_original_bls_output_source_replayed_this_run"])
            self.assertEqual(r["fresh_original_bls_source_year_cells_authenticated"],0)

    def test_available_corrupt_source_fails_not_blocked(self):
        data=synthetic_bls()
        data["Results"]["series"][0]["data"][0]["value"]="999.999"
        with tempfile.TemporaryDirectory() as root:
            with patch("sys.argv",["m31","--as-of-date","2026-10-12","--out",root,"--fetch-original"]):
                with patch.object(m31,"fetch_original_bls",return_value=(data,"0"*64)):
                    with self.assertRaisesRegex(ValueError,"M31_BLS_OFFICIAL_SOURCE_VALUE_CHANGED_REQUIRES_REVIEW"):
                        m31.main()

    def test_html_escape_and_bea_missing_guard(self):
        r=m31.report_shell(as_of=TODAY)
        r["caveat"]="<script>alert('cash refund')</script>"
        html=m31.render_html(r)
        self.assertNotIn("<script>",html)
        self.assertIn("&lt;script&gt;",html)
        self.assertIn("BEA real gross output",html)
        self.assertIn("NOT AUTHENTICATED",html)

    def test_trusted_catalog_receipt_is_stable(self):
        r=m31.report_shell(as_of=TODAY)
        self.assertEqual(r["receipt_sha256"],canon_hash({
            k:v for k,v in r.items() if k!="receipt_sha256"
        }))


if __name__=="__main__":
    unittest.main()
