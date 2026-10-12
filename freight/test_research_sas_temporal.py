"""Mission 24 adversarial Census SAS temporal revision tests (all synthetic/offline).

The pure source-row tests never constitute original U.S. Census ZIP-byte proof.
A separate CI job must replay both exact publisher workbooks.
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
from freight import research_sas_temporal as m24

TODAY=date(2026,10,11)


def catalog():
    return json.loads(m24.BOOK.read_text(encoding="utf-8"))


def synthetic_rows(ident=m24.REVISED):
    data=[]
    for code in m24.NAICS:
        label,positions,_,cv=m24.M23_2022[ident][code]
        yearly=m24.EXPECTED_ANNUAL[ident][code]
        for i,rowno in enumerate(positions):
            cell={
                "A":code,"B":label,"C":"Revenue",
                "D":"All Establishments" if i==0 else
                    "Establishments subject to federal income tax",
                "E":"Employer Firms","P":cv,
            }
            for year,value in zip(m24.YEARS,yearly):
                cell[m24.COLUMNS[year]]=format(value,",")
            data.append((rowno,cell))
    return data


class HistoricalSasRevisionTests(unittest.TestCase):
    def test_git_pinned_manifest_and_closed_source_catalog(self):
        self.assertEqual(m24._blob(m24.BOOK.read_bytes()),m24.BOOK_BLOB_SHA1)
        self.assertEqual(m24.validate_manifest(catalog(),as_of=TODAY),[])
        self.assertEqual(tuple(catalog()["year_range"]),m24.YEARS)
        self.assertEqual(set(catalog()["original_source_vintages"]),set(m24.IDS))

    def test_all_2017_anchors_unchanged_in_both_vintages(self):
        r=m24.report_shell(as_of=TODAY)
        self.assertEqual(r["2017_unchanged_anchor_categories"],3)
        self.assertEqual(r["source_year_cells_changed"],15)
        self.assertEqual(r["2018_2022_downward_revised_categories_years"],15)
        self.assertEqual(r["unique_naics_year_vintage_comparisons"],36)
        self.assertEqual(r["original_excel_tax_population_year_cells_required"],72)
        for x in r["industry_comparisons"]:
            self.assertTrue(x["same_published_2017_anchor"])
            self.assertEqual(x["first_year_revision_detected"],2018)
            self.assertEqual(x["annual_comparisons"][0]["signed_vintage_revision_million_usd"],0)

    def test_all_2018_2022_source_revisions_downward_and_increasing_absolute_magnitude(self):
        r=m24.report_shell(as_of=TODAY)
        for industry in r["industry_comparisons"]:
            self.assertTrue(industry["2018_to_2022_every_year_downward_revised"])
            self.assertTrue(industry["absolute_benchmark_revision_increases_each_year"])
            changes=[-x["signed_vintage_revision_million_usd"]
                     for x in industry["annual_comparisons"]]
            self.assertEqual(changes[0],0)
            self.assertEqual(changes,sorted(changes))
            self.assertTrue(all(changes[i]<changes[i+1] for i in range(5)))

    def test_source_vintage_growth_revisions_exact_from_publisher_survey(self):
        r=m24.report_shell(as_of=TODAY)
        bycode={x["naics"]:x for x in r["industry_comparisons"]}
        for code,old,new,diff in (
            ("484","53.34","45.69","-7.65"),
            ("484121","63.18","53.61","-9.57"),
            ("484122","48.10","42.21","-5.89"),
        ):
            x=bycode[code]
            self.assertEqual(x["2017_to_2022_older_vintage_nominal_cumulative_growth_pct"],old)
            self.assertEqual(x["2017_to_2022_benchmarked_nominal_cumulative_growth_pct"],new)
            self.assertEqual(x["revised_minus_old_cumulative_growth_pp"],diff)
            self.assertTrue(x["nominal_growth_is_not_inflation_adjusted_or_causally_identified"])

    def test_ltl_2020_and_2022_source_series_remain_exact(self):
        r=m24.report_shell(as_of=TODAY)
        rows=next(x for x in r["industry_comparisons"] if x["naics"]=="484122")["annual_comparisons"]
        self.assertEqual([x["year"] for x in rows],list(m24.YEARS))
        self.assertEqual(rows[3]["earlier_sas_revenue_million_usd"],50515)
        self.assertEqual(rows[3]["revised_sas_revenue_million_usd"],49186)
        self.assertEqual(rows[5]["signed_vintage_revision_million_usd"],-2723)
        self.assertEqual(rows[5]["revision_pct_of_earlier_vintage"],"-3.98")

    def test_source_scope_still_14_labs_and_18_human_approval_holds(self):
        r=m24.report_shell(as_of=TODAY)
        self.assertEqual(r["lab"],14)
        self.assertFalse(r["new_lab_created"])
        self.assertIsNone(r["freight_invoice_error_rate_pct"])
        self.assertIsNone(r["recoverable_overpayment_market_usd"])
        self.assertIsNone(r["actual_retally_recovered_cash_usd"])
        self.assertEqual(r["actual_paid_customer_freight_invoice_sample_size"],0)
        self.assertFalse(r["buyer_demand_study_completed"])
        self.assertFalse(r["actual_customer_data_ingested"])
        self.assertTrue(r["pilot_18_independent_external_controls_still_unmet"])
        self.assertFalse(r["scheduled_tasks_created_or_modified"])
        self.assertFalse(r["permitted_commercial_publication_or_outreach"])

    def test_frozen_workbook_source_sha_and_row_shapes_cannot_drift(self):
        for ident in m24.IDS:
            for key,value in (
                ("source_url","https://unauthorized.example/pretend"),
                ("source_xlsx_sha256","0"*64),
                ("source_xlsx_bytes",123),
                ("source_sheet_member","xl/worksheets/other.xml"),
                ("source_sheet_row_count",38),
            ):
                b=catalog()
                b["original_source_vintages"][ident][key]=value
                self.assertTrue(m24.validate_manifest(b,as_of=TODAY),key)

    def test_rejected_private_data_in_catalog_or_source_rows(self):
        b=catalog()
        b["customer_invoice_number"]="private"
        self.assertTrue(m24.validate_manifest(b,as_of=TODAY))
        b=catalog()
        b["original_source_vintages"][m24.LEGACY]["industries"]["484122"]["customer_invoice_id"]="X"
        self.assertTrue(m24.validate_manifest(b,as_of=TODAY))

    def test_source_book_rejects_removed_year_or_changed_2020_revenue(self):
        for ident in m24.IDS:
            for code in m24.NAICS:
                b=catalog()
                del b["original_source_vintages"][ident]["industries"][code]["yearly_revenue_million_usd"]["2021"]
                self.assertTrue(m24.validate_manifest(b,as_of=TODAY))
                b=catalog()
                b["original_source_vintages"][ident]["industries"][code]["yearly_revenue_million_usd"]["2020"]+=1
                self.assertTrue(m24.validate_manifest(b,as_of=TODAY))

    def test_source_book_industry_and_tax_row_cannot_be_swapped(self):
        for ident in m24.IDS:
            b=catalog()
            b["original_source_vintages"][ident]["industries"]["484121"]["all_establishments_row"]=40
            self.assertTrue(m24.validate_manifest(b,as_of=TODAY))
            b=catalog()
            b["original_source_vintages"][ident]["industries"]["484122"]["raw_2022_cv_pct"]="99"
            self.assertTrue(m24.validate_manifest(b,as_of=TODAY))

    def test_source_book_must_preserve_false_evidence_guards(self):
        for flag in m24.FALSE_GUARDS:
            b=catalog()
            b[flag]=True
            self.assertIn("M24_UNAUTHORIZED_SOURCE_OR_COMMERCIAL_PROMOTION",
                          "; ".join(m24.validate_manifest(b,as_of=TODAY)),flag)
        b=catalog()
        b["pilot_18_independent_approvals_still_unverified"]=False
        self.assertTrue(m24.validate_manifest(b,as_of=TODAY))

    def test_parent_child_overlap_and_tax_status_not_independent(self):
        book=catalog()
        self.assertTrue(book["parent_and_child_categories_cannot_be_added_as_distinct_markets"])
        self.assertTrue(book["both_tax_status_rows_are_not_two_independent_observations"])
        self.assertFalse(book["benchmarking_years_are_separate_survey_panels"])

    def test_pure_synthetic_row_checks_all_six_years_both_tax_classes(self):
        for ident in m24.IDS:
            rows=m24.audit_rows(synthetic_rows(ident),ident=ident)
            self.assertEqual(len(rows),6)
            self.assertEqual(sum(len(x["annual_revenue_million_usd"]) for x in rows),36)
            self.assertEqual(set(x["naics"] for x in rows),set(m24.NAICS))
            self.assertEqual(sum(x["tax_population"]=="All Establishments" for x in rows),3)
            self.assertTrue(all(x["independent_customer_invoice_count"]==0 for x in rows))

    def test_zero_and_negative_revenue_are_not_reported_published_cells(self):
        for amount in ("0","-5","1.9",".","S","",None,"$23,000"):
            rows=synthetic_rows(m24.REVISED)
            rows[0][1]["H"]=amount
            with self.assertRaises(ValueError,msg=str(amount)):
                m24.audit_rows(rows,ident=m24.REVISED)

    def test_one_dollar_unit_error_in_any_year_fails_closed(self):
        for ident in m24.IDS:
            for year,col in m24.COLUMNS.items():
                rows=synthetic_rows(ident)
                orig=rows[0][1][col]
                rows[0][1][col]=str(int(orig.replace(",",""))+1)
                with self.assertRaisesRegex(ValueError,"M24_CENSUS_ANNUAL_VALUE_MISMATCH",
                                            msg=ident+str(year)):
                    m24.audit_rows(rows,ident=ident)

    def test_source_metadata_change_cv_or_label_or_tax_cohort_is_rejected(self):
        for ident in m24.IDS:
            for key,value in (("B","Freight recovery invoice billing"),
                              ("D","Only individual customers"),
                              ("P","0.1"),
                              ("E","Nonemployer firms")):
                rows=synthetic_rows(ident)
                rows[0][1][key]=value
                with self.assertRaises(ValueError,msg=key):
                    m24.audit_rows(rows,ident=ident)

    def test_duplicate_expected_tax_status_row_is_not_new_source(self):
        for ident in m24.IDS:
            rows=synthetic_rows(ident)
            rows.append(deepcopy(rows[0]))
            with self.assertRaisesRegex(ValueError,"M24_DUPLICATE_SOURCE_ROW"):
                m24.audit_rows(rows,ident=ident)

    def test_missing_industry_or_tax_row_detected(self):
        for ident in m24.IDS:
            rows=synthetic_rows(ident)
            for k in range(len(rows)):
                limited=rows[:k]+rows[k+1:]
                with self.assertRaisesRegex(ValueError,"M24_SOURCE_YEAR_NAICS_TAX_ROWS_INCOMPLETE",
                                            msg=ident+str(k)):
                    m24.audit_rows(limited,ident=ident)

    def test_swapped_source_year_values_do_not_pass(self):
        rows=synthetic_rows(m24.LEGACY)
        rows[0][1]["H"],rows[0][1]["I"]=rows[0][1]["I"],rows[0][1]["H"]
        with self.assertRaisesRegex(ValueError,"M24_CENSUS_ANNUAL_VALUE_MISMATCH"):
            m24.audit_rows(rows,ident=m24.LEGACY)

    def test_source_row_address_spoofing_fails(self):
        rows=synthetic_rows(m24.LEGACY)
        rows[0]=(rows[0][0]+9,rows[0][1])
        with self.assertRaisesRegex(ValueError,"M24_UNEXPECTED_SAS_NAICS_SOURCE_ROW_ADDRESS"):
            m24.audit_rows(rows,ident=m24.LEGACY)

    def test_wrong_source_id_prohibited(self):
        with self.assertRaisesRegex(ValueError,"M24_UNKNOWN_PUBLIC_CENSUS_SOURCE_OR_ROWS"):
            m24.audit_rows(synthetic_rows(),ident="unknown")
        with self.assertRaisesRegex(ValueError,"M24_UNAUTHORIZED_CENSUS_SOURCE"):
            m24.inspect_workbook(b"invalid",ident="unknown")

    def test_changed_original_archive_rejected_before_source_parser(self):
        for ident in m24.IDS:
            with self.assertRaisesRegex(ValueError,"M24_ORIGINAL_WORKBOOK_BYTE_LENGTH_MISMATCH"):
                m24.inspect_workbook(b"fake",ident=ident)
            with self.assertRaisesRegex(ValueError,"M24_ORIGINAL_WORKBOOK_SHA256_CHANGED"):
                m24.inspect_workbook(b"x"*m24.M22_SOURCES[ident]["bytes"],ident=ident)

    def test_unavailable_single_source_does_not_claim_both_verified(self):
        with self.assertRaisesRegex(ValueError,"M24_TWO_SOURCE_VINTAGES_REQUIRED_FOR_ORIGINAL_REPLAY"):
            m24.verify_originals(as_of=TODAY,archives={m24.REVISED:b"fake"})

    def test_offline_and_blocked_source_statuses_distinct(self):
        base=m24.report_shell(as_of=TODAY)
        hold=m24.blocked(as_of=TODAY)
        self.assertEqual(base["source_status"],m24.OFFLINE)
        self.assertEqual(hold["source_status"],m24.BLOCKED)
        self.assertFalse(hold["census_original_workbooks_replayed_this_run"])
        self.assertEqual(hold["original_census_workbook_receipts"],[])
        self.assertEqual(hold["receipt_sha256"],canon_hash({
            k:v for k,v in hold.items() if k!="receipt_sha256"
        }))

    def test_http_timeout_generates_blocked_evidence_json_not_publisher_proof(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch("sys.argv",["prog","--out",folder,"--as-of-date","2026-10-11",
                                    "--fetch-originals"]):
                with patch.object(m24,"get_source",side_effect=TimeoutError("synthetic network")):
                    m24.main()
            report=json.loads((Path(folder)/"sas_temporal_revisions.json").read_text())
            self.assertEqual(report["source_status"],m24.BLOCKED)
            self.assertFalse(report["census_original_workbooks_replayed_this_run"])
            self.assertIsNone(report["freight_invoice_error_rate_pct"])

    def test_corrupted_census_file_fails_not_marked_network_block(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch("sys.argv",["prog","--out",folder,"--as-of-date","2026-10-11",
                                    "--fetch-originals"]):
                with patch.object(m24,"get_source",return_value=b"tampered"):
                    with self.assertRaisesRegex(ValueError,"M24_ORIGINAL_WORKBOOK_BYTE_LENGTH_MISMATCH"):
                        m24.main()

    def test_report_sha_follows_exact_claims_not_rerendered_output(self):
        report=m24.report_shell(as_of=TODAY)
        self.assertEqual(report["receipt_sha256"],canon_hash({
            k:v for k,v in report.items() if k!="receipt_sha256"
        }))
        self.assertFalse(report["census_original_workbooks_replayed_this_run"])

    def test_xss_untrusted_caveat_escaped_from_html(self):
        r=m24.report_shell(as_of=TODAY)
        r["caveat"]="<script>alert('bad')</script>"
        html=m24.render_html(r)
        self.assertNotIn("<script>",html)
        self.assertIn("&lt;script&gt;",html)
        self.assertIn("2017",html)
        self.assertIn("2022",html)


if __name__ == "__main__":
    unittest.main()
