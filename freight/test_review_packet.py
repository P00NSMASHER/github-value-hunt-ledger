from dataclasses import asdict, replace

import pytest

from freight.contracts import PopulationRow, canonical_hash, freeze_population
from freight.finding_factory import FIXED, ChargeRule, InvoiceCharge, derive_batch
from freight.review_packet import (
    ADD_APPLICABLE_RULE,
    REVIEW_VALIDATED_FINDING,
    VERIFY_CONTROLLING_AUTHORITY,
    build_review_packet,
    render_review_packet_markdown,
)
from freight.review_queue import build_review_queue


def setup():
    pop = freeze_population(
        "buyer", "unit", "three",
        [
            PopulationRow("i1", "s1", "customer", "carrier", "USD", "p1"),
            PopulationRow("i2", "s2", "customer", "carrier", "USD", "p2"),
            PopulationRow("i3", "s3", "customer", "carrier", "USD", "p3"),
        ],
    )
    charges = (
        InvoiceCharge("buyer","unit","i1","s1","customer","carrier","USD",
                      "c1","DETENTION","2026-09-10",1,12500,"line-1"),
        InvoiceCharge("buyer","unit","i2","s2","customer","carrier","USD",
                      "c2","MISC","2026-09-10",1,15000,"line-2"),
        InvoiceCharge("buyer","unit","i3","s3","customer","carrier","USD",
                      "c3","UNKNOWN","2026-09-10",1,9000,"line-3"),
    )
    rules = (
        ChargeRule("buyer","unit","customer","carrier","USD","rate-confirmation",
                   "DETENTION",FIXED,"2026-09-01","2026-09-30","a"*64,True,10000,None),
        ChargeRule("buyer","unit","customer","carrier","USD","candidate-addendum",
                   "MISC",FIXED,"2026-09-01","2026-09-30","b"*64,False,10000,None),
    )
    batch = derive_batch(pop, charges, rules)
    queue = build_review_queue(batch)
    return batch, queue, charges, rules


def test_packet_joins_charge_rule_and_finding_evidence_in_queue_order():
    batch, queue, charges, rules = setup()
    packet = build_review_packet(batch, queue, charges, rules)
    assert [case.charge_id for case in packet.cases] == ["c1", "c2", "c3"]
    assert [case.action_hint for case in packet.cases] == [
        REVIEW_VALIDATED_FINDING,
        VERIFY_CONTROLLING_AUTHORITY,
        ADD_APPLICABLE_RULE,
    ]
    assert packet.cases[0].rule_evidence[0].verified_controlling_authority is True
    assert packet.cases[1].rule_evidence[0].verified_controlling_authority is False
    assert packet.cases[2].rule_evidence == ()
    assert packet.cases[0].finding_proof_hash
    assert len(packet.packet_hash) == 64


def test_packet_rejects_tampered_queue():
    batch, queue, charges, rules = setup()
    bad = replace(queue, queue_hash="0" * 64)
    with pytest.raises(ValueError, match="queue does not match"):
        build_review_packet(batch, bad, charges, rules)


def test_packet_rejects_charge_not_matching_derivation_proof():
    batch, queue, charges, rules = setup()
    changed = (replace(charges[0], billed_cents=999999),) + charges[1:]
    with pytest.raises(ValueError, match="charge proof"):
        build_review_packet(batch, queue, changed, rules)


def test_packet_requires_all_matched_rule_evidence():
    batch, queue, charges, rules = setup()
    with pytest.raises(ValueError, match="matched rule proof missing"):
        build_review_packet(batch, queue, charges, rules[1:])


def test_packet_is_deterministic():
    batch, queue, charges, rules = setup()
    a = build_review_packet(batch, queue, charges, rules)
    b = build_review_packet(batch, queue, charges, rules)
    assert a == b


def test_markdown_is_human_readable_and_does_not_call_variance_savings():
    batch, queue, charges, rules = setup()
    text = render_review_packet_markdown(build_review_packet(batch, queue, charges, rules))
    assert "Reviewer Work Packet" in text
    assert "Supported variance" in text
    assert "not realized savings" in text
    assert "verified controlling" in text
    assert "No applicable rule proof was established" in text
    assert "realized savings:**" not in text


def _rehash_finding(finding, **changes):
    candidate = replace(finding, **changes)
    body = asdict(candidate)
    body.pop("proof_hash")
    return replace(candidate, proof_hash=canonical_hash({"schema": 2, **body}))


def _rehash_derivation(item, **changes):
    candidate = replace(item, **changes)
    finding = candidate.finding
    authority = candidate.authority_ref
    body = {
        "schema": 1,
        "charge_id": candidate.charge_id,
        "decision": candidate.decision,
        "reason": candidate.reason,
        "billed_cents": candidate.billed_cents,
        "expected_cents": candidate.expected_cents,
        "variance_cents": candidate.variance_cents,
        "charge_hash": candidate.charge_hash,
        "matched_rule_hashes": candidate.matched_rule_hashes,
        "authority_id": authority.authority_id if authority else None,
        "finding_proof_hash": finding.proof_hash if finding else None,
    }
    return replace(candidate, derivation_hash=canonical_hash(body))


def _rehash_batch_with_derivation(batch, original, changed):
    findings = tuple(
        changed.finding if finding.finding_id == original.finding.finding_id else finding
        for finding in batch.truth.findings
    )
    truth = replace(batch.truth, findings=findings)
    truth_body = {
        "schema": 3,
        "buyer_id": truth.buyer_id,
        "business_unit": truth.business_unit,
        "population_hash": truth.population_hash,
        "authorities": [asdict(authority) for authority in truth.authorities],
        "findings": [asdict(finding) for finding in truth.findings],
    }
    truth = replace(truth, truth_hash=canonical_hash(truth_body))
    derivations = tuple(
        changed if item.charge_id == original.charge_id else item
        for item in batch.derivations
    )
    factory_body = {
        "schema": 1,
        "population_hash": truth.population_hash,
        "derivation_hashes": [item.derivation_hash for item in derivations],
        "truth_hash": truth.truth_hash,
    }
    return replace(
        batch,
        truth=truth,
        derivations=derivations,
        factory_hash=canonical_hash(factory_body),
    )


def test_packet_rederives_calculation_even_after_all_outer_hashes_are_reforged():
    batch, _queue, charges, rules = setup()
    original = next(item for item in batch.derivations if item.charge_id == "c1")
    assert original.finding is not None

    forged_finding = _rehash_finding(original.finding, expected_cents=0)
    forged_derivation = _rehash_derivation(
        original,
        expected_cents=0,
        variance_cents=original.billed_cents,
        finding=forged_finding,
    )
    forged_batch = _rehash_batch_with_derivation(
        batch,
        original,
        forged_derivation,
    )

    # Internal hashes and cross-object amounts are now self-consistent, so the
    # factory/queue integrity verifier alone cannot know the original rate math.
    forged_queue = build_review_queue(forged_batch)

    # Packet construction re-runs derive_charge against the actual charge and
    # supplied rule evidence, so a re-hashed but false calculation still fails.
    with pytest.raises(ValueError, match="does not match current charge/rule evidence"):
        build_review_packet(forged_batch, forged_queue, charges, rules)


def test_packet_accepts_untampered_canonical_derivation_after_reverification():
    batch, queue, charges, rules = setup()
    packet = build_review_packet(batch, queue, charges, rules)
    case = next(item for item in packet.cases if item.charge_id == "c1")
    assert case.billed_cents == 12500
    assert case.expected_cents == 10000
    assert case.variance_cents == 2500
