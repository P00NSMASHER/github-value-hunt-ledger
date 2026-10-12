"""Mission 28 adversarial corrected native BLS trucking subsector PPI tests.

Fixtures simulate JSON source rows and prove parser behavior, not official BLS
HTTP origin. The separate CI source job must download and validate all 96
months against original BLS v2 with correct PCU484---484--- identifier.
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
from freight.research_bls_parent_origin import (
    BOOK, BOOK_SHA1, SOURCE_ID, FRED_ALIAS_ID,
)
from freight import research_bls_parent_origin as m28

TODAY=date(2026,10,12)


def book()->dict:
    return json.loads(BOOK.read_text(encoding="utf-8"))


def synthetic_v2()->dict:
    data=[]
    for year in reversed(m28.YEARS):
        for month in range(12,0,-1):
            value=book()["monthly_values_by_year"][str(year)][month-1]
            # BLS source can publish 132.5 instead of FRED's 132.500:
            raw=str(Decimal(value))
            data.append({
                "year":str(year), "period":f"M{month:02d}",
                "value":raw,"footnotes":[{}],
            })
    return {
        "status":"REQUEST_SUCCEEDED",
        "message":[],
        "Results":{"series":[{"seriesID":SOURCE_ID,"data":data}]}
    }


class OriginalBLSNativeAggregateTests(unittest.TestCase):
    def test_correct_native_bls_series_id_and_fred_alias_are_distinct(self):
        self.assertEqual(SOURCE_ID,"PCU484---484---")
        self.assertEqual(FRED_ALIAS_ID,"PCU484484")
        self.assertNotEqual(SOURCE_ID,FRED_ALIAS_ID)
        self.assertEqual(book()["catalog_native_industry_code"],"484---")
        self.assertEqual(book()["catalog_native_product_code"],"484---")
        self.assertEqual(book()["catalog_base_date_code"],"200312")

    def test_github_blob_pinned_source_book_validated(self):
        self.assertEqual(m28._git_blob(BOOK.read_bytes()),BOOK_SHA1)
        self.assertEqual(m28.validate_catalog(book(),as_of=TODAY),[])
        self.assertEqual(len(BOOK_SHA1),40)

    def test_official_v2_post_payload_exact_year_and_native_series(self):
        catalog=book()
        self.assertEqual(catalog["original_api_v2_payload"],{
            "seriesid":[SOURCE_ID],"startyear":"2017","endyear":"2024"
        })
        self.assertEqual(catalog["original_api_v2_method"],"POST")
        self.assertEqual(catalog["original_api_v2_url"],m28.BLS_API)
        self.assertEqual(catalog["native_bls_api_v2_post_initial_bytes"],8483)
        self.assertEqual(len(catalog["native_bls_api_v2_post_initial_sha256"]),64)

    def test_all_96_native_source_months_numerically_match_prior_fred_alias(self):
        catalog=book()
        self.assertEqual(sum(len(v) for v in catalog["monthly_values_by_year"].values()),96)
        previous=m28.previous_fred_book()["year_to_monthly_observations"]
        for yr in m28.YEARS:
            self.assertEqual(len(previous[str(yr)]),12)
            for val,fred in zip(catalog["monthly_values_by_year"][str(yr)],previous[str(yr)]):
                self.assertEqual(Decimal(val),Decimal(fred))

    def test_synthetic_bls_v2_complete_96_source_months_validate(self):
        observed=m28.parse_bls_v2(synthetic_v2(),catalog=book())
        self.assertEqual(len(observed),8)
        self.assertEqual(sum(len(v) for v in observed.values()),96)
        self.assertEqual(observed[2017][0],Decimal("132.500"))
        self.assertEqual(observed[2024][-1],Decimal("182.528"))
        self.assertEqual(observed[2024][0],Decimal("184.262"))

    def test_original_source_months_not_duplicated_across_alias_and_native(self):
        r=m28.report_shell(as_of=TODAY)
        self.assertEqual(r["native_bls_original_series_id"],SOURCE_ID)
        self.assertEqual(r["fred_redistributed_alias_series_id"],FRED_ALIAS_ID)
        self.assertEqual(r["bls_months_in_previous_first_party_probe"],96)
        self.assertTrue(r["historic_m27_fred_http_attempts_in_m27_were_blocked"])
        self.assertTrue(r["historic_m27_fred_provisional_status_unchanged"])

    def test_source_catalog_month_missing_rejected(self):
        b=book()
        b["monthly_values_by_year"]["2023"].pop()
        self.assertTrue(m28.validate_catalog(b,as_of=TODAY))
        b=book()
        b["monthly_values_by_year"].pop("2024")
        self.assertTrue(m28.validate_catalog(b,as_of=TODAY))

    def test_bls_fred_mismatch_fails_manifest(self):
        b=book()
        b["monthly_values_by_year"]["2022"][4]="230.100"
        self.assertIn("M28_BLS_NATIVE_VERSUS_FRED_PRIOR_OBSERVATION_MISMATCH",
                      ";".join(m28.validate_catalog(b,as_of=TODAY)))

    def test_v2_request_succeeded_with_error_message_is_not_source_verification(self):
        response=synthetic_v2()
        response["message"]=["Series does not exist for Series PCU484484"]
        with self.assertRaisesRegex(ValueError,"M28_BLS_API_MESSAGE_DENIES_NATIVE_SERIES"):
            m28.parse_bls_v2(response,catalog=book())

    def test_v2_http200_but_request_failed_is_not_source_verification(self):
        response=synthetic_v2()
        response["status"]="REQUEST_FAILED"
        with self.assertRaisesRegex(ValueError,"M28_BLS_API_V2_NOT_REQUEST_SUCCEEDED"):
            m28.parse_bls_v2(response,catalog=book())

    def test_fred_short_id_returns_wrong_source_even_with_matching_numeric_rows(self):
        response=synthetic_v2()
        response["Results"]["series"][0]["seriesID"]=FRED_ALIAS_ID
        with self.assertRaisesRegex(ValueError,"M28_DIRECT_BLS_NATIVE_SERIES_ID_WRONG_OR_FRED_ALIAS"):
            m28.parse_bls_v2(response,catalog=book())

    def test_second_series_added_is_not_independent_double_confirmation(self):
        response=synthetic_v2()
        response["Results"]["series"].append(deepcopy(response["Results"]["series"][0]))
        with self.assertRaisesRegex(ValueError,"M28_DIRECT_BLS_NATIVE_SERIES_ID_WRONG_OR_FRED_ALIAS"):
            m28.parse_bls_v2(response,catalog=book())

    def test_get_recent_window_does_not_replace_full_2017_2024_post(self):
        response=synthetic_v2()
        response["Results"]["series"][0]["data"]=[
            r for r in response["Results"]["series"][0]["data"] if r["year"]=="2024"
        ]
        with self.assertRaisesRegex(ValueError,"M28_NATIVE_BLS_TWELVE_MONTHS_NOT_PRESENT"):
            m28.parse_bls_v2(response,catalog=book())

    def test_duplicate_year_month_cannot_inflate_96_count(self):
        response=synthetic_v2()
        response["Results"]["series"][0]["data"].append(
            deepcopy(response["Results"]["series"][0]["data"][-1])
        )
        with self.assertRaisesRegex(ValueError,"M28_DUPLICATED_NATIVE_BLS_MONTH"):
            m28.parse_bls_v2(response,catalog=book())

    def test_missing_one_month_cannot_be_replaced_by_annual_average_period(self):
        response=synthetic_v2()
        response["Results"]["series"][0]["data"].pop()
        response["Results"]["series"][0]["data"].append({
            "year":"2024","period":"M13","value":"180.000","footnotes":[{}],
        })
        with self.assertRaisesRegex(ValueError,"M28_NATIVE_BLS_TWELVE_MONTHS_NOT_PRESENT"):
            m28.parse_bls_v2(response,catalog=book())

    def test_extra_annual_period_not_treated_as_month(self):
        response=synthetic_v2()
        response["Results"]["series"][0]["data"].append({
            "year":"2024","period":"M13","value":"200.000","footnotes":[],
        })
        self.assertEqual(
            sum(len(v) for v in m28.parse_bls_v2(response,catalog=book()).values()),96
        )

    def test_wrong_year_month_or_source_period_rejected(self):
        for field,value in (
            ("year","2016"),("year","2025"),("period","M00"),
            ("period","M14"),("period","S01"),("period","M-1"),
        ):
            response=synthetic_v2()
            response["Results"]["series"][0]["data"][0][field]=value
            with self.assertRaises(ValueError,msg=str(value)):
                m28.parse_bls_v2(response,catalog=book())

    def test_source_preliminary_or_flagged_month_disallowed(self):
        response=synthetic_v2()
        response["Results"]["series"][0]["data"][5]["footnotes"]=[
            {"code":"P","text":"Preliminary"}
        ]
        with self.assertRaisesRegex(ValueError,"M28_BLS_PRELIMINARY_OR_FLAGGED_PPI_NOT_FINAL"):
            m28.parse_bls_v2(response,catalog=book())

    def test_one_month_revised_after_initial_archive_is_not_silently_accepted(self):
        response=synthetic_v2()
        response["Results"]["series"][0]["data"][0]["value"]="999.999"
        with self.assertRaisesRegex(ValueError,"M28_NATIVE_BLS_VALUE_DIFFERS_FROM_FRED_ALIAS_PUBLICATION"):
            m28.parse_bls_v2(response,catalog=book())

    def test_float_bool_none_zero_bad_value_or_suppressed_source_rejected(self):
        for value in (None,False,0,-1,"NaN","S","",0.1,{},"-100","0.500"):
            with self.assertRaises(ValueError,msg=repr(value)):
                m28._dec(value)

    def test_2017_2024_original_ppi_nominal_and_proxy_arithmetic_reproduced(self):
        r=m28.report_shell(as_of=TODAY)
        self.assertEqual(r["2017_to_2024_census_nominal_revenue_change_pct"],"38.65")
        self.assertEqual(r["2017_to_2024_bls_parent_ppi_change_pct"],"37.04")
        self.assertEqual(r["2017_to_2024_illustrative_adjusted_revenue_proxy_pct"],"1.18")
        byyear={x["year"]:x for x in r["yearly_index_adjustments"]}
        self.assertEqual(byyear[2017]["bls_original_price_index_annual_arithmetic_mean"],"134.3583")
        self.assertEqual(byyear[2024]["bls_original_price_index_annual_arithmetic_mean"],"184.1238")
        self.assertEqual(byyear[2024]["illustrative_2017_price_level_revenue_proxy_million_usd"],"293949.981")
        self.assertEqual(len(byyear),8)

    def test_source_grade_offline_is_not_fresh_bls_api_attestation(self):
        r=m28.report_shell(as_of=TODAY)
        self.assertEqual(r["source_status"],m28.OFFLINE)
        self.assertFalse(r["direct_bls_original_v2_source_replay_completed"])
        self.assertFalse(r["direct_original_bls_source_authenticated_in_current_run"])
        self.assertIsNone(r["original_bls_api_v2_raw_response_sha256"])
        self.assertEqual(r["original_bls_api_v2_months_replayed_this_execution"],0)
        self.assertEqual(r["receipt_sha256"],canon_hash({
            k:v for k,v in r.items() if k!="receipt_sha256"
        }))

    def test_test_fixture_can_validate_math_without_claiming_network_origin(self):
        r=m28.verify_source(
            as_of=TODAY,response=synthetic_v2(),raw_sha256="1"*64
        )
        self.assertEqual(r["source_status"],m28.VERIFIED)
        self.assertTrue(r["direct_bls_original_v2_source_replay_completed"])
        self.assertEqual(r["original_bls_api_v2_months_replayed_this_execution"],96)
        self.assertEqual(r["original_bls_api_v2_raw_response_sha256"],"1"*64)
        self.assertEqual(r["receipt_sha256"],canon_hash({
            k:v for k,v in r.items() if k!="receipt_sha256"
        }))

    def test_false_sha256_attestation_format_rejected(self):
        with self.assertRaisesRegex(ValueError,"M28_ORIGINAL_BLS_RAW_RESPONSE_SHA256_INVALID"):
            m28.verify_source(as_of=TODAY,response=synthetic_v2(),raw_sha256="not a digest")

    def test_network_unavailable_creates_explicit_hold_not_success(self):
        r=m28.blocked(as_of=TODAY)
        self.assertEqual(r["source_status"],m28.BLOCKED)
        self.assertEqual(r["original_bls_api_v2_months_replayed_this_execution"],0)
        self.assertFalse(r["direct_bls_original_v2_source_replay_completed"])

    def test_cli_network_timeout_writes_blocked_report(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch("sys.argv",["m28","--out",directory,"--as-of-date","2026-10-12",
                                   "--fetch-bls-native"]):
                with patch.object(m28,"fetch_bls_native_v2",side_effect=TimeoutError("synthetic")):
                    m28.main()
            r=json.loads((Path(directory)/"bls_parent_origin.json").read_text())
            self.assertEqual(r["source_status"],m28.BLOCKED)
            self.assertEqual(r["original_bls_api_v2_months_replayed_this_execution"],0)
            self.assertFalse(r["direct_original_bls_source_authenticated_in_current_run"])

    def test_available_bls_changed_source_rejected_without_network_hold(self):
        response=synthetic_v2()
        response["Results"]["series"][0]["data"][0]["value"]="999.999"
        with tempfile.TemporaryDirectory() as directory:
            with patch("sys.argv",["m28","--out",directory,"--as-of-date","2026-10-12",
                                   "--fetch-bls-native"]):
                with patch.object(m28,"fetch_bls_native_v2",return_value=(response,"1"*64)):
                    with self.assertRaisesRegex(ValueError,"M28_NATIVE_BLS_VALUE_DIFFERS"):
                        m28.main()

    def test_false_real_output_and_recovery_gates_remain_blocked(self):
        r=m28.report_shell(as_of=TODAY)
        self.assertEqual(r["lab"],14)
        self.assertFalse(r["new_lab_created"])
        self.assertEqual(r["real_customer_freight_invoices_observed"],0)
        self.assertEqual(r["approved_independent_billing_audit_findings"],0)
        self.assertIsNone(r["verified_recoverable_market_tam_usd"])
        self.assertIsNone(r["actual_cash_refunds_proven_usd"])
        self.assertFalse(r["buyer_demand_measured"])
        self.assertFalse(r["external_carrier_or_customer_contact_authorized"])
        self.assertTrue(r["18_human_customer_pilot_requirements_unmet"])
        self.assertTrue(r["index_adjustment_is_not_official_real_freight_output"])
        self.assertFalse(r["scheduled_tasks_modified"])

    def test_manifest_rejects_wrong_issuer_api_units_or_alias(self):
        for key,value in (
            ("original_bls_series_id","PCU484484"),
            ("prior_fred_distributor_series_id",SOURCE_ID),
            ("original_api_v2_url","https://attacker.example/data"),
            ("catalog_base_date_code","202401"),
            ("native_bls_monthly_index_units","CUSTOMER_CHARGES_PERCENTAGE"),
            ("original_bls_bulk_download_runner_http_status",200),
            ("all_years_form_one_direct_bls_series",False),
            ("monthly_values_by_year",{"2017":["999.999"]}),
        ):
            b=book()
            b[key]=value
            self.assertTrue(m28.validate_catalog(b,as_of=TODAY),key)

    def test_false_real_output_and_client_payment_promotions_in_manifest_fail(self):
        for key in m28.FALSE_GUARDS:
            b=book()
            b[key]=True
            self.assertIn("M28_FAKE_REAL_OUTPUT_OR_RECOVERY_ASSERTION",
                          ";".join(m28.validate_catalog(b,as_of=TODAY)),key)

    def test_observation_date_time_travel_and_extra_private_fields_rejected(self):
        self.assertTrue(m28.validate_catalog(book(),as_of=date(2026,10,11)))
        b=book()
        b["freight_client_id"]="private"
        self.assertTrue(m28.validate_catalog(b,as_of=TODAY))
        with self.assertRaisesRegex(ValueError,"M28_BLS_SOURCE_CATALOG_REJECTED"):
            m28.report_shell(as_of=date(2026,10,11))

    def test_escaping_and_original_source_boundary_in_report(self):
        r=m28.report_shell(as_of=TODAY)
        r["caveat"]="<svg onload=evil()>"
        html=m28.render_html(r)
        self.assertNotIn("<svg onload=",html)
        self.assertIn("&lt;svg onload=",html)
        self.assertIn("PCU484---484---",html)
        self.assertIn("PCU484484",html)
        self.assertIn("not official real freight output",html.lower())


if __name__=="__main__":
    unittest.main()
