import pytest

from freight.canonical_schema import ChargeLine, PackageFacts, ShipmentFacts, SourceArtifact, build_record
from freight.payment_orchestration import (
    PaymentOrchestrator,
    authorize_payment,
    prepare_payment_instruction,
    verify_payment_snapshot,
)
from freight.rate_authority import AuthorityBook, compile_authority
from freight.rating_engine import RATED, REVIEW_REQUIRED, rate_record


def source():
    return SourceArtifact(
        source_id="phase2-source",
        kind="CARRIER_INVOICE",
        sha256="a" * 64,
        observed_at="2026-10-07T03:00:00.000000Z",
        transport="API",
    )


def record(mode, billed, *, weight=10_000, miles=None, packages=(), container_type=None, chassis_days=None):
    shipment = ShipmentFacts(
        shipment_id="SHIP-" + mode,
        carrier_id="CARRIER-" + mode,
        mode=mode,
        service_date="2026-10-01",
        origin_postal="17901",
        destination_postal="21224",
        actual_weight_grams=weight,
        package_count=sum(p.quantity for p in packages) if packages else 1,
        packages=packages,
        miles=miles,
        container_type=container_type,
        chassis_days=chassis_days,
    )
    return build_record(
        buyer_id="BUYER-1",
        business_unit="BU-1",
        invoice_id="INV-" + mode,
        invoice_date="2026-10-02",
        customer_id="CUSTOMER-1",
        currency="USD",
        shipment=shipment,
        charges=tuple(
            ChargeLine("C" + str(i), code, cents)
            for i, (code, cents) in enumerate(billed, 1)
        ),
        sources=(source(),),
    )


def authority(mode, terms, *, verified=True):
    return compile_authority(
        {
            "authority_id": "AUTH-" + mode,
            "buyer_id": "BUYER-1",
            "business_unit": "BU-1",
            "customer_id": "CUSTOMER-1",
            "carrier_id": "CARRIER-" + mode,
            "currency": "USD",
            "mode": mode,
            "effective_from": "2026-01-01",
            "priority": 10,
            "terms": terms,
        },
        source_sha256="b" * 64,
        verified_controlling_authority=verified,
    )


def test_tl_per_mile_fuel_and_accessorial_rating():
    rec = record(
        "TL",
        (("LINEHAUL", 105_000), ("FUEL", 10_000), ("DETENTION", 5_000)),
        miles=500,
    )
    auth = authority("TL", {
        "pricing_model": "PER_MILE",
        "per_mile_cents": 200,
        "minimum_cents": 80_000,
        "fuel_bps": 1_000,
        "accessorials": {"DETENTION": {"model": "FIXED", "cents": 4_000}},
    })
    result = rate_record(rec, AuthorityBook((auth,)))
    assert result.status == RATED
    assert result.expected_total_cents == 114_000
    assert result.variance_cents == 6_000


def test_intermodal_base_mileage_fuel_and_chassis_rating():
    rec = record(
        "INTERMODAL",
        (("TRANSPORTATION", 62_000), ("FUEL", 6_000), ("CHASSIS", 7_000)),
        miles=100,
        chassis_days=2,
    )
    auth = authority("INTERMODAL", {
        "base_cents": 50_000,
        "per_mile_cents": 100,
        "fuel_bps": 1_000,
        "chassis_per_day_cents": 3_000,
    })
    result = rate_record(rec, AuthorityBook((auth,)))
    assert result.status == RATED
    assert result.expected_total_cents == 72_000
    assert result.variance_cents == 3_000


def test_air_uses_greater_of_actual_and_volumetric_weight():
    pkg = PackageFacts("AIR-1", 5_000, length_mm=500, width_mm=400, height_mm=300)
    rec = record(
        "AIR",
        (("TRANSPORTATION", 5_200), ("FUEL", 550), ("SECURITY", 250)),
        weight=5_000,
        packages=(pkg,),
    )
    auth = authority("AIR", {
        "per_kg_cents": 500,
        "minimum_cents": 0,
        "volumetric_divisor_cm3_per_kg": 6000,
        "fuel_bps": 1_000,
        "security_per_kg_cents": 20,
    })
    result = rate_record(rec, AuthorityBook((auth,)))
    assert result.status == RATED
    assert result.expected_total_cents == 5_700
    assert result.variance_cents == 300


