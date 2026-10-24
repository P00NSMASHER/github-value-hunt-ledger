"""Public FY2027 SAM archive source and anti-lookahead validation regressions."""
from __future__ import annotations

import copy
import csv
import hashlib
import io
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from freight.capturebrief_sam_fy2027_asof import (
    MAX_ORIGINAL_BYTES, MAX_ORIGINAL_ROWS, REQUIRED_COLUMNS,
    PREVIOUS_PUBLIC_REFERENCE_SHA256, SOURCE_URL, STATUS_OK,
    STATUS_DEGRADED, assess_cross_source_chronology,
    build_receipt, fetch_original, parse_archive, run, validate_receipt,
)
from freight.unified_research_lab import ResearchError, digest

NOW=datetime(2026,10,24,7,0,0,tzinfo=timezone.utc)


def archive(records=None):
    records=records if records is not None else [
        {"NoticeId":"notice-1000", "Sol#":"47QTCA27R001A",
         "PostedDate":"10/10/2026", "Type":"Solicitation", "Active":"No",
         "AAC Code":"47PA01", "Office":"GSA OFFICE 1","Link":"https://sam.gov/x"},
        {"NoticeId":"notice-1001", "Sol#":"47QTCA27R001A",
         "PostedDate":"2026-10-11", "Type":"Amendment", "Active":"No",
         "AAC Code":"47PA01", "Office":"GSA OFFICE 1","Link":"https://sam.gov/y"},
        {"NoticeId":"notice-1002", "Sol#":"DLA0001R0021",
         "PostedDate":"2026-10-18T10:40:00Z", "Type":"Sources Sought", "Active":"Yes",
         "AAC Code":"DLA1", "Office":"DLA OFFICE 2","Link":"https://sam.gov/z"},
    ]
    buf=io.StringIO(newline="")
    cols=["NoticeId","Sol#","PostedDate","Type","Active","AAC Code","Office","Link"]
    writer=csv.DictWriter(buf,fieldnames=cols,lineterminator="\n",extrasaction="ignore")
    writer.writeheader()
    writer.writerows(records)
    return buf.getvalue().encode("utf-8")


def join_sources():
    notice={
        "solicitation_number":"47QTCA27R001A", "agency_code":"47PA01",
        "office":"GSA OFFICE 1", "posted_date":"2026-10-10",
    }
    award={
        "solicitation_identifier":"47QTCA27R001A",
        "matched_issuer_agency_code":"47PA01",
        "matched_issuer_office":"GSA OFFICE 1",
        "award_date_signed":"2026-10-25",
    }
    return notice,award


