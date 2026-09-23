from dataclasses import replace

import pytest

from freight.audit_workflow import RuleCSVInput, run_audit_workflow
from freight.buyer_review_workflow import BuyerReviewDecisionInput, build_buyer_review_batch
from freight.contracts import open_incumbent_output, seal_incumbent_submission
from freight.carrier_action_payload import CarrierActionPayload
from freight.pilot_reporting import ReviewDisposition
from freight.recovery_claim_workflow import build_recovery_claim_batch
from freight.recovery_stack import (
    ContractRedlineTarget,
    FleetOperationEvidence,
    LandedCostObservation,
    RecoveryStackStore,
    StackCapability,
    StackJobState,
    build_recovery_stack_plan,
    verify_recovery_stack_plan,
)


INVOICE_HEADER = "invoice_id,shipment_id,customer_id,carrier_id,currency,charge_id,charge_code,service_date,quantity_units,billed_cents\n"
RULE_HEADER = "charge_code,pricing_model,effective_from,effective_to,fixed_cents,unit_rate_cents\n"


def claim_batch():
    result = run_audit_workflow(
        invoice_filename="charges.csv",
        invoice_data=(INVOICE_HEADER + "I1,S1,C,K,USD,X1,A,2026-09-10,1,12000\n").encode(),
        buyer_id="buyer",
        business_unit="unit",
        selection_rule="period",
        rule_inputs=(RuleCSVInput(
            "a.csv", (RULE_HEADER + "A,FIXED,2026-09-01,,10000,\n").encode(),
            "C", "K", "USD", "a", "a" * 64, True,
        ),),
    )
    artifacts = result.artifacts
    assert artifacts is not None
    case_hash = artifacts.review_routing.buyer_review_case_hashes[0]
    review = build_buyer_review_batch(
        review_packet=artifacts.review_packet,
        review_routing=artifacts.review_routing,
        truth=artifacts.factory.truth,
        reviewer_role="Buyer Controller",
        decisions=(BuyerReviewDecisionInput(
            case_hash, ReviewDisposition.CONFIRMED, 2, "2026-09-21T09:00:00Z"
        ),),
    )
    population = artifacts.population_build.population
    sealed = seal_incumbent_submission(population, "incumbent-source")
    incumbent = open_incumbent_output(
        population=population,
        truth=artifacts.factory.truth,
        submission=sealed,
        finding_ids=(),
    )
    return build_recovery_claim_batch(
        truth=artifacts.factory.truth,
        incumbent=incumbent,
        review_packet=artifacts.review_packet,
        review_routing=artifacts.review_routing,
        buyer_review=review,
        issued_at="2026-09-21T10:00:00Z",
    )


def complete_plan():
    return build_recovery_stack_plan(
        recovery_claims=claim_batch(),
        generated_at="2026-09-23T16:00:00-04:00",
        contract_redlines=(ContractRedlineTarget(
            document_sha256="d" * 64,
            paragraph_id="p-12",
            fingerprint="fp-12",
            find_text="Credits may be requested within 30 days.",
            replace_text="Credits may be requested within 60 days.",
        ),),
        fleet_events=(FleetOperationEvidence(
            event_id="evt-1",
            order_id="order-1",
            shipment_id="S1",
            event_type="PROOF_OF_DELIVERY",
            occurred_at="2026-09-10T18:00:00Z",
            source_sha256="e" * 64,
            proof_of_delivery_sha256="f" * 64,
        ),),
        landed_cost_observations=(LandedCostObservation(
            observation_id="tariff-1",
            hts10="8507600010",
            origin_country="CN",
            destination_country="US",
            effective_on="2026-09-01",
            declared_value_cents=1_000_000,
            currency="USD",
            baseline_rate_bps=250,
            observed_rate_bps=500,
            source_sha256="1" * 64,
        ),),
    )


def test_complete_plan_adds_all_winning_stack_capabilities():
    plan = complete_plan()
    assert {job.capability for job in plan.jobs} == {
        capability.value for capability in StackCapability
    }
    assert plan.estimated_landed_cost_delta_cents == 25_000
    assert all(job.may_assert_recovery is False for job in plan.jobs)
    assert all(len(job.idempotency_key) == 64 for job in plan.jobs)
    verify_recovery_stack_plan(plan)


def test_same_inputs_produce_same_plan_and_jobs():
    assert complete_plan() == complete_plan()


def test_contract_redline_is_strong_targeted_atomic_and_non_overwriting():
    plan = complete_plan()
    job = next(job for job in plan.jobs if job.capability == StackCapability.CONTRACT_REDLINE.value)
    assert job.payload["operation"]["paragraphId"] == "p-12"
    assert job.payload["operation"]["fingerprint"] == "fp-12"
    assert job.payload["options"]["atomic"] is True
    assert job.payload["options"]["requireComplete"] is True
    assert job.payload["source_document_may_be_overwritten"] is False


def test_fleetbase_adapter_is_read_only_evidence_import():
    plan = complete_plan()
    job = next(job for job in plan.jobs if job.capability == StackCapability.FLEET_OPERATIONS.value)
    assert job.payload["mode"] == "READ_ONLY_EVIDENCE_IMPORT"
    assert job.payload["may_mutate_fleetbase"] is False