def test_ocean_container_rating():
    rec = record(
        "OCEAN",
        (("TRANSPORTATION", 205_000), ("FUEL", 25_000)),
        container_type="40HC",
    )
    auth = authority("OCEAN", {
        "pricing_model": "CONTAINER",
        "container_rates_cents": {"20GP": 150_000, "40HC": 200_000},
        "fuel_bps": 1_000,
    })
    result = rate_record(rec, AuthorityBook((auth,)))
    assert result.status == RATED
    assert result.expected_total_cents == 220_000
    assert result.variance_cents == 10_000


def test_ocean_weight_measurement_rating():
    pkg = PackageFacts("OCEAN-1", 500_000, length_mm=1000, width_mm=1000, height_mm=1000)
    rec = record(
        "OCEAN",
        (("TRANSPORTATION", 11_000),),
        weight=500_000,
        packages=(pkg,),
    )
    auth = authority("OCEAN", {
        "pricing_model": "W_M",
        "w_m_per_unit_cents": 10_000,
        "minimum_cents": 0,
        "fuel_bps": 0,
    })
    result = rate_record(rec, AuthorityBook((auth,)))
    assert result.status == RATED
    assert result.expected_total_cents == 10_000
    assert result.variance_cents == 1_000


def test_multimode_unverified_authority_never_auto_rates():
    rec = record("TL", (("LINEHAUL", 100_000),), miles=500)
    auth = authority("TL", {
        "pricing_model": "PER_MILE",
        "per_mile_cents": 200,
        "fuel_bps": 0,
    }, verified=False)
    result = rate_record(rec, AuthorityBook((auth,)))
    assert result.status == REVIEW_REQUIRED
    assert "AUTHORITY_NOT_HUMAN_VERIFIED" in result.blockers


def test_payment_orchestration_requires_human_authorization_and_observed_settlement():
    instruction = prepare_payment_instruction(
        instruction_id="PAY-1",
        buyer_id="BUYER-1",
        business_unit="BU-1",
        payer_id="CARRIER-A",
        payee_id="CUSTOMER-1",
        currency="USD",
        amount_cents=10_000,
        purpose="Recovery remittance",
        finding_proof_hashes=("f" * 64,),
        idempotency_key="payment-1",
    )
    orchestrator = PaymentOrchestrator(instruction)
    with pytest.raises(ValueError, match="prior human authorization"):
        orchestrator.record_provider_event(
            state="SUBMITTED",
            provider="Provider",
            provider_reference="R1",
            amount_cents=10_000,
            source_hash="1" * 64,
            occurred_at="2026-10-07T03:00:00Z",
        )

    authorization = authorize_payment(
        instruction,
        authorized_by="owner-1",
        reason="Approved against confirmed finding.",
        authorized_at="2026-10-07T03:01:00Z",
    )
    orchestrator.authorize(authorization)
    submitted = orchestrator.record_provider_event(
        state="SUBMITTED",
        provider="Provider",
        provider_reference="R1",
        amount_cents=10_000,
        source_hash="1" * 64,
        occurred_at="2026-10-07T03:02:00Z",
    )
    accepted = orchestrator.record_provider_event(
        state="ACCEPTED",
        provider="Provider",
        provider_reference="R1",
        amount_cents=10_000,
        source_hash="2" * 64,
        occurred_at="2026-10-07T03:03:00Z",
    )
    settled = orchestrator.record_provider_event(
        state="SETTLED",
        provider="Provider",
        provider_reference="R1",
        amount_cents=10_000,
        source_hash="3" * 64,
        occurred_at="2026-10-07T03:04:00Z",
    )
    snapshot = orchestrator.snapshot()
    assert snapshot.current_state == "SETTLED"
    assert snapshot.settled_cents == 10_000
    verify_payment_snapshot(instruction, authorization, (submitted, accepted, settled), snapshot)

    orchestrator.record_provider_event(
        state="REVERSED",
        provider="Provider",
        provider_reference="R1",
        amount_cents=10_000,
        source_hash="4" * 64,
        occurred_at="2026-10-07T03:05:00Z",
    )
    reversed_snapshot = orchestrator.snapshot()
    assert reversed_snapshot.current_state == "REVERSED"
    assert reversed_snapshot.settled_cents == 0
