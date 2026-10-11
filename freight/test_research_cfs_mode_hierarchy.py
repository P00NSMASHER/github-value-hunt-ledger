"""Mission 16 adversarial CFS 2022 for-hire truck data, flags and hierarchy."""
from __future__ import annotations

from copy import deepcopy
from datetime import date
import json
import unittest

from freight.research_evidence_gate import canon_hash
from freight.research_cfs_mode_hierarchy import (
    BOOK, EXPECTED_BOOK_BLOB_SHA1, _git_blob_sha1,
    _component_pct, _partition, build_forhire, render_html, validate_catalog,
)
from freight.research_industry_comparison import build_comparison

TODAY=date(2026,10,11)


def source():
    return json.loads(BOOK.read_text(encoding="utf-8"))


def changed(table="CF2200A18", naics="4931", bucket="09", key="tonnage_flag",
            value=""):
    b=source()
    row=next(x for x in b["selected_source_rows"] if
             x["table_id"]==table and x["naics2017"]==naics and
             x["stratum_code"]==bucket)
    row[key]=value
    return b


class CfsForhireModeTests(unittest.TestCase):
    def test_frozen_source_git_blob_sha_detects_drift(self):
        self.assertEqual(_git_blob_sha1(BOOK.read_bytes()),EXPECTED_BOOK_BLOB_SHA1)
        self.assertEqual(validate_catalog(source(),as_of=TODAY),[])

    def test_sector_forhire_totals_reconcile_from_two_mirror_tables(self):
        r=build_forhire(as_of=TODAY)
        self.assertEqual(r["scope"],"LAB14_CFS_FORHIRE_MODE_RESEARCH_NOT_LTL_BILLING")
        self.assertEqual(r["qa"]["source_selected_rows"],60)
        self.assertEqual(r["qa"]["source_tables"],2)
        self.assertTrue(r["qa"]["all_twelve_total_cells_agree_between_mirrors"])
        self.assertEqual([x["naics2017"] for x in r["three_sector_forhire_results"]],
                         ["31-33","42","4931"])
        self.assertEqual(r["receipt_sha256"],canon_hash({
            k:v for k,v in r.items() if k!="receipt_sha256"
        }))
        self.assertEqual(r["frozen_source_row_receipt_sha256"],canon_hash(source()))

    def test_actual_forhire_goods_and_weight_shares_not_ltl_spend(self):
        r=build_forhire(as_of=TODAY)
        expected={
          "31-33":(3799845,"53.72",1740594,"35.16","1.8","2.3"),
          "42":(3341533,"41.28",1348938,"32.78","3.2","5.3"),
          "4931":(635089,"47.12",140628,"46.01","7.5","9.8"),
        }
        for row in r["three_sector_forhire_results"]:
            val,vshare,ton,tshare,cvv,cvt=expected[row["naics2017"]]
            self.assertEqual(row["for_hire_goods_value_million_usd"],val)
            self.assertEqual(row["for_hire_goods_value_pct_of_this_sectors_all_mode_goods"],vshare)
            self.assertEqual(row["for_hire_weight_thousand_tons"],ton)
            self.assertEqual(row["for_hire_weight_pct_of_sector_all_mode_weight"],tshare)
            self.assertEqual(row["published_for_hire_value_cv_pct"],cvv)
            self.assertEqual(row["published_for_hire_weight_cv_pct"],cvt)
            self.assertEqual(row["mode_name"],"FOR_HIRE_TRUCK_NOT_LTL_ONLY")
            self.assertIsNone(row["within_sector_forhire_ltl_only_paid_invoice_spend_usd"])
            self.assertFalse(row["buyer_demand_proven"])
            self.assertTrue(row["cv_not_statistical_significance_or_margin_of_error"])

    def test_short_distance_fraction_is_great_circle_not_route_or_ltl(self):
        r=build_forhire(as_of=TODAY)
        exp={"31-33":"40.09","42":"61.71","4931":"58.75"}
        for row in r["three_sector_forhire_results"]:
            self.assertEqual(row["distance_less_than_250mi_for_hire_goods_value_share_pct"],
                             exp[row["naics2017"]])
            self.assertEqual(row["distance_measurement"],"GREAT_CIRCLE_DISTANCE_NOT_ROAD_MILES")
            self.assertFalse(row["joint_distance_and_weight_distribution_known"])

    def test_weight_500_to_9999_lbs_fraction_not_ltl_service(self):
        r=build_forhire(as_of=TODAY)
        exp={"31-33":"30.51","42":"31.48","4931":"33.68"}
        for row in r["three_sector_forhire_results"]:
            self.assertEqual(row["shipment_500_to_9999lbs_for_hire_goods_value_share_pct"],
                             exp[row["naics2017"]])
            self.assertEqual(row["weight_measurement"],
                             "SHIPMENT_SIZE_BANDS_NOT_LTL_CLASSIFICATION")
            self.assertTrue(row["joint_distribution_cannot_be_computed_from_separate_marginals"])

    def test_cfs_4931_includes_484_and_only_captive_warehouses(self):
        r=build_forhire(as_of=TODAY)
        row=next(x for x in r["three_sector_forhire_results"]
                 if x["naics2017"]=="4931")
        self.assertTrue(row["combined_naics_484_and_captive_warehouse_population"])
        self.assertIn("NAICS 484",r["caveat"])
        self.assertIn("public-service warehouses excluded",r["caveat"])
        self.assertIn("not only warehouses",row["label"].lower())
        self.assertIn("4931/484",row["label"])

    def test_unqualified_suppressed_source_cells_are_never_zero_or_imputed(self):
        r=build_forhire(as_of=TODAY)
        w=next(x for x in r["three_sector_forhire_results"] if x["naics2017"]=="4931")
        dp=w["distance_by_weight_partition"]
        v=w["shipment_size_by_goods_value_partition"]
        t=w["shipment_size_by_weight_partition"]
        self.assertEqual(dp["suppressed_or_qualified_buckets"],["09"])
        self.assertIsNone(dp["difference_from_total_due_to_published_rounding"])
        self.assertEqual(v["suppressed_or_qualified_buckets"],["10"])
        self.assertEqual(t["suppressed_or_qualified_buckets"],["10"])
        self.assertFalse(dp["hidden_residual_imputed"])
        self.assertFalse(v["partition_is_statistically_certified"])
        self.assertFalse(v["all_bucket_totals_publishable"])

    def test_complete_partition_sums_allow_only_rounding_variance(self):
        r=build_forhire(as_of=TODAY)
        m=next(x for x in r["three_sector_forhire_results"] if x["naics2017"]=="31-33")
        w=next(x for x in r["three_sector_forhire_results"] if x["naics2017"]=="42")
        self.assertEqual(m["distance_by_goods_value_partition"]["difference_from_total_due_to_published_rounding"],1)
        self.assertEqual(m["shipment_size_by_goods_value_partition"]["difference_from_total_due_to_published_rounding"],-1)
        self.assertEqual(w["distance_by_weight_partition"]["difference_from_total_due_to_published_rounding"],1)
        self.assertEqual(w["shipment_size_by_weight_partition"]["difference_from_total_due_to_published_rounding"],1)

    def test_national_truck_not_sector_ltl_or_annual_market(self):
        r=build_forhire(as_of=TODAY)
        self.assertEqual(r["actual_paid_ltl_invoices_observed"],0)
        self.assertFalse(r["market_size_or_recovery_rates_established"])
        self.assertFalse(r["public_sector_ranking_or_marketing_claims_allowed"])
        self.assertFalse(r["carrier_contact_or_money_actions_authorized"])
        self.assertFalse(r["automatic_external_source_fetch_or_schedule"])
        self.assertFalse(r["source_primary_zip_bytes_replayed_in_this_ci_run"])
        self.assertTrue(r["qa"]["mirror_reference_only"])
        self.assertFalse(r["qa"]["mirror_row_reproduction_against_original_census_dat_completed"])
        self.assertEqual(r["existing_lab_number"],14)
        self.assertFalse(r["new_lab_created"])

    def test_mirror_must_not_be_claimed_identical_to_original_zip(self):
        b=source()
        b["third_party_mirror_is_same_as_verified_original_zip_bytes"]=True
        self.assertIn("unapproved data","; ".join(validate_catalog(b,as_of=TODAY)))
        b=source()
        b["publisher_signatures_validated"]=True
        self.assertTrue(validate_catalog(b,as_of=TODAY))

    def test_hardcoded_source_mirror_ids_sizes_and_versions(self):
        for key,val in (
            ("mirror_git_blob_sha1","f"*40),
            ("mirror_file_bytes",500),
            ("browser_observed_original_zip_sha256","0"*64),
            ("axis","SHIPWT"),
            ("source_official_zip_url","https://example.com/fake.zip"),
            ("exact_original_raw_dat_hash_unverified",False),
        ):
            b=source()
            b["source_tables"][0][key]=val
            self.assertIn("falsified original/mirror source identity",
                          "; ".join(validate_catalog(b,as_of=TODAY)),key)

    def test_source_capture_date_cannot_be_backdated_or_future_dated(self):
        for d in ("2026-10-10","2027-01-01","malformed"):
            b=source()
            b["observed_on"]=d
            self.assertTrue(validate_catalog(b,as_of=TODAY))

    def test_duplicate_rows_and_false_census_buckets_rejected(self):
        for field,val in (
            ("naics2017","493"),
            ("stratum_code","001" ),
            ("table_id","CF2200A16"),
            ("mode_code","00"),
            ("goods_value_million_usd",100_000_000),
        ):
            b=changed("CF2200A19","4931","10",field,val)
            self.assertTrue(validate_catalog(b,as_of=TODAY),field)
        b=source()
        b["selected_source_rows"].append(deepcopy(b["selected_source_rows"][0]))
        self.assertIn("all sixty", "; ".join(validate_catalog(b,as_of=TODAY)))

    def test_suppression_flag_change_fails_and_missing_flag_does_not_look_zero(self):
        for table,bucket,field,val in (
            ("CF2200A18","09","tonnage_flag",""),
            ("CF2200A19","10","goods_value_flag",""),
            ("CF2200A19","10","tonnage_flag",""),
            ("CF2200A19","10","goods_value_cv_flag",""),
        ):
            b=changed(table,"4931",bucket,field,val)
            self.assertTrue(validate_catalog(b,as_of=TODAY),field)

    def test_warehouse_carrier_484_composite_note_required(self):
        for text in ("Warehouse TAM verified!",
                     "4931 represents only warehouses.",
                     ""):
            b=source()
            b["combined_naics_note"]=text
            self.assertIn("mixed 4931/484", "; ".join(validate_catalog(b,as_of=TODAY)))

    def test_cross_table_forhire_total_mismatch_rejected(self):
        b=changed("CF2200A19","31-33","01","goods_value_million_usd",3799844)
        self.assertIn("Census mode 111 total disagrees", "; ".join(
            validate_catalog(b,as_of=TODAY)))

    def test_wrong_cv_flag_or_extreme_cv_rejected(self):
        for key,value in (
            ("goods_value_cv_pct","500"),
            ("goods_value_cv_pct","abc"),
            ("tonnage_cv_flag","not-public"),
        ):
            b=changed("CF2200A18","42","02",key,value)
            self.assertTrue(validate_catalog(b,as_of=TODAY),key)

    def test_suppression_in_selected_component_yields_missing_share(self):
        data=source()
        row=next(x for x in data["selected_source_rows"]
                 if x["table_id"]=="CF2200A18" and x["naics2017"]=="31-33"
                 and x["stratum_code"]=="04")
        row["goods_value_flag"]="S"
        row["goods_value_million_usd"]=0
        row["goods_value_cv_flag"]="S"
        row["goods_value_cv_pct"]="0"
        self.assertTrue(validate_catalog(data,as_of=TODAY))
        self.assertIsNone(_component_pct(
            [x for x in data["selected_source_rows"]
             if x["table_id"]=="CF2200A18" and x["naics2017"]=="31-33"],
            ("02","03","04"),3799845,"value"
        ))

    def test_partition_cannot_infer_suppressed_residual(self):
        testrows=[
            {"stratum_code":"02","goods_value_flag":"","goods_value_million_usd":40,
             "tonnage_flag":"","tonnage_thousand_tons":40},
            {"stratum_code":"03","goods_value_flag":"S","goods_value_million_usd":0,
             "tonnage_flag":"S","tonnage_thousand_tons":0},
        ]
        r=_partition(testrows,60,"value")
        self.assertEqual(r["suppressed_or_qualified_buckets"],["03"])
        self.assertIsNone(r["difference_from_total_due_to_published_rounding"])
        self.assertFalse(r["hidden_residual_imputed"])
        self.assertFalse(r["partition_is_statistically_certified"])

    def test_partition_nonoverlap_conservation_not_guess_workflow(self):
        testrows=[
            {"stratum_code":"02","goods_value_flag":"","goods_value_million_usd":40,
             "tonnage_flag":"","tonnage_thousand_tons":40},
            {"stratum_code":"03","goods_value_flag":"","goods_value_million_usd":80,
             "tonnage_flag":"","tonnage_thousand_tons":80},
        ]
        with self.assertRaisesRegex(ValueError,"SOURCE_PARTITION_ARITHMETIC"):
            _partition(testrows,100,"value")

    def test_rehashed_fake_m15_market_claim_held(self):
        prior=build_comparison(as_of=TODAY)
        prior["ltl_market_tam_usd"]=1_000_000
        prior["receipt_sha256"]=canon_hash({
            k:v for k,v in prior.items() if k!="receipt_sha256"
        })
        with self.assertRaisesRegex(ValueError,"SOURCE_M15_RESEARCH_DENOMINATOR_UNTRUSTED"):
            build_forhire(as_of=TODAY,prior=prior)

    def test_missing_duplicate_or_corrupt_dataset_handled_without_revenue(self):
        b=source()
        b["selected_source_rows"].pop()
        self.assertTrue(validate_catalog(b,as_of=TODAY))
        b=source()
        b["selected_source_rows"]=[None]*60
        self.assertTrue(validate_catalog(b,as_of=TODAY))
        b=source()
        b["source_tables"]=[{}]
        self.assertTrue(validate_catalog(b,as_of=TODAY))

    def test_public_html_escapes_label_and_emphasizes_census_composite(self):
        report=build_forhire(as_of=TODAY)
        report["three_sector_forhire_results"][0]["label"]='<script>alert("bad")</script>'
        html=render_html(report)
        self.assertNotIn("<script>",html)
        self.assertIn("&lt;script&gt;",html)
        self.assertIn("NAICS 484",html)
        self.assertIn("not LTL billing",html)

    def test_valid_report_reproducible_and_still_research_only(self):
        a=build_forhire(as_of=TODAY)
        b=build_forhire(as_of=TODAY)
        self.assertEqual(a,b)
        self.assertTrue(a["census_2022_quality_note_4931_includes_naics_484"])
        self.assertFalse(a["carrier_contact_or_money_actions_authorized"])
        self.assertFalse(a["source_primary_zip_bytes_replayed_in_this_ci_run"])

    def test_quality_bucket_suppression_rates_not_ltl_error_rates(self):
        r=build_forhire(as_of=TODAY)
        self.assertTrue(r["qa"]["no_ltl_market_revenue_or_actual_customer_validation"])
        self.assertTrue(all(x["customer_claims_or_recoveries_count"]==0
                            for x in r["three_sector_forhire_results"]))
        self.assertIn("unknown, not zero",r["caveat"])


if __name__=="__main__":
    unittest.main()
