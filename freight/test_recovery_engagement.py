from dataclasses import replace

import pytest
import hashlib

from freight.test_recovery_claim_workflow import setup as buyer_review_setup
from freight.recovery_claim_workflow import build_recovery_claim_batch, persist_recovery_claim_batch
from freight.settlement_store import (
    SettlementStore, SettlementEventRecord, CounterEventRecord,
)

from freight.recovery_engagement import (
    RecoveryEngagementRequest,
    build_recovery_engagement,
    record_actual_recovery,
    render_engagement_summary,
)


def request(**overrides):
    values = {
        "engagement_id": "REC-001",
        "audit_reference": "AUDIT-001",
        "buyer_id": "BUYER-001",
        "business_unit": "US-FREIGHT",
        "scope": "Supported parcel and LTL opportunities in the agreed audit population.",
        "potential_recovery_low_cents": 1_000_000,
        "potential_recovery_high_cents": 2_000_000,
        "recovered_funds_definition": "Eligible cash refunds or posted credits received and verified by the buyer, net of reversals and exclusions.",
        "payment_timing": "Invoice after settlement evidence is reconciled under the governing agreement.",
        "confidentiality_terms_reference": "TERMS:CONFIDENTIALITY:V1",
        "data_use_terms_reference": "TERMS:DATA-USE:V1",
        "termination_terms_reference": "TERMS:TERMINATION:V1",
        "attribution_terms_reference": "TERMS:ATTRIBUTION:V1",
        "governing_agreement_reference": "AGREEMENT:REC-001:V1",
    }
    values.update(overrides)
    return RecoveryEngagementRequest(**values)


def accepted(**overrides):
    return build_recovery_engagement(
        request(
            buyer_accepted=True,
            freight_recovery_accepted=True,
            accepted_at="2026-09-23T15:00:00-04:00",
            **overrides,
        )
    )


def test_default_rate_is_configurable_and_not_applied_to_potential_value():
    engagement = build_recovery_engagement(request())
    assert engagement.state == "READY_FOR_ACCEPTANCE"
    assert engagement.contingency_rate == "0.3"
    assert engagement.contingency_rate_label == "30%"
    assert engagement.approved_claim_value_cents == 0
    assert engagement.actual_recovered_cents == 0
    assert engagement.external_action_authorized is False

    custom = build_recovery_engagement(request(contingency_rate="0.325"))
    assert custom.contingency_rate_label == "32.5%"


def test_acceptance_requires_both_parties_and_timestamp():
    with pytest.raises(ValueError, match="accepted_at"):
        build_recovery_engagement(
            request(buyer_accepted=True, freight_recovery_accepted=True)
        )
    with pytest.raises(ValueError, match="before both parties"):
        build_recovery_engagement(request(accepted_at="2026-09-23T19:00:00Z"))

    engagement = accepted()
    assert engagement.state == "ACCEPTED"
    assert engagement.accepted_at == "2026-09-23T19:00:00Z"
    assert engagement.external_action_authorized is False


def proof_case(tmp_path, *, cents=500):
    """Build the real buyer-review/claim/store/report chain with fictional invoices."""
    artifacts, review, incumbent = buyer_review_setup()
    truth = artifacts.factory.truth
    batch = build_recovery_claim_batch(
        truth=truth, incumbent=incumbent, review_packet=artifacts.review_packet,
        review_routing=artifacts.review_routing, buyer_review=review,
        issued_at="2026-09-21T10:00:00Z",
    )
    store = SettlementStore(tmp_path / "settlements.sqlite3", buyer_id="buyer", business_unit="unit")
    persist_recovery_claim_batch(store, batch)
    if cents:
        claim = batch.claims[0]
        store.ingest_event(SettlementEventRecord(
            "settlement-one", claim.reference, claim.payer_id, claim.payee_id,
            claim.currency, cents, "2026-09-22T00:00:00Z",
            hashlib.sha256(b"settlement-synthetic").hexdigest(),
        ))
        store.review_allocate(
            allocation_id="allocation-one", claim_id=claim.claim_id,
            event_id="settlement-one", amount_cents=cents,
            created_at="2026-09-22T00:10:00Z",
        )
    return dict(
        truth=truth, incumbent=incumbent, review_packet=artifacts.review_packet,
        review_routing=artifacts.review_routing, buyer_review=review,
        claim_batch=batch, store=store, recorded_at="2026-09-24T10:30:00-04:00",
    )


