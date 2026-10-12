"""Adversarial SAS 2022 publication-vintage reconciliation, Lab 14 Mission 22.

All source rows in these tests are fabricated. Authenticity can only be claimed
after GitHub Actions downloads and verifies original publisher XLSX digests.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from freight.research_evidence_gate import canon_hash
from freight import research_sas_benchmark as m22

TODAY = date(2026, 10, 11)


def frozen():
    return json.loads(m22.BOOK.read_text(encoding="utf-8"))


def source_probe(ident=m22.REVISED):
    spec=m22.SOURCES[ident]
    key="revised_table2" if ident==m22.REVISED else "original_2017_2022"
    rows=[]
    for i,num in enumerate(spec["selected_naics_rows"]):
        cells={
            "A":"484122",
            "B":"General Freight Trucking, Long-Distance, Less Than Truckload",
            "C":"Revenue",
            "D":"All Establishments" if i==0 else "Establishments subject to federal income tax",
            "E":"Employer Firms",
            "F":format(spec["revenue_2022_million_usd"],","),
            "P":spec["revenue_2022_cv_raw"],
        }
        rows.append({"row":str(num),"cells":{k+str(num):v for k,v in cells.items()}})
    return {
        "source_id":key,
        "source_url":spec["url"],
        "raw_xlsx_bytes":spec["bytes"],
        "raw_xlsx_sha256":spec["sha256"],
        "sheets":[{
            "sheet_member":spec["sheet_member"],
            "rows":spec["sheet_rows"],
            "headings":[
                {"row":"1","cells":{"A1":m22.TITLE}},
                {"row":"5","cells":{
                    "A5":"NAICS","C5":"Item","D5":"Tax Status",
                    "E5":"Employer Status","F5":"2022 Estimate",
                }},
            ],
            "naics_484122_hits":rows,
            "total_matching_rows":2,
        }],
    }


class SasBenchmark2022Tests(unittest.TestCase):
    def test_manifest_fixed_full_git_blob_and_verbatim_census_fingerprints(self):
        self.assertEqual(m22._git_blob(m22.BOOK.read_bytes()),m22.BOOK_SHA1)
        self.assertEqual(m22.validate_book(frozen(),as_of=TODAY),[])
        self.assertEqual(set(m22.SOURCES),{m22.REVISED,m22.LEGACY})
        self.assertEqual(m22.SOURCES[m22.REVISED]["revenue_2022_million_usd"],65688)
        self.assertEqual(m22.SOURCES[m22.LEGACY]["revenue_2022_million_usd"],68411)

    def test_snapshot_distinguishes_actual_revenue_from_auditable_invoices(self):
        r=m22.report_shell(as_of=TODAY)
        self.assertEqual(r["scope"],m22.SCOPE)
        self.assertEqual(r["status"],m22.METADATA)
        self.assertFalse(r["original_source_workbooks_replayed_this_run"])
        self.assertEqual(r["source_vintages_replayed_this_run"],[])
        self.assertEqual(r["vintage_2024_original_sas_million_usd"],68411)
        self.assertEqual(r["vintage_2026_benchmarked_sas_million_usd"],65688)
        self.assertEqual(r["revised_minus_old_sas_million_usd"],-2723)
        self.assertEqual(r["revised_vs_old_sas_pct_change"],"-3.98")
        self.assertEqual(r["original_aies_2022_historical_million_usd"],"65688.461")
        self.assertEqual(r["aies_minus_revised_sas_million_usd"],"0.461")
        self.assertTrue(r["aies_reconciles_to_published_benchmarked_sas_nearest_million"])
        self.assertEqual(r["actual_customer_paid_invoices_observed"],0)
        self.assertIsNone(r["real_customer_recovery_error_rate_pct"])
        self.assertIsNone(r["actual_cash_recoveries_usd"])
        self.assertIsNone(r["recoverable_freight_audit_tam_usd"])
        self.assertFalse(r["commercial_claims_and_carrier_contact_authorized"])
        self.assertTrue(r["human_pilot_18_approval_requirements_unmet"])
        self.assertEqual(r["lab"],14)
        self.assertFalse(r["new_lab_created"])
        self.assertEqual(r["receipt_sha256"],canon_hash({
            k:v for k,v in r.items() if k!="receipt_sha256"
        }))

    def test_exact_source_row_tax_status_subsets_from_both_vintages(self):
        for ident in (m22.REVISED,m22.LEGACY):
            out=m22.selected_sas_source(source_probe(ident),ident=ident)
            self.assertEqual(len(out["selected_source_rows"]),2)
            self.assertEqual(out["source_id"],ident)
            self.assertEqual(out["source_naics"],"484122")
            self.assertTrue(out["two_tax_status_rows_same_survey_not_independent"])
            self.assertEqual(out["number_of_independent_freight_audits"],0)
            self.assertEqual(out["revenue_million_usd"],
                             m22.SOURCES[ident]["revenue_2022_million_usd"])
            self.assertTrue(all(r["census_quality_risk"]==
                                "ZERO_CV_NOT_PROOF_OF_ERROR_FREE_INVOICES"
                                for r in out["selected_source_rows"]))

    def test_source_sha_and_length_protection_beyond_same_row_values(self):
        for ident in (m22.REVISED,m22.LEGACY):
            data=source_probe(ident)
            data["raw_xlsx_sha256"]="f"*64
            with self.assertRaisesRegex(ValueError,"SAS_XLSX_URL_SIZE_OR_SHA256_INCORRECT"):
                m22.selected_sas_source(data,ident=ident)
            data=source_probe(ident)
            data["raw_xlsx_bytes"]+=1
            with self.assertRaisesRegex(ValueError,"SAS_XLSX_URL_SIZE_OR_SHA256_INCORRECT"):
                m22.selected_sas_source(data,ident=ident)

    def test_unknown_source_identifier_never_calls_other_websites(self):
        with self.assertRaisesRegex(ValueError,"SAS_SOURCE_ID_NOT_APPROVED"):
            m22.selected_sas_source(source_probe(),"unknown")
        with self.assertRaisesRegex(ValueError,"SAS_EXACTLY_TWO_PUBLISHER_WORKBOOKS_REQUIRED"):
            m22.verify_source_bytes(as_of=TODAY,archives={})

    def test_missing_or_wrong_industry_year_header_rejected(self):
        for ident in (m22.REVISED,m22.LEGACY):
            for col,value in (
                ("A5","Company ID"),("F5","2023 Estimate"),("D5","No tax status")
            ):
                data=source_probe(ident)
                data["sheets"][0]["headings"][1]["cells"][col]=value
                with self.assertRaisesRegex(ValueError,"SAS_PUBLISHER_WORKBOOK_HEADER_OR_COLUMN_DRIFT"):
                    m22.selected_sas_source(data,ident=ident)

    def test_publisher_worksheet_number_and_count_rejected(self):
        for ident in (m22.REVISED,m22.LEGACY):
            data=source_probe(ident)
            data["sheets"][0]["rows"]-=1
            with self.assertRaisesRegex(ValueError,"SAS_PUBLISHER_SHEET_ROW_COUNT_OR_ID_CHANGED"):
                m22.selected_sas_source(data,ident=ident)

    def test_naics_corruption_and_value_substitution_rejected(self):
        for ident in (m22.REVISED,m22.LEGACY):
            for column,value in (("A","4931"),("B","Public Warehousing"),
                                 ("C","Customer invoice errors"),("E","Nonemployer firms"),
                                 ("F","0"),("P","99")):
                data=source_probe(ident)
                rownum=m22.SOURCES[ident]["selected_naics_rows"][0]
                data["sheets"][0]["naics_484122_hits"][0]["cells"][column+str(rownum)]=value
                with self.assertRaisesRegex(ValueError,"SAS_NAICS_REVENUE_TAX_STATUS_CV_FIELD_DIFFERS"):
                    m22.selected_sas_source(data,ident=ident)

    def test_numeric_units_not_confused_between_millions_and_thousands(self):
        data=source_probe(m22.REVISED)
        num=m22.SOURCES[m22.REVISED]["selected_naics_rows"][0]
        data["sheets"][0]["naics_484122_hits"][0]["cells"]["F"+str(num)]="65,688,461"
        with self.assertRaisesRegex(ValueError,"SAS_NAICS_REVENUE_TAX_STATUS_CV_FIELD_DIFFERS"):
            m22.selected_sas_source(data,ident=m22.REVISED)

    def test_two_tax_status_rows_are_not_independent_surveys(self):
        for ident in (m22.REVISED,m22.LEGACY):
            data=source_probe(ident)
            num=m22.SOURCES[ident]["selected_naics_rows"][1]
            data["sheets"][0]["naics_484122_hits"][1]["cells"]["D"+str(num)]="All Establishments"
            with self.assertRaisesRegex(ValueError,"SAS_NAICS_REVENUE_TAX_STATUS_CV_FIELD_DIFFERS"):
                m22.selected_sas_source(data,ident=ident)

    def test_duplicate_or_missing_naics_row_not_accepted(self):
        data=source_probe()
        data["sheets"][0]["naics_484122_hits"].pop()
        with self.assertRaisesRegex(ValueError,"SAS_ALL_TWO_TAX_STATUS_ROWS_REQUIRED"):
            m22.selected_sas_source(data,ident=m22.REVISED)
        data=source_probe()
        data["sheets"][0]["naics_484122_hits"].append(
            deepcopy(data["sheets"][0]["naics_484122_hits"][0])
        )
        with self.assertRaisesRegex(ValueError,"SAS_ALL_TWO_TAX_STATUS_ROWS_REQUIRED"):
            m22.selected_sas_source(data,ident=m22.REVISED)

    def test_revised_cv_zero_does_not_erase_sampling_and_billing_risks(self):
        b=frozen()
        b["revised_sas_cv_zero_means_exact_no_statistical_error"]=True
        self.assertIn("SAS_UNAUTHORIZED_PUBLISHER_OR_RECOVERY_PROMOTION",
                      "; ".join(m22.validate_book(b,as_of=TODAY)))
        r=m22.report_shell(as_of=TODAY)
        self.assertTrue(r["both_cvs_not_statistically_reconciled_or_independent_samples"])
        self.assertEqual(r["revised_cv_raw_not_invoice_error_rate"],"0")

    def test_false_industry_causal_adjustment_factor_rejected(self):
        for key in (
            "exact_census_industry_specific_carryforward_factor_reproduced",
            "pre_benchmark_modified_survey_row_retrieved",
            "industry_specific_benchmark_ratio_from_unmodified_sample_calculated",
            "all_residual_causes_and_underlying_method_coefficients_proven",
        ):
            b=frozen()
            b[key]=True
            self.assertTrue(m22.validate_book(b,as_of=TODAY),key)

    def test_false_business_or_client_revenue_promotions_rejected(self):
        for key in (
            "aies_historical_2022_is_new_standalone_aies_sample",
            "revised_sas_source_is_independent_economic_sample_from_old_sas",
            "legacy_sas_cv_is_billing_error_rate", "cash_recoveries_proven",
            "buyer_demand_proven","pilot_18_independent_approvals_satisfied",
            "customer_or_carrier_data_processed", "new_lab_created",
            "external_public_marketing_or_financial_claims_authorized",
        ):
            b=frozen()
            b[key]=True
            self.assertTrue(m22.validate_book(b,as_of=TODAY),key)

    def test_source_manifest_tampering_with_workbook_digest_disallowed(self):
        for ident in (m22.REVISED,m22.LEGACY):
            data=frozen()
            row=next(x for x in data["sources"] if x["id"]==ident)
            row["sha256"]="0"*64
            self.assertIn("SAS_FROZEN_PUBLISHER_ARCHIVE_CHANGED",
                          "; ".join(m22.validate_book(data,as_of=TODAY)))

    def test_sas_vintage_2022_million_difference_not_freight_refunds(self):
        report=m22.report_shell(as_of=TODAY)
        self.assertEqual(report["revised_minus_old_sas_million_usd"],-2723)
        self.assertFalse(report["revision_peculiar_to_freight_auditing_or_billing_errors"])
        self.assertFalse(report["exact_modified_sas_sample_and_carryforward_factor_verified"])
        self.assertTrue(report["revision_explained_as_updated_census_benchmark_publication_vintage"])

    def test_older_release_revised_release_differ_and_aies_within_rounding(self):
        report=m22.report_shell(as_of=TODAY)
        self.assertGreater(report["vintage_2024_original_sas_million_usd"],
                           report["vintage_2026_benchmarked_sas_million_usd"])
        self.assertTrue(report["aies_reconciles_to_published_benchmarked_sas_nearest_million"])
        self.assertEqual(report["aies_minus_revised_sas_million_usd"],"0.461")

    def test_wrong_2022_historical_release_date_cannot_pass(self):
        data=frozen()
        data["revised_benchmark_release_date"]="2025-08-31"
        self.assertTrue(m22.validate_book(data,as_of=TODAY))
        self.assertTrue(m22.validate_book(frozen(),as_of=date(2026,10,10)))

    def test_download_timeout_explicitly_blocked_and_not_verified(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch("sys.argv",["runner","--out",folder,
                                   "--as-of-date","2026-10-11",
                                   "--fetch-publisher-workbooks"]):
                with patch.object(m22,"get_source",side_effect=TimeoutError("synthetic source unavailable")):
                    m22.main()
            r=json.loads((Path(folder)/"sas_2022_reconciliation.json").read_text())
            self.assertEqual(r["status"],m22.BLOCKED)
            self.assertFalse(r["original_source_workbooks_replayed_this_run"])
            self.assertEqual(r["source_vintages_replayed_this_run"],[])
            self.assertEqual(r["receipt_sha256"],canon_hash({
                k:v for k,v in r.items() if k!="receipt_sha256"
            }))

    def test_modified_source_bytes_are_fail_not_network_block(self):
        bad={m22.REVISED:b"spoofed",m22.LEGACY:b"spoofed"}
        with self.assertRaisesRegex(ValueError,"SAS_ORIGINAL_XLSX_BYTE_LENGTH_MISMATCH"):
            m22.verify_source_bytes(as_of=TODAY,archives=bad)

    def test_modified_byte_sha_is_checked_after_length(self):
        bad={k:b"x"*v["bytes"] for k,v in m22.SOURCES.items()}
        with self.assertRaisesRegex(ValueError,"SAS_ORIGINAL_XLSX_SHA256_MISMATCH"):
            m22.verify_source_bytes(as_of=TODAY,archives=bad)

    def test_report_html_does_not_accept_unsanitized_user_text(self):
        report=m22.report_shell(as_of=TODAY)
        report["source_caveat"]="<script>alert('x')</script>"
        rendered=m22.render_html(report)
        self.assertNotIn("<script>",rendered)
        self.assertIn("&lt;script&gt;",rendered)
        self.assertIn("2022",rendered)


if __name__=="__main__":
    unittest.main()
