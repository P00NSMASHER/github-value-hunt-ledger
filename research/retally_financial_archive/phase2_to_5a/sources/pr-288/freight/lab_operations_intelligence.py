"""Read-only RETALLY cross-lab work routing, loss-preserving business analysis.

No workers are invoked by routing. Cash/credit statuses inherit the assurance
receipt's explicit *synthetic-only* trust boundary. Inputs are assumptions, not
observed customer behavior or revenue forecasts.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from typing import Mapping, Sequence

from freight.lab_assurance import AssuranceReceipt, AssuranceRejected, digest


LAB_CONSUMERS: Mapping[str, tuple[int, ...]] = {
    "INVOICE_INGESTED": (4, 6),
    "CONTRACT_AUTHORIZED": (2, 6, 9),
    "BLIND_RATING": (1, 3, 10),
    "DISCREPANCY_REVIEWED": (1, 3, 12),
    "BUYER_APPROVED": (2, 6, 9),
    "CLAIM_SUBMITTED": (2, 5, 11),
    "CARRIER_ACKNOWLEDGED": (2, 5),
    "CREDIT_ALLOCATED": (2, 5, 8, 11),
    "CREDIT_RECONCILED": (5, 8, 9),
    "FEE_ACCOUNTED": (2, 5, 8),
    "CUSTOMER_UPDATED": (2, 7, 9),
    "CREDIT_REVERSED": (2, 5, 8, 11, 12),
    "FINANCIAL_RECONCILED": (5, 6, 8, 11, 12),
    "ECONOMICS_ANALYZED": (7, 8, 13, 14),
}
PREREQUISITES = {
    "CONTRACT_AUTHORIZED": ("INVOICE_INGESTED",),
    "BLIND_RATING": ("INVOICE_INGESTED",),
    "DISCREPANCY_REVIEWED": ("BLIND_RATING",),
    "BUYER_APPROVED": ("CONTRACT_AUTHORIZED", "DISCREPANCY_REVIEWED"),
    "CLAIM_SUBMITTED": ("BUYER_APPROVED",),
    "CARRIER_ACKNOWLEDGED": ("CLAIM_SUBMITTED",),
    "CREDIT_ALLOCATED": ("CARRIER_ACKNOWLEDGED",),
    "CREDIT_RECONCILED": ("CREDIT_ALLOCATED",),
    "FEE_ACCOUNTED": ("CREDIT_RECONCILED",),
    "CUSTOMER_UPDATED": ("CLAIM_SUBMITTED",),
    "CREDIT_REVERSED": ("CREDIT_ALLOCATED",),
    "FINANCIAL_RECONCILED": ("CREDIT_RECONCILED", "FEE_ACCOUNTED"),
    "ECONOMICS_ANALYZED": ("FINANCIAL_RECONCILED",),
}


@dataclass(frozen=True)
class JourneyEvent:
    event_id: str
    stage: str
    occurred_at: str
    buyer_id: str
    business_unit: str
    invoice_id: str
    source_hash: str
    claim_id: str
    evidence_ids: tuple[str, ...]


@dataclass(frozen=True)
class LabRoutingReceipt:
    status: str
    scope: str
    source_hash: str
    stage_count: int
    lab_work_items: tuple[Mapping[str, object], ...]
    last_independent_receipt: str
    routing_hash: str


def build_lab_routing(events: Sequence[JourneyEvent], *, assurance: AssuranceReceipt) -> LabRoutingReceipt:
    if assurance.status != "PASS_SYNTHETIC_ONLY" or assurance.scope != "SIGNED_SYNTHETIC_EVIDENCE_ONLY":
        raise AssuranceRejected("ROUTE_REQUIRES_SEPARATE_FINANCIAL_PROOF")
    if not events or events[0].stage != "INVOICE_INGESTED":
        raise AssuranceRejected("ROUTE_REQUIRES_INVOICE_INTAKE")
    seen_stage=set();seen_id=set();out=[];previous=None
    scope=(events[0].buyer_id,events[0].business_unit,events[0].invoice_id,
           events[0].source_hash,events[0].claim_id)
    for index, ev in enumerate(events):
        if ev.stage not in LAB_CONSUMERS:
            raise AssuranceRejected("UNSUPPORTED_LAB_STAGE")
        if ev.event_id in seen_id or not ev.event_id:
            raise AssuranceRejected("DUPLICATE_OR_MISSING_JOURNEY_EVENT")
        seen_id.add(ev.event_id)
        if (ev.buyer_id,ev.business_unit,ev.invoice_id,ev.source_hash,ev.claim_id)!=scope:
            raise AssuranceRejected("LAB_SOURCE_SCOPE_CHANGED")
        try:
            when=datetime.fromisoformat(ev.occurred_at.replace("Z","+00:00"))
        except ValueError as ex:
            raise AssuranceRejected("INVALID_JOURNEY_TIME") from ex
        if when.tzinfo is None or when.utcoffset() is None:
            raise AssuranceRejected("INVALID_JOURNEY_TIME")
        when=when.astimezone(timezone.utc)
        if previous is not None and when < previous:
            raise AssuranceRejected("JOURNEY_OUT_OF_ORDER")
        previous=when
        if not set(PREREQUISITES.get(ev.stage,())).issubset(seen_stage):
            raise AssuranceRejected("JOURNEY_MISSING_PREREQUISITE")
        if not ev.evidence_ids or any(not x or type(x) is not str for x in ev.evidence_ids):
            raise AssuranceRejected("JOURNEY_REQUIRES_EVIDENCE_LINKS")
        if ev.stage in {"FINANCIAL_RECONCILED","ECONOMICS_ANALYZED"} and assurance.receipt_hash not in ev.evidence_ids:
            raise AssuranceRejected("JOURNEY_MISSING_FINANCIAL_PROOF")
        seen_stage.add(ev.stage)
        for lab in LAB_CONSUMERS[ev.stage]:
            out.append({"lab":lab,"event_id":ev.event_id,"stage":ev.stage,
                        "evidence_ids":list(ev.evidence_ids),"order":index+1,
                        "status":"ROUTED_NOT_EXECUTED"})
    if "FINANCIAL_RECONCILED" not in seen_stage or "ECONOMICS_ANALYZED" not in seen_stage:
        raise AssuranceRejected("JOURNEY_MISSING_TERMINAL_CHECKS")
    body={"schema":1,"scope":"ROUTING_PLAN_ONLY_NOT_WORKER_EXECUTION",
          "source_hash":scope[3],"items":out,"receipt_hash":assurance.receipt_hash}
    return LabRoutingReceipt("PASS_ROUTING_CONTRACT",body["scope"],scope[3],len(events),
                             tuple(out),assurance.receipt_hash,digest(body))


@dataclass(frozen=True)
class CostAssumptions:
    currency: str
    analyst_minutes: int
    loaded_hourly_cost_cents: int
    other_cost_cents: int
    additional_claim_value_cents: int
    estimated_collection_probability_bps: int
    applicable_fee_bps: int
    incremental_analyst_minutes: int
    incremental_cost_cents: int


def evaluate_operating_case(assurance: AssuranceReceipt, assumed: CostAssumptions) -> dict:
    """All costs and future recovery probabilities are modeled assumptions.

    Modeled realized-fee margin is *not* real RETALLY revenue or profitability.
    """
    if assurance.status != "PASS_SYNTHETIC_ONLY" or assurance.scope != "SIGNED_SYNTHETIC_EVIDENCE_ONLY":
        raise AssuranceRejected("OPERATING_ANALYSIS_REQUIRES_VERIFIED_SYNTHETIC_PROOF")
    if not isinstance(assumed.currency,str) or len(assumed.currency)!=3 or assumed.currency.upper()!=assumed.currency:
        raise ValueError("currency must be uppercase ISO code")
    for field in ("analyst_minutes","loaded_hourly_cost_cents","other_cost_cents",
                  "additional_claim_value_cents","incremental_analyst_minutes","incremental_cost_cents"):
        x=getattr(assumed,field)
        if type(x) is not int or x<0:
            raise ValueError(field+" must be a nonnegative integer")
    for field in ("estimated_collection_probability_bps","applicable_fee_bps"):
        x=getattr(assumed,field)
        if type(x) is not int or not 0<=x<=10000:
            raise ValueError(field+" must be integer basis points")
    observed=assurance.currency_totals.get(assumed.currency)
    if observed is None:
        raise AssuranceRejected("OPERATING_CURRENCY_NOT_IN_ASSURANCE")
    cost=(assumed.analyst_minutes*assumed.loaded_hourly_cost_cents+59)//60+assumed.other_cost_cents
    incremental_cost=(assumed.incremental_analyst_minutes*assumed.loaded_hourly_cost_cents+59)//60+assumed.incremental_cost_cents
    expected_recovery=assumed.additional_claim_value_cents*assumed.estimated_collection_probability_bps//10000
    expected_fee=expected_recovery*assumed.applicable_fee_bps//10000
    expected_incremental_margin=expected_fee-incremental_cost
    projected_margin=observed["collected_fee_cents"]-cost
    refund_due=observed["fee_refund_due_cents"]
    action=("REMEDIATE_FEE_REFUND" if refund_due>0 else
            "DO_NOT_ESCALATE_ON_MODELED_ECONOMICS" if expected_incremental_margin<=0 else
            "INVESTIGATE_SUPPORTED_ESCALATION")
    report={"scope":"ASSUMPTION_ONLY_BUSINESS_DECISION",
            "source_proof_scope":assurance.scope,"currency":assumed.currency,
            "simulated_recovery_cents":observed["recovered_cents"],
            "simulated_collected_fees_cents":observed["collected_fee_cents"],
            "simulated_open_receivables_cents":observed["fee_receivable_cents"],
            "simulated_refund_liability_cents":refund_due,
            "assumed_service_cost_cents":cost,
            "modeled_current_margin_cents":projected_margin,
            "modeled_additional_collection_cents":expected_recovery,
            "modeled_additional_fee_cents":expected_fee,
            "modeled_additional_cost_cents":incremental_cost,
            "modeled_incremental_margin_cents":expected_incremental_margin,
            "recommended_next_action":action,
            "evidence_needed":"buyer-controlled source/contract and independent bank/carrier remittance",
            "financial_proof_receipt":assurance.receipt_hash}
    report["report_hash"]=digest(report)
    return report
