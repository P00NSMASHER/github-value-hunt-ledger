import hashlib

from dataclasses import asdict, replace
import pytest

from freight.contracts import (
    AuthorityRef,
    canonical_hash,
    PopulationRow,
    freeze_population,
    freeze_truth,
    make_finding,
    open_incumbent_output,
    seal_incumbent_submission,
    VALIDATED,
)
from freight.pilot_package import (
    SourceEntry,
    build_data_room_manifest,
    build_pilot_package,
)


BUYER = "buyer-1"
BU = "bu-1"


def H(text):
    return hashlib.sha256(text.encode()).hexdigest()


def proof_objects():
    population = freeze_population(
        BUYER,
        BU,
        "one invoice",
        [PopulationRow("inv-1","shp-1","cust","car","USD",H("invoice-row"))],
    )
    authority = AuthorityRef(
        "auth-1",BUYER,BU,"cust","car","USD",H("authority-source")
    )
    truth = freeze_truth(
        population,
        [authority],
        [
            make_finding(
                finding_id="f-1", buyer_id=BUYER, business_unit=BU,
                invoice_id="inv-1", shipment_id="shp-1",
                customer_id="cust", carrier_id="car", currency="USD",
                authority_id="auth-1", expected_cents=10000,
                actual_cents=12500, status=VALIDATED,
            )
        ],
    )
    incumbent_hash = H("incumbent-file")
    sealed = seal_incumbent_submission(population, incumbent_hash)
    incumbent = open_incumbent_output(
        population=population,
        truth=truth,
        submission=sealed,
        finding_ids=[],
    )
    return population, truth, sealed, incumbent


def room_entries():
    return [
        SourceEntry("invoice-1",BUYER,BU,"invoice",H("invoice-file"),True,True,False,30),
        SourceEntry("authority-1",BUYER,BU,"authority",H("authority-file"),True,True,False,30),
        SourceEntry("incumbent-1",BUYER,BU,"incumbent_output",H("incumbent-file"),True,True,False,30),
    ]


@pytest.mark.parametrize("field", ["authorized", "read_only", "contains_secrets"])
@pytest.mark.parametrize("value", ["false", "true", 0, 1, None])
def test_data_permission_flags_cannot_be_inferred_from_non_boolean_values(field, value):
    entry = replace(room_entries()[0], **{field: value})
    with pytest.raises(ValueError, match=field + " must be a boolean"):
        build_data_room_manifest(BUYER, BU, [entry])


def test_boolean_retention_cannot_be_misread_as_one_day():
    entry = replace(room_entries()[0], retention_days=True)
    with pytest.raises(ValueError, match="positive integer"):
        build_data_room_manifest(BUYER, BU, [entry])


def test_valid_pilot_package_is_scope_and_hash_bound():
    population, truth, sealed, incumbent = proof_objects()
    room = build_data_room_manifest(BUYER, BU, room_entries())
    package = build_pilot_package(room, population, truth, sealed, incumbent)
    assert package.buyer_id == BUYER
    assert package.business_unit == BU
    assert package.population_hash == population.manifest_hash
    assert package.truth_hash == truth.truth_hash
    assert package.package_hash


def test_unauthorized_source_is_rejected():
    entries = room_entries()
    entries[0] = SourceEntry(
        "invoice-1",BUYER,BU,"invoice",H("invoice-file"),True,False,False,30
    )
    try:
        build_data_room_manifest(BUYER, BU, entries)
    except ValueError as exc:
        assert "unauthorized source" in str(exc)
    else:
        raise AssertionError("unauthorized source should fail")


def test_cross_buyer_source_is_rejected():
    entries = room_entries()
    entries[0] = SourceEntry(
        "invoice-1","buyer-2",BU,"invoice",H("invoice-file"),True,True,False,30
    )
    try:
        build_data_room_manifest(BUYER, BU, entries)
    except ValueError as exc:
        assert "source scope mismatch" in str(exc)
    else:
        raise AssertionError("cross-buyer source should fail")


def test_secret_bearing_source_is_rejected():
    entries = room_entries()
    entries[0] = SourceEntry(
        "invoice-1",BUYER,BU,"invoice",H("invoice-file"),True,True,True,30
    )
    try:
        build_data_room_manifest(BUYER, BU, entries)
    except ValueError as exc:
        assert "secret-bearing" in str(exc)
    else:
        raise AssertionError("secret-bearing source should fail")


def test_incumbent_source_must_be_in_data_room():
    population, truth, sealed, incumbent = proof_objects()
    entries = room_entries()
    entries[2] = SourceEntry(
        "incumbent-1",BUYER,BU,"incumbent_output",H("other-file"),True,True,False,30
    )
    room = build_data_room_manifest(BUYER, BU, entries)
    try:
        build_pilot_package(room, population, truth, sealed, incumbent)
    except ValueError as exc:
        assert "sealed incumbent source missing" in str(exc)
    else:
        raise AssertionError("unmanifested incumbent source should fail")