class SamArchiveAsOfTests(unittest.TestCase):
    def test_pinned_source_and_provenance_respect_historical_observation(self):
        data=archive()
        x=parse_archive(data,observed_at=NOW)
        self.assertEqual(x["source_rows"],3)
        self.assertEqual(x["unique_original_notice_ids"],3)
        self.assertEqual(x["repeated_notice_identifiers"],0)
        self.assertEqual(x["source_rows_with_solicitation"],3)
        self.assertEqual(x["source_rows_with_posted_date"],3)
        self.assertEqual(x["source_rows_posted_after_observation_day"],0)
        self.assertEqual(x["source_issuer_ambiguous_solicitation_families"],0)
        self.assertEqual(x["current_source_size_bytes"],len(data))
        self.assertEqual(x["current_source_sha256"],hashlib.sha256(data).hexdigest())
        self.assertEqual(len(REQUIRED_COLUMNS),8)
        self.assertEqual(MAX_ORIGINAL_ROWS,8000)
        self.assertEqual(MAX_ORIGINAL_BYTES,2_500_000)
        self.assertEqual(len(PREVIOUS_PUBLIC_REFERENCE_SHA256),64)

    def test_issuer_family_and_duplicate_notice_evidence_is_counted_not_promoted(self):
        rows=[
            {"NoticeId":"NOTICE1","Sol#":"SOL-1","PostedDate":"2026-10-15",
             "Type":"Solicitation","Active":"No","AAC Code":"AGY1",
             "Office":"OFFICE-1", "Link":"https://sam.gov/x"},
            {"NoticeId":"NOTICE1","Sol#":"SOL-1","PostedDate":"2026-10-15",
             "Type":"Amendment","Active":"No","AAC Code":"AGY1",
             "Office":"OFFICE-2","Link":"https://sam.gov/x"},
            {"NoticeId":"NOTICE3","Sol#":"SOL-2","PostedDate":"2026-10-25",
             "Type":"Solicitation","Active":"No","AAC Code":"",
             "Office":"","Link":"https://sam.gov/y"},
        ]
        v=parse_archive(archive(rows),observed_at=NOW)
        self.assertEqual(v["source_rows"],3)
        self.assertEqual(v["unique_original_notice_ids"],2)
        self.assertEqual(v["repeated_notice_identifiers"],1)
        self.assertEqual(v["source_issuer_ambiguous_solicitation_families"],2)
        self.assertEqual(v["source_rows_posted_after_observation_day"],1)

    def test_prohibited_raw_identifiers_never_enter_persisted_receipt(self):
        data=archive()
        receipt=build_receipt(observed_at=NOW,fetcher=lambda:data)
        self.assertEqual(receipt["source_status"],STATUS_OK)
        self.assertEqual(receipt["source_rows"],3)
        self.assertEqual(receipt["asof_award_join_candidates_count"],0)
        self.assertEqual(receipt["independently_verified_preaward_opportunity_cases"],0)
        self.assertEqual(receipt["independent_cross_source_award_outcomes"],0)
        self.assertEqual(receipt["fy2027_full_catalog_approved"],False)
        self.assertEqual(receipt["original_archive_bytes_persisted"],0)
        self.assertEqual(receipt["owner_rights_attestation"],"OWNER_ATTESTED_NOT_SOURCE_VERIFIED")
        self.assertEqual(receipt["receipt_sha256"],digest({
            k:v for k,v in receipt.items() if k!="receipt_sha256"}))
        self.assertEqual(receipt["matches_oct19_full_original_byte_digest"],False)
        self.assertNotIn("notice-1000",str(receipt))
        self.assertNotIn("47QTCA27R001A",str(receipt))
        self.assertNotIn("GSA OFFICE 1",str(receipt))
        self.assertNotIn("https://sam.gov/x",str(receipt))
        validate_receipt(receipt,now=NOW)

    def test_source_data_invalid_schema_fails_as_degraded_without_false_zero_coverage(self):
        bad_cases=[
            b"",
            b"NoticeId,Sol#,PostedDate\nx,y,2026-10-23\n",
            b"\xff\xfe\x00",
            archive([{"NoticeId":"","Sol#":"S","PostedDate":"2026-10-22",
                     "Type":"A", "Active":"Yes","AAC Code":"X","Office":"O","Link":"/x"}]),
        ]
        for raw in bad_cases:
            with self.subTest(raw=raw[:15]):
                d=build_receipt(observed_at=NOW,fetcher=lambda:raw)
                self.assertEqual(d["source_status"],STATUS_DEGRADED)
                self.assertEqual(d["source_rows"],0)
                self.assertEqual(d["independent_cross_source_award_outcomes"],0)
                self.assertIsNone(d["current_source_sha256"])
                self.assertEqual(len(d["source_error_codes"]),1)
                validate_receipt(d,now=NOW)

    def test_archive_source_sample_and_replay_is_daily_and_tamper_evident(self):
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/"sam-asof.json"
            count=[]
            def fetcher():
                count.append("public GET")
                return archive()
            first=run(output=target,fetcher=fetcher,now=NOW)
            self.assertEqual(first["source_rows"],3)
            self.assertEqual(len(count),1)
            original=target.read_bytes()
            same=run(output=target,fetcher=fetcher,now=NOW)
            self.assertFalse(same["verified"])
            self.assertEqual(len(count),1)
            self.assertEqual(original,target.read_bytes())
            self.assertTrue(run(output=target,now=NOW,verify_only=True)["verified"])
            altered=json.loads(target.read_text())
            altered["independently_verified_preaward_opportunity_cases"]=99
            altered["receipt_sha256"]=digest({
                k:v for k,v in altered.items() if k!="receipt_sha256"})
            target.write_text(json.dumps(altered))
            with self.assertRaisesRegex(ResearchError,"ARCHIVE_UNAPPROVED_EVIDENCE_PROMOTION"):
                run(output=target,now=NOW,verify_only=True)
            repaired=run(output=target,now=NOW,fetcher=fetcher)
            self.assertEqual(repaired["source_status"],STATUS_OK)
            self.assertEqual(len(count),2)
            self.assertFalse(json.loads(target.read_text())[
                "fy2027_full_catalog_approved"])

    def test_archive_asof_chronology_blocks_lookahead_and_mixed_agencies(self):
        notice,award=join_sources()
        source_time=datetime(2026,10,24,3,0,tzinfo=timezone.utc)
        self.assertEqual(assess_cross_source_chronology(
            notice,award,source_observed_at=source_time),
            "PREAWARD_CHRONOLOGY_CANDIDATE_ONLY")
        before=dict(award,award_date_signed="2026-10-22")
        self.assertEqual(assess_cross_source_chronology(
            notice,before,source_observed_at=source_time),
            "ARCHIVE_OBSERVED_AFTER_AWARD_NOT_ASOF")
        future=dict(notice,posted_date="2026-10-26")
        self.assertEqual(assess_cross_source_chronology(
            future,award,source_observed_at=source_time),
            "FUTURE_POSTED_NOTICE_NOT_PREAWARD")
        cross_agency=dict(award,matched_issuer_agency_code="MIL1")
        self.assertEqual(assess_cross_source_chronology(
            notice,cross_agency,source_observed_at=source_time),
            "ISSUER_CONFLICT")
        no_office=dict(award,matched_issuer_office=None)
        self.assertEqual(assess_cross_source_chronology(
            notice,no_office,source_observed_at=source_time),
            "ISSUER_NOT_INDEPENDENTLY_MATCHED")
        other_id=dict(award,solicitation_identifier="UNRELATED")
        self.assertEqual(assess_cross_source_chronology(
            notice,other_id,source_observed_at=source_time),
            "UNMATCHED_OR_UNKNOWN")
        unknown_date=dict(award,award_date_signed=None)
        self.assertEqual(assess_cross_source_chronology(
            notice,unknown_date,source_observed_at=source_time),
            "SOURCE_DATE_UNKNOWN")

    def test_uncertain_same_day_history_cannot_count_as_known_preaward(self):
        notice,award=join_sources()
        award["award_date_signed"]="2026-10-24"
        self.assertNotEqual(assess_cross_source_chronology(
            notice,award,source_observed_at=NOW),"PREAWARD_CHRONOLOGY_CANDIDATE_ONLY")

    def test_forged_sha_counts_source_scope_and_rights_fail_when_rehashed(self):
        report=build_receipt(observed_at=NOW,fetcher=archive)
        alterations=(
            ("fy2027_full_catalog_approved",True),
            ("source_specific_reuse_rights_verified",True),
            ("source_rows",9000),
            ("unique_original_notice_ids",99),
            ("asof_award_join_candidates_count",1),
            ("independent_cross_source_award_outcomes",1),
            ("independently_verified_preaward_opportunity_cases",1),
            ("owner_rights_attestation","ALL_RIGHTS_VERIFIED"),
            ("original_archive_bytes_persisted",1),
            ("source","https://evil.invalid/other"),
            ("matches_oct19_full_original_byte_digest",True),
            ("source_error_codes",["SECRET_TOKEN=ABC"]),
            ("source_status",STATUS_DEGRADED),
        )
        for field,new_value in alterations:
            with self.subTest(field=field):
                altered=copy.deepcopy(report)
                altered[field]=new_value
                altered["receipt_sha256"]=digest({
                    k:v for k,v in altered.items() if k!="receipt_sha256"})
                with self.assertRaises(ResearchError):
                    validate_receipt(altered,now=NOW)

    def test_read_only_fixed_public_origin_no_redirect_and_no_unbounded_transfer(self):
        from freight.capturebrief_sam_fy2027_asof import SOURCE_URL
        data=archive()
        trace=[]
        class Response:
            status=200
            headers={"Content-Type":"text/csv",
                     "Content-Encoding":"identity","Content-Length":str(len(data))}
            def __enter__(self):return self
            def __exit__(self,*_):return None
            def geturl(self):return SOURCE_URL
            def read(self,n):
                trace.append(n)
                return data
        class Opener:
            def open(self,req,timeout):
                trace.append((req.get_method(),req.full_url,timeout))
                return Response()
        with patch("freight.capturebrief_sam_fy2027_asof.global_dns"), \
             patch("freight.capturebrief_sam_fy2027_asof.build_opener",
                   return_value=Opener()):
            self.assertEqual(fetch_original(),data)
        self.assertEqual(trace[0],("GET",SOURCE_URL,15))
        self.assertEqual(trace[1],MAX_ORIGINAL_BYTES+1)

    def test_truncated_response_cannot_be_treated_as_complete_bytes(self):
        data=archive()
        class Response:
            status=200
            headers={"Content-Type":"text/csv",
                     "Content-Encoding":"identity","Content-Length":str(len(data)+10)}
            def __enter__(self):return self
            def __exit__(self,*_):return None
            def geturl(self):return SOURCE_URL
            def read(self,n):return data
        class Opener:
            def open(self,req,timeout):return Response()
        with patch("freight.capturebrief_sam_fy2027_asof.global_dns"), \
             patch("freight.capturebrief_sam_fy2027_asof.build_opener",
                   return_value=Opener()):
            with self.assertRaisesRegex(ResearchError,"SOURCE_INCOMPLETE"):
                fetch_original()


if __name__=="__main__":
    unittest.main()