def test_landed_cost_is_exposure_not_a_recovery_claim():
    plan = complete_plan()
    job = next(job for job in plan.jobs if job.capability == StackCapability.LANDED_COST.value)
    assert job.payload["estimated_delta_cents"] == 25_000
    assert job.payload["classification"] == "EXPOSURE_ONLY"
    assert job.payload["may_create_recovery_claim"] is False


def test_redline_rejects_weak_or_noop_targets():
    with pytest.raises(ValueError, match="must differ"):
        build_recovery_stack_plan(
            recovery_claims=claim_batch(),
            generated_at="2026-09-23T20:00:00Z",
            contract_redlines=(ContractRedlineTarget(
                "d" * 64, "p", "fp", "same", "same"
            ),),
        )


def test_unverified_carrier_payload_is_rejected_before_it_enters_agent_ledger():
    claims = claim_batch()
    forged = CarrierActionPayload(
        proposal_hash="p" * 64,
        recovery_claim_batch_hash=claims.batch_hash,
        action_type="SUBMIT_DISPUTE",
        target_carrier_id="K",
        target_customer_id="C",
        currency="USD",
        requested_cents=2_000,
        line_count=0,
        lines=(),
        subject="forged",
        body_text="forged",
        payload_hash="2" * 64,
    )
    with pytest.raises(ValueError, match="line count mismatch"):
        build_recovery_stack_plan(
            recovery_claims=claims,
            generated_at="2026-09-23T20:00:00Z",
            carrier_payload=forged,
        )


def test_tampered_plan_fails_verification():
    plan = complete_plan()
    with pytest.raises(ValueError, match="plan hash mismatch"):
        verify_recovery_stack_plan(replace(plan, plan_hash="0" * 64))


def test_store_is_idempotent_and_scoped(tmp_path):
    plan = complete_plan()
    store = RecoveryStackStore(tmp_path / "stack.sqlite", buyer_id="buyer", business_unit="unit")
    first = store.persist_plan(plan)
    second = store.persist_plan(plan)
    assert first.created_job_count == plan.job_count
    assert second.created_job_count == 0
    assert second.already_present_count == plan.job_count
    wrong = RecoveryStackStore(tmp_path / "other.sqlite", buyer_id="other", business_unit="unit")
    with pytest.raises(ValueError, match="scope mismatch"):
        wrong.persist_plan(plan)


def test_store_tracks_success_with_append_only_hash_chain(tmp_path):
    plan = complete_plan()
    store = RecoveryStackStore(tmp_path / "stack.sqlite", buyer_id="buyer", business_unit="unit")
    store.persist_plan(plan)
    job = plan.jobs[0]
    assert store.state(job.job_id) is StackJobState.PREPARED
    store.transition(
        job.job_id, state=StackJobState.RUNNING,
        occurred_at="2026-09-23T20:01:00Z", worker_id="worker-1",
    )
    store.transition(
        job.job_id, state=StackJobState.SUCCEEDED,
        occurred_at="2026-09-23T20:02:00Z", worker_id="worker-1",
        result_sha256="9" * 64,
    )
    assert store.state(job.job_id) is StackJobState.SUCCEEDED
    store.verify_event_chain(job.job_id)
    with pytest.raises(ValueError, match="invalid stack job transition"):
        store.transition(
            job.job_id, state=StackJobState.RUNNING,
            occurred_at="2026-09-23T20:03:00Z", worker_id="worker-1",
        )


def test_unknown_outcome_requires_review_then_can_retry(tmp_path):
    plan = complete_plan()
    store = RecoveryStackStore(tmp_path / "stack.sqlite", buyer_id="buyer", business_unit="unit")
    store.persist_plan(plan)
    job = plan.jobs[0]
    store.transition(job.job_id, state=StackJobState.RUNNING,
                     occurred_at="2026-09-23T20:01:00Z", worker_id="worker")
    store.transition(job.job_id, state=StackJobState.UNKNOWN,
                     occurred_at="2026-09-23T20:02:00Z", worker_id="worker",
                     error_code="ADAPTER_TIMEOUT")
    assert store.state(job.job_id) is StackJobState.UNKNOWN
    with pytest.raises(ValueError, match="requires review evidence"):
        store.transition(job.job_id, state=StackJobState.RUNNING,
                         occurred_at="2026-09-23T20:03:00Z", worker_id="unsafe-retry")
    store.transition(job.job_id, state=StackJobState.RUNNING,
                     occurred_at="2026-09-23T20:03:00Z", worker_id="reviewed-retry",
                     result_sha256="8" * 64)
    assert store.state(job.job_id) is StackJobState.RUNNING
    store.verify_event_chain(job.job_id)


def test_store_rejects_backdated_execution_events(tmp_path):
    plan = complete_plan()
    store = RecoveryStackStore(tmp_path / "stack.sqlite", buyer_id="buyer", business_unit="unit")
    store.persist_plan(plan)
    job = plan.jobs[0]
    with pytest.raises(ValueError, match="cannot move backwards"):
        store.transition(
            job.job_id, state=StackJobState.RUNNING,
            occurred_at="2026-09-23T19:59:59Z", worker_id="worker",
        )
