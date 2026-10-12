"""Adversarial Mission 20 historical Census AIES provenance tests.

Synthetic source bytes have no Census-source authority. Live CI does all
original hash/size/member/row equality checks on actual publisher ZIPs.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date
from hashlib import sha256
import csv
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile, ZIP_DEFLATED

from freight.research_evidence_gate import canon_hash
from freight import research_aies_historical_lineage as m20

TODAY=date(2026,10,11)


def book():
    return json.loads(m20.BOOK.read_text(encoding="utf-8"))


def rows(ident="2023_published"):
    naics=m20.PINNED[ident][-1]
    cells=[]
    for code,(label,val,cv) in m20.EXPECTED_2023.items():
        cells.append({
            "#GEOTYPE":"01", "ST":"00", "GEO_ID":"0100000US",
            "GEO_LABEL":"United States", "GEO_ID_F":"",
            naics:code, naics+"_LABEL":label, naics+"_F":"",
            "TYPOP":"00","TYPOP_LABEL":"All establishments",
            "TAXSTAT":"00","TAXSTAT_LABEL":"All establishments",
            "YEAR":"2023", "RCPT_TOT_VAL":str(val),"RCPT_TOT_VAL_F":"",
            "RCPT_TOT_CV":"."+cv.split(".")[1] if "." in cv and cv.startswith("0.") else cv,
            "RCPT_TOT_CV_F":"",
        })
    return cells


def fake_zip(ident: str, data=None):
    if data is None:
        data=rows(ident)
    naics=m20.PINNED[ident][-1]
    cols=list(m20.SOURCE_REQUIRED | {naics,naics+"_LABEL",naics+"_F"})
    cols=sorted(cols)
    buf=io.StringIO(newline="")
    writer=csv.DictWriter(buf,fieldnames=cols,delimiter="|",
                          extrasaction="ignore",lineterminator="\n")
    writer.writeheader()
    writer.writerows(data)
    dat=buf.getvalue().encode("utf-8")
    member=m20.PINNED[ident][2]
    out=io.BytesIO()
    with ZipFile(out,"w",compression=ZIP_DEFLATED) as z:
        z.writestr(member,dat)
        z.writestr(member.replace(".dat","_FIELDS.txt"),b"Test metadata only\n")
        z.writestr(member.replace(".dat","_README.txt"),b"Test README\n")
    return out.getvalue(),dat


def synthetic_inspect(ident="2023_published",data=None, corrupt_sha=False):
    raw,dat=fake_zip(ident,data)
    meta=m20.PINNED[ident]
    updated=("f"*64 if corrupt_sha else sha256(raw).hexdigest(),
             len(raw),meta[2],len(dat),3,meta[-1])
    with patch.dict(m20.PINNED,{ident:updated}):
        return m20.inspect_2023_zip(raw,source={"id":ident,"url":m20.URLS[ident]})


class HistoricalLineageTests(unittest.TestCase):
    def test_pinned_manifest_origin_and_2022_hold(self):
        self.assertEqual(m20._git_blob_sha1(m20.BOOK.read_bytes()),
                         m20.EXPECTED_BOOK_BLOB_SHA1)
        self.assertEqual(m20.validate_manifest(book(),as_of=TODAY),[])
        self.assertFalse(book()["source_year_2022_original_reproduced"])
        self.assertEqual(len(book()["sources"]),2)

    def test_historical_reference_values_and_2024_growth(self):
        out=m20.report_shell(as_of=TODAY)
        self.assertEqual(out["2022_m18_historical_ltl_thousand_usd_unverified_primary"],65688461)
        self.assertEqual(out["2023_national_ltl_thousand_usd"],64651167)
        self.assertEqual(out["2024_national_ltl_thousand_usd"],65096292)
        self.assertEqual(out["2023_to_2024_nominal_change_pct"],"0.69")
        self.assertFalse(out["2022_to_2024_cagr_or_2022_to_2023_growth_promotion_allowed"])
        self.assertEqual(out["status"],m20.OFFLINE)
        self.assertFalse(out["original_2023_and_2024_replayed_this_run"])
        self.assertEqual(out["original_2023_archive_replays"],[])

    def test_no_real_business_claims_or_new_labs(self):
        out=m20.report_shell(as_of=TODAY)
        self.assertEqual(out["lab"],14)
        self.assertFalse(out["new_lab_created"])
        self.assertEqual(out["actual_paid_ltl_invoices_observed"],0)
        self.assertIsNone(out["customer_billing_error_rate_pct"])
        self.assertIsNone(out["actual_cash_recovered_usd"])
        self.assertIsNone(out["recoverable_freight_audit_tam_usd"])
        self.assertFalse(out["marketing_contact_or_external_claims_authorized"])
        self.assertTrue(out["18_pilot_approval_requirements_unmet"])
        self.assertFalse(out["source_family_is_independent_crosscheck"])

    def test_synthetic_national_2023_source_rows_for_both_source_formats(self):
        a=m20.select_national_2023(rows("2023_published"),naics_field="NAICS2017")
        b=m20.select_national_2023(rows("2023_timeseries"),naics_field="NAICS")
        self.assertEqual(a,b)
        self.assertEqual([x["revenue_thousand_usd"] for x in a],
                         [406651010,163025116,64651167])
        self.assertEqual([x["published_cv_pct"] for x in a],["0.6","1.1","0.9"])

    def test_synthetic_zip_can_pass_only_with_replaced_test_fingerprints(self):
        for ident in ("2023_published","2023_timeseries"):
            verified=synthetic_inspect(ident)
            self.assertEqual(verified["source_rows_total"],3)
            self.assertEqual(len(verified["source_2023_naics_rows"]),3)
            self.assertEqual(verified["source_id"],ident)
            self.assertFalse(verified["government_publisher_digitally_signed_bytes"])

    def test_original_zip_hash_rejects_changed_source_even_if_rows_parse(self):
        for ident in ("2023_published","2023_timeseries"):
            with self.assertRaisesRegex(ValueError,"M20_OFFICIAL_ZIP_SHA256_CHANGED"):
                synthetic_inspect(ident,corrupt_sha=True)

    def test_original_zip_size_rejected(self):
        ident="2023_published"
        raw,_=fake_zip(ident)
        with self.assertRaisesRegex(ValueError,"M20_OFFICIAL_ZIP_BYTE_LENGTH_MISMATCH"):
            m20.inspect_2023_zip(raw,source={"id":ident,"url":m20.URLS[ident]})

    def test_one_changed_revenue_is_not_rounded_into_verified(self):
        for ident in ("2023_published","2023_timeseries"):
            rr=rows(ident)
            rr[2]["RCPT_TOT_VAL"]="64651168"
            with self.assertRaisesRegex(ValueError,"M20_FRED_CENSUS_REVENUE_DISAGREEMENT"):
                m20.select_national_2023(rr,naics_field=m20.PINNED[ident][-1])

    def test_missing_duplicate_key_rejected(self):
        for ident in ("2023_published","2023_timeseries"):
            key=m20.PINNED[ident][-1]
            rr=rows(ident)
            with self.assertRaisesRegex(ValueError,"M20_CENSUS_2023_NAICS_INCOMPLETE"):
                m20.select_national_2023(rr[:2],naics_field=key)
            rr.append(deepcopy(rr[0]))
            with self.assertRaisesRegex(ValueError,"M20_DUPLICATE_NATIONAL_INDUSTRY_SOURCE_ROW"):
                m20.select_national_2023(rr,naics_field=key)

    def test_non_2023_or_non_national_rows_fail_to_credit(self):
        for attr,value in (
            ("YEAR","2022"), ("ST","42"),("GEO_ID","fake"),
            ("GEO_LABEL","Pennsylvania"),("TYPOP","01"),("TAXSTAT","01"),
            ("#GEOTYPE","02"),
        ):
            rr=rows()
            rr[2][attr]=value
            with self.assertRaisesRegex(ValueError,"M20_CENSUS_2023_NAICS_INCOMPLETE",msg=attr):
                m20.select_national_2023(rr,naics_field="NAICS2017")

    def test_suppressed_or_nonpublic_cv_rejected(self):
        for field in ("GEO_ID_F","NAICS2017_F","RCPT_TOT_VAL_F","RCPT_TOT_CV_F"):
            rr=rows()
            rr[2][field]="S"
            with self.assertRaisesRegex(ValueError,"M20_CENSUS_ESTIMATE_SUPPRESSED_OR_FLAGGED",msg=field):
                m20.select_national_2023(rr,naics_field="NAICS2017")
        for val in ("S", ".", "", "-1", "5e30", "1000"):
            rr=rows()
            rr[1]["RCPT_TOT_CV"]=val
            with self.assertRaises(ValueError,msg=str(val)):
                m20.select_national_2023(rr,naics_field="NAICS2017")

    def test_counterfeit_units_and_2022_substitution_not_verified(self):
        for val in ("64651167000","64651.167","0","-1","$64651167",""):
            rr=rows()
            rr[2]["RCPT_TOT_VAL"]=val
            with self.assertRaises(ValueError,msg=val):
                m20.select_national_2023(rr,naics_field="NAICS2017")

    def test_changed_2023_naics_labels_or_population_rejected(self):
        for key,value in (
            ("NAICS2017_LABEL","Customer shipments"),
            ("NAICS2017_F","S"),
            ("TAXSTAT_LABEL","Tax-exempt establishments only"),
            ("TYPOP_LABEL","Individuals"),
        ):
            rr=rows()
            rr[2][key]=value
            with self.assertRaises(ValueError,msg=key):
                m20.select_national_2023(rr,naics_field="NAICS2017")

    def test_original_source_inventory_cannot_be_renamed_or_replaced(self):
        for ident in ("2023_published","2023_timeseries"):
            b=book()
            obj=next(x for x in b["sources"] if x["id"]==ident)
            for key,value in (
                ("sha256","a"*64),("url","https://example.com/fake.zip"),
                ("archive_bytes",100),("dat_rows",3),("naics_field","NAICS2022"),
            ):
                old=obj[key]
                obj[key]=value
                self.assertTrue(m20.validate_manifest(b,as_of=TODAY),key)
                obj[key]=old

    def test_false_original_2022_and_marketing_claims_fail(self):
        for key in (
            "source_year_2022_original_reproduced","historical_2022_census_original_replay",
            "industry_revenue_equals_customer_spend","real_overcharges_or_cash_recovery_proven",
            "buyer_demand_proven","human_pilot_18_gates_completed","publication_or_marketing_allowed",
            "customer_or_carrier_data_used","new_lab_created",
        ):
            b=book()
            b[key]=True
            self.assertIn("M20_UNSUPPORTED_COMMERCIAL_OR_SOURCE_PROMOTION",
                          "; ".join(m20.validate_manifest(b,as_of=TODAY)),key)

    def test_modified_historical_values_or_wrong_year_fail(self):
        b=book()
        b["selected_industries"][2]["revenue_thousand_usd"]=65688461
        self.assertTrue(m20.validate_manifest(b,as_of=TODAY))
        b=book()
        b["referenced_m18_2022_historical_ltl_thousand_usd"]=0
        self.assertTrue(m20.validate_manifest(b,as_of=TODAY))
        self.assertTrue(m20.validate_manifest(book(),as_of=date(2026,10,10)))

    def test_unapproved_web_endpoint_cannot_be_downloaded(self):
        with self.assertRaisesRegex(ValueError,"M20_UNAUTHORIZED_REMOTE_SOURCE_ID"):
            m20._download_exact("https://attacker.example/data")

    def test_all_three_current_archives_required_for_certification(self):
        with self.assertRaisesRegex(ValueError,"M20_ALL_2023_AND_2024_CENSUS_ARCHIVES_REQUIRED"):
            m20.verify_originals(as_of=TODAY,archives={"2023_published":b"fake"})

    def test_requested_network_timeout_yields_blocked_but_not_verified(self):
        with tempfile.TemporaryDirectory() as root:
            with patch("sys.argv",["module","--fetch-originals","--as-of-date","2026-10-11","--out",root]):
                with patch.object(m20,"_download_exact",side_effect=TimeoutError("synthetic")):
                    m20.main()
            report=json.loads((Path(root)/"aies_historical_lineage.json").read_text())
            self.assertEqual(report["status"],m20.BLOCKED)
            self.assertEqual(report["original_2023_archive_replays"],[])
            self.assertFalse(report["original_2023_and_2024_replayed_this_run"])
            self.assertEqual(report["receipt_sha256"],canon_hash({
                k:v for k,v in report.items() if k!="receipt_sha256"
            }))

    def test_tampered_downloaded_bytes_raise_not_network_block(self):
        with tempfile.TemporaryDirectory() as root:
            with patch("sys.argv",["module","--fetch-originals","--as-of-date","2026-10-11","--out",root]):
                with patch.object(m20,"_download_exact",return_value=b"tampered source"):
                    with self.assertRaisesRegex(ValueError,"M20_OFFICIAL_ZIP_BYTE_LENGTH_MISMATCH"):
                        m20.main()

    def test_static_render_escapes_caveats_and_holds_2022(self):
        report=m20.report_shell(as_of=TODAY)
        report["caveat"]="<img src=x onerror=evil()>"
        html=m20.render_html(report)
        self.assertNotIn("<img src=x",html)
        self.assertIn("&lt;img src=x",html)
        self.assertIn("2022",html)
        self.assertIn("not primary replayed",html)


if __name__=="__main__":
    unittest.main()
