"""Adverse read-only acceptance tests against CaptureBrief's pinned producer format."""

from __future__ import annotations

import copy
from datetime import datetime, timedelta, timezone
import hashlib
import json
import unittest

from ai_business_os.retally_capturebrief import (
    CaptureBriefObservationError, CaptureBriefOutcomeReader,
)

NOW = datetime(2026, 10, 20, 21, 0, tzinfo=timezone.utc)
OBSERVED = "2026-10-20T20:30:00+00:00"
GENESIS = "0"*64
CASE_SHA = "a"*64
BUNDLE = "b"*64


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def event(kind, *, case="CB-SYNTHETIC", case_sha=CASE_SHA, bundle=None,
          at="2026-10-20T19:30:00Z", data=None):
    samples = {
        "PAYMENT": {"state": "PAID", "payment_evidence_ref": "processor:synthetic-receipt", "amount_cents": 14900, "currency": "USD"},
        "DELIVERY": {"started_at": "2026-10-20T18:00:00Z", "delivered_at": "2026-10-20T19:00:00Z", "delivery_evidence_ref": "delivery:synthetic-receipt"},
        "FEEDBACK": {"usefulness": "USEFUL", "action_effect": "CHANGED_ACTION", "source_limited": False, "finding_classes": ["ASSUMPTION"], "feedback_evidence_ref": "feedback:synthetic-receipt"},
        "RETRACTION": {"severity": "CRITICAL", "reason_code": "WRONG_SOURCE", "retraction_evidence_ref": "retraction:synthetic-receipt"},
        "REPEAT_REQUEST": {"state": "REQUESTED_REPEAT", "repeat_evidence_ref": "repeat:synthetic-receipt"},
        "EFFORT": {"stage": "DELIVERY", "minutes": 25, "effort_evidence_ref": "timer:synthetic-receipt"},
    }
    return {"schema_version": "1.0", "case_id": case, "case_sha256": case_sha,
            "event_type": kind, "event_at": at,
            "delivery_bundle_sha256": bundle if bundle is not None else (BUNDLE if kind in {"DELIVERY", "FEEDBACK", "RETRACTION", "REPEAT_REQUEST"} else None),
            "data": samples[kind] if data is None else data}


def producer_ledger(*events):
    lines = []
    previous = GENESIS
    for item in events:
        body = {"ledger_version": "capturebrief-evidence-ledger-v1", "record_type": "CAPTUREBRIEF_OUTCOME_EVENT",
                "recorded_at": "2026-10-20T20:00:00+00:00", "previous_record_sha256": previous,
                "payload_sha256": digest(canonical(item)), "payload": item}
        body["record_sha256"] = digest(canonical(body))
        lines.append(json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False))
        previous = body["record_sha256"]
    return ("\n".join(lines) + ("\n" if lines else "")).encode()


def snapshot(raw=b"", *, observed=OBSERVED):
    return {"present": True, "content": raw, "snapshot_sha256": digest(raw), "observed_at": observed}


