"""Adversarial source-grain tests for public USAspending contract award readback."""
from __future__ import annotations

import copy
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from unittest.mock import patch

from freight.official_capturebrief_award_lab import (
    API, DETAIL_PREFIX, MAX_DETAIL_BYTES, FIXED_WINDOW, MAX_ROWS, MAX_SECOND_READS, MAX_RESPONSE_BYTES,
    SOURCE_ANCHOR, SCOPE, _check_query, _minimal, _money_minor, _query,
    _detail_identity_and_amount_consistent, build_receipt,
    fetch_public_awards, fetch_public_award_detail, run, validate_receipt,
)
from freight.unified_research_lab import (
    ResearchError, digest, ledger_from, source_record,
)

NOW = datetime.now(timezone.utc).date()
FAKE_SOURCE = [
    {"internal_id": 10013, "Award ID": "FA-2026-A013",
     "generated_internal_id": "CONT_AWD_FA2026A013_4568_1234",
     "Award Amount": 1500000.25, "Base Obligation Date": "2026-06-01"},
    {"internal_id": 10014, "Award ID": "47QT-2026-A141",
     "generated_internal_id": "CONT_AWD_47QT2026A141_4852_2468",
     "Award Amount": -125.13, "Base Obligation Date": "2026-04-11"},
    {"internal_id": 10015, "Award ID": "W91Q-2026-0002",
     "generated_internal_id": "CONT_AWD_W91Q20260002_9024_1890",
     "Award Amount": 245000.00, "Base Obligation Date": "2026-07-18"},
]


def ledger():
    return ledger_from([source_record(
        SOURCE_ANCHOR, "capturebrief", "2026-10-23"
    )])


def fake_api(query):
    assert _check_query(query) == query
    ids = query["filters"].get("award_ids")
    if ids is None:
        return copy.deepcopy(FAKE_SOURCE)
    search = ids[0].strip('"')
    return [copy.deepcopy(row) for row in FAKE_SOURCE
            if row["Award ID"] == search]


