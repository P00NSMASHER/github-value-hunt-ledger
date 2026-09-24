"""Buyer-safe RecoveryWorks pilot activation packet.

This packages an authoritative prelaunch decision for human review. It is not
customer-data authorization, kickoff authorization, outreach, or a contract.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from recoveryworks.commercial_pilot import CloudCommercialPilotPackage
from recoveryworks.models import canonical_hash, normalize_sha256
from recoveryworks.pilot_launch_brief import PilotLaunchBrief
from recoveryworks.pilot_launch_gate import (
    PilotLaunchDecision,
    PilotLaunchStatus,
)


@dataclass(frozen=True)
class BuyerDataRequest:
    timing: str
    category: str
    requirement: str

    @property
    def proof_hash(self) -> str:
        return canonical_hash({"schema":1, **asdict(self)})


@dataclass(frozen=True)
class RecoveryWorksActivationPacket:
    packet_id: str
    launch_decision_id: str
    launch_decision_proof_hash: str
    launch_brief_proof_hash: str
    commercial_package_proof_hash: str
    launch_status: PilotLaunchStatus
    offer_name: str
    pricing_currency: str
    diagnostic_fee_cents_hypothesis: int
    recovered_cash_success_fee_bps_hypothesis: int
    monthly_assurance_fee_cents_hypothesis: int
    buyer_data_requests: tuple[BuyerDataRequest, ...]
    buyer_responsibilities: tuple[str, ...]
    recoveryworks_responsibilities: tuple[str, ...]
    protocol_stages: tuple[str, ...]
    report_surfaces: tuple[str, ...]
    commercial_invariants: tuple[str, ...]
    customer_data_authorized: bool = False
    kickoff_authorized: bool = False
    outreach_authorized: bool = False
    external_action_authorized: bool = False
    contract_created: bool = False

    def __post_init__(self) -> None:
        for name in (
            "launch_decision_proof_hash",
            "launch_brief_proof_hash",
            "commercial_package_proof_hash",
        ):
            object.__setattr__(self,name,normalize_sha256(name,getattr(self,name)))
        if not isinstance(self.launch_status,PilotLaunchStatus):
            raise ValueError("launch_status must be PilotLaunchStatus")
        if self.launch_status is PilotLaunchStatus.BLOCKED:
            raise ValueError("blocked launch decision cannot create activation packet")
        if (
            self.customer_data_authorized or self.kickoff_authorized
            or self.outreach_authorized or self.external_action_authorized
            or self.contract_created
        ):
            raise ValueError("activation packet cannot create authorization or commitment")
        expected="recoveryworks-activation-packet:"+canonical_hash(self._identity())
        if self.packet_id!=expected:
            raise ValueError("packet_id does not bind activation packet")

    def _identity(self)->dict[str,Any]:
        return {
            "schema":1,
            "launch_decision_id":self.launch_decision_id,
            "launch_decision_proof_hash":self.launch_decision_proof_hash,
            "launch_brief_proof_hash":self.launch_brief_proof_hash,
            "commercial_package_proof_hash":self.commercial_package_proof_hash,
            "launch_status":self.launch_status.value,
            "offer_name":self.offer_name,
            "pricing_currency":self.pricing_currency,
            "diagnostic_fee_cents_hypothesis":self.diagnostic_fee_cents_hypothesis,
            "recovered_cash_success_fee_bps_hypothesis":
                self.recovered_cash_success_fee_bps_hypothesis,
            "monthly_assurance_fee_cents_hypothesis":
                self.monthly_assurance_fee_cents_hypothesis,
            "buyer_data_request_hashes":[x.proof_hash for x in self.buyer_data_requests],
            "buyer_responsibilities":list(self.buyer_responsibilities),
            "recoveryworks_responsibilities":list(self.recoveryworks_responsibilities),
            "protocol_stages":list(self.protocol_stages),
            "report_surfaces":list(self.report_surfaces),
            "commercial_invariants":list(self.commercial_invariants),
            "customer_data_authorized":False,
            "kickoff_authorized":False,
            "outreach_authorized":False,
            "external_action_authorized":False,
            "contract_created":False,
        }

    @property
    def proof_hash(self)->str:
        return canonical_hash(self._identity())

    def as_dict(self)->dict[str,Any]:
        return {
            **self._identity(),
            "packet_id":self.packet_id,
            "proof_hash":self.proof_hash,
            "buyer_data_requests":[
                {**asdict(x),"proof_hash":x.proof_hash}
                for x in self.buyer_data_requests
            ],
            "state":"BUYER_SAFE_ACTIVATION_PACKET_READY",
        }


_COMMON_REQUESTS=(
    BuyerDataRequest(
        "NOW","AUTHORIZATION",
        "Document buyer entity, approved billing account(s), service period, processing purpose, retention/deletion terms, and named authorizer."
    ),
    BuyerDataRequest(
        "NOW","BILLING_ACTUALS",
        "Provide authorized cloud billing/FOCUS export with stable account/service/resource identifiers and exact source hash."
    ),
    BuyerDataRequest(
        "NOW","INDEPENDENT_USAGE",
        "Provide independent meter/usage evidence used to reproduce expected charges."
    ),
    BuyerDataRequest(
        "NOW","COMMERCIAL_AUTHORITY",
        "Provide reviewed contract/rate/discount/commitment authority applicable to the selected period."
    ),
    BuyerDataRequest(
        "CONDITIONAL","SAVINGS_SIGNALS",
        "Provide savings/anomaly/reconciliation inputs only when those optional surfaces are in scope."
    ),
    BuyerDataRequest(
        "LATER_OUTCOME","SETTLEMENT",
        "Identify buyer-controlled credits/refunds/remittance evidence required to prove realized recovery later."
    ),
)

_BUYER_RESPONSIBILITIES=(
    "Authorize the exact read-only billing/account/date scope.",
    "Provide source exports without embedding credentials or secrets.",
    "Provide controlling commercial authority and all effective amendments.",
    "Name the buyer truth/review owner and later recovery-action approver.",
    "Keep settlement evidence independent from RecoveryWorks calculations.",
    "Separately approve any future external provider/vendor action.",
)

_RW_RESPONSIBILITIES=(
    "Hash and freeze authorized input evidence before calculation.",
    "Keep permission to process separate from financial evidence verification.",
    "Reproduce expected charges deterministically from controlling authority.",
    "Keep unsupported or ambiguous dollars in REVIEW rather than validated recovery.",
    "Separate validated recovery, prospective savings, anomaly exposure, and realized savings.",
    "Perform no cloud mutation or external recovery action from this packet.",
)

_STAGES=(
    "0 - Buyer-safe prelaunch review",
    "1 - Customer authorization and exact scope",
    "2 - Evidence intake/hash freeze",
    "3 - Independent evidence review",
    "4 - Deterministic recovery calculation",
    "5 - Buyer review of validated evidence packets",
    "6 - Separately authorized recovery/remediation actions if any",
    "7 - Independent settlement/readback evidence",
)

_REPORTS=(
    "validated/review recovery lifecycle totals",
    "recovery evidence packets",
    "prospective savings opportunities",
    "verified realized savings",
    "anomaly exposure and reconciliation drift",
)

_INVARIANTS=(
    "Estimated savings and anomaly exposure are not recovery dollars.",
    "Unverified controlling authority or evidence cannot produce VALIDATED recovery.",
    "Success-fee math applies only to independently verified recovered cash.",
    "Customer-data permission does not imply evidence verification.",
    "This packet does not authorize cloud mutation, vendor contact, claims, or money movement.",
)


def build_recoveryworks_activation_packet(
    decision:PilotLaunchDecision,
    brief:PilotLaunchBrief,
    commercial:CloudCommercialPilotPackage,
)->RecoveryWorksActivationPacket:
    if decision.status is PilotLaunchStatus.BLOCKED:
        raise ValueError("blocked launch gate cannot produce activation packet")
    if brief.launch_decision_id!=decision.decision_id:
        raise ValueError("launch brief decision id mismatch")
    if brief.launch_decision_proof_hash!=decision.proof_hash:
        raise ValueError("launch brief does not bind authoritative decision")
    if decision.commercial_package_proof_hash!=commercial.proof_hash:
        raise ValueError("launch gate commercial package mismatch")

    requests=tuple(_COMMON_REQUESTS)
    identity={
        "schema":1,
        "launch_decision_id":decision.decision_id,
        "launch_decision_proof_hash":decision.proof_hash,
        "launch_brief_proof_hash":brief.proof_hash,
        "commercial_package_proof_hash":commercial.proof_hash,
        "launch_status":decision.status.value,
        "offer_name":commercial.offer_name,
        "pricing_currency":commercial.pricing.currency,
        "diagnostic_fee_cents_hypothesis":commercial.pricing.diagnostic_fee_cents,
        "recovered_cash_success_fee_bps_hypothesis":
            commercial.pricing.recovered_cash_success_fee_bps,
        "monthly_assurance_fee_cents_hypothesis":
            commercial.pricing.monthly_assurance_fee_cents,
        "buyer_data_request_hashes":[x.proof_hash for x in requests],
        "buyer_responsibilities":list(_BUYER_RESPONSIBILITIES),
        "recoveryworks_responsibilities":list(_RW_RESPONSIBILITIES),
        "protocol_stages":list(_STAGES),
        "report_surfaces":list(_REPORTS),
        "commercial_invariants":list(_INVARIANTS),
        "customer_data_authorized":False,
        "kickoff_authorized":False,
        "outreach_authorized":False,
        "external_action_authorized":False,
        "contract_created":False,
    }
    return RecoveryWorksActivationPacket(
        packet_id="recoveryworks-activation-packet:"+canonical_hash(identity),
        launch_decision_id=decision.decision_id,
        launch_decision_proof_hash=decision.proof_hash,
        launch_brief_proof_hash=brief.proof_hash,
        commercial_package_proof_hash=commercial.proof_hash,
        launch_status=decision.status,
        offer_name=commercial.offer_name,
        pricing_currency=commercial.pricing.currency,
        diagnostic_fee_cents_hypothesis=commercial.pricing.diagnostic_fee_cents,
        recovered_cash_success_fee_bps_hypothesis=
            commercial.pricing.recovered_cash_success_fee_bps,
        monthly_assurance_fee_cents_hypothesis=
            commercial.pricing.monthly_assurance_fee_cents,
        buyer_data_requests=requests,
        buyer_responsibilities=_BUYER_RESPONSIBILITIES,
        recoveryworks_responsibilities=_RW_RESPONSIBILITIES,
        protocol_stages=_STAGES,
        report_surfaces=_REPORTS,
        commercial_invariants=_INVARIANTS,
        customer_data_authorized=False,kickoff_authorized=False,
        outreach_authorized=False,external_action_authorized=False,
        contract_created=False,
    )
