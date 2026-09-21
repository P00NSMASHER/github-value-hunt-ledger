from dataclasses import asdict, replace

import pytest

from freight.audit_workflow import RuleCSVInput, run_audit_workflow
from freight.buyer_review_workflow import BuyerReviewDecisionInput, build_buyer_review_batch
from freight.carrier_action_execution import (
    CarrierActionDeliveryEvidence,
    CarrierActionExecutionEvidence,
    ExecutionChannel,
    ExecutionOutcome,
    build_carrier_action_execution_intent,
    record_carrier_action_delivery_confirmation,
    record_carrier_action_execution,
    render_delivery_receipt_markdown,
    render_execution_intent_markdown,
    render_execution_receipt_markdown,
    validate_delivery_history,
    validate_execution_history,
    verify_carrier_action_delivery_receipt,
    verify_carrier_action_execution_intent,
    verify_carrier_action_execution_receipt,
)
from freight.carrier_action_payload import (
    authorize_carrier_action_payload,
    build_carrier_action_payload,
)
from freight.carrier_action_workflow import (
    CarrierActionApprovalInput,
    build_carrier_action_proposal_batch,
)
from freight.contracts import canonical_hash, open_incumbent_output, seal_incumbent_submission
from freight.engagement_state import resolve_engagement
from freight.external_action_authorization import (
    ActionType,
    revoke_authorization,
)
from freight.pilot_activation_packet import build_packet
from freight.pilot_charter import build_charter, from_dict as charter_from_dict
from freight.pilot_reporting import ReviewDisposition
from freight.recovery_claim_workflow import build_recovery_claim_batch


INVOICE_HEADER = "invoice_id,shipment_id,customer_id,carrier_id,currency,charge_id,charge_code,service_date,quantity_units,billed_cents\n"
RULE_HEADER = "charge_code,pricing_model,effective_from,effective_to,fixed_cents,unit_rate_cents\n"


def active_charter():
    readiness = {
        "authorization_documented": True,
        "read_only_access": True,
        "population_reproducible": True,
        "incumbent_output_sealable": True,
        "settlement_observable": True,
        "material_authority_reconstructable": True,
        "customer_identity_stable": True,
        "carrier_identity_stable": True,
        "retention_defined": True,
        "deletion_defined": True,
        "invoice_source_coverage": 1.0,
        "authority_source_coverage": 1.0,
        "shipment_evidence_coverage": 1.0,
    }
    packet = build_packet(
        readiness,
        {
            "status": "READY",
            "route": "CONTROLLED_MANUAL_BLIND_PILOT",
            "blockers": [],
            "conditions": [],
            "warnings": [],
        },
    )
    request = charter_from_dict(
        {
            "engagement_id": "ENG-EXEC-1",
            "buyer_id": "buyer",
            "business_unit": "unit",
            "population_rule": "period",
            "source_date_start": "2026-09-01",
            "source_date_end": "2026-09-30",
            "carrier_scope": ["K"],
            "mode_scope": ["LTL"],
            "fixed_fee_usd": 20000,
            "buyer_truth_owner_role": "Truth Owner",
            "buyer_action_approver_role": "VP Supply Chain",
            "freight_engagement_owner_role": "Pilot Lead",
            "buyer_acknowledges_scope": True,
            "buyer_acknowledges_blind_protocol": True,
            "buyer_acknowledges_report_totals_separate": True,
            "buyer_acknowledges_no_guaranteed_recovery": True,
            "freight_acknowledges_no_external_action_without_buyer_approval": True,
        }
    )
    return __import__("json").loads(
        __import__("json").dumps(
            __import__("dataclasses").asdict(
                build_charter(
                    __import__("json").loads(
                        __import__("json").dumps(__import__("dataclasses").asdict(packet))
                    ),
                    request,
                )
            )
        )
    )


