"""Lab 14 Mission 25: adversarial original Census SAS/AIES source bridge tests.

Fixture rows are synthetic/pinned snapshots. They do not authenticate Census
publisher ZIP bytes; the separate live read-only CI replay must do so.
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
from freight import research_sas_aies_bridge as m25

TODAY=date(2026,10,12)


def catalog():
    return json.loads(m25.BOOK.read_text(encoding="utf-8"))


def grids():
    return {
        "sas":{c:m25._expected_values(m25.SAS_ID,c) for c in m25.NAICS},
        "aies":{c:m25._expected_values(m25.HISTORY_ID,c) for c in m25.NAICS},
        "basic":{c:m25._expected_values(m25.BASIC_ID,c) for c in m25.NAICS},
    }


class EightYearCensusBridgeTests(unittest.TestCase):
    def test_pinned_manifest_provenance_and_accepted_closed_grain(self):
        self.assertEqual(m25._git_blob(m25.BOOK.read_bytes()),m25.BOOK_BLOB_SHA1)
        self.assertEqual(m25.validate_catalog(catalog(),as_of=TODAY),[])
        self.assertEqual(tuple(catalog()["national_naics"]),m25.NAICS)
        self.assertEqual(tuple(catalog()["selected_years"]),m25.ALL_YEARS)
        self.assertEqual(len(catalog()["sources"]),3)

    def test_exact_original_three_archives_and_dates_not_invented(self):
        sources={s["id"]:s for s in catalog()["sources"]}
        self.assertEqual(set(sources),set(m25.SOURCE_IDS))
        for ident in m25.SOURCE_IDS:
            raw=sources[ident]
            self.assertEqual(len(raw["original_sha256"]),64)
            self.assertEqual(raw["original_bytes"],m25.SOURCE_IDENTITY[ident][2])
            self.assertTrue(raw["source_url"].startswith("https://www2.census.gov/"))
        self.assertEqual(sources[m25.SAS_ID]["source_years"],list(range(2017,2023)))
        self.assertEqual(sources[m25.HISTORY_ID]["source_years"],[2022,2023,2024])
        self.assertEqual(sources[m25.BASIC_ID]["source_years"],[2024])

    def test_2022_revised_sas_and_aies_linked_history_reconcile_all_three(self):
        result=m25.stitch_values(**grids())
        self.assertEqual(len(result["overlap_2022"]),3)
        self.assertEqual(
            [x["aies_minus_sas_million_usd"] for x in result["overlap_2022"]],
            ["-0.042","0.339","0.461"],
        )
        self.assertTrue(all(x["agrees_at_original_sas_nearest_million"]
                            and not x["is_2022_independently_fielded_aies_survey"]
                            for x in result["overlap_2022"]))

    def test_source_specific_2017_2024_grid_24_industry_years(self):
        result=m25.stitch_values(**grids())
        self.assertEqual(len(result["industry_series"]),3)
        for industry in result["industry_series"]:
            annual=industry["annual_revenue"]
            self.assertEqual([x["year"] for x in annual],list(m25.ALL_YEARS))
            self.assertEqual(len(annual),8)
            self.assertEqual([x["source_id"] for x in annual],
                             [m25.SAS_ID]*5+[m25.HISTORY_ID]*3)
            self.assertEqual(
                [x["year"] for x in annual if x["year_is_linked_legacy_not_standalone_aies_survey"]],
                [2022],
            )
            self.assertTrue(all(not x["is_customer_freight_invoice_or_recovered_cash"] for x in annual))

    def test_sas_million_conversion_to_aies_thousand_precision(self):
        result=m25.stitch_values(**grids())
        ltl=result["industry_series"][2]["annual_revenue"]
        self.assertEqual(ltl[0]["revenue_thousand_usd"],46_192_000)
        self.assertEqual(ltl[0]["revenue_million_usd"],"46192.000")
        self.assertEqual(ltl[4]["revenue_million_usd"],"58035.000")
        self.assertEqual(ltl[5]["revenue_million_usd"],"65688.461")
        self.assertEqual(ltl[6]["revenue_million_usd"],"64651.167")
        self.assertEqual(ltl[7]["revenue_million_usd"],"65096.292")

    def test_eight_year_nominal_industry_changes_are_descriptive_only(self):
        r=m25.report_shell(as_of=TODAY)
        bycode={x["naics"]:x for x in r["industry_series"]}
        for code,nominal,end_in_2024 in (
            ("484","38.65","402827.246"),
            ("484121","43.48","161329.027"),
            ("484122","40.93","65096.292"),
        ):
            self.assertEqual(bycode[code]["2017_to_2024_nominal_cumulative_change_pct"],nominal)
            self.assertEqual(bycode[code]["annual_revenue"][-1]["revenue_million_usd"],end_in_2024)
            self.assertFalse(bycode[code]["2017_to_2024_change_is_statistically_significant"])
        self.assertEqual(bycode["484122"]["2022_to_2023_aies_nominal_change_pct"],"-1.58")
        self.assertEqual(bycode["484122"]["2023_to_2024_aies_nominal_change_pct"],"0.69")
        self.assertFalse(r["nominal_growth_is_inflation_adjusted"])

    def test_offline_source_state_not_mistaken_for_fresh_archive_replay(self):
        r=m25.report_shell(as_of=TODAY)
        self.assertEqual(r["source_status"],m25.OFFLINE)
        self.assertFalse(r["census_original_replay_completed_in_this_run"])
        self.assertEqual(r["source_original_archive_receipts"],[])
        self.assertEqual(r["original_source_archives_required"],3)
        self.assertEqual(r["distinct_industry_year_values"],24)
        self.assertEqual(r["receipt_sha256"],canon_hash({
            k:v for k,v in r.items() if k!="receipt_sha256"
        }))

    def test_parent_trucking_revenue_contains_both_children_not_additive_market(self):
        r=m25.report_shell(as_of=TODAY)
        self.assertTrue(r["naics_484_contains_484121_and_484122"])
        self.assertTrue(r["same_parent_child_revenue_cannot_be_added_as_independent_markets"])
        self.assertTrue(r["source_family_not_independent_surveys"])
        self.assertTrue(r["released_census_aies_2024_from_same_publisher_not_independent_market_study"])

    def test_all_eighteen_pilot_controls_and_zero_true_customer_evidence(self):
        r=m25.report_shell(as_of=TODAY)
        self.assertEqual(r["lab"],14)
        self.assertFalse(r["new_lab_created"])
        self.assertEqual(r["real_ltl_freight_invoice_cases_observed"],0)
        self.assertIsNone(r["customer_billing_error_rate_pct"])
        self.assertIsNone(r["contractually_eligible_refund_volume_usd"])
        self.assertIsNone(r["actual_retally_collected_recovery_cash_usd"])
        self.assertIsNone(r["recoverable_freight_audit_market_usd"])
        self.assertFalse(r["buyer_demand_established"])
        self.assertFalse(r["carrier_or_customer_contact_authorized"])
        self.assertFalse(r["customer_or_carrier_private_documents_accessed"])
        self.assertTrue(r["human_pilot_18_independent_requirements_unmet"])
        self.assertFalse(r["automated_tasks_or_schedules_modified"])

    def test_2022_overlap_tolerance_is_not_a_license_to_mix_old_sas(self):
        data=grids()
        data["sas"]["484122"][-1]=68411
        with self.assertRaisesRegex(ValueError,"M25_SAS_AIES_2022_HANDOFF"):
            m25.stitch_values(**data)

    def test_reject_2022_wrong_population_or_inconsistent_rounded_number(self):
        data=grids()
        data["aies"]["484"][-3]+=1000
        with self.assertRaisesRegex(ValueError,"M25_SAS_AIES_2022_HANDOFF"):
            m25.stitch_values(**data)

    def test_2024_history_basic_mismatch_rejected(self):
        data=grids()
        data["basic"]["484121"][-1]+=1
        with self.assertRaisesRegex(ValueError,"M25_2024_AIES_BASIC_DISAGREES"):
            m25.stitch_values(**data)

    def test_2023_revenue_tamper_not_hidden_by_matching_overlap(self):
        data=grids()
        data["aies"]["484122"][1]+=1
        with self.assertRaisesRegex(ValueError,"M25_SOURCE_VINTAGE_OR_INDUSTRY_REVENUE_CHANGED"):
            m25.stitch_values(**data)

    def test_single_2018_sas_wrong_year_value_rejected(self):
        data=grids()
        data["sas"]["484121"][1]+=1
        with self.assertRaisesRegex(ValueError,"M25_SOURCE_VINTAGE_OR_INDUSTRY_REVENUE_CHANGED"):
            m25.stitch_values(**data)

    def test_aies_millions_mislabeled_as_thousands_rejected(self):
        data=grids()
        data["aies"]["484122"]=[65688,64651,65096]
        with self.assertRaisesRegex(ValueError,"M25_SAS_AIES_2022_HANDOFF"):
            m25.stitch_values(**data)

    def test_null_negative_float_bool_or_fake_customer_source_values(self):
        for val in (None,True,0,-1,42.1,"65096292",{"invoice":1}):
            data=grids()
            data["sas"]["484"][0]=val
            with self.assertRaisesRegex(ValueError,"M25_REJECT_WRONG_YEAR_GRAIN_UNIT_OR_UNPUBLISHED_VALUE",
                                        msg=repr(val)):
                m25.stitch_values(**data)

    def test_added_removed_industry_or_missing_years_fail_closed(self):
        for field in ("sas","aies","basic"):
            data=grids()
            del data[field]["484"]
            with self.assertRaisesRegex(ValueError,"M25_REJECT_MISSING_OR_ADDED_NAICS_CLASSIFICATION"):
                m25.stitch_values(**data)
            data=grids()
            data[field]["484"][0:1]=[]
            with self.assertRaisesRegex(ValueError,"M25_REJECT_WRONG_YEAR_GRAIN_UNIT_OR_UNPUBLISHED_VALUE"):
                m25.stitch_values(**data)

    def test_swapped_source_year_2017_2018_in_sas_rejected(self):
        data=grids()
        data["sas"]["484"][0],data["sas"]["484"][1]=data["sas"]["484"][1],data["sas"]["484"][0]
        with self.assertRaisesRegex(ValueError,"M25_SOURCE_VINTAGE_OR_INDUSTRY_REVENUE_CHANGED"):
            m25.stitch_values(**data)

    def test_source_manifest_rejects_all_unsupported_surveys_and_commercial_claims(self):
        for flag in m25.FALSE_GUARDS:
            book=catalog()
            book[flag]=True
            self.assertIn("M25_FALSE_CENSUS_OR_CUSTOMER_EVIDENCE_PROMOTION",
                          "; ".join(m25.validate_catalog(book,as_of=TODAY)),flag)

    def test_source_manifest_cannot_change_ids_dates_or_census_hashes(self):
        for sid in m25.SOURCE_IDS:
            for key,value in (
                ("original_sha256","0"*64),
                ("original_bytes",123),
                ("source_url","https://unapproved.example/revenue.csv"),
                ("source_years",[2025]),
                ("unit","DOLLAR_CUSTOMER_SPEND"),
            ):
                book=catalog()
                source=next(x for x in book["sources"] if x["id"]==sid)
                source[key]=value
                self.assertTrue(m25.validate_catalog(book,as_of=TODAY),sid+key)

    def test_manifest_rejects_unrelated_invoice_fields_in_public_source(self):
        book=catalog()
        book["customer_contract_rate"]=0.1
        self.assertTrue(m25.validate_catalog(book,as_of=TODAY))
        book=catalog()
        book["sources"][1]["naics_revenue"]["484122"][0]+=1
        self.assertTrue(m25.validate_catalog(book,as_of=TODAY))

    def test_source_observation_date_cannot_be_retroactively_assumed(self):
        self.assertTrue(m25.validate_catalog(catalog(),as_of=date(2026,10,11)))
        with self.assertRaisesRegex(ValueError,"M25_CLOSED_CENSUS_SOURCE_BOOK_INVALID"):
            m25.report_shell(as_of=date(2026,10,11))

    def test_exact_three_original_archives_mandatory(self):
        with self.assertRaisesRegex(ValueError,"M25_THREE_CENSUS_ORIGINAL_ARCHIVES_REQUIRED_FOR_REPLAY"):
            m25.verify_origins(as_of=TODAY,archives={m25.SAS_ID:b"irrelevant"})

    def test_false_sha_pinned_original_sas_fails_before_data_parsing(self):
        data={m25.SAS_ID:b"fake",m25.HISTORY_ID:b"fake",m25.BASIC_ID:b"fake"}
        with self.assertRaisesRegex(ValueError,"M24_ORIGINAL_WORKBOOK_BYTE_LENGTH_MISMATCH"):
            m25.verify_origins(as_of=TODAY,archives=data)

    def test_blocked_state_never_promotes_unfetched_archive_claim(self):
        r=m25.blocked(as_of=TODAY)
        self.assertEqual(r["source_status"],m25.BLOCKED)
        self.assertFalse(r["census_original_replay_completed_in_this_run"])
        self.assertEqual(r["source_original_archive_receipts"],[])
        self.assertEqual(r["receipt_sha256"],canon_hash({
            k:v for k,v in r.items() if k!="receipt_sha256"
        }))

    def test_timeout_writes_explicit_network_block_report(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch("sys.argv",["program","--out",directory,"--as-of-date","2026-10-12",
                                   "--fetch-originals"]):
                with patch.object(m25,"get_source",side_effect=TimeoutError("synthetic")):
                    m25.main()
            report=json.loads((Path(directory)/"sas_aies_revenue_bridge.json").read_text())
            self.assertEqual(report["source_status"],m25.BLOCKED)
            self.assertIsNone(report["recoverable_freight_audit_market_usd"])
            self.assertFalse(report["census_original_replay_completed_in_this_run"])

    def test_downloaded_but_changed_source_is_fail_not_network_block(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch("sys.argv",["program","--out",directory,"--as-of-date","2026-10-12",
                                   "--fetch-originals"]):
                with patch.object(m25,"get_source",return_value=b"tampered"), \
                     patch.object(m25,"download_aies_history",return_value=b"untrusted"), \
                     patch.object(m25,"download_aies_basic",return_value=b"untrusted"):
                    with self.assertRaisesRegex(ValueError,"M24_ORIGINAL_WORKBOOK_BYTE_LENGTH_MISMATCH"):
                        m25.main()

    def test_html_report_escapes_untrusted_text_and_clearly_marks_2022(self):
        r=m25.report_shell(as_of=TODAY)
        r["caveat"]="<script>alert('invoice')</script>"
        html=m25.render_html(r)
        self.assertNotIn("<script>",html)
        self.assertIn("&lt;script&gt;",html)
        self.assertIn("2022",html)
        self.assertIn("not a separately fielded",html)
        self.assertIn("original Census",html)

    def test_source_year_description_must_not_claim_direct_2022_sample(self):
        b=catalog()
        b["source_year_2022"]="2022_INDEPENDENTLY_SAMPLED_ORIGINAL_AIES"
        self.assertTrue(m25.validate_catalog(b,as_of=TODAY))


if __name__ == "__main__":
    unittest.main()
