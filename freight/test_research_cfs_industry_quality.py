"""RETALLY Mission 14: adversarial CFS public NAICS, mode and quality controls."""
from __future__ import annotations

from copy import deepcopy
from datetime import date
from hashlib import sha256
from html import escape
import io
import json
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile, ZIP_DEFLATED

from freight.research_evidence_gate import canon_hash
from freight.research_cfs_industry_quality import (
    BOOK, TABLES, build_readiness, profile_local_zip,
    render_html, validate_manifest,
)

TODAY=date(2026,10,11)


def book():
    return json.loads(BOOK.read_text(encoding="utf-8"))


def fake_archive(table="CF2200A18", *, edit=None):
    axis=TABLES[table]["axis"]
    columns=[
        "NAICS2017","DMODE",axis,"YEAR","VAL","VAL_F","VAL_S","VAL_S_F",
        "TON","TON_F","TON_S","TON_S_F",
    ]
    rows=[
       {"NAICS2017":"31-33","DMODE":"111",axis:"00","YEAR":"2022",
        "VAL":"1000","VAL_F":"","VAL_S":"12.5","VAL_S_F":"",
        "TON":"200","TON_F":"","TON_S":"9","TON_S_F":""},
       {"NAICS2017":"42","DMODE":"111",axis:"00","YEAR":"2022",
        "VAL":"0","VAL_F":"S","VAL_S":"0","VAL_S_F":"S",
        "TON":"300","TON_F":"","TON_S":"13.1","TON_S_F":""},
       {"NAICS2017":"4931","DMODE":"111",axis:"00","YEAR":"2022",
        "VAL":"123","VAL_F":"","VAL_S":"0","VAL_S_F":"N",
        "TON":"0","TON_F":"N","TON_S":"0","TON_S_F":"N"},
       {"NAICS2017":"31-33","DMODE":"11",axis:"00","YEAR":"2022",
        "VAL":"1800","VAL_F":"","VAL_S":"10","VAL_S_F":"",
        "TON":"400","TON_F":"","TON_S":"5","TON_S_F":""},
       {"NAICS2017":"31-33","DMODE":"111",axis:"02","YEAR":"2022",
        "VAL":"650","VAL_F":"","VAL_S":"20","VAL_S_F":"",
        "TON":"140","TON_F":"","TON_S":"11","TON_S_F":""},
    ]
    if edit is not None:
        edit(rows)
    dat="|".join(columns)+"\n"+"\n".join(
        "|".join(str(r.get(k,"")) for k in columns) for r in rows
    )+"\n"
    out=io.BytesIO()
    with ZipFile(out,"w",compression=ZIP_DEFLATED) as z:
        z.writestr(f"{table}.dat",dat.encode("utf-8"))
        z.writestr(f"{table}_FIELDS.txt","FICTITIOUS QA DICTIONARY")
    return out.getvalue()


