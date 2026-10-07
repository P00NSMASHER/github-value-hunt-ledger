from dataclasses import replace

import pytest

from freight.benchmark_harness import run_benchmark
from freight.canonical_schema import (
    ChargeLine,
    PackageFacts,
    ShipmentFacts,
    SourceArtifact,
    build_record,
    verify_record,
)
from freight.ingestion_gateway import IngressEnvelope, ingest_bytes
from freight.rate_authority import AuthorityBook, compile_authority
from freight.rating_engine import RATED, REVIEW_REQUIRED, rate_record
from freight.reviewer_cockpit import build_queue, make_case, record_disposition


SHA_A = "a" * 64
SHA_B = "b" * 64


def source():
    return SourceArtifact(
        source_id="invoice:1",
        kind="CARRIER_INVOICE",
        sha256=SHA_A,
        observed_at="2026-10-06T12:00:00.000000Z",
        transport="UPLOAD",
        filename="invoice.csv",
    )


def ltl_record():
    shipment = ShipmentFacts(
        shipment_id="S-LTL-1",
        carrier_id="CARRIER-A",
        mode="LTL",
        service_date="2026-10-01",
        origin_postal="17901",
        destination_postal="21224",
        actual_weight_grams=45_359,
        package_count=1,
        freight_class="70",
    )
    return build_record(
        buyer_id="BUYER-1",
        business_unit="BU-1",
        invoice_id="INV-LTL-1",
        invoice_date="2026-10-02",
        customer_id="CUSTOMER-1",
        currency="USD",
        shipment=shipment,
        charges=(
            ChargeLine("L1", "LINEHAUL", 12_000),
            ChargeLine("F1", "FUEL", 1_200),
            ChargeLine("A1", "LIFTGATE", 5_500),
        ),
        sources=(source(),),
    )


def ltl_authority(*, verified=True):
    return compile_authority(
        {
            "authority_id": "AUTH-LTL-1",
            "buyer_id": "BUYER-1",
            "business_unit": "BU-1",
            "customer_id": "CUSTOMER-1",
            "carrier_id": "CARRIER-A",
            "currency": "USD",
            "mode": "LTL",
            "effective_from": "2026-01-01",
            "priority": 10,
            "terms": {
                "per_cwt_cents": 10_000,
                "minimum_cents": 0,
                "discount_bps": 0,
                "fuel_bps": 1_000,
                "lane_multiplier_bps": 10_000,
                "class_multipliers_bps": {"70": 10_000},
                "accessorials": {
                    "LIFTGATE": {"model": "FIXED", "cents": 5_000},
                },
            },
        },
        source_sha256=SHA_B,
        verified_controlling_authority=verified,
    )


def parcel_record():
    shipment = ShipmentFacts(
        shipment_id="S-P-1",
        carrier_id="CARRIER-P",
        mode="PARCEL",
        service_date="2026-10-01",
        origin_postal="17901",
        destination_postal="21224",
        actual_weight_grams=453,
        package_count=1,
        packages=(PackageFacts("PKG-1", 453),),
        zone="2",
        residential=True,
    )
    return build_record(
        buyer_id="BUYER-1",
        business_unit="BU-1",
        invoice_id="INV-P-1",
        invoice_date="2026-10-02",
        customer_id="CUSTOMER-1",
        currency="USD",
        shipment=shipment,
        charges=(
            ChargeLine("P1", "TRANSPORTATION", 1_100),
            ChargeLine("PF1", "FUEL", 110),
            ChargeLine("PR1", "RESIDENTIAL", 300),
            ChargeLine("PS1", "SIGNATURE", 250),
        ),
        sources=(source(),),
    )


def parcel_authority():
    return compile_authority(
        {
            "authority_id": "AUTH-P-1",
            "buyer_id": "BUYER-1",
            "business_unit": "BU-1",
            "customer_id": "CUSTOMER-1",
            "carrier_id": "CARRIER-P",
            "currency": "USD",
            "mode": "PARCEL",
            "effective_from": "2026-01-01",
            "priority": 10,
            "terms": {
                "dimensional_divisor": 139,
                "fuel_bps": 1_000,
                "residential_cents": 300,
                "weight_bands": [
                    {"max_billable_lb": 1, "zone_rates_cents": {"2": 1_000}},
                    {"max_billable_lb": 5, "zone_rates_cents": {"2": 1_500}},
                ],
                "accessorials": {
                    "SIGNATURE": {"model": "FIXED", "cents": 200},
                },
            },
        },
        source_sha256="c" * 64,
        verified_controlling_authority=True,
    )


