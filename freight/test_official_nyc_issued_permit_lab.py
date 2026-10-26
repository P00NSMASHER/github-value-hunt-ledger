"""Original NYC approved-permit publisher record readback (no customer data saved)."""
from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from unittest.mock import patch

from freight.official_nyc_issued_permit_lab import (
    DATASET_ID, FIELDS, MAX_BODY_BYTES, MAX_READBACK, MAX_ROWS,
    OFFICIAL_HOST, SOURCE_URL, SCOPE, _check, _classification,
    _key, _minimal, _validate_target, build_receipt, fetch_rows,
    query_url, run,
)
from freight.unified_research_lab import (
    ResearchError, digest, ledger_from, source_record,
)

DAY = date(2026, 10, 23)
rows = [
    {"tracking_number":"5001001", "job_filing_number":"M01300000-I1",
     "work_permit":"M01300000-I1-GC", "sequence_number":"1",
     "issued_date":"2026-10-21T00:00:00.000", "permit_status":"Permit Issued"},
    {"tracking_number":"5001001", "job_filing_number":"M01300000-I1",
     "work_permit":"M01300000-I1-PL", "sequence_number":"1",
     "issued_date":"2026-10-22T00:00:00.000", "permit_status":"Permit Issued"},
    {"tracking_number":"5002002", "job_filing_number":"B01122233-I1",
     "work_permit":"Permit is not yet issued", "sequence_number":"2",
     "issued_date":"2026-10-22T00:00:00.000", "permit_status":"Approved"},
    {"tracking_number":"5003003", "job_filing_number":"B03333333-S1",
     "work_permit":"B03333333-S1-FN", "sequence_number":"1",
     "issued_date":"2026-10-22T00:00:00.000", "permit_status":"Expired"},
]


def source_ledger():
    return ledger_from([source_record(SOURCE_URL,"permitplate","2026-10-20")])


def simulated_provider(url):
    query = parse_qs(urlsplit(url).query)
    assert query.get("$select") == [",".join(FIELDS)]
    if query.get("$order"):
        candidates = rows
    else:
        where=query["$where"][0]
        key=where.split(" = ",1)[1].strip("'")
        candidates = [r for r in rows if str(r["tracking_number"]) == key]
    # Honor Socrata $select; omitted columns cannot appear magically in mocked GETs.
    return [{field: r[field] for field in FIELDS if field in r} for r in candidates]


