"""Mission 15 adversarial QA: source-backed CFS comparisons, not LTL TAM."""
from __future__ import annotations

from copy import deepcopy
from datetime import date
import json
import unittest

from freight.research_evidence_gate import canon_hash
from freight.research_market_audit import build_market_audit
from freight.research_cfs_industry_quality import BOOK as ORIGINAL_INDUSTRY_BOOK
from freight.research_industry_comparison import (
    PLAN, _percent, _dollars_per_ton,
    build_comparison, render_html, validate_plan,
)

DAY=date(2026,10,11)


def fixture():
    return (json.loads(PLAN.read_text(encoding="utf-8")),
            json.loads(ORIGINAL_INDUSTRY_BOOK.read_text(encoding="utf-8")))


class CfsIndustryComparisonTests(unittest.TestCase):
    def test_reported_4931_combines_484_transportation_not_pure_warehouse(self):
        r=build_comparison(as_of=DAY)
        row=next(x for x in r["industry_comparisons"] if x["naics2017"]=="4931")
        self.assertTrue(row["source_4931_484_tabulation_group_not_pure_warehouse"])
        self.assertIn("4931/484",row["label"])
        self.assertIn("captive warehouse",r["source_4931_484_tabulation_note"])
        self.assertIn("excludes warehouses serving the public",
                      r["source_4931_484_tabulation_note"])

    def test_three_exact_national_all_mode_source_comparisons(self):
        p,s=fixture()
        self.assertEqual(validate_plan(p,s,as_of=DAY),[])
        r=build_comparison(as_of=DAY,plan=p,source_book=s)
        self.assertEqual(r["n_industries"],3)
        self.assertEqual(r["scope"],"LAB14_DIRECT_CFS_INDUSTRY_COMPARISON_RESEARCH_ONLY")
        self.assertEqual([x["naics2017"] for x in r["industry_comparisons"]],
                         ["31-33","42","4931"])
        self.assertEqual(r["national_shipment_value_million_usd_goods"],17996782)
        self.assertEqual(r["national_forhire_truck_goods_value_million_usd_not_ltl_spend"],8062541)
        self.assertEqual(r["national_forhire_truck_goods_value_share_of_us_pct"],"44.80")
        self.assertEqual(r["receipt_sha256"],canon_hash({
            k:v for k,v in r.items() if k!="receipt_sha256"
        }))

    def test_exact_values_and_industry_shares_are_consistently_denominated(self):
        r=build_comparison(as_of=DAY)
        pairs=[
            ("manufacturing",7073495,4949955,"39.30","40.67","1429.00"),
            ("wholesale",8094350,4115279,"44.98","33.82","1966.90"),
            ("warehousing",1347716,305651,"7.49","2.51","4409.33"),
        ]
        for row, expected in zip(r["industry_comparisons"],pairs):
            i,v,t,sv,st,density=expected
            self.assertEqual(row["id"],i)
            self.assertEqual(row["value_million_usd_goods_shipped"],v)
            self.assertEqual(row["weight_thousand_tons_goods_shipped"],t)
            self.assertEqual(row["source_value_share_of_survey_covered_us_pct"],sv)
            self.assertEqual(row["source_weight_share_of_survey_covered_us_pct"],st)
            self.assertEqual(
                row["shipped_goods_value_density_usd_per_ton_not_carrier_rate"],density
            )
            self.assertEqual(row["source_mode_code"],"00")
            self.assertEqual(row["source_location"],"A18 SHIPDIST 001 / A19 SHIPWT 01")

    def test_no_imputed_forhire_fraction_or_synthetic_ltl_revenue(self):
        r=build_comparison(as_of=DAY)
        for row in r["industry_comparisons"]:
            for k in (
                "for_hire_truck_value_in_this_industry_million_usd",
                "within_industry_for_hire_shipment_value_share_pct",
                "distance_under_250mi_forhire_share_pct",
                "shipment_weight_500_to_9999lbs_forhire_share_pct",
                "actual_paid_ltl_invoice_count", "actual_ltl_invoice_spend_usd",
                "independently_verified_invoice_overcharges",
            ):
                self.assertIsNone(row[k],k)
            self.assertFalse(row["buyer_demand_verified"])
            self.assertFalse(row["consumer_revenue_or_market_rank_authorized"])
            self.assertFalse(row["source_industry_specific_cv_review_complete"])
        self.assertIsNone(r["ltl_market_tam_usd"])
        self.assertIsNone(r["paid_ltl_spend_by_industry_usd"])
        self.assertEqual(r["actual_invoice_bills_counted"],0)
        self.assertIsNone(r["actual_recovered_cash_usd"])
        self.assertEqual(r["market_or_customer_rankings_created"],0)

    def test_global_a18_quality_rate_numbers_not_industry_specific(self):
        r=build_comparison(as_of=DAY)
        a=r["global_table_quality_flags"][0]["metrics"]
        self.assertEqual(a["goods_value"]["n_table_rows"],7312)
        self.assertEqual(a["goods_value"]["flag_S_rows"],1839)
        self.assertEqual(a["goods_value"]["flag_Z_rows"],43)
        self.assertEqual(a["goods_value"]["flag_S_pct_of_table_rows"],"25.15")
        self.assertEqual(a["goods_value"]["flagged_S_or_Z_pct_of_table_rows"],"25.74")
        self.assertEqual(a["weight"]["flag_S_rows"],2224)
        self.assertEqual(a["weight"]["flagged_S_or_Z_pct_of_table_rows"],"31.74")

    def test_global_a19_quality_rate_numbers_not_industry_specific(self):
        r=build_comparison(as_of=DAY)
        a=r["global_table_quality_flags"][1]["metrics"]
        self.assertEqual(a["goods_value"]["n_table_rows"],6782)
        self.assertEqual(a["goods_value"]["flag_Z_rows"],91)
        self.assertEqual(a["goods_value"]["flagged_S_or_Z_pct_of_table_rows"],"31.76")
        self.assertEqual(a["weight"]["flag_S_rows"],1956)
        self.assertEqual(a["weight"]["flag_Z_rows"],352)
        self.assertEqual(a["weight"]["flagged_S_or_Z_pct_of_table_rows"],"34.03")
        self.assertTrue(a["weight"]["industry_specific_flag_incidence_unmeasured"])

    def test_one_survey_family_is_not_three_independent_markets(self):
        r=build_comparison(as_of=DAY)
        self.assertTrue(r["same_survey_not_independent_sources"])
        self.assertEqual(r["quantitative_data_basis"],"FIVE_DIRECT_NATIONAL_A18_A19_CFS2022_TOTALS")
        self.assertIn("not freight rate",r["limits"])
        self.assertIn("not freight-billing error rates among manufacturers",r["quality_statistical_caveat"])
        self.assertFalse(r["no_public_buyer_claims_authorized"] is False)

    def test_all_four_real_data_gates_remain_unapproved(self):
        r=build_comparison(as_of=DAY)
        self.assertEqual(len(r["research_gates"]),4)
        self.assertEqual(
            [g["id"] for g in r["research_gates"]],
            ["source_consistency","mode_segmentation","distance_weight","customer_reality"]
        )
        self.assertTrue(all(g["evidence_independently_observed"] is False
                            and g["external_action_authorized"] is False
                            for g in r["research_gates"]))
        self.assertEqual(r["real_buyer_records"],0)
        self.assertFalse(r["automated_source_fetch_or_schedule"])
        self.assertFalse(r["new_lab_created"])
        self.assertEqual(r["existing_lab_number"],14)

    def test_source_receipts_are_bound_not_claimed_as_external_certification(self):
        p,s=fixture()
        r=build_comparison(as_of=DAY,plan=p,source_book=s)
        self.assertEqual(r["source_receipts"]["M14_industry_original_browser_report"],canon_hash(s))
        self.assertEqual(r["source_receipts"]["M15_hypothesis_plan"],canon_hash(p))
        self.assertEqual(r["source_receipts"]["M12_national_comparison"],
                         build_market_audit(as_of=DAY)["receipt_sha256"])
        self.assertFalse(r["global_table_quality_flags"][0]["original_bytes_replayed_in_ci"])
        self.assertTrue(r["global_table_quality_flags"][1][
            "all_table_cell_quality_not_proof_of_sector_precision"])

    def test_money_and_percent_math_exact_and_guarded(self):
        self.assertEqual(_percent(1,3),"33.33")
        self.assertEqual(_percent(2,3),"66.67")
        self.assertEqual(_dollars_per_ton(1,1),"1000.00")
        with self.assertRaisesRegex(ValueError,"INCOMPATIBLE_CENSUS_DENOMINATOR"):
            _percent(3,2)
        for num,den in ((10,0),(-1,100),(True,100),(1,True)):
            with self.assertRaises(ValueError):
                _percent(num,den)
        for val,tons in ((-1,10),(1,0),(False,1)):
            with self.assertRaises(ValueError):
                _dollars_per_ton(val,tons)

    def test_source_date_expires_but_does_not_refresh_itself(self):
        r=build_comparison(as_of=DAY)
        self.assertFalse(r["independent_source_verification_due_for_recheck"])
        r=build_comparison(as_of=date(2027,2,1))
        self.assertTrue(r["independent_source_verification_due_for_recheck"])
        self.assertEqual(r["actual_invoice_bills_counted"],0)
        self.assertIsNone(r["paid_ltl_spend_by_industry_usd"])

    def test_wrong_plan_vintage_units_and_shared_survey_family_rejected(self):
        for key,bad in (
            ("survey_year",2017),("units",{"value":"USD_SPENT_ON_LTL","weight":"TONS"}),
            ("source_lineage","INDEPENDENT_AGENCY_CONFIRMATIONS"),
            ("data_sources",["CF2200A18","CF2200A19"]),
        ):
            p,s=fixture()
            p[key]=bad
            self.assertTrue(validate_plan(p,s,as_of=DAY),key)
            with self.assertRaisesRegex(ValueError,"INVALID_CFS_INDUSTRY_COMPARISON"):
                build_comparison(as_of=DAY,plan=p,source_book=s)

    def test_false_customer_evidence_or_deployment_permissions_rejected(self):
        p,s=fixture()
        false_fields=(
            "privacy_or_customer_source_data_used",
            "local_original_archives_replayed_in_ci",
            "industry_forhire_rows_verified_for_each_segment",
            "paid_ltl_invoice_total_known",
            "actual_audit_revenue_tam_known",
            "customer_demand_established",
            "real_external_claims_or_actions_authorized",
            "public_marketing_accuracy_claims_authorized",
            "new_lab_created",
        )
        for field in false_fields:
            bogus=deepcopy(p)
            bogus[field]=True
            self.assertIn("unverified market/customer approval", "; ".join(
                validate_plan(bogus,s,as_of=DAY)),field)

    def test_research_plan_falsification_text_must_remain_not_a_marketing_claim(self):
        for field in ("question","counterargument","disproof"):
            p,s=fixture()
            p["analysis_profiles"][0][field]="Buy now!"
            self.assertTrue(validate_plan(p,s,as_of=DAY),field)
        p,s=fixture()
        p["analysis_profiles"][0]["customer_name"]="private"
        self.assertIn("missing/extra fields", "; ".join(validate_plan(p,s,as_of=DAY)))

    def test_cannot_swap_naics_4931_into_493_or_rank_by_goods_value(self):
        p,s=fixture()
        p["analysis_profiles"][2]["naics"]="493"
        self.assertIn("source code/label or priority falsified", "; ".join(
            validate_plan(p,s,as_of=DAY)))
        p,s=fixture()
        p["analysis_profiles"][0]["sector_research_order_not_market_rank"]=True
        self.assertIn("source code/label or priority falsified", "; ".join(
            validate_plan(p,s,as_of=DAY)))
        p,s=fixture()
        p["analysis_profiles"][1]["source_status"]="VERIFIED_LTL_BUYER"
        self.assertTrue(validate_plan(p,s,as_of=DAY))

    def test_duplicate_missing_or_extra_sector_rejected(self):
        p,s=fixture()
        p["analysis_profiles"].pop()
        self.assertIn("three sourced, unranked", "; ".join(validate_plan(p,s,as_of=DAY)))
        p,s=fixture()
        p["analysis_profiles"][1]["naics"]="31-33"
        self.assertTrue(validate_plan(p,s,as_of=DAY))
        p,s=fixture()
        p["analysis_profiles"].append(deepcopy(p["analysis_profiles"][0]))
        self.assertTrue(validate_plan(p,s,as_of=DAY))

    def test_cannot_mark_pilot_authority_or_source_replication_complete(self):
        p,s=fixture()
        p["independent_evidence_gaps"][0]["approved"]=True
        self.assertIn("fabricated provenance or signoff","; ".join(
            validate_plan(p,s,as_of=DAY)))
        p,s=fixture()
        p["independent_evidence_gaps"][3]["dependency"]="M11_SUCCEEDED"
        self.assertTrue(validate_plan(p,s,as_of=DAY))
        p,s=fixture()
        p["independent_evidence_gaps"].pop()
        self.assertIn("four independent evidence gaps","; ".join(
            validate_plan(p,s,as_of=DAY)))

    def test_cannot_promote_survey_statistics_to_paid_freight_monetization(self):
        p,s=fixture()
        p["prohibited_measures"].remove("LTL_ONLY_FOR_HIRE_SHARE_BY_NAICS")
        self.assertIn("prohibited LTL market", "; ".join(validate_plan(p,s,as_of=DAY)))
        p,s=fixture()
        p["paid_ltl_invoices_usd"]=123456789
        self.assertIn("M15 scope or schema changed","; ".join(validate_plan(p,s,as_of=DAY)))

    def test_changes_to_original_cfs_industry_values_are_rejected(self):
        p,s=fixture()
        s["actual_industry_source_records"][2]["value_million_usd"]=10_000_000
        self.assertTrue(validate_plan(p,s,as_of=DAY))
        with self.assertRaisesRegex(ValueError,"INVALID_CFS_INDUSTRY_COMPARISON"):
            build_comparison(as_of=DAY,plan=p,source_book=s)

    def test_forged_flags_and_source_hashes_rejected(self):
        p,s=fixture()
        s["official_archives"][0]["weight_flag_counts"]["S"]=0
        self.assertTrue(validate_plan(p,s,as_of=DAY))
        p,s=fixture()
        s["official_archives"][1]["original_zip_sha256"]="a"*64
        self.assertTrue(validate_plan(p,s,as_of=DAY))

    def test_corrupt_m12_published_national_denominator_is_rejected(self):
        p,s=fixture()
        m=build_market_audit(as_of=DAY)
        m["published_estimate_measurements"]["total_value_million_usd"]=1
        m["receipt_sha256"]=canon_hash({k:v for k,v in m.items() if k!="receipt_sha256"})
        with self.assertRaisesRegex(ValueError,"NATIONAL_CFS_DENOMINATOR_DISAGREES_WITH_M12"):
            build_comparison(as_of=DAY,plan=p,source_book=s,market_report=m)

    def test_rehashed_market_tam_claim_cannot_pass(self):
        p,s=fixture()
        m=build_market_audit(as_of=DAY)
        m["market_ranking_or_recovery_tam_established"]=True
        m["receipt_sha256"]=canon_hash({k:v for k,v in m.items() if k!="receipt_sha256"})
        with self.assertRaisesRegex(ValueError,"M12_ORIGINAL_DENOMINATOR_AUDIT_UNTRUSTED"):
            build_comparison(as_of=DAY,plan=p,source_book=s,market_report=m)

    def test_invalid_nested_json_gracefully_fails_closed(self):
        for field,val in (
            ("analysis_profiles",[None,None,None]),
            ("independent_evidence_gaps",[1,2,3,4]),
            ("prohibited_measures",{}),
            ("units",[]),
        ):
            p,s=fixture()
            p[field]=val
            self.assertTrue(validate_plan(p,s,as_of=DAY),field)
        p,s=fixture()
        p["analysis_profiles"]=None
        with self.assertRaisesRegex(ValueError,"INVALID_CFS_INDUSTRY_COMPARISON"):
            build_comparison(as_of=DAY,plan=p,source_book=s)

    def test_bad_source_recheck_backdating_is_not_allowed(self):
        p,s=fixture()
        p["observed_on"]="2030-01-01"
        self.assertIn("future", "; ".join(validate_plan(p,s,as_of=DAY)))
        p,s=fixture()
        p["observed_on"]="2026-10-10"
        self.assertIn("cannot be backdated", "; ".join(validate_plan(p,s,as_of=DAY)))

    def test_html_escapes_hypotheses_and_warns_about_noninvoice_data(self):
        r=build_comparison(as_of=DAY)
        r=deepcopy(r)
        r["industry_comparisons"][0]["research_question"]='<script>alert("bad")</script>'
        html=render_html(r)
        self.assertNotIn("<script>",html)
        self.assertIn("&lt;script&gt;",html)
        self.assertIn("Compare observed freight goods",html)
        self.assertIn("NOT the error rate",html)
        self.assertIn("NOT a freight rate",html)

    def test_reproducible_static_receipts_do_not_establish_real_results(self):
        r=build_comparison(as_of=DAY)
        self.assertEqual(r,build_comparison(as_of=DAY))
        self.assertTrue(r["no_public_buyer_claims_authorized"])
        self.assertTrue(r["same_survey_not_independent_sources"])
        self.assertEqual(r["n_industries"],3)
        self.assertEqual(r["actual_invoice_bills_counted"],0)


if __name__=="__main__":
    unittest.main()
