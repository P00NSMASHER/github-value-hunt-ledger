"""Adversarial tests for M29's unified direct-BLS source and method warning.

These are synthetic response fixtures and do NOT authenticate fresh source
bytes. The separate CI original BLS v2 POST must verify all 288 months.
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
from freight import research_unified_blspci as m29

TODAY=date(2026,10,12)


def policy():
    return json.loads(m29.BOOK.read_text(encoding="utf-8"))


def original_fixture():
    _,grid,_=m29._price_grid(as_of=TODAY)
    series=[]
    for sid in reversed(m29.PPI_SERIES):
        rows=[]
        for year in reversed(m29.YEARS):
            for month in range(12,0,-1):
                index=grid[sid][year][month-1]
                rows.append({
                    "year":str(year),
                    "period":f"M{month:02d}",
                    "value":str(index),
                    "footnotes":[{}],
                })
        series.append({"seriesID":sid,"data":rows})
    return {"status":"REQUEST_SUCCEEDED","message":[],"Results":{"series":series}}


def inspected_fixture():
    _,grid,_=m29._price_grid(as_of=TODAY)
    return m29.validate_first_party_response(original_fixture(),expected=grid)


class UnifiedOriginalPPITests(unittest.TestCase):
    def test_source_policy_git_blob_and_closure(self):
        self.assertEqual(m29._blob_id(m29.BOOK.read_bytes()),m29.BOOK_SHA1)
        self.assertEqual(m29.validate_policy(policy(),as_of=TODAY),[])
        self.assertEqual(policy()["required_monthly_observations_total"],288)
        self.assertEqual(policy()["required_monthly_observations_per_series"],96)

    def test_only_three_correct_first_party_series_identifiers_permitted(self):
        self.assertEqual(m29.PPI_SERIES,(
            "PCU484---484---","PCU484121484121","PCU484122484122"
        ))
        self.assertEqual(m29.PPI_MAP["484"],"PCU484---484---")
        self.assertEqual(policy()["legacy_fred_parent_alias"],"PCU484484")
        self.assertEqual(policy()["source_api_payload"]["seriesid"],list(m29.PPI_SERIES))

    def test_original_catalogs_were_separately_verified_and_grain_matches(self):
        p,values,prior=m29._price_grid(as_of=TODAY)
        self.assertEqual(set(values),set(m29.PPI_SERIES))
        for sid,years in values.items():
            self.assertEqual(sorted(years),list(m29.YEARS))
            self.assertEqual(sum(len(x) for x in years.values()),96,sid)
            self.assertTrue(all(val>0 for records in years.values() for val in records))
        self.assertEqual(prior["parent"]["original_bls_series_id"],"PCU484---484---")
        self.assertEqual(len(prior["children"]["industries"]),2)

    def test_complete_synthetic_response_all_288_months_and_precise_values(self):
        result=inspected_fixture()
        self.assertEqual(set(result),set(m29.PPI_SERIES))
        self.assertEqual(sum(len(r) for v in result.values() for r in v.values()),288)
        self.assertEqual(result["PCU484---484---"][2017][0],"132.5")
        self.assertEqual(result["PCU484121484121"][2024][-1],"171.718")
        self.assertEqual(result["PCU484122484122"][2024][-1],"243.422")

    def test_source_fixture_record_order_does_not_change_annual_values(self):
        a=original_fixture()
        b=deepcopy(a)
        b["Results"]["series"].reverse()
        for s in b["Results"]["series"]:
            s["data"].reverse()
        _,expected,_=m29._price_grid(as_of=TODAY)
        self.assertEqual(
            m29.validate_first_party_response(a,expected=expected),
            m29.validate_first_party_response(b,expected=expected),
        )

    def test_offline_grade_is_not_a_fresh_three_series_verification(self):
        r=m29.report_shell(as_of=TODAY)
        self.assertEqual(r["status"],m29.OFFLINE)
        self.assertEqual(r["current_source_authenticated_month_count"],0)
        self.assertFalse(r["current_original_bls_source_replayed_this_run"])
        self.assertIsNone(r["original_bls_response_sha256"])
        self.assertEqual(r["historical_original_bls_months_in_pinned_catalogs"],288)
        self.assertEqual(r["industry_counts"],3)
        self.assertTrue(r["legacy_source_reports_kept_as_historical_evidence"])

    def test_synthetic_fresh_response_passes_semantic_validation_without_network(self):
        r=m29.verify_original_bls(
            as_of=TODAY,response=original_fixture(),raw_sha256="a"*64
        )
        self.assertEqual(r["status"],m29.VERIFIED)
        self.assertTrue(r["current_original_bls_source_replayed_this_run"])
        self.assertEqual(r["current_source_authenticated_month_count"],288)
        self.assertEqual(r["original_bls_response_sha256"],"a"*64)
        self.assertEqual(len(r["fresh_source_semantic_receipt_sha256"]),64)
        self.assertEqual(r["receipt_sha256"],canon_hash({
            key:value for key,value in r.items() if key!="receipt_sha256"
        }))

    def test_original_census_nominal_2017_2024_growth_reproduced_three_industries(self):
        rows={x["naics"]:x for x in m29.report_shell(as_of=TODAY)["industry_comparisons"]}
        self.assertEqual(
            [rows[c]["2017_to_2024_census_nominal_revenue_change_pct"] for c in m29.NAICS],
            ["38.65","43.48","40.93"]
        )
        self.assertTrue(all(len(x["annual_observations"])==8 for x in rows.values()))

    def test_annual_average_2017_index_adjusted_proxy_reproduced(self):
        rows={x["naics"]:x for x in m29.report_shell(as_of=TODAY)["industry_comparisons"]}
        self.assertEqual(
            [rows[c]["2017_to_2024_illustrative_annual_mean_price_adjusted_revenue_pct"]
             for c in m29.NAICS],
            ["1.18","2.82","-1.89"],
        )
        self.assertTrue(all(x["is_official_bls_real_output_volume_or_freight_spend"] is False
                            for x in rows.values()))

    def test_december_endpoint_methodological_sensitivity_not_equal_annual_mean(self):
        rows={x["naics"]:x for x in m29.report_shell(as_of=TODAY)["industry_comparisons"]}
        self.assertEqual([rows[c]["2017_to_2024_december_endpoint_price_adjusted_revenue_pct"]
                          for c in m29.NAICS],["4.75","8.87","1.60"])
        self.assertEqual([rows[c]["december_minus_annual_mean_adjusted_change_percentage_points"]
                          for c in m29.NAICS],["3.57","6.06","3.49"])
        self.assertTrue(all(x["year_end_sensitivity_is_not_a_comparable_annual_revenue_deflator"]
                            for x in rows.values()))

    def test_ltl_sensitivity_flips_sign_not_a_proven_volume_reversal(self):
        ltl=next(x for x in m29.report_shell(as_of=TODAY)["industry_comparisons"]
                 if x["naics"]=="484122")
        self.assertTrue(Decimal(ltl["2017_to_2024_illustrative_annual_mean_price_adjusted_revenue_pct"])<0)
        self.assertTrue(Decimal(ltl["2017_to_2024_december_endpoint_price_adjusted_revenue_pct"])>0)
        self.assertFalse(ltl["is_official_bls_real_output_volume_or_freight_spend"])
        self.assertFalse(m29.policy().get("december_endpoint_is_annual_average",False)
                         if hasattr(m29,"policy") else policy()["december_endpoint_is_annual_average"])

    def test_parent_and_child_overlap_cannot_be_summed(self):
        r=m29.report_shell(as_of=TODAY)
        self.assertTrue(r["naics484_is_parent_of_484121_and_484122_non_additive"])
        self.assertEqual(r["industry_counts"],3)
        self.assertTrue(r["comparisons_are_not_inflation_adjusted_client_freight_billing_spend"])

    def test_m26_missing_parent_and_m27_fred_timeout_remain_historically_true(self):
        r=m29.report_shell(as_of=TODAY)
        self.assertTrue(r["historical_m26_missing_parent_was_wrong_alias_not_deleted_bls_series"])
        self.assertTrue(r["historical_m27_fred_source_timeout_remains_true"])
        self.assertTrue(r["m28_native_parent_id_supersedes_invalid_fred_alias_for_current_reports"])
        self.assertTrue(r["legacy_source_reports_kept_as_historical_evidence"])

    def test_error_message_on_http_success_rejects_source(self):
        resp=original_fixture()
        resp["message"]=["Series does not exist for Series PCU484484"]
        _,ref,_=m29._price_grid(as_of=TODAY)
        with self.assertRaisesRegex(ValueError,"M29_BLS_API_SERIES_ERROR_MESSAGE_PRESENT"):
            m29.validate_first_party_response(resp,expected=ref)

    def test_api_failed_status_is_not_replay(self):
        resp=original_fixture()
        resp["status"]="REQUEST_FAILED"
        _,ref,_=m29._price_grid(as_of=TODAY)
        with self.assertRaisesRegex(ValueError,"M29_BLS_PUBLIC_API_NOT_REQUEST_SUCCEEDED"):
            m29.validate_first_party_response(resp,expected=ref)

    def test_short_fred_alias_rejected_even_if_months_look_identical(self):
        resp=original_fixture()
        resp["Results"]["series"][0]["seriesID"]="PCU484484"
        _,ref,_=m29._price_grid(as_of=TODAY)
        with self.assertRaisesRegex(ValueError,"M29_DUPLICATE_UNKNOWN_OR_FRED_ALIAS_BLS_SERIES"):
            m29.validate_first_party_response(resp,expected=ref)

    def test_wrong_source_id_rejected_for_each_industry(self):
        for idx in range(3):
            resp=original_fixture()
            resp["Results"]["series"][idx]["seriesID"]="PCU484484"
            _,ref,_=m29._price_grid(as_of=TODAY)
            with self.assertRaisesRegex(ValueError,"M29_DUPLICATE_UNKNOWN_OR_FRED_ALIAS_BLS_SERIES"):
                m29.validate_first_party_response(resp,expected=ref)

    def test_duplicate_second_industry_not_three_independent_sources(self):
        resp=original_fixture()
        resp["Results"]["series"][1]["seriesID"]=resp["Results"]["series"][0]["seriesID"]
        _,ref,_=m29._price_grid(as_of=TODAY)
        with self.assertRaisesRegex(ValueError,"M29_DUPLICATE_UNKNOWN_OR_FRED_ALIAS_BLS_SERIES"):
            m29.validate_first_party_response(resp,expected=ref)

    def test_one_series_missing_does_not_satisfy_288_months(self):
        resp=original_fixture()
        resp["Results"]["series"].pop()
        _,ref,_=m29._price_grid(as_of=TODAY)
        with self.assertRaisesRegex(ValueError,"M29_REQUIRE_EXACTLY_THREE_INDUSTRY_SERIES"):
            m29.validate_first_party_response(resp,expected=ref)

    def test_source_2017_2024_window_must_have_96_per_industry(self):
        for i in range(3):
            resp=original_fixture()
            resp["Results"]["series"][i]["data"]= [
                x for x in resp["Results"]["series"][i]["data"] if x["year"]=="2024"
            ]
            _,ref,_=m29._price_grid(as_of=TODAY)
            with self.assertRaisesRegex(ValueError,"M29_INCOMPLETE_TWELVE_MONTH_YEAR"):
                m29.validate_first_party_response(resp,expected=ref)

    def test_duplicate_month_rejected_not_inflated_record_count(self):
        resp=original_fixture()
        resp["Results"]["series"][1]["data"].append(deepcopy(resp["Results"]["series"][1]["data"][0]))
        _,ref,_=m29._price_grid(as_of=TODAY)
        with self.assertRaisesRegex(ValueError,"M29_DUPLICATE_BLS_MONTH"):
            m29.validate_first_party_response(resp,expected=ref)

    def test_month_13_does_not_count_as_2017_month(self):
        resp=original_fixture()
        resp["Results"]["series"][2]["data"].pop()
        resp["Results"]["series"][2]["data"].append({
            "year":"2017","period":"M13","value":"1000.0","footnotes":[],
        })
        _,ref,_=m29._price_grid(as_of=TODAY)
        with self.assertRaisesRegex(ValueError,"M29_INCOMPLETE_TWELVE_MONTH_YEAR"):
            m29.validate_first_party_response(resp,expected=ref)

    def test_source_rejects_bad_month_and_out_of_period_year(self):
        for field,value,code in (
            ("period","M00","M29_BLS_SOURCE_NOT_CALENDAR_MONTH"),
            ("period","M14","M29_BLS_SOURCE_NOT_CALENDAR_MONTH"),
            ("period","S01","M29_BLS_SOURCE_NOT_CALENDAR_MONTH"),
            ("year","2016","M29_BLS_OUT_OF_WINDOW_YEAR"),
            ("year","2025","M29_BLS_OUT_OF_WINDOW_YEAR"),
        ):
            resp=original_fixture()
            resp["Results"]["series"][0]["data"][0][field]=value
            _,ref,_=m29._price_grid(as_of=TODAY)
            with self.assertRaisesRegex(ValueError,code,msg=value):
                m29.validate_first_party_response(resp,expected=ref)

    def test_preliminary_or_bad_bls_flag_forbidden(self):
        resp=original_fixture()
        resp["Results"]["series"][1]["data"][0]["footnotes"]=[
            {"code":"P","text":"Preliminary"}
        ]
        _,ref,_=m29._price_grid(as_of=TODAY)
        with self.assertRaisesRegex(ValueError,"M29_BLS_FLAGGED_OR_PRELIMINARY_PPI"):
            m29.validate_first_party_response(resp,expected=ref)

    def test_changed_source_index_requires_human_review_not_silent_pass(self):
        for i in range(3):
            resp=original_fixture()
            resp["Results"]["series"][i]["data"][0]["value"]="999.999"
            _,ref,_=m29._price_grid(as_of=TODAY)
            with self.assertRaisesRegex(ValueError,"M29_BLS_NATIVE_MONTH_VALUE_REVISED_HUMAN_REVIEW_REQUIRED"):
                m29.validate_first_party_response(resp,expected=ref)

    def test_bad_index_values_rejected(self):
        for val in (None,0,False,"","NaN","S","-3","0.500",1000.2,{},[]):
            with self.assertRaises(ValueError,msg=repr(val)):
                m29._source_number(val)

    def test_closed_policy_vetoes_false_commercial_and_real_output_promotions(self):
        for flag in (
            "adjusted_revenue_is_official_bea_or_bls_real_output",
            "price_index_is_customer_rate_overcharge_percentage",
            "aggregate_trucking_is_sum_of_children",
            "december_endpoint_is_annual_average",
            "confidence_intervals_calculated",
            "external_recovery_market_claims_allowed",
            "pilot_18_real_customer_authorizations_satisfied",
            "customer_or_carrier_private_data_ingested",
            "scheduled_tasks_modified","new_lab_created",
        ):
            b=policy()
            b[flag]=True
            self.assertTrue(m29.validate_policy(b,as_of=TODAY),flag)

    def test_policy_cannot_change_series_or_source_origin(self):
        for key,value in (
            ("live_api_url","https://untrusted.example/ppi"),
            ("source_api_payload",{"seriesid":["PCU484484"]}),
            ("first_full_three_series_source_probe_run_id",0),
            ("required_monthly_observations_total",100),
        ):
            b=policy()
            b[key]=value
            self.assertTrue(m29.validate_policy(b,as_of=TODAY),key)

    def test_source_metadata_time_travel_rejected(self):
        self.assertTrue(m29.validate_policy(policy(),as_of=date(2026,10,11)))
        with self.assertRaisesRegex(ValueError,"M29_POLICY_INVALID"):
            m29.report_shell(as_of=date(2026,10,11))

    def test_no_source_bytes_on_timeout_returns_blocked_and_no_verified_months(self):
        r=m29.blocked(as_of=TODAY)
        self.assertEqual(r["status"],m29.BLOCKED)
        self.assertEqual(r["current_source_authenticated_month_count"],0)
        self.assertFalse(r["current_original_bls_source_replayed_this_run"])
        self.assertIsNone(r["original_bls_response_sha256"])
        self.assertEqual(r["receipt_sha256"],canon_hash({
            k:v for k,v in r.items() if k!="receipt_sha256"
        }))

    def test_fetch_timeout_cli_does_not_claim_original_source_replay(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch("sys.argv",["m29","--out",tmp,"--as-of-date","2026-10-12","--fetch-original"]):
                with patch.object(m29,"fetch_original_bls",side_effect=TimeoutError("synthetic outage")):
                    m29.main()
            r=json.loads((Path(tmp)/"unified_bls_evidence.json").read_text())
            self.assertEqual(r["status"],m29.BLOCKED)
            self.assertEqual(r["current_source_authenticated_month_count"],0)

    def test_bad_publisher_response_fails_instead_of_network_hold(self):
        with tempfile.TemporaryDirectory() as tmp:
            resp=original_fixture()
            resp["Results"]["series"][0]["data"][0]["value"]="9999"
            with patch("sys.argv",["m29","--out",tmp,"--as-of-date","2026-10-12","--fetch-original"]):
                with patch.object(m29,"fetch_original_bls",return_value=(resp,"f"*64)):
                    with self.assertRaisesRegex(ValueError,"M29_BLS_NATIVE_MONTH_VALUE_REVISED_HUMAN_REVIEW_REQUIRED"):
                        m29.main()

    def test_receipt_sha256_invalid_cannot_fake_source(self):
        with self.assertRaisesRegex(ValueError,"M29_BLS_PUBLISHER_RAW_RESPONSE_SHA256_INVALID"):
            m29.verify_original_bls(as_of=TODAY,response=original_fixture(),raw_sha256="fake")

    def test_real_customer_pilot_gates_remain_unmet(self):
        r=m29.report_shell(as_of=TODAY)
        self.assertEqual(r["lab"],14)
        self.assertFalse(r["new_lab_created"])
        self.assertEqual(r["actual_paid_customer_freight_invoices_observed"],0)
        self.assertEqual(r["independently_adjudicated_carrier_overcharges"],0)
        self.assertIsNone(r["actual_retally_cash_recovered_usd"])
        self.assertIsNone(r["freight_recovery_market_tam_usd"])
        self.assertEqual(r["customer_buyers_with_verified_demand"],0)
        self.assertFalse(r["commercial_recovery_claims_or_external_contact_authorized"])
        self.assertTrue(r["original_18_independent_pilot_requirements_still_unmet"])
        self.assertFalse(r["scheduled_tasks_created_or_modified"])

    def test_html_escape_and_current_source_grade_not_overstated(self):
        r=m29.report_shell(as_of=TODAY)
        r["caveat"]="<img src=x onerror=evil()>"
        html=m29.render_html(r)
        self.assertNotIn("<img src=x",html)
        self.assertIn("&lt;img src=x",html)
        self.assertIn(m29.OFFLINE,html)
        self.assertIn("Dec-endpoint sensitivity",html)
        self.assertIn("not official real output",html.lower())


if __name__=="__main__":
    unittest.main()
