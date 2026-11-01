"""Mission 21 original historical source tests. Synthetic ZIPs never prove Census."""
from __future__ import annotations

from copy import deepcopy
from datetime import date
from hashlib import sha256
from io import BytesIO, StringIO
from pathlib import Path
import csv
import json
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile, ZIP_DEFLATED

from freight.research_evidence_gate import canon_hash
from freight import research_aies_2022_lineage as m21

TODAY=date(2026,10,11)


def manifest():
    return json.loads(m21.BOOK.read_text(encoding="utf-8"))


def sample_rows():
    rows=[]
    for (year,code),value in m21.EXPECTED_VALUES.items():
        rows.append({
            "#GEOTYPE":"01","ST":"00","GEO_ID":"0100000US",
            "GEO_LABEL":"United States","GEO_ID_F":"",
            "NAICS":code,"NAICS_LABEL":m21.EXPECTED_LABELS[code],"NAICS_F":"",
            "TYPOP":"00","TYPOP_LABEL":"All establishments",
            "TAXSTAT":"00","TAXSTAT_LABEL":"All establishments",
            "YEAR":str(year),"RCPT_TOT_VAL":str(value),
            "RCPT_TOT_VAL_F":"",
            "RCPT_TOT_CV":m21.EXPECTED_CV[(year,code)],"RCPT_TOT_CV_F":"",
        })
    return sorted(rows,key=lambda x:(x["YEAR"],x["NAICS"]))