def setup():
    result = run_audit_workflow(
        invoice_filename="charges.csv",
        invoice_data=(
            INVOICE_HEADER
            + "I1,S1,C,K,USD,X1,A,2026-09-10,1,12500\n"
        ).encode(),
        buyer_id="buyer",
        business_unit="unit",
        selection_rule="period",
        rule_inputs=(
            RuleCSVInput(
                "a.csv",
                (RULE_HEADER + "A,FIXED,2026-09-01,,10000,\n").encode(),
                "C","K","USD","a","a"*64,True,
            ),
        ),
    )
    artifacts = result.artifacts
    assert artifacts is not None
    case_hash = artifacts.review_routing.buyer_review_case_hashes[0]
    buyer_review = build_buyer_review_batch(
        review_packet=artifacts.review_packet,
        review_routing=artifacts.review_routing,
        truth=artifacts.factory.truth,
        reviewer_role="Buyer Controller",
        decisions=(
            BuyerReviewDecisionInput(
                case_hash,
                ReviewDisposition.CONFIRMED,
                2,
                "2026-09-21T09:00:00Z",
            ),
        ),
    )
    population = artifacts.population_build.population
    incumbent = open_incumbent_output(
        population=population,
        truth=artifacts.factory.truth,
        submission=seal_incumbent_submission(population, "incumbent-source"),
        finding_ids=(),
    )
    recovery_claims = build_recovery_claim_batch(
        truth=artifacts.factory.truth,
        incumbent=incumbent,
        review_packet=artifacts.review_packet,
        review_routing=artifacts.review_routing,
        buyer_review=buyer_review,
        issued_at="2026-09-21T10:00:00Z",
    )
    proposal = build_carrier_action_proposal_batch(
        recovery_claims=recovery_claims
    ).proposals[0]
    payload = build_carrier_action_payload(
        proposal=proposal,
        recovery_claims=recovery_claims,
        action_type=ActionType.REQUEST_CREDIT_REVIEW,
    )
    charter = active_charter()
    authorization = authorize_carrier_action_payload(
        resolution=resolve_engagement(charter),
        operative_charter=charter,
        truth=artifacts.factory.truth,
        review_packet=artifacts.review_packet,
        review_routing=artifacts.review_routing,
        buyer_review=buyer_review,
        recovery_claims=recovery_claims,
        proposal=proposal,
        payload=payload,
        approval=CarrierActionApprovalInput(
            proposal_hash=proposal.proposal_hash,
            authorization_id="ACT-EXEC-1",
            action_type=ActionType.REQUEST_CREDIT_REVIEW,
            recipient_reference_hash="d"*64,
            action_payload_hash=payload.payload_hash,
            approver_role="VP Supply Chain",
            issued_on="2026-09-21",
            expires_on="2026-09-30",
        ),
    )
    return authorization, proposal, payload, recovery_claims


def _rehash_execution_receipt(receipt, **changes):
    candidate = replace(receipt, **changes)
    fields = asdict(candidate)
    fields.pop("receipt_hash")
    return replace(
        candidate,
        receipt_hash=canonical_hash({"schema": 1, **fields}),
    )


def _rehash_delivery_receipt(receipt, **changes):
    candidate = replace(receipt, **changes)
    fields = asdict(candidate)
    fields.pop("delivery_receipt_hash")
    return replace(
        candidate,
        delivery_receipt_hash=canonical_hash({"schema": 2, **fields}),
    )


def evidence(intent, outcome=ExecutionOutcome.SUBMITTED, executed_at="2026-09-21T11:01:00Z"):
    return CarrierActionExecutionEvidence(
        execution_key=intent.execution_key,
        outcome=outcome,
        channel=ExecutionChannel.EMAIL,
        external_reference_hash="e"*64,
        evidence_source_hash="f"*64,
        executed_at=executed_at,
        executor_role="Freight Operator",
    )


def test_execution_intent_is_deterministic_and_has_stable_idempotency_key():
    auth, proposal, payload, claims = setup()
    a = build_carrier_action_execution_intent(
        authorization=auth,
        proposal=proposal,
        payload=payload,
        recovery_claims=claims,
        prepared_at="2026-09-21T11:00:00Z",
    )
    b = build_carrier_action_execution_intent(
        authorization=auth,
        proposal=proposal,
        payload=payload,
        recovery_claims=claims,
        prepared_at="2026-09-21T11:00:00Z",
    )
    later = build_carrier_action_execution_intent(
        authorization=auth,
        proposal=proposal,
        payload=payload,
        recovery_claims=claims,
        prepared_at="2026-09-21T11:05:00Z",
    )
    assert a == b
    assert a.execution_key == later.execution_key
    assert a.intent_hash != later.intent_hash
    assert a.buyer_id == "buyer"
    assert a.business_unit == "unit"
    assert a.payload_hash == payload.payload_hash
    assert a.recipient_reference_hash == auth.recipient_reference_hash
    assert len(a.execution_key) == 64
    assert len(a.intent_hash) == 64