class SnapshotReaderTests(unittest.TestCase):
    def reader(self, data):
        return CaptureBriefOutcomeReader(lambda: copy.deepcopy(data))

    def test_genuinely_present_empty_snapshot_not_missing_file(self):
        got = self.reader(snapshot()).observe(now=NOW)
        self.assertEqual("PRESENT_EMPTY", got["snapshot_presence"])
        self.assertEqual(0, got["ledger_record_count"])
        self.assertEqual(GENESIS, got["ledger_head_sha256"])
        self.assertEqual(0, got["distinct_case_count_not_customer_count"])
        self.assertTrue(all(v is None for v in got["verified_metrics"].values()))
        self.assertEqual("NOT_CONNECTED", got["account_identity_binding"])
        self.assertEqual("UNVERIFIED_BY_READER", got["source_authenticity"])

    def test_missing_or_unavailable_is_never_misreported_as_empty(self):
        for bad in (None, {}, {"present": False, "content": b"", "snapshot_sha256": digest(b""), "observed_at": OBSERVED},
                    {"present": True, "snapshot_sha256": digest(b""), "observed_at": OBSERVED},
                    {"present": True, "content": None, "snapshot_sha256": digest(b""), "observed_at": OBSERVED},
                    {"present": True, "content": b"", "snapshot_sha256": "deadbeef", "observed_at": OBSERVED}):
            with self.subTest(bad=bad), self.assertRaises(CaptureBriefObservationError):
                self.reader(bad).observe(now=NOW)

    def test_provider_failure_cannot_leak_sensitive_exception(self):
        def failing():
            raise RuntimeError("secret-token=real-contact@example.com")
        with self.assertRaises(CaptureBriefObservationError) as caught:
            CaptureBriefOutcomeReader(failing).observe(now=NOW)
        self.assertEqual("CaptureBrief immutable outcome snapshot could not be validated", str(caught.exception))
        self.assertTrue(caught.exception.__suppress_context__)

    def test_wrong_config_and_clock_fail_closed(self):
        for reader, age in ((None, 60), (lambda: None, 0), (lambda: None, True), (lambda: None, -10)):
            with self.subTest(reader=reader, age=age), self.assertRaises(CaptureBriefObservationError):
                CaptureBriefOutcomeReader(reader, max_age_seconds=age)
        with self.assertRaises(CaptureBriefObservationError):
            self.reader(snapshot()).observe(now=NOW.replace(tzinfo=None))

    def test_invalid_timestamp_and_staleness_boundaries(self):
        for observed in ("2026-10-20", "2026-10-20T20:00:00", "2026-10-20T19:00:00-00:00", "2026-10-20T21:00:01Z", "evil"):
            with self.subTest(observed=observed), self.assertRaises(CaptureBriefObservationError):
                self.reader(snapshot(observed=observed)).observe(now=NOW)
        older = (NOW - timedelta(days=2)).isoformat()
        result = self.reader(snapshot(observed=older)).observe(now=NOW)
        self.assertEqual("STALE", result["freshness"])
        self.assertGreater(result["source_age_seconds"], 86400)

    def test_digest_and_size_mismatch_rejected(self):
        bad = snapshot(b"content")
        bad["snapshot_sha256"] = "a"*64
        with self.assertRaises(CaptureBriefObservationError):
            self.reader(bad).observe(now=NOW)
        huge = snapshot(b"" + b"a" * (16 * 1024 * 1024 + 1))
        with self.assertRaises(CaptureBriefObservationError):
            self.reader(huge).observe(now=NOW)

    def test_producer_format_checks_complete_chain_and_never_reports_cash(self):
        raw = producer_ledger(event("PAYMENT"), event("DELIVERY"), event("FEEDBACK"), event("REPEAT_REQUEST"), event("EFFORT"))
        got = self.reader(snapshot(raw)).observe(now=NOW)
        self.assertEqual(5, got["ledger_record_count"])
        self.assertEqual(5, got["outcome_event_count"])
        self.assertEqual(1, got["distinct_case_count_not_customer_count"])
        self.assertEqual(0, got["unbound_postdelivery_event_count"])
        self.assertEqual(1, got["event_counts"]["PAYMENT"])
        self.assertEqual("NOT_INDEPENDENTLY_VERIFIED", got["payment_settlement"])
        self.assertIsNone(got["verified_metrics"]["cash_collected"])
        self.assertFalse(any(got["authority"].values()))
        rendered = json.dumps(got)
        self.assertNotIn("CB-SYNTHETIC", rendered)
        self.assertNotIn("processor:synthetic", rendered)
        self.assertNotIn("14900", rendered)

    def test_missing_delivery_binding_is_surfaced_not_promoted(self):
        raw = producer_ledger(event("FEEDBACK"), event("REPEAT_REQUEST"), event("PAYMENT"))
        got = self.reader(snapshot(raw)).observe(now=NOW)
        self.assertEqual(2, got["unbound_postdelivery_event_count"])
        self.assertEqual(1, got["event_counts"]["PAYMENT"])
        self.assertIsNone(got["verified_metrics"]["paying_customers"])

    def test_payment_status_is_a_declaration_even_for_refunds(self):
        refund = event("PAYMENT", data={"state": "REFUNDED", "payment_evidence_ref": "refund:synthetic"})
        got = self.reader(snapshot(producer_ledger(event("PAYMENT"), refund))).observe(now=NOW)
        self.assertEqual(2, got["event_counts"]["PAYMENT"])
        self.assertIsNone(got["verified_metrics"]["cash_collected"])

    def test_tampering_and_chain_breaks_fail(self):
        raw = producer_ledger(event("PAYMENT"), event("DELIVERY"))
        lines = [json.loads(x) for x in raw.decode().splitlines()]
        for mutation in ("payload", "record", "link", "version"):
            copy_rows = copy.deepcopy(lines)
            if mutation == "payload":
                copy_rows[0]["payload"]["data"]["amount_cents"] = 999
            if mutation == "record":
                copy_rows[1]["record_sha256"] = "c"*64
            if mutation == "link":
                copy_rows[1]["previous_record_sha256"] = GENESIS
            if mutation == "version":
                copy_rows[0]["ledger_version"] = "not-the-producer-version"
            broken = ("\n".join(json.dumps(x) for x in copy_rows)+"\n").encode()
            with self.subTest(mutation=mutation), self.assertRaises(CaptureBriefObservationError):
                self.reader(snapshot(broken)).observe(now=NOW)

    def test_duplicate_json_keys_and_incomplete_lines_fail(self):
        raw = producer_ledger(event("PAYMENT"))
        with self.assertRaises(CaptureBriefObservationError):
            self.reader(snapshot(raw.rstrip(b"\n"))).observe(now=NOW)
        duplicated = raw.replace(b'"ledger_version":', b'"ledger_version":"extra","ledger_version":', 1)
        with self.assertRaises(CaptureBriefObservationError):
            self.reader(snapshot(duplicated)).observe(now=NOW)
        with self.assertRaises(CaptureBriefObservationError):
            self.reader(snapshot(raw + b"\n")).observe(now=NOW)
        with self.assertRaises(CaptureBriefObservationError):
            self.reader(snapshot(b"\xff\n")).observe(now=NOW)

    def test_wrong_case_fingerprint_rejected_even_if_chain_consistent(self):
        raw = producer_ledger(event("PAYMENT"), event("EFFORT", case_sha="f"*64))
        with self.assertRaises(CaptureBriefObservationError):
            self.reader(snapshot(raw)).observe(now=NOW)

    def test_disallowed_contact_keys_invalid_even_with_fully_rehashed_chain(self):
        bad = event("PAYMENT")
        bad["data"]["customer_email"] = "secret@company.test"
        with self.assertRaises(CaptureBriefObservationError) as caught:
            self.reader(snapshot(producer_ledger(bad))).observe(now=NOW)
        self.assertNotIn("secret", str(caught.exception))

    def test_future_event_and_reversed_delivery_invalid_even_when_hashedup(self):
        future = event("PAYMENT", at="2026-10-20T22:00:00Z")
        with self.assertRaises(CaptureBriefObservationError):
            self.reader(snapshot(producer_ledger(future))).observe(now=NOW)
        bad = event("DELIVERY", data={"started_at": "2026-10-20T19:01:00Z", "delivered_at": "2026-10-20T19:00:00Z", "delivery_evidence_ref": "delivery:synthetic"})
        with self.assertRaises(CaptureBriefObservationError):
            self.reader(snapshot(producer_ledger(bad))).observe(now=NOW)

    def test_source_continuity_blocks_rewind_and_history_rewrite(self):
        e1, e2, e3 = event("PAYMENT"), event("DELIVERY"), event("FEEDBACK")
        s1 = snapshot(producer_ledger(e1, e2), observed="2026-10-20T20:00:00Z")
        s2 = snapshot(producer_ledger(e1, e2, e3), observed="2026-10-20T20:30:00Z")
        current = [s1]
        reader = CaptureBriefOutcomeReader(lambda: copy.deepcopy(current[0]))
        reader.observe(now=NOW)
        current[0] = s2
        self.assertEqual(3, reader.observe(now=NOW)["ledger_record_count"])
        current[0] = s1
        with self.assertRaises(CaptureBriefObservationError):
            reader.observe(now=NOW)
        current[0] = snapshot(producer_ledger(event("PAYMENT", case="CB-OTHER"), e2, e3), observed="2026-10-20T20:40:00Z")
        with self.assertRaises(CaptureBriefObservationError):
            reader.observe(now=NOW)

    def test_same_length_modified_snapshot_and_failed_read_do_not_advance_checkpoint(self):
        raw = producer_ledger(event("PAYMENT"))
        source = [snapshot(raw)]
        reader = CaptureBriefOutcomeReader(lambda: copy.deepcopy(source[0]))
        reader.observe(now=NOW)
        source[0] = snapshot(producer_ledger(event("PAYMENT", case="CB-REWRITTEN")))
        with self.assertRaises(CaptureBriefObservationError):
            reader.observe(now=NOW)
        source[0] = snapshot(raw)
        self.assertEqual(1, reader.observe(now=NOW)["outcome_event_count"])

    def test_reader_never_reads_local_paths_and_unknown_ledger_is_not_connected(self):
        calls = []
        source = snapshot(producer_ledger(event("PAYMENT")))
        def read_only():
            calls.append("immutable_snapshot")
            return copy.deepcopy(source)
        reader = CaptureBriefOutcomeReader(read_only)
        result = reader.observe(now=NOW)
        self.assertEqual(["immutable_snapshot"], calls)
        self.assertEqual("NOT_CONNECTED", result["account_identity_binding"])
        self.assertEqual("UNVERIFIED_BY_READER", result["source_authenticity"])


if __name__ == "__main__":
    unittest.main()
