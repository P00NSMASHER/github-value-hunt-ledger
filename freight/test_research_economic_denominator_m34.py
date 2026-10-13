"""M34 adversarial tests: source concept and prohibited freight-audit inference.

Synthetic verified source receipts ONLY test the reconciler and never prove
a real direct-publisher fetch. The dedicated CI live-source lane retrieves
original BEA, Census and BLS sources itself.
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
from freight import research_economic_denominator_m34 as m34

TODAY=date(2026,10,12)


def manifest():
    return json.loads(m34.BOOK.read_text(encoding="utf-8"))


def synthetic_receipts():
    """Fixtures exercise policy, not first-party publisher provenance."""
    bea=m34.bea_original(as_of=TODAY)
    cen=m34.census_history(as_of=TODAY)
    bls=m34.original_bls_prices(as_of=TODAY)
    bea.update({
        "status":m34.BEA_VERIFIED,
        "direct_bea_original_numeric_source_authenticated":True,
        "fresh_original_bea_table16_year_cells_authenticated":8,
        "fresh_four_original_bea_tables_year_cells_authenticated":32,
        "fresh_original_bea_xlsx_sha256":m34.BEA_ORIGINAL_SHA256,
    })
    cen.update({
        "source_status":m34.CENSUS_VERIFIED,
        "census_original_replay_completed_in_this_run":True,
        "source_original_archive_receipts":[
            {"id":id_,"sha256":sha}
            for id_,sha in m34.EXPECTED_CENSUS_ORIGINAL_SHA256.items()
        ],
    })
    bls.update({
        "status":m34.BLS_VERIFIED,
        "current_original_bls_source_replayed_this_run":True,
        "current_source_authenticated_month_count":288,
        "original_bls_response_sha256":"b"*64,
    })
    for source in (bea,cen,bls):
        source["receipt_sha256"]=canon_hash({
            k:v for k,v in source.items() if k!="receipt_sha256"
        })
    return bea,cen,bls


class NominalIndustryDenominatorTests(unittest.TestCase):
    def test_original_source_book_pinned_git_blob(self):
        self.assertEqual(m34._blob(m34.BOOK.read_bytes()),m34.BOOK_SHA1)
        self.assertEqual(m34.validate_policy(manifest(),as_of=TODAY),[])
        self.assertEqual(manifest()["naics"],"484")
        self.assertEqual(manifest()["years"],list(m34.YEARS))

    def test_bea_census_bls_distinct_source_roles_preserved(self):
        b=manifest()
        self.assertEqual(set(b["sources"]),{"bea","census","bls"})
        self.assertEqual(b["sources"]["bea"]["repository_book_git_blob_sha1"],
                         "501ec6d18cdc29b7ac6b7c718c1d85d5f520fafd")
        self.assertEqual(b["sources"]["census"]["repository_book_git_blob_sha1"],
                         "0df081d41cb519b142c1ccfcbaf9d14bd82af3d0")
        self.assertEqual(b["sources"]["bls"]["series"],"PCU484---484---")
        self.assertEqual(b["sources"]["bea"]["unit"],"MILLION_CURRENT_USD")
        self.assertEqual(b["sources"]["census"]["unit"],
                         "MILLION_NOMINAL_USD_EMPLOYER_INDUSTRY")

    def test_full_eight_year_sourced_nominal_bea_census_values(self):
        r=m34.report_shell(as_of=TODAY)
        rows=r["comparison_2017_to_2024"]
        self.assertEqual(len(rows),8)
        self.assertEqual([x["year"] for x in rows],list(m34.YEARS))
        self.assertEqual([x["bea_nominal_gross_output_million_usd"] for x in rows],
                         [m34._f3(Decimal(x)) for x in m34.EXPECTED_BEANOM])
        self.assertEqual([x["census_employer_industry_revenue_million_usd"]
                          for x in rows],
                         [m34._f3(Decimal(x)) for x in m34.EXPECTED_CENSUS])

    def test_eight_year_dollar_differences_are_descriptive_not_recoveries(self):
        r=m34.report_shell(as_of=TODAY)
        expected=["76622.000","90636.000","95381.000","105464.000",
                  "129091.000","154021.042","140341.990","142607.754"]
        rows=r["comparison_2017_to_2024"]
        self.assertEqual([x["bea_minus_census_nominal_difference_million_usd"]
                          for x in rows],expected)
        self.assertTrue(all(
            x["nominal_difference_is_actual_missed_invoices_or_recoverable_cash"] is False
            for x in rows
        ))
        self.assertTrue(all(
            x["ratio_is_share_of_actual_freight_invoices"] is False for x in rows
        ))

    def test_growth_rates_difference_and_measure_ratio_are_not_market_coverage(self):
        r=m34.report_shell(as_of=TODAY)
        self.assertEqual(r["bea_2017_to_2024_nominal_growth_pct"],"48.56")
        self.assertEqual(r["census_2017_to_2024_nominal_growth_pct"],"38.65")
        self.assertEqual(r["bea_minus_census_nominal_growth_percentage_points"],"9.91")
        self.assertEqual(r["nominal_census_to_bea_measure_ratio_2017_pct"],"79.13")
        self.assertEqual(r["nominal_census_to_bea_measure_ratio_2024_pct"],"73.85")
        self.assertEqual(r["ratio_change_percentage_points"],"-5.28")
        self.assertFalse(r["census_nominal_ratio_to_bea_is_actual_market_coverage"])

    def test_gap_rises_but_not_billing_errors_or_missing_invoices(self):
        r=m34.report_shell(as_of=TODAY)
        self.assertEqual(r["bea_minus_census_nominal_2017_million_usd"],"76622.000")
        self.assertEqual(r["bea_minus_census_nominal_2024_million_usd"],"142607.754")
        self.assertEqual(
            r["bea_minus_census_nominal_gap_increase_2017_to_2024_million_usd"],
            "65985.754"
        )
        self.assertFalse(r["nominal_gap_is_missing_carrier_invoices_or_recoverable_overcharges"])
        self.assertFalse(r["nominal_gap_has_decomposed_verified_economic_causes"])

    def test_bea_price_vs_bls_net_output_ppi_are_not_same_deflator(self):
        r=m34.report_shell(as_of=TODAY)
        self.assertEqual(r["bea_gross_output_2017_2024_price_index_growth_pct"],"37.49")
        self.assertEqual(r["bls_2017_2024_net_output_producer_price_growth_pct"],"37.04")
        self.assertEqual(r["bea_minus_bls_producer_price_change_difference_pp"],"0.45")
        self.assertEqual(
            r["census_bls_ppi_2017_2024_illustrative_adjusted_revenue_growth_pct"],
            "1.18"
        )
        self.assertFalse(r["bea_price_and_bls_net_output_ppi_interchangeable"])

    def test_original_2022_data_are_linked_historical_census_not_new_standalone(self):
        r=m34.report_shell(as_of=TODAY)
        byyear={x["year"]:x for x in r["comparison_2017_to_2024"]}
        self.assertEqual(byyear[2021]["census_source_year_family"],
                         "REVISED_2026_SAS_2017_2021")
        self.assertEqual(byyear[2022]["census_source_year_family"],
                         "2024_AIES_LINKED_HISTORICAL_2022_2024")
        self.assertEqual(byyear[2022]["census_employer_industry_revenue_million_usd"],
                         "423270.958")

    def test_offline_report_has_zero_fresh_publisher_source_claims(self):
        r=m34.report_shell(as_of=TODAY)
        self.assertEqual(r["source_status"],m34.OFFLINE)
        self.assertFalse(r["full_three_first_party_source_families_replayed_this_run"])
        self.assertEqual(r["source_families_authenticated_fresh_this_run"],0)
        self.assertIsNone(r["bea_original_xlsx_sha256_verified_this_run"])
        self.assertFalse(r["census_three_publisher_archives_verified_this_run"])
        self.assertFalse(r["bls_original_288_ppi_months_verified_this_run"])
        self.assertEqual(len(r["source_original_replay_statuses"]),3)

    def test_fake_incomplete_eight_year_source_rejected(self):
        bea={y:Decimal(m34.EXPECTED_BEANOM[i]) for i,y in enumerate(m34.YEARS)}
        census={y:Decimal(m34.EXPECTED_CENSUS[i]) for i,y in enumerate(m34.YEARS)}
        self.assertEqual(len(m34.nominal_comparison(bea,census)),8)
        del census[2017]
        with self.assertRaisesRegex(ValueError,"M34_EXACTLY_EIGHT_NATIONAL_NAICS484_YEARS_REQUIRED"):
            m34.nominal_comparison(bea,census)

    def test_bad_decimal_nan_zero_boolean_and_wrong_grain_rejected(self):
        for val in ("NaN","Infinity","-1","0","",False,0,None,{},[]):
            with self.assertRaises(ValueError,msg=repr(val)):
                m34._d(val)
        with self.assertRaisesRegex(ValueError,"M34_NATIONAL_NOMINAL_VALUE_NON_DECIMAL_OR_INVALID"):
            m34.nominal_comparison(
                {y:Decimal("10") for y in m34.YEARS},
                {y:("10" if y==2017 else Decimal("5")) for y in m34.YEARS}
            )

    def test_forged_original_bea_source_catalog_value_rejected(self):
        b=manifest()
        b["bea_gross_output_million_nominal_usd"]["2024"]="999999.000"
        self.assertTrue(m34.validate_policy(b,as_of=TODAY))

    def test_forged_census_source_catalog_value_rejected(self):
        b=manifest()
        b["census_employer_revenue_million_nominal_usd"]["2022"]="426000"
        self.assertTrue(m34.validate_policy(b,as_of=TODAY))

    def test_original_source_survey_ids_sha_and_url_cannot_be_substituted(self):
        for family in ("bea","census","bls"):
            b=manifest()
            b["sources"][family]["publisher"]="Private freight bills audit"
            self.assertTrue(m34.validate_policy(b,as_of=TODAY),family)
        for family in ("bea","census"):
            b=manifest()
            b["sources"][family]["repository_book_git_blob_sha1"]="0"*40
            self.assertTrue(m34.validate_policy(b,as_of=TODAY),family)

    def test_illegal_customer_market_claims_rejected_on_all_policy_flags(self):
        for flag in m34.FALSE_FLAGS:
            b=manifest()
            b[flag]=True
            self.assertTrue(m34.validate_policy(b,as_of=TODAY),flag)

    def test_policy_cannot_inject_customer_invoices_or_refunds(self):
        for key,value in (
            ("real_paid_customer_invoices_observed",42),
            ("independent_actual_carrier_overcharges_detected",1),
            ("actual_cash_refunds_recovered_usd",1000000),
            ("recovery_market_tam_usd",142607754000),
            ("real_freight_customers_or_buyers_contacted",5),
        ):
            b=manifest()
            b[key]=value
            self.assertTrue(m34.validate_policy(b,as_of=TODAY),key)

    def test_no_source_time_travel_or_extra_fields(self):
        self.assertTrue(m34.validate_policy(manifest(),as_of=date(2026,10,11)))
        b=manifest()
        b["carrier_paid_invoice_file"]="private"
        self.assertTrue(m34.validate_policy(b,as_of=TODAY))
        with self.assertRaisesRegex(ValueError,"M34_SOURCE_DENOMINATOR_POLICY_INVALID"):
            m34.report_shell(as_of=date(2026,10,11))

    def test_tam_18_real_customer_pilot_gates_are_still_unmet(self):
        r=m34.report_shell(as_of=TODAY)
        self.assertEqual(r["lab"],14)
        self.assertFalse(r["new_lab_created"])
        self.assertEqual(r["real_paid_customer_freight_invoices"],0)
        self.assertEqual(r["adjudicated_freight_invoice_errors"],0)
        self.assertIsNone(r["retally_recovered_cash_usd"])
        self.assertIsNone(r["recoverable_audit_market_tam_usd"])
        self.assertFalse(r["buyer_demand_established"])
        self.assertFalse(r["customer_or_carrier_contact_authorized"])
        self.assertFalse(r["private_customer_data_accessed"])
        self.assertTrue(r["human_pilot_18_independent_requirements_unmet"])
        self.assertFalse(r["scheduled_tasks_modified"])

    def test_synthetic_three_complete_verified_receipts_semantic_check(self):
        receipts=synthetic_receipts()
        r=m34.verify_source_receipts(as_of=TODAY,bea=receipts[0],
                                      census=receipts[1],bls=receipts[2])
        self.assertEqual(r["source_status"],m34.VERIFIED)
        self.assertEqual(r["source_families_authenticated_fresh_this_run"],3)
        self.assertTrue(r["full_three_first_party_source_families_replayed_this_run"])
        self.assertEqual(r["bea_original_xlsx_sha256_verified_this_run"],
                         m34.BEA_ORIGINAL_SHA256)
        self.assertTrue(r["census_three_publisher_archives_verified_this_run"])
        self.assertTrue(r["bls_original_288_ppi_months_verified_this_run"])
        self.assertEqual(r["receipt_sha256"],canon_hash({
            k:v for k,v in r.items() if k!="receipt_sha256"
        }))

    def test_forged_verified_receipt_integrity_fails(self):
        bea,cen,bls=synthetic_receipts()
        bea["bea_nominal_gross_output_2024_million_usd"]="777"
        with self.assertRaisesRegex(ValueError,"M34_PRIOR_PUBLISHER_EVIDENCE_RECEIPT_HASH_CHANGED"):
            m34.verify_source_receipts(as_of=TODAY,bea=bea,census=cen,bls=bls)

    def test_false_bea_32_original_cells_fails(self):
        bea,cen,bls=synthetic_receipts()
        bea["fresh_four_original_bea_tables_year_cells_authenticated"]=0
        bea["receipt_sha256"]=canon_hash({k:v for k,v in bea.items() if k!="receipt_sha256"})
        with self.assertRaisesRegex(ValueError,"M34_MISSING_32_FIRST_PARTY_BEA_XLSX_SOURCE_CELLS"):
            m34.verify_source_receipts(as_of=TODAY,bea=bea,census=cen,bls=bls)

    def test_fake_original_bea_changed_2024_nominal_cell_rejected(self):
        bea,cen,bls=synthetic_receipts()
        bea["bea_484_2017_2024_gross_output_annual_observations"][-1][
            "first_party_bea_current_dollar_gross_output_million_usd"
        ]="9999999"
        bea["receipt_sha256"]=canon_hash({k:v for k,v in bea.items() if k!="receipt_sha256"})
        with self.assertRaisesRegex(ValueError,"M34_FRESH_BEA_REAL_PUBLISHER_NOMINAL_SOURCE_DISAGREES"):
            m34.verify_source_receipts(as_of=TODAY,bea=bea,census=cen,bls=bls)

    def test_fake_census_2024_employer_receipts_rejected(self):
        bea,cen,bls=synthetic_receipts()
        row=next(x for x in cen["industry_series"] if x["naics"]=="484")
        row["annual_revenue"][-1]["revenue_million_usd"]="999999.999"
        cen["receipt_sha256"]=canon_hash({k:v for k,v in cen.items() if k!="receipt_sha256"})
        with self.assertRaisesRegex(ValueError,"M34_FRESH_CENSUS_ORIGINAL_NOMINAL_SOURCE_DISAGREES"):
            m34.verify_source_receipts(as_of=TODAY,bea=bea,census=cen,bls=bls)

    def test_wrong_census_archives_cannot_be_passed_by_claimed_success(self):
        bea,cen,bls=synthetic_receipts()
        cen["source_original_archive_receipts"][0]["sha256"]="0"*64
        cen["receipt_sha256"]=canon_hash({k:v for k,v in cen.items() if k!="receipt_sha256"})
        with self.assertRaisesRegex(ValueError,"M34_MISSING_OR_CHANGED_THREE_CENSUS_ORIGINAL_ARCHIVES"):
            m34.verify_source_receipts(as_of=TODAY,bea=bea,census=cen,bls=bls)

    def test_missing_original_bls_months_causes_failure(self):
        bea,cen,bls=synthetic_receipts()
        bls["current_source_authenticated_month_count"]=96
        bls["receipt_sha256"]=canon_hash({k:v for k,v in bls.items() if k!="receipt_sha256"})
        with self.assertRaisesRegex(ValueError,"M34_BLS_DIRECT_ORIGINAL_MONTHS_NOT_288"):
            m34.verify_source_receipts(as_of=TODAY,bea=bea,census=cen,bls=bls)

    def test_fresh_bea_original_network_block_does_not_prove_all_three(self):
        bea,cen,bls=synthetic_receipts()
        bea["status"]="M33_ORIGINAL_BEA_XLSX_NETWORK_UNAVAILABLE_NO_NEW_SOURCE_REPLAY"
        bea["receipt_sha256"]=canon_hash({k:v for k,v in bea.items() if k!="receipt_sha256"})
        r=m34.verify_source_receipts(as_of=TODAY,bea=bea,census=cen,bls=bls)
        self.assertEqual(r["source_status"],m34.BLOCKED)
        self.assertEqual(r["source_families_authenticated_fresh_this_run"],2)
        self.assertFalse(r["full_three_first_party_source_families_replayed_this_run"])
        self.assertIsNone(r["bea_original_xlsx_sha256_verified_this_run"])

    def test_wrong_publisher_state_is_failure_not_network_blocked(self):
        bea,cen,bls=synthetic_receipts()
        cen["source_status"]="INVALID_CENSUS_SOURCE_DISTRIBUTION"
        cen["receipt_sha256"]=canon_hash({k:v for k,v in cen.items() if k!="receipt_sha256"})
        with self.assertRaisesRegex(ValueError,"M34_ORIGINAL_CENSUS_PUBLISHER_SOURCE_STATUS_WRONG"):
            m34.verify_source_receipts(as_of=TODAY,bea=bea,census=cen,bls=bls)

    def test_partial_census_network_block_does_not_claim_full_origin(self):
        bea,cen,bls=synthetic_receipts()
        cen["source_status"]="BLOCKED_CENSUS_SOURCE_NOT_REACHABLE_NO_NEW_REPLAY"
        cen["receipt_sha256"]=canon_hash({k:v for k,v in cen.items() if k!="receipt_sha256"})
        r=m34.verify_source_receipts(as_of=TODAY,bea=bea,census=cen,bls=bls)
        self.assertEqual(r["source_status"],m34.BLOCKED)
        self.assertFalse(r["census_three_publisher_archives_verified_this_run"])
        self.assertEqual(r["source_families_authenticated_fresh_this_run"],2)

    def test_html_labels_all_gap_values_not_customer_spend(self):
        r=m34.report_shell(as_of=TODAY)
        r["caveat"]="<img src=x onerror=alert('overcharges')>"
        html=m34.render_html(r)
        self.assertNotIn("<img src=x",html)
        self.assertIn("&lt;img src=x",html)
        self.assertIn("NOT a missing-freight-invoice",html)
        self.assertIn("NOT invoice coverage",html)
        self.assertIn(m34.OFFLINE,html)

    def test_offline_receipt_hash_stable(self):
        r=m34.report_shell(as_of=TODAY)
        self.assertEqual(r["receipt_sha256"],canon_hash({
            k:v for k,v in r.items() if k!="receipt_sha256"
        }))


if __name__=="__main__":
    unittest.main()
