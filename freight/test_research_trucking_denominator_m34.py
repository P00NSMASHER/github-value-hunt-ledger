"""Mission 34 adversarial BEA/Census denominator controls.

Fixtures for two publisher verification paths are synthetic. Only separate
GitHub CI, downloading original XLSX/ZIP files, can authenticate fresh bytes.
No freight invoice or recovery market is estimated by economic table gaps.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date
from decimal import Decimal
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from freight.research_evidence_gate import canon_hash
from freight import research_trucking_denominator_m34 as m34

TODAY=date(2026,10,12)


def book():
    return json.loads(m34.BOOK.read_text(encoding="utf-8"))


def source_reports():
    return (
        m34.census_m25.report_shell(as_of=TODAY),
        m34.bea_m33.report_shell(as_of=TODAY),
    )


def fictional_full_original_receipts():
    """Mock verified source reports: NOT original BEA/Census publisher proof."""
    bea=m34.bea_m33.report_shell(as_of=TODAY)
    census=m34.census_m25.report_shell(as_of=TODAY)
    bea.update({
        "status":m34.bea_m33.VERIFIED,
        "fresh_four_original_bea_tables_year_cells_authenticated":32,
        "fresh_original_bea_xlsx_sha256":m34.bea_m33.BEA_ORIGINAL_SHA256,
        "fresh_primary_source_semantic_receipt_sha256":"a"*64,
    })
    census.update({
        "source_status":m34.census_m25.VERIFIED,
        "census_original_replay_completed_in_this_run":True,
        "source_original_archive_receipts":[
            {"id":m34.census_m25.SAS_ID,"source_tax_year_cells":36},
            {"id":m34.census_m25.HISTORY_ID,"national_industry_year_cells":9},
            {"id":m34.census_m25.BASIC_ID,"national_industry_year_cells":3},
        ],
    })
    return bea,census


class OriginalEconomicDenominatorM34Tests(unittest.TestCase):
    def test_pinned_manifest_git_blob_identity(self):
        self.assertEqual(m34._git_blob(m34.BOOK.read_bytes()),m34.BOOK_BLOB_SHA1)
        self.assertEqual(m34.validate_book(book(),as_of=TODAY),[])
        self.assertEqual(book()["scope"],m34.BOOK_SCOPE)
        self.assertEqual(book()["naics"],"484")

    def test_same_nominal_million_dollar_units_but_different_population(self):
        r=m34.report_shell(as_of=TODAY)
        self.assertEqual(r["unit"],"MILLION_NOMINAL_USD")
        self.assertEqual(r["naics"],"484")
        self.assertFalse(r["bea_census_economic_measurement_coverage_identical_proven"])
        self.assertFalse(r["arithmetic_gap_is_paid_freight_bill_or_overcharge"])
        self.assertFalse(r["economic_population_difference_causally_decomposed"])

    def test_complete_eight_annual_original_source_pair_rows(self):
        r=m34.report_shell(as_of=TODAY)
        self.assertEqual([x["year"] for x in r["annual_comparisons"]],list(m34.YEARS))
        self.assertEqual(len(r["annual_comparisons"]),8)
        self.assertEqual(
            [x["bea_current_dollar_gross_output_million_usd"] for x in r["annual_comparisons"]],
            [v+".000" for v in m34.BEA],
        )
        self.assertEqual(
            [x["census_employer_industry_revenue_million_usd"] for x in r["annual_comparisons"]],
            list(m34.CENSUS),
        )

    def test_2017_2024_absolute_arithmetic_difference_source_verified(self):
        r=m34.report_shell(as_of=TODAY)
        self.assertEqual(r["bea_minus_census_2017_arithmetic_difference_million_usd"],"76622.000")
        self.assertEqual(r["bea_minus_census_2024_arithmetic_difference_million_usd"],"142607.754")
        self.assertEqual(r["annual_comparisons"][5]["bea_minus_census_arithmetic_difference_million_usd"],
                         "154021.042")

    def test_growth_from_original_publishers_not_invoices(self):
        r=m34.report_shell(as_of=TODAY)
        self.assertEqual(r["bea_nominal_gross_output_2017_2024_pct"],"48.56")
        self.assertEqual(r["census_nominal_employer_revenue_2017_2024_pct"],"38.65")
        self.assertEqual(r["difference_in_nominal_growth_percentage_points"],"9.91")
        self.assertEqual(r["bea_real_gross_output_quantity_index_change_pct"],"8.05")
        self.assertFalse(r["arithmetic_gap_is_paid_freight_bill_or_overcharge"])

    def test_census_bea_ratio_not_verified_invoice_market_share(self):
        r=m34.report_shell(as_of=TODAY)
        self.assertEqual(r["census_over_bea_2017_arithmetic_ratio_pct"],"79.13")
        self.assertEqual(r["census_over_bea_2024_arithmetic_ratio_pct"],"73.85")
        self.assertEqual(r["ratio_change_2024_minus_2017_percentage_points"],"-5.28")
        self.assertFalse(r["census_bea_ratio_measures_addressable_freight_market"])
        self.assertTrue(all(x["arithmetic_ratio_measures_freight_invoice_coverage"] is False
                            for x in r["annual_comparisons"]))

    def test_bea_and_bls_producer_prices_are_differently_scoped(self):
        r=m34.report_shell(as_of=TODAY)
        self.assertEqual(r["bea_gross_output_price_index_2017_2024_pct"],"37.49")
        self.assertEqual(r["bls_producer_net_output_ppi_2017_2024_pct"],"37.04")
        self.assertEqual(r["bea_vs_bls_price_change_percentage_points"],"0.45")
        self.assertFalse(r["bea_gross_output_price_index_and_bls_ppi_identical"])

    def test_existing_m29_price_proxy_preserved_not_official_real_output(self):
        r=m34.report_shell(as_of=TODAY)
        self.assertEqual(r["illustrative_census_ppi_adjusted_revenue_change_pct"],"1.18")
        self.assertFalse(r["arithmetic_gap_is_paid_freight_bill_or_overcharge"])
        self.assertTrue(r["parent_484_includes_484121_truckload_and_484122_ltl"])
        self.assertFalse(r["bea_gross_output_and_census_revenue_additive_as_markets"])

    def test_2022_census_is_legacy_linked_and_not_new_independent_aies_survey(self):
        r=m34.report_shell(as_of=TODAY)
        self.assertEqual([row["year"] for row in r["annual_comparisons"]
                          if row["2022_census_legacy_linked_observation"]],[2022])
        self.assertEqual(r["census_2022"],
                         "LEGACY_LINKED_AIES_HISTORICAL_NOT_INDEPENDENT_AIES_SURVEY")

    def test_manifest_guards_reject_faked_missing_invoices_and_tam(self):
        for flag in m34.FALSE_CLAIMS:
            data=book()
            data[flag]=True
            self.assertTrue(m34.validate_book(data,as_of=TODAY),flag)

    def test_source_identity_and_year_tampering_cannot_change_denominator(self):
        for key,value in (
            ("naics","484122"),("years",[2017,2018,2019]),("industry","LTL"),
            ("geography","Pennsylvania"),
            ("bea_gross_output_2017_2024_nominal_growth_pct","100"),
            ("census_over_bea_nominal_ratio_2024_pct","100"),
            ("ratio_change_2024_minus_2017_percentage_points","0"),
        ):
            data=book()
            data[key]=value
            self.assertTrue(m34.validate_book(data,as_of=TODAY),key)

    def test_wrong_bea_or_census_original_publisher_source_rejected(self):
        for industry,field,new in (
            ("bea","source","https://example.invalid/customer-data"),
            ("bea","sheet","TGO106-A"),
            ("bea","unit","MILLIONS_2017_CHAINED"),
            ("census","unit","INVOICE_USD"),
            ("bls","series","PCU484484"),
        ):
            data=book()
            data["sources"][industry][field]=new
            self.assertTrue(m34.validate_book(data,as_of=TODAY),industry)

    def test_changed_2022_census_or_2024_bea_value_detected_in_manifest(self):
        for key,year in (
            ("bea_gross_output_million_nominal_usd","2024"),
            ("census_employer_revenue_million_nominal_usd","2022"),
        ):
            data=book()
            data[key][year]="999999.999"
            self.assertTrue(m34.validate_book(data,as_of=TODAY),key+year)

    def test_missing_2018_or_added_2025_manifest_year_fails(self):
        for key in ("bea_gross_output_million_nominal_usd",
                    "census_employer_revenue_million_nominal_usd"):
            data=book()
            del data[key]["2018"]
            self.assertTrue(m34.validate_book(data,as_of=TODAY))
            data=book()
            data[key]["2025"]="99999"
            self.assertTrue(m34.validate_book(data,as_of=TODAY))

    def test_missing_or_duplicate_naics_484_census_parent_fails(self):
        census,bea=source_reports()
        census["industry_series"]=[x for x in census["industry_series"] if x["naics"]!="484"]
        with self.assertRaisesRegex(ValueError,"M34_CENSUS_PARENT_INDUSTRY_MISSING"):
            m34.compare_nominal_source_rows(bea=bea,census=census,book=book())
        census,bea=source_reports()
        source_row=next(x for x in census["industry_series"] if x["naics"]=="484")
        census["industry_series"].append(deepcopy(source_row))
        with self.assertRaisesRegex(ValueError,"M34_CENSUS_PARENT_INDUSTRY_MISSING"):
            m34.compare_nominal_source_rows(bea=bea,census=census,book=book())

    def test_duplicate_or_swapped_year_from_either_publisher_fails(self):
        for side in ("census","bea"):
            census,bea=source_reports()
            rows=(next(x for x in census["industry_series"] if x["naics"]=="484")
                  ["annual_revenue"] if side=="census" else
                  bea["bea_484_2017_2024_gross_output_annual_observations"])
            rows[1]["year"]=2017
            with self.assertRaisesRegex(ValueError,"M34_SOURCE_YEAR_SEQUENCE_MISSING"):
                m34.compare_nominal_source_rows(bea=bea,census=census,book=book())

    def test_changed_numeric_original_rows_fail_not_silently_pass(self):
        for side in ("census","bea"):
            census,bea=source_reports()
            if side=="census":
                next(x for x in census["industry_series"] if x["naics"]=="484")[
                    "annual_revenue"][6]["revenue_million_usd"]="999.000"
                err="M34_CENSUS_ORIGINAL_SOURCE_ROW_VALUE_CHANGED"
            else:
                bea["bea_484_2017_2024_gross_output_annual_observations"][0][
                    "first_party_bea_current_dollar_gross_output_million_usd"]="999"
                err="M34_BEA_ORIGINAL_SOURCE_ROW_VALUE_CHANGED"
            with self.assertRaisesRegex(ValueError,err):
                m34.compare_nominal_source_rows(bea=bea,census=census,book=book())

    def test_fake_2022_independent_aies_or_freight_bill_detected(self):
        census,bea=source_reports()
        next(x for x in census["industry_series"] if x["naics"]=="484")[
            "annual_revenue"][5]["year_is_linked_legacy_not_standalone_aies_survey"]=False
        with self.assertRaisesRegex(ValueError,"M34_FABRICATED_INDEPENDENT_2022"):
            m34.compare_nominal_source_rows(bea=bea,census=census,book=book())
        census,bea=source_reports()
        bea["bea_484_2017_2024_gross_output_annual_observations"][0][
            "is_customer_invoice_or_recoverable_cash"]=True
        with self.assertRaisesRegex(ValueError,"M34_FABRICATED_INDEPENDENT_2022"):
            m34.compare_nominal_source_rows(bea=bea,census=census,book=book())

    def test_wrong_original_source_scope_rejected(self):
        census,bea=source_reports()
        bea["scope"]="VALUE_ADDED_REAL_GDP"
        with self.assertRaisesRegex(ValueError,"M34_WRONG_ECONOMIC_SOURCE_SCOPE"):
            m34.compare_nominal_source_rows(bea=bea,census=census,book=book())

    def test_offline_does_not_claim_new_original_bea_census_source_bytes(self):
        r=m34.report_shell(as_of=TODAY)
        self.assertEqual(r["source_status"],m34.OFFLINE)
        self.assertFalse(r["fresh_bea_original_workbook_replayed_this_run"])
        self.assertFalse(r["fresh_three_original_census_archives_replayed_this_run"])
        self.assertEqual(r["fresh_original_publisher_file_count"],0)
        self.assertEqual(r["fresh_bea_four_table_year_cells_authenticated"],0)
        self.assertEqual(r["fresh_census_original_source_cell_instances_authenticated"],0)
        self.assertEqual(r["receipt_sha256"],canon_hash({
            k:v for k,v in r.items() if k!="receipt_sha256"
        }))

    def test_source_publisher_manifest_sha_and_separate_bls_provenance(self):
        r=m34.report_shell(as_of=TODAY)
        proofs=r["source_family_manifest_receipts"]
        self.assertEqual(proofs["bea_primary_workbook_sha256"],
                         m34.bea_m33.BEA_ORIGINAL_SHA256)
        self.assertEqual(len(proofs["bea_m33_source_catalog_receipt_sha256"]),64)
        self.assertEqual(len(proofs["census_m25_source_catalog_receipt_sha256"]),64)
        self.assertEqual(len(proofs["bls_m29_source_policy_receipt_sha256"]),64)

    def test_fake_verified_original_replay_semantics_rejected_by_first_party(self):
        r=m34.report_shell(as_of=TODAY)
        self.assertEqual(r["fresh_original_publisher_file_count"],0)
        with self.assertRaisesRegex(ValueError,"M33_ORIGINAL_BEA_XLSX_BYTE_LENGTH_MISMATCH"):
            m34.verify_publishers(
                as_of=TODAY,bea_xlsx=b"fake primary publisher",
                census_archives={},
            )

    def test_fixture_can_validate_replay_combination_but_not_network(self):
        bea,census=fictional_full_original_receipts()
        with patch.object(m34.bea_m33,"verify_original_publisher",return_value=bea):
            with patch.object(m34.census_m25,"verify_origins",return_value=census):
                out=m34.verify_publishers(as_of=TODAY,bea_xlsx=b"not real",census_archives={})
        self.assertEqual(out["source_status"],m34.VERIFIED)
        self.assertEqual(out["fresh_original_publisher_file_count"],4)
        self.assertEqual(out["fresh_bea_four_table_year_cells_authenticated"],32)
        self.assertEqual(out["fresh_census_original_source_cell_instances_authenticated"],48)
        self.assertEqual(len(out["new_original_publisher_receipts"]["census_three_archives"]),3)
        self.assertEqual(out["actual_paid_customer_freight_invoices_observed"],0)

    def test_mocked_wrong_census_source_year_requires_reconciliation_failure(self):
        bea,census=fictional_full_original_receipts()
        next(x for x in census["industry_series"] if x["naics"]=="484")[
            "annual_revenue"][7]["revenue_million_usd"]="9999999.000"
        with patch.object(m34.bea_m33,"verify_original_publisher",return_value=bea):
            with patch.object(m34.census_m25,"verify_origins",return_value=census):
                with self.assertRaisesRegex(ValueError,"M34_FRESH_ORIGINAL_PUBLISHER_NAICS484_YEAR_VALUE_MISMATCH"):
                    m34.verify_publishers(as_of=TODAY,bea_xlsx=b"fake",census_archives={})

    def test_incomplete_original_census_archives_cannot_fake_success(self):
        bea,census=fictional_full_original_receipts()
        census["source_original_archive_receipts"].pop()
        with patch.object(m34.bea_m33,"verify_original_publisher",return_value=bea):
            with patch.object(m34.census_m25,"verify_origins",return_value=census):
                with self.assertRaisesRegex(ValueError,"M34_THREE_CENSUS_ARCHIVES_48_SOURCE_INSTANCES_REQUIRED"):
                    m34.verify_publishers(as_of=TODAY,bea_xlsx=b"fake",census_archives={})

    def test_original_download_timeout_is_distinct_from_source_drift(self):
        r=m34.blocked(as_of=TODAY)
        self.assertEqual(r["source_status"],m34.BLOCKED)
        self.assertEqual(r["fresh_original_publisher_file_count"],0)
        self.assertEqual(r["receipt_sha256"],canon_hash({
            k:v for k,v in r.items() if k!="receipt_sha256"
        }))

    def test_cli_network_timeout_writes_blocked_receipt(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch("sys.argv",["m34","--as-of-date","2026-10-12",
                                   "--fetch-originals","--out",folder]):
                with patch.object(m34,"fetch_all_origins",
                                  side_effect=TimeoutError("synthetic outage")):
                    m34.main()
            out=json.loads((Path(folder)/"trucking_denominator.json").read_text())
            self.assertEqual(out["source_status"],m34.BLOCKED)
            self.assertEqual(out["fresh_original_publisher_file_count"],0)

    def test_workbook_source_change_fails_instead_of_a_network_hold(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch("sys.argv",["m34","--as-of-date","2026-10-12",
                                   "--fetch-originals","--out",folder]):
                with patch.object(m34,"fetch_all_origins",
                                  return_value=(b"forged",{})):
                    with self.assertRaisesRegex(ValueError,"M33_ORIGINAL_BEA_XLSX_BYTE_LENGTH_MISMATCH"):
                        m34.main()

    def test_non_numeric_wrong_zero_bool_and_infinity_rejected(self):
        for n in (None,False,0,"",float("nan"),"NaN","-1","0",{},[],42.5):
            with self.assertRaises(ValueError,msg=str(n)):
                m34._dec(n)

    def test_manifest_denies_fake_recovery_dollars_or_buyer_count(self):
        for key,value in (
            ("real_paid_customer_invoices_observed",1000),
            ("independent_actual_carrier_overcharges_detected",18),
            ("actual_cash_refunds_recovered_usd","100000"),
            ("recovery_market_tam_usd","142607754000"),
            ("real_freight_customers_or_buyers_contacted",1),
        ):
            data=book()
            data[key]=value
            self.assertTrue(m34.validate_book(data,as_of=TODAY),key)

    def test_caveat_cannot_be_removed_or_replaced_by_revenue_promise(self):
        b=book()
        b["source_caveat"]="The difference is recoverable freight invoices."
        self.assertTrue(m34.validate_book(b,as_of=TODAY))

    def test_time_travel_requires_observed_on_or_later_date(self):
        self.assertTrue(m34.validate_book(book(),as_of=date(2026,10,11)))
        with self.assertRaisesRegex(ValueError,"M34_SOURCE_CATALOG_REJECTED"):
            m34.report_shell(as_of=date(2026,10,11))

    def test_html_escapes_untrusted_text_and_disclaims_missing_invoices(self):
        r=m34.report_shell(as_of=TODAY)
        r["caveat"]="<script>alert('freight claims')</script>"
        out=m34.render_html(r)
        self.assertIn("&lt;script&gt;",out)
        self.assertNotIn("<script>",out)
        self.assertIn("NOT a freight-audit TAM",out)
        self.assertIn("142607.754",out)
        self.assertIn("2017",out)
        self.assertIn("2024",out)

    def test_no_public_government_economics_can_satisfy_customer_pilot(self):
        r=m34.report_shell(as_of=TODAY)
        self.assertEqual(r["lab"],14)
        self.assertFalse(r["new_lab_created"])
        self.assertEqual(r["actual_paid_customer_freight_invoices_observed"],0)
        self.assertEqual(r["independently_adjudicated_freight_overcharges"],0)
        self.assertIsNone(r["actual_cash_refunds_usd"])
        self.assertIsNone(r["recoverable_freight_market_tam_usd"])
        self.assertEqual(r["verified_buyers_with_demand"],0)
        self.assertFalse(r["external_carrier_customer_contact_authorized"])
        self.assertTrue(r["all_18_independent_customer_pilot_requirements_unmet"])
        self.assertFalse(r["scheduled_tasks_modified"])


if __name__=="__main__":
    unittest.main()
