import hashlib

from freight.contracts import (
    AuthorityRef,
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