@pytest.mark.parametrize(
    ("outcome","submitted","delivered"),
    [
        (ExecutionOutcome.FAILED, False, False),
        (ExecutionOutcome.SUBMITTED, True, False),
        (ExecutionOutcome.DELIVERED, True, True),
    ],
)
def test_receipt_distinguishes_failed_submitted_and_delivered(outcome, submitted, delivered):
    auth, proposal, payload, claims = setup()
    intent = build_carrier_action_execution_intent(
        authorization=auth,
        proposal=proposal,
        payload=payload,
        recovery_claims=claims,
        prepared_at="2026-09-21T11:00:00Z",
    )
    receipt = record_carrier_action_execution(
        intent=intent,
        authorization=auth,
        proposal=proposal,
        payload=payload,
        recovery_claims=claims,
        evidence=evidence(intent, outcome=outcome),
    )
    assert receipt.action_submitted is submitted
    assert receipt.delivery_confirmed is delivered
    assert receipt.outcome == outcome.value
    assert len(receipt.receipt_hash) == 64
    verify_carrier_action_execution_receipt(receipt)


def test_receipt_rejects_execution_before_intent_preparation():
    auth, proposal, payload, claims = setup()
    intent = build_carrier_action_execution_intent(
        authorization=auth,
        proposal=proposal,
        payload=payload,
        recovery_claims=claims,
        prepared_at="2026-09-21T11:00:00Z",
    )
    with pytest.raises(ValueError, match="cannot precede"):
        record_carrier_action_execution(
            intent=intent,
            authorization=auth,
            proposal=proposal,
            payload=payload,
            recovery_claims=claims,
            evidence=evidence(intent, executed_at="2026-09-21T10:59:59Z"),
        )


def test_revocation_after_preparation_blocks_later_execution_receipt():
    auth, proposal, payload, claims = setup()
    intent = build_carrier_action_execution_intent(
        authorization=auth,
        proposal=proposal,
        payload=payload,
        recovery_claims=claims,
        prepared_at="2026-09-21T11:00:00Z",
    )
    revocation = revoke_authorization(
        auth,
        revocation_id="REV-EXEC-1",
        revoked_on="2026-09-22",
        approver_role="VP Supply Chain",
        reason="Buyer withdrew approval before execution",
    )
    with pytest.raises(ValueError, match="REVOKED"):
        record_carrier_action_execution(
            intent=intent,
            authorization=auth,
            proposal=proposal,
            payload=payload,
            recovery_claims=claims,
            evidence=evidence(intent, executed_at="2026-09-22T10:00:00Z"),
            revocations=(revocation,),
        )


def test_expired_authorization_cannot_prepare_execution_intent():
    auth, proposal, payload, claims = setup()
    with pytest.raises(ValueError, match="EXPIRED"):
        build_carrier_action_execution_intent(
            authorization=auth,
            proposal=proposal,
            payload=payload,
            recovery_claims=claims,
            prepared_at="2026-10-01T10:00:00Z",
        )


def test_tampered_intent_is_rejected():
    auth, proposal, payload, claims = setup()
    intent = build_carrier_action_execution_intent(
        authorization=auth,
        proposal=proposal,
        payload=payload,
        recovery_claims=claims,
        prepared_at="2026-09-21T11:00:00Z",
    )
    bad = replace(intent, body_text=intent.body_text + "\nChanged")
    with pytest.raises(ValueError, match="does not match current proofs"):
        verify_carrier_action_execution_intent(
            bad,
            authorization=auth,
            proposal=proposal,
            payload=payload,
            recovery_claims=claims,
        )


def test_rehashed_execution_receipt_cannot_claim_execution_before_preparation():
    auth, proposal, payload, claims = setup()
    intent = build_carrier_action_execution_intent(
        authorization=auth,
        proposal=proposal,
        payload=payload,
        recovery_claims=claims,
        prepared_at="2026-09-21T11:00:00Z",
    )
    receipt = record_carrier_action_execution(
        intent=intent,
        authorization=auth,
        proposal=proposal,
        payload=payload,
        recovery_claims=claims,
        evidence=evidence(intent, outcome=ExecutionOutcome.SUBMITTED),
    )
    forged = _rehash_execution_receipt(
        receipt,
        prepared_at="2026-09-21T11:02:00.000000Z",
    )
    with pytest.raises(ValueError, match="predates preparation"):
        verify_carrier_action_execution_receipt(forged)