class OfficialNYCOriginalReadbackTests(unittest.TestCase):
    def test_url_scope_and_small_publisher_request_budgets(self):
        first=query_url()
        self.assertEqual(_validate_target(first),first)
        self.assertEqual(_validate_target(query_url(tracking_number="5001001")),
                         query_url(tracking_number="5001001"))
        self.assertEqual(_validate_target(query_url(tracking_number=123456)),
                         query_url(tracking_number=123456))
        self.assertEqual(MAX_ROWS,20)
        self.assertEqual(MAX_READBACK,3)
        for bad in (
            "http://data.cityofnewyork.us/resource/rbx6-tga4.json",
            "https://private.invalid/resource/rbx6-tga4.json",
            "https://data.cityofnewyork.us/resource/w9ak-ipjd.json",
            "https://data.cityofnewyork.us/resource/rbx6-tga4.json?$limit=999999",
            query_url()+"&$limit=999",
            query_url()+"&token=secret",
            query_url()+"#evil",
            query_url(tracking_number="5001001").replace("tracking_number", "owner_name"),
        ):
            with self.subTest(url=bad),self.assertRaises(ResearchError):
                _validate_target(bad)
        for unsafe in ("5001001' OR 1=1", "../../etc/passwd", "person@example.com", "", "42"):
            with self.subTest(unsafe=unsafe),self.assertRaises(ResearchError):
                query_url(tracking_number=unsafe)
        with self.assertRaises(ResearchError):
            query_url(tracking_number=0)

    def test_original_source_row_and_second_readback_are_distinct_evidence(self):
        receipt=build_receipt(source_ledger(),as_of=DAY,fetcher=simulated_provider)
        self.assertEqual(receipt["schema_version"],1)
        self.assertEqual(receipt["scope"],SCOPE)
        self.assertEqual(receipt["official_dataset_id"],DATASET_ID)
        self.assertEqual(receipt["status"],"PUBLISHER_REPLAY_OK")
        self.assertEqual(receipt["sample_count"],4)
        self.assertEqual(receipt["sample_unique_source_identities"],4)
        self.assertEqual(receipt["sample_repeated_source_rows"],0)
        self.assertEqual(receipt["readback_checked"],3)
        self.assertEqual(receipt["readback_exact_match"],3)
        self.assertEqual(receipt["readback_changed"],0)
        self.assertEqual(receipt["publisher_status_classifications"],{
            "publisher_issue_date_present":3,
            "publisher_not_yet_issued_marker":1})
        self.assertEqual(receipt["user_commercial_reuse_attestation"],
                         "OWNER_ATTESTED_NOT_SOURCE_VERIFIED")
        self.assertFalse(receipt["source_specific_commercial_license_verified"])
        self.assertEqual(receipt["independent_issuance_outcome_labels"],0)
        self.assertFalse(receipt["buyer_opportunity_ground_truth"])
        self.assertEqual(receipt["sample_original_rows_stored"],0)
        self.assertEqual(receipt["receipt_sha256"],
                         digest({k:v for k,v in receipt.items() if k!="receipt_sha256"}))
        _check(receipt,source_ledger(),DAY)
        self.assertNotIn("job_filing_number",receipt)
        self.assertNotIn("5001001",str(receipt))
        self.assertNotIn("street_name",str(receipt))
        self.assertNotIn("owner_name",str(receipt))

    def test_source_change_is_degraded_not_false_green(self):
        def changed_provider(url):
            result=simulated_provider(url)
            if not parse_qs(urlsplit(url).query).get("$order"):
                for row in result:
                    row["permit_status"]="Status Changed After First Read"
            return result
        receipt=build_receipt(source_ledger(),as_of=DAY,fetcher=changed_provider)
        self.assertEqual(receipt["status"],"PUBLISHER_REPLAY_DEGRADED")
        self.assertEqual(receipt["readback_checked"],3)
        self.assertGreater(receipt["readback_changed"],0)
        self.assertEqual(receipt["source_errors"],["PUBLISHER_ROW_READBACK_INCOMPLETE"])
        _check(receipt,source_ledger(),DAY)

    def test_unavailable_publisher_does_not_create_fake_label(self):
        def unavailable(_url):
            raise ResearchError("HTTP_STATUS")
        receipt=build_receipt(source_ledger(),as_of=DAY,fetcher=unavailable)
        self.assertEqual(receipt["status"],"PUBLISHER_REPLAY_DEGRADED")
        self.assertEqual(receipt["source_errors"],["HTTP_STATUS"])
        self.assertEqual(receipt["readback_checked"],0)
        self.assertEqual(receipt["sample_count"],0)
        self.assertEqual(receipt["independent_issuance_outcome_labels"],0)
        self.assertIsNone(receipt["sample_canonical_sha256"])
        _check(receipt,source_ledger(),DAY)

    def test_missing_approval_source_in_ledger_fails_closed(self):
        other=ledger_from([source_record(
            "https://data.cityofnewyork.us/d/w9ak-ipjd",
            "permitplate","2026-10-22")])
        with self.assertRaisesRegex(ResearchError,"APPROVED_PERMIT_SOURCE_NOT_IN_LEDGER"):
            build_receipt(other,as_of=DAY,fetcher=simulated_provider)

    def test_duplicate_source_snapshots_are_counted_not_misidentified_as_distinct_cases(self):
        self.assertNotEqual(_key(_minimal(rows[0],DAY)),_key(_minimal(rows[1],DAY)))
        def duplicate_provider(url):
            if parse_qs(urlsplit(url).query).get("$order"):
                return rows + [copy.deepcopy(rows[0])]
            return simulated_provider(url)
        receipt = build_receipt(source_ledger(),as_of=DAY,fetcher=duplicate_provider)
        self.assertEqual(receipt["status"],"PUBLISHER_REPLAY_DEGRADED")
        self.assertEqual(receipt["sample_count"],5)
        self.assertEqual(receipt["sample_unique_source_identities"],4)
        self.assertEqual(receipt["sample_repeated_source_rows"],1)
        self.assertEqual(receipt["readback_exact_match"],3)
        self.assertEqual(receipt["readback_checked"],3)
        self.assertEqual(receipt["source_errors"],["DUPLICATE_SOURCE_IDENTITIES"])
        self.assertEqual(receipt["independent_issuance_outcome_labels"],0)
        _check(receipt,source_ledger(),DAY)

    def test_all_repeated_source_rows_cannot_become_false_green(self):
        count=[]
        def all_duplicates(url):
            count.append(url)
            if parse_qs(urlsplit(url).query).get("$order"):
                return [copy.deepcopy(rows[0]) for _ in range(20)]
            return [copy.deepcopy(rows[0])]
        receipt=build_receipt(source_ledger(),as_of=DAY,fetcher=all_duplicates)
        self.assertEqual(receipt["sample_count"],20)
        self.assertEqual(receipt["sample_unique_source_identities"],1)
        self.assertEqual(receipt["sample_repeated_source_rows"],19)
        self.assertEqual(receipt["readback_checked"],0)
        self.assertEqual(receipt["status"],"PUBLISHER_REPLAY_DEGRADED")
        self.assertIn("DUPLICATE_SOURCE_IDENTITIES",receipt["source_errors"])
        self.assertIn("PUBLISHER_ROW_READBACK_INCOMPLETE",receipt["source_errors"])
        self.assertEqual(len(count),1)
        _check(receipt,source_ledger(),DAY)

    def test_truncated_publisher_readbacks_are_ambiguous_not_exact_verified(self):
        def provider(url):
            if parse_qs(urlsplit(url).query).get("$order"):
                return [rows[0]]
            return [rows[0]]*MAX_ROWS
        receipt=build_receipt(source_ledger(),as_of=DAY,fetcher=provider)
        self.assertEqual(receipt["readback_ambiguous"],1)
        self.assertEqual(receipt["readback_exact_match"],0)
        self.assertEqual(receipt["status"],"PUBLISHER_REPLAY_DEGRADED")
        _check(receipt,source_ledger(),DAY)

    def test_second_read_source_error_retains_original_sample_and_reports_unavailable(self):
        def provider(url):
            if parse_qs(urlsplit(url).query).get("$order"):
                return [rows[0]]
            raise ResearchError("HTTP_STATUS")
        receipt=build_receipt(source_ledger(),as_of=DAY,fetcher=provider)
        self.assertEqual(receipt["sample_count"],1)
        self.assertEqual(receipt["readback_checked"],1)
        self.assertEqual(receipt["readback_unavailable"],1)
        self.assertEqual(receipt["readback_exact_match"],0)
        self.assertEqual(receipt["status"],"PUBLISHER_REPLAY_DEGRADED")
        self.assertEqual(receipt["source_errors"],["PUBLISHER_ROW_READBACK_INCOMPLETE"])
        _check(receipt,source_ledger(),DAY)


    def test_malformed_columns_and_future_or_impossible_dates_fail_closed(self):
        for mutation in (
            {"tracking_number":None}, {"job_filing_number":"bad value with spaces"},
            {"issued_date":"2027-01-01T00:00:00.000"},
            {"issued_date":"2010-02-01"},
            {"issued_date":"2026-10-23banana"},
            {"work_permit":""}, {"permit_status":123},
            {"sequence_number":"\n\nevil"},
        ):
            invalid={**rows[0],**mutation}
            with self.subTest(mutation=mutation),self.assertRaisesRegex(
                    ResearchError,"SCHEMA_CHANGED"):
                _minimal(invalid,DAY)

    @patch("freight.official_nyc_issued_permit_lab.datetime")
    def test_replay_snapshot_is_deterministic_cached_and_tamper_evident(self, test_clock):
        # Freeze only the unit-test clock; do not weaken production UTC freshness.
        test_clock.now.return_value.date.return_value = DAY
        observed=[]
        def fetcher(url):
            observed.append(url)
            return simulated_provider(url)
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            ledger_path=root/"leads.json"
            target=root/"readback.json"
            ledger_path.write_text(json.dumps(source_ledger()),encoding="utf-8")
            res=run(ledger_path=ledger_path,output=target,fetcher=fetcher,as_of=DAY)
            self.assertEqual(res["source_rows_replayed"],4)
            self.assertEqual(len(observed),4)
            first=target.read_bytes()
            res2=run(ledger_path=ledger_path,output=target,fetcher=fetcher,as_of=DAY)
            self.assertEqual(first,target.read_bytes())
            self.assertEqual(len(observed),4)
            report=json.loads(target.read_text())
            report["buyer_opportunity_ground_truth"]=True
            report["receipt_sha256"]=digest({k:v for k,v in report.items()
                                               if k!="receipt_sha256"})
            target.write_text(json.dumps(report))
            # Cannot silently accept a forged claim with a recomputed digest.
            with self.assertRaises(ResearchError):
                run(ledger_path=ledger_path,output=target,verify_only=True)
            cleaned=run(ledger_path=ledger_path,output=target,as_of=DAY,
                        fetcher=fetcher)
            self.assertEqual(cleaned["status"],"PUBLISHER_REPLAY_OK")
            self.assertEqual(len(observed),8)
            self.assertFalse(json.loads(target.read_text())["buyer_opportunity_ground_truth"])

    def test_reconstructed_receipt_rejects_forced_permissions_and_fake_source_outcomes(self):
        original=build_receipt(source_ledger(),as_of=DAY,fetcher=simulated_provider)
        for field,val in (
            ("source_specific_commercial_license_verified",True),
            ("independent_issuance_outcome_labels",1),
            ("sample_original_rows_stored",1),
            ("external_customer_contacts",1),
            ("new_paid_services",1),
            ("official_dataset_id","other-dataset"),
            ("status","PUBLISHER_REPLAY_GREEN_BY_FORCE"),
            ("readback_exact_match",99),
            ("sample_repeated_source_rows",99),
            ("readback_ambiguous",1),
        ):
            receipt=copy.deepcopy(original)
            receipt[field]=val
            receipt["receipt_sha256"]=digest({k:v for k,v in receipt.items()
                                              if k!="receipt_sha256"})
            with self.subTest(field=field),self.assertRaises(ResearchError):
                _check(receipt,source_ledger(),DAY)

    def test_dedicated_public_get_only_with_no_redirects_and_byte_ceiling(self):
        target=query_url()
        class Response:
            status=200
            def __init__(self,content=b"[]",ctype="application/json",url=target):
                self.content=content
                self.url=url
                self.headers={"Content-Type":ctype,"Content-Encoding":"identity"}
            def __enter__(self):return self
            def __exit__(self,*args):return None
            def geturl(self):return self.url
            def read(self,size):
                self.requested=size
                return self.content[:size]
        seen=[]
        class Opener:
            def open(self,req,timeout):
                self_host=urlsplit(req.full_url).hostname
                seen.append((req.get_method(),self_host,timeout))
                return Response()
        with patch("freight.official_nyc_issued_permit_lab.global_dns"),\
             patch("freight.official_nyc_issued_permit_lab.build_opener",
                   return_value=Opener()):
            self.assertEqual(fetch_rows(target),[])
        self.assertEqual(seen,[("GET",OFFICIAL_HOST,10)])
        self.assertEqual(MAX_BODY_BYTES,160_000)
        def huge(_url):
            raise ResearchError("SOURCE_TOO_LARGE")
        result=build_receipt(source_ledger(),as_of=DAY,fetcher=huge)
        self.assertEqual(result["status"],"PUBLISHER_REPLAY_DEGRADED")
        self.assertEqual(result["source_errors"],["SOURCE_TOO_LARGE"])

    def test_publisher_not_yet_issued_placeholder_never_becomes_issue_positive(self):
        marker=_minimal(rows[2],DAY)
        self.assertEqual(_classification(marker),"PUBLISHER_NOT_YET_ISSUED_MARKER")
        self.assertNotEqual(_classification(marker),"PUBLISHER_ISSUE_DATE_PRESENT")


    def test_official_sequence_projection_negative_control_and_rights_hold(self):
        """Publisher-declared sequence is not a live identity unless selected."""
        path=Path(__file__).with_name("fixtures") / "nyc_dob_sequence_projection_v1.json"
        pack=json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(pack["schema_version"],"1.0.0")
        self.assertEqual(pack["source"]["dataset_id"],DATASET_ID)
        self.assertEqual(pack["source"]["publisher_field_verified"],"sequence_number")
        self.assertIsNone(pack["source"]["original_publisher_response_bytes_sha256"])
        self.assertIsNone(pack["source"]["publisher_metadata_response_bytes_sha256"])
        self.assertFalse(pack["source"]["dataset_specific_commercial_reuse_authorized"])
        self.assertEqual(pack["cohort"]["independent_held_out_labeled_cases"],0)
        self.assertFalse(pack["cohort"]["independent_holdout_verified"])
        self.assertFalse(pack["inspected_source"]["live_collision_in_publisher_data_verified"])
        self.assertEqual(len(pack["synthetic_negative_controls"]),3)
        self.assertTrue(all(c["synthetic"] for c in pack["synthetic_negative_controls"]))
        self.assertTrue(all(c["actual_real_world_error_label"] is None
                            for c in pack["synthetic_negative_controls"]))
        synthetic=pack["synthetic_negative_controls"][0]["rows"]
        self.assertEqual(len(synthetic),2)
        self.assertNotEqual(synthetic[0]["sequence_number"],synthetic[1]["sequence_number"])
        self.assertEqual({key:val for key,val in synthetic[0].items()
                          if key!="sequence_number"},
                         {key:val for key,val in synthetic[1].items()
                          if key!="sequence_number"})
        def select_accurate_provider(url):
            args=parse_qs(urlsplit(url).query)
            sample=(synthetic if args.get("$order") else
                    [r for r in synthetic if str(r["tracking_number"])==
                     args["$where"][0].split(" = ",1)[1].strip("'")])
            return [{f:r[f] for f in FIELDS if f in r} for r in sample]
        sample=select_accurate_provider(query_url())
        self.assertEqual(set(sample[0]),set(FIELDS))
        receipt=build_receipt(source_ledger(),as_of=DAY,
                              fetcher=select_accurate_provider)
        self.assertEqual(receipt["sample_count"],2)
        if "sequence_number" in FIELDS:
            self.assertEqual(receipt["sample_unique_source_identities"],2)
            self.assertEqual(receipt["status"],"PUBLISHER_REPLAY_OK")
            self.assertEqual(receipt["readback_exact_match"],2)
        else:
            self.assertEqual(receipt["sample_unique_source_identities"],1)
            self.assertEqual(receipt["sample_repeated_source_rows"],1)
            self.assertEqual(receipt["readback_checked"],0)
            self.assertEqual(receipt["status"],"PUBLISHER_REPLAY_DEGRADED")
            self.assertIn("DUPLICATE_SOURCE_IDENTITIES",receipt["source_errors"])
        self.assertFalse(receipt["source_specific_commercial_license_verified"])
        self.assertEqual(receipt["independent_issuance_outcome_labels"],0)
        self.assertFalse(receipt["buyer_opportunity_ground_truth"])
        _check(receipt,source_ledger(),DAY)



if __name__=="__main__":
    unittest.main()
