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
                # Duplicate snapshot still obeys the original $select projection.
                return [{field:r[field] for field in FIELDS if field in r}
                        for r in rows + [copy.deepcopy(rows[0])]]
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

    def test_receipt_freshness_rejects_future_and_expired_source_proof(self):
        receipt=build_receipt(source_ledger(),as_of=DAY,fetcher=simulated_provider)
        # Two-day evidence validity is a production safeguard, not a test timeout.
        _check(receipt,source_ledger(),DAY+timedelta(days=2))
        for checked_at in (DAY-timedelta(days=1),DAY+timedelta(days=3)):
            with self.subTest(checked_at=checked_at),self.assertRaisesRegex(
                    ResearchError,"STALE_OR_FUTURE_READBACK_RECEIPT"):
                _check(receipt,source_ledger(),checked_at)

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
        self.assertEqual(len(pack["synthetic_negative_controls"]),6)
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



    def test_official_metadata_declares_nullable_sequence_without_ground_truth(self):
        """Cached first-party metadata shows nullable identity, not row-level truth."""
        path=Path(__file__).with_name("fixtures") / "nyc_dob_sequence_projection_v1.json"
        pack=json.loads(path.read_text(encoding="utf-8"))
        profile=pack["publisher_cached_sequence_profile"]
        self.assertEqual(profile["observed_dataset_id"],DATASET_ID)
        self.assertEqual(profile["field_name"],"sequence_number")
        self.assertEqual(profile["publisher_rows_updated_at_utc"],
                         "2026-10-25T18:41:35Z")
        self.assertEqual(profile["publisher_cached_null_count"],351)
        self.assertEqual(profile["publisher_cached_non_null_count"],1019801)
        self.assertEqual(profile["publisher_cached_total_count"],
                         profile["publisher_cached_null_count"]+
                         profile["publisher_cached_non_null_count"])
        self.assertIsNone(profile["publisher_original_metadata_response_sha256"])
        self.assertFalse(profile["source_specific_commercial_reuse_authorized"])
        self.assertFalse(profile["proves_nulls_within_current_live_query_cohort"])
        self.assertFalse(profile["proves_distinct_real_identity_collisions"])
        self.assertEqual(profile["actual_rows_read_or_stored"],0)
        self.assertEqual(profile["independent_holdout_labeled_count"],0)
        control=next(c for c in pack["synthetic_negative_controls"]
                     if c["id"]=="nullable_sequence_cannot_prove_distinct_issuance")
        self.assertTrue(control["synthetic"])
        self.assertIsNone(control["actual_real_world_error_label"])
        a,b=(_minimal(x,DAY) for x in control["rows"])
        self.assertIsNone(a["sequence_number"])
        self.assertIsNone(b["sequence_number"])
        self.assertEqual(_key(a),_key(b))
        self.assertNotEqual(a["issued_date"],b["issued_date"])
        self.assertEqual(pack["cohort"]["independent_held_out_labeled_cases"],0)


    def test_official_cached_status_expiry_profile_never_promotes_current_validity(self):
        """Original NYC metadata is source-wide, not a live permit-validity label."""
        path=Path(__file__).with_name("fixtures") / "nyc_dob_sequence_projection_v1.json"
        pack=json.loads(path.read_text(encoding="utf-8"))
        profile=pack["publisher_cached_status_and_expiry_profile"]
        self.assertEqual(profile["dataset_id"],DATASET_ID)
        self.assertEqual(profile["publisher_rows_updated_at_utc"],
                         "2026-10-25T18:41:35Z")
        counts=profile["permit_status_cached_counts"]
        self.assertEqual(counts,{"Signed-off":652244,"Permit Issued":367908})
        self.assertEqual(sum(counts.values()),profile["total_cached_records"])
        self.assertEqual(profile["permit_status_column_null_count"],0)
        self.assertEqual(profile["expired_date_cached_non_null_count"]+
                         profile["expired_date_cached_null_count"],
                         profile["total_cached_records"])
        self.assertEqual(profile["expired_date_cached_null_count"],1168)
        self.assertEqual(profile["expired_date_cached_minimum"],
                         "1899-12-30T00:00:00.000")
        self.assertFalse(profile["date_1899_is_sentinel_verified"])
        self.assertFalse(profile["status_and_expiry_joint_distribution_verified"])
        self.assertIsNone(profile["publisher_metadata_response_raw_sha256"])
        self.assertEqual(profile["actual_publisher_rows_downloaded"],0)
        self.assertEqual(profile["independent_current_permit_validity_labels"],0)
        self.assertFalse(profile["dataset_specific_commercial_reuse_approved"])
        control=next(x for x in pack["synthetic_negative_controls"]
                     if x["id"]=="signed_off_or_1899_expiry_is_not_current_validity_proof")
        self.assertTrue(control["synthetic"])
        self.assertIsNone(control["independent_current_validity_label"])
        self.assertIsNone(control["actual_real_world_error_label"])
        normalized=_minimal(control["row"],DAY)
        self.assertEqual(normalized["permit_status"],"Signed-off")
        self.assertEqual(_classification(normalized),"PUBLISHER_ISSUE_DATE_PRESENT")
        self.assertNotIn("expired_date",normalized)
        self.assertEqual(pack["cohort"]["independent_held_out_labeled_cases"],0)



    def test_official_filing_reason_placeholder_profile_not_issuance_truth(self):
        """Publisher category and placeholder counts cannot be issuer labels."""
        path=Path(__file__).with_name("fixtures") / "nyc_dob_sequence_projection_v1.json"
        pack=json.loads(path.read_text(encoding="utf-8"))
        profile=pack["publisher_cached_filing_reason_profile"]
        self.assertEqual(profile["dataset_id"],DATASET_ID)
        self.assertEqual(profile["publisher_rows_updated_at_utc"],
                         "2026-10-25T18:41:35Z")
        counts=profile["filing_reason_cached_counts"]
        self.assertEqual(counts["No Work Permit"],6764)
        self.assertEqual(counts["None"],415)
        self.assertEqual(sum(counts.values()),profile["total_cached_records"])
        self.assertEqual(profile["work_permit_column_null_count"],212)
        self.assertEqual(profile["work_permit_placeholder_cached_top_count"],345)
        self.assertEqual(profile["work_permit_placeholder_text"],
                         "Permit is not yet issued")
        self.assertFalse(profile["filing_reason_and_work_permit_joint_distribution_verified"])
        self.assertFalse(profile["these_counts_in_filtered_20_row_replay_verified"])
        self.assertIsNone(profile["original_publisher_metadata_response_sha256"])
        self.assertFalse(profile["source_specific_commercial_reuse_approved"])
        self.assertEqual(profile["independent_permit_issuance_labels"],0)
        case=next(c for c in pack["synthetic_negative_controls"]
                  if c["id"]=="filing_reason_no_work_permit_not_issued_truth")
        self.assertTrue(case["synthetic"])
        self.assertIsNone(case["actual_real_world_error_label"])
        self.assertIsNone(case["independent_current_validity_label"])
        normalized=_minimal(case["row"],DAY)
        self.assertEqual(_classification(normalized),"PUBLISHER_NOT_YET_ISSUED_MARKER")
        self.assertNotEqual(_classification(normalized),"PUBLISHER_ISSUE_DATE_PRESENT")
        self.assertEqual(pack["cohort"]["independent_held_out_labeled_cases"],0)


    def test_socrata_system_id_proposal_does_not_promote_api_rows_to_permit_labels(self):
        """Documented :id and :updated_at are unprobed, rights-held identity aids."""
        pack=json.loads((Path(__file__).with_name("fixtures") /
                         "nyc_dob_live_replay_quality_candidate_v0.json")
                        .read_text(encoding="utf-8"))
        probe=pack["publisher_platform_identity_validation_candidate"]
        self.assertEqual(probe["documentation_url"],
                         "https://dev.socrata.com/docs/system-fields")
        self.assertEqual(probe["documented_system_select_fields"],
                         [":id",":updated_at"])
        self.assertEqual(probe["source_dataset_id"],DATASET_ID)
        self.assertFalse(probe["current_collector_selects_system_fields"])
        self.assertFalse(probe["original_publisher_dataset_specific_probe_executed"])
        self.assertIsNone(probe["original_publisher_system_field_response_sha256"])
        self.assertIsNone(probe["number_of_real_collisions_disambiguated"])
        self.assertFalse(probe["cross_full_replacement_id_stability_verified"])
        self.assertFalse(probe["source_specific_commercial_reuse_authorized"])
        self.assertEqual(probe["independent_held_out_validity_labels"],0)
        cases={c["id"]:c for c in pack["synthetic_negative_controls"]}
        different=cases["SYNTH_PROJECTED_COLLISION_WITH_DISTINCT_SODA_ROW_IDS"]
        self.assertEqual(different["kind"],"SYNTHETIC")
        a,b=different["rows"]
        self.assertEqual(a["projected_key"],b["projected_key"])
        self.assertNotEqual(a["system_row_id"],b["system_row_id"])
        self.assertIsNone(a["independent_permit_validity"])
        self.assertIsNone(b["independent_permit_validity"])
        updated=cases["SYNTH_UPDATED_API_ROW_IS_NOT_AN_INDEPENDENT_PERMIT"]
        self.assertEqual(updated["kind"],"SYNTHETIC")
        a,b=updated["rows"]
        self.assertEqual(a["system_row_id"],b["system_row_id"])
        self.assertNotEqual(a["system_updated_at"],b["system_updated_at"])
        self.assertIsNone(a["independent_permit_validity"])
        self.assertIsNone(b["independent_permit_validity"])
        self.assertEqual(pack["observed"]["actual_distinct_original_records"],"UNKNOWN")
        self.assertEqual(pack["observed"]["held_out_labeled_permits"],0)


    def test_live_20row_replay_has_repeated_identities_not_twenty_labels(self):
        """Freeze a real source-readback receipt; never promote it to scoring truth."""
        case=json.loads((Path(__file__).with_name("fixtures") /
                         "nyc_dob_live_replay_quality_candidate_v0.json")
                        .read_text(encoding="utf-8"))
        self.assertEqual(case["engine"],"permitplate")
        self.assertEqual(case["source"]["original_publisher_url"],
                         "https://data.cityofnewyork.us/d/rbx6-tga4")
        self.assertIsNone(case["source"]["publisher_original_http_bytes_sha256"])
        self.assertFalse(case["source"]["dataset_specific_commercial_reuse_authorized"])
        provenance=case["provenance"]
        self.assertEqual(provenance["writer_commit"],
                         "9e1805f6e18fd6174f548e99d21bc0e5ee0b52be")
        self.assertEqual(provenance["receipt_blob_git_sha1"],
                         "519e03c3c24c1d8b5e72e9f2e87ecf921cd60525")
        self.assertEqual(provenance["receipt_sha256"],
                         "a889b091d7f834b95375cfd77a9a389ee0ee5306f7767def2ee6b4c300ff192e")
        self.assertEqual(provenance["sample_canonical_sha256"],
                         "d68bc6f3921427208de9708bd2ef4d2e68abe6c19e92c9154daf315a8a0c3f93")
        self.assertEqual(provenance["raw_publisher_rows_stored"],0)
        o=case["observed"]
        def safely_degraded(p):
            r=p["observed"]
            return (r["sample_count"]-r["sample_unique_source_identities"]
                    ==r["sample_repeated_source_rows"]
                    and r["sample_repeated_source_rows"]>0
                    and r["receipt_status"]=="PUBLISHER_REPLAY_DEGRADED"
                    and r["error_codes"]==["DUPLICATE_SOURCE_IDENTITIES"]
                    and r["second_read_exact_match"]<=r["second_read_checked"]
                    and r["held_out_labeled_permits"]==0
                    and r["independent_current_validity_labels"]==0
                    and r["actual_distinct_original_records"]=="UNKNOWN")
        self.assertTrue(safely_degraded(case))
        self.assertEqual((o["sample_count"],o["sample_unique_source_identities"],
                          o["sample_repeated_source_rows"]),(20,18,2))
        self.assertEqual((o["second_read_checked"],o["second_read_exact_match"]),(3,3))
        fabricated=json.loads(json.dumps(case))
        fabricated["observed"]["sample_unique_source_identities"]=20
        self.assertFalse(safely_degraded(fabricated))
        fabricated["observed"]["sample_unique_source_identities"]=18
        fabricated["observed"]["held_out_labeled_permits"]=20
        self.assertFalse(safely_degraded(fabricated))
        controls=case["synthetic_negative_controls"]
        self.assertEqual(len(controls),6)
        self.assertTrue(all(x["kind"]=="SYNTHETIC" for x in controls))
        self.assertFalse(case["consumers"]["production_release_authorized"])


    def test_structural_notice_conditions_do_not_promote_public_permit_rows(self):
        """Official 2026 DOB conditional gates cannot be inferred from five-field readback."""
        candidate=json.loads((Path(__file__).with_name("fixtures") /
                              "nyc_dob_structural_gates_2026_candidate_v0.json")
                             .read_text(encoding="utf-8"))
        notice=candidate["source"]
        self.assertEqual(notice["original_notice_url"],
                         "https://www.nyc.gov/assets/buildings/pdf/stpermits_dn-sn.pdf")
        self.assertEqual((notice["notice_date"],notice["policy_effective_date"]),
                         ("2026-01-21","2026-02-02"))
        self.assertIsNone(notice["original_pdf_sha256"])
        self.assertFalse(notice["original_pdf_bytes_acquired"])
        self.assertFalse(notice["dataset_specific_commercial_use_authorized"])
        scope=candidate["scope"]
        self.assertTrue(scope["notice_not_universal_for_all_permits"])
        self.assertFalse(scope["historical_policy_retroactively_applied"])
        self.assertEqual({x["rule"] for x in scope["gates"]},
                         {"FO_OR_EA_ISSUANCE","ST_ISSUANCE_NB_NBEE_ALTCO",
                          "ST_ISSUANCE_ALT_ENLARGEMENT","ST_RENEWAL"})
        evaluation=candidate["evaluation"]
        historical_projection=tuple(evaluation["current_collector_select"])
        self.assertEqual(historical_projection,
                         ("tracking_number","job_filing_number","work_permit",
                          "issued_date","permit_status"))
        # This documents the captured source head, not a permanent owner contract.
        # A later :48 collector fix adding fields must not break this evidence test.
        self.assertNotIn("work_type",historical_projection)
        self.assertEqual(evaluation["independently_held_out_labeled_cases"],0)
        self.assertIsNone(evaluation["permitplate_precision_recall"])
        self.assertEqual(evaluation["current_permit_validity_truth"],"UNKNOWN")
        controls=candidate["synthetic_negative_controls"]
        self.assertEqual(len(controls),evaluation["synthetic_control_count"])
        self.assertEqual(len(controls),6)
        self.assertEqual(len({c["id"] for c in controls}),len(controls))
        self.assertTrue(all(c["kind"]=="SYNTHETIC" for c in controls))
        for c in controls:
            with self.subTest(control=c["id"]):
                normalized=_minimal(c["projected_row"],date(2026,10,26))
                self.assertEqual(_classification(normalized),"PUBLISHER_ISSUE_DATE_PRESENT")
                self.assertIsNone(c["independent_issuance_label"])
                self.assertIsNone(c["independent_current_validity_label"])
                self.assertIsNone(c["independent_commercial_lead_label"])
                self.assertNotIn("PERMIT_VALID",c["expected_truth_boundary"])
        self.assertEqual(candidate["safety"]["private_customer_rows_stored"],0)
        self.assertEqual(candidate["safety"]["new_provider_calls"],0)
        self.assertFalse(candidate["consumers"]["release_authorized"])


    def test_publisher_unfiltered_same_row_status_placeholder_does_not_prove_issuance(self):
        """One publisher-rendered unfiltered row is not an independent issued permit label."""
        pack=json.loads((Path(__file__).with_name("fixtures") /
                         "nyc_dob_sequence_projection_v1.json")
                        .read_text(encoding="utf-8"))
        item=pack["publisher_unfiltered_placeholder_join_20261026"]
        self.assertEqual(item["official_dataset_id"], DATASET_ID)
        self.assertEqual(item["source_url"],
                         "https://data.cityofnewyork.us/resource/rbx6-tga4.json")
        self.assertIn("UNFILTERED", item["cohort"])
        self.assertFalse(item["collector_filtered_cohort_inclusion_verified"])
        self.assertFalse(item["original_publisher_http_body_acquired"])
        self.assertIsNone(item["original_publisher_http_sha256"])
        self.assertFalse(item["original_permit_row_or_personal_identifiers_stored"])
        self.assertEqual(item["identifying_fields_copied"], [])
        fields=item["material_fields_observed_together"]
        self.assertEqual(fields["work_permit"],"Permit is not yet issued")
        self.assertEqual(fields["permit_status"],"Signed-off")
        self.assertFalse(fields["issued_date_present"])
        self.assertEqual(item["independently_held_out_issuance_labels"],0)
        self.assertIsNone(item["independent_validity_label"])
        self.assertFalse(item["source_specific_commercial_reuse_authorized"])
        case=item["synthetic_negative_control"]
        self.assertEqual(case["kind"],"SYNTHETIC")
        self.assertIsNone(case["issued_date"])
        self.assertIsNone(case["independent_issuance_label"])
        self.assertIsNone(case["independent_current_validity_label"])
        self.assertEqual(case["expected"],
                         "NO_ISSUANCE_OR_CURRENT_VALIDITY_PROMOTION_FROM_STATUS_ALONE")
        # Even if status changes, no dated independent truth is supplied.
        def can_promote(v):
            return (v.get("issued_date") is not None
                    and v.get("independent_issuance_label") is True)
        self.assertFalse(can_promote(case))
        altered=dict(case,permit_status="Permit Issued")
        self.assertFalse(can_promote(altered))


    def test_original_dob_renewal_sequences_are_not_independent_new_permits(self):
        """The DOB 2020 training identifies sequence as renewal iteration, not a new permit."""
        pack=json.loads((Path(__file__).with_name("fixtures") /
                         "nyc_dob_sequence_projection_v1.json")
                        .read_text(encoding="utf-8"))
        doc=pack["publisher_renewal_sequence_training_2020"]
        self.assertEqual(doc["publisher"],"NYC Department of Buildings")
        self.assertEqual(doc["original_document_url"],
                         "https://www.nyc.gov/assets/buildings/pdf/contractor_training_presentation.pdf")
        self.assertEqual((doc["pdf_page_index_zero_based"],doc["slide_number_one_based"]),(71,72))
        self.assertEqual(doc["document_updated_date"],"2020-12-22")
        facts=doc["historical_training_assertions"]
        self.assertTrue(all(facts.values()))
        self.assertFalse(doc["dataset_sequence_field_mapping_to_training_verified"])
        self.assertFalse(doc["nyc_open_data_xlsx_dictionary_original_bytes_acquired"])
        self.assertIsNone(doc["nyc_open_data_xlsx_dictionary_sha256"])
        self.assertFalse(doc["original_publisher_pdf_bytes_acquired"])
        self.assertIsNone(doc["original_publisher_pdf_sha256"])
        self.assertFalse(doc["source_specific_commercial_reuse_authorized"])
        self.assertFalse(doc["same_permit_repeated_renewal_rows_in_original_publisher_cohort_confirmed"])
        self.assertEqual(doc["independently_held_out_new_permit_outcome_labels"],0)
        self.assertEqual(doc["independently_held_out_current_validity_labels"],0)
        self.assertIsNone(doc["permitplate_new_buyer_opportunity_accuracy"])
        self.assertEqual(doc["buyer_demand"],"UNKNOWN")
        controls=doc["synthetic_negative_controls"]
        self.assertEqual(len(controls),2)
        self.assertEqual(len({c["id"] for c in controls}),2)
        self.assertTrue(all(c["kind"]=="SYNTHETIC" for c in controls))
        first=controls[0]
        self.assertEqual(first["initial"]["work_permit"],first["renewal"]["work_permit"])
        self.assertNotEqual(first["initial"]["tracking_number"],first["renewal"]["tracking_number"])
        self.assertEqual(int(first["renewal"]["sequence_number"]),
                         int(first["initial"]["sequence_number"])+1)
        self.assertIsNone(first["independent_new_permit_label"])
        self.assertIsNone(first["independent_current_validity_label"])
        self.assertIn("NOT_TWO_INDEPENDENT_NEW_PERMIT_OPPORTUNITIES",first["expected"])
        second=controls[1]
        self.assertFalse(second["projection"]["sequence_number_selected"])
        self.assertIn("UNKNOWN",second["expected"])
        self.assertIsNone(second["independent_current_validity_label"])
        self.assertFalse(doc["engine_code_edited"])
        self.assertEqual((doc["extra_provider_calls"],doc["new_workflows"]),(0,0))
        self.assertFalse(doc["release_authorized"])


    def test_publisher_sequence_counts_do_not_define_renewal_labels(self):
        """Dataset-wide source marginals disprove an exact renewal/sequence proxy."""
        pack=json.loads((Path(__file__).with_name("fixtures") /
                         "nyc_dob_sequence_projection_v1.json")
                        .read_text(encoding="utf-8"))
        p=pack["publisher_cached_sequence_reason_marginal_non_equivalence_20261026"]
        self.assertEqual(p["dataset_id"],DATASET_ID)
        self.assertEqual(p["source_schema"],
                         {"sequence_number":"text","filing_reason":"text"})
        self.assertFalse(p["publisher_metadata_raw_bytes_acquired"])
        self.assertIsNone(p["publisher_metadata_sha256"])
        self.assertFalse(p["attached_data_dictionary_original_bytes_acquired"])
        self.assertIsNone(p["attached_data_dictionary_sha256"])
        self.assertIn("HELD",p["source_admission"])
        n=p["counts"]
        self.assertEqual(n["total"],1020152)
        self.assertEqual(n["sequence_non_null"]+n["sequence_null"],n["total"])
        not_one=n["sequence_non_null"]-n["sequence_value_one"]
        renewals=(n["filing_renewal_without_changes"]
                  +n["filing_renewal_with_changes"])
        self.assertEqual(not_one,n["sequence_other_non_null"])
        self.assertEqual(renewals,n["filing_renewal_total"])
        self.assertEqual(renewals-not_one,n["minimum_non_equivalence_count"])
        self.assertEqual(n["minimum_non_equivalence_count"],130)
        self.assertGreater(renewals,not_one)
        self.assertEqual(p["actual_mismatch_rows_or_direction"],
                         "UNKNOWN_NOT_IDENTIFIED_BY_MARGINAL_COUNTS")
        self.assertEqual(p["independently_held_out_labeled_permit_or_lead_cases"],0)
        self.assertEqual(p["real_permit_rows_or_personal_identifiers_stored"],0)
        cases=p["synthetic_negative_controls"]
        self.assertEqual(len(cases),2)
        self.assertEqual(len({x["id"] for x in cases}),len(cases))
        self.assertTrue(all(x["kind"]=="SYNTHETIC" for x in cases))
        self.assertTrue(all(x["independent_ground_truth"] is None for x in cases))
        self.assertNotEqual(cases[0]["filing_reason"].startswith("Initial"),
                            cases[1]["filing_reason"].startswith("Initial"))


if __name__=="__main__":
    unittest.main()