def test_rehashed_execution_receipt_cannot_change_action_or_amount_semantics():
    auth, proposal, payload, claims = setup()
    intent = build_carrier_action_execution_intent(
        authorization=auth,
        proposal=proposal,
        payload=payload,
        recovery_claims=claims,
        prepared_at="2026-09-21T11:00:00Z",
    )
    receipt = record_carrier_action_execution(
        intent=intent,
        authorization=auth,
        proposal=proposal,
        payload=payload,
        recovery_claims=claims,
        evidence=evidence(intent),
    )
    with pytest.raises(ValueError, match="action type"):
        verify_carrier_action_execution_receipt(
            _rehash_execution_receipt(receipt, action_type="NOT-ACTION")
        )
    with pytest.raises(ValueError, match="positive integer cents"):
        verify_carrier_action_execution_receipt(
            _rehash_execution_receipt(receipt, requested_cents=0)
        )


def test_rehashed_execution_receipt_must_preserve_idempotency_key_and_external_evidence():
    auth, proposal, payload, claims = setup()
    intent = build_carrier_action_execution_intent(
        authorization=auth,
        proposal=proposal,
        payload=payload,
        recovery_claims=claims,
        prepared_at="2026-09-21T11:00:00Z",
    )
    receipt = record_carrier_action_execution(
        intent=intent,
        authorization=auth,
        proposal=proposal,
        payload=payload,
        recovery_claims=claims,
        evidence=evidence(intent),
    )
    with pytest.raises(ValueError, match="idempotency key mismatch"):
        verify_carrier_action_execution_receipt(
            _rehash_execution_receipt(receipt, execution_key="9"*64)
        )
    with pytest.raises(ValueError, match="evidence source is not external"):
        verify_carrier_action_execution_receipt(
            _rehash_execution_receipt(
                receipt,
                evidence_source_hash=receipt.payload_hash,
            )
        )


def test_rehashed_execution_receipt_requires_canonical_utc_timestamps():
    auth, proposal, payload, claims = setup()
    intent = build_carrier_action_execution_intent(
        authorization=auth,
        proposal=proposal,
        payload=payload,
        recovery_claims=claims,
        prepared_at="2026-09-21T11:00:00Z",
    )
    receipt = record_carrier_action_execution(
        intent=intent,
        authorization=auth,
        proposal=proposal,
        payload=payload,
        recovery_claims=claims,
        evidence=evidence(intent),
    )
    forged = _rehash_execution_receipt(
        receipt,
        prepared_at="2026-09-21T07:00:00-04:00",
    )
    with pytest.raises(ValueError, match="canonical UTC"):
        verify_carrier_action_execution_receipt(forged)


def test_rehashed_execution_receipt_rejects_duplicate_or_unsorted_finding_sets():
    auth, proposal, payload, claims = setup()
    intent = build_carrier_action_execution_intent(
        authorization=auth,
        proposal=proposal,
        payload=payload,
        recovery_claims=claims,
        prepared_at="2026-09-21T11:00:00Z",
    )
    receipt = record_carrier_action_execution(
        intent=intent,
        authorization=auth,
        proposal=proposal,
        payload=payload,
        recovery_claims=claims,
        evidence=evidence(intent),
    )
    finding_id = receipt.finding_ids[0]
    with pytest.raises(ValueError, match="unique"):
        verify_carrier_action_execution_receipt(
            _rehash_execution_receipt(
                receipt,
                finding_ids=(finding_id, finding_id),
            )
        )
    with pytest.raises(ValueError, match="sorted"):
        verify_carrier_action_execution_receipt(
            _rehash_execution_receipt(
                receipt,
                finding_ids=("z-finding", "a-finding"),
            )
        )


