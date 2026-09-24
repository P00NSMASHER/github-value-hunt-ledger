"""Machine-checkable RecoveryWorks pilot prelaunch charter.

The charter freezes proposed scope, pricing hypotheses, roles, and explicit
acknowledgments around a buyer-safe activation packet. It is not an e-signature
system, legal contract, customer-data authorization, kickoff authorization, or
external-action authorization.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from enum import Enum
from typing import Any, Mapping

from recoveryworks.models import canonical_hash, normalize_sha256
from recoveryworks.pilot_activation_packet import RecoveryWorksActivationPacket
from recoveryworks.pilot_launch_gate import PilotLaunchStatus


class PilotCharterState(str,Enum):
    PENDING_ACKNOWLEDGMENT="PENDING_ACKNOWLEDGMENT"
    PRELAUNCH_ACCEPTED="PRELAUNCH_ACCEPTED"


@dataclass(frozen=True)
class PilotCharterRequest:
    engagement_id: str
    buyer_id: str
    business_unit: str
    population_rule: str
    source_date_start: str
    source_date_end: str
    billing_account_scope: tuple[str,...]
    provider_scope: tuple[str,...]
    diagnostic_fee_cents: int
    recovered_cash_success_fee_bps: int
    monthly_assurance_fee_cents: int
    buyer_truth_owner_role: str
    buyer_action_approver_role: str
    recoveryworks_engagement_owner_role: str
    buyer_acknowledges_scope: bool
    buyer_acknowledges_read_only_intake: bool
    buyer_acknowledges_report_surfaces_separate: bool
    buyer_acknowledges_no_guaranteed_recovery: bool
    buyer_acknowledges_success_fee_only_on_verified_recovered_cash: bool
    recoveryworks_acknowledges_no_external_action_without_separate_approval: bool


@dataclass(frozen=True)
class RecoveryWorksPilotCharter:
    charter_id: str
    state: PilotCharterState
    activation_packet_id: str
    activation_packet_proof_hash: str
    launch_decision_proof_hash: str
    engagement_id: str
    buyer_id: str
    business_unit: str
    population_rule: str
    source_date_start: str
    source_date_end: str
    billing_account_scope: tuple[str,...]
    provider_scope: tuple[str,...]
    diagnostic_fee_cents: int
    recovered_cash_success_fee_bps: int
    monthly_assurance_fee_cents: int
    buyer_truth_owner_role: str
    buyer_action_approver_role: str
    recoveryworks_engagement_owner_role: str
    acknowledgments: Mapping[str,bool]
    customer_data_authorized: bool = False
    kickoff_authorized: bool = False
    outreach_authorized: bool = False
    external_action_authorized: bool = False
    contract_created: bool = False

    def __post_init__(self)->None:
        for name in ("activation_packet_proof_hash","launch_decision_proof_hash"):
            object.__setattr__(self,name,normalize_sha256(name,getattr(self,name)))
        if not isinstance(self.state,PilotCharterState):
            raise ValueError("state must be PilotCharterState")
        if not self.acknowledgments:
            raise ValueError("charter acknowledgments are required")
        for key,value in self.acknowledgments.items():
            if type(value) is not bool:
                raise ValueError(f"acknowledgment {key} must be literal boolean")
        if (
            self.customer_data_authorized or self.kickoff_authorized
            or self.outreach_authorized or self.external_action_authorized
            or self.contract_created
        ):
            raise ValueError("prelaunch charter cannot authorize consequential actions")
        expected="recoveryworks-pilot-charter:"+canonical_hash(self._identity())
        if self.charter_id!=expected:
            raise ValueError("charter_id does not bind pilot charter")

    def _identity(self)->dict[str,Any]:
        return {
            "schema":1,"state":self.state.value,
            "activation_packet_id":self.activation_packet_id,
            "activation_packet_proof_hash":self.activation_packet_proof_hash,
            "launch_decision_proof_hash":self.launch_decision_proof_hash,
            "engagement_id":self.engagement_id,"buyer_id":self.buyer_id,
            "business_unit":self.business_unit,"population_rule":self.population_rule,
            "source_date_start":self.source_date_start,"source_date_end":self.source_date_end,
            "billing_account_scope":list(self.billing_account_scope),
            "provider_scope":list(self.provider_scope),
            "diagnostic_fee_cents":self.diagnostic_fee_cents,
            "recovered_cash_success_fee_bps":self.recovered_cash_success_fee_bps,
            "monthly_assurance_fee_cents":self.monthly_assurance_fee_cents,
            "buyer_truth_owner_role":self.buyer_truth_owner_role,
            "buyer_action_approver_role":self.buyer_action_approver_role,
            "recoveryworks_engagement_owner_role":self.recoveryworks_engagement_owner_role,
            "acknowledgments":dict(sorted(self.acknowledgments.items())),
            "customer_data_authorized":False,"kickoff_authorized":False,
            "outreach_authorized":False,"external_action_authorized":False,
            "contract_created":False,
        }

    @property
    def proof_hash(self)->str:
        return canonical_hash(self._identity())

    def as_dict(self)->dict[str,Any]:
        return {
            **self._identity(),
            "charter_id":self.charter_id,
            "proof_hash":self.proof_hash,
            "state_label":"PILOT_PRELAUNCH_CHARTER",
        }


def _required_text(name:str,value:Any)->str:
    if not isinstance(value,str) or not value.strip():
        raise ValueError(f"{name} is required")
    return value.strip()


def _iso_date(name:str,value:Any)->str:
    raw=_required_text(name,value)
    try:
        return date.fromisoformat(raw).isoformat()
    except ValueError as exc:
        raise ValueError(f"{name} must be YYYY-MM-DD") from exc


def pilot_charter_request_from_dict(data:Mapping[str,Any])->PilotCharterRequest:
    fields=PilotCharterRequest.__dataclass_fields__
    missing=sorted(set(fields)-set(data))
    extra=sorted(set(data)-set(fields))
    if missing:
        raise ValueError("missing charter fields: "+", ".join(missing))
    if extra:
        raise ValueError("unknown charter fields: "+", ".join(extra))
    ack_fields=(
        "buyer_acknowledges_scope",
        "buyer_acknowledges_read_only_intake",
        "buyer_acknowledges_report_surfaces_separate",
        "buyer_acknowledges_no_guaranteed_recovery",
        "buyer_acknowledges_success_fee_only_on_verified_recovered_cash",
        "recoveryworks_acknowledges_no_external_action_without_separate_approval",
    )
    for field in ack_fields:
        if type(data[field]) is not bool:
            raise ValueError(f"{field} must be literal boolean")
    for field in (
        "diagnostic_fee_cents",
        "recovered_cash_success_fee_bps",
        "monthly_assurance_fee_cents",
    ):
        if type(data[field]) is not int or data[field] < 0:
            raise ValueError(f"{field} must be a non-negative integer")
    if data["recovered_cash_success_fee_bps"] > 10000:
        raise ValueError("recovered_cash_success_fee_bps must be <=10000")
    return PilotCharterRequest(
        **{
            **dict(data),
            "billing_account_scope":tuple(data["billing_account_scope"]),
            "provider_scope":tuple(data["provider_scope"]),
        }
    )


def build_recoveryworks_pilot_charter(
    packet:RecoveryWorksActivationPacket,
    request:PilotCharterRequest,
)->RecoveryWorksPilotCharter:
    if packet.launch_status is PilotLaunchStatus.BLOCKED:
        raise ValueError("blocked launch packet cannot create prelaunch charter")
    for name in (
        "engagement_id","buyer_id","business_unit","population_rule",
        "buyer_truth_owner_role","buyer_action_approver_role",
        "recoveryworks_engagement_owner_role",
    ):
        _required_text(name,getattr(request,name))
    start=_iso_date("source_date_start",request.source_date_start)
    end=_iso_date("source_date_end",request.source_date_end)
    if end<start:
        raise ValueError("source_date_end cannot precede source_date_start")
    if not request.billing_account_scope or any(
        not isinstance(x,str) or not x.strip() for x in request.billing_account_scope
    ):
        raise ValueError("billing_account_scope must contain non-empty ids")
    if not request.provider_scope or any(
        not isinstance(x,str) or not x.strip() for x in request.provider_scope
    ):
        raise ValueError("provider_scope must contain non-empty providers")
    if request.diagnostic_fee_cents!=packet.diagnostic_fee_cents_hypothesis:
        raise ValueError("charter diagnostic fee differs from activation packet hypothesis")
    if (
        request.recovered_cash_success_fee_bps
        != packet.recovered_cash_success_fee_bps_hypothesis
    ):
        raise ValueError("charter success fee differs from activation packet hypothesis")
    if request.monthly_assurance_fee_cents!=packet.monthly_assurance_fee_cents_hypothesis:
        raise ValueError("charter monthly fee differs from activation packet hypothesis")

    acks={
        "buyer_acknowledges_scope":request.buyer_acknowledges_scope,
        "buyer_acknowledges_read_only_intake":request.buyer_acknowledges_read_only_intake,
        "buyer_acknowledges_report_surfaces_separate":
            request.buyer_acknowledges_report_surfaces_separate,
        "buyer_acknowledges_no_guaranteed_recovery":
            request.buyer_acknowledges_no_guaranteed_recovery,
        "buyer_acknowledges_success_fee_only_on_verified_recovered_cash":
            request.buyer_acknowledges_success_fee_only_on_verified_recovered_cash,
        "recoveryworks_acknowledges_no_external_action_without_separate_approval":
            request.recoveryworks_acknowledges_no_external_action_without_separate_approval,
    }
    for key,value in acks.items():
        if type(value) is not bool:
            raise ValueError(f"acknowledgment {key} must be literal boolean")
    state=(
        PilotCharterState.PRELAUNCH_ACCEPTED
        if all(acks.values())
        else PilotCharterState.PENDING_ACKNOWLEDGMENT
    )
    identity={
        "schema":1,"state":state.value,
        "activation_packet_id":packet.packet_id,
        "activation_packet_proof_hash":packet.proof_hash,
        "launch_decision_proof_hash":packet.launch_decision_proof_hash,
        "engagement_id":request.engagement_id,"buyer_id":request.buyer_id,
        "business_unit":request.business_unit,"population_rule":request.population_rule,
        "source_date_start":start,"source_date_end":end,
        "billing_account_scope":list(request.billing_account_scope),
        "provider_scope":list(request.provider_scope),
        "diagnostic_fee_cents":request.diagnostic_fee_cents,
        "recovered_cash_success_fee_bps":request.recovered_cash_success_fee_bps,
        "monthly_assurance_fee_cents":request.monthly_assurance_fee_cents,
        "buyer_truth_owner_role":request.buyer_truth_owner_role,
        "buyer_action_approver_role":request.buyer_action_approver_role,
        "recoveryworks_engagement_owner_role":request.recoveryworks_engagement_owner_role,
        "acknowledgments":dict(sorted(acks.items())),
        "customer_data_authorized":False,"kickoff_authorized":False,
        "outreach_authorized":False,"external_action_authorized":False,
        "contract_created":False,
    }
    return RecoveryWorksPilotCharter(
        charter_id="recoveryworks-pilot-charter:"+canonical_hash(identity),
        state=state,activation_packet_id=packet.packet_id,
        activation_packet_proof_hash=packet.proof_hash,
        launch_decision_proof_hash=packet.launch_decision_proof_hash,
        engagement_id=request.engagement_id,buyer_id=request.buyer_id,
        business_unit=request.business_unit,population_rule=request.population_rule,
        source_date_start=start,source_date_end=end,
        billing_account_scope=request.billing_account_scope,
        provider_scope=request.provider_scope,
        diagnostic_fee_cents=request.diagnostic_fee_cents,
        recovered_cash_success_fee_bps=request.recovered_cash_success_fee_bps,
        monthly_assurance_fee_cents=request.monthly_assurance_fee_cents,
        buyer_truth_owner_role=request.buyer_truth_owner_role,
        buyer_action_approver_role=request.buyer_action_approver_role,
        recoveryworks_engagement_owner_role=request.recoveryworks_engagement_owner_role,
        acknowledgments=acks,customer_data_authorized=False,
        kickoff_authorized=False,outreach_authorized=False,
        external_action_authorized=False,contract_created=False,
    )
