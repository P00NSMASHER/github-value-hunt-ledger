"""Mission 16: adversarial fixture tests; NO original Census ZIP bytes in CI."""
from __future__ import annotations

from copy import deepcopy
from datetime import date
import io
import json
import unittest
from zipfile import ZipFile, ZIP_DEFLATED

from freight.research_cfs_industry_quality import (
    BOOK as M14_BOOK, OFFICIAL_PROFILES,
)
from freight.research_cfs_forhire import (
    PLAN, BUCKETS, FILES, INDUSTRIES, build_readiness,
    replay_source_pair, render_html, validate_plan, _ratio,
)
from freight.research_evidence_gate import canon_hash

DAY=date(2026,10,11)
KNOWN_ALL={
    "31-33": (7073495, 4949955),
    "42":(8094350,4115279),
    "4931":(1347716,305651),
}
MOCK_FORHIRE={
    "31-33":(4000000,2000000),
    "42":(5000000,2300000),
    "4931":(500000,100000),
}


def _plan():
    return json.loads(PLAN.read_text(encoding="utf-8")),json.loads(
        M14_BOOK.read_text(encoding="utf-8")
    )


def _fixture(table: str, mutate=None, *, all_buckets=True, member=None) -> bytes:
    axis,total,name,*_=FILES[table]
    cols=OFFICIAL_PROFILES[table]["header"].split("|")
    rows=[]
    for naics in INDUSTRIES:
        for mode in ("00","111"):
            value,weight = (
                KNOWN_ALL[naics] if mode=="00" else MOCK_FORHIRE[naics]
            )
            fields={
                "#GEOTYPE":"01","ST":"00","GEO_ID":"0100000US",
                "GEO_LABEL":"United States",
                "NAICS2017":naics,"DMODE":mode,"YEAR":"2022",
                axis:total,"VAL":str(value),"TON":str(weight),
                "VAL_F":"","TON_F":"","VAL_S":"4.2","TON_S":"7.8",
                "VAL_S_F":"","TON_S_F":"",
            }
            rows.append(fields)
            if mode=="111" and all_buckets:
                for i,k in enumerate(BUCKETS):
                    v,r=divmod(value,len(BUCKETS))
                    w,s=divmod(weight,len(BUCKETS))
                    part=dict(fields)
                    part.update({axis:k,"VAL":str(v+(i<r)),
                                 "TON":str(w+(i<s))})
                    rows.append(part)
    if mutate:
        mutate(rows,axis,total)
    data="|".join(cols)+"\n"+"\n".join(
        "|".join(str(row.get(c,"")) for c in cols) for row in rows
    )+"\n"
    buff=io.BytesIO()
    with ZipFile(buff,"w",compression=ZIP_DEFLATED) as zip_file:
        zip_file.writestr(member or name,data.encode("utf-8"))
        zip_file.writestr(f"{table}_FIELDS.txt","FICTITIOUS UNIT TEST FIELD NOTES")
    return buff.getvalue()


def _pair(f18=None,f19=None,*, buckets=True):
    return (
        _fixture("CF2200A18",f18,all_buckets=buckets),
        _fixture("CF2200A19",f19,all_buckets=buckets)
    )


def _run(a=None,b=None):
    if a is None or b is None:
        a,b=_pair()
    return replay_source_pair(
        a18_zip=a,a19_zip=b,as_of=DAY,synthetic_test=True
    )


