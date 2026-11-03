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
    STATUS_DEGRADED, STATUS_PARTIAL, assess_cross_source_chronology,
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
        self.assertEqual(MAX_ORIGINAL_BYTES,12_000_000)
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

    def test_one_malformed_solicitation_control_is_quarantined_not_silently_cleaned(self):
        rows=[
            {"NoticeId":"notice-1010", "Sol#":"PAPER\nINJECTED-ISSUE",
             "PostedDate":"2026-10-12", "Type":"Solicitation", "Active":"No",
             "AAC Code":"GSA1", "Office":"TEST OFFICE", "Link":"https://sam.gov/x"},
            {"NoticeId":"notice-1011", "Sol#":"47QTCA27R0032",
             "PostedDate":"2026-10-12", "Type":"Solicitation", "Active":"No",
             "AAC Code":"GSA1", "Office":"TEST OFFICE", "Link":"https://sam.gov/y"},
        ]
        original=archive(rows)
        observed=parse_archive(original,observed_at=NOW)
        self.assertEqual(observed["source_rows"],2)
        self.assertEqual(observed["unique_original_notice_ids"],2)
        self.assertEqual(observed["source_rows_quarantined_solicitation_control"],1)
        self.assertEqual(observed["source_rows_with_solicitation"],1)
        self.assertEqual(observed["current_source_sha256"],
                         hashlib.sha256(original).hexdigest())
        doc=build_receipt(observed_at=NOW,fetcher=lambda:original)
        self.assertEqual(doc["source_status"],STATUS_PARTIAL)
        self.assertEqual(doc["source_error_codes"],
                         ["SOURCE_SOLICITATION_CONTROL_QUARANTINED"])
        self.assertEqual(doc["source_rows"],2)
        self.assertEqual(doc["source_rows_quarantined_solicitation_control"],1)
        self.assertIsNotNone(doc["current_source_sha256"])
        self.assertEqual(doc["original_opportunity_ids_persisted"],0)
        self.assertEqual(doc["independent_cross_source_award_outcomes"],0)
        self.assertNotIn("INJECTED-ISSUE",str(doc))
        validate_receipt(doc,now=NOW)
        tampered=copy.deepcopy(doc)
        tampered["source_rows_quarantined_solicitation_control"]=0
        tampered["receipt_sha256"]=digest({
            k:v for k,v in tampered.items() if k!="receipt_sha256"})
        with self.assertRaises(ResearchError):
            validate_receipt(tampered,now=NOW)

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

    def test_fy2027_archive_growth_is_bounded_not_silently_zeroed(self):
        # Source-bound observed failure; generated rows below are SYNTHETIC.
        pack_path = Path(__file__).with_name("fixtures") / (
            "capturebrief_fy2027_archive_growth_boundary_v1.json"
        )
        pack = json.loads(pack_path.read_text(encoding="utf-8"))
        self.assertEqual(pack["schema_version"], 1)
        self.assertEqual(pack["observation"]["result"], "SOURCE_TOO_LARGE")
        self.assertIsNone(pack["observation"]["source_byte_sha256"])
        self.assertEqual(pack["observation"]["source_rows_scored"], 0)
        self.assertFalse(pack["rights_and_truth"]["commercial_scoring_allowed"])
        self.assertEqual(pack["rights_and_truth"]["independent_cross_source_outcomes"], 0)
        self.assertEqual(MAX_ORIGINAL_BYTES, pack["proposal"]["bounded_limit_bytes"])
        self.assertEqual(MAX_ORIGINAL_ROWS, pack["proposal"]["maximum_csv_rows"])
        # Original publisher HEAD metadata, not an original-byte hash.
        head = pack["current_public_head_observation"]
        self.assertEqual(head["http_method"], "HEAD")
        self.assertEqual(head["http_status"], 200)
        self.assertEqual(head["reported_content_length_bytes"], 8_833_904)
        self.assertGreater(head["reported_content_length_bytes"], 8_000_000)
        self.assertLess(head["reported_content_length_bytes"], MAX_ORIGINAL_BYTES)
        self.assertIsNone(head["original_body_sha256"])
        self.assertFalse(head["original_body_read"])
        self.assertEqual(head["independently_verified_award_labels"], 0)


        columns = ["NoticeId", "Sol#", "PostedDate", "Type", "Active",
                   "AAC Code", "Office", "Link", "Description"]
        buf = io.StringIO(newline="")
        writer = csv.DictWriter(buf, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        for i in range(256):
            writer.writerow({
                "NoticeId": f"SYNTHETIC-NOTICE-{i:04d}",
                "Sol#": f"SYNTHETIC-SOL-{i:04d}",
                "PostedDate": "2026-10-20",
                "Type": "Solicitation", "Active": "No",
                "AAC Code": "FAKE", "Office": "FAKE TEST OFFICE",
                "Link": "https://sam.gov/synthetic-not-real",
                "Description": "X" * 10500,
            })
        fabricated = buf.getvalue().encode("utf-8")
        self.assertGreater(len(fabricated), pack["observation"]["previous_bounded_limit_bytes"])
        self.assertLess(len(fabricated), MAX_ORIGINAL_BYTES)

        class CompleteResponse:
            status = 200
            headers = {
                "Content-Type": "text/csv",
                "Content-Encoding": "identity",
                "Content-Length": str(len(fabricated)),
            }
            def __enter__(self): return self
            def __exit__(self, *_): return None
            def geturl(self): return SOURCE_URL
            def read(self, n):
                self_outer.assertEqual(n, MAX_ORIGINAL_BYTES + 1)
                return fabricated

        self_outer = self
        class TooLargeResponse(CompleteResponse):
            headers = {
                "Content-Type": "text/csv",
                "Content-Encoding": "identity",
                "Content-Length": str(MAX_ORIGINAL_BYTES + 1),
            }
            def read(self, n):
                raise AssertionError("oversize response must fail before reading")

        class Opener:
            def __init__(self, response): self.response = response
            def open(self, req, timeout):
                self_outer.assertEqual(req.get_method(), "GET")
                self_outer.assertEqual(req.full_url, SOURCE_URL)
                return self.response

        with patch("freight.capturebrief_sam_fy2027_asof.global_dns"), \
             patch("freight.capturebrief_sam_fy2027_asof.build_opener",
                   return_value=Opener(CompleteResponse())):
            self.assertEqual(fetch_original(), fabricated)
        receipt = build_receipt(observed_at=NOW, fetcher=lambda: fabricated)
        self.assertEqual(receipt["source_status"], STATUS_OK)
        self.assertEqual(receipt["source_rows"], 256)
        self.assertEqual(receipt["current_source_sha256"],
                         hashlib.sha256(fabricated).hexdigest())
        self.assertEqual(receipt["independent_cross_source_award_outcomes"], 0)
        self.assertEqual(receipt["original_archive_bytes_persisted"], 0)
        validate_receipt(receipt, now=NOW)
        with patch("freight.capturebrief_sam_fy2027_asof.global_dns"), \
             patch("freight.capturebrief_sam_fy2027_asof.build_opener",
                   return_value=Opener(TooLargeResponse())):
            with self.assertRaisesRegex(ResearchError, "SOURCE_TOO_LARGE"):
                fetch_original()

    def test_one_shot_original_body_manifest_is_pinned_not_a_scoring_benchmark(self):
        # The actual hosted original-source run is NOT a synthetic source row,
        # an independent award adjudication or a current scheduled-writer receipt.
        fixture_root = Path(__file__).with_name("fixtures")
        manifest = json.loads((fixture_root /
            "sam_fy2027_original_body_observation_20261101_v1.json"
        ).read_text(encoding="utf-8"))
        historical = json.loads((fixture_root /
            "capturebrief_fy2027_archive_growth_boundary_v1.json"
        ).read_text(encoding="utf-8"))

        def canonical_checksum(document):
            payload = {k: v for k, v in document.items()
                       if k != "manifest_sha256"}
            raw = json.dumps(payload, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=False).encode("utf-8")
            return hashlib.sha256(raw).hexdigest()

        self.assertEqual(manifest["schema_version"], 1)
        self.assertEqual(manifest["manifest_sha256"],
                         canonical_checksum(manifest))
        self.assertEqual(manifest["source_url"], SOURCE_URL)
        observation = manifest["observation"]
        proof = manifest["proof"]
        self.assertEqual(proof["actual_execution"],
                         "GITHUB_ACTIONS_ONE_SHOT_FULL_ORIGINAL_READ")
        self.assertEqual(proof["workflow_run_id"], 41351922492)
        self.assertEqual(proof["workflow_job_id"], 124983775762)
        self.assertEqual(proof["source_reader_git_blob_sha1"],
                         "2a31d52b5feb2882f3a86c578e5e17299ee901b4")
        self.assertEqual(observation["original_bytes"], 8_833_904)
        self.assertEqual(observation["original_body_sha256"],
                         "980840a8d53ad92caec672c35910c61908a96b5f17e9234c667294001479662b")
        self.assertEqual(observation["original_bytes"],
                         historical["current_public_head_observation"]
                                   ["reported_content_length_bytes"])
        self.assertEqual(observation["original_csv_rows"], 5_139)
        self.assertEqual(observation["distinct_notice_ids"], 5_139)
        self.assertEqual(observation["status"], STATUS_PARTIAL)
        self.assertEqual(observation["quarantined_solicitation_control_fields"], 1)
        self.assertFalse(observation["publisher_etag_is_sha256"])
        self.assertNotEqual(observation["publisher_etag"].strip('"'),
                            observation["original_body_sha256"])
        self.assertFalse(proof["original_bytes_retained_in_repo"])
        self.assertFalse(proof["original_notice_identifiers_retained_in_repo"])
        self.assertFalse(proof["source_hash_independently_recomputed_this_checkpoint"])

        labels = manifest["ground_truth"]
        self.assertEqual(labels["independent_held_out_award_positive_cases"], 0)
        self.assertEqual(labels["independent_held_out_award_negative_cases"], 0)
        self.assertEqual(labels["verified_notice_to_award_cross_source_cases"], 0)
        self.assertEqual(labels["scoring_benchmark"], "NO_VALIDATED_BENCHMARK")
        self.assertFalse(labels["approved_for_customer_scoring"])
        self.assertEqual(labels["source_specific_commercial_reuse"],
                         "UNKNOWN_NOT_CLEARED")
        self.assertEqual(labels["live_scheduled_writer_receipt"],
                         "NOT_VERIFIED_BY_ONE_SHOT_PROOF")
        controls = manifest["synthetic_negative_controls"]
        self.assertEqual(len(controls), 5)
        self.assertEqual(len({c["id"] for c in controls}), 5)
        self.assertTrue(all(c["id"].startswith("SYNTHETIC_")
                            and c["independent_ground_truth"] is False
                            for c in controls))
        # The control descriptions must retain their exact fail-closed
        # outcomes. Merely having five SYNTHETIC_ strings is not a gate.
        expected_control_outcomes = {
            "SYNTHETIC_BODY_HASH_IS_NOT_AWARD_LABEL":
                "NO_VALIDATED_BENCHMARK",
            "SYNTHETIC_ETAG_IS_NOT_SHA256":
                "REJECT_ETAG_AS_BODY_DIGEST",
            "SYNTHETIC_HEAD_LENGTH_IS_NOT_BODY_PROOF":
                "REQUIRE_FULL_ORIGINAL_BODY_READ",
            "SYNTHETIC_SINGLE_ARCHIVE_IS_NOT_ASOF_HISTORY":
                "HISTORICAL_VISIBILITY_UNKNOWN",
            "SYNTHETIC_QUARANTINED_FIELD_IS_NOT_CLEAN_LABEL":
                "QUARANTINE_NOT_ADJUDICATION",
        }
        self.assertEqual(
            {c["id"]: c["expected"] for c in controls},
            expected_control_outcomes,
        )
        head_only = historical["current_public_head_observation"]
        self.assertFalse(head_only["original_body_read"])
        self.assertIsNone(head_only["original_body_sha256"])
        self.assertEqual(labels["historical_version_completeness"],
                         "UNKNOWN_NOT_ESTABLISHED")
        self.assertGreater(
            observation["quarantined_solicitation_control_fields"], 0
        )

        # Tampering with original bytes or inventing positive labels makes
        # the pinned manifest digest fail, even if its source shape is valid.
        for section, field, replacement in (
            ("observation", "original_body_sha256", "0" * 64),
            ("ground_truth", "independent_held_out_award_positive_cases", 5_139),
            ("ground_truth", "approved_for_customer_scoring", True),
        ):
            forged = copy.deepcopy(manifest)
            forged[section][field] = replacement
            self.assertNotEqual(canonical_checksum(forged),
                                forged["manifest_sha256"])

    def test_official_daily_public_extract_is_not_archived_fy2027_ground_truth(self):
        pack = json.loads((Path(__file__).with_name('fixtures') /
            'capturebrief_fy2027_archive_growth_boundary_v1.json').read_text())
        lead = pack['adjacent_original_source_discovery']
        self.assertEqual(lead['catalog_item'], 'ContractOpportunitiesFullCSV.csv')
        self.assertTrue(lead['catalog_url'].startswith('https://sam.gov/data-services/'))
        self.assertEqual(lead['cohort'], 'CURRENT_DAILY_PUBLIC_NOT_FY2027_ARCHIVED_HISTORY')
        self.assertNotEqual(lead['cohort'], pack['source_effective_scope'])
        self.assertFalse(lead['source_bytes_acquired'])
        self.assertIsNone(lead['source_response_sha256'])
        self.assertIsNone(lead['source_row_count'])
        self.assertEqual(lead['independent_positive_labels'], 0)
        self.assertEqual(lead['independent_negative_labels'], 0)
        self.assertIn('COMMERCIAL_REUSE_NOT_CLEARED', lead['rights_classification'])
        self.assertIn('NO_ACTIVE_DAILY_TO_ARCHIVE_CHRONOLOGY_SUBSTITUTION',
                      lead['compliance_controls'])
        self.assertFalse(pack['rights_and_truth']['commercial_scoring_allowed'])

    def test_degraded_same_day_cache_and_next_utc_day_replay_are_source_bounded(self):
        # Wholly SYNTHETIC controls. Never contacts SAM.gov or persists raw IDs.
        pack_path = Path(__file__).with_name("fixtures") / (
            "capturebrief_fy2027_archive_growth_boundary_v1.json"
        )
        pack = json.loads(pack_path.read_text(encoding="utf-8"))
        controls = {case["id"]: case for case in pack["synthetic_controls"]}
        self.assertEqual(
            controls["SYNTHETIC_DEGRADED_RECEIPT_SAME_UTC_DAY"]["expected"],
            "CACHE_DEGRADED_SAME_UTC_DAY_NEXT_DAY_BOUNDED_FETCH_ELIGIBLE",
        )
        self.assertIsNone(
            controls["SYNTHETIC_SAM_SAME_ORIGIN_AWARD_METADATA"]["true_independent_award_label"]
        )
        self.assertEqual(
            pack["documentation_controls"]["original_notice_version_history_completeness"],
            "UNKNOWN_NOT_VERIFIED",
        )
        self.assertFalse(
            pack["documentation_controls"]["original_source_bytes_retrieved_by_this_update"]
        )
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "synthetic-failed-receipt.json"
            calls = []

            def unavailable():
                calls.append("SYNTHETIC-GET")
                raise ResearchError("SOURCE_TOO_LARGE")

            first_at = datetime(2026, 10, 30, 2, 11, 33, tzinfo=timezone.utc)
            first = run(output=target, fetcher=unavailable, now=first_at)
            self.assertEqual(first["source_status"], STATUS_DEGRADED)
            self.assertEqual(first["source_error_codes"], ["SOURCE_TOO_LARGE"])
            original_receipt = target.read_bytes()

            def unexpected_fetch():
                raise AssertionError("same UTC day must not refetch valid degraded receipt")

            same_day = datetime(2026, 10, 30, 23, 59, 59, tzinfo=timezone.utc)
            cached = run(output=target, fetcher=unexpected_fetch, now=same_day)
            self.assertEqual(cached["source_error_codes"], ["SOURCE_TOO_LARGE"])
            self.assertEqual(target.read_bytes(), original_receipt)
            self.assertEqual(calls, ["SYNTHETIC-GET"])

            def next_day_synthetic_fetch():
                calls.append("SYNTHETIC-GET")
                return archive()

            next_utc_day = datetime(2026, 10, 31, 0, 0, 1, tzinfo=timezone.utc)
            new_receipt = run(output=target, fetcher=next_day_synthetic_fetch,
                              now=next_utc_day)
            self.assertEqual(new_receipt["source_status"], STATUS_OK)
            self.assertEqual(new_receipt["source_rows"], 3)
            self.assertEqual(calls, ["SYNTHETIC-GET", "SYNTHETIC-GET"])
            self.assertEqual(
                json.loads(target.read_text(encoding="utf-8"))[
                    "independent_cross_source_award_outcomes"], 0,
            )

    def test_unframed_csv_prefix_metadata_is_not_promoted_to_verified_truth(self):
        pack_path = Path(__file__).with_name("fixtures") / (
            "capturebrief_fy2027_archive_growth_boundary_v1.json"
        )
        pack = json.loads(pack_path.read_text(encoding="utf-8"))
        controls = {x["id"]: x for x in pack["synthetic_controls"]}
        case = controls["SYNTHETIC_UNFRAMED_COMPLETE_CSV_PREFIX"]
        self.assertEqual(case["expected"], "SOURCE_INCOMPLETE")
        self.assertEqual(case["candidate_state"], "REPAIRED_BY_EXPLICIT_TRANSPORT_FRAMING")
        self.assertIsNone(case["true_independent_award_label"])
        self.assertFalse(pack["rights_and_truth"]["commercial_scoring_allowed"])
        self.assertEqual(pack["documentation_controls"]["current_source_framing"],
                         "UNKNOWN_NO_NEW_SOURCE_READ")

    def test_unframed_csv_prefix_is_rejected_even_if_csv_schema_parses(self):
        # Synthetic valid CSV prefix with no HTTP completion proof.
        full = archive()
        prefix = b"".join(full.splitlines(keepends=True)[:-1])
        self.assertLess(len(prefix), len(full))
        self.assertEqual(parse_archive(prefix, observed_at=NOW)["source_rows"], 2)

        class Response:
            status = 200
            headers = {"Content-Type": "text/csv",
                       "Content-Encoding": "identity"}
            def __enter__(self): return self
            def __exit__(self, *_): return None
            def geturl(self): return SOURCE_URL
            def read(self, n): return prefix

        class Opener:
            def open(self, req, timeout): return Response()

        with patch("freight.capturebrief_sam_fy2027_asof.global_dns"), \
             patch("freight.capturebrief_sam_fy2027_asof.build_opener",
                   return_value=Opener()):
            with self.assertRaisesRegex(ResearchError, "SOURCE_INCOMPLETE"):
                fetch_original()

    def test_complete_chunked_http11_transfer_remains_accepted(self):
        # Real HTTP/1.1 framing semantics, wholly SYNTHETIC bytes, no network.
        # Positive compatibility guard for the two unresolved completeness xfails.
        from http.client import HTTPResponse
        from urllib.response import addinfourl

        pack_path = Path(__file__).with_name("fixtures") / (
            "capturebrief_fy2027_archive_growth_boundary_v1.json"
        )
        pack = json.loads(pack_path.read_text(encoding="utf-8"))
        case = next(x for x in pack["synthetic_controls"]
                    if x["id"] == "SYNTHETIC_COMPLETE_CHUNKED_TRANSFER")
        self.assertEqual(case["expected"], STATUS_OK)
        self.assertIsNone(case["true_independent_award_label"])
        self.assertFalse(pack["rights_and_truth"]["commercial_scoring_allowed"])

        source = archive()
        wire = (
            b"HTTP/1.1 200 OK\r\n"
            b"Content-Type: text/csv\r\n"
            b"Content-Encoding: identity\r\n"
            b"Transfer-Encoding: chunked\r\n\r\n"
            + f"{len(source):X}\r\n".encode("ascii")
            + source + b"\r\n0\r\n\r\n"
        )
        self_outer = self

        class Socket:
            def makefile(self, mode):
                self_outer.assertEqual(mode, "rb")
                return io.BytesIO(wire)

        raw_http = HTTPResponse(Socket())
        raw_http.begin()
        self.assertTrue(raw_http.chunked)
        self.assertIsNone(raw_http.length)

        class Opener:
            def open(self, req, timeout):
                self_outer.assertEqual(req.full_url, SOURCE_URL)
                self_outer.assertEqual(req.get_method(), "GET")
                return addinfourl(raw_http, raw_http.headers, SOURCE_URL,
                                   raw_http.status)

        with patch("freight.capturebrief_sam_fy2027_asof.global_dns"), \
             patch("freight.capturebrief_sam_fy2027_asof.build_opener",
                   return_value=Opener()):
            self.assertEqual(fetch_original(), source)

        observed = build_receipt(observed_at=NOW, fetcher=lambda: source)
        self.assertEqual(observed["source_status"], STATUS_OK)
        self.assertEqual(observed["source_rows"], 3)
        self.assertEqual(observed["independent_cross_source_award_outcomes"], 0)
        self.assertEqual(observed["original_opportunity_ids_persisted"], 0)

    def test_chunked_incomplete_read_degrades_not_uncaught(self):
        # SYNTHETIC interrupted HTTP/1.1 chunked body: no publisher GET.
        from http.client import IncompleteRead

        pack_path = Path(__file__).with_name("fixtures") / (
            "capturebrief_fy2027_archive_growth_boundary_v1.json"
        )
        pack = json.loads(pack_path.read_text(encoding="utf-8"))
        control = next(x for x in pack["synthetic_controls"]
                       if x["id"] == "SYNTHETIC_TRUNCATED_CHUNKED_TRANSFER")
        self.assertEqual(control["expected"], "SOURCE_INCOMPLETE")
        self.assertEqual(control["candidate_state"],
                         "REPAIRED_BY_INCOMPLETE_READ_MAPPING")
        self.assertIsNone(control["true_independent_award_label"])

        read_calls = []
        class Response:
            status = 200
            chunked = True
            headers = {"Content-Type": "text/csv",
                       "Content-Encoding": "identity",
                       "Transfer-Encoding": "chunked"}
            def __enter__(self): return self
            def __exit__(self, *_): return None
            def geturl(self): return SOURCE_URL
            def read(self, n):
                read_calls.append(n)
                self_outer.assertEqual(n, MAX_ORIGINAL_BYTES + 1)
                raise IncompleteRead(b"SYNTHETIC-TRUNCATED-BODY", 50)

        self_outer = self
        class Opener:
            def open(self, req, timeout): return Response()

        with patch("freight.capturebrief_sam_fy2027_asof.global_dns"), \
             patch("freight.capturebrief_sam_fy2027_asof.build_opener",
                   return_value=Opener()):
            receipt = build_receipt(observed_at=NOW)
        self.assertEqual(receipt["source_status"], STATUS_DEGRADED)
        self.assertEqual(receipt["source_error_codes"], ["SOURCE_INCOMPLETE"])
        self.assertEqual(read_calls, [MAX_ORIGINAL_BYTES + 1])

    def test_chunked_header_only_and_conflicting_length_fail_closed(self):
        # Both transport attacks are SYNTHETIC: no original notice fetched.
        pack = json.loads((Path(__file__).with_name('fixtures') /
            'capturebrief_fy2027_archive_growth_boundary_v1.json').read_text())
        control_ids = {c['id'] for c in pack['synthetic_controls']}
        self.assertIn('SYNTHETIC_FORGED_CHUNKED_HEADER', control_ids)
        self.assertIn('SYNTHETIC_DUAL_LENGTH_TRANSFER_FRAMING', control_ids)
        data = archive()
        for content_length, chunked_reader in ((None, False), (len(data), True)):
            with self.subTest(content_length=content_length):
                headers = {'Content-Type': 'text/csv',
                           'Content-Encoding': 'identity',
                           'Transfer-Encoding': 'chunked'}
                if content_length is not None:
                    headers['Content-Length'] = str(content_length)
                class Response:
                    status = 200
                    chunked = chunked_reader
                    def __enter__(self): return self
                    def __exit__(self, *_): return None
                    def geturl(self): return SOURCE_URL
                    def read(self, n):
                        raise AssertionError('must reject before read')
                response = Response()
                response.headers = headers
                class Opener:
                    def open(self, req, timeout): return response
                with patch('freight.capturebrief_sam_fy2027_asof.global_dns'):
                    with patch('freight.capturebrief_sam_fy2027_asof.build_opener',
                               return_value=Opener()):
                        with self.assertRaisesRegex(ResearchError, 'SOURCE_INCOMPLETE'):
                            fetch_original()

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


    def test_gsa_public_opportunities_history_documentation_guard(self):
        # GSA first-party documented coverage, NOT acquired SAM notices.
        pack = json.loads((Path(__file__).with_name("fixtures") /
            "capturebrief_fy2027_archive_growth_boundary_v1.json").read_text(encoding="utf-8"))
        d = pack["opportunities_api_version_history_evidence"]
        self.assertEqual(d["first_party_documentation_url"],
                         "https://open.gsa.gov/api/get-opportunities-public-api/")
        self.assertEqual(d["first_party_public_api_endpoint"],
                         "https://api.sam.gov/opportunities/v2/search")
        self.assertEqual(d["documented_api_history_scope"],
                         "LATEST_ACTIVE_VERSION_ONLY_NOT_COMPLETE_VERSION_HISTORY")
        self.assertEqual(d["documented_active_notice_update_cadence"], "DAILY")
        self.assertEqual(d["documented_archived_notice_update_cadence"], "WEEKLY")
        self.assertEqual(d["documented_status_filter"],
                         "COMING_SOON_NOT_CONFIRMED_OPERATIONAL")
        self.assertTrue(d["documented_date_required"])
        self.assertEqual(d["documented_posted_date_from_to_max_range"], "ONE_YEAR")
        self.assertIn("postedFrom", d["scope_and_schema"])
        self.assertIn("postedTo", d["scope_and_schema"])
        self.assertEqual(d["real_fy2027_notice_rows_from_this_source"], 0)
        self.assertEqual(d["independently_heldout_real_notice_version_change_labels"], 0)
        self.assertEqual(d["independent_preaward_notice_to_award_labels"], 0)
        self.assertIsNone(d["documentation_raw_http_response_sha256"])
        self.assertFalse(d["documentation_raw_response_bytes_retained"])
        self.assertEqual(d["publisher_effective_revision_date"], "UNKNOWN_NOT_ATTESTED")
        self.assertEqual(d["source_specific_data_reuse_and_third_party_commercial_rights"],
                         "UNKNOWN_NOT_APPROVED")
        self.assertFalse(d["legacy_15_lab_consolidation_verified"])
        self.assertFalse(pack["rights_and_truth"]["commercial_scoring_allowed"])

    def test_gsa_history_negative_controls_vs_unsafe_baseline(self):
        # Benchmark readiness only: these are SYNTHETIC, not real outcomes.
        pack = json.loads((Path(__file__).with_name("fixtures") /
            "capturebrief_fy2027_archive_growth_boundary_v1.json").read_text(encoding="utf-8"))
        controls = pack["opportunities_api_history_synthetic_controls"]
        self.assertEqual(len(controls), 4)
        ids = [c["id"] for c in controls]
        self.assertEqual(len(set(ids)), 4)
        self.assertEqual(sum(c["split"] == "synthetic_holdout" for c in controls), 3)
        self.assertEqual(sum(c["split"] == "synthetic_calibration" for c in controls), 1)
        for control in controls:
            with self.subTest(case=control["id"]):
                self.assertTrue(control["id"].startswith("SYN_"))
                self.assertEqual(control["provenance"],
                                 "RESEARCH_AUTHORED_SYNTHETIC_NOT_A_NOTICE")
                self.assertIsNone(control["independent_real_label"])
                self.assertTrue(control["expected_guard"].startswith("UNKNOWN_"))
                # RED = naive certainty. GREEN = source-aware UNKNOWN.
                self.assertNotEqual(control["unsafe_inference"], control["expected_guard"])
        self.assertEqual(pack["rights_and_truth"]["independent_holdout_award_cases"], 0)
        self.assertEqual(pack["rights_and_truth"]["independent_cross_source_outcomes"], 0)
        self.assertIsNone(pack["observation"]["source_byte_sha256"])
        self.assertEqual(pack["repair_evidence"]["new_original_source_calls"], 0)

    def test_gsa_history_false_label_promotion_is_not_benchmark_ready(self):
        pack = json.loads((Path(__file__).with_name("fixtures") /
            "capturebrief_fy2027_archive_growth_boundary_v1.json").read_text(encoding="utf-8"))
        def independent_truth_ready(d):
            h = d["opportunities_api_version_history_evidence"]
            return (h["real_fy2027_notice_rows_from_this_source"] > 0
                    and h["independently_heldout_real_notice_version_change_labels"] > 0
                    and h["documentation_raw_http_response_sha256"] is not None
                    and d["rights_and_truth"]["commercial_scoring_allowed"])
        self.assertFalse(independent_truth_ready(pack))
        forged = copy.deepcopy(pack)
        forged["opportunities_api_version_history_evidence"][
            "independently_heldout_real_notice_version_change_labels"] = 5
        # A fabricated positive label does not overcome missing original bytes/rights.
        self.assertFalse(independent_truth_ready(forged))



class USASpendingPublisherAwardBoundaryV1Tests(unittest.TestCase):
    """Two public publisher-page metadata examples, never an award accuracy benchmark."""

    @staticmethod
    def _pack():
        return json.loads((Path(__file__).with_name("fixtures") /
            "usaspending_reported_award_cross_source_boundary_v1.json").read_text(encoding="utf-8"))

    def test_real_reported_awards_have_source_urls_but_no_original_bytes_or_ground_truth(self):
        x=self._pack()
        self.assertEqual(x["schema_version"],1)
        self.assertEqual(x["publisher_scope"]["sample_count"],2)
        self.assertEqual(x["publisher_scope"]["independently_matched_notice_award_pairs"],0)
        self.assertEqual(x["publisher_scope"]["independently_adjudicated_award_outcomes"],0)
        self.assertEqual(x["publisher_scope"]["independent_real_negative_labels"],0)
        self.assertEqual(x["publisher_scope"]["independent_real_positive_labels"],0)
        self.assertIsNone(x["publisher_scope"]["measured_precision"])
        self.assertFalse(x["rights"]["commercial_scoring_allowed"])
        self.assertFalse(x["original_http_response_bytes_collected"])
        self.assertIsNone(x["original_publisher_http_body_sha256"])
        self.assertIsNone(x["original_publisher_http_body_byte_length"])
        self.assertEqual(len(x["real_publisher_page_observations"]),2)
        for record in x["real_publisher_page_observations"]:
            self.assertTrue(record["source_url"].startswith("https://www.usaspending.gov/award/"))
            self.assertTrue(record["source_url"].endswith(record["award_unique_key"]))
            self.assertIsNone(record["award_signed_date"])
            self.assertIsNone(record["pre_award_source_observation_sha256"])
            self.assertIsNone(record["independently_verified_sam_notice_id"])
            self.assertIsNone(record["independent_adjudication_label"])
            self.assertIsNone(record["independently_verified_cash"])

    def test_obligation_outlay_and_period_dates_cannot_be_promoted_to_cash_or_fy2027_notice(self):
        from decimal import Decimal
        x=self._pack()
        records={r["piid"]:r for r in x["real_publisher_page_observations"]}
        doe=records["89703026FAR000022"]
        faa=records["6973GH24F00956"]
        self.assertEqual(doe["period_of_performance_start_date"],"2026-09-16")
        self.assertEqual(doe["period_of_performance_current_end_date"],"2027-09-25")
        self.assertEqual(Decimal(doe["obligated_amount_usd"]),Decimal("29000.00"))
        self.assertEqual(Decimal(doe["outlayed_amount_usd"]),Decimal("0.00"))
        self.assertEqual(faa["period_of_performance_start_date"],"2024-07-24")
        self.assertEqual(faa["period_of_performance_current_end_date"],"2029-08-31")
        self.assertEqual(Decimal(faa["obligated_amount_usd"]),Decimal("1454413.80"))
        self.assertEqual(Decimal(faa["outlayed_amount_usd"]),Decimal("899473.19"))
        for r in records.values():
            self.assertNotEqual(Decimal(r["obligated_amount_usd"]),
                                Decimal(r["outlayed_amount_usd"]))
            self.assertIsNone(r["independently_verified_sam_notice_id"])
            self.assertIsNone(r["independently_verified_cash"])

    def test_synthetic_adversarial_controls_are_not_independent_holdout_cases(self):
        x=self._pack()
        controls=x["synthetic_controls"]
        self.assertEqual(len(controls),8)
        self.assertEqual(len({c["id"] for c in controls}),8)
        self.assertEqual(sum(c["split"]=="synthetic_holdout" for c in controls),5)
        self.assertEqual(sum(c["split"]=="calibration" for c in controls),3)
        self.assertTrue(all(c["kind"]=="SYNTHETIC_NOT_AN_ORIGINAL_AWARD_RECORD"
                            for c in controls))
        self.assertTrue(all(c["independent_real_label"] is None for c in controls))
        self.assertTrue(all(c["expected_guard_result"] in ("UNKNOWN","REJECT")
                            for c in controls))
        self.assertEqual(x["quality_and_dedup"]["independent_heldout_real_outcome_count"],0)
        self.assertEqual(x["quality_and_dedup"]["synthetic_holdout_count"],5)
        self.assertEqual(x["quality_and_dedup"]["original_publisher_byte_sha256_status"],
                         "UNKNOWN_NOT_ACQUIRED")

    def test_negative_controls_expose_naive_claim_as_proof_but_not_engine_accuracy(self):
        x=self._pack()
        controls=x["synthetic_controls"]
        naive_claims=["CLAIM_PROVED" for _ in controls]  # SYNTHETIC counterfactual
        guarded=[c["expected_guard_result"] for c in controls]
        self.assertEqual(sum(a!=b for a,b in zip(naive_claims,guarded)),8)
        self.assertEqual(sum(v not in ("UNKNOWN","REJECT") for v in guarded),0)
        self.assertEqual(x["publisher_scope"]["independent_real_positive_labels"],0)
        self.assertEqual(x["publisher_scope"]["independent_real_negative_labels"],0)
        self.assertIsNone(x["publisher_scope"]["measured_recall"])

    def test_publisher_key_dedup_and_malformed_cross_source_promotion_are_rejected(self):
        x=self._pack()
        records=x["real_publisher_page_observations"]
        keys=[r["award_unique_key"] for r in records]
        self.assertEqual(len(set(keys)),2)
        self.assertEqual(len(set(keys + keys[:1])),2)
        self.assertEqual(x["quality_and_dedup"]["observed_distinct_publisher_award_keys"],2)
        self.assertEqual(len(set(r["source_url"].split("/")[2] for r in records)),1)
        self.assertFalse(x["restrictions"]["legacy_15_lab_consolidation_certified"])
        self.assertFalse(x["restrictions"]["no_engine_code_changes"] is False)
        tampered=copy.deepcopy(x)
        tampered["publisher_scope"]["independently_matched_notice_award_pairs"]=1
        def is_eligible_for_real_award_benchmark(pack):
            return (
                pack["publisher_scope"]["independently_matched_notice_award_pairs"]>0
                and all(r["pre_award_source_observation_sha256"] is not None
                        and r["independent_adjudication_label"] is not None
                        for r in pack["real_publisher_page_observations"])
            )
        self.assertFalse(is_eligible_for_real_award_benchmark(x))
        self.assertFalse(is_eligible_for_real_award_benchmark(tampered))



class CaptureBriefPriorFullArchiveByteProvenanceTests(unittest.TestCase):
    """Cross-repo ORIGINAL-byte receipt reuse without any new SAM download."""

    @classmethod
    def setUpClass(cls):
        cls.pack = json.loads(
            (Path(__file__).with_name("fixtures") /
             "capturebrief_fy2027_archive_growth_boundary_v1.json")
            .read_text(encoding="utf-8"))

    def test_historical_original_byte_observation_has_pinned_custody_reference(self):
        d = self.pack
        h = d["historical_original_full_byte_receipt"]
        self.assertEqual(h["first_party_source_url"], d["source_url"])
        self.assertEqual(h["original_http_sha256_reported"], PREVIOUS_PUBLIC_REFERENCE_SHA256)
        self.assertEqual(h["original_http_status"], 200)
        self.assertEqual(h["original_http_byte_size_reported"], 1607260)
        self.assertEqual(h["original_csv_data_rows_reported"], 1104)
        self.assertTrue(h["original_required_headers_reported_present"])
        self.assertEqual(h["receipt_blob_git_sha1"],
                         "3975380b25b168398c6a7b0012f03bab90471f30")
        self.assertEqual(h["gh_run_commit"],
                         "7f4dad8de34eb1570e5f936664577c81bf7e451e")
        self.assertIn("/capturebrief/actions/runs/39205786451", h["gh_run_url"])
        self.assertEqual(h["publisher_last_modified_utc"], "2026-10-18T14:51:03Z")
        self.assertEqual(h["observed_utc"][:10], "2026-10-19")
        self.assertFalse(h["original_sha256_recomputed_by_unified_lab_this_cycle"])

    def test_old_success_does_not_promote_current_writer_failure(self):
        h = self.pack["historical_original_full_byte_receipt"]
        current = self.pack["repair_evidence"]["reused_existing_writer_receipt"]
        self.assertEqual(current["status"], "SOURCE_TOO_LARGE")
        self.assertEqual(h["latest_unified_writer_state"], current["status"])
        self.assertIsNone(current["original_source_byte_sha256"])
        self.assertIsNone(h["current_2026_10_31_source_sha256"])
        self.assertFalse(h["historical_original_bytes_are_current_source_bytes"])
        self.assertFalse(h["raw_bytes_durably_retained"])
        self.assertFalse(h["commercial_reuse_authorized"])
        self.assertEqual(h["independently_heldout_real_award_labels"], 0)
        self.assertEqual(h["independently_matched_award_outcomes"], 0)
        self.assertFalse(self.pack["rights_and_truth"]["commercial_scoring_allowed"])

    def test_five_synthetic_historical_claims_fail_closed(self):
        controls = self.pack["historical_full_byte_synthetic_controls"]
        self.assertEqual(len(controls), 5)
        self.assertEqual(len({c["id"] for c in controls}), 5)
        self.assertEqual(sum(c["split"] == "synthetic_holdout" for c in controls), 4)
        for c in controls:
            with self.subTest(c=c["id"]):
                self.assertEqual(c["provenance"],
                                 "RESEARCH_AUTHORED_SYNTHETIC_NOT_AN_ORIGINAL_NOTICE")
                self.assertIsNone(c["independent_real_label"])
                self.assertTrue(c["expected_guard"].startswith("UNKNOWN_"))
                self.assertNotEqual(c["unsafe_inference"], c["expected_guard"])
        self.assertIsNone(self.pack["historical_full_byte_quality"]["real_test_accuracy"])

    def test_false_byte_hash_promotion_and_label_forgery_are_not_benchmark_ready(self):
        d = self.pack
        h = d["historical_original_full_byte_receipt"]
        def ready(pack):
            x = pack["historical_original_full_byte_receipt"]
            return (x["current_2026_10_31_source_sha256"] is not None
                    and x["original_sha256_recomputed_by_unified_lab_this_cycle"]
                    and x["raw_bytes_durably_retained"]
                    and x["independently_heldout_real_award_labels"] > 0
                    and x["commercial_reuse_authorized"])
        self.assertFalse(ready(d))
        forged = copy.deepcopy(d)
        forged["historical_original_full_byte_receipt"]["current_2026_10_31_source_sha256"] = h["original_http_sha256_reported"]
        forged["historical_original_full_byte_receipt"]["independently_heldout_real_award_labels"] = 10
        self.assertFalse(ready(forged))
        self.assertEqual(d["historical_full_byte_quality"]["original_csv_rows_new"], 0)
        self.assertFalse(d["historical_full_byte_quality"]["fifteen_legacy_labs_consolidated"])

if __name__=="__main__":
    unittest.main()