class CensusIndustryQualityTests(unittest.TestCase):
    def test_two_official_sources_are_distinct_grains_and_research_only(self):
        b=book()
        self.assertEqual(validate_manifest(b,as_of=TODAY),[])
        r=build_readiness(as_of=TODAY)
        self.assertEqual(r["public_archive_leads"],2)
        self.assertEqual([x["table_id"] for x in r["sources"]],
                         ["CF2200A18","CF2200A19"])
        self.assertEqual([x["published_table_row_count"] for x in r["sources"]],
                         [7312,6782])
        self.assertEqual(r["existing_lab_number"],14)
        self.assertFalse(r["new_lab_created"])
        self.assertFalse(r["buyer_demand_verified"])
        self.assertFalse(r["recovery_tam_calculated"])
        self.assertIsNone(r["verified_paid_ltl_spend_usd"])
        self.assertEqual(r["source_rows_from_full_files_replayed_in_ci"],0)
        self.assertFalse(r["public_market_or_recovery_claims_allowed"])
        self.assertEqual(r["receipt_sha256"],canon_hash({
            k:v for k,v in r.items() if k!="receipt_sha256"
        }))

    def test_read_only_observed_source_hashes_and_row_counts_are_pinned(self):
        r=build_readiness(as_of=TODAY)
        self.assertEqual(r["remote_browser_original_rows_observed"],14094)
        self.assertEqual([s["remote_observed_zip_size_bytes"] for s in r["sources"]],
                         [93390,107682])
        self.assertEqual([s["remote_observed_original_dataset_rows"] for s in r["sources"]],
                         [7312,6782])
        self.assertEqual(r["sources"][0]["remote_observed_zip_sha256"],
                         "a18ce071599457572177dd56f8a6174594d1018da9b9024476c4e9832a357bf5")
        self.assertEqual(r["sources"][1]["remote_observed_zip_sha256"],
                         "fe3085d23a3c76704a0d86d9213bb38d3d341b2c228990a5ebf40b6b3f1b661d")
        self.assertTrue(all(s["original_source_downloaded_or_inspected_in_external_browser"]
                            for s in r["sources"]))
        self.assertTrue(all(s["original_source_archive_bytes_replayed_in_ci"] is False
                            for s in r["sources"]))

    def test_exact_browser_observed_cfs_quality_flag_counts(self):
        r=build_readiness(as_of=TODAY)
        flags=r["remote_browser_flag_counts"]
        self.assertEqual(flags["CF2200A18"]["value"],{"blank":5430,"S":1839,"Z":43})
        self.assertEqual(flags["CF2200A18"]["weight"],{"blank":4991,"S":2224,"Z":97})
        self.assertEqual(flags["CF2200A19"]["value"],{"blank":4628,"S":2063,"Z":91})
        self.assertEqual(flags["CF2200A19"]["weight"],{"blank":4474,"S":1956,"Z":352})
        for table,n in (("CF2200A18",7312),("CF2200A19",6782)):
            self.assertEqual(sum(flags[table]["value"].values()),n)
            self.assertEqual(sum(flags[table]["weight"].values()),n)

    def test_five_direct_national_source_rows_not_hierarchical_sum(self):
        r=build_readiness(as_of=TODAY)
        rows={(x["naics"],x["mode"]):x for x in r["verified_source_industry_direct_totals"]}
        self.assertEqual(len(rows),5)
        self.assertEqual(rows[("00","00")]["value_million_usd"],17996782)
        self.assertEqual(rows[("00","111")]["value_million_usd"],8062541)
        self.assertEqual(rows[("31-33","00")]["value_million_usd"],7073495)
        self.assertEqual(rows[("42","00")]["weight_thousand_tons"],4115279)
        self.assertEqual(rows[("4931","00")]["value_million_usd"],1347716)
        self.assertTrue(all(x["cross_archive_direct_totals_match"] is True for x in rows.values()))
        self.assertFalse(r["recovery_tam_calculated"])

    def test_rounded_zero_flag_is_not_an_exact_zero(self):
        def flag(rows):
            rows[0]["VAL"]="0"
            rows[0]["VAL_F"]="Z"
        out=profile_local_zip(raw=fake_archive(edit=flag),table_id="CF2200A18",
                              as_of=TODAY,synthetic_test=True)
        self.assertEqual(out["sample_value_quality_counts"]["value:CENSUS_ROUNDED_TO_ZERO_NOT_LITERAL_ZERO"],1)
        self.assertIsNone(out["industry_examples"]["31-33"][0]["goods_value_million_usd"])

    def test_local_original_source_flag_counts_cannot_be_silently_forged(self):
        for key,bad in (
            ("original_zip_sha256","b"*64),
            ("value_flag_counts",{"blank":7312,"S":0,"Z":0}),
            ("unique_naics_codes_observed",51),
            ("remote_observed_header","badheader"),
            ("remote_observed_parsed_data_rows",100),
        ):
            b=book()
            b["official_archives"][0][key]=bad
            self.assertIn("pinned source byte hash", "; ".join(validate_manifest(b,as_of=TODAY)),key)

    def test_source_vintage_and_index_row_count_cannot_be_swapped(self):
        for key,val in (
            ("dataset_grain","NAICS2017_X_DMODE_X_SHIPWT_US_2022"),
            ("published_table_row_count",6782),
            ("url","https://attack.example/naics.zip"),
            ("table_member","CF2200A01.dat"),
        ):
            b=book()
            b["official_archives"][0][key]=val
            self.assertIn("official provenance/grain/count drift","; ".join(
                validate_manifest(b,as_of=TODAY)),key)

    def test_fake_download_hash_without_inspection_is_rejected(self):
        for key,value in (
            ("original_zip_size_bytes",105000),
            ("original_zip_sha256","b"*64),
            ("original_archive_observed_by_read_only_browser",False),
            ("original_member_structure_inspected",False),
        ):
            b=book();b["official_archives"][0][key]=value
            self.assertTrue(validate_manifest(b,as_of=TODAY),key)

    def test_no_claims_of_invoice_spend_buyer_demand_or_recovery_tam(self):
        for key in (
            "original_source_binary_stored_in_repo","raw_data_ingested_in_ci",
            "any_customer_or_carrier_records","actual_ltl_invoice_spend_measured",
            "invoice_error_prevalence_established",
            "buyer_opportunity_ranking_authorized",
            "freight_audit_market_revenue_established",
            "external_contact_or_financial_actions_allowed",
            "publisher_signature_verified",
        ):
            b=book();b[key]=True
            self.assertIn(key,"; ".join(validate_manifest(b,as_of=TODAY)))

    def test_manufacturing_wholesale_warehousing_are_not_tam_rankings(self):
        r=build_readiness(as_of=TODAY)
        s=r["candidate_segments"]
        self.assertEqual([x["id"] for x in s],
                         ["manufacturing","wholesale","warehousing"])
        self.assertEqual([x["candidate_naics2017"] for x in s],
                         [["31-33"],["42"],["4931"]])
        self.assertTrue(all(x["buying_propensity_known"] is False and
                            x["verified_paid_ltl_invoice_count"] == 0
                            for x in s))

    def test_unauthorized_segment_rank_naics_or_customer_result_rejected(self):
        for key,value in (
            ("candidate_naics_groups",["311"]),
            ("rank",0),
            ("demand_verified",True),
            ("customer_invoice_count_verified",120),
            ("lfv_market_opportunity_usd",400000),
        ):
            b=book();b["research_segments"][0][key]=value
            self.assertTrue(validate_manifest(b,as_of=TODAY),key)

    def test_synthetic_a18_source_gives_quality_coverage_not_study_findings(self):
        r=profile_local_zip(raw=fake_archive("CF2200A18"),
                            table_id="CF2200A18",as_of=TODAY,synthetic_test=True)
        self.assertEqual(r["scope"],"SYNTHETIC_QA_ONLY")
        self.assertEqual(r["source_rows_examined"],5)
        self.assertEqual(r["source_member"],"CF2200A18.dat")
        self.assertFalse(r["original_source_hash_matched"])
        self.assertFalse(r["source_index_count_matches_exactly"])
        self.assertEqual(r["total_distinct_naics_codes"],3)
        self.assertEqual(r["total_distinct_mode_codes"],2)
        self.assertEqual(r["total_distinct_strata"],2)
        self.assertFalse(r["invoice_billing_revenue_verified"])
        self.assertFalse(r["totaling_nested_industry_or_transport_modes_authorized"])
        self.assertFalse(r["statistical_precision_cleared_from_cvs"])
        self.assertEqual(r["receipt_sha256"],canon_hash({
            k:v for k,v in r.items() if k!="receipt_sha256"
        }))

    def test_synthetic_a19_has_distinct_weight_axis(self):
        r=profile_local_zip(raw=fake_archive("CF2200A19"),
                            table_id="CF2200A19",as_of=TODAY,synthetic_test=True)
        self.assertEqual(r["table_id"],"CF2200A19")
        self.assertEqual(r["source_member"],"CF2200A19.dat")
        self.assertEqual(r["source_rows_examined"],5)

    def test_suppressed_value_is_null_not_zero(self):
        r=profile_local_zip(raw=fake_archive(),table_id="CF2200A18",
                            as_of=TODAY,synthetic_test=True)
        self.assertEqual(r["sample_value_quality_counts"]["value:CENSUS_FLAGGED_ESTIMATE"],1)
        items=r["industry_examples"]["42"]
        self.assertIsNone(items[0]["goods_value_million_usd"])
        self.assertEqual(items[0]["goods_value_flag"],"S")
        self.assertIsNone(items[0]["goods_value_cv"])
        self.assertEqual(items[0]["shipment_weight_thousand_tons"],300)

    def test_unavailable_weight_not_reported_as_observed_zero(self):
        r=profile_local_zip(raw=fake_archive(),table_id="CF2200A18",
                            as_of=TODAY,synthetic_test=True)
        row=r["industry_examples"]["4931"][0]
        self.assertIsNone(row["shipment_weight_thousand_tons"])
        self.assertEqual(row["shipment_weight_flag"],"N")

    def test_missing_cv_with_N_flag_does_not_create_certified_precision(self):
        r=profile_local_zip(raw=fake_archive(),table_id="CF2200A18",
                            as_of=TODAY,synthetic_test=True)
        row=r["industry_examples"]["4931"][0]
        self.assertEqual(row["goods_value_million_usd"],123)
        self.assertIsNone(row["goods_value_cv"])
        self.assertTrue(r["sample_value_quality_counts"]["value:CV_NOT_ESTABLISHED"]>=1)
        self.assertFalse(r["statistical_precision_cleared_from_cvs"])

    def test_naics_mode_stratum_duplicates_fail_closed(self):
        def dup(rows):rows.append(deepcopy(rows[0]))
        with self.assertRaisesRegex(ValueError,"CFS_DUPLICATE_CROSSTAB_CLAIM"):
            profile_local_zip(raw=fake_archive(edit=dup),table_id="CF2200A18",
                              as_of=TODAY,synthetic_test=True)

    def test_wrong_or_missing_axis_must_fail_not_treat_another_as_distance(self):
        with self.assertRaisesRegex(ValueError,"EXPECTED_OFFICIAL_DAT_MEMBER_MISSING"):
            profile_local_zip(raw=fake_archive("CF2200A19"),table_id="CF2200A18",
                              as_of=TODAY,synthetic_test=True)

    def test_wrong_survey_year_fails_closed(self):
        def rewrite(rows):rows[0]["YEAR"]="2017"
        with self.assertRaisesRegex(ValueError,"CFS_INDUSTRY_WRONG_YEAR"):
            profile_local_zip(raw=fake_archive(edit=rewrite),table_id="CF2200A18",
                              as_of=TODAY,synthetic_test=True)

    def test_unflagged_non_numeric_value_is_not_a_verified_zero(self):
        def rewrite(rows):rows[0]["VAL"]="S"
        r=profile_local_zip(raw=fake_archive(edit=rewrite),table_id="CF2200A18",
                            as_of=TODAY,synthetic_test=True)
        self.assertEqual(r["sample_value_quality_counts"]["value:MISSING_OR_NONNUMERIC_SOURCE_ESTIMATE"],1)
        self.assertIsNone(r["industry_examples"]["31-33"][0]["goods_value_million_usd"])

    def test_unknown_quality_flag_must_fail(self):
        def bad(rows):rows[0]["VAL_F"]="APPROVED"
        with self.assertRaisesRegex(ValueError,"UNKNOWN_CENSUS_ESTIMATE_FLAG"):
            profile_local_zip(raw=fake_archive(edit=bad),table_id="CF2200A18",
                              as_of=TODAY,synthetic_test=True)

    def test_fake_six_good_rows_cannot_claim_official_census_archive(self):
        with self.assertRaisesRegex(ValueError,"ORIGINAL_CFS_INDUSTRY_ARCHIVE_SHA256_MISMATCH"):
            profile_local_zip(raw=fake_archive(),table_id="CF2200A18",
                              as_of=TODAY,synthetic_test=False)

    def test_wrong_table_id_cannot_be_requested(self):
        with self.assertRaisesRegex(ValueError,"UNKNOWN_CENSUS_INDUSTRY_TABLE"):
            profile_local_zip(raw=fake_archive(),table_id="CF2200A01",
                              as_of=TODAY,synthetic_test=True)

    def test_missing_industry_or_mode_not_a_research_eligible_row(self):
        for key in ("NAICS2017","DMODE","SHIPDIST"):
            def erase(rows):rows[0][key]=""
            with self.assertRaisesRegex(ValueError,"MISSING_INDUSTRY_MODE_OR_STRATUM"):
                profile_local_zip(raw=fake_archive(edit=erase),table_id="CF2200A18",
                                  as_of=TODAY,synthetic_test=True)

    def test_original_public_rows_never_converted_to_annual_freight_revenue(self):
        r=build_readiness(as_of=TODAY)
        self.assertNotIn("total_ltl_invoices",r)
        self.assertNotIn("annual_recurring_revenue",r)
        self.assertEqual(r["market_share_claims_approved"],0)
        self.assertFalse(r["buyer_demand_verified"])
        self.assertFalse(r["recovery_tam_calculated"])

    def test_missing_actual_original_download_or_customer_data_is_visible(self):
        r=build_readiness(as_of=TODAY)
        self.assertEqual(r["source_rows_from_full_files_replayed_in_ci"],0)
        self.assertEqual(r["real_customer_invoices"],0)
        self.assertEqual(r["source_quality_flags_dismissed"],0)
        self.assertFalse(r["network_or_scheduler_enabled"])

    def test_bounded_source_inventory_and_date(self):
        b=book()
        b["observed_on"]="2027-12-01"
        self.assertIn("date is invalid or from the future","; ".join(
            validate_manifest(b,as_of=TODAY)))
        b=book()
        b["official_archives"].append(deepcopy(b["official_archives"][0]))
        self.assertIn("exactly two","; ".join(validate_manifest(b,as_of=TODAY)))

    def test_hypothesis_extra_customer_identifier_rejected(self):
        b=book()
        b["research_segments"][0]["buyer_email"]="not allowed"
        self.assertIn("malformed buyer industry hypothesis","; ".join(
            validate_manifest(b,as_of=TODAY)))

    def test_html_escapes_untrusted_segment_claims(self):
        r=build_readiness(as_of=TODAY)
        r["candidate_segments"][0]["hypothesis"]='<script>alert("x")</script>'
        html=render_html(r)
        self.assertIn("&lt;script&gt;",html)
        self.assertNotIn("<script>",html)
        self.assertIn("Industry exposure is not invoice opportunity",html)

    def test_industry_record_edit_does_not_become_new_source_truth(self):
        b=book()
        b["actual_industry_source_records"][0]["value_million_usd"]=50_000_000
        self.assertIn("published direct industry source values","; ".join(
            validate_manifest(b,as_of=TODAY)))

    def test_quality_control_expires_after_90_days_without_fake_refresh(self):
        r=build_readiness(as_of=date(2027,2,1))
        self.assertTrue(r["source_recheck_due_after_90_days"])
        self.assertGreaterEqual(r["source_review_age_days"],90)
        self.assertEqual(r["source_rows_from_full_files_replayed_in_ci"],0)

    def test_later_replay_does_not_invent_new_source_verification(self):
        r=build_readiness(as_of=date(2027,1,20))
        self.assertEqual(r["source_rows_from_full_files_replayed_in_ci"],0)
        self.assertFalse(r["public_market_or_recovery_claims_allowed"])


if __name__=="__main__":
    unittest.main()
