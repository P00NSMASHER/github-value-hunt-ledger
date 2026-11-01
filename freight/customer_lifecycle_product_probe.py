"""Synthetic customer-to-payment bridge using REAL RecoveryOS payment-orchestration code.

This is an isolated executable probe, not a production API, bank integration,
OCR service, authenticated carrier portal or customer communication system.
All identities, receipts, dates, payment providers and values in its tests are fake.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import re

from freight.payment_orchestration import (
    PaymentOrchestrator,
    authorize_payment,
    prepare_payment_instruction,
    verify_payment_snapshot,
)

_SHA = re.compile(r"^[a-f0-9]{64}$")


@dataclass(frozen=True)
class SyntheticCustomerCase:
    scenario_id: str
    customer_id: str
    carrier_id: str
    invoice_id: str
    source_sha256: str
    truth: str
    independently_validated_cents: int
    contract_accepted: bool
    claim_authorized: bool
    authorization_revoked: bool = False
    receipt_reconciled: bool = False
    fee_bps: int = 2000


@dataclass(frozen=True)
class ProbeReceipt:
    scenario_id: str
    assessment: str
    real_orchestrator_state: str
    provider_settled_cents: int
    customer_reconciled_cents: int
    fee_eligible_cents: int
    simulator_provenance: str


def run_synthetic_customer_case(
    case: SyntheticCustomerCase,
    provider_states: tuple[str, ...] = ("SUBMITTED", "ACCEPTED", "SETTLED"),
) -> ProbeReceipt:
    """Run a fictitious case against real RecoveryOS payment-orchestrator objects.

    Note that provider SETTLED is NOT bank reconciled or fee earned.
    Fee eligibility is zero unless a separate fake customer receipt flag exists.
    """
    if not case.scenario_id.startswith("SC-") or not case.customer_id.startswith("FCUST-"):
        raise ValueError("probe requires synthetic-only identifiers")
    if type(case.independently_validated_cents) is not int or case.independently_validated_cents < 0:
        raise ValueError("invalid synthetic validated amount")
    if not 0 <= case.fee_bps <= 10000:
        raise ValueError("invalid contingency fee")
    if not _SHA.fullmatch(case.source_sha256):
        raise ValueError("synthetic source must be SHA-256 bound")
    if (case.truth != "POSITIVE" or case.independently_validated_cents == 0
            or not case.contract_accepted or not case.claim_authorized
            or case.authorization_revoked):
        return ProbeReceipt(
            scenario_id=case.scenario_id, assessment="CLAIM_BLOCKED",
            real_orchestrator_state="NOT_PREPARED",
            provider_settled_cents=0, customer_reconciled_cents=0,
            fee_eligible_cents=0, simulator_provenance="SYNTHETIC_ONLY",
        )

    instruction = prepare_payment_instruction(
        instruction_id="SIM-" + case.scenario_id,
        buyer_id=case.customer_id,
        business_unit="SYNTHETIC_TEST",
        payer_id=case.carrier_id,
        payee_id=case.customer_id,
        currency="USD",
        amount_cents=case.independently_validated_cents,
        purpose="FICTIONAL_CUSTOMER_RECOVERY_TEST",
        finding_proof_hashes=(case.source_sha256,),
        idempotency_key="SIM-IDEMP-" + case.scenario_id,
    )
    orchestrator = PaymentOrchestrator(instruction)
    authorization = authorize_payment(
        instruction, authorized_by="FICTIONAL_REVIEWER",
        reason="FICTIONAL_CUSTOMER_AUTHORIZED",
        authorized_at="2026-10-07T00:00:00.000000Z",
    )
    orchestrator.authorize(authorization)
    for idx, state in enumerate(provider_states, 1):
        orchestrator.record_provider_event(
            state=state, provider="OFFLINE_FICTIONAL_PROVIDER",
            provider_reference=f"SIM-{case.scenario_id}-{idx}",
            amount_cents=case.independently_validated_cents,
            source_hash=sha256(f"{case.scenario_id}:{state}:{idx}".encode()).hexdigest(),
            occurred_at=f"2026-10-07T00:{idx:02d}:00.000000Z",
        )
    snapshot = orchestrator.snapshot()
    verify_payment_snapshot(
        instruction, authorization, orchestrator.events, snapshot,
    )
    settled = snapshot.settled_cents
    reconciled = settled if case.receipt_reconciled else 0
    fee = (reconciled * case.fee_bps) // 10000
    return ProbeReceipt(
        scenario_id=case.scenario_id,
        assessment="FICTIONAL_PROVIDER_REVERSED" if snapshot.current_state == "REVERSED"
                   else ("FICTIONAL_CUSTOMER_RECONCILED" if reconciled else "NOT_RECONCILED"),
        real_orchestrator_state=snapshot.current_state,
        provider_settled_cents=settled,
        customer_reconciled_cents=reconciled,
        fee_eligible_cents=fee,
        simulator_provenance="SYNTHETIC_ONLY",
    )