def test_receipt_flags_are_hash_verified():
    auth, proposal, payload, claims = setup()
    intent = build_carrier_action_execution_intent(
        authorization=auth,
        proposal=proposal,
        payload=payload,
        recovery_claims=claims,
        prepared_at="2026-09-21T11:00:00Z",
    )
    receipt = record_carrier_action_execution(
        intent=intent,
        authorization=auth,
        proposal=proposal,
        payload=payload,
        recovery_claims=claims,
        evidence=evidence(intent, outcome=ExecutionOutcome.SUBMITTED),
    )
    bad = replace(receipt, delivery_confirmed=True)
    with pytest.raises(ValueError, match="delivery flag mismatch|hash mismatch"):
        verify_carrier_action_execution_receipt(bad)


def test_existing_proof_hash_cannot_be_reused_as_execution_evidence():
    auth, proposal, payload, claims = setup()
    intent = build_carrier_action_execution_intent(
        authorization=auth,
        proposal=proposal,
        payload=payload,
        recovery_claims=claims,
        prepared_at="2026-09-21T11:00:00Z",
    )
    bad_evidence = replace(
        evidence(intent),
        evidence_source_hash=payload.payload_hash,
    )
    with pytest.raises(ValueError, match="external to existing proof"):
        record_carrier_action_execution(
            intent=intent,
            authorization=auth,
            proposal=proposal,
            payload=payload,
            recovery_claims=claims,
            evidence=bad_evidence,
        )


def test_history_rejects_two_submitted_executions_for_same_idempotency_key():
    auth, proposal, payload, claims = setup()
    intent = build_carrier_action_execution_intent(
        authorization=auth,
        proposal=proposal,
        payload=payload,
        recovery_claims=claims,
        prepared_at="2026-09-21T11:00:00Z",
    )
    submitted = record_carrier_action_execution(
        intent=intent,
        authorization=auth,
        proposal=proposal,
        payload=payload,
        recovery_claims=claims,
        evidence=evidence(intent, outcome=ExecutionOutcome.SUBMITTED),
    )
    delivered = record_carrier_action_execution(
        intent=intent,
        authorization=auth,
        proposal=proposal,
        payload=payload,
        recovery_claims=claims,
        evidence=replace(
            evidence(
                intent,
                outcome=ExecutionOutcome.DELIVERED,
                executed_at="2026-09-21T11:02:00Z",
            ),
            external_reference_hash="1"*64,
            evidence_source_hash="2"*64,
        ),
    )
    with pytest.raises(ValueError, match="multiple submitted executions"):
        validate_execution_history((submitted, delivered))


def test_multiple_failed_attempts_do_not_count_as_submitted_duplicate():
    auth, proposal, payload, claims = setup()
    intent = build_carrier_action_execution_intent(
        authorization=auth,
        proposal=proposal,
        payload=payload,
        recovery_claims=claims,
        prepared_at="2026-09-21T11:00:00Z",
    )
    first = record_carrier_action_execution(
        intent=intent,
        authorization=auth,
        proposal=proposal,
        payload=payload,
        recovery_claims=claims,
        evidence=evidence(intent, outcome=ExecutionOutcome.FAILED),
    )
    second = record_carrier_action_execution(
        intent=intent,
        authorization=auth,
        proposal=proposal,
        payload=payload,
        recovery_claims=claims,
        evidence=replace(
            evidence(
                intent,
                outcome=ExecutionOutcome.FAILED,
                executed_at="2026-09-21T11:02:00Z",
            ),
            external_reference_hash="1"*64,
            evidence_source_hash="2"*64,
        ),
    )
    validate_execution_history((first, second))


def test_renderers_do_not_conflate_intent_submission_delivery_or_recovery():
    auth, proposal, payload, claims = setup()
    intent = build_carrier_action_execution_intent(
        authorization=auth,
        proposal=proposal,
        payload=payload,
        recovery_claims=claims,
        prepared_at="2026-09-21T11:00:00Z",
    )
    receipt = record_carrier_action_execution(
        intent=intent,
        authorization=auth,
        proposal=proposal,
        payload=payload,
        recovery_claims=claims,
        evidence=evidence(intent, outcome=ExecutionOutcome.SUBMITTED),
    )
    intent_text = render_execution_intent_markdown(intent)
    receipt_text = render_execution_receipt_markdown(receipt)
    assert "does not mean the action was submitted or delivered" in intent_text
    assert "SUBMITTED does not mean delivery was confirmed" in receipt_text
    assert "does not prove settlement" in receipt_text


