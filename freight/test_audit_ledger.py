from dataclasses import replace

import pytest

from freight.audit_ledger import (
    AuditEventType,
    append_record,
    chain_head,
    verify_chain,
)


BUYER = "buyer-a"
BU = "bu-a"


def test_append_only_chain_verifies():
    records = ()
    records = append_record(
        records,
        buyer_id=BUYER,
        business_unit=BU,
        event_type=AuditEventType.SOURCE_PRESENT,
        object_id="source-1",
        occurred_at="2026-09-20T12:00:00Z",
        evidence_hash="a" * 64,
    )
    records = append_record(
        records,
        buyer_id=BUYER,
        business_unit=BU,
        event_type=AuditEventType.TRUTH_FROZEN,
        object_id="truth-1",
        occurred_at="2026-09-20T12:05:00Z",
        evidence_hash="b" * 64,
    )
    verify_chain(records, buyer_id=BUYER, business_unit=BU)
    assert records[0].sequence == 1
    assert records[1].sequence == 2
    assert records[1].previous_hash == records[0].event_hash
    assert chain_head(records) == records[-1].event_hash


def test_cross_scope_append_is_rejected():
    records = append_record(
        (),
        buyer_id=BUYER,
        business_unit=BU,
        event_type=AuditEventType.SOURCE_PRESENT,
        object_id="source-1",
        occurred_at="2026-09-20T12:00:00Z",
    )
    with pytest.raises(ValueError, match="scope mismatch"):
        append_record(
            records,
            buyer_id="buyer-b",
            business_unit=BU,
            event_type=AuditEventType.REPORT_ISSUED,
            object_id="report-1",
            occurred_at="2026-09-20T13:00:00Z",
        )


def test_tampered_event_is_detected():
    records = append_record(
        (),
        buyer_id=BUYER,
        business_unit=BU,
        event_type=AuditEventType.SOURCE_PRESENT,
        object_id="source-1",
        occurred_at="2026-09-20T12:00:00Z",
    )
    tampered = (replace(records[0], object_id="other"),)
    with pytest.raises(ValueError, match="event hash mismatch"):
        verify_chain(tampered, buyer_id=BUYER, business_unit=BU)


def test_reordered_chain_is_detected():
    records = ()
    for i in range(2):
        records = append_record(
            records,
            buyer_id=BUYER,
            business_unit=BU,
            event_type=AuditEventType.SOURCE_PRESENT,
            object_id=f"source-{i}",
            occurred_at=f"2026-09-20T12:0{i}:00Z",
        )
    with pytest.raises(ValueError, match="sequence gap|previous_hash"):
        verify_chain(tuple(reversed(records)), buyer_id=BUYER, business_unit=BU)


def test_timestamps_are_canonicalized_and_cannot_go_backwards():
    records = append_record(
        (),
        buyer_id=BUYER,
        business_unit=BU,
        event_type=AuditEventType.SOURCE_PRESENT,
        object_id="source-1",
        occurred_at="2026-09-20T08:00:00-04:00",
    )
    assert records[0].occurred_at == "2026-09-20T12:00:00.000000Z"
    with pytest.raises(ValueError, match="nondecreasing"):
        append_record(
            records,
            buyer_id=BUYER,
            business_unit=BU,
            event_type=AuditEventType.TRUTH_FROZEN,
            object_id="truth-1",
            occurred_at="2026-09-20T11:59:59Z",
        )