def accepted_for(proof, *, accepted_at="2026-09-20T12:00:00Z"):
    return build_recovery_engagement(request(
        buyer_id="buyer", business_unit="unit",
        audit_reference="TRUTH:" + proof["truth"].truth_hash,
        buyer_accepted=True, freight_recovery_accepted=True,
        accepted_at=accepted_at,
    ))


def test_fee_derived_from_verified_claim_and_settlement_not_caller_amount(tmp_path):
    proof = proof_case(tmp_path)
    record = record_actual_recovery(
        accepted_for(proof),
        buyer_posting_evidence_reference="BUYERPOSTED:CASE-001", **proof,
    )
    assert record.actual_recovered_cents == 500
    assert record.fee_eligible_recovered_cents == 500
    assert record.recovery_fee_cents == 150
    assert record.customer_net_recovery_cents == 350
    assert record.settlement_evidence_reference.startswith("PILOTREPORT:")
    assert record.claim_batch_hash == proof["claim_batch"].batch_hash
    assert len(record.settlement_snapshot_hash) == 64
    assert record.billing_authorized is False
    assert record.recorded_at == "2026-09-24T14:30:00Z"
    # The API cannot accept a raw, unreviewed amount, even if someone labels it a settlement.
    with pytest.raises(TypeError, match="actual_recovered_cents"):
        record_actual_recovery(
            accepted_for(proof),
            actual_recovered_cents=9_000_000, **proof,
        )


def test_no_settlement_no_fee_no_posting_evidence_required(tmp_path):
    proof = proof_case(tmp_path, cents=0)
    record = record_actual_recovery(accepted_for(proof), **proof)
    assert record.actual_recovered_cents == 0
    assert record.recovery_fee_cents == 0
    assert record.billing_authorized is False


def test_record_rejects_missing_buyer_posting_evidence(tmp_path):
    proof = proof_case(tmp_path)
    with pytest.raises(ValueError, match="buyer posting evidence"):
        record_actual_recovery(accepted_for(proof), **proof)


def test_fee_cannot_be_recorded_before_acceptance_or_with_wrong_customer(tmp_path):
    proof = proof_case(tmp_path)
    with pytest.raises(ValueError, match="accepted engagement"):
        record_actual_recovery(
            build_recovery_engagement(request(buyer_id="buyer", business_unit="unit")),
            **proof,
        )
    with pytest.raises(ValueError, match="engagement buyer/business-unit scope"):
        record_actual_recovery(
            accepted(), buyer_posting_evidence_reference="BUYERPOSTED:CASE-001", **proof,
        )


def test_tampered_claim_approval_and_engagement_rejected(tmp_path):
    proof = proof_case(tmp_path)
    buyer = accepted_for(proof)
    with pytest.raises(ValueError, match="engagement hash"):
        record_actual_recovery(replace(buyer, contingency_rate="0.5"), **proof)
    forged = dict(proof, claim_batch=replace(proof["claim_batch"], batch_hash="0" * 64))
    with pytest.raises(ValueError, match="does not match buyer review proofs"):
        record_actual_recovery(buyer, **forged)


def test_reversal_and_replay_reduce_fee_without_double_count(tmp_path):
    proof = proof_case(tmp_path)
    store = proof["store"]
    buyer = accepted_for(proof)
    before = record_actual_recovery(
        buyer, buyer_posting_evidence_reference="BUYERPOSTED:CASE-001", **proof,
    )
    store.ingest_counter(CounterEventRecord(
        "return-one", "settlement-one", "USD", 200,
        "2026-09-23T00:00:00Z", hashlib.sha256(b"return-synthetic").hexdigest(),
    ))
    store.auto_apply_counter("return-one", created_at="2026-09-23T00:10:00Z")
    after = record_actual_recovery(
        buyer, buyer_posting_evidence_reference="BUYERPOSTED:CASE-001", **proof,
    )
    replay = record_actual_recovery(
        buyer, buyer_posting_evidence_reference="BUYERPOSTED:CASE-001", **proof,
    )
    assert before.recovery_fee_cents == 150
    assert after.actual_recovered_cents == 300
    assert after.recovery_fee_cents == 90
    assert after.record_hash == replay.record_hash
    assert before.settlement_snapshot_hash != after.settlement_snapshot_hash