def test_canonical_record_is_hash_bound_and_fails_on_mutation():
    record = ltl_record()
    verify_record(record)
    assert record.billed_total_cents == 18_700
    with pytest.raises(ValueError, match="hash mismatch"):
        verify_record(replace(record, invoice_id="MUTATED"))


def test_authority_resolution_fails_closed_on_tied_precedence():
    record = ltl_record()
    first = ltl_authority()
    second = compile_authority(
        {
            "authority_id": "AUTH-LTL-2",
            "buyer_id": "BUYER-1",
            "business_unit": "BU-1",
            "customer_id": "CUSTOMER-1",
            "carrier_id": "CARRIER-A",
            "currency": "USD",
            "mode": "LTL",
            "effective_from": "2026-01-01",
            "priority": 10,
            "terms": {
                "per_cwt_cents": 9_000,
                "minimum_cents": 0,
                "fuel_bps": 1_000,
                "class_multipliers_bps": {"70": 10_000},
            },
        },
        source_sha256="d" * 64,
        verified_controlling_authority=True,
    )
    result = AuthorityBook((first, second)).resolve(record)
    assert result.status == "AMBIGUOUS"
    assert result.authority is None


def test_ltl_rating_is_deterministic_and_reproduces_expected_charge():
    record = ltl_record()
    book = AuthorityBook((ltl_authority(),))
    first = rate_record(record, book)
    second = rate_record(record, book)
    assert first.status == RATED
    assert first.expected_total_cents == 16_000
    assert first.variance_cents == 2_700
    assert first.rating_hash == second.rating_hash


def test_unverified_authority_can_calculate_but_not_auto_rate():
    result = rate_record(ltl_record(), AuthorityBook((ltl_authority(verified=False),)))
    assert result.status == REVIEW_REQUIRED
    assert result.expected_total_cents == 16_000
    assert "AUTHORITY_NOT_HUMAN_VERIFIED" in result.blockers


def test_parcel_rating_handles_weight_zone_fuel_residential_and_accessorial():
    result = rate_record(parcel_record(), AuthorityBook((parcel_authority(),)))
    assert result.status == RATED
    assert result.expected_total_cents == 1_600
    assert result.billed_total_cents == 1_760
    assert result.variance_cents == 160


def test_reviewer_cockpit_prioritizes_and_records_human_disposition():
    low = make_case(
        case_id="LOW",
        record_hash="r1",
        amount_cents=100,
        confidence_ppm=950_000,
        novelty_ppm=10_000,
        downstream_risk_ppm=10_000,
    )
    high = make_case(
        case_id="HIGH",
        record_hash="r2",
        amount_cents=10_000,
        confidence_ppm=500_000,
        novelty_ppm=500_000,
        downstream_risk_ppm=500_000,
        blocker_codes=("AUTHORITY",),
    )
    queue = build_queue((low, high))
    assert [x.case_id for x in queue.items] == ["HIGH", "LOW"]
    disposition = record_disposition(
        high,
        reviewer_id="human-1",
        decision="MODIFY_RULE",
        reason="Contract amendment changes this charge.",
        decided_at="2026-10-06T20:00:00-04:00",
        corrected_expected_cents=8_000,
        rule_candidate="Apply amendment A-17.",
    )
    assert disposition.decision == "MODIFY_RULE"
    assert disposition.decided_at == "2026-10-07T00:00:00.000000Z"
    assert len(disposition.disposition_hash) == 64


def test_ingestion_gateway_separates_transport_from_file_validation():
    envelope = IngressEnvelope("ING-1", "BUYER-1", "BU-1", "SFTP", "invoice.csv")
    receipt = ingest_bytes(envelope, b"a,b\n1,2\n")
    assert receipt.status == "ACCEPT"
    assert receipt.transport == "SFTP"
    assert receipt.route == "NORMALIZE"
    rejected = ingest_bytes(
        IngressEnvelope("ING-2", "BUYER-1", "BU-1", "EMAIL", "payload.zip"),
        b"not-an-allowed-format",
    )
    assert rejected.status == "REJECT"
    assert rejected.route == "NONE"


def test_benchmark_replays_rating_hashes_and_reports_counts():
    records = (ltl_record(), parcel_record())
    book = AuthorityBook((ltl_authority(), parcel_authority()))
    result = run_benchmark(records, book)
    assert result.record_count == 2
    assert result.rated_count == 2
    assert result.review_count == 0
    assert result.deterministic_replay is True
    assert result.variance_cents == 2_860
    assert result.records_per_second > 0
    assert len(result.benchmark_hash) == 64