class OriginalUSAspendingAwardReadbackTests(unittest.TestCase):
    def test_fixed_publisher_scope_exact_filters_no_unrestricted_search(self):
        query = _query()
        self.assertEqual(query["filters"]["award_type_codes"], ["A", "B", "C", "D"])
        self.assertEqual(query["filters"]["time_period"],
                         [{"start_date": FIXED_WINDOW[0], "end_date": FIXED_WINDOW[1]}])
        self.assertEqual(query["limit"], MAX_ROWS)
        self.assertEqual(query["order"], "desc")
        self.assertEqual(urlparse(API).hostname, "api.usaspending.gov")
        self.assertEqual(_check_query(query), query)
        for mutated in (
            {**query, "limit": 1000},
            {**query, "fields": ["Recipient UEI", "Recipient Name"]},
            {**query, "page": 2},
            {**query, "filters": {**query["filters"], "award_type_codes": ["02"]}},
            {**query, "filters": {**query["filters"], "award_ids": ['"id" OR 1=1']}},
        ):
            with self.subTest(payload=mutated), self.assertRaises(ResearchError):
                _check_query(mutated)
        for bad in ("", 'bad" or "1=1', "../private", "a@example.com",
                    " 47Q-A123", "a" * 200):
            with self.subTest(award=bad), self.assertRaises(ResearchError):
                _query(exact_award_id=bad)

    def test_complete_original_publisher_contract_sample_matches_bounded_second_reads(self):
        result = build_receipt(ledger(), as_of=NOW, fetcher=fake_api)
        self.assertEqual(result["schema_version"], 1)
        self.assertEqual(result["scope"], SCOPE)
        self.assertEqual(result["status"], "PUBLISHER_AWARD_READBACK_OK")
        self.assertEqual(result["sample_rows"], 3)
        self.assertEqual(result["distinct_award_internal_ids"], 3)
        self.assertEqual(result["repeated_source_rows"], 0)
        self.assertEqual(result["publisher_readbacks_attempted"], MAX_SECOND_READS)
        self.assertEqual(result["publisher_readbacks_exact"], MAX_SECOND_READS)
        self.assertEqual(result["sample_net_awarded_amount_minor"],
                         150000025 - 12513 + 24500000)
        self.assertEqual(result["publisher_source_anchor_id"],
                         ledger()["entries"][0]["id"])
        self.assertFalse(result["source_specific_commercial_reuse_verified"])
        self.assertEqual(result["independent_award_outcome_labels"], 0)
        self.assertEqual(result["recipient_identifiers_stored"], 0)
        self.assertEqual(result["source_payloads_stored"], 0)
        self.assertEqual(result["buyer_opportunity_truth"], False)
        self.assertEqual(result["receipt_sha256"],
                         digest({k:v for k,v in result.items()
                                 if k != "receipt_sha256"}))
        self.assertNotIn("FA-2026-A013", str(result))
        self.assertNotIn("47QT-2026-A141", str(result))
        self.assertNotIn("generated_internal_id", str(result))
        validate_receipt(result, ledger(), NOW)

    def test_duplicate_award_rows_are_not_independent_cases(self):
        def double_search(query):
            return ([copy.deepcopy(FAKE_SOURCE[0]) for _ in range(2)]
                    + [copy.deepcopy(FAKE_SOURCE[1])]) if (
                "award_ids" not in query["filters"]) else fake_api(query)
        result = build_receipt(ledger(), as_of=NOW, fetcher=double_search)
        self.assertEqual(result["sample_rows"], 3)
        self.assertEqual(result["distinct_award_internal_ids"], 2)
        self.assertEqual(result["repeated_source_rows"], 1)
        self.assertEqual(result["publisher_readbacks_attempted"], 1)
        self.assertEqual(result["publisher_readbacks_exact"], 1)
        self.assertEqual(result["status"], "PUBLISHER_AWARD_READBACK_DEGRADED")
        self.assertEqual(result["source_errors"], ["REPEATED_AWARD_SOURCE_ROWS"])
        validate_receipt(result, ledger(), NOW)

    def test_changed_publisher_award_amount_is_not_source_consistent(self):
        def changed(query):
            if "award_ids" not in query["filters"]:
                return fake_api(query)
            subset = fake_api(query)
            return [{**row, "Award Amount": 999999.99} for row in subset]
        result = build_receipt(ledger(), as_of=NOW, fetcher=changed)
        self.assertEqual(result["publisher_readbacks_changed"], 2)
        self.assertEqual(result["publisher_readbacks_exact"], 0)
        self.assertEqual(result["status"], "PUBLISHER_AWARD_READBACK_DEGRADED")
        self.assertEqual(result["source_errors"], ["READBACK_INCOMPLETE"])
        validate_receipt(result, ledger(), NOW)

    def test_saturated_award_id_matches_are_ambiguous_not_exact(self):
        def saturated(query):
            if "award_ids" not in query["filters"]:
                return [FAKE_SOURCE[0]]
            return [FAKE_SOURCE[0]] * 20
        result = build_receipt(ledger(), as_of=NOW, fetcher=saturated)
        self.assertEqual(result["publisher_readbacks_ambiguous"], 1)
        self.assertEqual(result["publisher_readbacks_exact"], 0)
        self.assertEqual(result["publisher_readbacks_attempted"], 1)
        self.assertEqual(result["status"], "PUBLISHER_AWARD_READBACK_DEGRADED")
        validate_receipt(result, ledger(), NOW)

    def test_provider_unavailable_does_not_fabricate_award_or_rights(self):
        def unavailable(_):
            raise ResearchError("HTTP_STATUS")
        result = build_receipt(ledger(), as_of=NOW, fetcher=unavailable)
        self.assertEqual(result["sample_rows"], 0)
        self.assertIsNone(result["source_canonical_sample_sha256"])
        self.assertEqual(result["status"], "PUBLISHER_AWARD_READBACK_DEGRADED")
        self.assertEqual(result["source_errors"], ["HTTP_STATUS"])
        self.assertEqual(result["publisher_readbacks_attempted"], 0)
        self.assertFalse(result["source_specific_commercial_reuse_verified"])
        validate_receipt(result, ledger(), NOW)

    def test_malformed_provider_identity_amount_and_dates_fail_closed(self):
        for mutation in (
            {"internal_id": 0}, {"internal_id": "1"},
            {"Award ID": "../unsafe"}, {"Award ID": None},
            {"Award Amount": float("nan")}, {"Award Amount": "1.234"},
            {"Award Amount": "1e120"},
            {"Base Obligation Date": "not-a-date"},
            {"generated_internal_id": "\nINJECTION"},
        ):
            value = {**FAKE_SOURCE[0], **mutation}
            with self.subTest(mutation=mutation), self.assertRaises(ResearchError):
                _minimal(value)
        self.assertEqual(_money_minor("0.01"), 1)
        self.assertEqual(_money_minor("-0.01"), -1)

    def test_receipt_rights_truth_recovery_and_tamper_guards_enforced(self):
        report = build_receipt(ledger(), as_of=NOW, fetcher=fake_api)
        for key, value in (
            ("source_specific_commercial_reuse_verified", True),
            ("buyer_opportunity_truth", True),
            ("independent_sam_solicitation_matches", 1),
            ("independent_award_outcome_labels", 1),
            ("recipient_identifiers_stored", 1),
            ("realized_recovery_cents", 1),
            ("new_paid_services", 1),
            ("sample_rows", 999),
            ("publisher_readbacks_exact", 99),
            ("publisher_source_anchor_id", "x" * 64),
            ("status", "PUBLISHER_AWARD_READBACK_OK_WITHOUT_EVIDENCE"),
        ):
            tampered = copy.deepcopy(report)
            tampered[key] = value
            tampered["receipt_sha256"] = digest(
                {k:v for k,v in tampered.items() if k != "receipt_sha256"})
            with self.subTest(key=key), self.assertRaises(ResearchError):
                validate_receipt(tampered, ledger(), NOW)

    def test_exact_day_repeated_run_cache_and_fail_closed_corrupted_receipt(self):
        tracked = []
        def provider(query):
            tracked.append(query)
            return fake_api(query)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root/"leads.json"
            dest = root/"capturebrief_awards.json"
            source.write_text(json.dumps(ledger()), encoding="utf-8")
            first = run(ledger_path=source, output=dest,
                        fetcher=provider, as_of=NOW)
            self.assertEqual(first["sample_contract_awards"], 3)
            self.assertEqual(len(tracked), 3)
            original_bytes = dest.read_bytes()
            again = run(ledger_path=source, output=dest,
                        fetcher=provider, as_of=NOW)
            self.assertEqual(original_bytes, dest.read_bytes())
            self.assertEqual(len(tracked), 3)
            self.assertTrue(run(ledger_path=source, output=dest,
                                verify_only=True)["verified"])
            malicious = json.loads(dest.read_text(encoding="utf-8"))
            malicious["independent_award_outcome_labels"] = 999
            malicious["receipt_sha256"] = digest(
                {k:v for k,v in malicious.items() if k != "receipt_sha256"})
            dest.write_text(json.dumps(malicious), encoding="utf-8")
            with self.assertRaises(ResearchError):
                run(ledger_path=source, output=dest, verify_only=True)
            repaired = run(ledger_path=source, output=dest,
                           fetcher=provider, as_of=NOW)
            self.assertEqual(repaired["status"], "PUBLISHER_AWARD_READBACK_OK")
            self.assertEqual(len(tracked), 6)

    def test_unpinned_publisher_anchor_cannot_run_network_probes(self):
        other = ledger_from([source_record(
            "https://sam.gov/opportunities", "capturebrief", "2026-10-22"
        )])
        with self.assertRaisesRegex(ResearchError, "OFFICIAL_USASPENDING_ANCHOR_MISSING"):
            build_receipt(other, as_of=NOW, fetcher=lambda _: (_ for _ in ()).throw(
                AssertionError("UNAUTHORIZED_NETWORK_REQUEST")))

    def test_fixed_public_host_post_rejects_redirects_and_bounded_response(self):
        class Response:
            status = 200
            headers = {"Content-Type": "application/json",
                       "Content-Encoding": "identity"}
            def __init__(self, url, content):
                self.url, self.body = url, content
            def __enter__(self):
                return self
            def __exit__(self, *_):
                return None
            def geturl(self):
                return self.url
            def read(self, maxlen):
                self.maxlen = maxlen
                return self.body[:maxlen]
        class Opener:
            def open(self, request, timeout):
                self.method = request.get_method()
                self.url = request.full_url
                self.timeout = timeout
                self.sent = json.loads(request.data)
                return Response(self.url, json.dumps(
                    {"results": FAKE_SOURCE}).encode("utf-8"))
        opener = Opener()
        with patch("freight.official_capturebrief_award_lab.global_dns",
                   return_value=None), patch(
                "freight.official_capturebrief_award_lab.build_opener",
                return_value=opener):
            result = fetch_public_awards(_query())
        self.assertEqual(len(result), 3)
        self.assertEqual(opener.method, "POST")
        self.assertEqual(opener.url, API)
        self.assertEqual(opener.timeout, 12)
        self.assertEqual(opener.sent, _query())
        self.assertEqual(MAX_RESPONSE_BYTES, 220000)


    def test_secondary_http_code_classes_are_redacted_aggregated_and_not_claimed_exact(self):
        def reject_secondary(query):
            if "award_ids" not in query["filters"]:
                return fake_api(query)
            raise ResearchError("HTTP_400")
        receipt = build_receipt(ledger(), as_of=NOW, fetcher=reject_secondary)
        self.assertEqual(receipt["sample_rows"], 3)
        self.assertEqual(receipt["publisher_readbacks_unavailable"], 2)
        self.assertEqual(receipt["publisher_readback_error_codes"], {"HTTP_400": 2})
        self.assertEqual(receipt["source_errors"], ["READBACK_INCOMPLETE"])
        self.assertEqual(receipt["status"], "PUBLISHER_AWARD_READBACK_DEGRADED")
        validate_receipt(receipt, ledger(), NOW)
        for bad in ({"HTTP_400": 3}, {"PRIVATE_AWARD_ID=123": 2}, {"HTTP_400": True}):
            forged = copy.deepcopy(receipt)
            forged["publisher_readback_error_codes"] = bad
            forged["receipt_sha256"] = digest({
                k: v for k, v in forged.items() if k != "receipt_sha256"})
            with self.subTest(bad=bad), self.assertRaises(ResearchError):
                validate_receipt(forged, ledger(), NOW)

    def test_only_known_http_failure_codes_survive_publisher_transport(self):
        from urllib.error import HTTPError
        def throw_429(*_args, **_kwargs):
            raise HTTPError(API, 429, "PRIVATE-ID=do-not-log", hdrs=None, fp=None)
        class ErroringOpener:
            open = staticmethod(throw_429)
        with patch("freight.official_capturebrief_award_lab.global_dns",
                   return_value=None), patch(
                "freight.official_capturebrief_award_lab.build_opener",
                return_value=ErroringOpener()):
            with self.assertRaisesRegex(ResearchError, "^HTTP_429$"):
                fetch_public_awards(_query())


    def test_503_exact_search_uses_documented_get_detail_as_separate_partial_evidence(self):
        attempts = []
        def throttled_secondary(query):
            if "award_ids" not in query["filters"]:
                return fake_api(query)
            raise ResearchError("HTTP_503")
        def detail_provider(internal):
            attempts.append(internal)
            row = next(x for x in FAKE_SOURCE if x["internal_id"] == internal)
            return {
                "id": internal,
                "piid": row["Award ID"],
                "generated_unique_award_id": row["generated_internal_id"],
                "total_obligation": row["Award Amount"],
                "date_signed": "2026-06-01",
                "recipient": {"recipient_name": "NOT FOR STORAGE"},
            }
        receipt = build_receipt(ledger(), as_of=NOW, fetcher=throttled_secondary,
                                detail_fetcher=detail_provider)
        self.assertEqual(len(attempts), 2)
        self.assertEqual(receipt["publisher_readbacks_unavailable"], 2)
        self.assertEqual(receipt["publisher_readbacks_exact"], 0)
        self.assertEqual(receipt["publisher_readback_error_codes"], {"HTTP_503": 2})
        self.assertEqual(receipt["publisher_detail_lookup_attempted"], 2)
        self.assertEqual(receipt["publisher_detail_identity_amount_matched"], 2)
        self.assertEqual(receipt["publisher_detail_changed"], 0)
        self.assertEqual(receipt["publisher_detail_unavailable"], 0)
        self.assertEqual(receipt["publisher_detail_error_codes"], {})
        self.assertEqual(receipt["status"], "PUBLISHER_AWARD_READBACK_DEGRADED")
        self.assertNotIn("NOT FOR STORAGE", str(receipt))
        self.assertNotIn("FA-2026-A013", str(receipt))
        self.assertEqual(receipt["independent_award_outcome_labels"], 0)
        validate_receipt(receipt, ledger(), NOW)

    def test_detail_get_does_not_promote_different_amount_or_identity(self):
        def throttled_secondary(query):
            if "award_ids" not in query["filters"]:
                return [FAKE_SOURCE[0]]
            raise ResearchError("HTTP_503")
        detail = {
            "id": FAKE_SOURCE[0]["internal_id"],
            "piid": FAKE_SOURCE[0]["Award ID"],
            "generated_unique_award_id": FAKE_SOURCE[0]["generated_internal_id"],
            "total_obligation": FAKE_SOURCE[0]["Award Amount"] + 1,
        }
        self.assertFalse(_detail_identity_and_amount_consistent(_minimal(FAKE_SOURCE[0]),detail))
        receipt = build_receipt(ledger(), as_of=NOW, fetcher=throttled_secondary,
                                detail_fetcher=lambda _: detail)
        self.assertEqual(receipt["publisher_detail_lookup_attempted"], 1)
        self.assertEqual(receipt["publisher_detail_changed"], 1)
        self.assertEqual(receipt["publisher_detail_identity_amount_matched"], 0)
        self.assertEqual(receipt["independent_sam_solicitation_matches"], 0)
        validate_receipt(receipt,ledger(),NOW)

    def test_detail_get_failure_cannot_suppress_503_or_forge_original_record(self):
        def throttled(query):
            if "award_ids" not in query["filters"]:
                return [FAKE_SOURCE[0]]
            raise ResearchError("HTTP_503")
        receipt = build_receipt(ledger(),as_of=NOW,fetcher=throttled,
                                detail_fetcher=lambda _: (_ for _ in ()).throw(
                                    ResearchError("HTTP_429")))
        self.assertEqual(receipt["publisher_readbacks_unavailable"],1)
        self.assertEqual(receipt["publisher_detail_lookup_attempted"],1)
        self.assertEqual(receipt["publisher_detail_unavailable"],1)
        self.assertEqual(receipt["publisher_detail_error_codes"],{"HTTP_429":1})
        self.assertEqual(receipt["source_errors"],["READBACK_INCOMPLETE"])
        validate_receipt(receipt,ledger(),NOW)
        for field,value in (
            ("publisher_detail_identity_amount_matched",2),
            ("publisher_detail_lookup_attempted",0),
            ("publisher_detail_error_codes",{"SOURCE_SECRET":1}),
        ):
            tampered=copy.deepcopy(receipt)
            tampered[field]=value
            tampered["receipt_sha256"]=digest({
                k:v for k,v in tampered.items() if k!="receipt_sha256"})
            with self.subTest(field=field),self.assertRaises(ResearchError):
                validate_receipt(tampered,ledger(),NOW)

    def test_documented_detail_get_is_strict_fixed_origin_read_only_and_bounded(self):
        from urllib.error import HTTPError
        for bad in (0,-1,1.1,"123","1 OR 1=1",10**17):
            with self.subTest(bad=bad),self.assertRaisesRegex(
                    ResearchError,"UNSAFE_PUBLISHER_DETAIL_ID"):
                fetch_public_award_detail(bad)
        requested = []
        class Response:
            status=200
            headers={"Content-Type":"application/json","Content-Encoding":"identity"}
            def __enter__(self):return self
            def __exit__(self,*_):return None
            def geturl(self):return DETAIL_PREFIX+"10013/"
            def read(self,n):
                requested.append(n)
                return json.dumps({
                    "id":10013, "piid":"FA-2026-A013",
                    "total_obligation":1500000.25,
                    "recipient":{"recipient_name":"SENSITIVE NOT SAVED"}
                }).encode("utf-8")
        class Opener:
            def open(self,request,timeout):
                requested.append((request.get_method(),request.full_url,timeout))
                return Response()
        with patch("freight.official_capturebrief_award_lab.global_dns"),\
             patch("freight.official_capturebrief_award_lab.build_opener",
                   return_value=Opener()):
            body=fetch_public_award_detail(10013)
        self.assertEqual(body["id"],10013)
        self.assertEqual(requested[0],("GET",DETAIL_PREFIX+"10013/",12))
        self.assertEqual(requested[1],MAX_DETAIL_BYTES+1)
        self.assertGreaterEqual(MAX_DETAIL_BYTES,220000)



if __name__ == "__main__":
    unittest.main()