def fake_zip(rows=None, *, extra_member=False):
    if rows is None:
        rows=sample_rows()
    head=sorted(m21.SELECTOR_FIELDS)
    t=StringIO(newline="")
    w=csv.DictWriter(t,fieldnames=head,delimiter="|",
                     extrasaction="ignore",lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    dat=t.getvalue().encode("utf-8")
    stream=BytesIO()
    with ZipFile(stream,"w",compression=ZIP_DEFLATED) as z:
        z.writestr(m21.DAT_MEMBER,dat)
        z.writestr("AIESTIMESERIES_FIELDS.txt","Synthetic fields; not Census\n")
        z.writestr("AIESTIMESERIES_README.txt","Synthetic only\n")
        if extra_member:
            z.writestr("EXTRA.txt","unexpected")
    return stream.getvalue(),dat


def fake_verify(rows=None, *, extra_member=False):
    raw,dat=fake_zip(rows,extra_member=extra_member)
    # Keep the real frozen-source manifest gate intact; patch only the
    # synthetic byte parser expectations in this isolated unit fixture.
    offline = m21._shell(TODAY)
    with patch.object(m21,"_shell",return_value=offline),\
         patch.object(m21,"ZIP_BYTES",len(raw)),\
         patch.object(m21,"ZIP_SHA256",sha256(raw).hexdigest()),\
         patch.object(m21,"DAT_BYTES",len(dat)),\
         patch.object(m21,"DAT_SHA256",sha256(dat).hexdigest()),\
         patch.object(m21,"DAT_ROWS",len(rows or sample_rows())),\
         patch.object(m21,"DAT_FIELDS",len(m21.SELECTOR_FIELDS)):
        return m21.verify_archive(raw,as_of=TODAY)


class CensusHistoricalSourceTests(unittest.TestCase):
    def test_publisher_zip_source_manifest_fixed_and_valid(self):
        self.assertEqual(m21._blob_id(m21.BOOK.read_bytes()),m21.BOOK_GIT_BLOB_SHA1)
        self.assertEqual(m21.validate_manifest(manifest(),as_of=TODAY),[])
        self.assertEqual(m21.ZIP_BYTES,771290)
        self.assertEqual(len(m21.ZIP_SHA256),64)
        self.assertEqual(m21.DAT_ROWS,23448)
        self.assertEqual(m21.DAT_FIELDS,89)
        self.assertEqual(m21.DAT_BYTES,6800762)
        self.assertEqual(m21.SOURCE_URL,
            "https://www2.census.gov/programs-surveys/aies/data/2024/API_Datasets/AIESTIMESERIES.zip")

    def test_nine_revenue_cells_and_quality_flags_match_prior_2022_2024(self):
        selected=m21.selected_cells(sample_rows())
        self.assertEqual(len(selected),9)
        self.assertEqual([x["revenue_thousand_usd"] for x in selected if x["naics"]=="484122"],
                         [65688461,64651167,65096292])
        self.assertTrue(all(x["cv_is_not_an_invoice_error_rate"] for x in selected))

    def test_2022_historic_source_cv_zero_does_not_mean_perfect_precision(self):
        for row in m21.selected_cells(sample_rows()):
            if row["year"]==2022:
                self.assertEqual(row["published_cv_raw"],"0")
                self.assertFalse(row["source_year_direct_2022_aies_survey_collected"])
                self.assertTrue(row["historical_2022_cv_zero_does_not_establish_zero_uncertainty"])

    def test_explicit_sas_comparison_without_misrepresenting_causal_mechanism(self):
        report=m21._shell(TODAY)
        self.assertEqual(report["status"],m21.OFFLINE)
        self.assertEqual(report["published_2022_historical_ltl_revenue_thousand_usd"],65688461)
        self.assertEqual(report["legacy_sas_2022_revenue_million_usd"],68411)
        self.assertEqual(report["legacy_sas_gap_million_usd"],"2722.539")
        self.assertTrue(report["legacy_sas_2022_vintage_mismatch_still_unadjudicated"])
        self.assertIsNone(report["legacy_sas_gap_assigned_causal_mechanism"])
        self.assertFalse(report["latest_2022_sas_benchmark_original_rows_replayed"])

    def test_no_real_recoveries_and_existing_18_controls_preserved(self):
        report=m21._shell(TODAY)
        self.assertEqual(report["lab"],14)
        self.assertFalse(report["new_lab_created"])
        self.assertEqual(report["actual_customer_invoice_rows_processed"],0)
        self.assertFalse(report["actual_issued_refunds_or_recoveries_proven"])
        self.assertIsNone(report["ltl_recoverable_market_tam_usd"])
        self.assertIsNone(report["invoice_error_prevalence_pct"])
        self.assertFalse(report["buyer_demand_established"])
        self.assertFalse(report["external_contact_or_commercial_claims_authorized"])
        self.assertTrue(report["human_pilot_18_controls_still_unverified"])
        self.assertFalse(report["automatic_source_refresh_or_schedule_created"])

    def test_complete_synthetic_local_zip_roundtrip_not_official_certification(self):
        proof=fake_verify()
        self.assertEqual(proof["status"],m21.VERIFIED)
        self.assertEqual(proof["matched_national_year_naics_source_cells"],9)
        self.assertEqual(proof["source_dat_rows"],9)
        self.assertEqual(proof["source_dat_fields"],len(m21.SELECTOR_FIELDS))
        self.assertEqual(proof["receipt_sha256"],canon_hash({
            k:v for k,v in proof.items() if k!="receipt_sha256"
        }))

    def test_wrong_zip_bytes_or_original_hash_fails_closed(self):
        with self.assertRaisesRegex(ValueError,"M21_ORIGINAL_CENSUS_ZIP_SIZE_MISMATCH"):
            m21.verify_archive(b"not zip",as_of=TODAY)
        raw,_=fake_zip()
        with patch.object(m21,"ZIP_BYTES",len(raw)):
            with self.assertRaisesRegex(ValueError,"M21_ORIGINAL_CENSUS_ZIP_SHA256_DRIFT"):
                m21.verify_archive(raw,as_of=TODAY)

    def test_extra_member_is_not_allowed_even_with_rehashed_synthetic_zip(self):
        with self.assertRaisesRegex(ValueError,"M21_UNEXPECTED_ORIGINAL_ARCHIVE_MEMBER"):
            fake_verify(extra_member=True)

    def test_wrong_value_for_each_year_fails_even_in_same_source_format(self):
        for year in ("2022","2023","2024"):
            data=sample_rows()
            r=next(x for x in data if x["YEAR"]==year and x["NAICS"]=="484122")
            r["RCPT_TOT_VAL"]=str(int(r["RCPT_TOT_VAL"])+1)
            with self.assertRaisesRegex(ValueError,"M21_CENSUS_PRIMARY_HISTORIC_VS_FRED_DISAGREEMENT"):
                m21.selected_cells(data)

    def test_fake_2022_direct_aies_survey_flag_is_blocked(self):
        for flag in m21.BOOLEAN_HOLDS:
            b=manifest()
            b[flag]=True
            self.assertTrue(m21.validate_manifest(b,as_of=TODAY),flag)

    def test_forged_source_url_fingerprints_or_legacy_series_rejected(self):
        fields=[
            ("source_url","https://attacker.invalid/zip"),
            ("original_archive_sha256","0"*64),
            ("original_data_member_sha256","0"*64),
            ("original_data_field_count",9),
            ("original_data_row_count",9),
            ("legacy_sas_2022_revenue_million_usd",65688),
            ("reconciliation_status","SAS_RECONCILED"),
        ]
        for field,value in fields:
            b=manifest()
            b[field]=value
            self.assertTrue(m21.validate_manifest(b,as_of=TODAY),field)

    def test_wrong_geography_establishment_scope_or_year_is_not_counted(self):
        for k,value in [
            ("YEAR","2021"),("#GEOTYPE","02"),("ST","42"),
            ("GEO_ID","0500000US"),("GEO_LABEL","Pennsylvania"),
            ("TYPOP","01"),("TAXSTAT","01"),("NAICS","4931"),
        ]:
            data=sample_rows()
            data[0][k]=value
            with self.assertRaisesRegex(ValueError,"M21_CENSUS_HISTORIC_NINE_KEYS_MISSING",msg=k):
                m21.selected_cells(data)

    def test_suppressed_source_not_an_observed_zero(self):
        for key in ("NAICS_F","GEO_ID_F","RCPT_TOT_VAL_F","RCPT_TOT_CV_F"):
            data=sample_rows()
            data[0][key]="S"
            with self.assertRaisesRegex(ValueError,"M21_CENSUS_SOURCE_SUPPRESSION_OR_QUALITY_FLAG",msg=key):
                m21.selected_cells(data)

    def test_wrong_cv_or_improper_zero_precision_flags_rejected(self):
        for year in ("2022","2023"):
            data=sample_rows()
            row=next(x for x in data if x["YEAR"]==year and x["NAICS"]=="484122")
            row["RCPT_TOT_CV"]="0" if year=="2023" else ".9"
            with self.assertRaisesRegex(ValueError,"M21_HISTORICAL_CV_SOURCE_CELL_MISMATCH"):
                m21.selected_cells(data)

    def test_wrong_label_or_population_fields_rejected(self):
        for key,value in (
            ("NAICS_LABEL","All warehouses"),
            ("TYPOP_LABEL","Nonemployers"),("TAXSTAT_LABEL","Tax exempt"),
        ):
            data=sample_rows()
            data[-1][key]=value
            with self.assertRaises(ValueError,msg=key):
                m21.selected_cells(data)

    def test_duplicate_or_missing_historic_year_naics_rejected(self):
        data=sample_rows()
        with self.assertRaisesRegex(ValueError,"M21_CENSUS_HISTORIC_NINE_KEYS_MISSING"):
            m21.selected_cells(data[:-1])
        data.append(deepcopy(data[-1]))
        with self.assertRaisesRegex(ValueError,"M21_DUPLICATE_2022_2024_NATIONAL_SOURCE_ROW"):
            m21.selected_cells(data)

    def test_legacy_sas_data_instead_of_census_2022_rejected(self):
        data=sample_rows()
        row=next(x for x in data if x["YEAR"]=="2022" and x["NAICS"]=="484122")
        row["RCPT_TOT_VAL"]="68411000"
        with self.assertRaisesRegex(ValueError,"M21_CENSUS_PRIMARY_HISTORIC_VS_FRED_DISAGREEMENT"):
            m21.selected_cells(data)

    def test_census_value_zero_or_wrong_unit_rejected(self):
        for value in ("0","-1",".","65.688461","65688461000",None):
            data=sample_rows()
            data[0]["RCPT_TOT_VAL"]=value
            with self.assertRaises(ValueError,msg=str(value)):
                m21.selected_cells(data)

    def test_source_future_as_of_not_retroactively_verified(self):
        self.assertTrue(m21.validate_manifest(manifest(),as_of=date(2026,10,10)))
        with self.assertRaises(ValueError):
            m21._shell(date(2026,10,10))

    def test_offline_receipt_has_no_original_archive_fingerprint(self):
        r=m21._shell(TODAY)
        self.assertIsNone(r["verified_source_zip_sha256"])
        self.assertIsNone(r["verified_source_dat_sha256"])
        self.assertEqual(r["selected_source_cells"],[])
        self.assertEqual(r["matched_national_year_naics_source_cells"],0)
        self.assertEqual(r["receipt_sha256"],canon_hash({
            k:v for k,v in r.items() if k!="receipt_sha256"
        }))

    def test_network_timeout_no_fake_original_replay(self):
        with tempfile.TemporaryDirectory() as root:
            with patch("sys.argv",["m21","--as-of-date","2026-10-11","--out",root,"--fetch-original"]):
                with patch.object(m21,"_fetch_census_original",side_effect=TimeoutError("test")):
                    m21.main()
            out=json.loads((Path(root)/"aies_2022_lineage.json").read_text())
            self.assertEqual(out["status"],m21.BLOCKED)
            self.assertEqual(out["matched_national_year_naics_source_cells"],0)
            self.assertIsNone(out["verified_source_zip_sha256"])

    def test_changed_download_is_error_not_network_block(self):
        with tempfile.TemporaryDirectory() as root:
            with patch("sys.argv",["m21","--as-of-date","2026-10-11","--out",root,"--fetch-original"]):
                with patch.object(m21,"_fetch_census_original",return_value=b"corrupt government data"):
                    with self.assertRaisesRegex(ValueError,"M21_ORIGINAL_CENSUS_ZIP_SIZE_MISMATCH"):
                        m21.main()

    def test_html_escapes_historical_source_caveat(self):
        report=m21._shell(TODAY)
        report["caveat"]="<img src=x onerror=evil()>"
        html=m21.render_html(report)
        self.assertNotIn("<img src=x",html)
        self.assertIn("&lt;img src=x",html)
        self.assertIn("2022",html)


if __name__=="__main__":
    unittest.main()
