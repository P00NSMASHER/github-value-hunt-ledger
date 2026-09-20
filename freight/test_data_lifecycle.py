import hashlib

import pytest

from freight.data_lifecycle import (
    LifecycleState,
    ObservationStatus,
    build_lifecycle,
    confirm_delete,
    mark_delete_unknown,
    observe_source,
    request_delete,
    retention_due,
    verify_item,
)
from freight.pilot_package import DataRoomManifest, SourceEntry


def H(text):
    return hashlib.sha256(text.encode()).hexdigest()


def room():
    entries=(
        SourceEntry(
            "invoice-1","buyer-a","bu-a","invoice",H("invoice"),
            True,True,False,2,
        ),
        SourceEntry(
            "authority-1","buyer-a","bu-a","authority",H("authority"),
            True,True,False,5,
        ),
    )
    return DataRoomManifest(
        buyer_id="buyer-a",
        business_unit="bu-a",
        engagement_id="ENG-LIFECYCLE",
        launch_authorization_hash=H("launch-authorization"),
        launch_authorization_valid_until="2026-10-20",
        entries=entries,
        manifest_hash=H("data-room"),
    )


def test_lifecycle_uses_manifest_as_census_and_retention_as_scope():
    items = build_lifecycle(room(), ingested_at="2026-09-20T12:00:00Z")
    assert len(items) == 2
    assert items[0].state is LifecycleState.PRESENT
    due = retention_due(items, as_of="2026-09-23T12:00:00Z")
    assert [x.source_id for x in due] == ["invoice-1"]
    for item in items:
        verify_item(item)


def test_deletion_requires_explicit_confirmation():
    item = build_lifecycle(room(), ingested_at="2026-09-20T12:00:00Z")[0]
    requested = request_delete(item, H("request"))
    unknown = mark_delete_unknown(requested, H("timeout"))
    assert unknown.state is LifecycleState.DELETE_UNKNOWN
    assert unknown.state is not LifecycleState.DELETE_CONFIRMED
    confirmed = confirm_delete(unknown, H("provider-confirmation"))
    assert confirmed.state is LifecycleState.DELETE_CONFIRMED
    verify_item(confirmed)


def test_cannot_confirm_delete_from_present_without_request():
    item = build_lifecycle(room(), ingested_at="2026-09-20T12:00:00Z")[0]
    with pytest.raises(ValueError, match="invalid lifecycle transition"):
        confirm_delete(item, H("confirmation"))


def test_verified_empty_requires_completeness_evidence():
    with pytest.raises(ValueError, match="completeness evidence"):
        observe_source(
            buyer_id="buyer-a",
            business_unit="bu-a",
            source_id="settlement-feed",
            observed_at="2026-09-20T12:00:00Z",
            status=ObservationStatus.VERIFIED_EMPTY,
            evidence_hash=H("query"),
        )


def test_unavailable_is_distinct_from_verified_empty():
    receipt = observe_source(
        buyer_id="buyer-a",
        business_unit="bu-a",
        source_id="settlement-feed",
        observed_at="2026-09-20T12:00:00Z",
        status=ObservationStatus.UNAVAILABLE,
        evidence_hash=H("timeout"),
    )
    assert receipt.status is ObservationStatus.UNAVAILABLE
    assert receipt.completeness_evidence_hash is None