class ForHireCfsReplayTests(unittest.TestCase):
    def test_default_research_state_never_claims_source_values(self):
        report=build_readiness(as_of=DAY)
        self.assertEqual(report["scope"],"LAB14_CFS_FORHIRE_SECTOR_REPLAY_AWAITING_ORIGINAL_ZIPS")
        self.assertEqual(report["source_files_replayed_in_ci"],0)
        self.assertEqual(report["source_industry_forhire_rows_reproduced_in_ci"],0)
        self.assertEqual(report["sectors_with_verified_forhire_numerators"],0)
        self.assertEqual(report["source_total_rows_to_reconcile"],12)
        self.assertEqual(len(report["industry_research_targets"]),3)
        for row in report["industry_research_targets"]:
            self.assertIsNone(row["forhire_value_million_usd"])
            self.assertIsNone(row["forhire_weight_thousand_tons"])
            self.assertIsNone(row["goods_value_share_pct"])
        self.assertFalse(report["source_fetch_or_scheduler_enabled"])
        self.assertFalse(report["new_lab_created"])
        self.assertEqual(report["existing_lab_number"],14)
        self.assertEqual(report["receipt_sha256"],canon_hash({
            k:v for k,v in report.items() if k!="receipt_sha256"
        }))

    def test_original_file_hashes_and_data_grains_frozen(self):
        r=build_readiness(as_of=DAY)
        self.assertEqual(r["original_source_hashes_verified_remotely"],{
            "CF2200A18":"a18ce071599457572177dd56f8a6174594d1018da9b9024476c4e9832a357bf5",
            "CF2200A19":"fe3085d23a3c76704a0d86d9213bb38d3d341b2c228990a5ebf40b6b3f1b661d",
        })
        self.assertTrue(r["no_inferred_ltl_only_transport_classification"])
        self.assertTrue(r["no_paid_ltl_invoice_spend_available"])

    def test_synthetic_complete_archives_reconcile_six_mode_rows(self):
        r=_run()
        self.assertEqual(r["scope"],"LAB14_SYNTHETIC_FORHIRE_PARSER_TEST_NOT_REAL_CENSUS")
        self.assertFalse(r["original_Census_ZIPs_hash_replayed"])
        self.assertTrue(r["no_new_lab_created"])
        self.assertEqual(r["existing_lab_number"],14)
        self.assertEqual(r["national_2022_mode_111_direct_sector_cells"],3)
        self.assertEqual(len(r["industry_results"]),3)
        self.assertFalse(r["paid_ltl_invoice_spend_confirmed"])
        self.assertFalse(r["customer_demand_confirmed"])
        self.assertFalse(r["recovery_revenue_estimated"])
        self.assertFalse(r["customer_or_carrier_action_allowed"])

    def test_synthetic_fractions_are_not_commercial_ltl_measurements(self):
        r=_run()
        for row in r["industry_results"]:
            naics=row["naics2017"]
            v,t=MOCK_FORHIRE[naics]
            self.assertEqual(row["forhire_goods_value_million_usd"],v)
            self.assertEqual(row["forhire_weight_thousand_tons"],t)
            self.assertEqual(row["forhire_value_cv_percent"],"4.2")
            self.assertEqual(row["forhire_weight_cv_percent"],"7.8")
            self.assertEqual(row["adjudication"],"DESCRIPTIVE_FORHIRE_GOODS_SHARE_NOT_LTL")
            self.assertIsNone(row["verified_paid_ltl_invoice_count"])
            self.assertIsNone(row["recoverable_overcharges_usd"])
            self.assertFalse(row["ltl_only_modal_classification_established"])
            self.assertIn("Ratio covariance",row["precision_limitation"])
            self.assertEqual(
                row["forhire_share_of_sector_shipped_goods_value_pct"],
                _ratio(v,KNOWN_ALL[naics][0])
            )

    def test_per_stratum_shares_require_complete_nonoverlap(self):
        r=_run()
        for row in r["industry_results"]:
            self.assertEqual(row["distance_under_250_miles_goods_value_share"]["status"],
                             "DESCRIPTIVE_SOURCE_FRACTION_NO_STATISTICAL_CLAIM")
            self.assertEqual(row["shipment_weight_500_to_9999lbs_goods_value_share"]["status"],
                             "DESCRIPTIVE_SOURCE_FRACTION_NO_STATISTICAL_CLAIM")
            self.assertIsNotNone(row["distance_under_250_miles_goods_value_share"][
                "percent_of_forhire_goods_value"
            ])

    def test_missing_any_bucket_causes_hold_not_extrapolation(self):
        a,b=_pair(buckets=False)
        r=_run(a,b)
        self.assertEqual(r["industry_results"][0][
            "distance_under_250_miles_goods_value_share"]["status"],
            "HOLD_INCOMPLETE_OR_SUPPRESSED_BUCKET_FRAME")
        self.assertIsNone(r["industry_results"][0][
            "shipment_weight_500_to_9999lbs_goods_value_share"][
                "percent_of_forhire_goods_value"
            ])

    def test_suppressed_forhire_value_is_not_zero_or_accuracy(self):
        def altered(rows,axis,total):
            for row in rows:
                if row["NAICS2017"]=="31-33" and row["DMODE"]=="111" and row[axis]==total:
                    row["VAL"]="0";row["VAL_F"]="S"
        a,b=_pair(altered,altered)
        r=_run(a,b)
        record=r["industry_results"][0]
        self.assertIsNone(record["forhire_goods_value_million_usd"])
        self.assertEqual(record["forhire_value_source_flag"],"S")
        self.assertEqual(record["adjudication"],"HOLD_UNPUBLISHABLE_OR_UNKNOWN_NUMERIC_ESTIMATE")
        self.assertIsNone(record["forhire_share_of_sector_shipped_goods_value_pct"])

    def test_rounds_to_zero_flag_is_never_literal_exact_zero(self):
        def altered(rows,axis,total):
            for row in rows:
                if row["NAICS2017"]=="42" and row["DMODE"]=="111" and row[axis]==total:
                    row["TON"]="0";row["TON_F"]="Z"
        a,b=_pair(altered,altered)
        r=_run(a,b)
        item=r["industry_results"][1]
        self.assertIsNone(item["forhire_weight_thousand_tons"])
        self.assertEqual(item["forhire_weight_source_flag"],"Z")
        self.assertIsNone(item["forhire_share_of_sector_shipped_tonnage_pct"])

    def test_quality_flagged_bucket_causes_held_composition(self):
        def altered(rows,axis,total):
            for row in rows:
                if row["NAICS2017"]=="4931" and row["DMODE"]=="111" and row[axis]=="04":
                    row["VAL_F"]="S"
        a,b=_pair(altered,altered)
        r=_run(a,b)
        self.assertEqual(r["industry_results"][2]["distance_under_250_miles_goods_value_share"]["status"],
                         "HOLD_INCOMPLETE_OR_SUPPRESSED_BUCKET_FRAME")
        self.assertEqual(r["industry_results"][2]["shipment_weight_500_to_9999lbs_goods_value_share"]["status"],
                         "HOLD_INCOMPLETE_OR_SUPPRESSED_BUCKET_FRAME")

    def test_unavailable_cv_is_explicitly_null(self):
        def altered(rows,axis,total):
            for row in rows:
                if row["NAICS2017"]=="31-33" and row["DMODE"]=="111" and row[axis]==total:
                    row["VAL_S"]="0";row["VAL_S_F"]="S"
        a,b=_pair(altered,altered)
        r=_run(a,b)
        self.assertIsNone(r["industry_results"][0]["forhire_value_cv_percent"])
        self.assertIn("covariance",r["industry_results"][0]["precision_limitation"])

    def test_mismatched_a18_a19_total_is_not_silently_averaged(self):
        def bad(rows,axis,total):
            for row in rows:
                if row["NAICS2017"]=="31-33" and row["DMODE"]=="111" and row[axis]==total:
                    row["VAL"]="4000001"
        a,b=_pair(f19=bad)
        with self.assertRaisesRegex(ValueError,"CFS_A18_A19_INCOMPATIBLE_NATIONAL_TOTALS"):
            _run(a,b)

    def test_forhire_cannot_exceed_all_modes_in_same_industry(self):
        def bad(rows,axis,total):
            for row in rows:
                if row["NAICS2017"]=="4931" and row["DMODE"]=="111" and row[axis]==total:
                    row["VAL"]="1400000"
        a,b=_pair(bad,bad)
        with self.assertRaisesRegex(ValueError,"CFS_FORHIRE_EXCEEDS_ALL_MODE_VALUE"):
            _run(a,b)

    def test_m14_known_all_mode_denominator_is_invariant(self):
        def bad(rows,axis,total):
            for row in rows:
                if row["NAICS2017"]=="42" and row["DMODE"]=="00" and row[axis]==total:
                    row["VAL"]="1"
        a,b=_pair(bad,bad)
        with self.assertRaisesRegex(ValueError,"CFS_M14_ALL_MODE_PUBLISHED_TOTAL_MISMATCH"):
            _run(a,b)

    def test_duplicate_national_mode_bucket_key_fail_closed(self):
        def bad(rows,axis,total):
            rows.append(deepcopy(rows[0]))
        a,b=_pair(f18=bad)
        with self.assertRaisesRegex(ValueError,"DUPLICATED_CFS_INDUSTRY_MODE_BUCKET"):
            _run(a,b)

    def test_missing_original_total_is_not_derived_from_buckets(self):
        def missing(rows,axis,total):
            rows[:]=[r for r in rows if not (
                r["NAICS2017"]=="4931" and r["DMODE"]=="111" and r[axis]==total
            )]
        a,b=_pair(f18=missing)
        with self.assertRaisesRegex(ValueError,"MISSING_INDUSTRY_MODE_TOTAL"):
            _run(a,b)

    def test_wrong_year_does_not_relabel_2017_to_2022(self):
        def bad(rows,axis,total):
            rows[0]["YEAR"]="2017"
        a,b=_pair(f18=bad)
        with self.assertRaisesRegex(ValueError,"CFS_NATIONAL_SOURCE_VINTAGE_MISMATCH"):
            _run(a,b)

    def test_wrong_geography_cannot_create_a_national_reference(self):
        def bad(rows,axis,total):
            rows[0]["GEO_ID"]="0200000US3"
        a,b=_pair(f18=bad)
        with self.assertRaisesRegex(ValueError,"MISSING_INDUSTRY_MODE_TOTAL"):
            _run(a,b)

    def test_unknown_bucket_code_is_not_summed(self):
        def bad(rows,axis,total):
            for row in rows:
                if row["NAICS2017"]=="31-33" and row["DMODE"]=="111" and row[axis]=="02":
                    row[axis]="UNKNOWN"
        a,b=_pair(f18=bad)
        with self.assertRaisesRegex(ValueError,"UNEXPECTED_CFS_FORHIRE_STRATUM"):
            _run(a,b)

    def test_wrong_source_zip_member_is_held(self):
        a=_fixture("CF2200A18",member="source_relabel.csv")
        _,b=_pair()
        with self.assertRaisesRegex(ValueError,"OFFICIAL_CFS_DAT_MEMBER_NOT_FOUND"):
            _run(a,b)

    def test_unverified_zip_cannot_receive_an_original_source_label(self):
        a,b=_pair()
        with self.assertRaisesRegex(ValueError,"OFFICIAL_CFS_ORIGINAL_ZIP_HASH_MISMATCH"):
            replay_source_pair(a18_zip=a,a19_zip=b,as_of=DAY,synthetic_test=False)

    def test_no_new_customer_or_income_fields_allowed_in_source_plan(self):
        p,original=_plan()
        p["buyer_email"]="hidden@example.org"
        self.assertIn("provenance/scope fields changed","; ".join(
            validate_plan(p,original,as_of=DAY)))

    def test_plan_original_source_hash_tamper_is_detected(self):
        p,original=_plan()
        p["source_files"][0]["sha256"]="0"*64
        self.assertIn("source identity or fingerprint changed","; ".join(
            validate_plan(p,original,as_of=DAY)))

    def test_plan_claim_of_real_customer_recovery_is_blocked(self):
        p,original=_plan()
        p["real_ltl_invoice_values_measured"]=True
        self.assertIn("fabricated original data or commercial authority","; ".join(
            validate_plan(p,original,as_of=DAY)))

    def test_changed_source_geography_mode_or_naics_denied(self):
        p,original=_plan()
        p["geo"]["geo_id"]="0200000US3"
        self.assertIn("national NAICS/mode/stratum source grain altered","; ".join(
            validate_plan(p,original,as_of=DAY)))
        p,original=_plan()
        p["naics"][2]="493"
        self.assertTrue(validate_plan(p,original,as_of=DAY))

    def test_m14_original_source_quality_cannot_be_overwritten(self):
        p,original=_plan()
        original["official_archives"][0]["weight_flag_counts"]["S"]=0
        self.assertTrue(validate_plan(p,original,as_of=DAY))

    def test_date_or_archival_cross_year_tamper_denied(self):
        p,original=_plan()
        p["observed_on"]="2030-12-31"
        self.assertIn("future","; ".join(validate_plan(p,original,as_of=DAY)))
        p,original=_plan()
        p["year"]="2017"
        self.assertIn("incompatible CFS vintage","; ".join(
            validate_plan(p,original,as_of=DAY)))

    def test_incomplete_bucket_rounding_is_not_silent(self):
        def bad(rows,axis,total):
            for row in rows:
                if row["NAICS2017"]=="31-33" and row["DMODE"]=="111" and row[axis]=="09":
                    row["VAL"]="1"
        a,b=_pair(f18=bad)
        r=_run(a,b)
        self.assertEqual(r["industry_results"][0]["distance_under_250_miles_goods_value_share"]["status"],
                         "HOLD_BUCKET_DENOMINATOR_OR_ROUNDING_MISMATCH")

    def test_html_report_does_not_imply_customer_accuracy(self):
        r=build_readiness(as_of=DAY)
        h=render_html(r)
        self.assertIn("For-hire industry evidence must come from the original source.",h)
        self.assertIn("Unverified",h)
        self.assertNotIn("Verified LTL accuracy",h)

    def test_generated_synthetic_reports_are_reproducible(self):
        a,b=_pair()
        x=_run(a,b)
        self.assertEqual(x,_run(a,b))
        self.assertEqual(x["receipt_sha256"],canon_hash({
            k:v for k,v in x.items() if k!="receipt_sha256"
        }))
        self.assertTrue(x["same_underlying_CFS_survey_not_independent_datasets"])


if __name__ == "__main__":
    unittest.main()
