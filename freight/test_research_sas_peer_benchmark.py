"""Mission 23: adversarial Census SAS trucking peer benchmark tests.

Synthetic parsed cells in this file are not real publisher evidence; exact
Census XLSX byte verification is a separate read-only CI job.
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
from freight import research_sas_peer_benchmark as m23

TODAY=date(2026,10,11)


def catalog():
    return json.loads(m23.BOOK.read_text(encoding="utf-8"))


def mock_peer_rows(ident=m23.REVISED):
    data=[]
    for code in m23.NAICS:
        label, nums, revenue, cv = m23.EXPECTED[ident][code]
        for i,number in enumerate(nums):
            data.append((number, {
                "A":code, "B":label,
                "C":"Revenue",
                "D":"All Establishments" if i==0 else
                    "Establishments subject to federal income tax",
                "E":"Employer Firms",
                "F":format(revenue,","),
                "P":cv,
            }))
    return data


class SasPeerBenchmarkTests(unittest.TestCase):
    def test_frozen_manifest_sha1_and_source_book_no_customer_fields(self):
        self.assertEqual(m23._blob(m23.BOOK.read_bytes()),
                         m23.EXPECTED_BOOK_BLOB_SHA1)
        self.assertEqual(m23.validate_manifest(catalog(),as_of=TODAY),[])
        self.assertEqual(len(catalog()["publisher_workbooks"]),2)
        self.assertEqual(catalog()["approved_real_customer_studies"],0)
        self.assertFalse(catalog()["consumer_invoice_data_ingested"])

    def test_three_peer_source_revisions_and_nominal_units(self):
        r=m23.report_shell(as_of=TODAY)
        bycode={p["naics"]:p for p in r["naics_peer_revisions"]}
        for code,old,new,diff,pct in (
            ("484",445509,423271,-22238,"-4.99"),
            ("484121",183482,172717,-10765,"-5.87"),
            ("484122",68411,65688,-2723,"-3.98"),
        ):
            self.assertEqual(bycode[code]["old_sas_revenue_million_usd"],old)
            self.assertEqual(bycode[code]["revised_sas_revenue_million_usd"],new)
            self.assertEqual(bycode[code]["signed_revision_million_usd"],diff)
            self.assertEqual(bycode[code]["signed_revision_pct_of_old"],pct)

    def test_peer_revisions_not_ltl_specific(self):
        r=m23.report_shell(as_of=TODAY)
        self.assertTrue(r["all_three_industries_downward_revised"])
        self.assertFalse(r["ltl_revised_down_more_than_parent_or_tl_in_percentage_terms"])
        self.assertEqual(r["ltl_original_parent_share_pct"],"15.36")
        self.assertEqual(r["ltl_revised_parent_share_pct"],"15.52")
        self.assertEqual(r["ltl_absolute_revision_share_of_parent_revision_pct"],"12.24")

    def test_parent_subindustry_overlap_and_residual_decomposition(self):
        r=m23.report_shell(as_of=TODAY)
        self.assertEqual(r["other_trucking_residual_old_million_usd"],193616)
        self.assertEqual(r["other_trucking_residual_revised_million_usd"],184866)
        self.assertEqual(r["other_trucking_residual_revision_million_usd"],-8750)
        self.assertFalse(r["other_trucking_residual_is_a_separate_surveyed_naics"])
        p={v["naics"]:v for v in r["naics_peer_revisions"]}
        self.assertEqual(
            p["484"]["signed_revision_million_usd"],
            p["484121"]["signed_revision_million_usd"]+
            p["484122"]["signed_revision_million_usd"]+
            r["other_trucking_residual_revision_million_usd"]
        )

    def test_all_aies_2022_source_rows_match_rounded_revised_sas(self):
        r=m23.report_shell(as_of=TODAY)
        p={row["naics"]:row for row in r["naics_peer_revisions"]}
        self.assertEqual(p["484"]["aies_2022_historical_revenue_million_usd"],"423270.958")
        self.assertEqual(p["484121"]["aies_2022_historical_revenue_million_usd"],"172717.339")
        self.assertEqual(p["484122"]["aies_2022_historical_revenue_million_usd"],"65688.461")
        self.assertEqual(p["484"]["aies_minus_revised_sas_million_usd"],"-0.042")
        self.assertEqual(p["484121"]["aies_minus_revised_sas_million_usd"],"0.339")
        self.assertEqual(p["484122"]["aies_minus_revised_sas_million_usd"],"0.461")
        self.assertTrue(all(row["aies_agrees_at_sas_nearest_million_precision"] for row in r["naics_peer_revisions"]))

    def test_offline_dashboard_never_claims_original_zip_replay(self):
        r=m23.report_shell(as_of=TODAY)
        self.assertEqual(r["source_status"],m23.OFFLINE)
        self.assertFalse(r["original_workbooks_replayed_this_run"])
        self.assertEqual(r["original_workbook_evidence"],[])
        self.assertEqual(r["naics_industries_compared"],3)
        self.assertEqual(r["receipt_sha256"],canon_hash({
            k:v for k,v in r.items() if k!="receipt_sha256"
        }))

    def test_14_labs_18_pilot_gates_and_zero_customer_evidence_held(self):
        r=m23.report_shell(as_of=TODAY)
        self.assertEqual(r["lab"],14)
        self.assertFalse(r["new_lab_created"])
        self.assertEqual(r["actual_independently_adjudicated_freight_invoices"],0)
        self.assertIsNone(r["ltl_invoice_error_rate_pct"])
        self.assertIsNone(r["customer_paid_ltl_invoice_volume_usd"])
        self.assertIsNone(r["freight_recovery_tam_usd"])
        self.assertIsNone(r["verified_retally_customer_recoveries_usd"])
        self.assertFalse(r["actual_buyer_demand_verified"])
        self.assertFalse(r["marketing_or_prospect_contact_authorized"])
        self.assertFalse(r["customer_or_carrier_data_processed"])
        self.assertEqual(r["pilots_approved"],0)
        self.assertTrue(r["pilot_18_external_requirements_unmet"])
        self.assertFalse(r["automated_background_refresh_or_schedule_created"])

    def test_source_rows_have_both_tax_statuses_for_all_three_naics(self):
        for ident in m23.IDS:
            proof=m23.selected_peers_from_rows(mock_peer_rows(ident),ident=ident)
            self.assertEqual(len(proof),6)
            self.assertEqual(sorted({p["naics"] for p in proof}),list(m23.NAICS))
            self.assertTrue(all(not p["customer_invoice_sample"] for p in proof))
            self.assertEqual(len([p for p in proof if p["tax_status"]=="All Establishments"]),3)

    def test_source_missing_one_peer_rejected(self):
        for ident in m23.IDS:
            rows=[row for row in mock_peer_rows(ident) if row[1]["A"]!="484121"]
            with self.assertRaisesRegex(ValueError,"M23_MISSING_REQUIRED_SAS_PEER_SOURCE_ROWS"):
                m23.selected_peers_from_rows(rows,ident=ident)

    def test_source_missing_one_tax_status_rejected(self):
        for ident in m23.IDS:
            rows=mock_peer_rows(ident)
            rows=rows[:-1]
            with self.assertRaisesRegex(ValueError,"M23_MISSING_REQUIRED_SAS_PEER_SOURCE_ROWS"):
                m23.selected_peers_from_rows(rows,ident=ident)

    def test_source_duplicate_row_rejected(self):
        for ident in m23.IDS:
            rows=mock_peer_rows(ident)
            rows.append(deepcopy(rows[0]))
            with self.assertRaisesRegex(ValueError,"M23_DUPLICATE_SAS_SOURCE_RECORD"):
                m23.selected_peers_from_rows(rows,ident=ident)

    def test_source_wrong_naics_address_not_accepted(self):
        for ident in m23.IDS:
            rows=mock_peer_rows(ident)
            number,data=rows[0]
            rows[0]=(number+1,data)
            with self.assertRaisesRegex(ValueError,"M23_UNEXPECTED_NAICS_SOURCE_ROW|M23_DUPLICATE_SAS_SOURCE_RECORD"):
                m23.selected_peers_from_rows(rows,ident=ident)

    def test_sas_census_population_or_label_spoof_rejected(self):
        for ident in m23.IDS:
            for field,value in (("B","Warehouse only"),
                                ("D","No tax status"),("E","All individuals")):
                rows=mock_peer_rows(ident)
                rows[0][1][field]=value
                with self.assertRaises(ValueError,msg=field+ident):
                    m23.selected_peers_from_rows(rows,ident=ident)

    def test_values_must_remain_millions_not_thousands_or_recoveries(self):
        for value in ("0","-1","1.5","423271000","S",".","$423,271","",None):
            rows=mock_peer_rows(m23.REVISED)
            rows[0][1]["F"]=value
            with self.assertRaises(ValueError,msg=str(value)):
                m23.selected_peers_from_rows(rows,ident=m23.REVISED)

    def test_original_2022_cv_field_cannot_be_zeroed_retroactively(self):
        for ident in m23.IDS:
            rows=mock_peer_rows(ident)
            rows[0][1]["P"]=".9" if ident==m23.REVISED else "0"
            with self.assertRaisesRegex(ValueError,"M23_SAS_PUBLISHED_CV_CHANGED"):
                m23.selected_peers_from_rows(rows,ident=ident)

    def test_source_book_cannot_remove_or_substitute_industry(self):
        book=catalog()
        book["publisher_workbooks"][0]["records"].pop(0)
        self.assertTrue(m23.validate_manifest(book,as_of=TODAY))
        book=catalog()
        book["publisher_workbooks"][0]["records"][0]["naics"]="4931"
        self.assertTrue(m23.validate_manifest(book,as_of=TODAY))

    def test_source_book_cannot_change_value_or_row_address(self):
        for ident in m23.IDS:
            for field,value in (
                ("revenue_million_usd",999999),("raw_2022_cv","0.01"),
                ("row_numbers",[2,3]),("label","Other trucking"),
            ):
                book=catalog()
                source=next(s for s in book["publisher_workbooks"] if s["id"]==ident)
                source["records"][0][field]=value
                self.assertTrue(m23.validate_manifest(book,as_of=TODAY),ident+field)

    def test_source_book_cannot_change_original_publisher_identity(self):
        for field,value in (
            ("archive_sha256","a"*64),("archive_bytes",45),
            ("source_url","https://attacker.example/pretend.xlsx"),
            ("tab","xl/worksheets/sheet20.xml"),("sheet_row_count",100),
        ):
            book=catalog()
            book["publisher_workbooks"][1][field]=value
            self.assertTrue(m23.validate_manifest(book,as_of=TODAY),field)

    def test_unsupported_market_or_source_assertions_fail_closed(self):
        for field in m23.FALSE_GUARDS:
            book=catalog()
            book[field]=True
            self.assertIn("M23_FORGED_SOURCE_OR_CUSTOMER_RECOVERY_EVIDENCE",
                          ";".join(m23.validate_manifest(book,as_of=TODAY)),field)
        book=catalog()
        book["approved_real_customer_studies"]=2
        self.assertTrue(m23.validate_manifest(book,as_of=TODAY))
        book=catalog()
        book["pilot_18_requirements_remain_unverified"]=False
        self.assertTrue(m23.validate_manifest(book,as_of=TODAY))

    def test_source_date_before_evidence_cutoff_rejected(self):
        self.assertTrue(m23.validate_manifest(catalog(),as_of=date(2026,10,10)))
        with self.assertRaisesRegex(ValueError,"M23_INVALID_FROZEN_SOURCE_BOOK"):
            m23.report_shell(as_of=date(2026,10,10))

    def test_source_cv_zero_not_statistical_perfection(self):
        r=m23.report_shell(as_of=TODAY)
        self.assertFalse(r["survey_2022_cv_zero_means_no_uncertainty"])
        self.assertTrue(r["census_same_survey_vintages_are_independent_market_estimates"] is False)
        self.assertTrue(all(p["revised_raw_cv"]=="0" for p in r["naics_peer_revisions"]))
        self.assertEqual([p["prior_raw_cv"] for p in r["naics_peer_revisions"]],["1.3","2.7","1.6"])

    def test_unrecognized_archive_key_or_partial_pair_rejected(self):
        with self.assertRaisesRegex(ValueError,"M23_UNAPPROVED_CENSUS_ORIGINAL_SOURCE"):
            m23.inspect_source(b"x",ident="arbitrary_private_url")
        with self.assertRaisesRegex(ValueError,"M23_BOTH_CENSUS_ORIGINAL_SAS_VINTAGES_REQUIRED"):
            m23.verify_sources(as_of=TODAY,downloaded={m23.REVISED:b"fake"})

    def test_modified_original_source_bytes_fail_before_parsing(self):
        for ident in m23.IDS:
            with self.assertRaisesRegex(ValueError,"M23_ORIGINAL_SAS_XLSX_SIZE_MISMATCH"):
                m23.inspect_source(b"attacker data",ident=ident)
            with self.assertRaisesRegex(ValueError,"M23_ORIGINAL_SAS_XLSX_SHA256_MISMATCH"):
                m23.inspect_source(b"x"*m23.M22_SOURCES[ident]["bytes"],ident=ident)

    def test_source_reader_does_not_accept_noninteger_or_comma_misformatting(self):
        for value in ("one","42.5","123,45","1,234,56","1,2,3","",None):
            with self.assertRaisesRegex(ValueError,"M23_SAS_REVENUE_NON_INTEGER_OR_WRONG_UNITS"):
                m23._source_million(value)
        self.assertEqual(m23._source_million("445,509"),445509)

    def test_network_timeout_returns_blocked_not_fraudulent_source_success(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch("sys.argv",["module","--out",folder,
                                   "--as-of-date","2026-10-11",
                                   "--fetch-publisher-workbooks"]):
                with patch.object(m23,"get_source",side_effect=TimeoutError("synthetic outage")):
                    m23.main()
            r=json.loads((Path(folder)/"sas_peer_benchmark.json").read_text())
            self.assertEqual(r["source_status"],m23.BLOCKED)
            self.assertFalse(r["original_workbooks_replayed_this_run"])
            self.assertEqual(r["original_workbook_evidence"],[])
            self.assertEqual(r["receipt_sha256"],canon_hash({
                k:v for k,v in r.items() if k!="receipt_sha256"
            }))

    def test_corrupt_retrieved_archive_is_failure_not_blocked(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch("sys.argv",["module","--out",folder,
                                   "--as-of-date","2026-10-11",
                                   "--fetch-publisher-workbooks"]):
                with patch.object(m23,"get_source",return_value=b"invalid"):
                    with self.assertRaisesRegex(ValueError,"M23_ORIGINAL_SAS_XLSX_SIZE_MISMATCH"):
                        m23.main()

    def test_render_html_escapes_untrusted_source_caveat(self):
        r=m23.report_shell(as_of=TODAY)
        r["caveat"]="<svg onload=evil()>"
        html=m23.render_html(r)
        self.assertNotIn("<svg onload=",html)
        self.assertIn("&lt;svg onload=",html)
        self.assertIn("NAICS",html)


if __name__=="__main__":
    unittest.main()
