"""RETALLY Phase 2 opt-in research pipeline across existing settlement domain.

Executes read-only independent financial verification and decision analysis.
Returns proposed work items for 14 labs; never triggers them, customers, bank
providers, hosted endpoints, emails, deployment, or recurring workflows.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Sequence

from freight.lab_assurance import Evidence, EvidenceVerifier, FeeEvent, verify_settlement, digest
from freight.lab_operations_intelligence import (
    CostAssumptions, JourneyEvent, build_lab_routing, evaluate_operating_case,
)


@dataclass(frozen=True)
class LabDecisionPacket:
    status: str
    source_scope: str
    financial_proof: dict
    business_decision: dict
    routed_lab_work: dict
    human_review_required: bool
    true_customer_recovery_proven: bool
    product_integration_passed: bool
    packet_hash: str


def evaluate_read_only_phase2(
    settlement_store,
    *,
    assertions: Sequence[Evidence],
    fee_events: Sequence[FeeEvent],
    verifier: EvidenceVerifier,
    assumptions: CostAssumptions,
    journey: Sequence[JourneyEvent],
) -> LabDecisionPacket:
    # Existing SettlementStore remains the operator for append-only allocations.
    # Its own summary is not sufficient proof and does not set the result.
    receipt=verify_settlement(
        settlement_store.path,
        buyer_id=settlement_store.buyer_id,
        business_unit=settlement_store.business_unit,
        assertions=assertions,fee_events=fee_events,verifier=verifier,
    )
    decision=evaluate_operating_case(receipt,assumptions)
    routing=build_lab_routing(journey,assurance=receipt)
    if settlement_store.count("recovery_claims")!=receipt.verified_claims:
        raise ValueError("SETTLEMENT_COUNT_RACE_OR_MISMATCH")
    # Never assert product equivalence. This checks a single case or currency
    # only; do not sum mixed-currency settlement_store.realized_cents globally.
    packet={"schema":1,"status":"RESEARCH_REVIEW_ONLY",
        "source_scope":receipt.scope,
        "financial_proof":asdict(receipt),
        "business_decision":decision,
        "routed_lab_work":asdict(routing),
        "human_review_required":True,
        "true_customer_recovery_proven":False,
        "product_integration_passed":False}
    return LabDecisionPacket(
        status=packet["status"],source_scope=packet["source_scope"],
        financial_proof=packet["financial_proof"],
        business_decision=packet["business_decision"],
        routed_lab_work=packet["routed_lab_work"],
        human_review_required=True,true_customer_recovery_proven=False,
        product_integration_passed=False,packet_hash=digest(packet),
    )


def render_owner_report(packet: LabDecisionPacket) -> str:
    total=packet.financial_proof["currency_totals"]
    currencies=[]
    for currency, amounts in sorted(total.items()):
        currencies.append(
            f"- {currency}: retained credit {amounts['recovered_cents']} cents, "
            f"earned fee {amounts['earned_fee_cents']} cents, "
            f"net fee collected {amounts['collected_fee_cents']} cents, "
            f"receivable {amounts['fee_receivable_cents']} cents, "
            f"refund due {amounts['fee_refund_due_cents']} cents")
    decision=packet.business_decision
    labs=sorted({str(x["lab"]) for x in packet.routed_lab_work["lab_work_items"]},key=int)
    return "\n".join([
        "# RETALLY LABORATORY DECISION REPORT (SYNTHETIC)",
        "",
        "Financial status: independently re-evaluated against **synthetic signed fixtures**, "
        "not authentic buyer, bank, or carrier documentation.",
        "\n## Financial snapshot",*currencies,
        "\n## Assumption-based economics",
        f"- Modeled current operating margin: {decision['modeled_current_margin_cents']} cents",
        f"- Modeled incremental margin: {decision['modeled_incremental_margin_cents']} cents",
        f"- Proposed action: {decision['recommended_next_action']}",
        "\n## Cross-laboratory handoff (not executed)",
        f"- Proposed recipients: {', '.join(labs)}",
        f"- Work items: {len(packet.routed_lab_work['lab_work_items'])}",
        "\n## Non-negotiable evidence gaps",
        "- Authentic buyer-held source ownership and signed contract terms",
        "- Independently confirmed carrier/bank credit and customer remittance",
        "- Hosted RecoveryOS authentication, deployment, and integration tests",
        "- Ground-truth adjudication of actual billing discrepancies",
        "\nNo historical findings are closed. No production activity occurred.",
        f"\nReport packet SHA-256: `{packet.packet_hash}`",
    ])
