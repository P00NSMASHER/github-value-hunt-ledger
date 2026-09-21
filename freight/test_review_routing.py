from dataclasses import asdict, replace

import pytest

from freight.contracts import PopulationRow, canonical_hash, freeze_population
from freight.finding_factory import FIXED, ChargeRule, InvoiceCharge, derive_batch
from freight.review_packet import build_review_packet
from freight.review_queue import build_review_queue
from freight.review_routing import (
    BUYER_REVIEW_READY,
    EVIDENCE_REMEDIATION_REQUIRED,
    MIXED_REVIEW_AND_REMEDIATION,
    NO_REVIEW,
    route_review_packet,
)


def setup(*, clean=False, include_unverified=True, include_missing=True):
    rows = [
        PopulationRow("i1", "s1", "c", "k", "USD", "p1"),
        PopulationRow("i2", "s2", "c", "k", "USD", "p2"),
        PopulationRow("i3", "s3", "c", "k", "USD", "p3"),
    ]
    population = freeze_population("b", "u", "scope", rows)
    charges = [
        InvoiceCharge("b","u","i1","s1","c","k","USD","c1","A","2026-09-10",1,9000 if clean else 12000,"l1"),
        InvoiceCharge("b","u","i2","s2","c","k","USD","c2","B","2026-09-10",1,9000 if clean else 15000,"l2"),
        InvoiceCharge("b","u","i3","s3","c","k","USD","c3","C","2026-09-10",1,9000,"l3"),
    ]
    rules = [
        ChargeRule("b","u","c","k","USD","doc-a","A",FIXED,"2026-09-01",None,"a"*64,True,10000,None),
    ]
    if include_unverified:
        rules.append(
            ChargeRule("b","u","c","k","USD","doc-b","B",FIXED,"2026-09-01",None,"b"*64,False,10000,None)
        )
    else:
        rules.append(
            ChargeRule("b","u","c","k","USD","doc-b","B",FIXED,"2026-09-01",None,"b"*64,True,10000,None)
        )
    if not include_missing:
        rules.append(
            ChargeRule("b","u","c","k","USD","doc-c","C",FIXED,"2026-09-01",None,"c"*64,True,10000,None)
        )

    batch = derive_batch(population, charges, rules)
    queue = build_review_queue(batch)
    packet = build_review_packet(batch, queue, charges, rules)
    return packet


def test_mixed_packet_separates_buyer_review_from_remediation():
    routing = route_review_packet(setup())
    assert routing.route == MIXED_REVIEW_AND_REMEDIATION
    assert routing.buyer_review_case_count == 1
    assert routing.evidence_remediation_case_count == 2
    assert routing.rerun_required is True
    assert dict(routing.remediation_action_counts) == {
        "ADD_APPLICABLE_RULE": 1,
        "VERIFY_CONTROLLING_AUTHORITY": 1,
    }
    assert len(routing.routing_hash) == 64


def test_all_validated_cases_are_buyer_review_ready():
    routing = route_review_packet(setup(include_unverified=False, include_missing=False))
    assert routing.route == BUYER_REVIEW_READY
    assert routing.buyer_review_case_count == 2
    assert routing.evidence_remediation_case_count == 0
    assert routing.rerun_required is False


def test_only_evidence_gaps_route_to_remediation():
    packet = setup(clean=True)
    routing = route_review_packet(packet)
    assert routing.route == EVIDENCE_REMEDIATION_REQUIRED
    assert routing.buyer_review_case_count == 0
    assert routing.evidence_remediation_case_count == 2
    assert routing.rerun_required is True


def test_empty_review_packet_routes_to_no_review():
    packet = setup(clean=True, include_unverified=False, include_missing=False)
    routing = route_review_packet(packet)
    assert routing.route == NO_REVIEW
    assert routing.buyer_review_case_count == 0
    assert routing.evidence_remediation_case_count == 0
    assert routing.rerun_required is False


def test_routing_is_deterministic():
    packet = setup()
    assert route_review_packet(packet) == route_review_packet(packet)


def test_tampered_packet_is_rejected():
    packet = setup()
    bad = replace(packet, packet_hash="0" * 64)
    with pytest.raises(ValueError, match="hash mismatch"):
        route_review_packet(bad)


def test_case_hash_order_is_preserved_from_review_packet():
    packet = setup()
    routing = route_review_packet(packet)
    expected_buyer = tuple(
        case.case_hash
        for case in packet.cases
        if case.action_hint == "REVIEW_VALIDATED_FINDING"
    )
    expected_remediation = tuple(
        case.case_hash
        for case in packet.cases
        if case.action_hint != "REVIEW_VALIDATED_FINDING"
    )
    assert routing.buyer_review_case_hashes == expected_buyer
    assert routing.remediation_case_hashes == expected_remediation


def test_recomputed_outer_packet_hash_cannot_hide_tampered_case_route():
    packet = setup()
    first = packet.cases[0]
    tampered_case = replace(first, action_hint="ADD_APPLICABLE_RULE")
    tampered_cases = (tampered_case,) + packet.cases[1:]
    packet_body = {
        "schema": 1,
        "buyer_id": packet.buyer_id,
        "business_unit": packet.business_unit,
        "factory_hash": packet.factory_hash,
        "queue_hash": packet.queue_hash,
        "truth_hash": packet.truth_hash,
        "cases": [asdict(case) for case in tampered_cases],
    }
    tampered_packet = replace(
        packet,
        cases=tampered_cases,
        packet_hash=canonical_hash(packet_body),
    )
    with pytest.raises(ValueError, match="case hash mismatch"):
        route_review_packet(tampered_packet)
