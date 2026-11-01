"""Adversarial BLS PPI 2017–24 source authenticity and price-adjustment tests.

Synthetic response fixtures are not publisher evidence. Actual source
verification requires CI to fetch the BLS API with no user/customer data.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from freight.research_evidence_gate import canon_hash
from freight import research_bls_ppi_bridge as m26

TODAY=date(2026,10,12)


def book():
    return json.loads(m26.BOOK.read_text(encoding="utf-8"))


def synthetic_response():
    catalog=book()
    items=[]
    for industry in catalog["industries"]:
        rows=[]
        for yr in m26.YEARS:
            for month,value in enumerate(industry["months_by_year"][str(yr)],1):
                rows.append({
                    "year":str(yr),
                    "period":"M"+str(month).zfill(2),
                    "value":value,
                    "footnotes":[],
                })
        items.append({"seriesID":industry["series_id"],"data":list(reversed(rows))})
    return {"status":"REQUEST_SUCCEEDED","message":[],"Results":{"series":items}}


class BLSPriceAdjustmentTests(unittest.TestCase):
    def test_pinned_bls_catalog_exact_original_source_identity(self):
        self.assertEqual(m26._blob(m26.BOOK.read_bytes()),m26.BOOK_SHA1)
        self.assertEqual(m26.validate_catalog(book(),as_of=TODAY),[])
        self.assertEqual(book()["publisher"],"U.S. Bureau of Labor Statistics")
        self.assertEqual(book()["api_url"],m26.API)
        self.assertEqual(book()["payload"]["seriesid"],list(m26.SERIES))
        self.assertEqual(len(book()["industries"]),2)

    def test_monthly_source_registry_192_exact_observations(self):
        registry=book()
        self.assertEqual(registry["year_range"],list(m26.YEARS))
        for source in registry["industries"]:
            self.assertEqual(len(source["months_by_year"]),8)
            self.assertEqual(sum(len(x) for x in source["months_by_year"].values()),96)
            self.assertEqual(sorted(source["months_by_year"]),[str(x) for x in m26.YEARS])
        self.assertEqual(m26.validate_bls_source_response(synthetic_response(),book=registry),
                         m26._expected_months(registry))

    def test_offline_report_does_not_claim_fresh_bls_download(self):
        r=m26.report_shell(as_of=TODAY)
        self.assertEqual(r["source_status"],m26.OFFLINE)
        self.assertFalse(r["original_bls_public_api_replayed_this_run"])
        self.assertEqual(r["source_monthly_observations_authenticated_in_this_run"],0)
        self.assertEqual(r["frozen_price_index_monthly_observations"],192)
        self.assertIsNone(r["original_bls_source_receipt_sha256"])
        self.assertEqual(r["receipt_sha256"],canon_hash({
            k:v for k,v in r.items() if k!="receipt_sha256"
        }))

    def test_synthetic_complete_response_is_validated_not_origin_proven(self):
        r=m26.verify_source(as_of=TODAY,response=synthetic_response())
        self.assertEqual(r["source_status"],m26.VERIFIED)
        self.assertTrue(r["original_bls_public_api_replayed_this_run"])
        self.assertEqual(r["source_monthly_observations_authenticated_in_this_run"],192)
        self.assertEqual(len(r["original_bls_source_receipt_sha256"]),64)

    def test_nominal_and_adjusted_industry_revenue_changes_are_distinct(self):
        r=m26.report_shell(as_of=TODAY)
        items={x["naics"]:x for x in r["industry_price_adjustments"]}
        self.assertEqual(len(items),2)
        self.assertEqual(items["484121"]["2017_to_2024_nominal_census_revenue_change_pct"],"43.48")
        self.assertEqual(items["484122"]["2017_to_2024_nominal_census_revenue_change_pct"],"40.93")
        self.assertEqual(items["484121"]["2017_to_2024_illustrative_price_adjusted_revenue_proxy_change_pct"],"2.82")
        self.assertEqual(items["484122"]["2017_to_2024_illustrative_price_adjusted_revenue_proxy_change_pct"],"-1.89")
        self.assertTrue(all(x["price_adjusted_growth_is_not_official_output_growth"] for x in items.values()))

    def test_adjusted_2017_source_anchor_has_identical_nominal_price_2017(self):
        r=m26.report_shell(as_of=TODAY)
        for industry in r["industry_price_adjustments"]:
            vals=industry["annual_observations"]
            self.assertEqual([x["year"] for x in vals],list(m26.YEARS))
            self.assertEqual(len(vals),8)
            self.assertEqual(vals[0]["census_nominal_revenue_million_usd"],
                             vals[0]["2017_price_level_adjusted_revenue_proxy_million_usd"])
            self.assertTrue(all(x["bls_months"]==12 for x in vals))

    def test_parent_all_trucking_absent_not_silently_deflated_with_child_index(self):
        r=m26.report_shell(as_of=TODAY)
        self.assertTrue(r["parent_484_source_rejected_by_bls_v1_api_in_original_probe"])
        self.assertIsNone(r["parent_trucking_naics484_price_adjusted_proxy_pct"])
        self.assertEqual(set(x["naics"] for x in r["industry_price_adjustments"]),set(m26.CODES))
        self.assertFalse(book()["all_trucking_price_index_available_from_original_api"])

    def test_blinded_invoice_and_real_world_recovery_controls_unchanged(self):
        r=m26.report_shell(as_of=TODAY)
        self.assertEqual(r["lab"],14)
        self.assertFalse(r["new_lab_created"])
        self.assertEqual(r["real_customer_freight_invoices_observed"],0)
        self.assertEqual(r["actual_adjudicated_customer_overcharges"],0)
        self.assertIsNone(r["eligible_recovery_market_tam_usd"])
        self.assertIsNone(r["actual_retally_cash_recovered_usd"])
        self.assertFalse(r["buyer_demand_established"])
        self.assertFalse(r["externally_publish_or_contact_customers_carriers"])
        self.assertFalse(r["customer_or_carrier_private_data_used"])
        self.assertTrue(r["human_pilot_18_requirements_unmet"])
        self.assertFalse(r["scheduled_tasks_modified"])
        self.assertTrue(r["ppi_adjusted_revenue_proxy_not_official_bls_real_output_measure"])

    def test_source_changed_month_value_rejected_even_when_all_periods_present(self):
        data=synthetic_response()
        data["Results"]["series"][0]["data"][0]["value"]="999.99"
        with self.assertRaisesRegex(ValueError,"M26_BLS_ORIGINAL_MONTHLY_INDEX_DRIFT"):
            m26.validate_bls_source_response(data,book=book())

    def test_missing_month_rejected_from_original_source(self):
        data=synthetic_response()
        data["Results"]["series"][1]["data"].pop()
        with self.assertRaisesRegex(ValueError,"M26_BLS_TWELVE_DISTINCT_MONTHS_MISSING"):
            m26.validate_bls_source_response(data,book=book())

    def test_duplicate_months_do_not_count_as_complete_annual_average(self):
        data=synthetic_response()
        data["Results"]["series"][0]["data"].append(deepcopy(data["Results"]["series"][0]["data"][-1]))
        with self.assertRaisesRegex(ValueError,"M26_BLS_DUPLICATED_MONTH"):
            m26.validate_bls_source_response(data,book=book())

    def test_preliminary_bls_values_are_not_final_sample_data(self):
        data=synthetic_response()
        data["Results"]["series"][0]["data"][0]["footnotes"]=[{"code":"P","text":"Preliminary"}]
        with self.assertRaisesRegex(ValueError,"M26_BLS_PRELIMINARY_FLAG"):
            m26.validate_bls_source_response(data,book=book())

    def test_source_messages_indicating_missing_parent_in_same_response_fail(self):
        data=synthetic_response()
        data["message"]=["Series does not exist for Series PCU484484"]
        with self.assertRaisesRegex(ValueError,"M26_BLS_SOURCE_HAS_ERROR_OR_UNRESOLVED_MESSAGE"):
            m26.validate_bls_source_response(data,book=book())

    def test_bls_response_failed_status_blocked_from_verified(self):
        data=synthetic_response()
        data["status"]="REQUEST_FAILED"
        with self.assertRaisesRegex(ValueError,"M26_BLS_SOURCE_RESPONSE_NOT_REQUEST_SUCCEEDED"):
            m26.validate_bls_source_response(data,book=book())

    def test_all_trucking_naics_484_parent_series_not_allowlisted(self):
        data=synthetic_response()
        data["Results"]["series"][0]["seriesID"]="PCU484484"
        with self.assertRaisesRegex(ValueError,"M26_BLS_SOURCE_ID_MISSING_DUPLICATED_OR_UNKNOWN"):
            m26.validate_bls_source_response(data,book=book())

    def test_duplicate_series_id_rejected(self):
        data=synthetic_response()
        data["Results"]["series"][1]["seriesID"]=m26.SERIES[0]
        with self.assertRaisesRegex(ValueError,"M26_BLS_SOURCE_ID_MISSING_DUPLICATED_OR_UNKNOWN"):
            m26.validate_bls_source_response(data,book=book())

    def test_dropped_second_source_cannot_make_parent_price_proxy(self):
        data=synthetic_response()
        data["Results"]["series"].pop()
        with self.assertRaisesRegex(ValueError,"M26_BLS_PPI_TWO_VALID_SERIES_REQUIRED"):
            m26.validate_bls_source_response(data,book=book())

    def test_month_13_yearly_average_not_counted_as_a_month(self):
        data=synthetic_response()
        data["Results"]["series"][1]["data"].append({
            "year":"2024","period":"M13","value":"999",
            "footnotes":[],
        })
        val=m26.validate_bls_source_response(data,book=book())
        self.assertEqual(sum(len(y) for yrs in val.values() for y in yrs.values()),192)

    def test_wrong_bls_month_or_earlier_year_not_promoted(self):
        for period in ("M00","M14","S01","January","2024"):
            data=synthetic_response()
            data["Results"]["series"][0]["data"][0]["period"]=period
            with self.assertRaisesRegex(ValueError,"M26_BLS_PPI_NOT_MONTHLY_OBSERVATION",msg=period):
                m26.validate_bls_source_response(data,book=book())
        data=synthetic_response()
        data["Results"]["series"][0]["data"][0]["year"]="2016"
        with self.assertRaisesRegex(ValueError,"M26_BLS_OUT_OF_SCOPE_YEAR"):
            m26.validate_bls_source_response(data,book=book())

    def test_wrong_ppi_decimal_data_or_suppression_rejected(self):
        for val in (None,0,False,{},-1,"NaN","0",".","S","-2.5","3000.999999"):
            with self.assertRaises(ValueError,msg=repr(val)):
                m26._read_decimal(val)

    def test_source_month_registry_manifest_cannot_switch_price_series(self):
        for key,value in (
            ("series_id","PCU484484"),("naics","484"),
            ("label","Payment error rate"),
        ):
            b=book()
            b["industries"][0][key]=value
            self.assertTrue(m26.validate_catalog(b,as_of=TODAY),key)

    def test_year_month_manifest_completeness_protected(self):
        b=book()
        del b["industries"][0]["months_by_year"]["2017"]
        self.assertTrue(m26.validate_catalog(b,as_of=TODAY))
        b=book()
        b["industries"][1]["months_by_year"]["2024"].pop()
        self.assertTrue(m26.validate_catalog(b,as_of=TODAY))

    def test_false_commercial_and_real_output_claims_rejected(self):
        for field in m26.FALSE_GUARDS:
            b=book()
            b[field]=True
            self.assertIn("M26_FORGED_PRICE_OR_FREIGHT_AUDIT_EVIDENCE",
                          "; ".join(m26.validate_catalog(b,as_of=TODAY)),field)

    def test_manifest_cannot_fake_publisher_or_api_endpoint(self):
        for field,value in (
            ("publisher","Private customer invoicing data"),
            ("api_url","https://unapproved.invalid/source"),
            ("index_base","2024=100"),
            ("original_bls_api_probe_receipt_sha256","f"*64),
            ("all_trucking_484_ppi_adjusted_growth_pct","12.00"),
        ):
            b=book()
            b[field]=value
            self.assertTrue(m26.validate_catalog(b,as_of=TODAY),field)

    def test_observation_time_travel_blocked(self):
        self.assertTrue(m26.validate_catalog(book(),as_of=date(2026,10,11)))
        with self.assertRaisesRegex(ValueError,"M26_BLS_PINNED_SOURCE_INVALID"):
            m26.report_shell(as_of=date(2026,10,11))

    def test_offline_and_network_unavailable_distinct(self):
        r=m26.blocked(as_of=TODAY)
        self.assertEqual(r["source_status"],m26.BLOCKED)
        self.assertEqual(r["source_monthly_observations_authenticated_in_this_run"],0)
        self.assertIsNone(r["original_bls_source_receipt_sha256"])
        self.assertEqual(r["receipt_sha256"],canon_hash({
            k:v for k,v in r.items() if k!="receipt_sha256"
        }))

    def test_network_timeout_writes_explicit_block_report(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch("sys.argv",["m26","--out",temp,"--as-of-date","2026-10-12","--fetch-original"]):
                with patch.object(m26,"fetch_bls",side_effect=TimeoutError("network unavailable")):
                    m26.main()
            r=json.loads((Path(temp)/"bls_ppi_adjustment.json").read_text())
            self.assertEqual(r["source_status"],m26.BLOCKED)
            self.assertFalse(r["original_bls_public_api_replayed_this_run"])
            self.assertIsNone(r["eligible_recovery_market_tam_usd"])

    def test_bls_changed_source_is_fail_not_silent_network_block(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch("sys.argv",["m26","--out",temp,"--as-of-date","2026-10-12","--fetch-original"]):
                data=synthetic_response()
                data["Results"]["series"][1]["data"][0]["value"]="1000"
                with patch.object(m26,"fetch_bls",return_value=data):
                    with self.assertRaisesRegex(ValueError,"M26_BLS_ORIGINAL_MONTHLY_INDEX_DRIFT"):
                        m26.main()

    def test_html_escaping_and_qualified_price_adjustment(self):
        r=m26.report_shell(as_of=TODAY)
        r["caveat"]="<script>alert('private')</script>"
        html=m26.render_html(r)
        self.assertNotIn("<script>",html)
        self.assertIn("&lt;script&gt;",html)
        self.assertIn("not verified from the original BLS API",html)
        self.assertIn("not",html.lower())


if __name__=="__main__":
    unittest.main()