def test_incumbent_known_recovery_is_not_fee_eligible(tmp_path):
    proof = proof_case(tmp_path, cents=0)
    store, claim = proof["store"], proof["claim_batch"].claims[1]
    assert claim.fee_disqualified is True
    store.ingest_event(SettlementEventRecord(
        "incumbent-credit", claim.reference, claim.payer_id, claim.payee_id,
        "USD", 500, "2026-09-22T00:00:00Z",
        hashlib.sha256(b"incumbent-synthetic").hexdigest(),
    ))
    store.review_allocate(
        allocation_id="incumbent-allocation", claim_id=claim.claim_id,
        event_id="incumbent-credit", amount_cents=500,
        created_at="2026-09-22T00:10:00Z",
    )
    result = record_actual_recovery(accepted_for(proof), **proof)
    assert result.actual_recovered_cents == 500
    assert result.fee_eligible_recovered_cents == result.recovery_fee_cents == 0


def test_summary_preserves_amount_distinctions_and_legal_boundary():
    summary = render_engagement_summary(accepted())
    assert "fee-eligible actual recovered funds" in summary
    assert "not approved claim value or actual recovered cash" in summary
    assert "External action authorized by this record:** false" in summary
    assert "not an e-signature system" in summary


@pytest.mark.parametrize("field", [
    "confidentiality_terms_reference",
    "data_use_terms_reference",
    "termination_terms_reference",
    "attribution_terms_reference",
    "governing_agreement_reference",
])
def test_agreement_hooks_are_required(field):
    with pytest.raises(ValueError, match=field):
        build_recovery_engagement(request(**{field: ""}))


def test_potential_range_and_reference_validation_fail_closed():
    with pytest.raises(ValueError, match="high value"):
        build_recovery_engagement(
            request(
                potential_recovery_low_cents=200,
                potential_recovery_high_cents=100,
            )
        )
    with pytest.raises(ValueError, match="stable non-secret"):
        build_recovery_engagement(request(governing_agreement_reference="not allowed!"))


def test_same_customer_different_audit_cannot_create_fee(tmp_path):
    """Different frozen truth must not be billable under an unrelated contract."""
    proof = proof_case(tmp_path)
    unrelated = accepted(buyer_id="buyer", business_unit="unit")
    with pytest.raises(ValueError, match="audit reference"):
        record_actual_recovery(
            unrelated,
            buyer_posting_evidence_reference="BUYERPOSTED:CASE-001",
            **proof,
        )


def test_retroactive_engagement_does_not_authorize_earlier_claim(tmp_path):
    """A claim issued on September 21 cannot inherit September 23 agreement."""
    proof = proof_case(tmp_path)
    late = accepted_for(proof, accepted_at="2026-09-23T15:00:00-04:00")
    with pytest.raises(ValueError, match="before engagement acceptance"):
        record_actual_recovery(
            late,
            buyer_posting_evidence_reference="BUYERPOSTED:CASE-001",
            **proof,
        )


def test_backdated_stored_claim_cannot_be_reissued_to_bypass_acceptance(tmp_path):
    """A newly reconstructed later claim cannot launder an older persisted one."""
    proof = proof_case(tmp_path)
    accepted_between = accepted_for(proof, accepted_at="2026-09-21T11:00:00Z")
    new_batch = build_recovery_claim_batch(
        truth=proof["truth"], incumbent=proof["incumbent"],
        review_packet=proof["review_packet"], review_routing=proof["review_routing"],
        buyer_review=proof["buyer_review"], issued_at="2026-09-21T12:00:00Z",
    )
    forged = dict(proof, claim_batch=new_batch)
    with pytest.raises(ValueError, match="persisted recovery claim"):
        record_actual_recovery(
            accepted_between,
            buyer_posting_evidence_reference="BUYERPOSTED:CASE-001",
            **forged,
        )


def test_valid_fee_requires_a_specific_audit_identity(tmp_path):
    """A matching account and a generic AUDIT-001 string are insufficient."""
    proof = proof_case(tmp_path)
    legitimate = accepted_for(proof)
    assert legitimate.audit_reference == "TRUTH:" + proof["truth"].truth_hash
    record = record_actual_recovery(
        legitimate,
        buyer_posting_evidence_reference="BUYERPOSTED:CASE-001",
        **proof,
    )
    assert record.billing_authorized is False
    assert record.recovery_fee_cents == 150