def submitted_context():
    auth, proposal, payload, claims = setup()
    intent = build_carrier_action_execution_intent(
        authorization=auth,
        proposal=proposal,
        payload=payload,
        recovery_claims=claims,
        prepared_at="2026-09-21T11:00:00Z",
    )
    receipt = record_carrier_action_execution(
        intent=intent,
        authorization=auth,
        proposal=proposal,
        payload=payload,
        recovery_claims=claims,
        evidence=evidence(intent, outcome=ExecutionOutcome.SUBMITTED),
    )
    return auth, proposal, payload, claims, intent, receipt


def delivery_evidence(
    receipt,
    *,
    delivered_at="2026-09-21T11:05:00Z",
    delivery_reference_hash="3"*64,
    evidence_source_hash="4"*64,
):
    return CarrierActionDeliveryEvidence(
        execution_key=receipt.execution_key,
        submitted_receipt_hash=receipt.receipt_hash,
        delivered_at=delivered_at,
        delivery_reference_hash=delivery_reference_hash,
        evidence_source_hash=evidence_source_hash,
        verifier_role="Delivery Verifier",
    )


def test_async_delivery_confirmation_attaches_to_submitted_receipt():
    _, _, _, _, _, submitted = submitted_context()
    delivery = record_carrier_action_delivery_confirmation(
        submitted_receipt=submitted,
        evidence=delivery_evidence(submitted),
    )
    assert delivery.buyer_id == "buyer"
    assert delivery.business_unit == "unit"
    assert delivery.execution_key == submitted.execution_key
    assert delivery.submitted_receipt_hash == submitted.receipt_hash
    assert delivery.delivery_confirmed is True
    assert delivery.delivered_at == "2026-09-21T11:05:00.000000Z"
    assert len(delivery.delivery_receipt_hash) == 64
    verify_carrier_action_delivery_receipt(delivery)


def test_failed_execution_cannot_receive_delivery_confirmation():
    auth, proposal, payload, claims = setup()
    intent = build_carrier_action_execution_intent(
        authorization=auth,
        proposal=proposal,
        payload=payload,
        recovery_claims=claims,
        prepared_at="2026-09-21T11:00:00Z",
    )
    failed = record_carrier_action_execution(
        intent=intent,
        authorization=auth,
        proposal=proposal,
        payload=payload,
        recovery_claims=claims,
        evidence=evidence(intent, outcome=ExecutionOutcome.FAILED),
    )
    with pytest.raises(ValueError, match="requires a submitted"):
        record_carrier_action_delivery_confirmation(
            submitted_receipt=failed,
            evidence=delivery_evidence(failed),
        )


def test_already_delivered_execution_does_not_get_second_delivery_receipt():
    auth, proposal, payload, claims = setup()
    intent = build_carrier_action_execution_intent(
        authorization=auth,
        proposal=proposal,
        payload=payload,
        recovery_claims=claims,
        prepared_at="2026-09-21T11:00:00Z",
    )
    delivered = record_carrier_action_execution(
        intent=intent,
        authorization=auth,
        proposal=proposal,
        payload=payload,
        recovery_claims=claims,
        evidence=evidence(intent, outcome=ExecutionOutcome.DELIVERED),
    )
    with pytest.raises(ValueError, match="already confirms delivery"):
        record_carrier_action_delivery_confirmation(
            submitted_receipt=delivered,
            evidence=delivery_evidence(delivered),
        )


def test_delivery_cannot_predate_submission():
    _, _, _, _, _, submitted = submitted_context()
    with pytest.raises(ValueError, match="cannot precede"):
        record_carrier_action_delivery_confirmation(
            submitted_receipt=submitted,
            evidence=delivery_evidence(
                submitted,
                delivered_at="2026-09-21T11:00:30Z",
            ),
        )


def test_delivery_requires_new_external_evidence():
    _, _, _, _, _, submitted = submitted_context()
    with pytest.raises(ValueError, match="external and new"):
        record_carrier_action_delivery_confirmation(
            submitted_receipt=submitted,
            evidence=delivery_evidence(
                submitted,
                evidence_source_hash=submitted.evidence_source_hash,
            ),
        )


def test_delivery_receipt_retains_submission_evidence_provenance():
    _, _, _, _, _, submitted = submitted_context()
    delivery = record_carrier_action_delivery_confirmation(
        submitted_receipt=submitted,
        evidence=delivery_evidence(submitted),
    )
    assert delivery.submission_evidence_source_hash == submitted.evidence_source_hash
    verify_carrier_action_delivery_receipt(delivery)


