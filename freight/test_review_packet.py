from dataclasses import replace

import pytest

from freight.contracts import PopulationRow, freeze_population
from freight.finding_factory import FIXED, ChargeRule, InvoiceCharge, derive_batch
from freight.review_packet import (
    ADD_APPLICABLE_RULE,
    REVIEW_VALIDATED_FINDING,
    VERIFY_CONTROLLING_AUTHORITY,
    _money,
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


def test_money_renderer_preserves_full_integer_cent_precision():
    assert _money("USD", 2**63 - 1) == "USD 92,233,720,368,547,758.07"