def _replace_room_entries(room, entries, *, rehash=False):
    """Construct untrusted metadata; recomputing a digest grants no permission."""
    entries = tuple(sorted(entries, key=lambda entry: entry.source_id))
    digest = room.manifest_hash
    if rehash:
        digest = canonical_hash({
            "schema": 1,
            "buyer_id": room.buyer_id,
            "business_unit": room.business_unit,
            "entries": [asdict(entry) for entry in entries],
        })
    return replace(room, entries=entries, manifest_hash=digest)


@pytest.mark.parametrize("rehash", [False, True])
@pytest.mark.parametrize("changes, message", [
    ({"authorized": False}, "unauthorized source"),
    ({"read_only": False}, "must be read-only"),
    ({"contains_secrets": True}, "secret-bearing"),
    ({"authorized": "true"}, "authorized must be a boolean"),
    ({"read_only": 1}, "read_only must be a boolean"),
    ({"contains_secrets": "false"}, "contains_secrets must be a boolean"),
    ({"buyer_id": "other-buyer"}, "source scope mismatch"),
    ({"business_unit": "other-unit"}, "source scope mismatch"),
    ({"source_type": "unregistered"}, "unsupported source_type"),
    ({"source_hash": "not-a-digest"}, "lowercase SHA-256"),
    ({"retention_days": 0}, "positive integer"),
    ({"retention_days": True}, "positive integer"),
])
def test_package_revalidates_every_source_even_with_a_recomputed_hash(changes, message, rehash):
    # The extra source leaves all required source types and incumbent links intact.
    extra = SourceEntry("extra-1", BUYER, BU, "other", H("extra"), True, True, False, 30)
    entries = room_entries() + [extra]
    room = build_data_room_manifest(BUYER, BU, entries)
    entries[-1] = replace(extra, **changes)
    untrusted = _replace_room_entries(room, entries, rehash=rehash)
    with pytest.raises(ValueError, match=message):
        build_pilot_package(untrusted, *proof_objects())


@pytest.mark.parametrize("digest", [None, "", True, "A" * 64, "a" * 63, H("wrong-room")])
def test_package_rejects_unbound_data_room_digest(digest):
    room = build_data_room_manifest(BUYER, BU, room_entries())
    with pytest.raises(ValueError, match="data-room manifest hash mismatch"):
        build_pilot_package(replace(room, manifest_hash=digest), *proof_objects())


@pytest.mark.parametrize("changes", [
    {"source_hash": H("replacement-invoice")},
    {"source_locator": "synthetic://replacement-invoice"},
    {"retention_days": 60},
    {"source_id": "replacement-id"},
])
def test_package_rejects_changed_metadata_under_an_old_data_room_hash(changes):
    entries = room_entries()
    room = build_data_room_manifest(BUYER, BU, entries)
    entries[0] = replace(entries[0], **changes)
    with pytest.raises(ValueError, match="data-room manifest hash mismatch"):
        build_pilot_package(_replace_room_entries(room, entries), *proof_objects())


@pytest.mark.parametrize("rehash", [False, True])
def test_package_rejects_duplicate_source_ids_after_manifest_construction(rehash):
    entries = room_entries()
    room = build_data_room_manifest(BUYER, BU, entries)
    untrusted = _replace_room_entries(room, entries + [entries[0]], rehash=rehash)
    with pytest.raises(ValueError, match="duplicate source_id"):
        build_pilot_package(untrusted, *proof_objects())


def test_non_pilot_readonly_exception_cannot_authorize_a_pilot_package():
    entries = [replace(entry, read_only=False) for entry in room_entries()]
    room = build_data_room_manifest(BUYER, BU, entries, require_pilot_read_only=False)
    with pytest.raises(ValueError, match="pilot source must be read-only"):
        build_pilot_package(room, *proof_objects())


def test_reordering_verified_sources_preserves_package_identity_without_mutation():
    room = build_data_room_manifest(BUYER, BU, room_entries())
    objects = proof_objects()
    expected = build_pilot_package(room, *objects)
    reordered = replace(room, entries=tuple(reversed(room.entries)))
    original_entries = reordered.entries
    assert build_pilot_package(reordered, *objects) == expected
    assert reordered.entries == original_entries


def test_rebuilt_valid_source_revision_changes_package_identity():
    entries = room_entries()
    original_room = build_data_room_manifest(BUYER, BU, entries)
    objects = proof_objects()
    original = build_pilot_package(original_room, *objects)
    entries[0] = replace(entries[0], source_locator="synthetic://approved-revision")
    revised_room = build_data_room_manifest(BUYER, BU, entries)
    revised = build_pilot_package(revised_room, *objects)
    assert revised.data_room_hash == revised_room.manifest_hash
    assert revised.package_hash != original.package_hash
    assert revised.population_hash == original.population_hash
