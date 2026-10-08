"""Independent synthetic staging integration with existing RecoveryOS Python domains.

This is NOT the hosted Floot application; all carrier events are fictional.
No customer data, provider credentials, actual bank calls, or live APIs.
Five existing laboratory PRs remain separate drafts and are never auto-merged.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from hashlib import sha256
from pathlib import Path
import re

from freight.accuracy_benchmark import load_fixture, _build_record, _book
from freight.rating_engine import rate_record, RATED
from freight.payment_orchestration import (
    prepare_payment_instruction,
    authorize_payment,
    PaymentOrchestrator,
    verify_payment_snapshot,
)

LAB_PR_REVISIONS = {
    263: "8c3601db31a1842061ce0544ac174eb8e428047b",
    264: "4ccc7526ccbf2c2988ea66ce21103299c47f03b",
    271: "75f145b635b47ea959c038483209818f354f68e2",
    272: "b0e805401527deca9fb279bcd74b7ed416153d21",
    273: "5fad0a87e9cb54f8c4ba2222f59f0e60a9ecd571",
}
FIXTURE = Path(__file__).parent / "fixtures" / "phase3_accuracy_gold_v1.json"
HASH = re.compile(r"^[a-f0-9]{64}$")


@dataclass(frozen=True)
class FictionalReleaseAuthorization:
    tenant: str
    source_invoice_id: str
    source_customer_id: str
    source_sha256: str
    buyer_signed_scope: bool
    reviewer_independent: bool
    buyer_action_approved: bool
    revoked: bool = False
    provider_reconciled: bool = False
    fee_bps: int = 2000


def validate_synthetic_authority(a: FictionalReleaseAuthorization) -> None:
    if not re.fullmatch(r"SIM-TENANT-[0-9]+", a.tenant):
        raise ValueError("synthetic tenant required")
    if not re.fullmatch(r"INV-[A-Za-z0-9_-]+", a.source_invoice_id):
        raise ValueError("invoice identity required")
    if not a.source_customer_id.startswith("FICTIONAL-"):
        raise ValueError("fictional customer identity required")
    if not HASH.fullmatch(a.source_sha256):
        raise ValueError("source proof must be sha256")
    if not type(a.fee_bps) is int or not 0 <= a.fee_bps <= 5000:
        raise ValueError("fee basis points invalid")


def lab_reconciliation_manifest() -> dict:
    """Manifest of independently accessible drafts; NOT an integrated merge."""
    return {
        "schema_version": 1,
        "draft_pull_requests": LAB_PR_REVISIONS.copy(),
        "all_draft_labs_integrated_into_production": False,
        "requires_human_merge_review": True,
        "common_currency": "USD_INTEGER_CENTS",
        "customer_data": "FICTIONAL_ONLY",
        "real_buyer_pilot": "BLOCKED_PENDING_INDEPENDENT_CUSTOMER_AUTHORIZATION",
    }


def run_actual_domain_shadow(
    *,
    rating_case_id: str,
    authorization: FictionalReleaseAuthorization,
    model_provider_states: tuple[str, ...] = ("SUBMITTED", "ACCEPTED", "SETTLED"),
) -> dict:
    """Exercise ACTUAL rating and payment domains with designed gold scenarios.

    Importantly, the fixture is the existing internal, code-adjacent synthetic
    benchmark. The call tests integration and fails closed; it does NOT estimate
    real production precision, recall, recoveries, or customer cash.
    """
    validate_synthetic_authority(authorization)
    fixture = load_fixture(FIXTURE)
    cases = {row["id"]: row for row in fixture["rating_cases"]}
    if rating_case_id not in cases:
        raise ValueError("unknown frozen rating fixture")
    case = cases[rating_case_id]
    record = _build_record(case["id"], case["record"], fixture["common"])
    if authorization.source_invoice_id != record.invoice_id:
        raise ValueError("synthetic invoice ID not bound to source record")
    if authorization.source_sha256 != record.sources[0].sha256:
        raise ValueError("synthetic source proof hash mismatch")
    if authorization.source_customer_id != "FICTIONAL-" + record.customer_id:
        raise ValueError("synthetic customer scope is not bound to the canonical record")
    observed = rate_record(record, _book(case["authority_profiles"], fixture))
    amount = observed.variance_cents or 0
    reason = "REVIEW_OR_NO_POSITIVE_VARIANCE"
    allowed = (
        observed.status == RATED and observed.authority_verified and amount > 0
        and authorization.buyer_signed_scope and authorization.reviewer_independent
        and authorization.buyer_action_approved and not authorization.revoked
    )
    result = {
        "rating_case_id": rating_case_id,
        "rating_engine_status": observed.status,
        "record_sha256": record.record_hash,
        "rating_sha256": observed.rating_hash,
        "candidate_variance_cents": amount if observed.status == RATED else 0,
        "allowed_fake_submission": allowed,
        "fictitious_carrier_state": "NOT_SENT",
        "carrier_reported_settled_cents": 0,
        "buyer_reconciled_cents": 0,
        "fee_eligible_cents": 0,
        "real_bank_amount_cents": 0,
        "real_customer_proof": False,
        "live_recoveryos_api_tested": False,
        "scope": "ISOLATED_REAL_PYTHON_DOMAIN_SYNTHETIC_FIXTURE",
    }
    if not allowed:
        result["blocking_reason"] = (
            "NO_CURRENT_BUYER_AUTHORIZATION_OR_REVIEW"
            if observed.status == RATED and amount
            else reason
        )
        return result

    # Exact label binding to an existing fictional source invoice.
    instruction = prepare_payment_instruction(
        instruction_id="SIM-SHADOW-" + rating_case_id,
        buyer_id=authorization.source_customer_id,
        business_unit=authorization.tenant,
        payer_id="FICTIONAL-CARRIER",
        payee_id=authorization.source_customer_id,
        currency="USD",
        amount_cents=amount,
        purpose="FICTIONAL_NO_EXTERNAL_SUBMISSION",
        finding_proof_hashes=(record.record_hash,),
        idempotency_key="SIM-IDEMP-" + rating_case_id,
    )
    state = PaymentOrchestrator(instruction)
    signed = authorize_payment(
        instruction,
        authorized_by="FICTIONAL-BUYER-REVIEWER",
        reason="FICTIONAL_EXACT_SCOPE",
        authorized_at="2026-10-07T12:00:00.000000Z",
    )
    state.authorize(signed)
    for n, status in enumerate(model_provider_states, start=1):
        state.record_provider_event(
            state=status,
            provider="SIMULATED_CARRIER_NEVER_CONTACTED",
            provider_reference=f"SIM-{rating_case_id}-{n}",
            amount_cents=amount,
            source_hash=sha256(f"fake:{rating_case_id}:{n}".encode()).hexdigest(),
            occurred_at=f"2026-10-07T12:0{n}:00.000000Z",
        )
    snapshot = state.snapshot()
    verify_payment_snapshot(instruction, signed, state.events, snapshot)
    result["fictitious_carrier_state"] = snapshot.current_state
    result["carrier_reported_settled_cents"] = snapshot.settled_cents
    if snapshot.current_state == "SETTLED" and authorization.provider_reconciled:
        result["buyer_reconciled_cents"] = snapshot.settled_cents
        result["fee_eligible_cents"] = snapshot.settled_cents * authorization.fee_bps // 10000
    return result


def real_customer_release_gate(*, externally_adjudicated_truth: bool,
                               buyer_signed: bool, real_bank_confirmation: bool,
                               tenant_isolation_verified: bool) -> dict:
    blockers = []
    if not buyer_signed: blockers.append("EXECUTED_BUYER_AUTHORIZATION_MISSING")
    if not externally_adjudicated_truth: blockers.append("BLIND_BUYER_TRUTH_MISSING")
    if not real_bank_confirmation: blockers.append("ACTUAL_SETTLEMENT_NOT_CONFIRMED")
    if not tenant_isolation_verified: blockers.append("HOSTED_TENANT_NEGATIVE_TESTS_MISSING")
    return {
        "status": "BLOCKED_EXTERNAL_REAL_CUSTOMER_PROOF" if blockers else "REVIEW_REQUIRED",
        "blockers": blockers,
        "automatic_production_deployment": False,
        "automatic_customer_claims": False,
        "human_compliance_approval_required": True,
    }