def test_rehashed_delivery_receipt_cannot_change_execution_semantics():
    _, _, _, _, _, submitted = submitted_context()
    delivery = record_carrier_action_delivery_confirmation(
        submitted_receipt=submitted,
        evidence=delivery_evidence(submitted),
    )
    with pytest.raises(ValueError, match="action type"):
        verify_carrier_action_delivery_receipt(
            _rehash_delivery_receipt(delivery, action_type="NOT-ACTION")
        )
    with pytest.raises(ValueError, match="invalid delivery receipt channel"):
        verify_carrier_action_delivery_receipt(
            _rehash_delivery_receipt(delivery, channel="TELEPATHY")
        )
    with pytest.raises(ValueError, match="positive integer cents"):
        verify_carrier_action_delivery_receipt(
            _rehash_delivery_receipt(delivery, requested_cents=0)
        )


def test_rehashed_delivery_receipt_must_preserve_execution_key_and_new_evidence():
    _, _, _, _, _, submitted = submitted_context()
    delivery = record_carrier_action_delivery_confirmation(
        submitted_receipt=submitted,
        evidence=delivery_evidence(submitted),
    )
    with pytest.raises(ValueError, match="execution key mismatch"):
        verify_carrier_action_delivery_receipt(
            _rehash_delivery_receipt(delivery, execution_key="8"*64)
        )
    with pytest.raises(ValueError, match="external and new"):
        verify_carrier_action_delivery_receipt(
            _rehash_delivery_receipt(
                delivery,
                delivery_evidence_source_hash=delivery.submission_evidence_source_hash,
            )
        )


def test_rehashed_delivery_receipt_requires_canonical_utc_timestamps():
    _, _, _, _, _, submitted = submitted_context()
    delivery = record_carrier_action_delivery_confirmation(
        submitted_receipt=submitted,
        evidence=delivery_evidence(submitted),
    )
    forged = _rehash_delivery_receipt(
        delivery,
        delivered_at="2026-09-21T07:05:00-04:00",
    )
    with pytest.raises(ValueError, match="canonical UTC"):
        verify_carrier_action_delivery_receipt(forged)


def test_rehashed_delivery_receipt_rejects_forged_submission_evidence_provenance():
    _, _, _, _, _, submitted = submitted_context()
    delivery = record_carrier_action_delivery_confirmation(
        submitted_receipt=submitted,
        evidence=delivery_evidence(submitted),
    )
    with pytest.raises(ValueError, match="submission evidence source is not external"):
        verify_carrier_action_delivery_receipt(
            _rehash_delivery_receipt(
                delivery,
                submission_evidence_source_hash=delivery.payload_hash,
            )
        )


def test_delivery_receipt_is_self_verifying():
    _, _, _, _, _, submitted = submitted_context()
    delivery = record_carrier_action_delivery_confirmation(
        submitted_receipt=submitted,
        evidence=delivery_evidence(submitted),
    )
    bad = replace(delivery, delivered_at="2026-09-21T11:06:00.000000Z")
    with pytest.raises(ValueError, match="hash mismatch"):
        verify_carrier_action_delivery_receipt(bad)


def test_delivery_history_rejects_second_confirmation_for_same_submission():
    _, _, _, _, _, submitted = submitted_context()
    first = record_carrier_action_delivery_confirmation(
        submitted_receipt=submitted,
        evidence=delivery_evidence(submitted),
    )
    second = record_carrier_action_delivery_confirmation(
        submitted_receipt=submitted,
        evidence=delivery_evidence(
            submitted,
            delivered_at="2026-09-21T11:06:00Z",
            delivery_reference_hash="5"*64,
            evidence_source_hash="6"*64,
        ),
    )
    with pytest.raises(ValueError, match="multiple delivery confirmations"):
        validate_delivery_history((first, second))


def test_delivery_renderer_keeps_delivery_separate_from_recovery():
    _, _, _, _, _, submitted = submitted_context()
    delivery = record_carrier_action_delivery_confirmation(
        submitted_receipt=submitted,
        evidence=delivery_evidence(submitted),
    )
    text = render_delivery_receipt_markdown(delivery)
    assert "Delivery Confirmation" in text
    assert "Delivery confirmed: **yes**" in text
    assert "does not prove settlement" in text
